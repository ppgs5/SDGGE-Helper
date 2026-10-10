# -*- coding: utf-8 -*-
"""v0.67 验证: 角色页能力条件 chips（以游戏截图为准）
① 阿姆罗·雷 1001000100 角色页「能力」: 显示 TAG 地球联邦军(宇宙世纪) / TAG 红色 / 耐久型类型
   （对应游戏「角色能力一览」的 TAG/类型 chips；支援防御时+20% 两条的门控已在 v0.66）
② abilityCondChips 扩展: unit_role 条件 → 「XX类型」chip（无 TAG 前缀）；TAG 类保持「TAG x」
③ 机体页 chips 回归: AGE-2(EX) 仍为 TAG 新人类 / TAG X行者（不含类型 chip 的误出为标题角色角标, 属既有元素）
④ 防御口径回归: defenderSkills 支援防御门控（v0.66）保持
回归: test_v58 / test_v59 / test_v63 / test_v64 / test_v66 全过
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8966

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

        # ---------- ① 阿姆罗角色页 chips ----------
        pg.evaluate("() => push({page:'char', title:'x', id:1001000100})")
        pg.wait_for_timeout(900)
        chips = pg.evaluate("() => [...document.querySelectorAll('#view .tagx.cond')].map(e => e.textContent)")
        print('[① 阿姆罗能力chips]', chips)
        for need in ['TAG 地球联邦军(宇宙世纪)', 'TAG 红色', '耐久型类型']:
            assert need in chips, f'缺 {need} (got {chips})'
        # 能力文本仍在
        body = pg.evaluate("() => document.querySelector('#view').textContent")
        assert '自身受到的损伤减轻15%' in body.replace(' ', ''), '减伤15%文案应在'
        print('[① 角色页能力chips] 通过(与游戏截图一致)')

        # ---------- ②③ 机体页 chips 回归 ----------
        pg.evaluate("() => { state.stack = []; push({page:'unit', title:'x', id:1400000550}); }")
        pg.wait_for_timeout(700)
        u = pg.evaluate("() => [...document.querySelectorAll('#view .tagx.cond')].map(e => e.textContent)")
        print('[③ AGE-2 chips]', u)
        assert 'TAG 新人类' in u and 'TAG X行者' in u, u
        assert not any(x.endswith('类型') for x in u), f'机体页不应出现类型chip: {u}'

        # ---------- ④ 防御门控回归 ----------
        d = pg.evaluate("""() => ({
          off: defenderSkills(1001000150, 1001000100, false).defPct,
          on: defenderSkills(1001000150, 1001000100, true).defPct
        })""")
        print('[④ defenderSkills 关/开]', d)
        assert d['off'] == 0 and d['on'] == 40, d
        print('[④ 支援防御门控] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v67 全部通过 ===')
