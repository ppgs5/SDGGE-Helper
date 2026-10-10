# -*- coding: utf-8 -*-
"""v0.68 验证: 改装核心(SSP满10)武器强化建模
语义(参考站源码 chunks_2UCe/nodes_8): 核心level≤10的 weapon_enhance —
  type1=威力平加(power=floor(lv%×基础)+Σ) / 2=EN减 / 3=弹药+ / 4=最大射程+; weapon_change 纯追加(无替换)
① EXZELIA: MAP(星星诞生的世界) +350 威力(满10) → lv5 4,080→4,430、lv1 3,400→3,750; 球体浮游炮 射程 3-5→3-6
② 机体页: SSP关显示基础值 / SSP开显示强化视图(威力/射程)
③ 计算页: SSP开时公式明细威力 = 4,430
④ 官方样例: 钢加农(core5 射程+1 / core10 威力+350) / 高达(core1+core10 共 +350)
回归: test_v58/v59/v63/v64/v66/v67 全过
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8964
EXZ, GUNC, GUNDAM = 1999000100, 1001000200, 1001000100

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

        # ---------- ① 数据/公式 ----------
        r = pg.evaluate(f"""() => {{
          const u = q1('SELECT * FROM units WHERE id={EXZ}');
          const mods = sspWeaponMods(u);
          const w1 = q1('SELECT * FROM weapons WHERE id={EXZ*100+1}');
          const w4 = q1('SELECT * FROM weapons WHERE id={EXZ*100+4}');
          return {{mods, lv1: Engine.weaponPower(w1, 1), lv5: Engine.weaponPower(w1, 5),
                  lv1a: Engine.weaponPower(sspAdjW(w1, u), 1), lv5a: Engine.weaponPower(sspAdjW(w1, u), 5),
                  rng0: w4.range_max, rng1: sspAdjW(w4, u).range_max}};
        }}""")
        print('[① 数据]', r)
        assert r['mods'][str(EXZ*100+1)]['pa'] == 350 and r['mods'][str(EXZ*100+4)]['rng'] == 1, r['mods']
        assert r['lv5'] == 4080 and r['lv5a'] == 4430, (r['lv5'], r['lv5a'])     # 满10: 4,080→4,430
        assert r['lv1'] == 3400 and r['lv1a'] == 3750, (r['lv1'], r['lv1a'])     # 平加逐级(参考站公式)
        assert r['rng0'] == 5 and r['rng1'] == 6, (r['rng0'], r['rng1'])
        print('[① 改装核心公式(威力平加/射程+)] 通过')

        # ---------- ② 机体页显示 ----------
        pg.evaluate(f"() => {{ state.unit = {{star:0, star3:true, sp:true, ssp:false}}; state.stack=[]; push({{page:'unit', title:'x', id:{EXZ}}}); }}")
        pg.wait_for_timeout(800)
        off = pg.evaluate("() => [...document.querySelectorAll('.wrow')].map(e => e.textContent.replace(/\\s+/g,' '))")
        pg.evaluate("() => { state.unit.ssp = true; render(); }")
        pg.wait_for_timeout(800)
        on = pg.evaluate("() => [...document.querySelectorAll('.wrow')].map(e => e.textContent.replace(/\\s+/g,' '))")
        assert any('3,400→4,080' in x for x in off) and any('球体浮游炮3-5' in x for x in off), off
        assert any('3,750→4,430' in x for x in on) and any('球体浮游炮3-6' in x for x in on), on
        print('[② 机体页 SSP开/关 武器视图] 通过')

        # ---------- ③ 计算页: MAP 行伤害 随SSP开/关变化(+350威力) ----------
        pg.evaluate(f"() => {{ state.calc = Object.assign(state.calc, {{unitId:{EXZ}, charId:{EXZ}, lv:5, s3u:true, spU:true}}); state.stack=[]; setTab('calc'); }}")
        pg.wait_for_timeout(2200)
        def map_dmg(ssp):
            pg.evaluate(f"() => {{ state.calc.ssp = {'true' if ssp else 'false'}; render(); }}")
            pg.wait_for_timeout(700)
            return pg.evaluate("() => { const tr = [...document.querySelectorAll('.ctable tr')].find(r => r.textContent.includes('星星诞生的世界')); return tr ? tr.querySelectorAll('td')[1].textContent : null; }")
        d_on, d_off = map_dmg(True), map_dmg(False)
        print('[③ MAP行 低防伤害] SSP开:', d_on, '| SSP关:', d_off)
        v_on = int(d_on.replace(',', '')); v_off = int(d_off.replace(',', ''))
        assert v_on > v_off and 1.02 < v_on / v_off < 1.15, (v_on, v_off)   # 威力 4,430/4,080 ≈ +8.6% → 伤害小幅上升
        print('[③ 计算页随SSP应用改装核心强化] 通过')

        # ---------- ④ 官方样例 ----------
        g = pg.evaluate(f"() => ({{ gunc: sspWeaponMods(q1('SELECT * FROM units WHERE id={GUNC}')), gd: sspWeaponMods(q1('SELECT * FROM units WHERE id={GUNDAM}')) }})")
        print('[④ 官方样例]', g)
        assert g['gunc'][str(GUNC*100+3)]['pa'] == 350 and g['gunc'][str(GUNC*100+3)]['rng'] == 1, g['gunc']
        assert g['gd'][str(GUNDAM*100+3)]['pa'] == 350, g['gd']
        print('[④ 官方样例(钢加农/高达)] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v68 全部通过 ===')
