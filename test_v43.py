# -*- coding: utf-8 -*-
"""v0.44 验证: 所有搜索支持大小写混合输入(含全角归一) — 标签/系列弹窗、图鉴、选择器、战舰、队伍增强"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8982
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

        # ---------- 1. 标签/系列弹窗(排行) 大小写+全角 ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_timeout(1500)
        pg.click('#rtag'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-lm="series"]'); pg.wait_for_timeout(400)
        cnt = lambda: pg.evaluate("() => document.querySelectorAll('#stlist .trow2').length")
        res = {}
        for q in ('v', 'V', 'msv', 'MSV', 'ＭＳＶ', 'Msv'):
            pg.fill('#ssearch', q); pg.wait_for_timeout(350)
            res[q] = cnt()
        print('[系列弹窗]', res)
        assert res['v'] > 0 and res['v'] == res['V'], f"系列 v/V 不等: {res}"
        assert res['msv'] > 0 and res['msv'] == res['MSV'] == res['ＭＳＶ'] == res['Msv'], f"系列 msv 变体不等: {res}"
        pg.click('#sheetPanel [data-lm="tag"]'); pg.wait_for_timeout(300)
        res2 = {}
        for q in ('gund', 'GUND', 'ＧＵＮＤ'):
            pg.fill('#ssearch', q); pg.wait_for_timeout(350)
            res2[q] = cnt()
        print('[标签弹窗]', res2)
        assert res2['gund'] > 0 and res2['gund'] == res2['GUND'] == res2['ＧＵＮＤ'], f"标签 gund 变体不等: {res2}"
        pg.click('#sx'); pg.wait_for_timeout(300)

        # ---------- 2. 图鉴搜索(SQL) 大小写+全角 ----------
        pg.click('[data-tab="units"]'); pg.wait_for_timeout(800)
        pg.click('[data-k="weapon"]'); pg.wait_for_timeout(700)
        res3 = {}
        for q in ('beam', 'BEAM', 'ＢＥＡＭ'):
            pg.fill('#sbox', q); pg.wait_for_timeout(500)
            res3[q] = pg.evaluate("() => document.querySelector('#hit').textContent")
        print('[图鉴武器]', res3)
        assert '命中 6 把' == res3['beam'] == res3['BEAM'] == res3['ＢＥＡＭ'], f"图鉴武器搜索不等: {res3}"
        pg.click('[data-k="unit"]'); pg.wait_for_timeout(700)
        pg.fill('#sbox', 'ex'); pg.wait_for_timeout(500)
        n1 = pg.evaluate("() => document.querySelector('#hit').textContent")
        pg.fill('#sbox', 'EX'); pg.wait_for_timeout(500)
        n2 = pg.evaluate("() => document.querySelector('#hit').textContent")
        print('[图鉴机体 ex/EX]', n1, n2)
        assert n1 == n2 and '0 台' not in n1, f'图鉴机体 ex/EX 不等: {n1}/{n2}'
        pg.fill('#sbox', ''); pg.wait_for_timeout(400)

        # ---------- 3. 选择器搜索 大小写 ----------
        pg.evaluate("() => openCalcPicker()"); pg.wait_for_selector('#pk')
        res4 = {}
        for q in ('zz', 'ZZ'):
            pg.fill('#pk', q); pg.wait_for_timeout(400)
            res4[q] = pg.evaluate("() => document.querySelectorAll('#pkl .trow2').length")
        print('[选择器 zz/ZZ]', res4)
        assert res4['zz'] > 0 and res4['zz'] == res4['ZZ'], f'选择器搜索不等: {res4}'
        pg.evaluate("() => closeSheet()")

        # ---------- 4. 战舰选择器搜索 大小写 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#picks'); pg.wait_for_timeout(800)
        pg.click('#picks'); pg.wait_for_selector('#pk')
        res5 = {}
        for q in ('j', 'J'):
            pg.fill('#pk', q); pg.wait_for_timeout(400)
            res5[q] = pg.evaluate("() => document.querySelectorAll('#pkl .trow2').length")
        print('[战舰 j/J]', res5)
        assert res5['j'] > 0 and res5['j'] == res5['J'], f'战舰搜索不等: {res5}'
        pg.evaluate("() => closeSheet()")

        # ---------- 5. 队伍增强搜索 大小写 ----------
        pg.wait_for_timeout(400)
        pg.click('#tbuff'); pg.wait_for_selector('#pk', timeout=15000)
        res6 = {}
        for q in ('ex', 'EX'):
            pg.fill('#pk', q); pg.wait_for_timeout(400)
            res6[q] = pg.evaluate("() => document.querySelectorAll('#pkl .trow2').length")
        print('[队伍增强 ex/EX]', res6)
        assert res6['ex'] > 0 and res6['ex'] == res6['EX'], f'队伍增强搜索不等: {res6}'
        pg.evaluate("() => closeSheet()")
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
