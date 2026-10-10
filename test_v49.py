# -*- coding: utf-8 -*-
"""v0.49 验证: ①特性-支援攻击+2/支援防御+2 排序按钮可点击(修 fctxb 作用域bug), 排序字段=次数+驾驶员参数(射击/格斗/觉醒/防御/反应) ②特性列表头部 标签/系列+排序 按钮同组对齐(不再散落错位)"""
import subprocess, time
from playwright.sync_api import sync_playwright

PORT = 8993
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
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow'); pg.wait_for_timeout(500)

        # ---------- ① 支援攻击+2: 排序按钮可点 + 字段含驾驶员参数 ----------
        pg.click("[data-k='support_atk']"); pg.wait_for_timeout(1000)
        n0 = pg.evaluate("() => [...document.querySelectorAll('#farea .lrow .val')].map(e => +e.textContent.replace('+',''))")
        print('[默认 次数倒序]', n0[:8])
        assert n0 and n0 == sorted(n0, reverse=True), f'默认应按次数倒序: {n0}'
        pg.click('#fsort'); pg.wait_for_selector('#sap2', timeout=15000)   # 修复前: ReferenceError fctxb, 弹窗不出现
        fields = pg.evaluate("() => [...document.querySelectorAll('#sheetPanel [data-sf]')].map(e => e.dataset.sf + ':' + e.textContent.trim())")
        print('[排序字段]', fields)
        assert fields == ['n:次数', 'id:图鉴顺序', 'name:名称', 'rarity:稀有度', 'max_ranged:射击', 'max_melee:格斗', 'max_awaken:觉醒', 'max_defense:防御力', 'max_reaction:反应'], f'字段错误: {fields}'
        pg.click("#sheetPanel [data-sf='max_melee']"); pg.click('#sap2'); pg.wait_for_timeout(1000)
        chk = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#farea .lrow')];
          const vals = rows.map(el => { const c = q1('SELECT rarity, max_melee, sp_max_melee FROM characters WHERE id=?', [+el.dataset.id]);
            return (c.rarity <= 4 && c.sp_max_melee != null) ? c.sp_max_melee : c.max_melee; });   // SP开(特性页默认)→非UR按sp数值
          return {vals, label: document.querySelector('#fsort').textContent.replace(/\\s+/g,' ').trim()};
        }""")
        print('[按格斗排序]', chk['label'], chk['vals'][:8])
        assert chk['vals'] == sorted(chk['vals'], reverse=True), f'格斗倒序不符: {chk}'
        assert '格斗' in chk['label'] and '倒序' in chk['label'], chk['label']
        pg.click('#fsort'); pg.wait_for_selector('#sap2')
        pg.click("#sheetPanel [data-sf='n']"); pg.click('#sap2'); pg.wait_for_timeout(900)
        n1 = pg.evaluate("() => [...document.querySelectorAll('#farea .lrow .val')].map(e => +e.textContent.replace('+',''))")
        print('[切回 次数]', n1[:8])
        assert n1 and n1 == sorted(n1, reverse=True), f'次数排序不符: {n1}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/55b_sup_sort.png')
        # 支援防御+2 同样可点
        pg.click("[data-k='support_def']"); pg.wait_for_timeout(1000)
        pg.click('#fsort'); pg.wait_for_selector('#sap2', timeout=15000)
        fs2 = pg.evaluate("() => [...document.querySelectorAll('#sheetPanel [data-sf]')].map(e => e.dataset.sf).join(',')")
        print('[支援防御 字段]', fs2)
        assert fs2 == 'n,id,name,rarity,max_ranged,max_melee,max_awaken,max_defense,max_reaction', f'支援防御字段缺失: {fs2}'
        pg.click('#sx'); pg.wait_for_timeout(600)

        # ---------- ② 头部按钮对齐(标签/系列+排序 同组同行) ----------
        for kind, wait in [('support_atk', 1000), ('ally_buff_self', 900), ('team_buff', 1200), ('unit_skill', 900), ('move7', 900)]:
            pg.click(f"[data-k='{kind}']"); pg.wait_for_timeout(wait)
            g = pg.evaluate("""() => {
              const ft = document.getElementById('ftag'), fs = document.getElementById('fsort');
              const sn = document.querySelector('#farea .subnote');
              if (!ft || !fs || !sn) return {missing: true};
              const a = ft.getBoundingClientRect(), b = fs.getBoundingClientRect(), s = sn.getBoundingClientRect();
              return {sameLine: Math.abs(a.top - b.top) < 5, gap: Math.round(b.left - a.right),
                      noOverlap: (b.top - a.top) > -2 && (a.top - b.top) > -2,
                      inBox: a.left >= s.left - 1 && b.right <= s.right + 1};
            }""")
            print(f'[头部对齐 {kind}]', g)
            assert g.get('sameLine') and 4 <= g.get('gap', 0) <= 12 and g.get('inBox'), f'{kind} 按钮应同组对齐: {g}'
        pg.click("[data-k='ally_buff_self']"); pg.wait_for_timeout(700)
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/55a_feat_header.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
