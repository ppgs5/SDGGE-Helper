# -*- coding: utf-8 -*-
"""v149 验证: 计算页「首动闪避」筛选（按实际 MP 模拟首动技能）
① 计算页有 #cfe 开关，点击切换 c.fe
② 开启后（F91 双V.S.B.R EX + 首动 + 反死风险），驾驶员 TOP 每行的首动技都是闪避类
   （摇摆闪避 / 命中率、闪避率提升），不会出现攻击爆裂/MP提升等
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9143

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1800}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        pg.evaluate("""() => { const c=state.calc; c.unitId=1163000150; c.first=true; c.fdth=true; c.fe=true;
          state._prKey=null; state.stack=[]; push({page:'calc',title:'计算'}); render(); }""")
        pg.wait_for_timeout(3000)
        r = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#view .trow[data-pid]')];
          const fa = rows.map(e => { const m = e.innerText.replace(/\\n/g,' ').match(/首动技 ([^ ]+ ?[^ ]*)/); return m ? m[0] : ''; });
          return { n: rows.length, fa, hasChip: !!document.getElementById('cfe') }; }""")
        print('[① chip]', r['hasChip'], '| 行数', r['n'])
        print('[② 首动技]', json.dumps(r['fa'][:6], ensure_ascii=False))
        assert r['hasChip'] and r['n'] > 0
        bad = [x for x in r['fa'] if x and not ('摇摆闪避' in x or '命中率、闪避率提升' in x)]
        assert not bad, bad

        note = pg.evaluate("() => document.getElementById('view').innerText.includes('备注：列表按')")
        print('[③ 备注]', note)
        assert note

        pg.evaluate("() => document.getElementById('cfe').click()")
        pg.wait_for_timeout(1200)
        assert pg.evaluate("() => state.calc.fe === false")

        assert not errors, errors
        print('=== test_v149 全部通过 ===')
        b.close()
finally:
    srv.terminate()
