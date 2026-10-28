# -*- coding: utf-8 -*-
"""v158 验证: 目标各项设置同步到计算 + 距离按最大效果计算
① 距离条件（攻击距离1格内攻击+20%）在条件被动关时按最大效果计入
② 目标「全能力+30%」使计算页伤害下降，与组队共享
③ 目标「选择防御」使伤害进一步下降（-40%），与组队共享开关
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9179

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1600}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        r = pg.evaluate("""() => ({ off: unitPassiveAtkPct(1376000300,'mid',false,null,false,false),
                                   on:  unitPassiveAtkPct(1376000300,'mid',true,null,false,false) })""")
        print('[① 距离条件]', r)
        assert r['off'] == 30 and r['on'] == 30, r

        def dmg(defup=0, guard=False):
            pg.evaluate("""([defup,guard]) => { const c=state.calc, t=state.team;
              c.unitId=1080000150; c.charId=1080000101; c.ca=true; c.first=false; c.allup=0; c.tDef=20000;
              t.defup=defup; t.guard=guard; t.sdef=false; t.dunit=null; t.dchar=null; t.tDef=0;
              state._prKey=null; state.stack=[]; push({page:'calc',title:'计算'}); render(); }""", [defup, guard])
            pg.wait_for_timeout(1700)
            return pg.evaluate("""() => { const tr=[...document.querySelectorAll('#view table.ctable tr')].find(r=>r.innerText.includes('冲浪者突击'));
              if(!tr) return null; const td=[...tr.querySelectorAll('td')]; return +td[2].innerText.replace(/,/g,''); }""")

        base = dmg(0, False); up = dmg(30, False); gd = dmg(0, True)
        print('[② 目标全能力]', base, '→', up, '| [③ 选择防御]', gd)
        assert base > up, (base, up)
        assert gd < base, (gd, base)

        sync = pg.evaluate("""() => { const t=state.team; t.guard=false; t.sdef=false; t.defup=0;
          state.stack=[]; push({page:'calc',title:'计算'}); render();
          document.getElementById('ctguard').click(); return {guard: state.team.guard}; }""")
        print('[③ 开关共享]', sync)
        assert sync['guard'] is True, sync

        assert not errors, errors
        print('=== test_v158 全部通过 ===')
        b.close()
finally:
    srv.terminate()
