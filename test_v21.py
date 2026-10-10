# -*- coding: utf-8 -*-
"""v0.21 验证: 先发攻击显示射程 / 防御目标改为全能力增加(buff后HP) / 防御选择器稀有度"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8891
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

        # ---------- 1. 先发攻击显示射程 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow')
        pg.click("[data-k='preemptive']"); pg.wait_for_timeout(700)
        ft = pg.evaluate("() => document.getElementById('farea').textContent.replace(/\\s+/g,' ')")
        print('[先发行]', ft[:150])
        assert '射程' in ft or 'MAP' in ft, '先发攻击未显示武器射程'

        # ---------- 2. 组队: 全能力增加 + buff 后 HP ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow'); pg.wait_for_timeout(2600)
        labels = pg.eval_on_selector_all('.chips .hint', "els => els.map(e=>e.textContent.trim())")
        print('[hint标签]', labels)
        assert '全能力增加' in labels, '标签未改为全能力增加'
        # 选择防御机体
        pg.click('#dpick'); pg.wait_for_timeout(600)
        pg.fill('#pk', '独角兽高达'); pg.wait_for_timeout(600)
        # 选择器稀有度
        rr = pg.eval_on_selector_all('#pkl .trow2 .rar', "els => els.slice(0,3).map(e=>e.textContent.trim())")
        print('[选择器稀有度]', rr)
        assert rr, '防御机体选择器缺稀有度'
        pg.click('#pkl [data-dpick]'); pg.wait_for_timeout(800)
        pg.click('#pkl [data-dpickc]'); pg.wait_for_timeout(2500)
        card = pg.evaluate("() => document.getElementById('dpick').textContent.replace(/\\s+/g,' ')")
        print('[防御卡]', card[:150])
        assert '耐久' in card and 'eHP' in card, '缺耐久/eHP'
        pg.fill('#tdefup', '50'); pg.dispatch_event('#tdefup', 'change'); pg.wait_for_timeout(2600)
        card2 = pg.evaluate("() => document.getElementById('dpick').textContent.replace(/\\s+/g,' ')")
        print('[+50%]', card2[card2.find('防御'):card2.find('防御') + 100])
        seg = card2[card2.find('防御'):card2.find('防御') + 100]
        assert '（+全能力50%）' in seg, '未显示全能力增加'
        assert seg.count('→') >= 2, '防御与耐久都应有buff后数值(→)'
        best = pg.evaluate("() => document.getElementById('tarea').textContent.replace(/\\s+/g,' ').slice(0,200)")
        print('[最大卡]', best[:190])
        assert '全能力50%' in best and '→' in best, '最大伤害卡未显示全能力buff'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/31a_team_allpct.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
