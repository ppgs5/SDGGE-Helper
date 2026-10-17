# -*- coding: utf-8 -*-
"""v117 验证: 排行行「驾驶员增伤」只显示被动增伤(首动爆裂单独显示), 伤害计算不变
① buildRanking(首动开·条件开) 卡碧尼(ZZ版)(EX)+哈曼: pct=35(机体), pdmg=35(被动20+15, 不含首动爆裂25), fa=攻击爆裂 v25, dmg=179792 不变, pstat/star/effPower 字段完好
② DOM: 行含「驾驶员增伤+35%」「首动 攻击爆裂 +25%」, 不含「驾驶员增伤+60%」
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9025
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
          const row = R.find(x => x.unitId === 1095002550);
          return row ? { pct: row.pct, pdmg: row.pdmg, faK: row.fa && row.fa.k, faV: row.fa && row.fa.v,
            dmg: row.dmg, pstat: row.pstat, star: row.star, effPower: row.effPower } : null; }""")
        print('[① 行数据]', r1)
        assert r1 and r1['pct'] == 35 and r1['pdmg'] == 35 and r1['faK'] == 'burst' and r1['faV'] == 25, r1
        assert r1['dmg'] == 179792 and r1['pstat'] == 25 and r1['star'] == 3 and r1['effPower'] == 7776, r1
        print('[① 驾驶员增伤=被动35(不含首动爆裂) · 伤害179792不变 · 字段完好 通过]')

        pg.evaluate("() => { const c = state.rankCfg; c.vigor = 'default'; c.first = true; c.skills = true; c.skills = true; c.ca = true; state.stack = []; push({ page:'rank', title:'排行' }); render(); }")
        pg.wait_for_timeout(3600)
        r2 = pg.evaluate("""() => { const t = document.getElementById('view').innerText; const i = t.indexOf('卡碧尼 (ZZ版) (EX)');
          if (i < 0) return null; const seg = t.slice(i, i + 300).replace(/\\n/g, '|');
          return { seg, ok35: seg.includes('驾驶员增伤+35%'), ok60: seg.includes('驾驶员增伤+60%'), burst: seg.includes('首动 攻击爆裂 +25%') }; }""")
        print('[② DOM]', (r2 or {}).get('ok35'), (r2 or {}).get('ok60'), (r2 or {}).get('burst'))
        assert r2 and r2['ok35'] and not r2['ok60'] and r2['burst'], r2

        assert not errors, errors
        print('=== test_v117 全部通过 ===')
        b.close()
finally:
    srv.terminate()
