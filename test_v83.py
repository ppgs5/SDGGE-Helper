# -*- coding: utf-8 -*-
"""v0.83 验证: 水中武器倍率数据源修正——全量「使用限制」(weapon_use), 原只扫 weapon_fx(2把)/ssp_json(57把)漏掉 2359 把
官方 capability 双轴(与 weapon_use 文本一一对应):
  「对水下敌人的伤害减半」→50 / 「不能在水下使用」(in_underwater=false) 或「对水下敌人没有伤害」(damage_underwater=0) →0 不可用
SSP版武器独立存限制: GN加农SSP 无限制(×1.0), 基础GN加农 减半 — 与用户截图(GN加农 使用限制)一致
① uwMult/terrDamage 单测(50/0/100 各类)
② 排行 全武器 水/陆对比: 同武器行 dmg_water==floor(dmg_plain×uw/100), 减半对数≥20, 无标记泄漏
③ 组队: GN-XⅡ加农型 SSP关→基础GN加农水中减半+行内标记; SSP开→SSP武器(无限制)不随水中变化
④ 武器页显示「使用限制: 对水下敌人的伤害减半」
仅回归最新版(用户口径)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8983
GN2 = 1376000800            # GN-XⅡ加农型 (SSR/支援型): 基础GN加农=减半 / SSP版=无限制

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

        # ---------- ① uwMult/terrDamage 单测 ----------
        r = pg.evaluate("""() => {
          const norm = q('SELECT id FROM weapons').map(x => x.id).find(id => uwMult(id) === 100);
          return {
            halfBase: uwMult(137600080003),   // GN加农 基础: 对水下敌人的伤害减半 → 50
            sspFree: uwMult(137600080090),    // GN加农 SSP: 无限制 → 100
            noUse: uwMult(111000010080),      // 飞翼浮游炮 SSP: 不能在水下使用 → 0
            zero: uwMult(140000381090),       // 法卢西亚浮游炮 SSP: 没有伤害 → 0
            zeroBase: uwMult(100900020002),   // 30cm炮(燃烧榴弹): 对水下敌人没有伤害 → 0
            fx: uwMult(106900015003),         // 天鹅EX 米加光束发射器 → 50
            norm: uwMult(norm), normId: norm,
            t1: terrDamage(1000, 137600080003, 'water'), t2: terrDamage(1001, 137600080003, 'water'),
            t3: terrDamage(1000, 111000010080, 'water'), t4: terrDamage(7777, norm, 'water'),
            t5: terrDamage(1000, 137600080003, 'ground'),
            cnt: (() => { let n50 = 0, n0 = 0; for (const x of q('SELECT id FROM weapons')) { const v = uwMult(x.id); if (v === 50) n50++; else if (v === 0) n0++; } return { n50, n0 }; })()
          };
        }""")
        print('[① uwMult 单测]', {k: v for k, v in r.items() if k != 'cnt'}, 'cnt=', r['cnt'])
        assert r['halfBase'] == 50 and r['sspFree'] == 100 and r['noUse'] == 0 and r['zero'] == 0 \
            and r['zeroBase'] == 0 and r['fx'] == 50 and r['norm'] == 100, r
        assert (r['t1'], r['t2'], r['t3'], r['t4'], r['t5']) == (500, 500, 0, 7777, 1000), r
        assert r['cnt']['n50'] > 2000 and r['cnt']['n0'] > 100, r['cnt']   # 全库 ~2193 减半 / ~166 不可用
        print('[① 水中倍率(减半50/不可用0/无限制100) 单测] 通过')

        # ---------- ② 排行 全武器 水/陆对比 ----------
        pg.evaluate("() => { state.stack = []; setTab('rank'); }")
        pg.wait_for_timeout(4500)
        pg.evaluate("() => document.querySelector('[data-rterr=\"\"]').click()")
        pg.wait_for_timeout(6000)
        js_cache = "() => { const rows = state.rankCache.rows || []; const m = {}; for (const r of rows) m[r.unitId] = { wid: r.weapon.id, dmg: r.dmg, uw: r.uwMult }; return { n: rows.length, rows: m }; }"
        plain = pg.evaluate(js_cache)
        pg.evaluate("() => document.querySelector('[data-rterr=\"water\"]').click()")
        pg.wait_for_timeout(6500)
        water = pg.evaluate(js_cache)
        assert water['n'] < plain['n'], (plain['n'], water['n'])
        wids = sorted({x['wid'] for x in water['rows'].values()} | {x['wid'] for x in plain['rows'].values()})
        uw = pg.evaluate(f"() => Object.fromEntries({wids}.map(w => [w, uwMult(w)]))")
        common = [u for u in water['rows'] if u in plain['rows'] and str(water['rows'][u]['wid']) == str(plain['rows'][u]['wid'])]
        bad, n50, n0 = [], 0, 0
        for u in common:
            m = uw[str(water['rows'][u]['wid'])]
            exp = plain['rows'][u]['dmg'] * m // 100 if m < 100 else plain['rows'][u]['dmg']
            if water['rows'][u]['dmg'] != exp:
                bad.append((u, str(water['rows'][u]['wid']), plain['rows'][u]['dmg'], water['rows'][u]['dmg'], m))
            n50 += (m == 50); n0 += (m == 0)
        print(f"[② 排行全武器 陆{plain['n']}水{water['n']} common={len(common)} 减半对={n50} 不可用对={n0} bad={bad[:3]}")
        assert not bad, bad[:5]
        assert n50 >= 20, n50
        # 过滤到 MAP+特殊 池(减半武器密度高)后, 前100行应出现水中标记
        pg.evaluate("() => document.querySelector('[data-rg=\"map\"]').click()")
        pg.wait_for_timeout(5500)
        pg.evaluate("() => document.querySelector('[data-wat=\"特殊\"]').click()")
        pg.wait_for_timeout(5500)
        dom = pg.evaluate("() => [...document.querySelectorAll('#rlist .rrow')].filter(el => el.textContent.includes('水中伤害减半') || el.textContent.includes('水中不可用')).length")
        assert dom > 0, dom
        print(f'[② 排行水中折算逐行一致(减半对{n50}/不可用对{n0}; MAP+特殊 前100行标记{dom}行)] 通过')

        # ---------- ③ 组队 GN-XⅡ加农型: SSP关→基础武器减半 / SSP开→SSP无限制 ----------
        pg.evaluate("""() => { window.__caps = []; const orig = buildRanking;
          buildRanking = function(f, cfg, P){ const r = orig(f, cfg, P);
            window.__caps.push({terr: cfg.terr || null, sspU: P.sspU !== false,
              rows: (r.sup || []).concat(r.def || [], r.main || []).map(x => ({ id: x.unitId, wid: x.weapon.id, dmg: x.dmg, uw: x.uwMult })) }); return r; }; }""")
        def team_cap(mut):
            pg.evaluate("() => { window.__caps = []; }")
            pg.evaluate(mut)
            pg.wait_for_timeout(6500)
            caps = pg.evaluate("() => window.__caps")
            return caps
        caps = team_cap(f"() => {{ state.team.suppId = 1125000250; state.team.shipStar = 0; state.team.sspU = false; state.team.terr = ''; state.team.urole = 3; state.stack = []; setTab('team'); }}")
        pg.evaluate("() => { window.__caps = []; document.querySelector('[data-tterr=\"water\"]').click(); }")
        pg.wait_for_timeout(6500)
        caps += pg.evaluate("() => window.__caps")
        def row_of(cap, uid):
            return next((x for x in cap['rows'] if x['id'] == uid), None)
        land = next(c for c in caps if c['terr'] is None and not c['sspU'])
        wat = next(c for c in caps if c['terr'] == 'water' and not c['sspU'])
        a, bb = row_of(land, GN2), row_of(wat, GN2)
        print('[③ SSP关 陆]', a, '\n[③ SSP关 水]', bb)
        assert a and bb and a['wid'] == 137600080003 and bb['wid'] == 137600080003, (a, bb)   # 基础GN加农
        assert a['uw'] == 100 and bb['uw'] == 50 and bb['dmg'] == a['dmg'] * 50 // 100, (a, bb)
        mk = pg.evaluate(f"""() => {{ const rows = [...document.querySelectorAll('#tarea .trow')];
          const el = rows.find(e => +e.dataset.id === {GN2});
          return {{ marked: rows.filter(e => e.textContent.includes('水中伤害减半')).length,
                    gn2: el ? el.textContent.replace(/\\s+/g,' ') : null }}; }}""")
        if mk['gn2']:
            assert '水中伤害减半' in mk['gn2'], mk['gn2']
        print(f"[③ 组队 SSP关: 基础GN加农 水中减半{'(含行内标记)' if mk['gn2'] else '(该机体不在前10, 标记见其他'+str(mk['marked'])+'行)'}] 通过")
        caps = team_cap(f"() => {{ state.team.sspU = true; state.team.terr = 'water'; state.team.urole = 3; state.stack = []; setTab('team'); }}")
        pg.evaluate("() => { window.__caps = []; document.querySelector('[data-tterr=\"\"]').click(); }")
        pg.wait_for_timeout(6500)
        caps += pg.evaluate("() => window.__caps")
        w2 = next(c for c in caps if c['terr'] == 'water' and c['sspU'])
        l2 = next(c for c in caps if c['terr'] is None and c['sspU'])
        c1, c2 = row_of(w2, GN2), row_of(l2, GN2)
        print('[③ SSP开 水]', c1, '\n[③ SSP开 陆]', c2)
        assert c1 and c2 and c1['wid'] == 137600080090 and c2['wid'] == 137600080090, (c1, c2)  # SSP武器
        assert c1['uw'] == 100 and c1['dmg'] == c2['dmg'], (c1, c2)   # 无限制 → 水中不变
        print('[③ 组队 SSP开: SSP武器水中无限制不变] 通过')

        # ---------- ④ 武器页「使用限制」 ----------
        pg.evaluate("() => { state.stack = []; push({ page: 'weapon', title: 'x', id: 137600080003 }); }")
        pg.wait_for_timeout(1200)
        txt = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '使用限制' in txt and '对水下敌人的伤害减半' in txt, txt[:400]
        print('[④ 武器页使用限制显示] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v83 全部通过 ===')
