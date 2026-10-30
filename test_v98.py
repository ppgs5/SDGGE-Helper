# -*- coding: utf-8 -*-
"""v0.98 验证: 武器图鉴射程筛选(全部/1/2/3/4/5/MAP, 可多选) + 武器详情「所属机体」跳转 + 详情显示 MAP 形状
① 武器页出现射程筛选行(7 个按钮)
② 点「5」→ 列表只剩射程含 5 的武器; 点「MAP」叠加 → 出现 MAP 武装; 点「全部」清空
③ 武器详情出现「所属机体」按钮, 点击进入该机体页
④ MAP 武器详情出现「MAP 形状」卡片
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 9008

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(120000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.add_init_script("window.Android = { dbInfo: () => '{}', listPatches: () => '[]' };")
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(1200)

        # ① 射程筛选行
        pg.evaluate("() => { state.stack = []; state.unitKind = 'weapon'; render(); }")
        pg.wait_for_timeout(800)
        n = pg.evaluate("() => document.querySelectorAll('#rangef [data-krange]').length")
        print('[① 射程筛选按钮数]', n)
        assert n == 7, n
        print('[① 射程筛选行(全部/1/2/3/4/5/MAP) 通过]')

        # ② 单选 5
        pg.click('#rangef [data-krange="5"]')
        pg.wait_for_timeout(900)
        w5 = pg.evaluate("() => (state.wRange||[]).slice()")
        hit5 = pg.evaluate("() => document.getElementById('hit').textContent")
        print('[② 选5]', w5, hit5)
        assert w5 == ['5'], w5

        # ② 叠加 MAP
        pg.click('#rangef [data-krange="map"]')
        pg.wait_for_timeout(900)
        wm = pg.evaluate("() => (state.wRange||[]).slice()")
        hitm = pg.evaluate("() => document.getElementById('hit').textContent")
        print('[② 叠加MAP]', wm, hitm)
        assert set(wm) == {'5', 'map'}, wm

        # ② 全部清空
        pg.click('#rangef [data-krange="all"]')
        pg.wait_for_timeout(900)
        wa = pg.evaluate("() => (state.wRange||[]).slice()")
        print('[② 全部]', wa)
        assert wa == [], wa
        print('[② 多选/清空 通过]')

        # ③④ 武器详情: 所属机体 + MAP 形状
        wid = pg.evaluate("() => q1(\"SELECT id FROM weapons WHERE type=3 LIMIT 1\").id")
        pg.evaluate("(id) => { state.stack = []; push({ page: 'weapon', title: 'MAP武器', id }); }", wid)
        pg.wait_for_timeout(900)
        hasBtn = pg.evaluate("() => !!document.getElementById('gounit')")
        hasMap = pg.evaluate("() => document.querySelector('#view').innerText.includes('MAP 形状')")
        print('[③ 所属机体按钮]', hasBtn, '| [④ MAP 形状卡片]', hasMap)
        assert hasBtn and hasMap

        pg.click('#gounit')
        pg.wait_for_timeout(900)
        onUnit = pg.evaluate("() => { const s = state.stack[state.stack.length-1]; return s && s.page; }")
        print('[③ 跳转后页面]', onUnit)
        assert onUnit == 'unit', onUnit
        print('[③ 所属机体跳转 通过]')
        b.close()
    assert not errors, errors[:3]
    print('=== test_v98 全部通过 ===')
finally:
    srv.terminate()
