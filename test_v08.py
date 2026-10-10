# -*- coding: utf-8 -*-
"""v0.8 验证: EX角色能力描述完整性（多段/超一击EX1·EX2）、技能标签修正"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8833
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 400, 'height': 860})
        pg.set_default_timeout(240000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append('console.' + m.type + ': ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        print('[boot] ok')

        # 真·飞鸟 角色页
        pg.evaluate("() => push({page:'char', title:'真·飞鸟', id:1330000103})")
        pg.wait_for_timeout(600)
        txt = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        card = pg.evaluate("() => [...document.querySelectorAll('#view .card')].map(c => c.textContent.replace(/\\s+/g,' ').trim())")
        print('[char page]', txt[:150])
        for c in card:
            if '能力' in c[:4]: print('[能力 card]', c[:420])
        assert '超一击EX1' in txt and '必定发动爆击' in txt and '自身MP减少12' in txt, 'EX角色能力描述不完整'
        assert '搭乘「命运高达 (EX)」时' in txt, 'MP提升条件描述缺失'
        assert '闪避+100%' in txt, '摇摆闪避标签未修正'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/17a_char_ex_full.png')

        # 机体页能力（多段描述）抽检
        pg.evaluate("() => push({page:'unit', title:'命运高达 (EX)', id:1330000100})")
        pg.wait_for_timeout(500)
        utxt = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        print('[unit page]', utxt[:200])
        print('[unit 能力]', utxt[utxt.find('能力'):utxt.find('能力') + 260])
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/17b_unit_ex_full.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
