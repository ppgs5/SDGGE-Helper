# -*- coding: utf-8 -*-
"""v146 验证: 计算页星级改为 0/1/2/3 单选，并显示机体面板(攻/防/机动/HP)
① 4 个星级 chip，且只有 1 个处于选中态；点击 ★1 后 c.star=1
② 面板攻击 ★0=7,608 / ★3=10,651（重生EX max_atk 7608 × [1.0,1.4]）
③ 面板显示 防御/机动/HP
④ 面板随「我方全能力+X%」提升
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9129

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1600}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        def panel(star, allup=0):
            pg.evaluate("""([star, allup]) => { const c = state.calc; c.unitId=1370011150; c.star=star; c.allup=allup;
              state._prKey=null; state.stack=[]; push({page:'calc',title:'计算'}); render(); }""", [star, allup])
            pg.wait_for_timeout(1500)
            return pg.evaluate("""() => { const t = document.getElementById('view').innerText;
              const seg = (t.split('机体面板:')[1] || '').split('驾驶员稀有度')[0];
              const num = k => { const m = seg.match(new RegExp(k + ' ([\\\\d,]+)')); return m ? +m[1].replace(/,/g,'') : null; };
              const on = [...document.querySelectorAll('#view [data-cstar]')].filter(e => e.className.includes('on') || e.className.includes('gold')).length;
              return { atk: num('攻击'), def: num('防御'), mob: num('机动'), hp: num('HP'), chips: document.querySelectorAll('#view [data-cstar]').length, on }; }""")

        r0 = panel(0); r3 = panel(3)
        print('[① chips/选中]', r0['chips'], r0['on'], '| ★0:', r0, '| ★3:', r3)
        assert r0['chips'] == 4 and r0['on'] == 1, r0
        assert r0['atk'] == 7608 and r3['atk'] == 10651, (r0['atk'], r3['atk'])
        assert r0['def'] and r0['mob'] and r0['hp'], r0

        pg.evaluate("() => { const el=[...document.querySelectorAll('#view [data-cstar]')].find(e=>e.dataset.cstar==='1'); el.click(); }")
        pg.wait_for_timeout(1200)
        st = pg.evaluate("() => state.calc.star")
        print('[① 点击★1]', st)
        assert st == 1, st

        r30 = panel(3, 30)
        print('[④ 全能力30%]', r30)
        assert r30['atk'] == int(10651 * 1.3), r30['atk']

        assert not errors, errors
        print('=== test_v146 全部通过 ===')
        b.close()
finally:
    srv.terminate()
