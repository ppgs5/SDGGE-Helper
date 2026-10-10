# -*- coding: utf-8 -*-
"""v0.95 验证: 机体排序「星数(突破)」选择 + 头像下方显示当前排序字段数值
① 机体排序弹窗含 星数 ★0-★3(默认★3, ULT固定值不受星数); 驾驶员弹窗无星数行
② 机体 攻击↓: ★3/★0 首卡=各口径全库最大(ULT不乘星 → 排序会变); 卡片显示「攻击力 N」
③ ULT(SECOND V/β·阿吉尔): ★3 与 ★0 值相同(不乘倍率)
④ 驾驶员行 头像下方显示当前排序字段值(随档位/SP): 觉醒↓+被动=「觉醒 970」; 非数值排序不显示
⑤ 组合: 攻击↓+★3+被动 first==best
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8999

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
        pg.evaluate("() => { state.cBstList=0; state.uBstList=0; delete state.uStarList; state.charSp=false; state.stack=[]; setTab('units'); }")
        pg.wait_for_timeout(2400)

        def open_sort():
            pg.evaluate("() => document.getElementById('sbtn').click()")
            pg.wait_for_timeout(600)

        def pick(field=None, d=None, bst=None, star=None):
            open_sort()
            if field:
                pg.evaluate(f"() => document.querySelector('#sheetPanel [data-sf=\"{field}\"]').click()")
                pg.wait_for_timeout(300)
            if d is not None:
                pg.evaluate(f"() => document.querySelector('#sheetPanel [data-sd=\"{d}\"]').click()")
                pg.wait_for_timeout(300)
            if bst is not None:
                pg.evaluate(f"() => document.querySelector('#sheetPanel [data-bst=\"{bst}\"]').click()")
                pg.wait_for_timeout(300)
            if star is not None:
                pg.evaluate(f"() => document.querySelector('#sheetPanel [data-star=\"{star}\"]').click()")
                pg.wait_for_timeout(300)
            pg.evaluate("() => document.getElementById('sap2').click()")
            pg.wait_for_timeout(1500)

        def ucard_first():
            return pg.evaluate("""() => { const el=document.querySelector('#listarea .ucard');
              return { id:+el.dataset.id, v:(el.querySelector('.uval')||{}).textContent }; }""")

        # ① 弹窗星数行
        open_sort()
        d = pg.evaluate("""() => ({ star: [...document.querySelectorAll('#sheetPanel [data-star]')].map(e => e.textContent.trim()),
          on: (document.querySelector('#sheetPanel [data-star].on') || {}).textContent,
          bst: [...document.querySelectorAll('#sheetPanel [data-bst]')].map(e => e.textContent.trim()) })""")
        pg.evaluate("() => document.getElementById('sx').click()")
        pg.wait_for_timeout(400)
        print('[① 机体弹窗]', d)
        assert d['star'] == ['★0', '★1', '★2', '★3'] and d['on'] == '★3' and d['bst'] == ['原值', '被动', '主被动', 'max'], d
        pg.evaluate("() => document.querySelector('#kinds [data-k=\"char\"]').click()")
        pg.wait_for_timeout(1500)
        open_sort()
        nd = pg.evaluate("() => document.querySelectorAll('#sheetPanel [data-star]').length")
        pg.evaluate("() => document.getElementById('sx').click()")
        pg.wait_for_timeout(400)
        print('[① 驾驶员弹窗星数行数]', nd)
        assert nd == 0, nd
        print('[① 机体星数★0-★3(默认★3) · 驾驶员无星数 通过]')

        # ② 攻击↓ ★3 / ★0
        pg.evaluate("() => document.querySelector('#kinds [data-k=\"unit\"]').click()")
        pg.wait_for_timeout(1400)
        pick('max_atk', -1)
        chk = pg.evaluate("""() => { const best = q('SELECT * FROM units').reduce((a, u) => { const v = unitListStat(u, 'atk', 0, unitStarSel()); return v > a.v ? { id: u.id, v } : a; }, { v: -1 });
          const ids = [...document.querySelectorAll('#listarea .ucard')].slice(0, 20).map(e => +e.dataset.id);
          const vs = ids.map(id => unitListStat(q1('SELECT * FROM units WHERE id=?', [id]), 'atk', 0, unitStarSel()));
          return { best: best.id, bestv: best.v, noninc: vs.every((v, i) => i === 0 || vs[i - 1] >= v) }; }""")
        f3 = ucard_first()
        print('[② ★3 首卡]', f3, '| best:', chk)
        assert f3['id'] == chk['best'] and f3['v'] == '攻击力 ' + str(chk['bestv']) and chk['noninc'], (f3, chk)
        pick(None, None, None, 0)
        chk0 = pg.evaluate("""() => q('SELECT * FROM units').reduce((a, u) => { const v = unitListStat(u, 'atk', 0, 0); return v > a.v ? { id: u.id, v } : a; }, { v: -1 })""")
        f0 = ucard_first()
        print('[② ★0 首卡]', f0, '| best0:', chk0)
        assert f0['id'] == chk0['id'] and f0['v'] == '攻击力 ' + str(chk0['v']), (f0, chk0)
        assert f3['id'] != f0['id'], (f3, f0)        # ULT(不乘星) → 首卡随星数变化
        print('[② 攻击↓ 星数切换排序/卡片值 通过]')

        # ③ ULT 不乘星
        pg.evaluate("() => { const el=document.getElementById('sbox'); el.value='SECOND V'; el.dispatchEvent(new Event('input')); }")
        pg.wait_for_timeout(1400)
        pick(None, None, None, 3)
        s3 = pg.evaluate("() => [...document.querySelectorAll('#listarea .ucard')].map(e => ({ id:+e.dataset.id, v:(e.querySelector('.uval')||{}).textContent }))")
        pick(None, None, None, 0)
        s0 = pg.evaluate("() => [...document.querySelectorAll('#listarea .ucard')].map(e => ({ id:+e.dataset.id, v:(e.querySelector('.uval')||{}).textContent }))")
        print('[③ SECOND V ★3 vs ★0]', s3, s0)
        assert s3 == s0 and s3[0] == {'id': 1175001202, 'v': '攻击力 10244'}, (s3, s0)
        pg.evaluate("() => { const el=document.getElementById('sbox'); el.value=''; el.dispatchEvent(new Event('input')); }")
        pg.wait_for_timeout(1300)
        # 组合 ⑤: 攻击↓+★3+被动
        pick(None, None, 1, 3)
        c5 = pg.evaluate("""() => { const best = q('SELECT * FROM units').reduce((a, u) => { const v = unitListStat(u, 'atk', 1, unitStarSel()); return v > a.v ? { id: u.id, v } : a; }, { v: -1 });
          const el = document.querySelector('#listarea .ucard');
          return { best: best.id, bestv: best.v, first: +el.dataset.id, v: (el.querySelector('.uval')||{}).textContent }; }""")
        print('[⑤ ★3+被动 首卡]', c5)
        assert c5['first'] == c5['best'] and c5['v'] == '攻击力 ' + str(c5['bestv']), c5
        pg.evaluate("() => { const el=document.getElementById('sbox'); el.value=''; el.dispatchEvent(new Event('input')); }")
        pg.wait_for_timeout(1200)
        pick(None, None, 0, 3)

        # ④ 驾驶员行头像下数值
        pg.evaluate("() => document.querySelector('#kinds [data-k=\"char\"]').click()")
        pg.wait_for_timeout(1500)
        pick('max_awaken', -1, 1)
        r = pg.evaluate("""() => { const el = [...document.querySelectorAll('#listarea .lrow')][0];
          const best = q('SELECT * FROM characters').reduce((a, c) => { const v = charListStat(c, 'awaken', 1, false); return v > a.v ? { id: c.id, v } : a; }, { v: -1 });
          const vs = [...document.querySelectorAll('#listarea .lrow')].map(e => charListStat(q1('SELECT * FROM characters WHERE id=?', [+e.dataset.id]), 'awaken', 1, false));
          return { av: (el.querySelector('.avval')||{}).textContent, id: +el.dataset.id, best: best.id, bestv: best.v,
                   noninc: vs.every((v, i) => i === 0 || vs[i - 1] >= v) }; }""")
        print('[④ 觉醒↓+被动 首行]', r)
        assert r['av'] == '觉醒 ' + str(r['bestv']) and r['id'] == r['best'] and r['noninc'], r
        pick('id', 1)
        assert pg.evaluate("() => document.querySelectorAll('#listarea .avval').length") == 0
        pg.evaluate("() => document.querySelector('#kinds [data-k=\"unit\"]').click()")
        pg.wait_for_timeout(1400)
        pick('id', 1)
        assert pg.evaluate("() => document.querySelectorAll('#listarea .uval').length") == 0
        print('[④ 头像下排序值(驾驶员 avval/机体 uval, 非数值排序不显示) 通过]')
        pg.evaluate("() => { state.cBstList = 0; state.uBstList = 0; delete state.uStarList; }")
        print('=== test_v95 全部通过 ===')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
