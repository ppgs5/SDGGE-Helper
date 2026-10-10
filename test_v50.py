# -*- coding: utf-8 -*-
"""v0.50 验证: 全部头像/零件图片打包为本地离线资源(web/img) ①与数据库图标全集一一对应 ②断网(仅localhost)下各页面图片正常显示 ③无任何图片请求打到在线CDN"""
import os, re, subprocess, time, sqlite3
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- ① 文件级: 图片清单齐全 ----------
db = sqlite3.connect(os.path.join(HERE, 'data', 'ggen.db'))
need = set()
for t in ('units', 'characters', 'supporters'):
    for (ic,) in db.execute(f"SELECT DISTINCT icon FROM {t} WHERE icon IS NOT NULL AND icon!=''"):
        need.add(f'thumb/thum_{ic}.webp')
for (ic,) in db.execute("SELECT DISTINCT icon FROM mods WHERE icon IS NOT NULL AND icon!=''"):
    need.add(f'item/{ic}.webp')
missing = [r for r in need if not os.path.exists(os.path.join(HERE, 'web', 'img', r))]
tot = sum(os.path.getsize(os.path.join(HERE, 'web', 'img', r)) for r in need if os.path.exists(os.path.join(HERE, 'web', 'img', r)))
print(f'[离线图] 需 {len(need)} 张 · 缺 {len(missing)} · 合计 {tot / 1048576:.1f}MB')
assert not missing, f'缺图: {missing[:10]}'
assert tot > 10_000_000, '图片总量异常'

PORT = 8994
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
cdn_hits = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 400, 'height': 860})
        pg.set_default_timeout(240000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append('console.' + m.type + ': ' + m.text) if m.type == 'error' else None)

        def route_cb(route):
            if 'kusoge' in route.request.url:
                cdn_hits.append(route.request.url)
            route.abort()
        pg.route(re.compile(r'^https?://(?!127\.0\.0\.1)'), route_cb)     # 除本机外全部断网

        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        print('[boot] ok (断网模式)')

        # ---------- ② 图鉴-机体 头像 ----------
        pg.wait_for_timeout(1500)
        chk = pg.evaluate("""() => {
          const imgs = [...document.querySelectorAll('#listarea img')].slice(0, 12);
          return {n: imgs.length, ok: imgs.filter(im => im.complete && im.naturalWidth > 0).length,
                  local: imgs.every(im => (im.getAttribute('src') || '').startsWith('img/'))};
        }""")
        print('[图鉴-机体 头像]', chk)
        assert chk['n'] >= 8 and chk['ok'] == chk['n'] and chk['local'], f'机体头像应本地加载: {chk}'

        # 驾驶员
        pg.click('[data-k="char"]'); pg.wait_for_timeout(1200)
        chk2 = pg.evaluate("""() => {
          const imgs = [...document.querySelectorAll('#listarea img')].slice(0, 8);
          return {n: imgs.length, ok: imgs.filter(im => im.complete && im.naturalWidth > 0).length};
        }""")
        print('[图鉴-驾驶员 头像]', chk2)
        assert chk2['n'] >= 5 and chk2['ok'] == chk2['n'], f'驾驶员头像应本地加载: {chk2}'

        # 零件(道具图 item/)
        pg.click('[data-k="mod"]'); pg.wait_for_timeout(1500)
        chk3 = pg.evaluate("""() => {
          const imgs = [...document.querySelectorAll('#listarea img')].slice(0, 8);
          return {n: imgs.length, ok: imgs.filter(im => im.complete && im.naturalWidth > 0).length,
                  item: imgs.every(im => (im.getAttribute('src') || '').startsWith('img/item/'))};
        }""")
        print('[图鉴-零件 道具图]', chk3)
        assert chk3['n'] >= 5 and chk3['ok'] == chk3['n'] and chk3['item'], f'零件图应本地加载: {chk3}'

        # 机体详情页
        pg.evaluate("() => push({page:'unit', title:'x', id:1001000150})"); pg.wait_for_timeout(2500)
        chk4 = pg.evaluate("""() => {
          const im = document.querySelector('#view .dhead img');
          return im ? {ok: im.complete && im.naturalWidth > 0, src: im.getAttribute('src')} : null;
        }""")
        print('[机体详情 头像]', chk4)
        assert chk4 and chk4['ok'] and chk4['src'].startswith('img/'), f'详情页头像应本地加载: {chk4}'

        # 战舰页
        pg.click('[data-tab="units"]'); pg.wait_for_timeout(400)
        pg.click('[data-k="supp"]'); pg.wait_for_timeout(1200)
        chk5 = pg.evaluate("""() => {
          const imgs = [...document.querySelectorAll('#listarea img')].slice(0, 6);
          return {n: imgs.length, ok: imgs.filter(im => im.complete && im.naturalWidth > 0).length};
        }""")
        print('[图鉴-战舰 头像]', chk5)
        assert chk5['n'] >= 4 and chk5['ok'] == chk5['n'], f'战舰头像应本地加载: {chk5}'

        assert cdn_hits == [], f'断网下不应有CDN请求: {cdn_hits[:3]}'
        pg.screenshot(path=os.path.join(HERE, 'shots_app', '56a_offline.png'))
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
