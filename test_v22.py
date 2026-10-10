# -*- coding: utf-8 -*-
"""v0.22 验证: 防御目标三星数据+防御类技能 / 选择防御·支援防御开关 / 先发攻击右侧最大伤害"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8895
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

        # ---------- 1. 防御机体三星数据 + 防御类技能 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow'); pg.wait_for_timeout(2600)
        pg.click('#dpick'); pg.wait_for_timeout(600)
        pg.fill('#pk', '独角兽高达'); pg.wait_for_timeout(600)
        pg.click('#pkl [data-dpick]'); pg.wait_for_timeout(800)
        pg.click('#pkl [data-dpickc]'); pg.wait_for_timeout(2600)
        card = pg.evaluate("() => document.getElementById('dpick').textContent.replace(/\\s+/g,' ')")
        print('[防御卡]', card[:170])
        assert '耐久' in card and 'eHP' in card, '缺耐久/eHP'
        assert '承伤-' in card, '未显示承伤减免(防御技能)'
        # 三星: df0 应等于 SP×1.4 (与其他页面 max_def*1.4 不同 → 直接校验数值)
        d0 = pg.evaluate("""() => { const u = q1("SELECT sp_max_def, max_def FROM units WHERE name LIKE '独角兽高达 (独角兽模式)%' LIMIT 1");
            return {sp: u.sp_max_def, mx: u.max_def}; }""")
        expect = int(d0['sp'] * 1.4)
        assert f'{expect:,}' in card, f'防御目标应按三星 SP 值({expect}): {card[:80]}'
        d1 = pg.evaluate("() => (document.querySelector('#tarea .trow .val')||{}).textContent")

        # ---------- 2. 选择防御 / 支援防御 开关 ----------
        pg.click('#tguard'); pg.wait_for_timeout(2800)
        t2 = pg.evaluate("() => document.getElementById('tarea').textContent.replace(/\\s+/g,' ')")
        d2 = pg.evaluate("() => (document.querySelector('#tarea .trow .val')||{}).textContent")
        print('[防御开] 承伤:', (t2[t2.find('承伤-'):t2.find('承伤-')+8] if '承伤-' in t2 else '?'), d1, '->', d2)
        assert '承伤-75%' in t2 or '承伤-60%' in t2 or '承伤-70%' in t2, '选择防御姿态减伤未生效'
        assert d2 != d1, '选择防御未影响伤害'
        pg.click('#tsdef'); pg.wait_for_timeout(2800)
        d3 = pg.evaluate("() => (document.querySelector('#tarea .trow .val')||{}).textContent")
        print('[支援防御也开]', d3)
        assert d3 != d2, '支援防御未影响伤害'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/33a_guard.png')

        # ---------- 3. 先发攻击右侧最大伤害 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow')
        pg.click("[data-k='preemptive']"); pg.wait_for_timeout(1200)
        n0 = pg.eval_on_selector_all('.prebest', 'els => els.length')
        assert n0 > 0, '先发攻击行缺右侧占位'
        pg.wait_for_timeout(9000)
        pre = pg.evaluate("() => { const e = document.querySelector('.prebest'); return e ? e.textContent.replace(/\\s+/g,' ') : '' }")
        print('[先发右侧]', pre[:70])
        assert pre and '…' not in pre and '—' != pre.strip(), '右侧最大伤害未填充'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/33b_prebest.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
