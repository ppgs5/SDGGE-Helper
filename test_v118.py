# -*- coding: utf-8 -*-
"""v118 验证: 驾驶员「含被动+X%」只含被动, 首动值增幅单列 (西布克: 被动20 + 首动25, 曾混显45)
① buildRanking(首动开) 西布克×异灵高达(最终决战时)(EX): pstat=20 fa=射击值增幅25 v=1033 dmg=156880; 飞翼零式EW dmg=155441
② 排行DOM: 含「含被动+20%·首动+25%」, 不含「含被动+45%」
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9026
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

        r1 = pg.evaluate("""() => {
          const f = filt('rank');
          const R = buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false },
            { passive: true, cpassive: true, skills: true, first: true, condAll: true, autoVigor: true, multiPhase: false, star: 3,
              spU: true, s3u: true, sspU: true, pSpU: true });
          const a = R.find(x => x.unitId === 1501002250), w = R.find(x => x.unitId === 1219000150);
          return { a: a ? { pstat: a.pstat, faK: a.fa && a.fa.k, faV: a.fa && a.fa.v, v: a.pilot.v, dmg: a.dmg, name: a.pilot.name } : null,
                   w: w ? { dmg: w.dmg, pstat: w.pstat, faV: w.fa && w.fa.v } : null }; }""")
        print('[① 行数据]', r1)
        assert r1['a'] and r1['a']['pstat'] == 20 and r1['a']['faK'] == 'stat' and r1['a']['faV'] == 25, r1
        assert r1['a']['v'] == 1033 and r1['a']['dmg'] == 156880 and r1['a']['name'] == '西布克·阿诺', r1
        assert r1['w'] and r1['w']['dmg'] == 155441 and r1['w']['pstat'] == 20, r1
        print('[① 西布克 被动20+首动25 分开 · 1033/156880/155441 不变 通过]')

        pg.evaluate("() => { const c = state.rankCfg; c.vigor = 'default'; c.first = true; c.skills = true; c.ca = true; state.stack = []; push({ page:'rank', title:'排行' }); render(); }")
        pg.wait_for_timeout(3600)
        r2 = pg.evaluate("""() => { const t = document.getElementById('view').innerText;
          return { ok: t.includes('含被动+20%·首动+25%'), bad: t.includes('含被动+45%') }; }""")
        print('[② 排行DOM]', r2)
        assert r2['ok'] and not r2['bad'], r2
        print('[② 含被动+20%·首动+25% · 无+45% 通过]')

        assert not errors, errors
        print('=== test_v118 全部通过 ===')
        b.close()
finally:
    srv.terminate()
