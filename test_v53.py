# -*- coding: utf-8 -*-
"""v0.53 验证: 排行/组队 新增「驾驶员稀有度」筛选(与机体稀有度独立) ①排行按驾驶员稀有度过过滤且可复位
②组队作用于攻击型TOP10(支援/防御列不参与), DOM与同参数重算一致且驾驶员稀有度全匹配"""
import subprocess, time
from playwright.sync_api import sync_playwright

PORT = 8997
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

        # ---------- ① 排行: 驾驶员稀有度筛选 ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('.rrow', timeout=180000); pg.wait_for_timeout(800)
        ui = pg.evaluate("""() => ({ rar: [...document.querySelectorAll('[data-prar]')].map(e => e.textContent.trim()),
          unitRar: [...document.querySelectorAll('[data-rar]')].map(e => e.textContent.trim()) })""")
        print('[排行 两行]', ui)
        assert ui['rar'] == ['全部', 'N', 'R', 'SR', 'SSR', 'UR'] and ui['unitRar'] == ['全部', 'N', 'R', 'SR', 'SSR', 'UR'], f'应有驾驶员稀有度与机体稀有度两独立行: {ui}'
        n_all = pg.evaluate("() => state.rankCache.rows.length")
        pg.click('[data-prar="5"]')
        pg.wait_for_function("() => state.rankCfg.prar === 5 && (state.rankCache.rows || []).every(r => (q1('SELECT rarity FROM characters WHERE id=?', [r.pilot.id]) || {}).rarity === 5)", timeout=300000)
        pg.wait_for_timeout(400)
        chk = pg.evaluate("""() => ({ n: state.rankCache.rows.length,
          cfgPrar: state.rankCfg.prar, cfgRar: state.rankCfg.rarity,
          sample: state.rankCache.rows.slice(0, 5).map(r => r.pilot.name + '/' + (q1('SELECT rarity FROM characters WHERE id=?', [r.pilot.id])||{}).rarity) })""")
        print('[排行 驾驶员稀有度=UR]', chk)
        assert chk['cfgPrar'] == 5 and chk['cfgRar'] is None and chk['n'] > 0 and chk['n'] <= n_all, f'排行驾驶员稀有度筛选错误: {chk}'
        assert all(x.endswith('/5') for x in chk['sample']), f'行内驾驶员应全为UR: {chk["sample"]}'
        pg.click('[data-prar="all"]')
        pg.wait_for_function(f"() => state.rankCfg.prar === null && state.rankCache.rows.length === {n_all}", timeout=300000)
        print('[排行 复位] ok')

        # ---------- ② 组队: 驾驶员稀有度(仅攻击型TOP10) ----------
        pg.click('[data-tab="team"]'); pg.wait_for_timeout(3000)
        ui2 = pg.evaluate("""() => ({ rar: [...document.querySelectorAll('[data-tprar]')].map(e => e.textContent.trim()),
          unitRar: [...document.querySelectorAll('[data-trar]')].map(e => e.textContent.trim()) })""")
        print('[组队 两行]', ui2)
        assert ui2['rar'] == ['全部', 'N', 'R', 'SR', 'SSR', 'UR'] and ui2['unitRar'] == ['全部', 'N', 'R', 'SR', 'SSR', 'UR'], ui2
        # 先记录无筛时光攻TOP10首行
        top0 = pg.evaluate("() => (document.querySelectorAll('#tarea .card')[1].querySelector('.trow .nm') || {}).textContent || ''")
        pg.click('[data-tprar="5"]'); pg.wait_for_timeout(6000)
        chk2 = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#tarea .card')[1].querySelectorAll('.trow')];
          const domIds = rows.map(el => +el.dataset.id);
          const t = state.team; const f = filt('team');
          const G = buildRanking(f, { targetDef: (t.tdef ?? 10000), targetCharDef: (t.tcdef ?? 750), vigor: 'mid', crit: false, range: t.range, rarity: t.rar || null, urole: t.urole || null, wat: t.wat || null, atk: t.atk || null, pSpU: t.pSpU !== false },
            { passive: true, cpassive: true, skills: !!t.skills, condAll: !!t.ca, autoVigor: true, multiPhase: !!t.mp, star: t.star ?? 3, spU: t.spU !== false, sspU: t.sspU !== false, pilotRar: t.prar || null, pilotGroups: { main: t.prole || null, sup: 3, def: 2 } });
          const atk = G.main.filter(r => r.unit.role === 1).slice(0, 10);
          return { n: rows.length, domIds, expIds: atk.map(r => r.unitId),
            rars: atk.map(r => (q1('SELECT rarity FROM characters WHERE id=?', [r.pilot.id]) || {}).rarity),
            prar: state.team.prar };
        }""")
        print('[组队 驾驶员稀有度=UR]', {k: chk2[k] for k in ('n', 'prar', 'rars')})
        assert chk2['prar'] == 5 and chk2['n'] > 0, f'组队驾驶员稀有度未生效: {chk2}'
        assert all(x == 5 for x in chk2['rars']), f'攻击TOP10驾驶员应全为UR: {chk2["rars"]}'
        assert chk2['domIds'] == chk2['expIds'], '页面结果与同参数重算不一致(pilotRar未接入?)'
        top1 = pg.evaluate("() => (document.querySelectorAll('#tarea .card')[1].querySelector('.trow .nm') || {}).textContent || ''")
        print('[组队 首行变化]', top0[:24], '→', top1[:24])
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/59a_team_prar.png')
        pg.click('[data-tprar="all"]'); pg.wait_for_timeout(5000)
        chk3 = pg.evaluate("() => state.team.prar")
        print('[组队 复位]', chk3)
        assert chk3 is None, '复位失败'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
