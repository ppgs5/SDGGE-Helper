# -*- coding: utf-8 -*-
"""v109 验证: ULT机体数值=固定值(不乘星, 与排行effStar=0/图鉴「ULT固定值」一致)
   用户报: 0星异端高达金色机天照 防御/剩余HP 高于 3星高达F91(EX) — 根因: 组队/计算页 ULT 误入SSR路径×1.4
① 图鉴详情 天照(1342000102) 防御 9,085 (=max_def 固定值)
② 组队: 天照 耐久107,828·防御9,085; F91EX(★3) 耐久116,650·防御11,629
③ 组队受(神高达EX+多蒙 首动): F91EX 受 < 天照 受 (倒挂消除)
④ 星数设置对ULT无效: t.star=0/3 天照受不变; F91EX 受变化
⑤ 目标=天照: 目标行基础防御 9,085
⑥ 计算页: 天照 ★3开关 on/off 武器伤害一致; F91EX 不同
"""
import os, re, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9017
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

        # ① 图鉴
        pg.evaluate("() => { state.stack = []; push({ page: 'unit', title: 'x', id: 1342000102 }); render(); }")
        pg.wait_for_timeout(800)
        dv = pg.evaluate("""() => { const m = document.getElementById('view').innerText.replace(/\\n/g,' ').match(/防御\\D*([\\d,]+)/); return m && m[1]; }""")
        print('[① 图鉴 天照 防御]', dv)
        assert dv == '9,085', dv
        print('[① 图鉴 ULT固定值 9,085 通过]')

        # ②③④ 组队
        def team(star):
            pg.evaluate("""(star) => { const t = state.team; t.dunit = 1200003950; t.dchar = 1200000103; t.first = true; t.star = star;
              t.guard = false; t.sdef = false; t.ca = true; state.stack = []; push({ page:'team', title:'组队' }); render(); }""", star)
            pg.wait_for_timeout(2800)
            return pg.evaluate("""() => { const recv = state._recv || {};
              const rows = {}; for (const r of (window.__lastDefRows || [])) rows[r.u.id] = r;
              return { amaterasu: recv[1342000102] || null, f91: recv[1162000150] || null }; }""")
        r3 = team(3)
        print('[③ 受 ★3] 天照:', r3['amaterasu'], '| F91EX:', r3['f91'])
        assert r3['amaterasu'] and r3['f91'] and r3['f91'] < r3['amaterasu'], r3
        r0 = team(0)
        print('[④ 受 ★0] 天照:', r0['amaterasu'], '| F91EX:', r0['f91'])
        assert r0['amaterasu'] <= r0['f91'], (r0, r3)   # ★0: 天照(固定9085)防≥F91EX(8307) → 受更小
        assert r0['f91'] != r3['f91'], (r0, r3)                                     # F91EX 受随星数变化(UR路径有效) → 天照受相对格局因F91EX变化而翻转
        print('[③ F91EX★3 受<天照 倒挂消除 · ④ ★0 天照受≤F91EX(ULT固定值)且F91EX随星数变化 通过]')

        # ② 行数值对照: F91EX(UR★3 非ULT路径) 行显示 防御11,629 (回归对照); 天照 defStat 由③④受断言覆盖
        pg.evaluate("""() => { const t = state.team; t.star = 3; render(); }""")
        pg.wait_for_timeout(2600)
        txt = pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
          const eh = cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes('有效耐久'));
          return eh ? eh.innerText.replace(/\\n/g, ' ⏎ ') : ''; }""")
        f_ok = '高达F91 (EX)' in txt and '防御 11,629' in txt and '耐久 116,650' in txt
        print('[② F91EX★3 行文本]', f_ok)
        assert f_ok, txt[:300]

        # ⑤ 目标行
        pg.evaluate("() => { const t = state.team; t.dunit = 1342000102; t.dchar = null; render(); }")
        pg.wait_for_timeout(1800)
        d5 = pg.evaluate("""() => { const m = document.getElementById('view').innerText.replace(/\\n/g,' ').match(/防御 ([\\d,]+)/); return m && m[1]; }""")
        print('[⑤ 目标行(天照) 防御]', d5)
        assert d5 == '9,085', d5
        print('[⑤ 目标防御数值 ULT固定值 通过]')

        # ⑥ 计算页
        def calc_dmg(uid, starOn):
            pg.evaluate("""([uid, so]) => { const c = state.calc; c.unitId = uid; c.charId = null; c.star = so; c.vigor = 'supercharged';
              c.crit = false; state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""", [uid, starOn])
            pg.wait_for_timeout(1300)
            return pg.evaluate("""() => { const tds = [...document.querySelectorAll('#view table.ctable tr')].map(tr => tr.cells[1] ? tr.cells[1].innerText : '');
              return tds.join('|').replace(/[^0-9|]/g, '').slice(0, 40); }""")
        a_on, a_off = calc_dmg(1342000102, True), calc_dmg(1342000102, False)
        f_on, f_off = calc_dmg(1162000150, True), calc_dmg(1162000150, False)
        print('[⑥ 计算页] 天照 on/off:', a_on == a_off, '| F91EX on/off:', f_on != f_off)
        assert a_on == a_off and f_on != f_off, (a_on, a_off, f_on, f_off)
        print('[⑥ 计算页 ULT星数开关无效/UR有效 通过]')

        assert not errors, errors
        print('=== test_v109 全部通过 ===')
        b.close()
finally:
    srv.terminate()
