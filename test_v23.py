# -*- coding: utf-8 -*-
"""v0.24 验证: SSP武器数据补全(核心解放词条+战意限制) / SSR以下恒3星 / SSP满10开关"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8897
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

        # ---------- 1. SSP武器页: 效果值UP词条 + 战意限制 ----------
        pg.evaluate("() => push({page:'weapon', title:'x', id:137000590090})")
        pg.wait_for_timeout(800)
        w = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        print('[强化巨剑SSP]', w[:260])
        assert '武装效果的效果值UP(且最大值提升3%)' in w, '缺 效果值UP 词条'
        assert '战意为超强势以上时即可使用' in w, '缺 战意使用限制'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/34a_ssp_weapon.png')

        # ---------- 2. 计算页: SSR以下恒3星 + SSP满10 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '00强化模组'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pick='1370005900']"); pg.wait_for_timeout(2600)
        st = pg.evaluate("() => ({star: document.getElementById('star').textContent, on: document.getElementById('star').classList.contains('on'), ssp: !!document.getElementById('ssp')})")
        print('[星数chip]', st)
        assert 'SSR及以下固定' in st['star'] and st['on'], 'SSR以下应固定三星'
        atk0 = pg.evaluate("() => document.querySelector('#picku small').textContent.replace(/\\s+/g,' ')")
        print('[SSP关]', atk0[:80])
        pg.click('#ssp'); pg.wait_for_timeout(2600)
        atk1 = pg.evaluate("() => document.querySelector('#picku small').textContent.replace(/\\s+/g,' ')")
        print('[SSP满10开]', atk1[:80])
        assert atk0 != atk1, 'SSP开关未影响攻击'
        # 数值校验: floor(floor((sp_max_atk+g)*1.4)*(1+被动%/100)), g=round(ssp_max_attack*10/19)
        chk = pg.evaluate("""() => {
          const u = q1('SELECT * FROM units WHERE id=1370005900');
          const g = sspGainOf(u, 10);
          const pct = +(document.querySelector('#picku small').textContent.match(/被动\\+(\\d+)%/) || [0, 0])[1];
          const sp = u.sp_max_atk || u.max_atk;
          return {
            expOff: Math.floor(Math.floor(sp * 1.4) * (1 + pct / 100)),
            expOn:  Math.floor(Math.floor((sp + g.atk) * 1.4) * (1 + pct / 100)),
            g, pct
          };
        }""")
        print('[期望攻击]', chk)
        assert f"{chk['expOff']:,}" in atk0, f'SSP关攻击值应为 {chk["expOff"]}'
        assert f"{chk['expOn']:,}" in atk1, f'SSP满10攻击值应为 {chk["expOn"]}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/34b_ssp_calc.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
