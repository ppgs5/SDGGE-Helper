# -*- coding: utf-8 -*-
"""v0.88 验证: 特性「6射程/7射程」 — 武器可达最大射程统计(同6/7移动口径)
来源: 基础射程 / SSP満10 / 机体被动(trait72) / 驾驶员被动(trait72, 开关) / 主动技能「射程增幅」(trait3, 开关); 可叠层
① 默认(双开关开): 6射程=恰好6(≥450台), 7射程≥60台(含大蛇等6+主动技能)
② 主动技能关(rgS off): 6射程=65台(基础/SSP/机体被动/驾驶员被动); 大蛇退出7射程
③ 驾驶员被动关(rgP off)+主动关: 7射程=3台(飞翼EW基础7 / V2突击暴风·飞翼零式机体被动), 多鲁基斯Ⅲ(需驾驶员被动)退出
④ 叠层行: 斗狼=SSP満10+机体被动+主动技能 → 射程7; 开关状态与chip显示一致
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8988

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

        def snap(k):
            pg.evaluate(f"() => document.querySelector('[data-k=\"{k}\"]').click()")
            pg.wait_for_timeout(2600)
            return pg.evaluate("""() => ({ n: document.querySelectorAll('#farea .lrow').length,
              chips: [...document.querySelectorAll('#farea .chip')].map(e => e.textContent),
              rows: [...document.querySelectorAll('#farea .lrow')].map(e => ({ id: +e.dataset.id, txt: e.textContent.replace(/\\s+/g,' '), pilot: !!e.querySelector('.ticon-col .avw.avsm') })) })""")

        def toggle(cid, k):
            pg.evaluate(f"() => document.getElementById('{cid}').click()")
            pg.wait_for_timeout(2600)
            return pg.evaluate("""() => ({ n: document.querySelectorAll('#farea .lrow').length,
              chips: [...document.querySelectorAll('#farea .chip')].map(e => e.textContent) })""")

        pg.evaluate("() => { state.stack = []; setTab('feat'); }")
        pg.wait_for_timeout(2500)

        # ① 默认双开
        r6 = snap('range6')
        nskill = pg.evaluate("""() => { const s = new Set();
          for (const t of ['char_skills', 'char_skills_sp'])
            for (const x of q(`SELECT char_id, traits_json FROM ${t}`)) {
              let ts = []; try { ts = JSON.parse(x.traits_json || '[]'); } catch (e) { continue; }
              for (const y of ts) { const tr = (y||{}).trait||{}; if (tr.trait_type === 3 && String(tr.desc||'').indexOf('射程') >= 0) s.add(x.char_id); }
            }
          return s.size; }""")
        print('[① 6射程]', r6['n'], r6['chips'])
        assert r6['n'] >= 450, r6['n']
        assert r6['chips'][0].endswith(' 开') and r6['chips'][1].startswith('主动技能') and ' 开（' in r6['chips'][1] and f'{nskill}位持有' in r6['chips'][1], r6['chips']
        r7 = snap('range7')
        print('[① 7射程]', r7['n'])
        assert r7['n'] >= 60, r7['n']
        assert any('大蛇' in x['txt'] and '主动技能' in x['txt'] for x in r7['rows']), '大蛇应含主动技能路径'
        print(f'[① 默认双开(6射程{r6["n"]}/7射程{r7["n"]}, 射程增幅{nskill}位持有) 通过]')

        # ② 主动关
        r7b = toggle('rgs', 'range7')
        print('[② 主动关 7射程]', r7b['n'], r7b['chips'][1])
        assert ' 关（' in r7b['chips'][1], r7b['chips']
        ids = set(pg.evaluate("() => [...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id)"))
        assert 1009000310 not in ids and 1211000360 in ids, ('大蛇(1009000310)应退出7射程/飞翼EW保留', sorted(ids)[:10])
        r6b = snap('range6')
        print('[② 主动关 6射程]', r6b['n'])
        assert r6b['n'] == 65, r6b['n']
        print('[② 主动技能开关(6射程回落65台) 通过]')

        # ③ 双关: 先关驾驶员被动(仍在range6视图), 回 range7 断言 3 台
        toggle('rgp', 'range6')
        r7c = snap('range7')
        print('[③ 双关 7射程]', r7c['n'], r7c['chips'])
        assert r7c['n'] == 3 and ' 关' in r7c['chips'][0] and ' 关（' in r7c['chips'][1], r7c
        names = [x['txt'][:16] for x in r7c['rows']]
        print('   行:', names)
        assert all(('飞翼' in x['txt'] or 'V2' in x['txt']) for x in r7c['rows']), r7c['rows']
        assert not any(x['pilot'] for x in r7c['rows']), '双关下不应有驾驶员头像'
        # ④ 只开驾驶员被动 → 多鲁基斯Ⅲ 回归(4台, 带头像)
        r7d = toggle('rgp', 'range7')
        print('[③ 仅被动开 7射程]', r7d['n'])
        rows7d = pg.evaluate("() => [...document.querySelectorAll('#farea .lrow')].map(e => ({ id: +e.dataset.id, pilot: !!e.querySelector('.ticon-col .avw.avsm') }))")
        assert r7d['n'] == 4 and any(x['pilot'] for x in rows7d), (r7d['n'], rows7d)
        print('[③ 驾驶员被动开关(3→4台, 头像) 通过]')

        # ④ 再开主动技能 → 69; 叠层行: 斗狼=SSP+机体被动+主动技能 → 7
        r7e = toggle('rgs', 'range7')
        row = pg.evaluate("""() => { const el = [...document.querySelectorAll('#farea .lrow')].find(e => e.textContent.includes('斗狼')); return el ? el.textContent.replace(/\s+/g,' ') : null; }""")
        print('[④ 双开 7射程]', r7e['n'], '| 斗狼行:', (row or '')[:110])
        assert r7e['n'] >= 60, r7e['n']
        assert row and '机体被动' in row and '主动技能' in row and '射程7' in row, row
        print('[④ 叠层(SSP+机体被动+主动技能→7) 通过]')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v88 全部通过 ===')
