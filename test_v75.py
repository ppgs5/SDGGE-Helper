# -*- coding: utf-8 -*-
"""v0.75 验证: 组队页 支援型(支援攻击机体)/防御型输出/防御型eHP 三个列表 前5→前10
① 三个区块标题 TOP5→TOP10; 各渲染 10 行
② 支援型行保留增伤/降防并集显示(v0.72特性)
③ 攻击型 TOP10 / 攻击型×支援型驾驶员 TOP10 不变
回归: 仅最新版 —— test_v73 已全过(用户口径「仅回归最后一个版本」)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8975

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
        pg.evaluate("() => { state.stack = []; setTab('team'); }")
        pg.wait_for_timeout(4500)

        r = pg.evaluate("""() => {
          const cards = [...document.querySelectorAll('#tarea .card')].map(c => ({
            title: (c.querySelector('h4') || {}).textContent || '',
            rows: c.querySelectorAll('.trow').length,
            text: c.textContent.replace(/\\s+/g, ' ').slice(0, 80)
          }));
          return cards.filter(c => c.title.includes('TOP') || c.title.includes('对防御目标'));
        }""")
        print('[组队区块]')
        for c in r: print('  ', c['title'][:46], '| rows =', c['rows'])
        def find(kw):
            return next((c for c in r if kw in c['title']), None)
        sup = find('支援型 TOP10'); dout = find('防御型 TOP10 · 输出'); dehp = find('防御型 TOP10 · 有效耐久')
        assert sup and sup['rows'] == 10, sup
        assert dout and dout['rows'] == 10, dout
        assert dehp and dehp['rows'] == 10, dehp
        atk10 = find('攻击型 TOP10 · 单发伤害'); atksup = find('攻击型 × 支援型驾驶员 TOP10')
        assert atk10 and atk10['rows'] == 10 and atksup and atksup['rows'] == 10, (atk10, atksup)
        assert not any('TOP5' in c['title'] for c in r), r
        print('[① 三个列表前10 + 标题TOP10] 通过')
        # ② 支援型行含增伤/降防并集(如 降防35% 1-5 / 特殊-40% 1-4)
        import re as _re
        body = pg.evaluate("() => { const c=[...document.querySelectorAll('#tarea .card')].find(x => x.querySelector('h4') && x.querySelector('h4').textContent.includes('支援型 TOP10')); return c ? c.textContent.replace(/\\s+/g,' ') : ''; }")
        assert _re.search(r'(光束|物理|特殊)-\d+%|降防\d+%', body), body[:200]
        print('[② 支援型行特效并集保留] 通过')
        print('[③ 攻击型区块不变(均10行)] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v75 全部通过 ===')
