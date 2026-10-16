# -*- coding: utf-8 -*-
"""v110 验证: 组队 5/6 TOP 显示生效的条件被动(对XX敌方, 机体+搭配机师)
① 驱动位(5th): ★3·全部档·靶=达利尔巴尔德EX(红色) → eHP行含「条件:机师 敌「红色」标签 减伤10%」(标签去重)
② 机体位(5th): ★0·UR筛选·靶=突击自由EX(SEED-D) → 天照行含「条件:机体 敌「机动战士高达SEED DESTINY」系列 防+30%」
③ 6th(进攻盾): 同②环境 → cs卡含同注明
④ 假设模式: 同②但无靶·ca开 → 「条件(假设):机体 敌「…SEED DESTINY」系列 防+30%」
⑤ 条件被动关+无靶 → 无「条件:机体」注明
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9018
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

        def render(du, ca, star, mode, rar):
            pg.evaluate("""([du, ca, star, mode, rar]) => { const t = state.team; t.dunit = du; t.dchar = null; t.ca = ca; t.star = star;
              t.sdefMode = mode; t.rar = rar; t.sdef = false; t.guard = false; t.first = false; t.shieldF = false; t.terr = '';
              state.stack = []; push({ page:'team', title:'组队' }); render(); }""", [du, ca, star, mode, rar])
            pg.wait_for_timeout(2800)
            return pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
              const pick = k => { const c = cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes(k)); return c ? c.innerText : ''; };
              const eh = pick('有效耐久'), cs = pick('进攻盾');
              const rowA = (() => { const c = cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes('有效耐久'));
                const r2 = c ? [...c.querySelectorAll('.trow')].find(e => e.innerText.includes('金色机天照')) : null;
                return r2 ? r2.innerText.replace(/\\n/g, ' | ') : null; })();
              return { eh, cs, rowA }; }""")

        # ① 驱动位
        r1 = render(1501003450, True, 3, 'all', None)
        ok1 = '条件:机师 敌「红色」标签 减伤10%' in r1['eh']
        print('[① 驱动位注明]', ok1, '|', (r1['eh'] or '').replace('\n', ' | ')[:200])
        assert ok1, r1['eh'][:400]

        # ② 机体位 5th
        r2 = render(1330000150, True, 0, 'all', 5)
        ok2 = r2['rowA'] is not None and '条件:机体 敌「机动战士高达SEED DESTINY」系列 防+30%' in r2['rowA']
        print('[② 机体位注明]', ok2, '|', (r2['rowA'] or '')[:180])
        assert ok2, r2['rowA']

        # ③ 6th cs
        ok3 = '条件:机体 敌「机动战士高达SEED DESTINY」系列 防+30%' in r2['cs']
        print('[③ 进攻盾注明]', ok3)
        assert ok3, r2['cs'][:300]

        # ④ 假设模式(无靶 ca开)
        r4 = render(None, True, 0, 'all', 5)
        ok4 = r4['rowA'] is not None and '条件(假设):机体 敌「机动战士高达SEED DESTINY」系列 防+30%' in r4['rowA']
        print('[④ 假设注明]', ok4, '|', (r4['rowA'] or '')[:170])
        assert ok4, r4['rowA']

        # ⑤ ca关 无注明
        r5 = render(None, False, 0, 'all', 5)
        ok5 = '条件:机体' not in r5['eh'] and '条件(假设)' not in r5['eh']
        print('[⑤ 条件关无注明]', ok5)
        assert ok5, r5['eh'][:300]

        assert not errors, errors
        print('=== test_v110 全部通过 ===')
        b.close()
finally:
    srv.terminate()
