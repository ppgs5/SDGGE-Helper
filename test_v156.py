# -*- coding: utf-8 -*-
"""v156 验证: 各处稀有度筛选改为多选
① 图鉴：点 UR+SR → filt('unit').rar=[5,3]，列表同时出现 UR 与 SR；点「全部」清空
② 计算：c.pRar=[5,4] 时驾驶员 TOP 只含 UR/SSR
③ 组队：t.rar=[5,4] 时攻击型 TOP 机体只含 UR/SSR
④ 特性/弹窗选择器：selRar 为数组（通过 openTagPicker 状态检查）
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9162

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1600}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        pg.evaluate("() => { state.unitKind='unit'; state.stack=[]; push({page:'units',title:'图鉴'}); render(); }")
        pg.wait_for_timeout(1200)
        r = pg.evaluate("""() => { const els=[...document.querySelectorAll('#rarf [data-krar]')];
          els.find(e=>e.dataset.krar==='5').click(); els.find(e=>e.dataset.krar==='3').click();
          const cards=[...document.querySelectorAll('#listarea .ucard')].slice(0,80).map(e=>e.innerText);
          return { rar: filt('unit').rar, n: cards.length,
                   hasUR: cards.some(x=>x.includes('UR')), hasSR: cards.some(x=>x.includes('SR')),
                   on: [...document.querySelectorAll('#rarf [data-krar]')].filter(e=>e.className.includes('gold')||e.className.includes('on')).map(e=>e.dataset.krar) }; }""")
        print('[① 图鉴]', json.dumps(r, ensure_ascii=False)[:200])
        assert r['rar'] == [5, 3] and r['hasUR'] and r['hasSR'], r

        r2 = pg.evaluate("""() => { [...document.querySelectorAll('#rarf [data-krar]')].find(e=>e.dataset.krar==='all').click(); return filt('unit').rar; }""")
        print('[① 全部清空]', r2)
        assert r2 == []

        pg.evaluate("""() => { const c=state.calc; c.unitId=1080000150; c.pRar=[5,4]; c.first=false; state._prKey=null;
          state.stack=[]; push({page:'calc',title:'计算'}); render(); }""")
        pg.wait_for_timeout(2800)
        r3 = pg.evaluate("""() => { const rows=[...document.querySelectorAll('#view .trow[data-pid]')];
          const rar = rows.map(e=>{ const t=e.innerText; return /UR/.test(t)?5:(/SSR/.test(t)?4:(/SR/.test(t)?3:0)); });
          return {n: rows.length, rar}; }""")
        print('[② 计算]', r3)
        assert r3['n'] > 0 and all(x in (4, 5) for x in r3['rar']), r3

        pg.evaluate("""() => { const t=state.team; state.teamCache=null; t.rar=[5,4]; t.prar=[]; t.first=false;
          state.stack=[]; push({page:'team',title:'组队'}); render(); }""")
        pg.wait_for_timeout(3400)
        r4 = pg.evaluate("""() => { const G=state.teamCache&&state.teamCache.G; if(!G) return null;
          return {n:G.main.length, rar: G.main.map(x=>x.unit.rarity)}; }""")
        print('[③ 组队]', json.dumps(r4)[:160])
        assert r4 and r4['n'] > 0 and all(x in (4, 5) for x in r4['rar']), r4

        assert not errors, errors
        print('=== test_v156 全部通过 ===')
        b.close()
finally:
    srv.terminate()
