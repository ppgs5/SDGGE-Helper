# -*- coding: utf-8 -*-
"""v0.34 验证: EX赋予按条件生效(非EX的00R也吃) — 仅HP恢复/特定被动(unit_ids)限指定机体"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8957
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
          const opts = { cpassive: true, upassive: true, multiPhase: true, condAll: true, vigor: 'supercharged' };
          const gt = (uid, cid) => grantedTraits(uid, cid, metaOf(uid), opts).length;
          const gate23 = (uid, cid) => (charPassives()[cid] || []).filter(x => (x.reqUnits || []).length && condOk(x, metaOf(uid), { condAll: true, vigor: 'mid' })).length;
          return {
            sf: gt(1370005900, 1370003701),        // 非EX 00R(高达+00系列) → 生效
            sfEX: gt(1370005950, 1370003701),
            unicorn: gt(1125000100, 1370003701),   // 独角兽(系列不符) → 不生效
            mpUnicorn: mpOf(1125000100, 1370003701, false, true),
            mpShinnWrong: mpOf(1370005900, 1330000103, false, true),   // 真飞鸟MP+2 仍限命运EX
            g23wrong: gate23(1200003950, 1219000501),                  // 双头龙格斗+15% 仍限机体
            g23right: gate23(1219000650, 1219000501),
          };
        }""")
        print('[数据]', chk)
        assert chk['sf'] >= 4 and chk['sfEX'] >= 4, '刹那EX赋予应对00系列高达生效(非EX也可)'
        assert chk['unicorn'] == 0 and chk['mpUnicorn'] == 0, '系列不符的机体不应生效'
        assert chk['mpShinnWrong'] == 2, '真飞鸟MP+2为官方bug豁免: 对所有机体生效'
        assert chk['g23right'] == 1 and chk['g23wrong'] == 0, '双头龙专属被动仍应限机体'

        # ---------- 1. 计算页: 非EX 00R + 刹那 → 多阶段增益生效 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '00强化模组'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pick='1370005900']"); pg.wait_for_timeout(800)
        pg.click('#picku'); pg.wait_for_timeout(300); pg.click('#wchar'); pg.wait_for_timeout(400)
        pg.fill('#pk', '刹那'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pickc='1370003701']"); pg.wait_for_timeout(900)
        pg.click('[data-vg="supercharged"]'); pg.wait_for_timeout(1800)
        d1 = pg.evaluate("() => { const e = document.getElementById('detail'); return e ? e.textContent.replace(/\\s+/g,' ') : '' }")
        print('[非EX 00R 明细尾]', d1[-90:])
        assert '多阶段增益(EX2) 赋予: 格斗值+50%' in d1, '非EX的00R应有多阶段增益赋予'

        # ---------- 2. 独角兽 + 刹那 → 无赋予 ----------
        pg.click('#picku'); pg.wait_for_timeout(300)
        pg.fill('#pk', '独角兽高达'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pick='1125000100']"); pg.wait_for_timeout(900)
        pg.click('[data-vg="supercharged"]'); pg.wait_for_timeout(1800)
        d2 = pg.evaluate("() => { const e = document.getElementById('detail'); return e ? e.textContent.replace(/\\s+/g,' ') : '' }")
        print('[独角兽 明细尾]', d2[-90:])
        assert '多阶段增益' not in d2, '系列不符的机体不应有多阶段增益'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/46a_grant_by_series.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
