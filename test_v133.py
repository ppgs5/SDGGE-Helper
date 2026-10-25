# -*- coding: utf-8 -*-
"""v133 验证: 机体图鉴详情把「标签」与「系列」分开显示
① 详情页同时出现「标签:」「系列:」两行，顺序在机体名/型号之下
② D高达3号机(EX): 标签行有 宇宙世纪系列/高达/…，系列行有《DOUBLE FAKE UNDER THE GUNDAM》(主系列,高亮)《机动战士高达 逆袭的夏亚》
③ 点系列 chip → 图鉴列表按该系列筛选(series=[1010])，切到机体页
④ 点标签 chip → 仍按标签筛选(tags 非空, series 清空)
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9099

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1000}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        pg.evaluate("() => { state.stack=[]; push({page:'unit',title:'x',id:1101000350}); render(); }")
        pg.wait_for_timeout(900)
        r = pg.evaluate("""() => {
          const v = document.getElementById('view');
          const txt = v.innerText;
          const tags = [...v.querySelectorAll('[data-gotag]')].map(e => e.innerText.replace('›','').trim());
          const sers = [...v.querySelectorAll('[data-goser]')].map(e => ({ id: e.dataset.goser, name: e.innerText.replace('《','').replace('》›','').trim(), on: e.classList.contains('on') }));
          return { hasTag: txt.includes('标签:'), hasSer: txt.includes('系列:'), tags, sers }; }""")
        print('[① 分区]', r['hasTag'], r['hasSer'], '| 标签数', len(r['tags']), '| 系列', r['sers'])
        assert r['hasTag'] and r['hasSer'], r
        assert r['tags'][:2] == ['宇宙世纪系列', '高达'], r['tags']
        names = [x['name'] for x in r['sers']]
        assert 'DOUBLE FAKE UNDER THE GUNDAM' in names, names
        assert any(x['on'] for x in r['sers']), r['sers']       # 主系列高亮

        # ③ 点系列
        pg.evaluate("() => { document.querySelector('[data-goser]').click(); }")
        pg.wait_for_timeout(1000)
        s1 = pg.evaluate("() => ({ tab: state.tab, series: filt('unit').series, tags: filt('unit').tags })")
        print('[③ 点系列]', s1)
        assert s1['tab'] == 'units' and s1['series'] == [1010] and s1['tags'] == [], s1

        # ④ 点标签
        pg.evaluate("() => { state.stack=[]; push({page:'unit',title:'x',id:1101000350}); render(); }")
        pg.wait_for_timeout(800)
        pg.evaluate("() => { document.querySelector('[data-gotag]').click(); }")
        pg.wait_for_timeout(900)
        s2 = pg.evaluate("() => ({ tab: state.tab, series: filt('unit').series, tags: filt('unit').tags })")
        print('[④ 点标签]', s2)
        assert s2['tab'] == 'units' and s2['series'] == [] and len(s2['tags']) == 1, s2

        assert not errors, errors
        print('=== test_v133 全部通过 ===')
        b.close()
finally:
    srv.terminate()
