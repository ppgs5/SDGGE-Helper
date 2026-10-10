# -*- coding: utf-8 -*-
"""v0.97 验证: 更新中心 — 去掉 soshage 遗留(标题/旧地址) + APP 自更新按钮(下载安装) + 作者署名
① 标题=「在线更新 · 数据仓库（镜像可配置）」不含 soshage; 底部「关于」含 作者 DeepSeek
② 遗留的 soshage 自定义地址自动清除(输入框为空 + localStorage 清空)
③ APP 版本行: 当前 v0.96(stub桥) vs 清单 v9.9.9 → 「可更新」+ 按钮出现
④ 点按钮 → Android.downloadApk(url, mirror, ver) 调用参数正确; 进度 42% 显示; installing → 完成提示
(无头浏览器用 init-script 注入 window.Android 桩 + 本地 mock app_version.json)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
MOCK = '/tmp/ggen_app_mock'
PORT, MPORT = 9004, 9005

os.makedirs(MOCK, exist_ok=True)
open(os.path.join(MOCK, 'app_version.json'), 'w', encoding='utf-8').write(
    '{"version":"9.9.9","size":12345678,"note":"测试版","apk_url":"https://example.com/apk",'
    '"apk_mirror":"https://mirror.example.com/apk"}')

import functools, http.server, threading
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
class _H(http.server.SimpleHTTPRequestHandler):   # mock 需带 CORS(真实镜像 github/jsDelivr 均有)
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
          try { localStorage.setItem('ggen_update_base', 'https://soshage.com/gget/zh-CN/weapon'); } catch (e) {}
          window.__UPD_AUTO = ['http://127.0.0.1:9005/'];
          window.Android = {
            dbInfo: () => '{}', listPatches: () => '[]',
            appInfo: () => JSON.stringify({versionName: '0.96', versionCode: 96}),
            downloadApk: (u, v) => { window.__dl = [u, v]; window.__st = {state: 'downloading', pct: 5}; return true; },
            apkState: () => JSON.stringify(window.__st || {state: 'idle'})
          };
        """)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(1000)
        pg.evaluate("() => { state.stack = []; push({page: 'update', title: '更新中心'}); }")
        pg.wait_for_timeout(2000)

        # ① 标题/作者
        t = pg.evaluate("() => document.querySelector('#view').innerText")
        print('[① 标题含数据仓库]', '数据仓库' in t, '| 不含soshage:', 'soshage' not in t.split('数据来源')[0])
        assert '在线更新 · 数据仓库' in t and 'DeepSeek' in t, t[:120]
        assert 'soshage（域名可配置）' not in t
        print('[① 标题(去 soshage) + 作者 DeepSeek 通过]')

        # ② (v0.101 起已去掉自定义更新源输入框) 断言不存在 + 遗留键被清理
        r = pg.evaluate("() => ({ has: !!document.getElementById('upbase'), ls: localStorage.getItem('ggen_update_base'), autoLine: document.body.innerText.includes('自动线路：') })")
        print('[② 自定义更新源已移除]', r)
        assert not r['has'] and r['ls'] is None and not r['autoLine'], r
        print('[② 输入框/自动线路说明行已移除, 遗留键已清理 通过]')

        # ③ APP 版本检测(exists→v9.9.9 可更新)
        r = pg.evaluate("""() => ({ ver: document.getElementById('appver').textContent,
          nw: document.getElementById('appnew').textContent, btn: getComputedStyle(document.getElementById('appupd')).display })""")
        print('[③ APP 版本]', r)
        assert r['ver'] == 'v0.96' and 'v9.9.9' in r['nw'] and '可更新' in r['nw'] and r['btn'] != 'none', r
        print('[③ APP 版本行(当前 v0.96 → v9.9.9 可更新) 通过]')

        # ④ 点击下载 → 桥参数 + 进度 + 完成
        pg.evaluate("() => document.getElementById('appupd').click()")
        pg.wait_for_timeout(500)
        dl = pg.evaluate("() => window.__dl")
        print('[④ downloadApk 参数]', dl)
        import json as _json
        assert dl == [_json.dumps(['https://example.com/apk', 'https://mirror.example.com/apk'], separators=(',', ':')), '9.9.9'], dl
        pg.evaluate("() => { window.__st = {state: 'downloading', pct: 42}; }")
        pg.wait_for_timeout(1200)
        note = pg.evaluate("() => document.getElementById('appnote').textContent")
        print('[④ 进度提示]', note[:40])
        assert '42%' in note, note
        pg.evaluate("() => { window.__st = {state: 'installing', pct: 100}; }")
        pg.wait_for_timeout(1200)
        note = pg.evaluate("() => document.getElementById('appnote').textContent")
        print('[④ 完成提示]', note[:40])
        assert '安装' in note, note
        print('[④ APP 下载→进度→系统安装 链路(桥调用) 通过]')
        b.close()
finally:
    srv.terminate(); _msrv.shutdown()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v97 全部通过 ===')
