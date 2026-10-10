# -*- coding: utf-8 -*-
"""v101 验证: 更新中心改版(去自定义更新源/修复「检测中」) + 关于开源地址 + 版本 v0.101 比较
① 无 #upbase 输入框、无「自动线路：…」说明行; 标题「在线更新 · 数据仓库」
② 关于卡: 作者 DeepSeek + 开源地址 github.com/ppgs5/SDGGE-Helper(点击→Android.openUrl)
③ APP 版本: stub 当前 0.101 vs mock 9.9.9 → 可更新+按钮 → downloadApk(url,mirror,'9.9.9') → 进度/安装
④ mock 改 0.100(<0.101) → 「已是最新」且说明不再停在「检测中…」(v0.96 bug 修复)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
MOCK = '/tmp/ggen_app_mock'
PORT, MPORT = 9006, 9007

os.makedirs(MOCK, exist_ok=True)

def write_mock(ver):
    open(os.path.join(MOCK, 'app_version.json'), 'w', encoding='utf-8').write(
        '{"version":"%s","size":12345678,"note":"测试版","apk_url":"https://example.com/apk",'
        '"apk_mirror":"https://mirror.example.com/apk"}' % ver)
write_mock('9.9.9')

import functools, http.server, threading
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
class _H(http.server.SimpleHTTPRequestHandler):   # mock 需带 CORS
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()
    def log_message(self, *a): pass
_msrv = http.server.ThreadingHTTPServer(('127.0.0.1', MPORT), functools.partial(_H, directory=MOCK))
threading.Thread(target=_msrv.serve_forever, daemon=True).start()
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(120000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.add_init_script("""
          window.__UPD_AUTO = ['http://127.0.0.1:9007/'];
          window.Android = {
            dbInfo: () => '{}', listPatches: () => '[]',
            appInfo: () => JSON.stringify({versionName: '0.101', versionCode: 101}),
            downloadApk: (u, u2, v) => { window.__dl = [u, u2, v]; window.__st = {state: 'downloading', pct: 5}; return true; },
            apkState: () => JSON.stringify(window.__st || {state: 'idle'}),
            openUrl: (u) => { window.__opened = u; }
          };
        """)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(1000)
        pg.evaluate("() => { state.stack = []; push({page: 'update', title: '更新中心'}); }")
        pg.wait_for_timeout(2200)

        # ① 去自定义更新源 + 标题
        r = pg.evaluate("""() => ({ upbase: !!document.getElementById('upbase'),
          autoLine: document.body.innerText.includes('自动线路：'), title: document.body.innerText.includes('在线更新 · 数据仓库') })""")
        print('[① 去自定义更新源]', r)
        assert not r['upbase'] and not r['autoLine'] and r['title'], r
        print('[① 无输入框/说明行, 标题=在线更新 · 数据仓库 通过]')

        # ② 关于: 作者 + 开源地址(点击→openUrl)
        t = pg.evaluate("() => document.body.innerText")
        assert 'DeepSeek' in t and 'github.com/ppgs5/SDGGE-Helper' in t, t[-300:]
        pg.evaluate("() => document.getElementById('osurl').click()")
        pg.wait_for_timeout(400)
        op = pg.evaluate("() => window.__opened")
        print('[② 开源地址点击]', op)
        assert op == 'https://github.com/ppgs5/SDGGE-Helper', op
        print('[② 关于(作者 DeepSeek + 开源地址可点) 通过]')

        # ③ 可更新流程
        r = pg.evaluate("""() => ({ ver: document.getElementById('appver').textContent,
          nw: document.getElementById('appnew').textContent })""")
        print('[③ APP 版本]', r)
        assert r['ver'] == 'v0.101' and 'v9.9.9' in r['nw'] and '可更新' in r['nw'], r
        pg.evaluate("() => document.getElementById('appupd').click()")
        pg.wait_for_timeout(500)
        dl = pg.evaluate("() => window.__dl")
        assert dl == ['https://example.com/apk', 'https://mirror.example.com/apk', '9.9.9'], dl
        pg.evaluate("() => { window.__st = {state: 'downloading', pct: 42}; }")
        pg.wait_for_timeout(1200)
        assert '42%' in pg.evaluate("() => document.getElementById('appnote').textContent")
        pg.evaluate("() => { window.__st = {state: 'installing', pct: 100}; }")
        pg.wait_for_timeout(1200)
        assert '安装' in pg.evaluate("() => document.getElementById('appnote').textContent")
        print('[③ 可更新→下载→安装链路 通过]')

        # ④ 已是最新(不再"检测中") — mock 改 0.100
        write_mock('0.100')
        pg.evaluate("() => { state.stack = []; push({page: 'update', title: '更新中心'}); }")
        pg.wait_for_timeout(2500)
        r = pg.evaluate("""() => ({ nw: document.getElementById('appnew').textContent, note: document.getElementById('appnote').textContent })""")
        print('[④ 已是最新分支]', r)
        assert '已是最新' in r['nw'] and '检测中' not in r['note'] and r['note'], r
        print('[④ 0.100<0.101 → 已是最新, 说明不再是「检测中…」 通过]')
        b.close()
finally:
    srv.terminate(); _msrv.shutdown()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v101 全部通过 ===')
