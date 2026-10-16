# -*- coding: utf-8 -*-
"""v108 验证: 组队 5/6 top(防御机 eHP/进攻盾) 接「对XX」敌方条件被动 —
   我方防御机/机师 的「发起对战的敌方包含「X」时 攻防提升」按攻方(目标)标签匹配计入 受;
   目标机师/机体 的「对XX」类按我方防御机(+搭配机师)标签匹配
① defenderSkills(1761000101 精神感应高达Mk-Ⅲ) x 通道: {kind defPct, v 25, series 机动战士高达ZZ}
② xMatch: 靶=ZZ高达 1095000100(ZZ系列)→true; 靶=ν高达 1110000100(CCA)→false
③ 受 集成: 靶=ZZ高达 时 _recv[1761000101] 计入 x 防御+25% (r1); 补丁清空 x 通道后 r2; r1 < r2; 恢复后 r1 一致
④ 驾驶员标签条件(ctags): 1400000550「敌方包含「新人类」标签」xMatch 按 ctags 新人类=true / 强化人=false
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9016
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

        # ① x 通道提取
        x1 = pg.evaluate("() => defenderSkills(1761000101, null, false, false, 'mid', true).x")
        print('[① defenderSkills x]', x1)
        assert any(e['kind'] == 'defPct' and e['v'] == 25 and '机动战士高达ZZ' in (e.get('series') or []) for e in x1), x1
        print('[① 「对机动战士高达ZZ系列」防御+25% 进入 x 通道 通过]')

        # ② 匹配
        m = pg.evaluate("""() => { const e = defenderSkills(1761000101, null, false, false, 'mid', true).x[0];
          return { zz: xMatch(e, metaOf(1095000100)), cca: xMatch(e, metaOf(1110000100)) }; }""")
        print('[② xMatch] 靶ZZ:', m['zz'], '| 靶ν(CCA):', m['cca'])
        assert m['zz'] is True and m['cca'] is False, m
        print('[② 按攻方(目标)系列匹配 通过]')

        # ③ 受 集成(同靶同设置, 仅补丁清空 x 通道对比)
        def render_recv(patch):
            pg.evaluate("""(patch) => { window.__origDS = window.__origDS || defenderSkills;
              defenderSkills = patch ? ((uid, cid, s, sp, vg, ca) => { const o = window.__origDS(uid, cid, s, sp, vg, ca); o.x = []; return o; }) : window.__origDS;
              const t = state.team; t.dunit = 1095000100; t.dchar = null; t.guard = false; t.sdef = false; t.ca = true;
              state.stack = []; push({ page:'team', title:'组队' }); render(); }""", patch)
            pg.wait_for_timeout(2600)
            return pg.evaluate("() => (state._recv || {})[1761000101] || null")
        r1 = render_recv(False)
        r2 = render_recv(True)
        r3 = render_recv(False)
        print('[③ 受] 计入x:', r1, '| 清空x:', r2, '| 恢复:', r3)
        assert r1 and r2 and r1 < r2 and r1 == r3, (r1, r2, r3)
        print('[③ 受: 我方防御机「对ZZ敌方防御+25%」按靶标签生效(剔除后受更高) 通过]')

        # ④ ctags(敌方驾驶员标签)匹配
        c = pg.evaluate("""() => { const xs = defenderSkills(1400000550, null, false, false, 'mid', true).x;
          const mk = tags => ({ tags: new Set(), seriesList: new Set(), ctags: new Set(tags) });
          const e = xs.find(x => (x.ctags || []).includes('新人类'));
          return e ? { n: xMatch(e, mk(['新人类'])), o: xMatch(e, mk(['强化人'])), v: e.v } : null; }""")
        print('[④ ctags 敌方驾驶员标签]', c)
        assert c and c['n'] is True and c['o'] is False, c
        print('[④ 「敌方驾驶员含「新人类」标签」按驾驶员标签匹配 通过]')

        assert not errors, errors
        print('=== test_v108 全部通过 ===')
        b.close()
finally:
    srv.terminate()
