# -*- coding: utf-8 -*-
"""v141 验证: 「射程加」只统计有射程被动的组合；开关打开时只保留「被动+主动技能」同时存在的组合；并显示最大射程
① 默认(开关关): 列表 9 位，全部含「被动」，行内含「最大射程 N」
② 打开「主动技能射程+1」: 列表为 0（当前数据里没有技师同时具备射程被动与射程主动技能）
③ 开关存在且可切换
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9117

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1200}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        def page(rgS):
            pg.evaluate("""([rgS]) => { state.featRgS=rgS; state.stack=[]; push({page:'feat',title:'特性',v:'x'});
              state.featKind='range_up'; pageFeat(document.getElementById('view')); }""", [rgS])
            pg.wait_for_timeout(1500)
            return pg.evaluate("""() => ({ text: document.getElementById('farea').innerText,
              rows: [...document.querySelectorAll('#farea .lrow')].map(e=>e.innerText.replace(/\\n/g,' | ')),
              rgs: document.querySelectorAll('#farea #rgs').length })""")

        off = page(False)
        print('[① 开关关]', len(off['rows']), '行 | #rgs', off['rgs'])
        assert off['rgs'] == 1, off['rgs']
        assert len(off['rows']) == 9, len(off['rows'])
        assert all('被动' in r for r in off['rows']), off['rows']
        assert all('最大射程' in r for r in off['rows']), off['rows']

        on = page(True)
        print('[② 开关开]', len(on['rows']), '行')
        assert len(on['rows']) == 0, on['rows']

        assert not errors, errors
        print('=== test_v141 全部通过 ===')
        b.close()
finally:
    srv.terminate()
