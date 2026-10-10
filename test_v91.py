# -*- coding: utf-8 -*-
"""v0.91 验证: 图鉴「图鉴顺序」支持倒序 (sortOrder 写死 ASC 修复)
① 机体图鉴: 顺序=最小id, 倒序=最大id (UI 排序弹窗操作)
② 驾驶员/武器/战舰/零件图鉴: 倒序生效 (武器为多列 w.unit_id,w.id 逐列反向)
③ 切「数值字段」排序不受影响(仍默认倒序), 再切回图鉴顺序正常
④ 特性页 图鉴顺序 倒序 回归(原本正常)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8991

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

        def set_sort(field, d):
            pg.evaluate("() => document.getElementById('sbtn').click()")
            pg.wait_for_timeout(600)
            pg.evaluate(f"() => document.querySelector('#sheetPanel [data-sf=\"{field}\"]').click()")
            pg.wait_for_timeout(400)
            pg.evaluate(f"() => document.querySelector('#sheetPanel [data-sd=\"{d}\"]').click()")
            pg.wait_for_timeout(400)
            pg.evaluate("() => document.getElementById('sap2').click()")
            pg.wait_for_timeout(1500)

        def first_id(sel):
            return pg.evaluate(f"() => {{ const el=document.querySelector({sel!r}); return el ? +el.dataset.id : null; }}")

        def switch_kind(k, wait=1800):
            pg.evaluate(f"() => {{ state.pageLimit = 60; document.querySelector('#kinds [data-k=\"{k}\"]').click(); }}")
            pg.wait_for_timeout(wait)

        pg.evaluate("() => { state.stack=[]; setTab('units'); }")
        pg.wait_for_timeout(2500)

        # ① 机体
        mn = pg.evaluate("() => q1('SELECT MIN(id) c FROM units').c")
        mx = pg.evaluate("() => q1('SELECT MAX(id) c FROM units').c")
        f0 = first_id('.ucard')
        set_sort('id', -1)
        fd = first_id('.ucard')
        lab = pg.evaluate("() => document.getElementById('sbtn').textContent.replace(/\\s+/g,' ')")
        print('[① 机体] min/max:', mn, mx, '| 默认首:', f0, '| 倒序首:', fd, '|', lab)
        assert f0 == mn and fd == mx, (f0, fd, mn, mx)
        assert '倒序' in lab, lab
        set_sort('id', 1)
        f1 = first_id('.ucard')
        print('[① 切回顺序首]', f1)
        assert f1 == mn, f1
        print('[① 机体图鉴顺序倒序 通过]')

        # ② 驾驶员 / 武器 / 战舰 / 零件
        cases = [
            ('char', '#listarea .lrow', "q1('SELECT MIN(id) c FROM characters').c", "q1('SELECT MAX(id) c FROM characters').c"),
            ('weapon', '#listarea .lrow', "q1('SELECT MIN(id) c FROM weapons').c", "q1('SELECT MAX(id) c FROM weapons').c"),
            ('supp', '#listarea .lrow', "q1('SELECT MIN(id) c FROM supporters').c", "q1('SELECT MAX(id) c FROM supporters').c"),
            ('mod', '#listarea .lrow', "q1('SELECT MIN(id) c FROM mods').c", "q1('SELECT MAX(id) c FROM mods').c"),
        ]
        for kind, sel, qmn, qmx in cases:
            switch_kind(kind)
            mn2 = pg.evaluate(f"() => {qmn}"); mx2 = pg.evaluate(f"() => {qmx}")
            a0 = first_id(sel)
            set_sort('id', -1)
            a1 = first_id(sel)
            print(f'[② {kind}] min/max: {mn2} {mx2} | 顺序首: {a0} | 倒序首: {a1}')
            assert a0 == mn2 and a1 == mx2, (kind, a0, a1, mn2, mx2)
            set_sort('id', 1)
            assert first_id(sel) == mn2, kind
        print('[② 驾驶员/武器(多列)/战舰/零件 图鉴顺序倒序 通过]')

        # ③ 数值字段排序不受影响: 武器按威力(默认倒序), 再切回图鉴顺序
        switch_kind('weapon')
        set_sort('power', -1)
        pw0 = pg.evaluate("() => +document.querySelector('#listarea .lrow').dataset.id")
        pwmax = pg.evaluate("() => q1('SELECT w.id x, MAX(w.power) p FROM weapons w').x")
        print('[③ 武器威力倒序 首]', pw0, '| 全库最大威力武器', pwmax)
        assert pw0 == pwmax, (pw0, pwmax)
        set_sort('id', 1)
        assert first_id('#listarea .lrow') == pg.evaluate("() => q1('SELECT MIN(id) c FROM weapons').c")
        set_sort('id', -1)
        assert first_id('#listarea .lrow') == pg.evaluate("() => q1('SELECT MAX(id) c FROM weapons').c")
        print('[③ 数值排序/图鉴顺序切换 通过]')

        # ④ 特性页回归(用户报告本就正常): fsort 图鉴顺序 正/倒序
        pg.evaluate("() => { state.stack=[]; setTab('feat'); }")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelector('[data-k=\"range_up\"]').click()")
        pg.wait_for_timeout(2800)
        pg.evaluate("() => document.getElementById('fsort').click()")
        pg.wait_for_timeout(600)
        pg.evaluate("() => document.querySelector('#sheetPanel [data-sf=\"id\"]').click()")
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.querySelector('#sheetPanel [data-sd=\"1\"]').click()")
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.getElementById('sap2').click()")
        pg.wait_for_timeout(1200)
        fu = pg.evaluate("""() => { const ids=[...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id);
          return { n: ids.length, asc: ids.every((v, i) => i === 0 || ids[i-1] <= v) }; }""")
        print('[④ 特性 range_up 顺序(id升)]', fu)
        assert fu['n'] == 164 and fu['asc'], fu
        pg.evaluate("() => document.getElementById('fsort').click()")
        pg.wait_for_timeout(600)
        pg.evaluate("() => document.querySelector('#sheetPanel [data-sf=\"id\"]').click()")
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.querySelector('#sheetPanel [data-sd=\"-1\"]').click()")
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.getElementById('sap2').click()")
        pg.wait_for_timeout(1200)
        fd2 = pg.evaluate("""() => { const ids=[...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id);
          return { desc: ids.every((v, i) => i === 0 || ids[i-1] >= v), first: ids[0] }; }""")
        print('[④ 特性 range_up 倒序(id降)]', fd2)
        assert fd2['desc'], fd2
        print('[④ 特性页 图鉴顺序倒序 回归 通过]')
        print('=== test_v91 全部通过 ===')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
