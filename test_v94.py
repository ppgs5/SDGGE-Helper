# -*- coding: utf-8 -*-
"""v0.94 验证: 图鉴列表「数值口径」档位移入排序弹窗 + 详情页「主被动」改名
① 排序弹窗(机体/驾驶员)含 数值口径: 原值/被动/主被动/max, 默认原值
② 驾驶员列表默认=原值(取消 previously 常开被动): 阿姆罗 1001000100 = 571/532/549/670/669
③ 档位=被动: 阿姆罗 = 658/703/802 (条件支援防御+20%/技能 不计); 西布克 = 748; 主被动 → 926
④ 排序随档位: 觉醒↓+被动 → 列表按被动觉醒非增 (阿姆罗系 897>841>684>658)
⑤ 机体列表: 攻击↓+被动 → 排序按 unitListStat(被动) 非增; 弹窗档位切换后变化生效
⑥ 详情页 chips: 「主被动」(原「主动」) 改名+可点
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8997

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
        pg.evaluate("() => { state.cBstList = 0; state.uBstList = 0; state.charSp = false; state.stack=[]; setTab('units'); }")
        pg.wait_for_timeout(2400)

        def kind(k, wait=1600):
            pg.evaluate(f"() => document.querySelector('#kinds [data-k=\"{k}\"]').click()")
            pg.wait_for_timeout(wait)

        def sbox(v):
            pg.evaluate(f"() => {{ const el=document.getElementById('sbox'); el.value={v!r}; el.dispatchEvent(new Event('input')); }}")
            pg.wait_for_timeout(1300)

        def rows(n=8):
            return pg.evaluate(f"""() => [...document.querySelectorAll('#listarea .lrow')].slice(0,{n}).map(e => ({{ id:+e.dataset.id, t:e.innerText.replace(/\\s+/g,' ') }}))""")

        def open_sort():
            pg.evaluate("() => document.getElementById('sbtn').click()")
            pg.wait_for_timeout(600)

        def pick(field, d, bst=None):
            open_sort()
            if field:
                pg.evaluate(f"() => document.querySelector('#sheetPanel [data-sf=\"{field}\"]').click()")
                pg.wait_for_timeout(300)
            if d is not None:
                pg.evaluate(f"() => document.querySelector('#sheetPanel [data-sd=\"{d}\"]').click()")
                pg.wait_for_timeout(300)
            if bst is not None:
                pg.evaluate(f"() => document.querySelector('#sheetPanel [data-bst=\"{bst}\"]').click()")
                pg.wait_for_timeout(400)
            pg.evaluate("() => document.getElementById('sap2').click()")
            pg.wait_for_timeout(1500)

        # ① 弹窗档位行
        kind('char')
        open_sort()
        br = pg.evaluate("() => ({ bst: [...document.querySelectorAll('#sheetPanel [data-bst]')].map(e => e.textContent.trim()), on: (document.querySelector('#sheetPanel [data-bst].on')||{}).textContent })")
        pg.evaluate("() => document.getElementById('sx').click()")
        pg.wait_for_timeout(400)
        print('[① char弹窗档位]', br)
        assert br['bst'] == ['原值', '被动', '主被动', 'max'] and br['on'] == '原值', br
        # ② 默认原值
        sbox('阿姆罗·雷')
        r0 = [r for r in rows(6) if r['id'] == 1001000100][0]
        print('[② 默认原值]', r0['t'][:70])
        assert '射击571 格斗532 觉醒549 防御670 反应669' in r0['t'], r0
        # ③ 档位=被动 / 主被动
        pick('max_awaken', -1, 1)
        sbox('阿姆罗·雷')
        r1 = [r for r in rows(6) if r['id'] == 1001000100][0]
        print('[③ 被动·阿姆罗1001000100]', r1['t'][:70])
        assert '觉醒658 防御703 反应802' in r1['t'], r1        # 条件(支援防御+20%)与技能不计
        # ④ 排序非增校验(整页可见行): 阿姆罗系应 897>841>684>658
        aw = pg.evaluate("""() => [...document.querySelectorAll('#listarea .lrow')].map(e => {
          const m = e.innerText.replace(/\\s+/g,' ').match(/觉醒(\\d+)/); return +m[1]; })""")
        print('[④ 觉醒序列(间段)]', aw[:6], '… 非增:', all(aw[i] >= aw[i+1] for i in range(len(aw)-1)))
        assert all(aw[i] >= aw[i+1] for i in range(len(aw)-1)), aw[:12]
        sbox('西布克')
        r2 = [r for r in rows(4) if r['id'] == 1162000102][0]
        print('[③ 被动·西布克]', r2['t'][:70])
        assert '射击748' in r2['t'], r2                          # 被动=+5%, 技能+25%不计
        pick(None, None, 2)
        sbox('西布克')
        r3 = [r for r in rows(4) if r['id'] == 1162000102][0]
        print('[③ 主被动·西布克]', r3['t'][:70])
        assert '射击926' in r3['t'] and '觉醒712' in r3['t'], r3  # 主被动=+技能(1.05+0.25)
        # ⑤ 机体列表排序随档位
        kind('unit')
        pick('max_atk', -1, 1)
        top = pg.evaluate("""() => [...document.querySelectorAll('#listarea .ucard')].slice(0,20).map(e => +e.dataset.id)""")
        chk = pg.evaluate(f"""() => {{ const ids = {top};
          const vs = ids.map(id => unitListStat(q1('SELECT * FROM units WHERE id=?', [id]), 'atk', 1, unitStarSel()));
          const best = q('SELECT * FROM units').reduce((a, u) => {{ const v = unitListStat(u, 'atk', 1, unitStarSel()); return v > a.v ? {{ id: u.id, v }} : a; }}, {{ v: -1 }});
          return {{ vs, first: ids[0], best: best.id, noninc: vs.every((v, i) => i === 0 || vs[i-1] >= v) }}; }}""")
        print('[⑤ 机体 攻击↓+被动] first/best:', chk['first'], chk['best'], '非增:', chk['noninc'], chk['vs'][:6])
        assert chk['first'] == chk['best'] and chk['noninc'], chk
        pick(None, None, 0)
        top0 = pg.evaluate("""() => [...document.querySelectorAll('#listarea .ucard')].slice(0,3).map(e => +e.dataset.id)""")
        print('[⑤ 回原值 前3]', top0)
        # ⑥ 详情页改名
        pg.evaluate("() => { state.stack=[]; push({page:'char', title:'x', id:1162000102}); }")
        pg.wait_for_timeout(1500)
        c2 = pg.evaluate("() => document.getElementById('cbst2').textContent.trim()")
        assert c2 == '主被动', c2
        pg.evaluate("() => document.getElementById('cbst2').click()")
        pg.wait_for_timeout(1000)
        v = pg.evaluate("""() => ({ bst: state.charBst, txt: [...document.querySelectorAll('.statgrid .stat')].slice(0,1)[0].querySelector('.v').innerText.trim() })""")
        print('[⑥ 驾驶员页 主被动]', v)
        assert v['bst'] == 2 and v['txt'].startswith('926'), v
        pg.evaluate("() => { state.stack=[]; push({page:'unit', title:'x', id:1001000100}); }")
        pg.wait_for_timeout(1600)
        u2 = pg.evaluate("() => document.getElementById('ubst2').textContent.trim()")
        print('[⑥ 机体页 chips]', u2)
        assert u2 == '主被动', u2
        pg.evaluate("() => { state.charBst = 0; }")
        print('=== test_v94 全部通过 ===')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
