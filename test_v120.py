# -*- coding: utf-8 -*-
"""v120 验证: ULT改造三挡(0/50/100) + 三段共用 + 50级ULT武器 + 100级三选一能力
① 主数据: ult_custom 16 / ult_skills 18 (6组三选一) / ult_weapons 24
② 数值: 1308000502 max_hp 108000/max_atk 9834 → Lv50 113400/10325, Lv100 118800/10817 (floor(max×Lv/1000))
③ 三段独立: 排行 ultLv=100 时 1308000500/501/502 同时存在, 总数1455(不再合并)
④ ULT武器: 50级才出现(1308000500→130800050170, 1308000502→130800050270); 0级隐藏
⑤ 三选一: 攻击爆裂+20%增伤 / 威力抵御+20%减伤 / 支援防御+1 / MP提升+6 只取所选
⑥ UI: 四页 ULT改造 chip 打开三挡弹层; 图鉴单列「ULT改造能力 · 三选一」
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9043
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(240000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        r1 = pg.evaluate("""() => ({
          custom: q('SELECT COUNT(*) c FROM ult_custom')[0].c,
          skills: q('SELECT COUNT(*) c FROM ult_skills')[0].c,
          weapons: q('SELECT COUNT(*) c FROM ult_weapons')[0].c,
          groups: q('SELECT COUNT(DISTINCT group_id) c FROM ult_skills')[0].c,
          g5: ultSkillsOf(13080005).length })""")
        print('[① 主数据]', r1)
        assert r1 == {'custom': 16, 'skills': 18, 'weapons': 24, 'groups': 6, 'g5': 3}, r1

        r2 = pg.evaluate("""() => {
          const u = q1('SELECT * FROM units WHERE id=1308000502');
          state.ultLv = 0; const a = effUnit(u);
          state.ultLv = 50; const b = effUnit(u);
          state.ultLv = 100; const c = effUnit(u);
          return { hp0: a.max_hp, hp50: b.max_hp, hp100: c.max_hp, atk50: b.max_atk, atk100: c.max_atk }; }""")
        print('[② 数值]', r2)
        assert r2 == {'hp0': 108000, 'hp50': 113400, 'hp100': 118800, 'atk50': 10325, 'atk100': 10817}, r2

        r3 = pg.evaluate("""() => {
          const f = filt('rank');
          const opts = { passive: true, cpassive: true, skills: false, condAll: true, autoVigor: true, multiPhase: false,
                         star: 3, spU: true, s3u: true, sspU: true, pSpU: true, uSk: true };
          state.ultLv = 100; state.ultSkill = {};
          const R = buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false }, opts);
          const ids = [1308000500, 1308000501, 1308000502];
          const got = ids.filter(id => R.some(x => x.unitId === id));
          return { n: R.length, got, hp500: effUnit(q1('SELECT * FROM units WHERE id=1308000500')).max_hp }; }""")
        print('[③ 三段独立]', r3)
        assert r3['n'] == 1455 and len(r3['got']) == 3, r3
        assert r3['hp500'] == 78137 + 7813, r3
        print('[③ 三段各自计算/不合并 通过]')

        r4 = pg.evaluate("""() => {
          const u0 = q1('SELECT * FROM units WHERE id=1308000500'), u2 = q1('SELECT * FROM units WHERE id=1308000502');
          state.ultLv = 0; const a0 = weaponsForUnit(u0).map(w => w.id), a2 = weaponsForUnit(u2).map(w => w.id);
          state.ultLv = 50; const b0 = weaponsForUnit(u0).map(w => w.id), b2 = weaponsForUnit(u2).map(w => w.id);
          return { off0: a0.includes(130800050170), off2: a2.includes(130800050270),
                   on0: b0.includes(130800050170), on2: b2.includes(130800050270) }; }""")
        print('[④ ULT武器]', r4)
        assert r4 == {'off0': False, 'off2': False, 'on0': True, 'on2': True}, r4
        print('[④ Lv50解锁/0级隐藏 通过]')

        r5 = pg.evaluate("""() => {
          const f = filt('rank');
          const opts = { passive: true, cpassive: true, skills: true, condAll: true, autoVigor: true, multiPhase: false,
                         star: 3, spU: true, s3u: true, sspU: true, pSpU: true, uSk: true };
          state.ultLv = 100;
          state.ultSkill = { 13790001: '200110100001' };   // 攻击爆裂
          const A = buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false }, opts);
          state.ultSkill = { 13790001: '200070100001' };   // 高速(无增伤)
          const B = buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false }, opts);
          const da = (A.find(x => x.unitId === 1379000102) || {}).dmg, db = (B.find(x => x.unitId === 1379000102) || {}).dmg;
          state.ultSkill = { 13080005: '200120100001' };   // 威力抵御
          const red = defenderSkills(1308000502, null, false, false, 'default', true).redPct;
          state.ultLv = 50; const red50 = defenderSkills(1308000502, null, false, false, 'default', true).redPct;
          state.ultLv = 100; state.ultSkill = { 13080005: '200040100001' };   // 支援防御次数增加
          const sup = supCountsOf(1330000103, 1308000502, 'default', true, true);
          state.ultSkill = { 13080005: '200120100001' };
          const sup0 = supCountsOf(1330000103, 1308000502, 'default', true, true);
          state.ultSkill = { 17640002: '200130100001' };   // MP提升
          const mp1 = mpOf(1764000202, 1330000103, true, true, true, false);
          state.ultSkill = { 17640002: '200070100001' };   // 高速
          const mp0 = mpOf(1764000202, 1330000103, true, true, true, false);
          return { da, db, red, red50, supDef: sup.def, supDef0: sup0.def, mp1, mp0 }; }""")
        print('[⑤ 三选一效果]', r5)
        assert r5['da'] > r5['db'], r5
        assert r5['red'] == 20 and r5['red50'] == 0, r5
        assert r5['supDef'] >= r5['supDef0'] + 1, r5
        assert r5['mp1'] == r5['mp0'] + 6, r5
        print('[⑤ 攻击爆裂/威力抵御/支援次数/MP 仅所选生效 通过]')

        # ⑥ UI: 四页 chip + 弹层三挡 + 图鉴能力卡
        pg.evaluate("() => { state.calc.unitId = 1308000502; state.stack = []; push({ page: 'calc', title: '' }); render(); }")
        pg.wait_for_selector('#curd', timeout=180000)
        pg.click('#curd')
        pg.wait_for_timeout(500)
        t = pg.evaluate("() => document.getElementById('sheetPanel').innerText")
        assert all(k in t for k in ('Lv50', 'Lv100', '三选一')), t[:300]
        pg.click('[data-ultlev="100"]')
        pg.wait_for_timeout(200)
        pg.click('#uultapply')
        pg.wait_for_timeout(1800)
        assert pg.evaluate('() => state.ultLv') == 100
        pg.evaluate("() => { state.stack = []; push({ page: 'unit', title: 'x', id: 1308000500 }); render(); }")
        pg.wait_for_timeout(900)
        t2 = pg.evaluate("() => document.getElementById('view').innerText")
        assert 'ULT改造能力 · 三选一' in t2 and '当前ULT改造 Lv100' in t2, t2[:300]
        for page, cid in (('rank', 'rurd'), ('team', 'turd')):
            pg.evaluate("(p2) => { state.stack = []; push({ page: p2, title: '' }); render(); }", page)
            pg.wait_for_selector('#' + cid, timeout=180000)
        print('[⑥ 四页chip/三挡弹层/图鉴能力卡 通过]')

        # ⑥b 选完直接关闭(X)也要生效(不必点「完成」)
        pg.wait_for_selector('#turd', timeout=180000)
        pg.click('#turd'); pg.wait_for_timeout(300)
        pg.click('[data-ultlev="0"]'); pg.wait_for_timeout(200)
        pg.click('#sx'); pg.wait_for_timeout(6000)
        lv0 = pg.evaluate('() => state.ultLv')
        chip0 = pg.evaluate("() => (document.getElementById('turd') || {}).innerText || ''")
        assert lv0 == 0 and '关' in chip0, (lv0, chip0)
        pg.click('#turd'); pg.wait_for_timeout(300)
        pg.click('[data-ultlev="100"]'); pg.wait_for_timeout(200)
        pg.click('#sx'); pg.wait_for_timeout(6000)
        lv1 = pg.evaluate('() => state.ultLv')
        assert lv1 == 100, lv1
        print('[⑥b 关闭弹层仍保存 Lv0/Lv100 通过]')

        # ⑦ 组队防御eHP榜(筛「终极」标签)必须包含ULT改造数值
        pg.evaluate("""() => { const f=filt('team'); f.tags=[7002]; f.series=[]; f.mode='and'; state.team.rar=null;
          state.ultLv=100; state.stack=[]; push({ page:'team', title:'' }); render(); }""")
        pg.wait_for_function("() => document.getElementById('view').innerText.includes('136,620')", timeout=180000)
        t3 = pg.evaluate("() => document.getElementById('view').innerText")
        ok7 = ('超级海伯瑞安高达' in t3 and '耐久 136,620 · 防御 10,000' in t3 and 'eHP 1,502,820' in t3)
        print('[⑦ 组队防御eHP(终极标签)]', ok7)
        assert ok7, t3[t3.find('超级海伯瑞')-160:t3.find('超级海伯瑞')+260]
        print('[⑦ 组队防御排行含ULT改造数值 通过]')
        # ⑧ 组队攻击行绿色伤害下显示攻击力
        ok8 = ('攻击力 14,062' in t3)
        print('[⑧ 组队攻击行显示攻击力]', ok8)
        assert ok8, t3[t3.find('攻击力')-80:t3.find('攻击力')+120] if '攻击力' in t3 else t3[:300]
        print('[⑧ 攻击力显示 通过]')

        assert not errors, errors
        print('=== test_v120 全部通过 ===')
        b.close()
finally:
    srv.terminate()
