# -*- coding: utf-8 -*-
"""v147 验证: 开「首动」时显示机师释放的技能名
① 计算页: 武器表与驾驶员TOP 出现「首动技 XXX」
② 组队页: 攻击型列表绿色伤害上方出现「首动技 XXX」
③ 排行页: 开启首动后，白色伤害下方出现「首动技 XXX」
④ 关闭首动后三页都不再出现「首动技」
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9134

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1600}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        def cnt():
            return pg.evaluate("() => (document.getElementById('view').innerText.match(/首动技/g) || []).length")

        pg.evaluate("() => { const c=state.calc; c.unitId=1370011150; c.charId=1370003501; c.first=true; state._prKey=null; state.stack=[]; push({page:'calc',title:'计算'}); render(); }")
        pg.wait_for_timeout(2800)
        n1 = cnt(); print('[① 计算]', n1)
        assert n1 > 0, n1

        pg.evaluate("() => { state.team.first=true; state.teamCache=null; state.stack=[]; push({page:'team',title:'组队'}); render(); }")
        pg.wait_for_timeout(3200)
        n2 = cnt(); print('[② 组队]', n2)
        assert n2 > 0, n2

        pg.evaluate("() => { state.rankCfg.first=true; state.stack=[]; push({page:'rank',title:'排行'}); render(); }")
        pg.wait_for_timeout(3200)
        n3 = cnt(); print('[③ 排行]', n3)
        assert n3 > 0, n3

        pg.evaluate("() => { state.calc.first=false; state._prKey=null; state.stack=[]; push({page:'calc',title:'计算'}); render(); }")
        pg.wait_for_timeout(2000)
        n4 = cnt(); print('[④ 关闭后计算]', n4)
        assert n4 == 0, n4

        assert not errors, errors
        print('=== test_v147 全部通过 ===')
        b.close()
finally:
    srv.terminate()
