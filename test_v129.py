# -*- coding: utf-8 -*-
"""v129 验证: 组队页「选择防御」与「支援防御」互斥(不再叠加计算)
问题: 原实现 stancePct = guard?40 + sdef?40 + (任一)盾20 → 两个都开=100% 减伤, 属重复计算
游戏口径: 防御(自身)与支援防御(代他人)是同一场战斗的互斥动作, 只能二选一
① stanceReduceOf: 都关=0 / 单开=60(带盾) / 都开(异常态)=60 而非 100
② 按钮互斥: 点「选择防御」后「支援防御」自动关; 反之亦然
③ 无盾机体: 单开=40
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9077

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        # ① 数值口径
        r = pg.evaluate("""() => ({
          none: stanceReduceOf({guard:false, sdef:false}, true),
          guard: stanceReduceOf({guard:true, sdef:false}, true),
          sdef: stanceReduceOf({guard:false, sdef:true}, true),
          both: stanceReduceOf({guard:true, sdef:true}, true),
          noShield: stanceReduceOf({guard:true, sdef:false}, false),
          noShieldBoth: stanceReduceOf({guard:true, sdef:true}, false)
        })""")
        print('[① 姿态减伤]', r)
        assert r['none'] == 0 and r['guard'] == 60 and r['sdef'] == 60, r
        assert r['both'] == 60, ('两个都开仍叠加', r)
        assert r['noShield'] == 40 and r['noShieldBoth'] == 40, r

        # ② 按钮互斥
        pg.evaluate("() => { state.stack=[]; push({page:'team',title:'组队'}); state.team.dunit=1308000502; render(); }")
        pg.wait_for_timeout(1500)
        pg.evaluate("() => { state.team.guard=false; state.team.sdef=false; pageTeam(document.getElementById('view')); }")
        pg.wait_for_timeout(800)
        pg.click('#tguard'); pg.wait_for_timeout(600)
        s1 = pg.evaluate("() => ({g:state.team.guard, s:state.team.sdef})")
        pg.click('#tsdef'); pg.wait_for_timeout(600)
        s2 = pg.evaluate("() => ({g:state.team.guard, s:state.team.sdef})")
        pg.click('#tguard'); pg.wait_for_timeout(600)
        s3 = pg.evaluate("() => ({g:state.team.guard, s:state.team.sdef})")
        print('[② 按钮互斥]', s1, s2, s3)
        assert s1 == {'g': True, 's': False}, s1
        assert s2 == {'g': False, 's': True}, s2
        assert s3 == {'g': True, 's': False}, s3

        assert not errors, errors
        print('=== test_v129 全部通过 ===')
        b.close()
finally:
    srv.terminate()
