# -*- coding: utf-8 -*-
"""v0.29 验证: SSP核心「最大值提升3%」应用到武装POWER效果 + SSP加成floor口径对齐soshage排行"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8919
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

        # ---------- 0. 数据层: 威力效果+3 与 soshage 排行对齐 ----------
        chk = pg.evaluate("""() => {
          const W = id => q1('SELECT * FROM weapons WHERE id=?', [id]);
          const T = id => q('SELECT * FROM weapon_traits WHERE weapon_id=? AND level=5', [id]);
          const eff = id => Engine.damageWithWeapon(10000, 1000, W(id), T(id), 5, 10000, 750, { vigor: 'mid' }).effPower;
          return {
            jj: eff(137000590090),                               // 强化巨剑SSP: 6300×1.15 → 7244(浮点截断)
            jjPct: Engine.powerBoostPct(T(137000590090), 5),     // 12+3 = 15
            s360: eff(100700116090),                             // 360mm加农炮SSP: 6120×(12+3+3) → 7221
            s360Pct: Engine.powerBoostPct(T(100700116090), 5),   // 18
            nt: eff(185000140090),                               // 线控式大型浮游炮SSP: 6060×1.15 → 6968
            kb: eff(108000386090),                               // 扩散米加粒子炮SSP: 6060×1.15 → 6968
            dt: eff(113300030103),                               // 超级米加粒子炮(德尔塔改,非SSP): 5520×1.17 → 6458, 不得+3
            dtPct: Engine.powerBoostPct(T(113300030103), 5),     // 17
            gain: sspGainOf(q1('SELECT * FROM units WHERE id=1370005900'), 10).atk,   // floor口径 → 288
          };
        }""")
        print('[数据]', chk)
        assert chk['jj'] == 7244, f'强化巨剑SSP威力应为7244(网站一致): {chk["jj"]}'
        assert chk['jjPct'] == 15, '强化巨剑SSP效果应为15%(12+3)'
        assert chk['s360'] == 7221 and chk['s360Pct'] == 18, f'360mm加农炮SSP应为7221(12+3+3): {chk["s360"]}/{chk["s360Pct"]}'
        assert chk['nt'] == 6968, f'线控式大型浮游炮SSP威力应为6968(网站一致): {chk["nt"]}'
        assert chk['kb'] == 6968, f'扩散米加粒子炮SSP威力应为6968(网站一致): {chk["kb"]}'
        assert chk['dt'] == 6458 and chk['dtPct'] == 17, f'非SSP超级米加粒子炮应保持17%不加3: {chk["dt"]}/{chk["dtPct"]}'
        assert chk['gain'] == 288, f'SSP满10攻击加成应为288(floor与网站一致): {chk["gain"]}'

        # ---------- 1. 计算页: 00R+被动攻击 = 13503(网站一致) ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '00强化模组'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pick='1370005900']"); pg.wait_for_timeout(800)
        pg.click('[data-vg="max"]'); pg.wait_for_timeout(1200)
        pg.click('#ssp'); pg.wait_for_timeout(1600)   # 开SSP满10
        small = pg.evaluate("() => document.querySelector('#picku small').textContent.replace(/\\s+/g,' ')")
        print('[计算页攻击]', small[:70])
        exp = pg.evaluate("() => { const u = q1('SELECT * FROM units WHERE id=1370005900'); const g = sspGainOf(u, 10); return Math.floor(Math.floor((u.sp_max_atk + g.atk) * 1.4) * 1.2); }")
        print('[期望]', exp)
        assert '13,503' in small and exp == 13503, f'SSP满10攻击应为13,503: {small[:50]}'

        # ---------- 2. 排行页: 强化巨剑SSP 行威力 7,244 效果+15% ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('#rlist .rrow'); pg.wait_for_timeout(5000)
        row = pg.evaluate("""() => { const e = [...document.querySelectorAll('#rlist .rrow')].find(x => x.textContent.includes('强化巨剑 SSP')); return e ? e.textContent.replace(/\\s+/g,' ') : '' }""")
        print('[排行行]', row[:190])
        assert '7,244' in row and '效果+15%' in row, '排行应显示 威力7,244 效果+15%'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/41a_rank_ssp3.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
