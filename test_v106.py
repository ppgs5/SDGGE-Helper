# -*- coding: utf-8 -*-
"""v106 验证: 详情页特性芯片 支援攻击/支援防御 次数显示实际条目数(曾静态显示 +2)
① 迪奥·麦克斯韦尔(EW版) 1219000201 (1条52型: 「支援防御」+1次) → 特性卡显示 支援防御+1次, 不显示 支援防御+2
② 1705003100 (merge后2条) → 支援防御+2次
③ 对照: 特性页 support_def 列表仍只含 n>=2 驾驶员(迪奥不在列)
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9014
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

        def detail_feats(cid):
            pg.evaluate("(cid) => { state.stack = []; push({ page: 'char', title: 'x', id: cid }); render(); }", cid)
            pg.wait_for_timeout(700)
            return pg.evaluate("() => { const cs = [...document.querySelectorAll('#view .card')].find(el => el.querySelector('h4') && el.querySelector('h4').innerText.startsWith('特性')); return cs ? cs.innerText : null; }")

        f1 = detail_feats(1219000201)
        ok1 = f1 is not None and '支援防御+1次' in f1 and '支援防御+2' not in f1
        print('[① 迪奥EW(1条)]', (f1 or '').replace('\n', ' | ')[:110], '→', ok1)
        assert ok1, f1

        f2 = detail_feats(1705003100)
        ok2 = f2 is not None and '支援防御+2次' in f2
        print('[② 1705003100(2条)]', (f2 or '').replace('\n', ' | ')[:110], '→', ok2)
        assert ok2, f2

        pg.evaluate("() => { state.stack = []; push({ page: 'feat', title: '特性' }); render(); }")
        pg.wait_for_timeout(900)
        tab = pg.evaluate("""() => { const c = document.querySelector('[data-k="support_def"]'); if (!c) return null;
          c.click(); return 1; }""")
        pg.wait_for_timeout(1200)
        t = pg.evaluate("() => document.getElementById('farea').innerText")
        ok3 = tab and '迪奥·麦克斯韦尔 (EW版)' not in t and '支援防御' in t
        print('[③ 特性页 support_def 列表]', t.replace('\n', ' ')[:100], '→', ok3)
        assert ok3, t[:300]

        assert not errors, errors
        print('=== test_v106 全部通过 ===')
        b.close()
finally:
    srv.terminate()
