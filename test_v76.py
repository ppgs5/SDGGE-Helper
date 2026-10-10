# -*- coding: utf-8 -*-
"""v0.76 验证: 组队「驾驶员稀有度」作用于全部组 (原仅攻击型TOP10; 攻×支/支援型/防御型输出一并生效)
① 驾驶员稀有度=SSR → 攻击型TOP10/攻×支TOP10/支援型TOP10/防御型TOP10 四列表的驾驶员角标全为SSR(各10行)
   支援型列表含塞西娅(SSR) 且不含阿瑟姆(UR)
② 驾驶员稀有度=全部 → 恢复混合(此前的口径)
③ 机体稀有度=UR → 全五列表(含eHP)机体角标全UR (顺带核验机体稀有度本就全组生效)
仅回归最新版(用户口径)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8976

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
        pg.evaluate("() => { state.stack = []; setTab('team'); }")
        pg.wait_for_timeout(4500)

        def cards():
            return pg.evaluate("""() => [...document.querySelectorAll('#tarea .card')].map(c => {
              const t = (c.querySelector('h4') || {}).textContent || '';
              const pilotB = [...c.querySelectorAll('.trow .avw.avsm .rarb')].map(x => x.textContent);
              const unitB = [...c.querySelectorAll('.trow .avw:not(.avsm):not(.avp) .rarb')].map(x => x.textContent);
              return { t, pilotB, unitB, rows: c.querySelectorAll('.trow').length, txt: c.textContent.replace(/\\s+/g,' ') };
            }).filter(c => c.t.includes('TOP'))""")

        def click(sel):
            pg.evaluate(f"() => document.querySelector('{sel}').click()")
            pg.wait_for_timeout(4200)

        # ① 驾驶员稀有度 = SSR
        click('[data-tprar="4"]')
        cs = cards()
        find_c = lambda pre: next(c for c in cs if c['t'].startswith(pre))
        for key in ('攻击型 TOP10', '攻击型 × 支援型驾驶员', '支援型 TOP10', '防御型 TOP10 · 输出'):
            c = find_c(key)
            assert c['rows'] == 10, (key, c['rows'])
            assert c['pilotB'] and all(x == 'SSR' for x in c['pilotB']), (key, c['pilotB'])
        sup = find_c('支援型 TOP10')
        assert '塞西娅' in sup['txt'] and '阿瑟姆' not in sup['txt'], sup['txt'][:120]
        print('[① 驾驶员稀有度=SSR 四列表全SSR(支援型含塞西娅/无阿瑟姆)] 通过')

        # ② 恢复全部 → 混合
        click('[data-tprar="all"]')
        cs = cards()
        sup = next(c for c in cs if c['t'].startswith('支援型 TOP10'))
        assert any(x != 'SSR' for x in sup['pilotB']), sup['pilotB']     # 恢复后应含UR等
        print('[② 恢复全部(混合) ] 通过')

        # ③ 机体稀有度 = UR → 五列表(含eHP)机体角标全UR
        click('[data-trar="5"]')
        cs = cards()
        assert len(cs) == 5, [c['t'][:16] for c in cs]
        for c in cs:
            assert c['unitB'] and all(x == 'UR' for x in c['unitB']), (c['t'][:20], c['unitB'][:5])
        print('[③ 机体稀有度=UR 全五列表生效] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v76 全部通过 ===')
