# -*- coding: utf-8 -*-
"""v0.92 验证: 驾驶员面板数值口径修复 —— max_* 改存「稀有度等级上限值」(非 Lv100 理论值)
参考站(soshage)与游戏面板显示 = base + (max100-base)*cap//100, cap: N60/R70/SR80/SSR90/UR100;
SP开 = sp_max(Lv100), 无SP角色 sp NULL 回退面板值(不再显示0)
① 图鉴驾驶员列表: 地球联邦将校(R) 射击611 格斗480 觉醒504 防御556 反应556 (与参考站 LV70/70 截图一致)
② 角色页(将校): 同值; 驾驶员SP 开 → 仍 611/…(无SP数据回退, 不再 0)
③ 凯·西汀(R): SP关 294/254/219/344/332; SP开 526/457/401/621/595 + "原"注释
④ 雪拉·玛斯 SSR: 623/529/383/358/450 (原值口径; 参考站页面 654/… 为叠加能力加成后值, 非面板值)
⑤ UR 阿姆罗 不变(571/532/549/670/669, SP开关无效); 手动收录 塞西娅 557/493/293/425/452, SP开 650/577/345/498/530 不变
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8992

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(120000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')

        def open_char(cid, wait=1800):
            pg.evaluate(f"() => {{ state.stack=[]; push({{page:'char', title:'x', id:{cid}}}); }}")
            pg.wait_for_timeout(wait)

        def char_stats():   # 角色页 statgrid: 射击/格斗/觉醒/防御/反应 → {k: v文本}
            return pg.evaluate("""() => { const o={};
              document.querySelectorAll('.statgrid .stat').forEach(s => {
                o[s.querySelector('.k').textContent.trim()] = s.querySelector('.v').innerText.replace(/\\s+/g,' ').trim(); });
              return o; }""")

        def set_sp(on):     # 驾驶员SP 为全局状态(跨页面保持), 显式置位
            cur = pg.evaluate("() => !!state.charSp")
            if cur != on:
                pg.evaluate("() => document.getElementById('cspu2').click()")
                pg.wait_for_timeout(1200)

        EXP611 = {'射击': '611', '格斗': '480', '觉醒': '504', '防御': '556', '反应': '556'}

        # ① 图鉴驾驶员列表(搜索)
        pg.evaluate("() => { state.stack=[]; state.tab='units'; setTab('units'); }")
        pg.wait_for_timeout(2200)
        pg.evaluate("() => document.querySelector('#kinds [data-k=\"char\"]').click()")
        pg.wait_for_timeout(1800)
        pg.evaluate("""() => { const el=document.getElementById('sbox'); el.value='地球联邦将校';
          el.dispatchEvent(new Event('input')); }""")
        pg.wait_for_timeout(1600)
        row = pg.evaluate("""() => { const el=[...document.querySelectorAll('#listarea .lrow')].find(e => e.textContent.includes('地球联邦将校'));
          return el ? el.innerText.replace(/\\s+/g,' ') : null; }""")
        print('[① 列表行]', row)
        assert row and '射击611' in row and '格斗480' in row and '觉醒504' in row and '防御556' in row and '反应556' in row, row
        print('[① 图鉴列表 将校=参考站LV70/70值 通过]')

        # ② 角色页(将校) + SP 开 → 回退面板值不再 0
        open_char(2001001000)
        st = char_stats()
        n0 = pg.evaluate("() => (q1('SELECT sp_max_ranged FROM characters WHERE id=2001001000')||{}).sp_max_ranged")
        print('[② 将校 SP关]', st, '| DB sp_max_ranged =', n0)
        assert st == EXP611 and n0 is None, (st, n0)
        set_sp(True)
        st2 = char_stats()
        print('[② 将校 SP开]', st2)
        assert st2 == EXP611, st2                      # 无SP数据 → 回退面板值(修复前会显示 0)
        set_sp(False)
        print('[② 角色页 将校 SP关=611/…, SP开回退不显示0 通过]')

        # ③ 凯·西汀 R: SP关 cap70, SP开 sp_max
        open_char(1001000200)
        st = char_stats()
        print('[③ 凯·西汀 SP关]', st)
        assert st == {'射击': '294', '格斗': '254', '觉醒': '219', '防御': '344', '反应': '332'}, st
        set_sp(True)
        st = char_stats()
        print('[③ 凯·西汀 SP开]', st)
        assert st == {'射击': '526 原294', '格斗': '457 原254', '觉醒': '401 原219', '防御': '621 原344', '反应': '595 原332'}, st
        print('[③ 凯·西汀 SP关294/…, SP开526+原注释 通过]')

        # ④ 雪拉·玛斯 SSR(403): 面板原值口径
        set_sp(False)
        open_char(1001000403)
        st = char_stats()
        print('[④ 雪拉SSR SP关]', st)
        assert st == {'射击': '623', '格斗': '529', '觉醒': '383', '防御': '358', '反应': '450'}, st
        print('[④ 雪拉SSR 原值口径(623/529/383/358/450) 通过]')

        # ⑤ UR 阿姆罗(cap100不变, SP开关无效) / 手动塞西娅不变
        open_char(1001000100)
        st = char_stats()
        print('[⑤ 阿姆罗UR SP关]', st)
        assert st == {'射击': '571', '格斗': '532', '觉醒': '549', '防御': '670', '反应': '669'}, st
        set_sp(True)
        st = char_stats()
        print('[⑤ 阿姆罗UR SP开]', st)
        assert st == {'射击': '571', '格斗': '532', '觉醒': '549', '防御': '670', '反应': '669'}, st
        set_sp(False)
        open_char(1999000100)
        st = char_stats()
        print('[⑤ 塞西娅(手动) SP关]', st)
        assert st == {'射击': '557', '格斗': '493', '觉醒': '293', '防御': '425', '反应': '452'}, st
        set_sp(True)
        st = char_stats()
        print('[⑤ 塞西娅(手动) SP开]', st)
        assert st == {'射击': '650 原557', '格斗': '577 原493', '觉醒': '345 原293', '防御': '498 原425', '反应': '530 原452'}, st
        print('[⑤ UR 不变 + 手动收录不变 通过]')
        print('=== test_v92 全部通过 ===')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
