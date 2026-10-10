# -*- coding: utf-8 -*-
"""v0.20 验证: 各页图标稀有度 / 防御目标驾驶员头像尺寸 / 防御目标buff后防御+HP显示"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8883
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

        # ---------- 1. 计算页 TOP10 稀有度 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '00强化模组'); pg.wait_for_timeout(600)
        pg.click("#pkl [data-pick='1370005950']"); pg.wait_for_timeout(2500)
        row = pg.evaluate("() => { const e = document.querySelector('[data-pid]'); return e ? e.textContent.replace(/\\s+/g,' ') : '' }")
        print('[计算TOP10]', row[:110])
        assert any(t in row for t in ('UR', 'SSR', 'SR')), '计算页TOP10缺稀有度'

        # ---------- 2. 排行/组队 稀有度（回归确认） ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('#rlist .rrow'); pg.wait_for_timeout(2600)
        r1 = pg.evaluate("() => document.querySelector('#rlist .rrow').textContent.replace(/\\s+/g,' ').slice(0,90)")
        assert any(t in r1 for t in ('UR', 'SSR', 'SR')), '排行缺稀有度'
        print('[排行]', r1[:70])

        # ---------- 3. 组队: 防御机体卡（头像尺寸+防御/耐久/eHP） ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow'); pg.wait_for_timeout(2600)
        # 组队输出行稀有度
        teamr = pg.evaluate("() => document.querySelector('#tarea .trow .nm').textContent.replace(/\\s+/g,' ').slice(0,60)")
        print('[组队行]', teamr)
        assert any(t in teamr for t in ('UR', 'SSR', 'SR')), '组队行缺稀有度'
        pg.click('#dpick'); pg.wait_for_timeout(600)
        pg.fill('#pk', '独角兽高达'); pg.wait_for_timeout(600)
        pg.click('#pkl [data-dpick]'); pg.wait_for_timeout(800)
        pg.click('#pkl [data-dpickc]'); pg.wait_for_timeout(2500)
        card = pg.evaluate("() => document.getElementById('dpick').textContent.replace(/\\s+/g,' ')")
        print('[防御机体卡]', card[:140])
        assert '耐久' in card and 'eHP' in card, '防御机体卡缺耐久/eHP'
        sizes = pg.eval_on_selector_all('#dpick .dico img', "els => els.map(e => e.clientWidth)")
        print('[头像宽]', sizes)
        assert sizes and all(w <= 60 for w in sizes), f'防御目标头像过大: {sizes}'
        # buff 后数值
        pg.fill('#tdefup', '50'); pg.dispatch_event('#tdefup', 'change'); pg.wait_for_timeout(2500)
        card2 = pg.evaluate("() => document.getElementById('dpick').textContent.replace(/\\s+/g,' ')")
        print('[+50%]', card2[card2.find('防御'):card2.find('防御') + 80])
        assert '→' in card2 and '全能力50%' in card2, 'buff后防御值未显示'
        best = pg.evaluate("() => document.getElementById('tarea').textContent.replace(/\\s+/g,' ').slice(0,160)")
        print('[最大伤害卡]', best[:150])
        assert '耐久' in best and 'eHP' in best and '→' in best and '全能力50%' in best, '最大伤害卡未显示buff后数值'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/30a_def_buffed.png')

        # ---------- 4. 特性页稀有度 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow')
        ft = pg.evaluate("() => document.querySelector('#farea .lrow .nm').textContent.replace(/\\s+/g,' ')")
        print('[特性页行]', ft[:70])
        assert any(t in ft for t in ('UR', 'SSR', 'SR')), '特性页缺稀有度'

        # ---------- 5. 先发攻击按稀有度降序 ----------
        pg.click("[data-k='preemptive']"); pg.wait_for_timeout(700)
        order = pg.eval_on_selector_all('#farea .lrow .rar', "els => els.map(e => e.textContent.trim())")
        rank = {'UR': 5, 'SSR': 4, 'SR': 3, 'R': 2, 'N': 1}
        vals = [rank.get(x, 0) for x in order]
        print('[先发稀有度序列]', order[:12])
        assert vals == sorted(vals, reverse=True), f'未按稀有度降序: {order[:12]}'

        # ---------- 6. 机体页: 对中防目标(20k)最大伤害 + 驾驶员 ----------
        pg.evaluate("() => push({page:'unit', title:'x', id:1200003950})")   # 神高达 (EX)
        pg.wait_for_timeout(4000)
        ub = pg.evaluate("() => { const e = document.getElementById('ubb'); return e ? e.textContent.replace(/\\s+/g,' ') : '' }")
        print('[机体页最大伤害]', ub[:110])
        assert ub and '计算中' not in ub and '—' != ub.strip(), '机体页最大伤害卡未出结果'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/30b_unit_best.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
