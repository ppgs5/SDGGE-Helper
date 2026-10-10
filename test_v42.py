# -*- coding: utf-8 -*-
"""v0.43 验证: ①图鉴全品类系列筛选(char/weapon/mod新增) ②搜索处(图鉴+选择器)标签/系列筛选 ③所有列表排序弹窗(图鉴5类/选择器/特性)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8978
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 400, 'height': 860})
        pg.set_default_timeout(240000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append('console.' + m.type + ': ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        print('[boot] ok')

        def open_sort(btn):
            pg.click(btn); pg.wait_for_selector('#sap2')
        def pick_field(f):
            pg.click('#sheetPanel [data-sf="%s"]' % f)
        def apply_sort():
            pg.click('#sap2'); pg.wait_for_timeout(500)

        # ---------- 1. 图鉴-机体: 排序弹窗(攻击力倒序 / 名称顺序 / 复位) ----------
        open_sort('#sbtn')
        pick_field('max_atk'); apply_sort()
        chk = pg.evaluate("""() => {
          const ids = [...document.querySelectorAll('#listarea .ucard')].slice(0, 5).map(el => +el.dataset.id);
          const top = q("SELECT id FROM units ORDER BY max_atk DESC, id ASC LIMIT 5", []).map(r => r.id);
          return {ids, top, label: document.querySelector('#sbtn').textContent.replace(/\\s+/g,' ')};
        }""")
        print('[机体排序 攻击力倒序]', chk['label'], chk['ids'][:3])
        assert chk['ids'] == chk['top'], f'攻击力倒序不符: {chk}'
        assert '攻击力' in chk['label'] and '倒序' in chk['label'], chk['label']
        open_sort('#sbtn'); pick_field('name'); apply_sort()
        chk2 = pg.evaluate("""() => {
          const names = [...document.querySelectorAll('#listarea .ucard .nm')].slice(0, 5).map(el => el.textContent.trim());
          const top = q("SELECT name FROM units ORDER BY name ASC, id ASC LIMIT 5", []).map(r => r.name);
          return {names, top};
        }""")
        print('[机体排序 名称顺序]', chk2['names'][:3])
        assert chk2['names'] == chk2['top'], f'名称顺序不符: {chk2}'
        open_sort('#sbtn'); pick_field('id'); apply_sort()
        d0 = pg.evaluate("() => [...document.querySelectorAll('#listarea .ucard')].slice(0,3).map(el => +el.dataset.id)")
        assert d0 == sorted(d0), '图鉴顺序应升序(按id)'

        # ---------- 2. 图鉴-机体: 系列筛选 ----------
        pg.click('#tbtn'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-lm="series"]'); pg.wait_for_timeout(300)
        sid = pg.evaluate("() => document.querySelector('#sheetPanel [data-sid]').dataset.sid")
        sname = pg.evaluate("() => document.querySelector('#sheetPanel [data-sid]').textContent.trim()")
        pg.click('#sheetPanel [data-sid]'); pg.click('#sapply'); pg.wait_for_timeout(600)
        chk3 = pg.evaluate("""(sid) => {
          const ids = [...document.querySelectorAll('#listarea .ucard')].map(el => +el.dataset.id);
          const bad = ids.filter(id => (q1('SELECT series_id FROM units WHERE id=?', [id]) || {}).series_id != sid);
          return {n: ids.length, bad: bad.length, hit: document.querySelector('#hit').textContent};
        }""", sid)
        print('[机体系列筛选]', sname, chk3)
        assert chk3['n'] > 0 and chk3['bad'] == 0, f'系列筛选含非该系列机体: {chk3}'
        pg.click('#tbtn'); pg.wait_for_selector('#sapply'); pg.click('#sclear'); pg.click('#sapply'); pg.wait_for_timeout(500)

        # ---------- 3. 图鉴-驾驶员: 系列筛选 + 排序 ----------
        pg.click('[data-k="char"]'); pg.wait_for_timeout(600)
        pg.click('#tbtn'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-lm="series"]'); pg.wait_for_timeout(300)
        sidc = pg.evaluate("() => document.querySelector('#sheetPanel [data-sid]').dataset.sid")
        pg.click('#sheetPanel [data-sid]'); pg.click('#sapply'); pg.wait_for_timeout(600)
        chk4 = pg.evaluate("""(sid) => {
          const ids = [...document.querySelectorAll('#listarea .lrow')].map(el => +el.dataset.id);
          const cmap = {}; q('SELECT DISTINCT series_set_id ss, series_id sid FROM units').forEach(r => cmap[String(r.ss)] = String(r.sid));
          const bad = ids.filter(id => cmap[(q1('SELECT series_set_id s FROM characters WHERE id=?', [id]) || {}).s] != String(sid));
          return {n: ids.length, bad: bad.length};
        }""", sidc)
        print('[驾驶员系列筛选]', sidc, chk4)
        assert chk4['n'] > 0 and chk4['bad'] == 0, f'驾驶员系列筛选错误: {chk4}'
        pg.click('#tbtn'); pg.wait_for_selector('#sapply'); pg.click('#sclear'); pg.click('#sapply'); pg.wait_for_timeout(400)
        open_sort('#sbtn'); pick_field('rarity'); apply_sort()
        chk5 = pg.evaluate("""() => {
          const ids = [...document.querySelectorAll('#listarea .lrow')].slice(0, 4).map(el => +el.dataset.id);
          const top = q("SELECT id FROM characters ORDER BY rarity DESC, id ASC LIMIT 4", []).map(r => r.id);
          return {ids, top};
        }""")
        print('[驾驶员排序 稀有度倒序]', chk5['ids'])
        assert chk5['ids'] == chk5['top'], f'驾驶员稀有度倒序不符: {chk5}'

        # ---------- 4. 图鉴-武器/零件: 系列筛选 ----------
        pg.click('[data-k="weapon"]'); pg.wait_for_timeout(700)
        pg.click('#tbtn'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-lm="series"]'); pg.wait_for_timeout(300)
        sidw = pg.evaluate("() => document.querySelector('#sheetPanel [data-sid]').dataset.sid")
        pg.click('#sheetPanel [data-sid]'); pg.click('#sapply'); pg.wait_for_timeout(700)
        chk6 = pg.evaluate("""(sid) => {
          const ids = [...document.querySelectorAll('#listarea .lrow')].map(el => +el.dataset.id);
          const bad = ids.filter(id => (q1('SELECT u.series_id s FROM weapons w JOIN units u ON u.id=w.unit_id WHERE w.id=?', [id]) || {}).s != sid);
          return {n: ids.length, bad: bad.length};
        }""", sidw)
        print('[武器系列筛选]', chk6)
        assert chk6['n'] > 0 and chk6['bad'] == 0, f'武器系列筛选错误: {chk6}'
        pg.click('#tbtn'); pg.wait_for_selector('#sapply'); pg.click('#sclear'); pg.click('#sapply'); pg.wait_for_timeout(400)
        open_sort('#sbtn'); pick_field('power'); apply_sort()
        chk7 = pg.evaluate("""() => {
          const ws = [...document.querySelectorAll('#listarea .lrow')].slice(0, 4).map(el => +el.dataset.id);
          return ws.map(id => q1('SELECT power FROM weapons WHERE id=?', [id]).power);
        }""")
        print('[武器排序 威力倒序]', chk7)
        assert chk7 == sorted(chk7, reverse=True), f'武器威力倒序不符: {chk7}'
        pg.click('[data-k="mod"]'); pg.wait_for_timeout(700)
        pg.click('#tbtn'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-lm="series"]'); pg.wait_for_timeout(300)
        sidm = pg.evaluate("() => document.querySelector('#sheetPanel [data-sid]').dataset.sid")
        pg.click('#sheetPanel [data-sid]'); pg.click('#sapply'); pg.wait_for_timeout(600)
        chk8 = pg.evaluate("""(sid) => {
          const ids = [...document.querySelectorAll('#listarea .lrow')].map(el => +el.dataset.id);
          const bad = ids.filter(id => (q1('SELECT series_id s FROM mods WHERE id=?', [id]) || {}).s != sid);
          return {n: ids.length, bad: bad.length};
        }""", sidm)
        print('[零件系列筛选]', chk8)
        assert chk8['n'] > 0 and chk8['bad'] == 0, f'零件系列筛选错误: {chk8}'

        # ---------- 5. 选择器: 标签筛选 + 排序 ----------
        pg.evaluate("() => openCalcPicker()"); pg.wait_for_selector('#pfil')
        n0 = pg.evaluate("() => document.querySelectorAll('#pkl .trow2').length")
        pg.click('#pfil'); pg.wait_for_selector('#stlist')
        tid = pg.evaluate("() => document.querySelector('#sheetPanel [data-id]').dataset.id")
        pg.click('#sheetPanel [data-id]'); pg.click('#sapply'); pg.wait_for_timeout(600)
        chk9 = pg.evaluate("""(tid) => {
          const ids = [...document.querySelectorAll('#pkl .trow2')].map(el => +el.dataset.pick);
          const bad = ids.filter(id => !q("SELECT 1 FROM unit_tags WHERE unit_id=? AND tag_id=?", [id, tid]).length);
          return {n0: null, n: ids.length, bad: bad.length};
        }""", tid)
        print('[选择器标签筛选]', '原', n0, '→', chk9)
        assert chk9['n'] > 0 and chk9['bad'] == 0, f'选择器标签筛选错误: {chk9}'
        pg.click('#psort'); pg.wait_for_selector('#sap2')
        pg.click('#sheetPanel [data-sf="max_def"]'); pg.click('#sap2'); pg.wait_for_timeout(600)
        chk10 = pg.evaluate("""() => {
          const ids = [...document.querySelectorAll('#pkl .trow2')].map(el => +el.dataset.pick);
          const defs = ids.map(id => q1('SELECT max_def FROM units WHERE id=?', [id]).max_def);
          return {defs: defs.slice(0, 5), sorted: JSON.stringify(defs) === JSON.stringify(defs.slice().sort((a,b)=>b-a))};
        }""")
        print('[选择器排序 防御力]', chk10['defs'])
        assert chk10['sorted'], f'选择器防御力倒序不符: {chk10}'
        pg.click('#pfil'); pg.wait_for_selector('#sapply'); pg.click('#sclear'); pg.click('#sapply'); pg.wait_for_timeout(400)
        pg.evaluate("() => closeSheet()")

        # ---------- 6. 特性列表排序 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow'); pg.wait_for_timeout(600)
        pg.click("[data-k='move7']"); pg.wait_for_timeout(900)
        pg.click('#fsort'); pg.wait_for_selector('#sap2')
        pg.click('#sheetPanel [data-sf="rarity"]'); pg.click('#sap2'); pg.wait_for_timeout(700)
        chk11 = pg.evaluate("""() => {
          const rr = [...document.querySelectorAll('#farea .lrow .nm')].map(el => { const m = el.textContent.match(/SSR|SR|UR|R|N/); return ({UR:5,SSR:4,SR:3,R:2,N:1})[m ? m[0] : 'N'] || 0; });
          return {rr, head: document.querySelector('#farea .subnote').textContent.replace(/\\s+/g,' ')};
        }""")
        print('[特性排序 稀有度]', chk11['rr'], '|', chk11['head'][-30:])
        assert chk11['rr'] and chk11['rr'] == sorted(chk11['rr'], reverse=True), f'特性稀有度倒序不符: {chk11["rr"]}'
        pg.click('#fsort'); pg.wait_for_selector('#sap2')
        pg.click('#sheetPanel [data-sf="id"]'); pg.click('#sap2'); pg.wait_for_timeout(600)
        head2 = pg.evaluate("() => document.querySelector('#farea .subnote').textContent.replace(/\\s+/g,' ')")
        print('[特性复位]', head2[-24:])
        assert '13条 · 7移动' in head2, '特性行数应仍为13'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/52a_sort_feat.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
