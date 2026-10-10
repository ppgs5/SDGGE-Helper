# -*- coding: utf-8 -*-
"""v0.89 验证: ①6/7射程 MAP武器开关 + 主被动/主动技能不作用于MAP ②计算/图鉴武器行属性+整行点击跳武器图鉴 ③新特性「射程加」
①-④ 6/7射程: 三开关/ MAP行不受加成 / 阿普萨拉斯Ⅲ停于6射程 / MAP关=0条·MAP且飞翼EW退出
⑤ 机体页武器行: 属性chip(物理/光束/特殊) 无详细按钮, 整行点击跳武器页
⑥ 计算页武器表: 属性chip, 整行点击跳武器页
⑦ 射程加: 164位(被动7+主动157); 被动行带机体小头像; 合计值射程+N; 开关(主动关=7位/双关=0/恢复)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8989

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(120000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')

        pg.evaluate("() => { state.stack = []; setTab('feat'); }")
        pg.wait_for_timeout(2500)

        def snap(k):
            pg.evaluate(f"() => document.querySelector('[data-k=\"{k}\"]').click()")
            pg.wait_for_timeout(2600)
            return pg.evaluate("""() => ({ n: document.querySelectorAll('#farea .lrow').length,
              chips: [...document.querySelectorAll('#farea .chip')].map(e => e.textContent),
              rows: [...document.querySelectorAll('#farea .lrow')].map(e => ({ id: +e.dataset.id, txt: e.textContent.replace(/\\s+/g,' ') })) })""")

        # ① 三开关
        r6 = snap('range6')
        r7 = snap('range7')
        print('[① 6射程]', r6['n'], r6['chips'])
        assert len(r7['chips']) == 3 and r7['chips'][0].endswith(' 开') and ' 开（' in r7['chips'][1] and r7['chips'][2].endswith('统计'), r7['chips']
        print('[① 三开关(被动开/主动开/MAP统计) 通过]')

        # ② MAP行不受加成
        allrows = r6['rows'] + r7['rows']
        map_rows = [x for x in allrows if '·MAP' in x['txt']]
        bad = [x['txt'][:90] for x in map_rows if any(t in x['txt'] for t in ['机体被动', '驾驶员 ', '主动技能'])]
        print('[② 含MAP行]', len(map_rows), '| 带加成(应为0):', len(bad))
        assert map_rows and not bad, bad[:3]
        print('[② 主被动/主动技能不作用于MAP武器 通过]')

        # ③ 阿普萨拉斯Ⅲ
        apu6 = [x['txt'][:70] for x in r6['rows'] if '阿普萨拉斯' in x['txt']]
        apu7 = [x['txt'][:70] for x in r7['rows'] if '阿普萨拉斯' in x['txt']]
        print('[③ 阿普萨拉斯Ⅲ] in6:', apu6, '| in7:', apu7)
        assert apu6 and not apu7, (apu6, apu7)
        print('[③ 基础6·MAP 停于6射程 通过]')

        # ④ MAP关
        pg.evaluate("() => document.getElementById('rgm').click()")
        pg.wait_for_timeout(2600)
        r7m = pg.evaluate("""() => ({ n: document.querySelectorAll('#farea .lrow').length,
          mapRows: [...document.querySelectorAll('#farea .lrow')].filter(e => e.textContent.includes('·MAP')).length,
          ids: [...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id),
          chip: document.getElementById('rgm').textContent })""")
        print('[④ MAP关 7射程]', r7m['n'], '| ·MAP行:', r7m['mapRows'], '| 飞翼EW:', 1211000360 in r7m['ids'], '| chip:', r7m['chip'])
        assert r7m['mapRows'] == 0 and 1211000360 not in r7m['ids'] and '不统计' in r7m['chip'], r7m
        r6m = snap('range6')
        m6 = [x for x in r6m['rows'] if '·MAP' in x['txt']]
        print('[④ MAP关 6射程]', r6m['n'], '| ·MAP行:', len(m6))
        assert not m6, m6[:2]
        # 切回恢复
        pg.evaluate("() => document.getElementById('rgm').click()")
        pg.wait_for_timeout(2600)
        n6 = pg.evaluate("() => document.querySelectorAll('#farea .lrow').length")
        print('[④ 切回 6射程]', n6, '(应恢复 %d)' % r6['n'])
        assert n6 == r6['n'], (n6, r6['n'])
        print('[④ MAP武器开关(关=不统计, 切回恢复) 通过]')

        # ⑤ 图鉴机体页: 武器名后属性(物理/光束/特殊) + 详细按钮跳武器图鉴
        pg.evaluate("() => { state.stack = []; push({ page: 'unit', title: 'x', id: 1001000150 }); }")
        pg.wait_for_timeout(1600)
        wrows = pg.evaluate("""() => [...document.querySelectorAll('#view .wrow')].map(e => ({
          wid: +e.dataset.id, txt: e.textContent.replace(/\\s+/g,' '),
          attr: (e.querySelector('.wattr') || {}).textContent || null,
          det: !!e.querySelector('.fbtn[data-wdet]') }))""")
        print('[⑤ 机体页武器行]', len(wrows))
        for x in wrows: print('   ', x['wid'], '| attr=', x['attr'], '| det=', x['det'], '|', x['txt'][:70])
        assert wrows and all(x['attr'] in ('物理', '光束', '特殊', '光束/物理', '物理/特殊', '光束/特殊', '全属性') for x in wrows), wrows
        assert not any(x['det'] for x in wrows), '详细按钮应已取消'
        saber = next(x for x in wrows if '光束军刀 EX' in x['txt'])
        assert saber['attr'] == '光束/物理', saber   # 武器属性复合(4=光束/物理)
        saber2 = next(x for x in wrows if x['wid'] == 100100015002)
        assert saber2['attr'] == '光束', saber2        # 光束步枪 = 光束
        pg.evaluate("() => { document.querySelector('#view .wrow').click(); }")
        pg.wait_for_timeout(1400)
        t = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '每级数据' in t and '光束军刀 EX' in t, t[:200]
        print('[⑤ 机体页武器属性(无按钮, 整行点击跳武器页)] 通过')

        # ⑥ 计算页武器表: 属性 + 整行点击跳转
        pg.evaluate("() => { state.stack = []; state.calc = Object.assign(state.calc, { unitId: 1001000150, charId: null }); setTab('calc'); }")
        pg.wait_for_timeout(2600)
        cr = pg.evaluate("""() => [...document.querySelectorAll('#view table.ctable tr')].slice(1).map(r => ({
          txt: r.textContent.replace(/\\s+/g,' '), attr: (r.querySelector('.wattr') || {}).textContent || null,
          det: !!r.querySelector('.fbtn[data-wdet]') }))""")
        print('[⑥ 计算页武器行]', len(cr))
        for x in cr[:3]: print('   ', '| attr=', x['attr'], '| det=', x['det'], '|', x['txt'][:70])
        assert cr and all(x['attr'] for x in cr) and not any(x['det'] for x in cr), cr[:3]
        pg.evaluate("() => { document.querySelector('#view table.ctable tr[data-wid]').click(); }")
        pg.wait_for_timeout(1400)
        t2 = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '每级数据' in t2, t2[:200]
        print('[⑥ 计算页武器属性(无按钮, 整行点击跳武器页)] 通过')

        # ⑦ 射程加: 驾驶员被动/主动射程提升合计(带机体小头像与开关)
        pg.evaluate("() => { state.stack = []; setTab('feat'); }")
        pg.wait_for_timeout(2200)
        pg.evaluate("() => document.querySelector('[data-k=\"range_up\"]').click()")
        pg.wait_for_timeout(2800)
        ru = pg.evaluate("""() => ({ n: document.querySelectorAll('#farea .lrow').length,
          chips: [...document.querySelectorAll('#farea .chip')].map(e => e.textContent),
          rows: [...document.querySelectorAll('#farea .lrow')].map(e => ({
            id: +e.dataset.id, val: (e.querySelector('.val') || {}).textContent,
            sub: !!e.querySelector('.ticon-col .avw.avsm'),
            txt: e.textContent.replace(/\\s+/g,' ') })) })""")
        print('[⑦ 射程加]', ru['n'], ru['chips'])
        assert ru['chips'][0].startswith('被动技能') and ru['chips'][1].startswith('主动技能'), ru['chips']
        by7 = {x['id']: x for x in ru['rows']}
        # 被动例: 阿姆罗(1110000102, 需搭乘 Hi-ν) — 带机体小头像
        am = by7[1110000102]
        assert am and am['val'] == '射程+1' and am['sub'] and 'Hi-ν' in am['txt'], am
        # 主动例: 夏亚 THE ORIGIN(1003000100) — 射程增幅+1 无机体头像
        cha = by7[1003000100]
        assert cha and cha['val'] == '射程+1' and not cha['sub'] and '射程增幅' in cha['txt'], cha
        # 关主动 → 只剩被动持有者(7)
        pg.evaluate("() => document.getElementById('rgs').click()")
        pg.wait_for_timeout(2400)
        n2 = pg.evaluate("() => document.querySelectorAll('#farea .lrow').length")
        pids = pg.evaluate("() => [...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id)")
        print('[⑦ 主动关]', n2, pids)
        assert n2 == 7 and am['id'] == 1110000102 and 1110000102 in pids, (n2, pids)
        # 关被动 → 0(无主人被动时全被过滤)
        pg.evaluate("() => document.getElementById('rgp').click()")
        pg.wait_for_timeout(2400)
        n3 = pg.evaluate("() => document.querySelectorAll('#farea .lrow').length")
        print('[⑦ 双关]', n3)
        assert n3 == 0, n3
        # 恢复
        pg.evaluate("() => { document.getElementById('rgp').click(); }")
        pg.wait_for_timeout(2200)
        pg.evaluate("() => { document.getElementById('rgs').click(); }")
        pg.wait_for_timeout(2400)
        n4 = pg.evaluate("() => document.querySelectorAll('#farea .lrow').length")
        print('[⑦ 双开恢复]', n4)
        assert n4 == ru['n'], (n4, ru['n'])
        print('[⑦ 射程加(合计值/机体头像/开关) 通过]')

        # ⑧ 射程加受筛选(标签)生效
        pg.evaluate("() => document.getElementById('ftag').click()")
        pg.wait_for_timeout(1200)
        pg.evaluate("""() => { const rows = [...document.querySelectorAll('#sheetPanel .trow2')];
          const el = rows.find(e => /^新人类\d*$/.test(e.textContent.trim())); if (el) el.click();
          document.querySelector('#sheetPanel [data-m=\"or\"]').click(); }""")
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.querySelector('#sapply').click()")
        pg.wait_for_timeout(2600)
        f1 = pg.evaluate("""() => ({ n: document.querySelectorAll('#farea .lrow').length,
          ok: [...document.querySelectorAll('#farea .lrow')].every(e => charMetaOf(+e.dataset.id).tags.has('新人类')),
          badge: document.getElementById('ftag').textContent.replace(/\\s+/g,' ') })""")
        print('[⑧ 标签筛后]', f1)
        assert f1['n'] == 29, f1   # 射程加164人中含「新人类」标签29位
        assert f1['n'] > 0 and f1['n'] < ru['n'] and f1['ok'], f1
        # 清除恢复
        pg.evaluate("() => document.getElementById('ftag').click()")
        pg.wait_for_timeout(1200)
        pg.evaluate("() => document.querySelector('#sheetPanel #sclear').click()")
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#sapply').click()")
        pg.wait_for_timeout(2600)
        n8 = pg.evaluate("() => document.querySelectorAll('#farea .lrow').length")
        print('[⑧ 清除恢复]', n8)
        assert n8 == ru['n'], (n8, ru['n'])
        print('[⑧ 射程加受标签/系列筛选] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v89 全部通过 ===')
