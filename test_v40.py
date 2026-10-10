# -*- coding: utf-8 -*-
"""v0.41/42 验证: 战意/HP条件移动力提升 — 条件行显示条件(机体被动(战意为「超一击」以上)); SSP移动+1仅status_up机体(阿利宙斯/京宝梵无)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8976
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

        # ---------- 0. 数据层: 条件移动行(SSP修正后) ----------
        chk = pg.evaluate("""() => {
          const get = (tid, feat) => {
            const r = q1('SELECT label, params_json FROM features WHERE feature=? AND target_id=?', [feat, tid]);
            return r ? Object.assign({label: r.label}, JSON.parse(r.params_json)) : null;
          };
          const cnt = sql => q(sql, [])[0].c;
          return {
            n6: cnt("SELECT COUNT(*) c FROM features WHERE feature='move6'"),
            n7: cnt("SELECT COUNT(*) c FROM features WHERE feature='move7'"),
            zen6: cnt("SELECT COUNT(*) c FROM features WHERE feature='move6' AND params_json LIKE '%战意%'"),
            zen7: cnt("SELECT COUNT(*) c FROM features WHERE feature='move7' AND params_json LIKE '%战意%'"),
            hp6: cnt("SELECT COUNT(*) c FROM features WHERE feature='move6' AND params_json LIKE '%HP75%'"),
            alex6: get(1150001360, 'move6'),    // 阿利宙斯: 5+战意超一击=6 (SSP无移动)
            alex7: get(1150001360, 'move7'),
            kyo6: get(1017000900, 'move6'),     // 京宝梵: 同上
            kyo7: get(1017000900, 'move7'),
            v2: get(1175001900, 'move6'),       // V2高达: 战意超强势
            f80: get(1154000100, 'move6'),      // F80: base4+HP75%+SSP=6
            xi: get(1150000150, 'move6'),       // Ξ高达EX: 5+战意超一击=6 (无SSP)
            konoe6: get(1175004910, 'move6'),   // 里格·夏柯: SSP+1 → 6
            konoe7: get(1175004910, 'move7'),   // +卡特吉娜 → 7
          };
        }""")
        print('[数据]', {k: v for k, v in chk.items()})
        assert chk['n6'] == 270 and chk['n7'] == 13, f"计数: {chk['n6']}/{chk['n7']}"
        assert chk['zen6'] == 15 and chk['zen7'] == 0 and chk['hp6'] == 2, f"条件行数: {chk['zen6']}/{chk['zen7']}/{chk['hp6']}"
        a6 = chk['alex6']
        assert a6 and a6['total'] == 6 and a6['pilot'] == 0 and '战意为「超一击」以上' in a6['desc'] and 'SSP' not in a6['desc'], f'阿利宙斯6移动=战意条件(无SSP): {a6}'
        assert chk['alex7'] is None, '阿利宙斯不应出现在7移动(SSP无移动加成)'
        assert '战意为「超一击」以上' in chk['kyo6']['desc'] and 'SSP' not in chk['kyo6']['desc'] and chk['kyo7'] is None, '京宝梵同阿利宙斯'
        assert '战意为「超强势」以上' in chk['v2']['desc'], 'V2高达应显示超强势条件'
        assert 'HP75%以上' in chk['f80']['desc'] and 'SSP强化' in chk['f80']['desc'] and chk['f80']['total'] == 6, 'F80应显示HP75%+SSP'
        assert '战意为「超一击」以上' in chk['xi']['desc'] and 'SSP' not in chk['xi']['desc'] and chk['xi']['total'] == 6, 'Ξ高达EX 6移动应显示战意条件'
        assert 'SSP' in chk['konoe6']['desc'] and chk['konoe6']['total'] == 6 and chk['konoe7']['pilot'] == 1175000500, '里格·夏柯 SSP6 + 卡特吉娜7'

        # ---------- 1. UI: 特性页 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow'); pg.wait_for_timeout(600)
        pg.click("[data-k='move7']"); pg.wait_for_timeout(1200)
        head = pg.evaluate("() => document.querySelector('#farea .subnote').textContent")
        rows7 = pg.evaluate("""() => [...document.querySelectorAll('#farea .lrow')].map(el => el.querySelector('.nm').textContent.replace(/\\s+/g,' '))""")
        print('[7移动]', head, '| 阿利宙斯在列:', any('阿利宙斯' in x for x in rows7))
        assert '共 13 条' in head, '7移动应共13条'
        assert not any('阿利宙斯' in x for x in rows7), '阿利宙斯不应在7移动列表'
        pg.click("[data-k='move6']"); pg.wait_for_timeout(1500)
        head6 = pg.evaluate("() => document.querySelector('#farea .subnote').textContent")
        rows6 = pg.evaluate("""() => [...document.querySelectorAll('#farea .lrow')].map(el => el.querySelector('.nm').textContent.replace(/\\s+/g,' ')).filter(t => t.includes('阿利宙斯'))""")
        print('[6移动]', head6, '|', rows6)
        assert '共 270 条' in head6, '6移动应共270条'
        assert rows6 and '移动5→6' in rows6[0] and '战意为「超一击」以上' in rows6[0], f'阿利宙斯6移动行应含条件: {rows6}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/51a_move6_cond.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
