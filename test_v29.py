# -*- coding: utf-8 -*-
"""v0.30 验证: 机体页数值口径 — SSR及以下 SP/SSP满10 开关; UR 突破星数选择(★0-★3)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8939
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

        def stats():
            return pg.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#view .statgrid .stat')].map(e => {
              const k = e.querySelector('.k').textContent;
              const v = e.querySelector('.v').textContent;
              const o = e.children[2] ? e.children[2].textContent : '';
              return [k, v + (o ? '|' + o : '')];
            }))""")

        # ---------- 1. SR 高达: SP / SSP 开关 ----------
        pg.evaluate("() => push({page:'unit', title:'x', id:1001000100})"); pg.wait_for_timeout(800)
        s0 = stats()
        print('[SR 默认]', s0)
        assert s0['攻击'] == '5,282' and s0['HP'] == '50,501', '默认应为基础Lv100数值'
        assert pg.evaluate("() => !!document.getElementById('usp') && !!document.getElementById('uss')"), 'SR应有SP/SSP开关'
        pg.click('#usp'); pg.wait_for_timeout(700)
        s1 = stats()
        print('[SR SP开]', s1)
        assert s1['攻击'] == '9,401|原 5,282', f'SP后攻击应为9401(6715×1.4): {s1["攻击"]}'
        assert s1['HP'] == '89,892|原 50,501', f'SP后HP应为89892(64209×1.4): {s1["HP"]}'
        pg.click('#uss'); pg.wait_for_timeout(700)
        s2 = stats()
        print('[SR SP+SSP]', s2)
        assert s2['攻击'] == '9,755|原 5,282', f'SSP后攻击应为9755((6715+253)×1.4): {s2["攻击"]}'
        assert s2['移动'] == '4', '移动不应受倍率影响'
        pg.click('#usp'); pg.wait_for_timeout(700)
        s3 = stats()
        print('[SR 全关]', s3)
        assert s3['攻击'] == '5,282' and 'uss' in pg.evaluate("() => document.getElementById('uss') ? 'uss' : ''"), '关闭SP应回基础值(SSP同时关)'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/42a_unit_sr.png')

        # ---------- 2. UR 高达(EX): 星数选择 ----------
        pg.evaluate("() => push({page:'unit', title:'x', id:1001000150})"); pg.wait_for_timeout(800)
        u0 = stats()
        print('[UR ★0]', u0)
        assert u0['攻击'] == '7,776', 'UR默认★0应为基础值'
        n = pg.evaluate("() => document.querySelectorAll('[data-ustar]').length")
        assert n == 4, f'UR应有4个星数选项: {n}'
        assert not pg.evaluate("() => !!document.getElementById('usp')"), 'UR不应有SP开关'
        pg.click("[data-ustar='3']"); pg.wait_for_timeout(700)
        u3 = stats()
        print('[UR ★3]', u3)
        assert u3['攻击'] == '10,886|原 7,776', f'★3攻击应为10886(7776×1.4): {u3["攻击"]}'
        assert u3['HP'] == '131,826|原 94,162', f'★3 HP应为131826: {u3["HP"]}'
        pg.click("[data-ustar='1']"); pg.wait_for_timeout(700)
        u1 = stats()
        print('[UR ★1]', u1)
        assert u1['攻击'] == '9,331|原 7,776', f'★1攻击应为9331(7776×1.2): {u1["攻击"]}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/42b_unit_ur.png')

        # ---------- 3. SSR 00强化模组: SP/SSP 与计算页口径一致 ----------
        pg.evaluate("() => push({page:'unit', title:'x', id:1370005900})"); pg.wait_for_timeout(800)
        r0 = stats()
        assert r0['攻击'] == '6,966', f'00R默认攻击应为基础6966: {r0["攻击"]}'
        pg.click('#usp'); pg.wait_for_timeout(700)
        r1 = stats()
        print('[00R SP]', r1['攻击'])
        assert r1['攻击'] == '10,850|原 6,966', f'SP后应为10850(7750×1.4): {r1["攻击"]}'
        pg.click('#uss'); pg.wait_for_timeout(700)
        r2 = stats()
        print('[00R SSP]', r2['攻击'])
        assert r2['攻击'] == '11,253|原 6,966', f'SSP后应为11253((7750+288)×1.4): {r2["攻击"]}'

        # ---------- 4. ULT: 固定无选择 ----------
        ult = pg.evaluate("() => (q1('SELECT id FROM units WHERE ult=1 LIMIT 1') || {}).id")
        if ult:
            pg.evaluate(f"() => push({{page:'unit', title:'x', id:{ult}}})"); pg.wait_for_timeout(700)
            n2 = pg.evaluate("() => document.querySelectorAll('[data-ustar]').length")
            assert n2 == 0 and not pg.evaluate("() => !!document.getElementById('usp')"), 'ULT不应有星数/SP开关'
            print('[ULT] 无开关 ✓')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
