# -*- coding: utf-8 -*-
"""v0.10 验证: 计算页 驾驶员伤害TOP10"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8837
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

        # 神高达(EX) 不选驾驶员 → 应出现 TOP10 列表
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(200)
        pg.click('#picku'); pg.fill('#pk', '神高达'); pg.wait_for_timeout(500)
        t0 = time.time()
        pg.click("#pkl [data-pick='1200003950']"); pg.wait_for_timeout(800)
        rows = pg.evaluate("""() => [...document.querySelectorAll('#view .card')].map(c => ({
            h: (c.querySelector('h4')||{}).textContent || '', n: c.querySelectorAll('.trow').length}))""")
        print('[cards]', json.dumps(rows, ensure_ascii=False))
        toplist = pg.evaluate("""() => [...document.querySelectorAll('[data-pid]')].map(e => e.textContent.replace(/\\s+/g,' ').trim())""")
        print(f'[pilot TOP10] ({time.time()-t0:.1f}s)', json.dumps(toplist[:5], ensure_ascii=False))
        assert len(toplist) == 10, 'TOP10 数量错误'
        assert any('多蒙' in x for x in toplist[:3]), '多蒙应在前三'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/19a_calc_pilots.png')

        # 点击第2名选用
        pg.locator('[data-pid]').nth(1).click(); pg.wait_for_timeout(600)
        sel = pg.evaluate("() => ({charId: state.calc.charId, cur: [...document.querySelectorAll('[data-pid]')].map(e => e.textContent).findIndex(t => t.includes('当前')), header: document.querySelector('#picku').textContent.replace(/\\s+/g,' ').trim()})")
        print('[after click]', json.dumps(sel, ensure_ascii=False))
        assert sel['charId'] and sel['cur'] == 1, '点击选用驾驶员失败'

        # 切机体为 SD(全能骑士高达) → 专属1人
        pg.click('#picku'); pg.fill('#pk', '全能骑士'); pg.wait_for_timeout(500)
        pg.click("#pkl [data-pick='1705002050']"); pg.wait_for_timeout(800)
        sd = pg.evaluate("""() => ({n: [...document.querySelectorAll('[data-pid]')].length,
            first: (document.querySelector('[data-pid]')||{textContent:''}).textContent.replace(/\\s+/g,' ').trim(),
            head: [...document.querySelectorAll('#view .card h4')].map(h => h.textContent).find(t => t.includes('驾驶员')) || ''})""")
        print('[SD unit]', json.dumps(sd, ensure_ascii=False))
        assert sd['n'] == 1 and '全能骑士高达' in sd['first'] and 'SD专属' in sd['head'], 'SD机体专属驾驶员列表错误'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/19b_calc_sd_pilot.png')

        # 暴击开关影响列表数值
        v0 = pg.eval_on_selector('[data-pid] .val', 'e => e.textContent')
        pg.click('#crit'); pg.wait_for_timeout(800)
        v1 = pg.eval_on_selector('[data-pid] .val', 'e => e.textContent')
        print(f'[crit off->on] {v0} -> {v1}')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
