# -*- coding: utf-8 -*-
"""v0.31 验证: SSP武器没有「超强势以上」限制(与非SSP版对照) — 限制只来自武器tension>=4"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8941
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

        # ---------- 0. 数据层 ----------
        chk = pg.evaluate("""() => {
          const use = id => q('SELECT text FROM weapon_use WHERE weapon_id=?', [id]).map(r => r.text).join('|');
          return {
            sspUse: use(137000590090),            // 强化巨剑SSP: 无超强势限制
            baseUse: use(137000590006),           // 强化巨剑(非SSP): 有
            sspHigh: vigorAllows(137000590090, 'high'),
            baseHigh: vigorAllows(137000590006, 'high'),
            baseMax: vigorAllows(137000590006, 'max'),
            n: q("SELECT DISTINCT weapon_id FROM weapon_use WHERE text LIKE '%超强势%'").length,
            fssp: q("SELECT desc FROM weapon_fx WHERE weapon_id=137000590090 AND level=1 AND desc LIKE '%效果值UP%'", [])[0].desc,
            fbase: q("SELECT desc FROM weapon_fx WHERE weapon_id=137000590006 AND level=1 AND desc LIKE '%效果值UP%'", [])[0].desc,
          };
        }""")
        print('[数据]', chk)
        assert '超强势' not in chk['sspUse'], 'SSP武器不应有超强势限制'
        assert '超强势' in chk['baseUse'], '非SSP强化巨剑应有超强势限制'
        assert chk['sspHigh'] is True, 'SSP武器在强势下应可用'
        assert chk['baseHigh'] is False and chk['baseMax'] is True, '非SSP限制武器应仅超强势以上可用'
        assert chk['n'] == 87, f'超强势限制武器数应为87(仅tension>=4): {chk["n"]}'
        assert '最大值提升3%' in chk['fssp'] and '最大值提升2%' in chk['fbase'], '固有効果文本(SSP3%/非SSP2%)异常'

        # ---------- 1. 武器页显示对照 ----------
        pg.evaluate("() => push({page:'weapon', title:'x', id:137000590090})"); pg.wait_for_timeout(700)
        w1 = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        assert '战意为超强势' not in w1 and '武装效果的效果值UP(且最大值提升3%)' in w1, 'SSP武器页显示错误'
        pg.evaluate("() => push({page:'weapon', title:'x', id:137000590006})"); pg.wait_for_timeout(700)
        w2 = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        assert '战意为超强势以上时即可使用' in w2 and '武装效果的效果值UP(且最大值提升2%)' in w2, '非SSP武器页显示错误'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/43a_weapon_pair.png')

        # ---------- 2. 计算页: 00R 强势下 SSP可用 / 非SSP版被隐藏(带提示) ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '00强化模组'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pick='1370005900']"); pg.wait_for_timeout(900)
        pg.click('[data-vg="high"]'); pg.wait_for_timeout(1600)
        t1 = pg.evaluate("() => document.querySelector('#view table.ctable').textContent.replace(/\\s+/g,' ')")
        note = pg.evaluate("() => { const n = document.querySelector('#view .subnote'); return n ? n.textContent : '' }")
        print('[计算 强势] 含SSP:', '强化巨剑 SSP' in t1, '| 含普通强化巨剑(应无):', ('强化巨剑 ' in t1 or '强化巨剑' in t1.replace('强化巨剑 SSP', '')), '| 提示:', note[:40])
        assert '强化巨剑 SSP' in t1, 'SSP武器在强势下应可用'
        assert '强化巨剑' in t1.replace('强化巨剑 SSP', '').strip() or '强化巨剑 SSP' not in t1.replace('强化巨剑 SSP', ''), 'sanity'
        assert '强化巨剑 ' not in t1.replace('强化巨剑 SSP', '') , '非SSP强化巨剑(超强势限定)不应出现在强势表内'
        assert '已隐藏' in note, '应提示隐藏的限定武器'
        pg.click('[data-vg="max"]'); pg.wait_for_timeout(1600)
        t2 = pg.evaluate("() => document.querySelector('#view table.ctable').textContent.replace(/\\s+/g,' ')")
        assert t2.count('强化巨剑') >= 2, '超强势下两个版本都应可用'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/43b_calc_ssp_unlock.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
