# -*- coding: utf-8 -*-
"""v0.32 验证: 排行页 — 行内武器属性显示(射程后) + 筛选(武器属性/类型/机体类型/稀有度)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8943
AATTR = {1: '物理', 2: '光束', 3: '特殊', 4: '光束/物理', 5: '物理/特殊', 6: '光束/特殊', 7: '全属性'}
WATTR = {1: ['ranged'], 2: ['melee'], 3: ['awaken'], 4: ['ranged', 'melee'], 5: ['ranged', 'awaken'], 6: ['melee', 'awaken'], 7: ['ranged', 'melee', 'awaken']}
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 400, 'height': 860})
        pg.set_default_timeout(240000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append('console.' + m.type + ': ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        print('[boot] ok')

        def rows(n=5):
            return pg.evaluate("""(n) => [...document.querySelectorAll('#rlist .rrow')].slice(0, n).map(el => {
              const wid = +el.dataset.wid, uid = +el.dataset.id;
              const w = q1('SELECT weapon_attr, attack_attr FROM weapons WHERE id=?', [wid]) || {};
              const u = q1('SELECT role, rarity FROM units WHERE id=?', [uid]) || {};
              const chip = el.querySelector('.wattr');
              return {wat: w.weapon_attr, aa: w.attack_attr, role: u.role, rar: u.rarity, chip: chip ? chip.textContent : ''};
            })""", n)

        pg.click('[data-tab="rank"]'); pg.wait_for_selector('#rlist .rrow', timeout=120000); pg.wait_for_timeout(3500)
        r0 = rows()
        print('[默认 前5行]', [(x['chip'], x['wat'], x['role'], x['rar']) for x in r0])
        assert r0 and all(x['chip'] and x['chip'] in AATTR.values() for x in r0), '行内应显示武器属性且与数据一致'
        assert all(x['chip'] == AATTR[x['wat']] for x in r0), '行内属性文本应与 weapon_attr 对应'

        # 武器属性=光束
        pg.click("[data-wat='光束']"); pg.wait_for_timeout(4000)
        r1 = rows()
        print('[属性=光束]', [(x['chip'], x['wat']) for x in r1])
        assert r1 and all('光束' in AATTR[x['wat']] for x in r1), '光束筛选异常'

        # 类型=格斗
        pg.click("[data-atk='melee']"); pg.wait_for_timeout(4000)
        r2 = rows()
        print('[类型=格斗]', [(x['chip'], x['wat'], x['aa']) for x in r2])
        assert r2 and all('melee' in WATTR[x['aa']] for x in r2), '格斗筛选异常'

        # 机体类型=支援型
        pg.click("[data-atk='all']"); pg.wait_for_timeout(3500)
        pg.click("[data-urole='3']"); pg.wait_for_timeout(4000)
        r3 = rows()
        print('[机体=支援型]', [(x['role'], x['rar']) for x in r3])
        assert r3 and all(x['role'] == 3 for x in r3), '机体类型筛选异常'

        # 稀有度=UR (叠加)
        pg.click("[data-rar='5']"); pg.wait_for_timeout(4000)
        r4 = rows()
        print('[+稀有度=UR]', [(x['role'], x['rar']) for x in r4])
        assert r4 and all(x['role'] == 3 and x['rar'] == 5 for x in r4), '稀有度叠加筛选异常'
        hit4 = pg.evaluate("() => document.getElementById('rhit').textContent")
        print('[条数]', hit4)
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/44a_rank_filters.png')

        # 全部复位
        pg.click("[data-urole='all']"); pg.wait_for_timeout(3500)
        pg.click("[data-rar='all']"); pg.wait_for_timeout(3500)
        r5 = rows()
        print('[复位]', [(x['chip'], x['role'], x['rar']) for x in r5])
        assert len(r5) >= 3, '复位后应有足够结果'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/44b_rank_reset.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
