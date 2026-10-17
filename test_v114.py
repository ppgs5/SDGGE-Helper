# -*- coding: utf-8 -*-
"""v114 验证: 终极机体(ULT)选项 + ULT数据/角标
① unitWhere('unit', rar='ult') 列出 63 台 ULT (全部 ult=1)
② buildRanking rarity='ult' → 63 行 全为 ULT
③ 图鉴: 稀有度出现 ULT chip; 点击筛选 命中63 且行尾显示 ULT 角标
④ 排行: ULT chip 生效 (cfg.rarity='ult' 时所有行为 ULT)
⑤ 组队: 机体稀有度 ULT chip, t.rar='ult' 时 eHP 行全为 ULT
⑥ ULT数据完整性: 21 家族×3 阶段(初始/ULT/改造), 每台均有武器与能力
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9022
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

        # ① ⑥
        r1 = pg.evaluate("""() => {
          const uw = unitWhere('unit', { tags: [], series: [], mode: 'and', rar: 'ult' });
          const rows = q(`SELECT u.id, u.ult FROM units u ${uw.where}`, uw.args);
          const fam = q("SELECT name, count(*) n FROM units WHERE ult=1 GROUP BY name");
          const incomplete = q("SELECT u.id FROM units u WHERE u.ult=1 AND (NOT EXISTS(SELECT 1 FROM weapons w WHERE w.unit_id=u.id) OR NOT EXISTS(SELECT 1 FROM unit_abilities a WHERE a.unit_id=u.id))");
          return { uwN: rows.length, allUlt: rows.every(x => x.ult === 1), famN: fam.length, fam3: fam.every(x => x.n === 3), incomplete: incomplete.length }; }""")
        print('[①⑥ ULT数据]', r1)
        assert r1['uwN'] == 63 and r1['allUlt'] and r1['famN'] == 21 and r1['fam3'] and r1['incomplete'] == 0, r1
        print('[① unitWhere ULT=63 · ⑥ 21家族×3阶段/武器能力齐全 通过]')

        # ②
        r2 = pg.evaluate("""() => {
          const R = buildRanking(filt('rank'), { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false, rarity: 'ult' },
            { passive: true, cpassive: true, skills: false, condAll: true, autoVigor: true, multiPhase: false, star: 3, spU: true, s3u: true, sspU: true, pSpU: true });
          return { n: R.length, all: R.every(x => x.unit.ult) }; }""")
        print('[② buildRanking ULT]', r2)
        assert r2['n'] == 63 and r2['all'], r2

        # ③ 图鉴
        pg.evaluate("() => { state.unitKind = 'unit'; state.stack = []; push({ page:'units', title:'图鉴' }); render(); }")
        pg.wait_for_timeout(1200)
        chip = pg.evaluate("() => !!document.querySelector('[data-krar=\"ult\"]')")
        pg.evaluate("() => document.querySelector('[data-krar=\"ult\"]').click()")
        pg.wait_for_timeout(1500)
        r3 = pg.evaluate("""() => { const tx = document.getElementById('view').innerText;
          const cards = [...document.querySelectorAll('#listarea .ucard, #listarea [data-go]')].filter(e => e.innerText.trim());
          const badges = cards.filter(e => e.innerText.includes('ULT')).length;
          return { chip: true, hit63: tx.includes('命中 63'), cards: cards.length, badges }; }""")
        print('[③ 图鉴 ULT]', r3)
        assert chip and r3['hit63'] and r3['cards'] > 0 and r3['badges'] == r3['cards'], r3
        print('[③ 图鉴 ULT chip 筛选63 + 行尾ULT角标 通过]')

        # ④ 排行
        pg.evaluate("() => { const c = state.rankCfg; c.rarity = 'ult'; state.stack = []; push({ page:'rank', title:'排行' }); render(); }")
        pg.wait_for_timeout(3400)
        r4 = pg.evaluate("""() => { const hasChip = !!document.querySelector('[data-rar=\"ult\"]');
          const rows = [...document.querySelectorAll('#rlist .rrow, #rlist [data-id]')].slice(0, 10);
          return { hasChip, n: rows.length, allUlt: rows.every(e => e.innerText.includes('ULT')) }; }""")
        print('[④ 排行 ULT]', r4)
        assert r4['hasChip'] and r4['n'] > 0 and r4['allUlt'], r4

        # ⑤ 组队
        pg.evaluate("""() => { const t = state.team; t.rar = 'ult'; t.terr = ''; t.terrO = false; state.stack = []; push({ page:'team', title:'组队' }); render(); }""")
        pg.wait_for_timeout(3200)
        r5 = pg.evaluate("""() => { const hasChip = !!document.querySelector('[data-trar=\"ult\"]');
          const cards = [...document.querySelectorAll('#tarea .card')];
          const eh = cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes('有效耐久'));
          const ids = eh ? [...eh.querySelectorAll('.trow')].map(e => +e.dataset.id).filter(Boolean) : [];
          const allUlt = ids.length > 0 && ids.every(id => q1('SELECT ult FROM units WHERE id=?', [id]).ult === 1);
          return { hasChip, n: ids.length, allUlt }; }""")
        print('[⑤ 组队 ULT]', r5)
        assert r5['hasChip'] and r5['n'] > 0 and r5['allUlt'], r5

        assert not errors, errors
        print('=== test_v114 全部通过 ===')
        b.close()
finally:
    srv.terminate()
