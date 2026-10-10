# -*- coding: utf-8 -*-
"""v0.42 验证: SSP移动力+1仅部分机体 — 来自SSP核心解放 status_up(type3/机体状态6); 格拉布罗/00R无, 里格·夏柯有; 7移动=SSP+卡特吉娜"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8977
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

        # ---------- 0. 数据层: sspMovOf 与特性行一致 ----------
        chk = pg.evaluate("""() => {
          const u = id => q1('SELECT * FROM units WHERE id=?', [id]);
          // 全库统计 sspMovOf 分布
          const dist = {};
          for (const r of q('SELECT * FROM units', [])) {
            const m = sspMovOf(r);
            dist[m] = (dist[m] || 0) + 1;
          }
          const mv = (id, feat) => {
            const r = q1('SELECT params_json FROM features WHERE feature=? AND target_id=?', [feat, id]);
            return r ? JSON.parse(r.params_json) : null;
          };
          return {
            dist,
            rigg: sspMovOf(u(1175004910)), garu: sspMovOf(u(1031002900)), oor: sspMovOf(u(1370005900)), f80: sspMovOf(u(1154000100)),
            garu7: mv(1031002900, 'move7'), garu6: mv(1031002900, 'move6'),
            rigg6: mv(1175004910, 'move6'), rigg7: mv(1175004910, 'move7'),
            oor6: mv(1370005900, 'move6'),
          };
        }""")
        print('[数据]', chk)
        assert chk['dist'].get('1') == 621 and chk['dist'].get('2') == 23, f"sspMovOf分布: {chk['dist']}"
        assert chk['rigg'] == 1 and chk['garu'] == 0 and chk['oor'] == 0 and chk['f80'] == 1, 'sspMovOf: 里格1/格拉布罗0/00R0/F801'
        assert chk['garu7'] is None and chk['garu6'] and 'SSP' not in chk['garu6']['desc'], '格拉布罗不应有SSP移动行'
        assert chk['oor6'] is None, '00R 无任何移动行'
        assert 'SSP' in chk['rigg6']['desc'] and chk['rigg7']['pilot'] == 1175000500, '里格·夏柯 SSP行+卡特吉娜行'

        # ---------- 1. 7移动 = SSP+1 且 卡特吉娜+1 (基础5的渣斯卡路系) ----------
        chk2 = pg.evaluate("""() => {
          const rows = q("SELECT f.target_id, f.params_json FROM features f WHERE f.feature='move7'", []);
          return rows.map(r => {
            const p = JSON.parse(r.params_json);
            const u = q1('SELECT * FROM units WHERE id=?', [r.target_id]);
            return {n: u.name, base: u.max_mov, mv: sspMovOf(u), pilot: p.pilot};
          });
        }""")
        print('[7移动构成]', len(chk2), '条')
        assert len(chk2) == 13, '7移动应13条'
        assert all(x['pilot'] == 1175000500 and x['base'] == 5 and x['mv'] == 1 for x in chk2), f'7移动应全为 基础5+SSP1+卡特吉娜1: {chk2}'

        # ---------- 2. 所有SSP移动行与 status_up 一致 ----------
        dep = pg.evaluate("""() => {
          const rows = q("SELECT target_id, params_json FROM features WHERE feature='move6' AND params_json LIKE '%SSP%'", []);
          return rows.filter(r => {
            const u = q1('SELECT * FROM units WHERE id=?', [r.target_id]);
            return sspMovOf(u) <= 0;
          }).length;
        }""")
        print('[SSP行一致性] 无数据行:', dep)
        assert dep == 0, 'SSP移动行必须都有 status_up 数据'

        # ---------- 3. 机体页: 移动 随SSP开关 (仅status_up机体+1) ----------
        def movOf(uid):
            pg.evaluate("(id) => { state.unit = {star: 0, sp: false, ssp: false}; push({page:'unit', title:'x', id}); }", uid)
            pg.wait_for_timeout(700)
            m0 = pg.evaluate("() => document.querySelector('#view .statgrid .stat:nth-child(6)').textContent.replace(/\\s+/g,' ')")
            if pg.query_selector('#uss'):
                pg.click('#uss'); pg.wait_for_timeout(600)
            m1 = pg.evaluate("() => document.querySelector('#view .statgrid .stat:nth-child(6)').textContent.replace(/\\s+/g,' ')")
            return m0, m1
        g0, g1 = movOf(1031002900)   # 格拉布罗: SSP无移动
        print('[格拉布罗 移动]', g0, '→', g1)
        assert g0.startswith('移动6') and g1.startswith('移动6') and '原' not in g1, f'格拉布罗SSP后移动应仍为6: {g1}'
        r0, r1 = movOf(1175004910)   # 里格·夏柯: SSP+1
        print('[里格·夏柯 移动]', r0, '→', r1)
        assert r0.startswith('移动5') and '移动6' in r1 and '原 5' in r1, f'里格·夏柯SSP后应为6(原5): {r1}'
        o0, o1 = movOf(1370005900)   # 00R: SSP无移动
        print('[00R 移动]', o0, '→', o1)
        assert o0.startswith('移动5') and o1.startswith('移动5') and '原' not in o1, f'00R SSP后移动应仍为5: {o1}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/51b_unit_mov_ssp.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
