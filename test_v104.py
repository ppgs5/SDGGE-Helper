# -*- coding: utf-8 -*-
"""v0.104 计算页三处口径一致性: 武器列表 == 公式明细 == 驾驶员TOP
   断言: 选中某机师后, 该机师在 TOP 里的伤害/机师攻击值 必须与武器表最优行、公式明细的最终值完全相等
"""
import subprocess, time, sys
from playwright.sync_api import sync_playwright
PORT = 9150
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
FAIL = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(600000)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("window.Android={dbInfo:()=>'{}',listPatches:()=>[]};")
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(1500)
        cases = [
            ("无限正义高达 (EX)", "阿斯兰·萨拉", 5),
            ("达利尔巴尔德(Season2规格)", "盖尔·杰特克", 5),
        ]
        for uq, cq, rar in cases:
            r = pg.evaluate("""(a) => {
                const u = q1("SELECT id FROM units WHERE name LIKE ? LIMIT 1", [a.uq + '%']);
                const c = q1("SELECT id,rarity FROM characters WHERE name LIKE ? AND rarity>=? LIMIT 1", [a.cq + '%', a.rar]);
                if (!u || !c) return { skip: true };
                state.stack = []; setTab('calc'); state.calc.unitId = u.id; state.calc.charId = c.id; render();
                return { cid: c.id };
            }""", {'uq': uq, 'cq': cq, 'rar': rar})
            if r.get('skip'):
                print(f'  跳过(未找到): {uq} + {cq}'); continue
            pg.wait_for_timeout(12000)
            out = pg.evaluate("""(cid) => {
                const s = state._calcSnap; if (!s) return null;
                const best = s.rows.reduce((a, b2) => (b2.dmg > a.dmg ? b2 : a));
                const pr = (state._prRows || []).find(x => x.id === cid);
                const d = document.getElementById('detail');
                const m = (d ? d.innerText : '').match(/最终\\s*([\\d,]+)/);
                return { tableDmg: best.dmg, tableW: best.w, detail: m ? +m[1].replace(/,/g, '') : null,
                         topDmg: pr ? pr.dmg : null, topW: pr ? pr.weapon.name : null, topPilot: pr ? pr.name : null };
            }""", r['cid'])
            ok = out and out['topDmg'] == out['tableDmg'] and (out['detail'] is None or out['detail'] == out['tableDmg'])
            print(f"  {uq} + {cq}: 表 {out['tableDmg']:,} / 明细 {out['detail']} / TOP {out['topDmg']:,} → {'一致' if ok else '不一致'}")
            if not ok: FAIL.append(f'{uq}+{cq}')
        print('errors:', errs[:1])
        b.close()
finally:
    srv.terminate()
print('\n' + ('=== test_v104 通过 ===' if not FAIL else f'=== 失败: {FAIL} ==='))
sys.exit(0 if not FAIL else 1)
