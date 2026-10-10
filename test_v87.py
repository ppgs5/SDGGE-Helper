# -*- coding: utf-8 -*-
"""v0.87 验证: 范围增益扩展 — 部队恢复收录 + 机体/驾驶员组合增强(双头像) + 最高值显示
① 数据: 补给机能=范围内的己方恢复HP20%(gamewith转录游戏表, 原16%修正)
② 范围增益 = 10 条: 4驾驶员技能 + 2驾驶员能力(岭司部队EN7%/马克部队HP5%) + 3武器 + 1单位技能
   组合行(LACUS=歌姬搭乗+2→MP+5 / 补给机能=奥利佛·梅搭乗+20%→HP40%) 显示 机体+驾驶员 双头像
   普通行右侧显示最高值(莉莉娜HP25% / TWC MP+3 / ν防护罩HP20% 等)
③ 不收录战舰
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8987

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

        # ① 数据
        r = pg.evaluate("""() => ({
          supply: q('SELECT DISTINCT desc FROM weapon_fx WHERE weapon_id=100900055006').map(x => x.desc),
          lacus: q('SELECT DISTINCT desc FROM weapon_fx WHERE weapon_id=133000590003').map(x => x.desc)
        })""")
        assert r['supply'] == ['范围内的己方恢复HP20%'], r
        assert r['lacus'] == ['范围内的己方MP增加3'], r
        print('[① 数据] 补给机能=HP20% / LACUS=MP增加3')
        print('[① 补给机能基础值修正(16%→20%) 通过]')

        # ② 范围增益
        pg.evaluate("() => { state.stack = []; setTab('feat'); }")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelector('[data-k=\"range_buff\"]').click()")
        pg.wait_for_timeout(2800)
        rows = pg.evaluate("""() => [...document.querySelectorAll('#farea .lrow')].map(e => ({
          t: e.dataset.t, id: +e.dataset.id, txt: e.textContent.replace(/\\s+/g, ' '),
          val: (e.querySelector('.val') || {}).textContent || null,
          pilot: !!e.querySelector('.ticon-col .avw.avsm .picon')
        }))""")
        print(f"[② 行数] {len(rows)}")
        for x in rows: print('   ', x['t'], x['id'], '| val=', x['val'], '| pilot=', x['pilot'], '|', x['txt'][:80])
        assert len(rows) == 10, len(rows)
        by = {x['id']: x for x in rows}
        # 组合行: LACUS(渣古战士) 双头像 + 歌姬 + MP+5
        lac = by[1330005900]
        assert lac['pilot'] and '歌姬' in lac['txt'] and lac['val'] == 'MP+5', lac
        assert 'LACUS' in lac['txt'] and 'MP增加3' in lac['txt'], lac
        # 组合行: 补给机能(比格·朗格) 双头像 + 奥利佛 + HP40%
        sup = by[1009000550]
        assert sup['pilot'] and '奥利佛' in sup['txt'] and sup['val'] == 'HP+40%', sup
        # 无增强的武器行: TWC 单头像 val MP+3
        twc = by[1139000100]
        assert not twc['pilot'] and twc['val'] == 'MP+3', twc
        # 部队恢复
        assert by[1604000100]['val'] == 'EN+7%' and '所属部队' in by[1604000100]['txt'], by[1604000100]
        assert by[1850000100]['val'] == 'HP+5%' and '所属部队' in by[1850000100]['txt'], by[1850000100]
        # 条件加成计入最高值
        assert by[1219000600]['val'] == 'HP+25%', by[1219000600]          # 莉莉娜 20%+W系列5%
        assert by[1114000450]['val'] == 'HP+20%', by[1114000450]          # ν双翼状 防护罩
        assert by[1300003203]['val'] == 'MP+5', by[1300003203]           # 拉克丝
        print('[② 范围增益=10条(含部队恢复2条; 组合双头像/最高值) 通过]')

        # ③ 不收录战舰
        assert all(x['t'] in ('char', 'unit') for x in rows), rows
        print('[③ 不收录战舰 通过]')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v87 全部通过 ===')
