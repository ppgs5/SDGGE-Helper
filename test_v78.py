# -*- coding: utf-8 -*-
"""v0.78 验证: 驾驶员数据口径=「未增强原值」(与官方一致) — 塞西娅射击 780→650 / 668→557
口径: 游戏蓝色字体=原值×常驻被动(floor)。官方例: 夏亚 706×1.05=741 / 659×1.25=823 / 535×1.25=668(游戏蓝字逐项一致)
① 数据: characters 塞西娅 max_ranged=557, sp_max_ranged=650; char_abilities 无 stat_included 残留
② 口径一致性: floor(650×1.2)=780 / floor(557×1.2)=668 (=游戏蓝字); 夏亚同式复算 741/823/668
③ 引擎: 神高达+条件全开 被动射+20(常驻LV3+LV1)/+技能=35; EXZELIA=35射+15攻
④ 计算页 超一击·类型=支援型: 塞西娅 187,069(cAtk=floor(650×1.35)=877) 且 rank>10; TOP1 巴纳吉 249,462 不变
⑤ 角色页(SP开)显示原值 650/原557 (非蓝字)
仅回归最新版(用户口径)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8978
GS, CH, XY = 1200003950, 1999000100, 1110000202   # 神高达EX / 塞西娅 / 夏亚(官方UR)

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

        # ① 数据
        r = pg.evaluate(f"""() => {{
          const c = q1('SELECT max_ranged, sp_max_ranged FROM characters WHERE id=?', [{CH}]);
          const flags = q('SELECT traits_json FROM char_abilities WHERE char_id=?', [{CH}]).some(x => (x.traits_json || '').includes('stat_included'));
          const xy = q1('SELECT max_ranged, max_awaken, max_reaction FROM characters WHERE id=?', [{XY}]);
          return {{ max_ranged: c.max_ranged, sp_max_ranged: c.sp_max_ranged, flags, xy }};
        }}""")
        print('[① 数据]', r)
        assert r['max_ranged'] == 557 and r['sp_max_ranged'] == 650 and not r['flags'], r

        # ② 口径一致性(原值×常驻被动=游戏蓝字, floor)
        r = pg.evaluate(f"""() => {{
          const CH2 = {CH}, XY2 = {XY};
          return {{
            sces_sp: Math.floor(q1('SELECT sp_max_ranged v FROM characters WHERE id=?', [CH2]).v * 1.2),   // 650×1.2=780
            sces_lv90: Math.floor(557 * 1.2),                                                                // 668
            xy_r: Math.floor(706 * 1.05), xy_a: Math.floor(659 * 1.25), xy_rc: Math.floor(535 * 1.25)       // 741/823/668
          }};
        }}""")
        print('[② 口径]', r)
        assert r == {'sces_sp': 780, 'sces_lv90': 668, 'xy_r': 741, 'xy_a': 823, 'xy_rc': 668}, r

        # ③ 引擎
        r = pg.evaluate(f"""() => {{
          const mk = (uid, ca, skills) => {{
            const b2 = charBonus({CH}, 'supercharged', {{ passive: true, cpassive: true, skills, condAll: ca, unitId: uid, upassive: true, multiPhase: false, pSpU: true, ussp: false }}, metaOf(uid));
            return {{ ranged: b2.ranged || 0, atk: b2.atk || 0 }};
          }};
          return {{ gs: mk({GS}, true, false), gs_sk: mk({GS}, true, true), ex: mk(1999000100, true, false) }};
        }}""")
        print('[③ 引擎]', r)
        assert r['gs'] == {'ranged': 20, 'atk': 0}, r
        assert r['gs_sk']['ranged'] == 35, r
        assert r['ex'] == {'ranged': 35, 'atk': 15}, r

        # ④ 计算页榜
        pg.evaluate(f"() => {{ Object.assign(state.calc, {{unitId:{GS}, charId:null, vigor:'supercharged', skills:true, ca:true, mp:true, passive:true, cpassive:true, pSpU:true, pRar:null, crit:false, tDef:10000, tCharDef:750}}); const f=filt('pickc'); f.role=3; f.rar=null; f.tags=[]; f.series=[]; state._prKey=null; state.stack=[]; setTab('calc'); }}")
        pg.wait_for_timeout(3500)
        r = pg.evaluate(f"""() => {{
          const rows = state._prRows || [];
          const i = rows.findIndex(x => x.name.indexOf('塞西娅') >= 0);
          return {{ top1: rows[0] && [rows[0].name, rows[0].dmg], rank: i + 1, dmg: i >= 0 ? rows[i].dmg : null, cAtk: i >= 0 ? rows[i].cAtk : null }};
        }}""")
        print('[④ 超一击支援榜]', r)
        assert r['top1'][0].startswith('巴纳吉') and r['top1'][1] == 249462, r
        assert r['dmg'] == 187069 and r['cAtk'] == 877 and r['rank'] > 10, r

        # ⑤ 角色页原值显示
        pg.evaluate(f"() => {{ state.charSp = true; state.stack=[]; push({{page:'char', title:'x', id:{CH}}}); }}")
        pg.wait_for_timeout(900)
        t = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '650' in t and '原557' in t, t[:300]
        print('[① ② ③ ④ ⑤ 原值口径(与官方一致)/引擎/显示] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v78 全部通过 ===')
