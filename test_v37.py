# -*- coding: utf-8 -*-
"""v0.38 验证: 卡特吉娜·露丝(渣斯卡路帝国+1移动/支援防御)纳入6移动 + 特性页机体头像显示类型角标"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8969
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

        # ---------- 0. 数据层 ----------
        chk = pg.evaluate("""() => {
          const rows = q("SELECT target_id, params_json FROM features WHERE feature='move6'", []);
          const kata = rows.filter(r => JSON.parse(r.params_json).pilot === 1175000500).map(r => r.target_id);
          const k = id => rows.find(r => r.target_id === id);
          return {
            n6: rows.length, kataN: kata.length,
            gotratan: k(1175001150) ? JSON.parse(k(1175001150).params_json).pilot : 0,   // 哥特拉坦(EX) 移动5 → 6
            zeroth: k(1175002610) ? 1 : 0,     // 索罗(克罗诺克尔专用) 移动4 → 5, 不应入列
            role: q1('SELECT role FROM units WHERE id=1175001150').role,
          };
        }""")
        print('[数据]', chk)
        assert chk['n6'] == 47, f'6移动应为47条: {chk["n6"]}'
        assert chk['kataN'] == 28, f'卡特吉娜行应为28条: {chk["kataN"]}'
        assert chk['gotratan'] == 1175000500, '哥特拉坦(EX)应由卡特吉娜达成6移动'
        assert chk['zeroth'] == 0, '移动4的机体(+1=5)不应入列'

        # ---------- 1. 特性页 UI: 驾驶员头像 + 机体类型角标 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow'); pg.wait_for_timeout(600)
        pg.click("[data-k='move6']"); pg.wait_for_timeout(1200)
        rows = pg.evaluate("""() => [...document.querySelectorAll('#farea .lrow')].map(el => ({
            name: el.querySelector('.nm').textContent.replace(/\\s+/g,' ').slice(0, 26),
            pip: !!el.querySelector('.picon'),
            roleb: (el.querySelector('.roleb') || {}).className || '',
        }))""")
        g = [r for r in rows if '哥特拉坦' in r['name']]
        t = [r for r in rows if '老虎特装型' in r['name']]
        k2 = [r for r in rows if '京宝梵' in r['name']]
        print('[哥特拉坦]', g, '[老虎]', t, '[京宝梵]', k2)
        assert g and g[0]['pip'], '哥特拉坦行应有卡特吉娜头像'
        assert t and t[0]['pip'], '老虎特装型行应有驾驶员头像'
        assert k2 and not k2[0]['pip'], '京宝梵行无驾驶员'
        assert all(r['roleb'].startswith('roleb') for r in rows), f"所有机体头像应有类型角标: {[r for r in rows if not r['roleb']][:3]}"
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/48a_move6_kata.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
