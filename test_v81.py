# -*- coding: utf-8 -*-
"""v0.81 验证: ①eHP行显示双支援防御(支援防御+2)最优驾驶员 ②组队各TOP折叠(跳转返回保持)
③计算页驾驶员行[选择/详情]按钮(行点击不再选中) ④机体页地形适性○△×
① eHP行尾「支防+2 X 防御N」: X可搭乘该机体且 supCountsOf(def)>=2, 防御值=候选最高
② 六个折叠key; 折叠→display:none; push/pop后保持折叠; 再点展开
③ [data-csel]/[data-cdet]; 详情→角色页; 选择→charId; .nm点击不选中
④ EXZELIA 宇宙○空中○地上○水面×水中△; Mk-Ⅲ 空中×; 图例「○正常移动 △移动力减半 ×不能出击」
仅回归最新版(用户口径)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8981

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
        pg.evaluate("() => { state.team.suppId = 1125000250; state.team.shipStar = 0; state.stack = []; setTab('team'); }")
        pg.wait_for_timeout(4500)

        # ---------- ① 双支援防御驾驶员 ----------
        r = pg.evaluate("""() => {
          const ehp = [...document.querySelectorAll('#tarea .card')].find(c => c.querySelector('h4') && c.querySelector('h4').textContent.includes('有效耐久 eHP'));
          const row = ehp.querySelector('.trow');
          const uid = +row.dataset.id, sdid = +row.dataset.sdef;
          if (!sdid) return { found: false, txt: row.textContent.replace(/\s+/g,' ').slice(0, 150) };
          const c = q1('SELECT id, name, role, rarity, max_defense, sp_max_defense FROM characters WHERE id=?', [sdid]);
          const sup = supCountsOf(sdid, uid, 'mid', true, true);
          return { found: true, id: sdid, cname: c.name, txt: row.textContent.replace(/\s+/g,' '), can: pilotCanDrive(sdid, uid), supDef: sup.def };
        }""")
        print('[① eHP支防驾驶员]', r['id'], r['cname'], r['can'], r['supDef'])
        assert r['found'] and r['can'] and r['supDef'] >= 2, r
        import re as _re
        m0 = _re.search(r'支防\+2 (\S+) (.*?) eHP', r['txt'])
        assert m0 and m0.group(1) == r['cname'] and '守备' in m0.group(2), (m0, r['txt'])
        # 防御值 = 候选最高(枚举验证)
        top = pg.evaluate(f"""() => {{
          const uid = document.querySelector('#tarea .card .trow').dataset.id;
          return +uid;
        }}""")
        ok = pg.evaluate(f"""() => {{
          const uid = {top};
          const so = charSupEntries();
          const u = q1('SELECT max_hp FROM units WHERE id=?', [uid]);
          const df0 = Math.floor(u.max_hp * 1.4);   // 仅用于权重(同行为常数)
          const ub = defenderSkills(uid, null, true, false);
          let best = -1; const ids = [];
          for (const cid of new Set([...Object.keys(so.base), ...Object.keys(so.sp)])) {{
            const lst = mergeSp(so.base[cid] || [], so.sp[cid] || []);
            if (lst.filter(p => p.kind === 'def').length < 2) continue;
            if (!pilotCanDrive(+cid, uid)) continue;
            if (supCountsOf(+cid, uid, 'mid', true, true).def < 2) continue;
            const c = q1('SELECT id,name,rarity,max_defense,sp_max_defense FROM characters WHERE id=?', [+cid]);
            const dk = defenderSkills(uid, +cid, true, false);
            const dPct = dk.defPct - ub.defPct, cPct = dk.cdefPct - ub.cdefPct, rPct = dk.redPct - ub.redPct;
            const guardEff = Math.round(pStat(c, 'defense', true) * (1 + cPct / 100));
            const score = Math.round(df0 * dPct / 100) + guardEff + rPct * 10;
            if (score > best) {{ best = score; ids.length = 0; ids.push(+cid); }}
            else if (score === best) ids.push(+cid);
          }}
          return {{ best, ids }};
        }}""")
        print('[① 综合防御最高]', ok)
        assert r['id'] in ok['ids'], (r, ok)
        print('[① eHP行双支援防御最优驾驶员] 通过')

        # ---------- ② 折叠 ----------
        folds = pg.evaluate("() => [...document.querySelectorAll('#tarea [data-fold]')].map(x => x.dataset.fold)")
        assert set(folds) == {'team_atk','team_atsup','team_sup','team_defout','team_dehp','team_cs'}, folds
        pg.evaluate("() => document.querySelector('[data-fold=\"team_sup\"]').click()"); pg.wait_for_timeout(300)
        assert pg.evaluate("() => document.querySelector('[data-fbody=\"team_sup\"]').style.display") == 'none'
        pg.evaluate("() => document.querySelector('#tarea .trow').click()"); pg.wait_for_timeout(900)
        pg.evaluate("() => pop()"); pg.wait_for_timeout(4500)
        st = pg.evaluate("() => ({ f: state.teamFold.team_sup, d: document.querySelector('[data-fbody=\"team_sup\"]').style.display, t: document.querySelector('[data-fold=\"team_sup\"]').textContent.trim() })")
        print('[② 返回后]', st)
        assert st['f'] is True and st['d'] == 'none' and st['t'] == '▸ 展开', st
        pg.evaluate("() => document.querySelector('[data-fold=\"team_sup\"]').click()"); pg.wait_for_timeout(200)
        assert pg.evaluate("() => document.querySelector('[data-fbody=\"team_sup\"]').style.display") == ''
        print('[② 六区折叠/返回保持/展开] 通过')

        # ---------- ③ 计算页 选择/详情 ----------
        pg.evaluate("() => { state.calc.unitId = 1200003950; state.calc.charId = null; state.stack = []; setTab('calc'); }")
        pg.wait_for_timeout(3500)
        r = pg.evaluate("""() => {
          const row = document.querySelector('#view .trow[data-pid]');
          return { sel: !!row.querySelector('[data-csel]'), det: !!row.querySelector('[data-cdet]'),
                   sub: [...document.querySelectorAll('#view .subnote')].some(x => x.textContent.includes('「选择」')) };
        }""")
        print('[③ 按钮]', r)
        assert r['sel'] and r['det'] and r['sub'], r
        pg.evaluate("() => document.querySelector('#view .trow[data-pid] .nm').click()"); pg.wait_for_timeout(400)
        assert pg.evaluate("() => state.calc.charId") is None, '行点击不应再选中'
        pg.evaluate("() => document.querySelector('#view .trow [data-cdet]').click()"); pg.wait_for_timeout(1000)
        assert pg.evaluate("() => document.querySelector('#view').textContent.includes('技能')"), '详情应跳角色页'
        pg.evaluate("() => pop()"); pg.wait_for_timeout(1500)
        pg.evaluate("() => document.querySelector('#view .trow [data-csel]').click()"); pg.wait_for_timeout(900)
        cid = pg.evaluate("() => state.calc.charId")
        assert cid and cid > 0, cid
        print('[③ 选择/详情按钮(行点击不再选中)] 通过')

        # ---------- ④ 地形适性 ----------
        def terrain(uid):
            pg.evaluate(f"() => {{ state.stack=[]; push({{page:'unit', title:'x', id:{uid}}}); }}")
            pg.wait_for_timeout(900)
            return pg.evaluate("() => { const el = [...document.querySelectorAll('#view .chips')].find(c => c.textContent.includes('地形')); return el ? el.textContent.replace(/\\s+/g,' ') : null; }")
        t1 = terrain(1999000100)
        print('[④ EXZELIA]', t1)
        assert '宇宙 ○' in t1 and '空中 ○' in t1 and '地上 ○' in t1 and '水面 ×' in t1 and '水中 △' in t1, t1
        assert '○正常移动' in t1 and '△移动力减半' in t1 and '×不能出击' in t1, t1
        t2 = terrain(1761000102)
        print('[④ Mk-Ⅲ]', t2)
        assert '空中 ×' in t2 and '宇宙 ○' in t2, t2
        print('[④ 地形适性○△×(图例)] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v81 全部通过 ===')
