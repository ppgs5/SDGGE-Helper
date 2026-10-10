# -*- coding: utf-8 -*-
"""v0.35 验证: 真飞鸟EX技能「搭乘命运高达(EX)时」为官方确认bug — 机体限制不生效(对所有机体生效)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8959
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

        chk = pg.evaluate("""() => {
          const opts = { cpassive: true, upassive: true, multiPhase: true, condAll: true, vigor: 'supercharged' };
          const gt = (uid, cid) => grantedTraits(uid, cid, metaOf(uid), opts).length;
          const gate23 = (uid, cid) => (charPassives()[cid] || []).filter(x => (x.reqUnits || []).length && condOk(x, metaOf(uid), { condAll: true, vigor: 'mid' })).length;
          return {
            shinn00R: mpOf(1370005900, 1330000103, false, true),       // 官方bug: 00R上也生效 +2
            shinnUnicorn: mpOf(1125000100, 1330000103, false, true),   // 独角兽 +2
            shinnGod: mpOf(1200003950, 1330000103, false, true),       // 神高达 +2
            shinnDestiny: mpOf(1330000750, 1330000103, false, true),   // 命运(EX) +2
            shinnGrant: gt(1200003950, 1330000103),                    // 赋予(数据无条件)仍任意机体生效
            bing00R: mpOf(1370005900, 1370003701, false, true),        // 刹那只限00系列: 00R +5
            bingUnicorn: mpOf(1125000100, 1370003701, false, true),    // 独角兽 0
            g23wrong: gate23(1200003950, 1219000501),                  // 双头龙限制仍有效
            g23right: gate23(1219000650, 1219000501),
            sfUnicorn: gt(1125000100, 1370003701),                     // 刹那赋予仍限系列
          };
        }""")
        print('[数据]', chk)
        assert chk['shinn00R'] == 2 and chk['shinnUnicorn'] == 2 and chk['shinnGod'] == 2 and chk['shinnDestiny'] == 2, \
            '真飞鸟MP+2应对所有机体生效(官方bug豁免)'
        assert chk['shinnGrant'] >= 4, '真飞鸟EX赋予仍生效'
        assert chk['bing00R'] == 5 and chk['bingUnicorn'] == 0 and chk['sfUnicorn'] == 0, '刹那的条件仍按标签+系列判定'
        assert chk['g23right'] == 1 and chk['g23wrong'] == 0, '普通unit_ids限制(双头龙)仍应生效'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
