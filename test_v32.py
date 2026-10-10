# -*- coding: utf-8 -*-
"""v0.33 验证: 驾驶员技能条件判定 — 特定机体(unit_ids)限制 + 「标签及系列」两者都要满足(EX赋予按机体限制)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8953
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
            sf: gt(1370005900, 1370003701), sfEX: gt(1370005950, 1370003701),
            unicorn: gt(1125000100, 1370003701), shinnWrong: gt(1370005900, 1330000103), shinnOwn: gt(1330000750, 1330000103),
            mpBing: mpOf(1370005900, 1370003701, false, true), mpUnicorn: mpOf(1125000100, 1370003701, false, true),
            mpShinnWrong: mpOf(1370005900, 1330000103, false, true), mpShinnOwn: mpOf(1330000750, 1330000103, false, true),
            g23right: gate23(1219000650, 1219000501), g23wrong: gate23(1200003950, 1219000501),
          };
        }""")
        print('[数据]', chk)
        assert chk['sf'] >= 4 and chk['sfEX'] >= 4, '刹那EX赋予应对高达标签+00系列机体生效(含非EX的00R)'
        assert chk['unicorn'] == 0, '刹那EX赋予不应对独角兽生效(系列不符)'
        assert chk['shinnOwn'] >= 4, '真飞鸟EX赋予对其条件机体生效'
        assert chk['mpBing'] == 5 and chk['mpUnicorn'] == 0, '变革者MP+5应仅限00系列(标签及系列)'
        assert chk['mpShinnWrong'] == 2 and chk['mpShinnOwn'] == 2, '真飞鸟MP+2为官方bug豁免: 对所有机体生效'
        assert chk['g23right'] == 1 and chk['g23wrong'] == 0, '双头龙专属格斗+15%应限对应机体'

        # ---------- 1. 计算页: 非EX 00R + 刹那 → 多阶段增益生效(00系列高达) ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '00强化模组'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pick='1370005900']"); pg.wait_for_timeout(800)
        pg.click('#picku'); pg.wait_for_timeout(300); pg.click('#wchar'); pg.wait_for_timeout(400)
        pg.fill('#pk', '刹那'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pickc='1370003701']"); pg.wait_for_timeout(900)
        pg.click('[data-vg="supercharged"]'); pg.wait_for_timeout(1800)
        d1 = pg.evaluate("() => { const e = document.getElementById('detail'); return e ? e.textContent.replace(/\\s+/g,' ') : '' }")
        print('[非EX 明细]', d1[-120:])
        assert '多阶段增益' in d1 and '格斗值+50%' in d1, '非EX的00R(00系列+高达)应有EX赋予'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/45a_mp_grant_nonEX.png')

        # ---------- 2. 切到 EX 版 → 多阶段增益生效 ----------
        pg.click('#picku'); pg.wait_for_timeout(300)
        pg.fill('#pk', '00强化模组'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pick='1370005950']"); pg.wait_for_timeout(900)
        pg.click('[data-vg="supercharged"]'); pg.wait_for_timeout(1800)
        d2 = pg.evaluate("() => { const e = document.getElementById('detail'); return e ? e.textContent.replace(/\\s+/g,' ') : '' }")
        print('[EX 明细]', d2[:200])
        assert '多阶段增益' in d2 and '格斗值+50%' in d2, 'EX版00R应有多阶段增益(EX2)赋予'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/45b_mp_grant.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
