# -*- coding: utf-8 -*-
"""v0.82 验证: ①折叠按钮统一最右 ②支防推荐改为「综合防御能力」(含被动: 支援防御时防御力提升/守备值提升/标签减伤)
③防御eHP行显示驾驶员头像(与其他top一致)
① 六区 h4 display:flex 且 fold 按钮贴右边缘(<14px)
② 推荐评分 = round(机体防御×ΣdefPct/100) + round(守备×(1+cdefPct/100)) + ΣredPct×10 (defenderSkills 含SupportDefense门控);
   data-sdef 驾驶员=全候选最高分; 行内显示 防+N%/守备M(+%)/减伤% 与之一致; 至少一行非阿姆罗(脑波传导差异)
③ eHP 行 .ticon-col 内含 .avw.avsm 驾驶员头像
④ 组队出击场地 ⑤ 排行出击场地(×剔除/△红框)
⑥ 水中伤害折算: uwMult(SSP MAP 50 / 法卢西亚浮游炮 SSP 0 / fx文本 50 / 普通 100) + terrDamage 单测 +
   排行 MAP 视图 e2e: 同武器行 dmg_water == floor(dmg_plain×uwMult/100), 行内显示「水中伤害减半」标记
仅回归最新版(用户口径)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8982

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
        pg.wait_for_timeout(6500)

        # ---------- ① 折叠按钮最右 ----------
        r = pg.evaluate("""() => {
          return [...document.querySelectorAll('#tarea [data-fold]')].map(fb => {
            const h4 = fb.closest('h4');
            const hr = h4.getBoundingClientRect(), fr = fb.getBoundingClientRect();
            return { k: fb.dataset.fold, flex: getComputedStyle(h4).display === 'flex', right: (hr.right - fr.right) < 14, last: h4.lastElementChild === fb };
          });
        }""")
        print('[① 折叠按钮位置]', r)
        assert len(r) == 6 and all(x['flex'] and x['right'] and x['last'] for x in r), r
        print('[① 六区折叠按钮统一最右] 通过')

        # ---------- ② 综合防御推荐 ----------
        data = pg.evaluate("""() => [...[...document.querySelectorAll('#tarea .card')].find(c => c.querySelector('h4') && c.querySelector('h4').textContent.includes('有效耐久 eHP')).querySelectorAll('.trow')]
          .map(r => ({ id: +r.dataset.id, sd: +r.dataset.sdef, t: r.textContent.replace(/\\s+/g,' ') }))""")
        print('[② eHP首4行]')
        for x in data[:4]: print('   ', x['t'][:125])
        assert data and all(x['sd'] for x in data), '每行应有 data-sdef'
        chk = pg.evaluate("""() => {
          const row = [...[...document.querySelectorAll('#tarea .card')].find(c => c.querySelector('h4') && c.querySelector('h4').textContent.includes('有效耐久 eHP')).querySelectorAll('.trow')][0];
          const uid = +row.dataset.id, sdid = +row.dataset.sdef;
          const so = charSupEntries();
          const ub = defenderSkills(uid, null, true, false);
          const scoreOf = cid => {
            const c = q1('SELECT id,name,rarity,max_defense,sp_max_defense FROM characters WHERE id=?', [cid]);
            const dk = defenderSkills(uid, cid, true, false);
            const dPct = dk.defPct - ub.defPct, cPct = dk.cdefPct - ub.cdefPct, rPct = dk.redPct - ub.redPct;
            const guardEff = Math.round(pStat(c, 'defense', true) * (1 + cPct / 100));
            return { dPct, cPct, rPct, guardEff, score: dPct * 1000 + guardEff + rPct * 10 };
          };
          let best = -1; const ids = [];
          for (const cid of new Set([...Object.keys(so.base), ...Object.keys(so.sp)])) {
            const lst = mergeSp(so.base[cid] || [], so.sp[cid] || []);
            if (lst.filter(p => p.kind === 'def').length < 2) continue;
            if (!pilotCanDrive(+cid, uid)) continue;
            if (supCountsOf(+cid, uid, 'mid', true, true).def < 2) continue;
            const sc = scoreOf(+cid);
            if (sc.score > best) { best = sc.score; ids.length = 0; ids.push(+cid); }
            else if (sc.score === best) ids.push(+cid);
          }
          return { inTop: ids.includes(sdid), mine: scoreOf(sdid), best };
        }""")
        print('[② 首行校验]', chk)
        import re as _re
        m0 = _re.search(r'支防\+2 (\S+) (.*?) eHP', data[0]['t'])
        print('[② 首行解析]', m0.groups() if m0 else None)
        assert m0 and '守备' in m0.group(2), data[0]['t']
        assert chk['inTop'], chk
        names = [x['t'].split('支防+2 ')[1].split(' ')[0] for x in data if '支防+2 ' in x['t']]
        print('[② 各行驾驶员]', names)
        assert any(n != '阿姆罗·雷' for n in names), names
        f91 = next(x for x in data if 'F91' in x['t'])
        assert '阿姆罗·雷' in f91['t'] and '防+40%' in f91['t'], f91['t']
        print('[② 综合防御推荐(含被动/按机体变化/非全阿姆罗)] 通过')

        # ---------- ③ 驾驶员头像 ----------
        av = pg.evaluate("""() => [...[...document.querySelectorAll('#tarea .card')]
          .find(c => c.querySelector('h4') && c.querySelector('h4').textContent.includes('有效耐久 eHP')).querySelectorAll('.trow')]
          .every(r => !!r.querySelector('.ticon-col .avw.avsm .picon'))""")
        print('[③ 行内头像]', av)
        assert av, 'eHP行应含驾驶员头像'
        print('[③ 防御eHP行驾驶员头像] 通过')

        # ---------- ④ 组队·出击场地(×剔除/△红框/名称统一为地上) ----------
        pg.evaluate("() => { state.stack=[]; setTab('team'); }")
        pg.wait_for_timeout(6500)
        r0 = pg.evaluate("() => ({ terr: state.team.terr, chips: [...document.querySelectorAll('[data-tterr]')].map(x => x.textContent), halfN: document.querySelectorAll('#tarea .trow.halfmove').length })")
        print('[④ 场地chips]', r0)
        assert r0['chips'] == ['无限制', '宇宙', '空中', '地上', '水面', '水中'], r0
        assert r0['halfN'] == 0, r0
        pg.evaluate("() => document.querySelector('[data-tterr=\"water\"]').click()")
        pg.wait_for_timeout(6500)
        chk = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#tarea .trow')];
          const bad = rows.filter(r => { const u = q1('SELECT * FROM units WHERE id=?', [+r.dataset.id]); return u && u.terrain_water === 1; }).length;
          const halfShown = rows.filter(r => r.classList.contains('halfmove')).map(r => +r.dataset.id).sort();
          const halfReal = rows.filter(r => { const u = q1('SELECT * FROM units WHERE id=?', [+r.dataset.id]); return u && u.terrain_water === 2; }).map(r => +r.dataset.id).sort();
          return { bad, halfOk: JSON.stringify(halfShown) === JSON.stringify(halfReal), halfN: halfShown.length, n: rows.length };
        }""")
        print('[④ 水中规则]', chk)
        assert chk['bad'] == 0 and chk['halfOk'] and chk['halfN'] > 0 and chk['n'] > 0, chk
        pg.evaluate("() => document.querySelector('[data-tterr=\"\"]').click()")
        pg.wait_for_timeout(4500)
        print('[④ 组队出击场地(×剔除/△红框/地上命名)] 通过')

        # ---------- ⑤ 排行·出击场地(同规则) ----------
        pg.evaluate("() => { state.rankCfg.terr = ''; state.stack=[]; setTab('rank'); }")
        pg.wait_for_timeout(4500)
        rc = pg.evaluate("() => [...document.querySelectorAll('[data-rterr]')].map(x => x.textContent)")
        assert rc == ['无限制', '宇宙', '空中', '地上', '水面', '水中'], rc
        pg.evaluate("() => document.querySelector('[data-rterr=\"water\"]').click()")
        pg.wait_for_timeout(5000)
        chk = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#rlist .rrow')];
          const bad = rows.filter(r => { const u = q1('SELECT * FROM units WHERE id=?', [+r.dataset.id]); return u && u.terrain_water === 1; }).length;
          const halfShown = rows.filter(r => r.classList.contains('halfmove')).map(r => +r.dataset.id).sort();
          const halfReal = rows.filter(r => { const u = q1('SELECT * FROM units WHERE id=?', [+r.dataset.id]); return u && u.terrain_water === 2; }).map(r => +r.dataset.id).sort();
          return { bad, halfOk: JSON.stringify(halfShown) === JSON.stringify(halfReal), n: rows.length };
        }""")
        print('[⑤ 排行水中规则]', chk)
        assert chk['bad'] == 0 and chk['halfOk'] and chk['n'] > 0, chk
        print('[⑤ 排行出击场地(同组队规则)] 通过')

        # ---------- ⑥ 水中伤害减半/不可用 ----------
        r = pg.evaluate("""() => {
          const norm = q('SELECT id FROM weapons').map(x => x.id).find(id => uwMult(id) === 100);
          return {
            w50: uwMult(111000010080), w0: uwMult(140000381090),
            fx: uwMult(106900015003), fx2: uwMult(114400015003),
            norm: uwMult(norm), normId: norm,
            t50: terrDamage(1000, 111000010080, 'water'), t50b: terrDamage(1001, 111000010080, 'water'),
            t0: terrDamage(1000, 140000381090, 'water'), tn: terrDamage(7777, norm, 'water'),
            tg: terrDamage(1000, 111000010080, 'ground')
          };
        }""")
        print('[⑥ uwMult/terrDamage 单测]', r)
        assert r['w50'] == 50 and r['w0'] == 0 and r['fx'] == 50 and r['fx2'] == 50 and r['norm'] == 100, r
        assert (r['t50'], r['t50b'], r['t0'], r['tn'], r['tg']) == (500, 500, 0, 7777, 1000), r

        # 排行 MAP+特殊 视图 (水池小到水中前100可见: 陆111→水94, 其中10行减半)
        NU = 1110000100
        pg.evaluate("() => { state.stack = []; setTab('rank'); }")
        pg.wait_for_timeout(4500)
        pg.evaluate("() => document.querySelector('[data-rterr=\"\"]').click()")
        pg.wait_for_timeout(3500)
        pg.evaluate("() => document.querySelector('[data-rg=\"map\"]').click()")
        pg.wait_for_timeout(5500)
        pg.evaluate("() => document.querySelector('[data-wat=\"特殊\"]').click()")
        pg.wait_for_timeout(5500)
        js_cache = "() => { const rows = state.rankCache.rows || []; const m = {}; for (const r of rows) m[r.unitId] = { wid: r.weapon.id, dmg: r.dmg, uw: r.uwMult }; return { n: rows.length, rows: m }; }"
        plain = pg.evaluate(js_cache)
        assert plain['n'] > 0 and not any(x['uw'] < 100 for x in plain['rows'].values()), '非水中视图不应出现水中倍率'
        pg.evaluate("() => document.querySelector('[data-rterr=\"water\"]').click()")
        pg.wait_for_timeout(6000)
        water = pg.evaluate(js_cache)
        assert water['n'] < plain['n'], (plain['n'], water['n'])   # 水中剔除不能出击机体
        assert all(u in plain['rows'] for u in water['rows']), '水中榜出现陆地榜没有的机体'
        wids = sorted({x['wid'] for x in water['rows'].values()} | {x['wid'] for x in plain['rows'].values()})
        uw = pg.evaluate(f"() => Object.fromEntries({wids}.map(w => [w, uwMult(w)]))")
        common = [u for u in water['rows'] if str(water['rows'][u]['wid']) == str(plain['rows'][u]['wid'])]
        bad, n50 = [], 0
        for u in common:
            m = uw[str(water['rows'][u]['wid'])]
            exp = plain['rows'][u]['dmg'] * m // 100 if m < 100 else plain['rows'][u]['dmg']
            if water['rows'][u]['dmg'] != exp:
                bad.append((u, plain['rows'][u]['dmg'], water['rows'][u]['dmg'], m))
            n50 += (m == 50)
        nu = str(NU)
        nu_ok = nu in water['rows'] and uw[str(water['rows'][nu]['wid'])] == 50 and \
            water['rows'][nu]['dmg'] == plain['rows'][nu]['dmg'] * 50 // 100
        print(f"[⑥ 陆/水同武器折算] 陆{plain['n']}水{water['n']} common={len(common)} 减半武器对={n50} ν高达={nu_ok} bad={bad[:3]}")
        assert len(common) >= 30 and n50 >= 3 and not bad, (len(common), n50, bad[:5])
        assert nu_ok, (water['rows'].get(nu), plain['rows'].get(nu))
        dom = pg.evaluate("() => [...document.querySelectorAll('#rlist .rrow')].map(el => ({ id: +el.dataset.id, wid: +el.dataset.wid, dmg: +el.querySelector('.dmg').textContent.replace(/[^0-9]/g,''), mark: el.textContent.includes('水中伤害减半') || el.textContent.includes('水中不可用') }))")
        mk = [x for x in dom if x['mark']]
        mk_bad = []
        for x in mk:
            m = uw[str(x['wid'])]
            if str(x['id']) not in plain['rows'] or not (m < 100 and x['dmg'] == plain['rows'][str(x['id'])]['dmg'] * m // 100):
                mk_bad.append((x['id'], x['wid'], x['dmg'], m))
        print(f"[⑥ 水下行标记] 显示{len(dom)}行 标记{len(mk)}行 bad={mk_bad[:3]}")
        assert mk and not mk_bad, (len(mk), mk_bad[:3])
        assert all(dom[i]['dmg'] >= dom[i + 1]['dmg'] for i in range(len(dom) - 1)), '水中榜未按伤害降序'
        print('[⑥ 水中伤害减半(折算/标记/排序)] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v82 全部通过 ===')
