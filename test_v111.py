# -*- coding: utf-8 -*-
"""v111 验证: ①「优势」类驾驶员标签条件被动互斥(未指定敌方时假设模式只取最高一项, 不再+20+20=40)
   ②首动「MP提升」释放条件: 自身被动MP≥3 才放(官方规则) — 佛罗伦萨(MP0)首动不放MP技; 张五飞(MP5)照放
① unitPassiveAtkPct(1400000550 AGE-2EX): 假设=20 (曾40); 敌方=新人类→20; 敌方含双标签→40(真匹配仍叠加)
② enemyCondNotes 假设模式: 只列计入的一项(敌驾驶员·新人类)
③ buildRanking 首动开: AGE-2EX 机体被动20% & 首动非MP(k=stat); 双头龙EX 首动=MP提升(MP5≥3) & 伤害147,220(不变)
④ firstActOfRows 条件: 佛罗伦萨 mp=0 → 非mp; mp=7 → mp; 张五飞 mp=5 → mp
⑤ 排行DOM: 双头龙行仍含「首动 MP提升 超一击」且 147,220; 无「+40%」的AGE-2EX行残留(跌出前100)
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9019
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

        # ①
        r1 = pg.evaluate("""() => ({
          assumed: unitPassiveAtkPct(1400000550, 'mid', true, null, false),
          nt: unitPassiveAtkPct(1400000550, 'mid', true, { tags: new Set(), seriesList: new Set(), ctags: new Set(['新人类']) }, false),
          both: unitPassiveAtkPct(1400000550, 'mid', true, { tags: new Set(), seriesList: new Set(), ctags: new Set(['新人类','X行者']) }, false) })""")
        print('[① 优势互斥]', r1)
        assert r1 == {'assumed': 20, 'nt': 20, 'both': 40}, r1
        print('[① 假设模式只取最高(+20) · 真匹配叠加 通过]')

        # ②
        r2 = pg.evaluate("""() => enemyCondNotes(1400000550, null, { condAll: true, upassive: true, passive: true, pSpU: true }, false, null)""")
        print('[② 条件注明]', r2)
        assert len(r2['detail']) == 1 and '新人类' in r2['detail'][0], r2
        print('[② enemyCondNotes 假设模式只列计入一项 通过]')

        # ③
        r3 = pg.evaluate("""() => {
          const f = filt('rank');
          const R = buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false },
            { passive: true, cpassive: true, skills: false, first: true, condAll: true, autoVigor: true, multiPhase: false, star: 3,
              spU: true, s3u: true, sspU: true, pSpU: true });
          const a = R.find(x => x.unitId === 1400000550), c = R.find(x => x.unitId === 1219000650);
          return { aPct: a && a.pct, aFaK: a && a.fa && a.fa.k, cFaK: c && c.fa && c.fa.k, cFaName: c && c.fa && c.fa.name, cDmg: c && c.dmg }; }""")
        print('[③ 排行首动]', r3)
        assert r3['aPct'] == 20 and r3['aFaK'] != 'mp' and r3['cFaK'] == 'mp' and r3['cDmg'] == 147220, r3
        print('[③ AGE-2EX 被动20%+首动非MP · 双头龙 首动MP提升 伤害不变 通过]')

        # ④
        r4 = pg.evaluate("""() => ({
          fl0: firstActOfRows(charActSkillRows(1850001501, true), ['awaken'], false, 0),
          fl7: firstActOfRows(charActSkillRows(1850001501, true), ['awaken'], false, 7),
          zwf: firstActOfRows(charActSkillRows(1219000501, true), ['melee'], false, mpOf(1219000650, 1219000501, false, true, true, false)) })""")
        print('[④ MP释放条件]', r4)
        assert r4['fl0']['k'] != 'mp' and r4['fl7']['k'] == 'mp' and r4['zwf']['k'] == 'mp', r4
        print('[④ 首动MP提升: 被动MP≥3才放 通过]')

        # ⑤ 排行DOM
        pg.evaluate("""() => { const c = state.rankCfg; c.vigor = 'default'; c.first = true; c.skills = false; c.mp = false; c.ca = true;
          state.stack = []; push({ page:'rank', title:'排行' }); render(); }""")
        pg.wait_for_timeout(3600)
        r5 = pg.evaluate("""() => { const tx = document.getElementById('view').innerText;
          const i = tx.indexOf('双头龙高达 (EW版) (EX)');
          const j = tx.indexOf('高达AGE-2 基本型');
          return { dbl: i < 0 ? null : tx.slice(i, i + 200).replace(/\\n/g, ' | '), age40: j >= 0 && tx.slice(j, j + 180).includes('机体被动+40%') }; }""")
        print('[⑤ 排行DOM]', (r5['dbl'] or '')[:160], '| 残留+40%:', r5['age40'])
        assert r5['dbl'] and '首动 MP提升 超一击' in r5['dbl'] and '147,220' in r5['dbl'] and not r5['age40'], r5
        print('[⑤ 排行: 双头龙保留首动MP提升·147,220; 无+40%残留 通过]')

        assert not errors, errors
        print('=== test_v111 全部通过 ===')
        b.close()
finally:
    srv.terminate()
