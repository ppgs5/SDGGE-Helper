# -*- coding: utf-8 -*-
"""v122 验证: 再生高达EX 原配机师 + 图鉴数值档位说明
① units.default_char_id: 1370011150 → 1370003501 (利保逊‧阿路玛古)
② 图鉴详情显示「原配驾驶员」及角色名
③ 攻击档位: 原值10651 / 主被动13313(单位技能+25%) / max13633(再含对战次数条件+3%)
   页面 hint 说明 max 含条件型
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9063
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        r1 = pg.evaluate("""() => {
          const u = q1('SELECT * FROM units WHERE id=1370011150');
          const c = u.default_char_id ? q1('SELECT id,name FROM characters WHERE id=?', [u.default_char_id]) : null;
          const v = {}; for (const m of [1, 2, 3]) v[m] = unitListStat(u, 'atk', m, 3);
          return { dcid: u.default_char_id, cname: c && c.name, v, bst: unitBstMaps()[1370011150] }; }""")
        print('[① 原配/档位]', r1)
        assert r1['dcid'] == 1370003501 and r1['cname'] == '利保逊‧阿路玛古', r1
        assert r1['v'] == {'1': 10651, '2': 13313, '3': 15230}, r1
        assert r1['bst']['2']['atk'] == 25 and r1['bst']['3']['atk'] == 43, r1
        print('[① 原配机师已补 / 主被动25% · max43%(+对战次数18%满层) 通过]')

        pg.evaluate("() => { state.stack = []; push({ page:'unit', title:'x', id:1370011150 }); render(); }")
        pg.wait_for_function("() => (document.getElementById('ubb') || {}).innerText.includes('原配驾驶员')", timeout=120000)
        t = pg.evaluate("() => document.getElementById('view').innerText")
        assert '原配驾驶员' in t and '利保逊‧阿路玛古' in t, t[:400]
        assert 'max=再含条件型被动' in t, t[:400]
        print('[② 图鉴原配驾驶员 + 档位说明 通过]')

        assert not errors, errors
        print('=== test_v122 全部通过 ===')
        b.close()
finally:
    srv.terminate()
