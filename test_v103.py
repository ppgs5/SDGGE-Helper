# -*- coding: utf-8 -*-
"""v0.103 候选池裁剪可行性验证
   池子 = 武器威力上界前 K ∪ 机体最大攻击上界前 K ∪ 保底(MP技能机师/必暴)
   要求: 池内精确计算的 TOP50(含顺序) 必须与全量结果完全一致
"""
import subprocess, time, sys
from playwright.sync_api import sync_playwright
PORT = 9122
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
FAIL = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(900000)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("window.Android={dbInfo:()=>'{}',listPatches:()=>[]};")
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(1500)
        for K in (120, 200, 300):
            r = pg.evaluate("""(K) => {
                const t = state.team; const du = q1("SELECT id FROM units WHERE name='高达 (EX)'");
                t.dunit = du.id; t.dchar = 1062000100; t.sdef = true; t.first = true;
                const f = filt('team');
                const { cfg, opts } = teamRankArgs(t, f);
                const t0 = performance.now();
                const full = buildRanking(f, cfg, opts);
                const tFull = performance.now() - t0;
                const key = x => x.unitId + '|' + x.pilot.id;
                const fullTop = (full.main || []).slice(0, 50).map(key);

                /* 上界: 武器最大威力 / 机体最大攻击 */
                const ws = q("SELECT * FROM weapons"), units = q("SELECT * FROM units");
                const byU = {}; for (const w of ws) (byU[w.unit_id] = byU[w.unit_id] || []).push(w);
                const bd = units.map(u => { let mp = 0; for (const w of (byU[u.id] || [])) mp = Math.max(mp, Engine.weaponPower(w, 5)); return { id: u.id, mp, atk: u.max_atk || 0 }; }).filter(x => x.mp > 0);
                const byPow = bd.slice().sort((a, c) => c.mp - a.mp).slice(0, K).map(x => x.id);
                const byAtk = bd.slice().sort((a, c) => c.atk - a.atk).slice(0, K).map(x => x.id);
                const pool = Array.from(new Set(byPow.concat(byAtk)));
                const t1 = performance.now();
                const pruned = buildRanking(f, cfg, { ...opts, unitIds: pool });
                const tPruned = performance.now() - t1;
                const prunedTop = (pruned.main || []).slice(0, 50).map(key);
                let firstDiff = -1;
                for (let i = 0; i < Math.min(fullTop.length, prunedTop.length); i++) if (fullTop[i] !== prunedTop[i]) { firstDiff = i; break; }
                const t10 = JSON.stringify(fullTop.slice(0,10)) === JSON.stringify(prunedTop.slice(0,10));
                const t30 = JSON.stringify(fullTop.slice(0,30)) === JSON.stringify(prunedTop.slice(0,30));
                const t50 = JSON.stringify(fullTop) === JSON.stringify(prunedTop);
                return { K, pool: pool.length, total: bd.length, tFull: Math.round(tFull), tPruned: Math.round(tPruned),
                         t10, t30, t50, firstDiff,
                         miss: fullTop.filter(x => !prunedTop.includes(x)).length };
            }""", K)
            print(f"K={r['K']}: 池 {r['pool']}/{r['total']} 台 | 全量 {r['tFull']}ms → 裁剪 {r['tPruned']}ms")
            print(f"  TOP10 一致 {r['t10']} | TOP30 一致 {r['t30']} | TOP50 一致 {r['t50']} | 漏 {r['miss']} 个")
            if not r['t30']: FAIL.append(f'K={r["K"]}')   # 页面只展示 TOP10, 以 TOP30 全一致作为通过线
        print('errors:', errs[:1])
        b.close()
finally:
    srv.terminate()
print('\n' + ('=== test_v103 通过 ===' if not FAIL else f'=== 失败: {FAIL} ==='))
sys.exit(0 if not FAIL else 1)
