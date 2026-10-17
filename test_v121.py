# -*- coding: utf-8 -*-
"""v121 验证: 计算/排行/组队 新增「支援攻击/反击」开关
① 默认开; 关=不计入「支援攻击/支援反击/反击时」被动
② 样例: 达里尔·洛伦兹(1031000601) (支援时)攻击力提升LV4 +20% × 支援型机体 1001000100
   条件被动开/关两种情况下, supAct 开=20 / 关=0
③ 三页 chip: csupact / rsupact / tsupact 存在且可切换
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9061
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        r1 = pg.evaluate("""() => {
          const opts = ca => ({ passive: true, cpassive: true, skills: false, condAll: ca, unitId: 1001000100, upassive: true, multiPhase: false, pSpU: true });
          state.supAct = true;
          const onCa = charBonus(1031000601, 'default', opts(true), metaOf(1001000100)).atk;
          const onNo = charBonus(1031000601, 'default', opts(false), metaOf(1001000100)).atk;
          state.supAct = false;
          const offCa = charBonus(1031000601, 'default', opts(true), metaOf(1001000100)).atk;
          state.supAct = true;
          return { def: state.supAct, onCa, onNo, offCa }; }""")
        print('[①/② 支援攻击被动]', r1)
        assert r1['def'] is True and r1['onCa'] == 20 and r1['onNo'] == 20 and r1['offCa'] == 0, r1
        print('[② 开关=计入/关闭=不计入(条件被动开/关均成立) 通过]')

        pg.evaluate("() => { state.calc.unitId = 1001000100; state.calc.charId = 1031000601; state.stack = []; push({ page:'calc', title:'' }); render(); }")
        pg.wait_for_selector('#csupact', timeout=120000)
        txt = pg.evaluate("() => document.getElementById('csupact').innerText")
        assert '开' in txt, txt
        pg.click('#csupact'); pg.wait_for_timeout(900)
        assert pg.evaluate('() => state.supAct') is False
        pg.click('#csupact'); pg.wait_for_timeout(900)
        assert pg.evaluate('() => state.supAct') is True
        for page, cid in (('rank', 'rsupact'), ('team', 'tsupact')):
            pg.evaluate("(p2) => { state.stack = []; push({ page:p2, title:'' }); render(); }", page)
            pg.wait_for_selector('#' + cid, timeout=180000)
        print('[③ 计算/排行/组队三页开关 通过]')

        assert not errors, errors
        print('=== test_v121 全部通过 ===')
        b.close()
finally:
    srv.terminate()
