# -*- coding: utf-8 -*-
"""v0.16 验证: 驾驶员类型筛选(排行/组队) + 攻击型×支援型/防御型输出分区"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8852
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

        # 组队: 多口径分区
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow')
        out = pg.evaluate("""() => {
          const c = {targetDef:10000, targetCharDef:750, vigor:'mid', crit:false, range:'all'};
          const G = buildRanking(filt('team'), c, {passive:true,cpassive:true,skills:false,condAll:true,autoVigor:true,multiPhase:true,pilotGroups:{main:null, sup:3, def:2}});
          const roleOf = id => q1('SELECT role FROM characters WHERE id=?',[id]).role;
          const atk = G.main.filter(r=>r.unit.role===1).slice(0,10);
          const atkSup = G.sup.filter(r=>r.unit.role===1).slice(0,10);
          const sup3 = G.sup.filter(r=>r.unit.role===3).slice(0,5);
          const defOut = G.def.filter(r=>r.unit.role===2).slice(0,5);
          return {
            atkAll1: atk.every(r=>r.unit.role===1),
            atkSupOk: atkSup.every(r=>r.unit.role===1 && roleOf(r.pilot.id)===3), atkSupN: atkSup.length, atkSupTop: atkSup[0] && (atkSup[0].unit.name+' + '+atkSup[0].pilot.name+' '+atkSup[0].dmg),
            supOk: sup3.every(r=>r.unit.role===3 && roleOf(r.pilot.id)===3), supN: sup3.length, supTop: sup3[0] && (sup3[0].unit.name+' + '+sup3[0].pilot.name+' '+sup3[0].dmg),
            defOk: defOut.every(r=>r.unit.role===2 && roleOf(r.pilot.id)===2), defN: defOut.length, defTop: defOut[0] && (defOut[0].unit.name+' + '+defOut[0].pilot.name+' '+defOut[0].dmg),
          };
        }""")
        print('[team groups]', json.dumps(out, ensure_ascii=False))
        assert out['atkAll1'] and out['atkSupOk'] and out['atkSupN']==10 and out['supOk'] and out['supN']==5 and out['defOk'] and out['defN']==5, '分区类型约束错误'
        titles = pg.eval_on_selector_all('#tarea h4', "els => els.map(e => e.textContent)")
        print('[titles]', titles)
        assert len(titles) == 5 and '支援型驾驶员' in titles[1] and '仅支援型' in titles[2] and '仅防御型' in titles[3], '分区标题不符'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/26a_team_roles.png')

        # 组队主口径: 仅防御型驾驶员
        pg.click("[data-prole='2']"); pg.wait_for_timeout(2500)
        first = pg.eval_on_selector('#tarea .trow .nm small', 'e => e.textContent.replace(/\\s+/g," ").trim()')
        role = pg.evaluate("""() => {
          const c = {targetDef:10000, targetCharDef:750, vigor:'mid', crit:false, range:'all'};
          const rows = buildRanking(filt('team'), c, {passive:true,cpassive:true,skills:false,condAll:true,autoVigor:true,multiPhase:true,pilotRole:2});
          const atk = rows.filter(r=>r.unit.role===1);
          return {ok: atk.every(r => q1('SELECT role FROM characters WHERE id=?',[r.pilot.id]).role===2), n: atk.length};
        }""")
        print('[team only-def]', first, role)
        assert role['ok'], '仅防御型驾驶员过滤错误'

        # 排行: 驾驶员类型 chips
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('#rlist .rrow')
        chips = pg.eval_on_selector_all('[data-prole]', "els => els.map(e => e.textContent.trim() + (e.classList.contains('gold') ? '*' : ''))")
        print('[rank prole chips]', chips)
        assert '全部*' in chips, '排行驾驶员类型默认应为全部'
        pg.click("[data-prole='3']"); pg.wait_for_timeout(4000)
        rr = pg.evaluate("""() => {
          const c = state.rankCfg;
          const rows = buildRanking(filt('rank'), c, {passive:c.passive,cpassive:c.cpassive,skills:c.skills,condAll:!!c.ca,autoVigor:c.vigor==='default',multiPhase:!!c.mp,star:c.star,pilotRole:c.prole});
          const bad = rows.filter(r => q1('SELECT role FROM characters WHERE id=?',[r.pilot.id]).role !== 3);
          return {n: rows.length, badN: bad.length, top: rows.slice(0,3).map(r => r.unit.name + ' + ' + r.pilot.name + ' ' + r.dmg)};
        }""")
        print('[rank only-sup]', json.dumps(rr, ensure_ascii=False))
        assert rr['badN'] == 0, '排行仅支援型过滤错误'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/26b_rank_sup.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
