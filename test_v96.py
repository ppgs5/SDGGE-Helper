# -*- coding: utf-8 -*-
"""v0.96 验证: 组队/排行首击卡顿修复(结果缓存 + 启动空闲预热)
① __prewarm() 离屏渲染组队/排行 → state.teamCache.G / state.rankCache 填充, 无页面错误
② 预热后首次点击组队 <1000ms(改动前约 4-6s); 二次进入 <1000ms
③ 改配置(star) → 缓存失效重算(耗时>1s)且 key 变化; 值随配置正确变化
④ 组队页正常渲染(元素数>50)
(自动化环境 navigator.webdriver=true 自动跳过启动预热, 测试用 __prewarm 手动触发)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 9001

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
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(800)
        assert pg.evaluate("() => !!window.__prewarm"), '缺少 __prewarm'

        # ① 预热填充(排行页为异步延迟计算 → 等待其完成)
        t0 = time.time()
        st = pg.evaluate("""() => { window.__prewarm();
          return { tc: !!(state.teamCache && state.teamCache.G) }; }""")
        print(f'[① 预热(组队同步) {time.time()-t0:.1f}s]', st)
        assert st['tc'], st
        pg.wait_for_timeout(5500)
        rc = pg.evaluate("() => !!state.rankCache")
        print('[① 排行异步预热完成]', rc)
        assert rc, 'rankCache 未填充'

        # ② 首击/二次组队耗时
        t0 = time.time()
        pg.evaluate("() => { state.stack=[]; setTab('team'); }")
        dt1 = (time.time() - t0) * 1000
        n1 = pg.evaluate("() => document.querySelectorAll('#view .trow, #view .card').length")
        print(f'[② 预热后首击组队 {dt1:.0f}ms, 元素 {n1}]')
        assert dt1 < 1000 and n1 > 50, (dt1, n1)
        pg.evaluate("() => { state.stack=[]; setTab('units'); }")
        pg.wait_for_timeout(200)
        t0 = time.time()
        pg.evaluate("() => { state.stack=[]; setTab('team'); }")
        dt2 = (time.time() - t0) * 1000
        print(f'[② 二次进入 {dt2:.0f}ms]')
        assert dt2 < 1000, dt2

        # ③ 改配置重算 + 正确变化
        k1 = pg.evaluate("() => state.teamCache.key")
        pg.evaluate("() => { state.stack=[]; setTab('units'); }")
        pg.wait_for_timeout(200)
        t0 = time.time()
        pg.evaluate("() => { state.team.star = (state.team.star === 0 ? 3 : 0); state.stack=[]; setTab('team'); }")
        dt3 = (time.time() - t0) * 1000
        k2 = pg.evaluate("() => state.teamCache.key")
        print(f'[③ 改star重算 {dt3:.0f}ms, key变化 {k1 != k2}]')
        assert dt3 > 1000 and k1 != k2, (dt3, k1 == k2)
        # 改回 → 再点应再度重算(单槽缓存, 无错误即可)
        pg.evaluate("() => { state.stack=[]; setTab('units'); state.team.star = (state.team.star === 0 ? 3 : 0); state.stack=[]; setTab('team'); }")
        n3 = pg.evaluate("() => document.querySelectorAll('#view .trow, #view .card').length")
        print(f'[③ 改回star后元素 {n3}]')
        assert n3 > 50, n3

        # ④ 排行
        pg.wait_for_timeout(200)
        t0 = time.time()
        pg.evaluate("() => { state.stack=[]; setTab('rank'); }")
        dtr = (time.time() - t0) * 1000
        pg.wait_for_timeout(600)
        n4 = pg.evaluate("() => document.querySelectorAll('#rlist .rrow').length")
        print(f'[④ 排行首击 {dtr:.0f}ms, 行 {n4}]')
        assert dtr < 1500 and n4 > 3, (dtr, n4)
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v96 全部通过 ===')
