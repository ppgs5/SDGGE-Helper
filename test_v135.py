# -*- coding: utf-8 -*-
"""v135 验证: 特性页的系列筛选同样按「系列集」命中（与 v134 图鉴口径一致）
问题: featFilterMatch 只看 m.series(主系列)，D高达3号机 主系列 DOUBLE FAKE(1010)，
      在特性页按《机动战士高达 逆袭的夏亚》(1100) 筛选时会被漏掉
修复: 改为 seriesList(系列集) 命中即算，回退兼容单系列(驾驶员)
① 单元: unit 1101000350 在 series=[1100] 下 featFilterMatch = true
② 反例: 不在 1100 的机体(1001000100 高达, 主系列10) = false
③ 特性页「盾牌防御」列表在 series=[1100] 下出现 D高达3号机
④ 驾驶员单系列回退仍正常(char 的 m.series 判定)
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9103

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1200}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        r = pg.evaluate("""() => {
          const f = filt('feat'); f.tags = []; f.mode = 'or'; f.series = [1100]; f.terr = ''; f.rar = null; f.role = null;
          return { d3: featFilterMatch('unit', 1101000350), g: featFilterMatch('unit', 1001000100) }; }""")
        print('[① 单元]', r)
        assert r['d3'] is True, r
        assert r['g'] is False, r

        pg.evaluate("""() => {
          const f = filt('feat'); f.tags = []; f.mode = 'or'; f.series = [1100]; f.terr = ''; f.rar = null; f.role = null;
          state.stack=[]; push({page:'feat',title:'特性',v:'x'}); state.featKind='shield_defense'; pageFeat(document.getElementById('view'));
        }""")
        pg.wait_for_timeout(1500)
        t = pg.evaluate("() => document.getElementById('farea').innerText")
        print('[③ 特性页含D高达3号机]', 'D高达3号机' in t)
        assert 'D高达3号机' in t, t[:400]

        r4 = pg.evaluate("""() => {
          const cm = charMetaOf(1001000100);
          const f = filt('feat'); f.tags = []; f.series = [10];
          const hit10 = featFilterMatch('char', 1001000100);
          return { hasSeriesList: !!cm.seriesList, series: cm.series, hit10 }; }""")
        print('[④ 驾驶员回退]', r4)
        assert r4['hasSeriesList'] is False and r4['series'] == '机动战士高达', r4
        assert r4['hit10'] is True, r4

        assert not errors, errors
        print('=== test_v135 全部通过 ===')
        b.close()
finally:
    srv.terminate()
