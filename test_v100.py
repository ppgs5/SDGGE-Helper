# -*- coding: utf-8 -*-
"""v0.100 验证: 机体图鉴新增「装置」筛选列表
① 机体页出现「装置」按钮
② 点击弹出装置列表(含数量)
③ 选择某项 → 列表按该装置筛选(命中数变化且 chip 显示当前装置)
④ 选「全部」→ 清除筛选
"""
import subprocess, time
from playwright.sync_api import sync_playwright
PORT=9014
srv=subprocess.Popen(['python3','-m','http.server',str(PORT)],cwd='/root/workspace/ggen_app/web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1.2)
try:
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={'width':420,'height':900}); pg.set_default_timeout(120000)
        pg.add_init_script("window.Android={dbInfo:()=>'{}',listPatches:()=>'[]'};")
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash',state='hidden'); pg.wait_for_timeout(1200)
        pg.evaluate("() => { state.stack=[]; state.unitKind='unit'; render(); }")
        pg.wait_for_timeout(800)
        has=pg.evaluate("() => !!document.getElementById('kmech')")
        print('[① 装置按钮]', has); assert has
        base=pg.evaluate("() => document.getElementById('hit').textContent")
        pg.click('#kmech'); pg.wait_for_timeout(500)
        n=pg.evaluate("() => document.querySelectorAll('#mechpick [data-mech]').length")
        print('[② 装置项数]', n); assert n>2
        pg.evaluate("() => { const els=[...document.querySelectorAll('#mechpick [data-mech]')]; const t=els.find(e=>e.dataset.mech==='变形机构'); t.click(); }")
        pg.wait_for_timeout(900)
        after=pg.evaluate("() => document.getElementById('hit').textContent")
        label=pg.evaluate("() => document.getElementById('kmech').textContent")
        print('[③ 筛选后]', base, '→', after, '| chip:', label)
        assert after != base and '变形' in label
        pg.click('#kmech'); pg.wait_for_timeout(400)
        pg.evaluate("() => document.querySelector('#mechpick [data-mech=\\\"\\\"]').click()")
        pg.wait_for_timeout(800)
        cleared=pg.evaluate("() => document.getElementById('hit').textContent")
        print('[④ 清除后]', cleared)
        assert cleared == base
        print('=== test_v100 通过 ===')
        b.close()
finally:
    srv.terminate()
