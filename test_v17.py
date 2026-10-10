# -*- coding: utf-8 -*-
"""v0.17 验证: 武器完整效果(全量fx) + 使用限制 + 自带额外行动特性页"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8851
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

        # ---------- 1. 光之翼(赞斯派因EX, MAP): 完整效果 + 使用限制 ----------
        pg.evaluate("() => push({page:'weapon', title:'光之翼', id:185000485005})")
        pg.wait_for_timeout(700)
        t1 = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        print('[光之翼]', t1[:300])
        assert '射程1-4·MAP' in t1 and 'MAP武装' in t1, 'MAP 标识缺失'
        assert '绝对命中' in t1 and '防御力减少(1回合) LV4' in t1 and '额外行动增加' in t1, '完整效果缺失'
        assert '使用限制' in t1 and '仅限于移动前使用' in t1 and '消耗6MP即可使用' in t1, '使用限制缺失'
        assert '+300510101' not in t1, '仍有未解析效果引用'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/24a_weapon_full.png')

        # ---------- 2. 洗牌同盟拳 EX: 效果 + 5MP ----------
        pg.evaluate("() => push({page:'weapon', title:'洗牌同盟拳 EX', id:120000395006})")
        pg.wait_for_timeout(700)
        t2 = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        print('[洗牌同盟拳EX]', t2[:260])
        assert '近距离时武装POWER提升 LV7' in t2, '每级效果名缺失'
        assert '消耗5MP即可使用' in t2, 'MP 限制缺失'

        # ---------- 3. 鐳射軍刀: 水下限制 ----------
        pg.evaluate("() => push({page:'weapon', title:'鐳射軍刀', id:100100010001})")
        pg.wait_for_timeout(700)
        t3 = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        print('[鐳射軍刀]', t3[:200])
        assert '对水下敌人的伤害减半' in t3, '水下限制缺失'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/24b_weapon_use.png')

        # ---------- 4. 自带额外行动: 胡索(无条件)+加岛勇+光之翼 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow')
        chips = pg.eval_on_selector_all('.chip[data-k]', "els => els.map(e => e.textContent.trim())")
        print('[feat chips]', chips)
        assert any('自带额外行动' in c for c in chips), '特性页无「自带额外行动」分组'
        pg.click("[data-k='auto_extra_action']"); pg.wait_for_timeout(500)
        ft = pg.evaluate("() => document.getElementById('farea').textContent.replace(/\\s+/g,' ')")
        print('[自带额外行动]', ft[:360])
        assert '加岛勇' in ft and '苍蓝命运1号机 (EX)' in ft, '加岛勇条目缺失'
        assert '胡索' in ft and '无条件额外行动' in ft, '胡索·无条件额外行动 条目缺失(v高达EX 例)'
        assert '光之翼' in ft and '赞斯派因' in ft, '光之翼武器条目缺失'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/24c_feat_auto.png')

        # ---------- 5. 额外行动+1: 胡索的「额外行动」+1次仍在此分组, 且无重复 ----------
        pg.click("[data-k='extra_action']"); pg.wait_for_timeout(500)
        ft2 = pg.evaluate("() => document.getElementById('farea').textContent.replace(/\\s+/g,' ')")
        print('[额外行动+1]', ft2[:260])
        assert '胡索' in ft2, '胡索「额外行动+1」缺失'
        n_hu = ft2.count('胡索')
        assert n_hu == 1, f'胡索在额外行动+1 应仅1条, got {n_hu}'

        # ---------- 6. 组队行内武器射程 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow'); pg.wait_for_timeout(2200)
        rng = pg.eval_on_selector_all('#tarea .trow .nm small', "els => els.map(e => e.textContent.match(/射程|MAP/) ? e.textContent.replace(/\\s+/g,' ').trim() : '')")
        rng = [x for x in rng if x]
        print('[组队射程]', rng[:4])
        assert rng, '组队行未显示武器射程'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
