# -*- coding: utf-8 -*-
"""v0.69 验证: SSP改装核心双层 — 能力变化(ability_change) + 武器效果(weapon_effect)
语义(参考站源码): ability_change before=0新增/before≠0替换(F()语义); weapon_effect 数值类(9/10/25/26/39/44/45/81/82/91/92)且目标武器lv5无同型 → 计入(同型仅并描述)
① 能力变化: 钢坦克「攻击力提升 LV2」新增(+10 攻击%) — unitPassiveAtkPct 关0/开10;
   高达「最大EN提升」LV1→LV2 替换; 钢加农「防御力提升 LV2」新增 → defenderSkills SSP视图 +10
② 武器效果: 核心战机 weapon {9,-10}(防减) / 钢坦克 weapon {92,+5}(POWER) 仅SSP视图; 引擎 powerBoostPct 计入
③ 机体页: SSP开显示 攻击力提升 LV2 + SSP徽标; SSP关不显示
④ 组队/计算 smoke
回归: test_v58/v59/v63/v64/v66/v67/v68 全过
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8961
GUNTANK, GUNDAM, GUNCANNON = 1001000300, 1001000100, 1001000200
CORE, GUNTANK_W, CORE_W = 1001000400, 100100030002, 100100040002

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(120000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')

        # ---------- ① 能力变化 ----------
        r = pg.evaluate(f"""() => ({{
          gt_off: unitPassiveAtkPct({GUNTANK}, 'supercharged', true, null, false),
          gt_on: unitPassiveAtkPct({GUNTANK}, 'supercharged', true, null, true),
          gd_off: unitAbilitiesOf({GUNDAM}, false).map(a => a.name),
          gd_on: unitAbilitiesOf({GUNDAM}, true).map(a => a.name + (a._ssp ? '[' + a._ssp + ']' : '')),
          gc_off: defenderSkills({GUNCANNON}, null, false, false).defPct,
          gc_on: defenderSkills({GUNCANNON}, null, false, true).defPct
        }})""")
        print('[① 能力变化]', r)
        assert r['gt_on'] - r['gt_off'] == 10, r            # 钢坦克 攻击力提升 LV2 新增 +10
        assert '最大EN提升 LV1' in r['gd_off'] and '最大EN提升 LV2[repl]' in r['gd_on'], r
        assert r['gc_on'] - r['gc_off'] == 10, r            # 钢加农 防御力提升 LV2 新增 → 防御方技能视图 +10
        print('[① 能力变化(新增/替换)] 通过')

        # ---------- ② 武器效果 ----------
        w = pg.evaluate(f"""() => {{
          const u3 = q1('SELECT * FROM units WHERE id={GUNTANK}');
          const aw3 = sspAdjW(q1('SELECT * FROM weapons WHERE id={GUNTANK_W}'), u3);
          const u4 = q1('SELECT * FROM units WHERE id={CORE}');
          const aw4 = sspAdjW(q1('SELECT * FROM weapons WHERE id={CORE_W}'), u4);
          const pb3 = Engine.powerBoostPct(wTraitsOf(aw3, null, true), 5);
          const pb3b = Engine.powerBoostPct(wTraitsOf({GUNTANK_W}, null, true), 5);
          const adj4 = Engine.targetDefAdjust(wTraitsOf(aw4, null, true), 5);
          const adj4b = Engine.targetDefAdjust(wTraitsOf({CORE_W}, null, true), 5);
          return {{pb3, pb3b, adj4, adj4b, has3: !!aw3._sspTraits, has4: !!aw4._sspTraits}};
        }}""")
        print('[② 武器效果]', w)
        assert w['has3'] and w['has4'], w
        assert w['pb3'] - w['pb3b'] == 5, w                 # 钢坦克 {92,+5} POWER 仅SSP视图
        assert w['adj4']['pct'] == -10 and w['adj4b']['pct'] == 0, w   # 核心战机 {9,-10} 防减 仅SSP视图
        print('[② 武器效果(POWER/防减,引擎计入)] 通过')

        # ---------- ③ 机体页显示 ----------
        pg.evaluate(f"() => {{ state.unit = {{star:0, star3:true, sp:true, ssp:false}}; state.stack=[]; push({{page:'unit', title:'x', id:{GUNTANK}}}); }}")
        pg.wait_for_timeout(800)
        off = pg.evaluate("() => document.querySelector('#view').textContent")
        assert '攻击力提升 LV2' not in off, 'SSP关不应显示新增能力'
        pg.evaluate("() => { state.unit.ssp = true; render(); }")
        pg.wait_for_timeout(800)
        on = pg.evaluate("() => document.querySelector('#view').textContent")
        assert '攻击力提升 LV2' in on and 'SSP' in on, on[:300]
        print('[③ 机体页SSP能力显示] 通过')

        # ---------- ④ 组队 smoke ----------
        pg.evaluate("() => { state.stack = []; setTab('team'); }"); pg.wait_for_timeout(2500)
        assert pg.evaluate("() => !!document.querySelector('#tarea').textContent.trim()"), '组队应正常渲染'
        print('[④ 组队 smoke] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v69 全部通过 ===')
