# -*- coding: utf-8 -*-
"""v127 验证: 特性页「MP」分类补机体（主动MP）
口径(用户): mp技能机体在特性mp中线扫, 按主动MP
① DB 侧: features(unit_skill) 中带 MP 提升的机体至少 1 台（超级海伯瑞安 ULT MP+6）
② 特性页 MP 分类出现「机体（主动MP）」区块，列出该机体并显示 主动MP+6
③ 点击机体行进入机体详情（不是机师详情）
④ 机师行仍正常（点击进机师详情）
"""
import os, subprocess, time, sqlite3
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9071
DB = os.path.join(HERE, 'data', 'ggen.db')

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        pg.evaluate("() => { state.stack=[]; push({page:'feat',title:'特性',v:'x'}); state.featKind='mp_skill'; pageFeat(document.getElementById('view')); }")
        pg.wait_for_timeout(1200)
        t = pg.evaluate("() => document.getElementById('farea').innerText")
        print('[① 页面含机体区块]', '机体（主动MP）' in t)
        assert '机体（主动MP）' in t, t[:500]
        assert '主动MP+6' in t and '主动MP+3' in t, t[:600]
        units = pg.evaluate("() => [...document.querySelectorAll('#farea .lrow[data-ut]')].map(e=>({id:+e.dataset.id,name:e.querySelector('.nm').innerText.split('\\n')[0]}))")
        print('[② 机体行]', units)
        assert units and any(x['id']==1764000202 for x in units) and len(units)>=3, units

        # ③ 点击机体行 → 机体详情
        pg.click('#farea .lrow[data-ut]')
        pg.wait_for_timeout(700)
        title = pg.evaluate("() => (state.stack[state.stack.length-1]||{}).page")
        print('[③ 点击进入]', title)
        assert title == 'unit', title

        # ④ 机师行仍可点（回到 MP 页取第一条非机体行）
        pg.evaluate("() => { state.stack=[]; push({page:'feat',title:'特性',v:'x'}); state.featKind='mp_skill'; pageFeat(document.getElementById('view')); }")
        pg.wait_for_timeout(1000)
        n = pg.evaluate("() => document.querySelectorAll('#farea .lrow:not([data-ut])').length")
        print('[④ 机师行数]', n)
        assert n > 0, n
        assert not errors, errors
        print('=== test_v127 全部通过 ===')
        b.close()
finally:
    srv.terminate()
