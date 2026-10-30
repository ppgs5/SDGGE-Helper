# -*- coding: utf-8 -*-
"""v0.102 校对: 无限正义高达(EX)+阿斯兰 EX武器 vs MAP武器, 在「无防御/选择防御/支援防御」三种状态下的伤害
口径: 目标=高达(EX)+阿姆罗·雷, 首动开, 条件被动关
期望: MAP 三种状态伤害不变(无法防御); EX 武器随姿态下降
"""
import subprocess, time, sys
from playwright.sync_api import sync_playwright
PORT = 9080
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
UID, EX_W, MAP_W = 1330002850, 133000285007, 133000285006
res = {}
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(240000)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("window.Android={dbInfo:()=>'{}',listPatches:()=>'[]'};")
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(1500)
        for lab, guard, sdef in (('无防御', False, False), ('选择防御', True, False), ('支援防御', False, True)):
            pg.evaluate("""(a) => { const t = state.team;
                const du = q1("SELECT id FROM units WHERE name='高达 (EX)'");
                const dc = q1("SELECT id FROM characters WHERE name LIKE '阿姆罗·雷%' LIMIT 1");
                const cid = q1("SELECT id FROM characters WHERE name LIKE '阿斯兰·萨拉%' LIMIT 1");
                t.dunit = du.id; t.dchar = dc ? dc.id : null; t.guard = a.g; t.sdef = a.s;
                t.first = true; t.ca = false; t.skills = false;
                state.teamCache = null;
                state.stack = []; setTab('calc'); state.calc.unitId = a.u; state.calc.charId = cid.id; render();
            }""", {'g': guard, 's': sdef, 'u': UID})
            pg.wait_for_timeout(11000)
            res[lab] = pg.evaluate("""(a) => { const s = state._calcSnap;
                const f = id => { const r = s && s.rows ? s.rows.find(x => x.wid === id) : null; return r ? r.dmg : null; };
                return {exW: f(a.ex), mapW: f(a.map), defReduce: s ? s.defReduce : null}; }""",
                {'ex': EX_W, 'map': MAP_W})
        print(f'{"状态":<8}{"EX武器(命运-00 EX)":>18}{"MAP(命运-01)":>14}{"页面减伤":>10}')
        for lab, v in res.items():
            print(f'{lab:<8}{v["exW"] if v["exW"] else "—":>18}{v["mapW"] if v["mapW"] else "—":>14}{str(round(v["defReduce"]))+"%":>10}')
        assert not errs, errs[:2]
        ex = [res[k]['exW'] for k in ('无防御', '选择防御', '支援防御')]
        mp = [res[k]['mapW'] for k in ('无防御', '选择防御', '支援防御')]
        assert all(v is not None for v in ex + mp), (ex, mp)
        ok_map = len(set(mp)) == 1
        ok_ex = ex[0] > ex[1] and ex[0] > ex[2]
        print(f'MAP 三种状态一致: {ok_map} {mp}')
        print(f'EX 武器无防御时最高: {ok_ex} {ex}')
        assert ok_map and ok_ex
        print('=== test_v102 通过 ===')
        b.close()
finally:
    srv.terminate()
