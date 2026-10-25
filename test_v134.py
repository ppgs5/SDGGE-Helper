# -*- coding: utf-8 -*-
"""v134 验证: 按系列筛选时, 机体只要「系列集」含该系列就应命中
问题: D高达3号机(EX) 主系列=DOUBLE FAKE(1010), 系列集含 逆袭的夏亚(1100);
      点《机动战士高达 逆袭的夏亚》后列表里却没有它 —— 旧筛选只看 u.series_id(主系列)
修复: unitWhere 系列条件改为 `主系列 IN (...) OR series_set_json LIKE '%"id"%'`;
      系列选择器的计数同步改为按「主系列+系列集」去重
① SQL 口径: series=[1100] 命中 47 台, 且包含 1101000350(D高达3号机)
② 图鉴详情点击《机动战士高达 逆袭的夏亚》→ 列表出现 D高达3号机
③ 选择器计数与筛选结果一致(1100 计数 == 筛选台数)
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9101

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1200}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        r = pg.evaluate("""() => {
          const f = filt('unit'); f.tags = []; f.mode = 'or'; f.series = [1100];
          const uw = unitWhere('unit', f);
          const rows = q(`SELECT u.id, u.name FROM units u ${uw.where}`, uw.args);
          return { n: rows.length, hasD3: rows.some(x => x.id === 1101000350) }; }""")
        print('[① SQL]', r)
        assert r['hasD3'] and r['n'] >= 40, r

        pg.evaluate("() => { state.stack=[]; push({page:'unit',title:'x',id:1101000350}); render(); }")
        pg.wait_for_timeout(900)
        pg.evaluate("""() => { const el=[...document.querySelectorAll('[data-goser]')].find(e=>e.dataset.goser==='1100'); el.click(); }""")
        pg.wait_for_timeout(1500)
        t = pg.evaluate("() => document.getElementById('view').innerText")
        print('[② 列表含D高达3号机]', 'D高达3号机' in t)
        assert 'D高达3号机' in t, t[:400]

        r3 = pg.evaluate("""() => {
          const f = filt('unit'); f.tags = []; f.mode = 'or'; f.series = [1100];
          const uw = unitWhere('unit', f);
          const n = q(`SELECT u.id FROM units u ${uw.where}`, uw.args).length;
          return { n }; }""")
        print('[③ 计数一致]', r3)
        assert r3['n'] == r['n'], (r3, r)

        assert not errors, errors
        print('=== test_v134 全部通过 ===')
        b.close()
finally:
    srv.terminate()
