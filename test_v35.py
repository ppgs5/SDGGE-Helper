# -*- coding: utf-8 -*-
"""v0.36 验证: 特性页 6移动/7移动 — 机体+驾驶员被动; 需特定驾驶员的行显示驾驶员头像"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8961
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
          const get = id => { const r = rows.find(x => x.target_id === id); return r ? JSON.parse(r.params_json) : null; };
          return {
            n6: rows.length,
            n7: q("SELECT COUNT(*) c FROM features WHERE feature='move7'", [])[0].c,
            tiger: get(1013000850),      // 老虎特装型: 需特定驾驶员(自护公国军)
            kyo: get(1017000900),        // 京宝梵: 机体自身(战意) → 无驾驶员
            shin: get(1125001250),       // 新安州(EX): 弗尔·伏朗特
            zaku: get(1031000300),       // 精神感应渣古(移动4): 不应入列
          };
        }""")
        print('[数据]', {k: (v if not isinstance(v, dict) else {kk: v[kk] for kk in ('pilot', 'base', 'total')}) for k, v in chk.items()})
        assert chk['n6'] == 47, f'6移动应为47条: {chk["n6"]}'
        assert chk['n7'] == 0, '7移动当前无数据'
        assert chk['tiger'] and chk['tiger']['pilot'] and chk['tiger']['total'] == 6, '老虎特装型应带驾驶员头像且达6'
        assert chk['kyo'] and chk['kyo']['pilot'] == 0, '京宝梵应无驾驶员'
        assert chk['shin'] and chk['shin']['pilot'] == 1125000302, '新安州应为弗尔·伏朗特(1125000302)'
        assert chk['zaku'] is None, '移动4+1=5 不应出现在6移动'

        # ---------- 1. 特性页 UI ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow'); pg.wait_for_timeout(600)
        chips = pg.eval_on_selector_all('.chip[data-k]', "els => els.map(e => e.textContent.trim())")
        assert '6移动' in chips and '7移动' in chips, '特性页应有6移动/7移动分组'
        pg.click("[data-k='move6']"); pg.wait_for_timeout(1000)
        head = pg.evaluate("() => document.querySelector('#farea .subnote').textContent")
        print('[6移动]', head)
        assert '共 47 条' in head, '6移动应共47条'
        rows = pg.evaluate("""() => [...document.querySelectorAll('#farea .lrow')].map(el => ({
            name: el.querySelector('.nm').textContent.replace(/\\s+/g,' ').slice(0, 24),
            pip: !!el.querySelector('.picon'),
        }))""")
        tiger = [r for r in rows if '老虎特装型' in r['name']]
        kyo = [r for r in rows if '京宝梵' in r['name']]
        print('[老虎]', tiger, '[京宝梵]', kyo)
        assert tiger and tiger[0]['pip'], '老虎特装型行应显示驾驶员头像'
        assert kyo and not kyo[0]['pip'], '京宝梵行不应显示驾驶员头像'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/47a_move6.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
