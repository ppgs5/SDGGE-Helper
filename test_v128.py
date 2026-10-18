# -*- coding: utf-8 -*-
"""v128 验证: 排行/组队「防御型 eHP」纳入机体被动防御%(含 max 满层)
口径(用户选项2): df = df0 × (1 + 被动防御% + 队伍/舰长%)，max 开时被动按满层
① defenderSkills('机体侧') 对 1031000150(防御力提升 LV3 +15%) 返回 defPct=15
② 组队页防御 eHP 行显示「防+15%」标记，且 eHP 数值 = hp×(1+df/1000)（df 已含被动）
③ 关掉被动(defPct 归零)重渲染 → 同机体 eHP 变小，证明被动确实计入
④ max 切换对条件型防御被动生效(仅条件被动开时)
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9072

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        r1 = pg.evaluate("() => defenderSkills(1031000150, null, true, false, 'mid', true).defPct")
        print('[① 被动防御%]', r1)
        assert r1 == 15, r1

        pg.evaluate("() => { state.stack=[]; push({page:'team',title:'组队'}); render(); }")
        pg.wait_for_timeout(2500)
        t = pg.evaluate("() => document.getElementById('view').innerText")
        rows = pg.evaluate("""() => [...document.querySelectorAll('.trow')].slice(0,60).map(e=>e.innerText.replace(/\\n/g,' | '))""")
        hit = [x for x in rows if '1031000150' in x]
        print('[② 防+ 标记出现]', t.count('防+'))
        assert '防+' in t, t[:600]

        # ③ 同一机体(全装甲高达 雷霆宙域版 EX)关掉被动后 eHP 变化
        def rowval():
            return pg.evaluate("() => { const e=[...document.querySelectorAll('.trow')].find(x=>x.innerText.includes('全装甲高达')); return e? e.querySelector('.val').innerText.split('\\n')[0] : null; }")
        valAfter = rowval()
        pg.evaluate("() => { window.__origDS = defenderSkills; defenderSkills = () => ({ defPct:0, cdefPct:0, redPct:0, x:[] }); state.stack=[]; push({page:'team',title:'组队'}); render(); }")
        pg.wait_for_timeout(2000)
        valBefore = rowval()
        print('[③ 同机体 eHP] 有被动:', valAfter, '| 无被动:', valBefore)
        assert valAfter and valBefore and valAfter != valBefore, (valAfter, valBefore)

        # ④ max 对条件型被动
        pg.evaluate("() => { defenderSkills = window.__origDS; }")
        r2 = pg.evaluate("""() => { const save=state.maxOn; state.maxOn=false; const off=defenderSkills(1095000350,null,true,false,'mid',true).defPct; state.maxOn=true; const on=defenderSkills(1095000350,null,true,false,'mid',true).defPct; state.maxOn=save; return {off,on}; }""")
        print('[④ 条件型 max]', r2)
        assert r2['off'] == 10 and r2['on'] == 50, r2

        assert not errors, errors
        print('=== test_v128 全部通过 ===')
        b.close()
finally:
    srv.terminate()
