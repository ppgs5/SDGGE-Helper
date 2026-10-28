# -*- coding: utf-8 -*-
"""v145 验证: 计算页「我方全能力+X%」 + 机师图鉴显示系列
① 计算页有 #callup 输入（我方全能力），改 30% 后攻击上升且头部提示「全能力+30%（攻/防/HP/机动）」
② 该值只作用于我方：靶防御输入值不变
③ 机师详情显示「系列」（可多系列，主系列高亮）并可点击按系列筛选机师
④ 计算页「机体图鉴 ›」「机师图鉴 ›」按钮可跳转对应详情
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9122

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1400}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        pg.evaluate("() => { state.calc.unitId=1370011150; state.calc.charId=1370003501; state.calc.allup=0; state.stack=[]; push({page:'calc',title:'计算'}); render(); }")
        pg.wait_for_timeout(1200)
        a0 = pg.evaluate("() => +document.getElementById('view').innerText.match(/攻击 ([0-9,]+)/)[1].replace(/,/g,'')")
        has_input = pg.evaluate("() => !!document.getElementById('callup')")
        print('[① 输入存在/初始攻击]', has_input, a0)
        assert has_input, '缺少 #callup'

        pg.evaluate("() => { state.calc.allup=30; render(); }")
        pg.wait_for_timeout(1200)
        r = pg.evaluate("""() => { const t=document.getElementById('view').innerText;
          return { atk: +t.match(/攻击 ([0-9,]+)/)[1].replace(/,/g,''), note: t.includes('全能力+30%'),
                   tdef: (document.getElementById('tdef2')||{}).value }; }""")
        print('[① 30%]', r)
        assert r['atk'] > a0, (a0, r['atk'])
        assert r['note'], '头部未显示全能力提示'
        assert r['tdef'] == '10000', r['tdef']          # ② 靶防御不变

        pg.evaluate("() => { state.stack=[]; push({page:'char',title:'x',id:1370003501}); render(); }")
        pg.wait_for_timeout(900)
        c = pg.evaluate("""() => { const v=document.getElementById('view'); const el=v.querySelector('[data-cser]');
          return { has: !!el, sid: el? el.dataset.cser : null, txt: el? el.innerText : null, tagRow: v.innerText.includes('标签:') }; }""")
        print('[③ 机师系列]', c)
        assert c['has'] and c['sid'] == '3700' and '机动战士高达00' in c['txt'], c

        pg.evaluate("() => { document.querySelector('[data-cser]').click(); }")
        pg.wait_for_timeout(1000)
        f = pg.evaluate("() => ({ tab: state.tab, kind: state.unitKind, series: filt('char').series, tags: filt('char').tags })")
        print('[③ 点击筛选]', f)
        assert f['tab'] == 'units' and f['kind'] == 'char' and f['series'] == [3700] and f['tags'] == [], f

        pg.evaluate("() => { state.stack=[]; push({page:'calc',title:'计算'}); render(); }")
        pg.wait_for_timeout(900)
        b1 = pg.evaluate("() => ({ u: !!document.getElementById('gounit'), c: !!document.getElementById('gochar') })")
        print('[④ 按钮]', b1)
        assert b1['u'] and b1['c'], b1
        pg.evaluate("() => document.getElementById('gounit').click()")
        pg.wait_for_timeout(700)
        assert pg.evaluate("() => (state.stack[state.stack.length-1]||{}).page") == 'unit'
        pg.evaluate("() => { state.stack=[]; push({page:'calc',title:'计算'}); render(); }")
        pg.wait_for_timeout(700)
        pg.evaluate("() => document.getElementById('gochar').click()")
        pg.wait_for_timeout(700)
        assert pg.evaluate("() => (state.stack[state.stack.length-1]||{}).page") == 'char'

        # ⑤ 驾驶员 TOP 伤害随全能力变化
        def pilot_top(allup):
            pg.evaluate("""([allup]) => { state.calc.allup=allup; state._prKey=null; state.stack=[]; push({page:'calc',title:'计算'}); render(); }""", [allup])
            pg.wait_for_timeout(3000)
            return pg.evaluate("""() => [...document.querySelectorAll('#view .trow[data-pid]')].slice(0,3).map(e=>e.innerText.replace(/\\n/g,' '))""")
        t0 = pilot_top(0); t30 = pilot_top(30)
        print('[⑤ 驾驶员TOP 0%]', json.dumps(t0, ensure_ascii=False)[:180])
        print('[⑤ 驾驶员TOP 30%]', json.dumps(t30, ensure_ascii=False)[:180])
        assert t0 and t30 and t0 != t30, (t0, t30)

        # ⑥ 多系列角色: 夏亚(THE ORIGIN版) 同时属于 THE ORIGIN(30) 与 高达(10)
        pg.evaluate("() => { state.stack=[]; push({page:'char',title:'x',id:1003000100}); render(); }")
        pg.wait_for_timeout(900)
        m = pg.evaluate("""() => [...document.querySelectorAll('#view [data-cser]')].map(e=>({id:e.dataset.cser,t:e.innerText,c:e.className}))""")
        print('[⑥ 多系列]', m)
        assert len(m) >= 2 and {x['id'] for x in m} >= {'10', '30'}, m
        assert m[0]['c'].find('on') >= 0, m[0]

        assert not errors, errors
        print('=== test_v145 全部通过 ===')
        b.close()
finally:
    srv.terminate()
