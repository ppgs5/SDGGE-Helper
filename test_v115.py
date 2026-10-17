# -*- coding: utf-8 -*-
"""v115 验证: ULT 三形态阶段标注(初始/ULT化/ULT改造)
① ultStageMap: 63 台全部识别, 21/21/21 三阶段
② β·阿吉尔(1114000800/801/802) → 0/1/2 (初始/ULT/改造)
③ 图鉴 ULT 筛选: 角标含 ULT·初始 与 ULT·改造, 中间体为 ULT
④ 详情页: · ULT（初始形态）/（ULT形态）/（ULT改造形态）
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9023
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

        r1 = pg.evaluate("""() => { const m = ultStageMap(); const cnt = { 0: 0, 1: 0, 2: 0 };
          for (const k in m) cnt[m[k]]++;
          const fam = [1114000800, 1114000801, 1114000802].map(id => ultStageOf(q1('SELECT * FROM units WHERE id=?', [id])));
          return { n: Object.keys(m).length, cnt, fam }; }""")
        print('[①② 阶段映射]', r1)
        assert r1['n'] == 63 and r1['cnt'] == {'0': 21, '1': 21, '2': 21} and r1['fam'] == [0, 1, 2], r1
        print('[① 63台全识别 · ② 初始/ULT/改造=0/1/2 通过]')

        pg.evaluate("() => { state.unitKind = 'unit'; state.stack = []; push({ page:'units', title:'图鉴' }); render(); }")
        pg.wait_for_timeout(1000)
        pg.evaluate("() => document.querySelector('[data-krar=\"ult\"]').click()")
        pg.wait_for_timeout(1500)
        r3 = pg.evaluate("""() => { const el = document.querySelector('#listarea');
          const rows = [...el.querySelectorAll('.ucard')].map(e => e.innerText);
          const cInit = rows.filter(t => t.includes('ULT·初始')).length;
          const cMod = rows.filter(t => t.includes('ULT·改造')).length;
          const cUlt = rows.filter(t => t.includes('ULT') && !t.includes('ULT·')).length;
          return { cInit, cMod, cUlt, n: rows.length }; }""")
        print('[③ 图鉴角标]', r3)
        assert r3['cInit'] > 0 and r3['cInit'] == r3['cMod'] == r3['cUlt'] and r3['n'] == r3['cInit'] * 3, r3
        print('[③ ULT·初始/ULT/ULT·改造 角标 通过]')

        def detail(uid):
            pg.evaluate("(uid) => { state.stack = []; push({ page:'unit', title:'x', id: uid }); render(); }", uid)
            pg.wait_for_timeout(800)
            return pg.evaluate("() => { const m = document.getElementById('view').innerText.match(/· ULT[^\\n]*/); return m && m[0]; }")
        d0, d1, d2 = detail(1114000800), detail(1114000801), detail(1114000802)
        print('[④ 详情]', d0, '|', d1, '|', d2)
        assert d0 == '· ULT（初始形态）' and d1 == '· ULT（ULT形态）' and d2 == '· ULT（ULT改造形态）', (d0, d1, d2)
        print('[④ 详情页阶段全称 通过]')

        assert not errors, errors
        print('=== test_v115 全部通过 ===')
        b.close()
finally:
    srv.terminate()
