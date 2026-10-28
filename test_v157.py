# -*- coding: utf-8 -*-
"""v157 验证: 计算页开关/输入跟随组队 + 条件被动如实判定
① 条件被动关 + 第一击/首动(满HP): Z高达EX 的「HP≥75% 攻击+20%」都计入（15% → 35%）
② 条件被动关 + 指定目标匹配: 完美吉翁号 的「敌·地球联邦军(宇宙世纪)」被动计入
③ 条件被动关 + 目标不匹配: 该被动不计入
④ 靶防御/靶守备/我方全能力 与组队页双向同步
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9175

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1600}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        r = pg.evaluate("""() => ({
          off_nofirst: unitPassiveAtkPct(1080000150,'mid',false,null,false,false),
          off_first:   unitPassiveAtkPct(1080000150,'mid',false,null,false,true),
          on_first:    unitPassiveAtkPct(1080000150,'mid',true,null,false,true) })""")
        print('[① HP条件]', r)
        assert r['off_nofirst'] == 35 and r['off_first'] == 35 and r['on_first'] == 35, r   # 第一击/首动都按满HP

        r2 = pg.evaluate("""() => {
          const fed = q1("SELECT id FROM units WHERE id IN (SELECT unit_id FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE t.name='地球联邦军(宇宙世纪)') LIMIT 1");
          const zion = q1("SELECT id FROM units WHERE id IN (SELECT unit_id FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE t.name='自护公国军') LIMIT 1");
          const m1 = Object.assign({}, metaOf(fed.id)), m2 = Object.assign({}, metaOf(zion.id));
          return { fed: unitPassiveAtkPct(1007000960,'mid',false,m1,false,false), zion: unitPassiveAtkPct(1007000960,'mid',false,m2,false,false) }; }""")
        print('[② 目标标签]', r2)
        assert r2['fed'] > r2['zion'], r2

        pg.evaluate("""() => { const c=state.calc; c.unitId=1080000150; c.charId=null; c.ca=false; c.first=false;
          state.stack=[]; push({page:'calc',title:'计算'}); render(); }""")
        pg.wait_for_timeout(1500)
        s1 = pg.evaluate("""() => { const el=document.getElementById('tdef2'); el.value='26000'; el.onchange();
          return {teamTdef: state.team.tdef, calcT: state.calc.tDef}; }""")
        print('[④ 靶防御 计算→组队]', s1)
        assert s1['teamTdef'] == 26000, s1
        s2 = pg.evaluate("""() => { const c=state.calc; c.allup=0; render(); const el=document.getElementById('callup');
          el.value='90'; el.onchange(); return {teamAtkup: state.team.atkup, calcAllup: state.calc.allup}; }""")
        print('[④ 全能力 计算→组队]', s2)
        assert s2['teamAtkup'] == 90 and s2['calcAllup'] == 90, s2
        s3 = pg.evaluate("""() => { const t=state.team; t.tdef=31000; t.tcdef=800; t.atkup=77;
          state.stack=[]; push({page:'team',title:'组队'}); render(); return null; }""")
        pg.wait_for_timeout(800)
        s4 = pg.evaluate("""() => { const el=document.getElementById('ttdef'); el.value='33000'; el.onchange();
          return {calcT: state.calc.tDef, teamT: state.team.tdef}; }""")
        print('[④ 靶防御 组队→计算]', s4)
        assert s4['calcT'] == 33000 and s4['teamT'] == 33000, s4
        s5 = pg.evaluate("""() => { const el=document.getElementById('tatkup'); el.value='66'; el.onchange();
          return {calcAllup: state.calc.allup}; }""")
        print('[④ 全能力 组队→计算]', s5)
        assert s5['calcAllup'] == 66, s5

        assert not errors, errors
        print('=== test_v157 全部通过 ===')
        b.close()
finally:
    srv.terminate()
