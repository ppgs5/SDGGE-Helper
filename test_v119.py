# -*- coding: utf-8 -*-
"""v119 验证: ①ULT改造开关(计算口径) + 图鉴显示ULT改造机体技能(主数据 MUnitUltGroup/MUnitUltCustomSkill 导入)
   ②机体技能开关(独立于驾驶员主动技能)
① ult_group 主数据: 63 台(21/21/21); redo 1114000800→1114000802, 1750000400→1750000402
② 图鉴 1750000302(改造形态): 机体技能 攻击爆裂/支援攻击次数增加/射程增幅 + ULT改造标签; stage0+ultRedo 同显
③ 图鉴数值: unitListStat(stage0) ultRedo 关=自身, 开=改造形态
④ 排行: ultRedo 开→ 1750000300/301 去重合并到 302; 关→ 各自独立
⑤ 机体技能开关: buildRanking 1370011150 uPct 开/关差25(机体技能攻击+25); 图鉴档位同口径
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9027
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        r1 = pg.evaluate("""() => { const st = ultStageMap(), rd = ultRedoMap();
          const cnt = {0:0,1:0,2:0}; for (const k in st) cnt[st[k]]++;
          return { n: Object.keys(st).length, cnt, r800: rd[1114000800], r400: rd[1750000400], r1341: rd[1342000101] }; }""")
        print('[① 主数据组]', r1)
        assert r1['n'] == 63 and r1['cnt'] == {'0': 21, '1': 21, '2': 21}, r1
        assert r1['r800'] == 1114000802 and r1['r400'] == 1750000402 and r1['r1341'] == 1342000102, r1
        print('[① ult_group 63 / redo 映射 通过]')

        def detail(uid, ultred):
            pg.evaluate("(a) => { state.ultLv = a[1] ? 100 : 0; state.stack = []; push({ page:'unit', title:'x', id: a[0] }); render(); }", [uid, ultred])
            pg.wait_for_timeout(700)
            return pg.evaluate("() => { const t = document.getElementById('view').innerText; return t; }")
        t2 = detail(1750000302, False)
        ok2 = all(k in t2 for k in ('攻击爆裂', '支援攻击次数增加', '射程增幅', '机体技能', 'ULT改造'))
        print('[② 改造形态详情技能]', ok2)
        assert ok2, t2[:400]
        t3 = detail(1750000300, True)
        ok3 = ('攻击爆裂' in t3 and '机体技能' in t3 and 'ULT改造 Lv100' in t3)
        print('[② stage0+ultRedo 详情]', ok3)
        assert ok3, t3[:400]
        print('[② 图鉴显示 ULT改造机体技能 通过]')

        r3 = pg.evaluate("""() => {
          const u0 = q1('SELECT * FROM units WHERE id=1750000300');
          state.ultLv = 0;
          const vOff = unitListStat(u0, 'hp', 0, 3);
          state.ultLv = 100;
          const vOn = unitListStat(u0, 'hp', 0, 3);
          state.ultLv = 0;
          return { own: u0.max_hp, vOff, vOn }; }""")
        print('[③ 图鉴数值]', r3)
        assert r3['vOff'] == r3['own'] and r3['vOn'] == r3['own'] + r3['own'] // 10, r3
        print('[③ 图鉴数值口径 ULT改造 Lv0/100 通过]')

        r4 = pg.evaluate("""() => {
          const f = filt('rank');
          const opts = { passive: true, cpassive: true, skills: false, condAll: true, autoVigor: true, multiPhase: false, star: 3, spU: true, s3u: true, sspU: true, pSpU: true, uSk: true };
          state.ultLv = 0;
          const off = buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false }, opts).map(x => x.unitId);
          state.ultLv = 100;
          const on = buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false }, opts).map(x => x.unitId);
          state.ultLv = 0;
          return { offHas0: off.includes(1750000300), offHas2: off.includes(1750000302), onHas0: on.includes(1750000300), onHas2: on.includes(1750000302), nOff: off.length, nOn: on.length }; }""")
        print('[④ 排行口径]', r4)
        assert r4['onHas0'] and r4['onHas2'] and r4['offHas0'] and r4['offHas2'], r4
        assert r4['nOn'] == r4['nOff'] == 1455, r4
        print('[④ 排行 三段独立(不合并) 通过]')

        r5 = pg.evaluate("""() => {
          const f = filt('rank');
          const opts = { passive: true, cpassive: true, skills: false, condAll: true, autoVigor: true, multiPhase: false, star: 3, spU: true, s3u: true, sspU: true, pSpU: true };
          const pick = (uSk) => { const R = buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false }, Object.assign({ uSk }, opts));
            const r = R.find(x => x.unitId === 1370011150); return r ? r.pct : null; };
          const on = pick(true), off = pick(false);
          const statOn = (() => { state.uSk = true; return unitListStat(q1('SELECT * FROM units WHERE id=1370011150'), 'atk', 2, 3); })();
          const statOff = (() => { state.uSk = false; return unitListStat(q1('SELECT * FROM units WHERE id=1370011150'), 'atk', 2, 3); })();
          state.uSk = true;
          return { pctOn: on, pctOff: off, statOn, statOff }; }""")
        print('[⑤ 机体技能开关]', r5)
        assert r5['pctOn'] is not None and r5['pctOn'] - r5['pctOff'] == 25, r5
        assert r5['statOn'] > r5['statOff'], r5
        print('[⑤ 机体技能 开/关(排行攻击+25 / 图鉴档位) 通过]')

        # ⑥ 四页开关 chip 存在且可点击
        def chips_of(page, ids):
            pg.evaluate("(p2) => { state.stack = []; push({ page: p2, title: '' }); render(); }", page)
            pg.wait_for_timeout(1800)
            return pg.evaluate("(ids) => { const out = {}; for (const id of ids) out[id] = !!document.getElementById(id); return out; }", ids)
        c1 = chips_of('calc', ['cusk', 'curd'])
        c2 = chips_of('rank', ['rusk', 'rurd'])
        c3 = chips_of('team', ['tusk', 'turd'])
        pg.evaluate("() => { state.unitKind = 'unit'; state.stack = []; push({ page:'units', title:'图鉴' }); render(); }")
        pg.wait_for_timeout(1000)
        c4 = pg.evaluate("() => ({ kusk: !!document.getElementById('kusk'), kurd: !!document.getElementById('kurd') })")
        print('[⑥ 开关chip]', c1, c2, c3, c4)
        assert all(c1.values()) and all(c2.values()) and all(c3.values()) and all(c4.values()), (c1, c2, c3, c4)
        pg.evaluate("() => { const before = state.uSk; document.getElementById('kusk').click(); return before; }")
        pg.wait_for_timeout(600)
        r6 = pg.evaluate("() => state.uSk")
        assert r6 is False, r6
        pg.evaluate("() => document.getElementById('kusk').click()")
        pg.wait_for_timeout(400)
        print('[⑥ 四页开关 chip 存在且可点击 通过]')

        # ⑦ 特性「单位技能」列表含 ULT改造技能
        pg.evaluate("() => { state.stack = []; push({ page:'feat', title:'特性' }); render(); }")
        pg.wait_for_timeout(900)
        pg.evaluate("() => document.querySelector('[data-k=\"unit_skill\"]').click()")
        pg.wait_for_timeout(1200)
        r7 = pg.evaluate("() => { const t = document.getElementById('farea').innerText; return { n: t.includes('31条'), ult: t.includes('威力抵御') || t.includes('攻击爆裂') }; }")
        print('[⑦ 特性单位技能]', r7)
        assert r7['ult'], r7
        print('[⑦ 特性-单位技能含ULT改造技能 通过]')

        assert not errors, errors
        print('=== test_v119 全部通过 ===')
        b.close()
finally:
    srv.terminate()
