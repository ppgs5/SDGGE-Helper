# -*- coding: utf-8 -*-
"""v0.15 验证: 排行取全驾驶员最优 / 武士道被动MP(trait43) / 性能"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8848
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 400, 'height': 860})
        pg.set_default_timeout(300000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append('console.' + m.type + ': ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        print('[boot] ok')

        # 排行全量计算计时 + 须佐之男最优驾驶员
        out = pg.evaluate("""() => {
          const c = state.rankCfg;
          const t0 = performance.now();
          const rows = buildRanking(filt('rank'), c, {passive:c.passive, cpassive:c.cpassive, skills:c.skills, condAll:!!c.ca, autoVigor:c.vigor==='default', multiPhase:!!c.mp, star:c.star});
          const ms = performance.now() - t0;
          const s = rows.find(r => r.unitId === 1370010150);
          return {ms: Math.round(ms), rows: rows.length,
                  sus: s ? {pilot: s.pilot.name, dmg: s.dmg, mp: s.mp, vigor: s.vigor, weapon: s.weapon.name} : null,
                  top3: rows.slice(0,3).map(r => r.unit.name + '|' + r.pilot.name + '|' + r.dmg)};
        }""")
        print('[rank full-scan]', json.dumps(out, ensure_ascii=False))
        assert out['sus'] and out['sus']['pilot'] == 'Mr.武士道', '须佐之男应选用最高伤害驾驶员(武士道: 被动MP6+技能MP6=12)'
        assert out['sus']['mp'] == 12, '武士道MP应为12'

        # 计算页同值
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '须佐之男'); pg.wait_for_timeout(500)
        pg.click("#pkl [data-pick='1370010150']"); pg.wait_for_timeout(1200)
        rows2 = pg.eval_on_selector_all('[data-pid]', "els => els.slice(0,3).map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        print('[calc top3]', json.dumps(rows2, ensure_ascii=False))
        assert '武士道' in rows2[0], '计算页TOP1应为 Mr.武士道(与排行一致)'
        assert f"{out['sus']['dmg']:,}" in rows2[0], '计算页与排行数值应一致'
        # 武士道: 被动MP(43)+技能MP, 应达超一击(12)
        wsb = next(r for r in rows2 if '武士道' in r)
        print('[武士道]', wsb)
        assert '超一击(12)' in wsb.replace(' ', ''), '武士道应 被动6+技能6=MP12 超一击'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/24a_susanoo.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
