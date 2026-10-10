# -*- coding: utf-8 -*-
"""v0.90 验证: 计算/排行/组队 标题栏中间「↺ 重置默认」按钮
① 按钮: 三页标题栏中间常驻(水平居中), 图鉴/特性无; 滚动后仍在
② 计算页: 改开关+数值+筛选 → 重置 → 全部回默认; 已选机体/驾驶员保留
③ 排行页: 改开关+筛选(UI 设标签) → 重置 → cfg 回默认 + 筛选清空
④ 组队页: 选战舰+改开关+筛选 → 重置 → 回默认; 战舰保留
⑤ 只对当前页: 排行改后 → 去组队重置 → 排行配置不变
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8990

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

        def click(sel, wait=500):
            pg.evaluate(f"() => {{ const el=document.querySelector({sel!r}); if(!el) throw new Error('no ' + {sel!r}); el.click(); }}")
            pg.wait_for_timeout(wait)

        def tab(name, wait=2400):
            pg.evaluate(f"() => {{ state.stack=[]; setTab({name!r}); }}")
            pg.wait_for_timeout(wait)

        # ① 按钮存在性/居中/滚动常驻/他页无
        for tb in ('calc', 'rank', 'team'):
            tab(tb, 2200)
            r = pg.evaluate("""() => { const el=document.getElementById('rstdef'); if(!el) return null;
              const b=el.getBoundingClientRect(), a=document.getElementById('app').getBoundingClientRect();
              const ab=document.getElementById('appbar').getBoundingClientRect();
              return { txt: el.textContent.replace(/\\s+/g,' '), cx: (b.left+b.right)/2, acx: (a.left+a.right)/2,
                       inbar: b.top>=ab.top-1 && b.bottom<=ab.bottom+1 }; }""")
            print('[①', tb, ']', r)
            assert r and '重置默认' in r['txt'] and abs(r['cx'] - r['acx']) < 3 and r['inbar'], r
        tab('units', 2000)
        assert pg.evaluate("() => !document.getElementById('rstdef')"), '图鉴页不应有重置按钮'
        tab('feat', 2000)
        assert pg.evaluate("() => !document.getElementById('rstdef')"), '特性页不应有重置按钮'
        print('[① 三页标题栏中间常驻(水平居中), 图鉴/特性无) 通过]')

        # ② 计算页重置
        tab('calc', 2400)
        pg.evaluate("() => { state.calc.unitId = 1001000150; state.calc.charId = null; render(); }")   # UR 高达EX
        pg.wait_for_timeout(2400)
        for sel in ('#crit', '#passive', '#cpassive', '#skills', '#mp', '#ca', '#ssp', '#star'):   # 注意: #ssp 须在 #star 前(点 #star 关时联动清 ssp)
            click(sel, 800)
        click('[data-tdef="40000"]', 1800)
        click('[data-prar="5"]', 1800)
        pg.evaluate("() => { filt('pickc').tags=[1109]; filt('pickc').series=[1]; filt('pickc').mode='or'; }")
        st = pg.evaluate("""() => ({ crit: state.calc.crit, passive: state.calc.passive, cpassive: state.calc.cpassive,
          skills: state.calc.skills, mp: state.calc.mp, ca: state.calc.ca, star: state.calc.star, ssp: !!state.calc.ssp,
          pRar: state.calc.pRar, tDef: state.calc.tDef })""")
        print('[② 改后]', st)
        assert st == {'crit': True, 'passive': False, 'cpassive': False, 'skills': False, 'mp': False, 'ca': False,
                      'star': False, 'ssp': False, 'pRar': 5, 'tDef': 40000}, st
        click('#rstdef', 2600)
        r2 = pg.evaluate("""() => ({ c: { crit: state.calc.crit, passive: state.calc.passive, cpassive: state.calc.cpassive,
            skills: state.calc.skills, mp: state.calc.mp, ca: state.calc.ca, star: state.calc.star, ssp: !!state.calc.ssp,
            pRar: state.calc.pRar, tDef: state.calc.tDef, tCharDef: state.calc.tCharDef, vigor: state.calc.vigor, pSpU: state.calc.pSpU },
          unit: state.calc.unitId, f: { tags: filt('pickc').tags.length, series: (filt('pickc').series||[]).length },
          chipCritOff: !document.getElementById('crit').classList.contains('on') })""")
        print('[② 重置后]', r2)
        assert r2['c'] == {'crit': False, 'passive': True, 'cpassive': True, 'skills': True, 'mp': True, 'ca': True,
                           'star': True, 'ssp': False, 'pRar': None, 'tDef': 10000, 'tCharDef': 750, 'vigor': 'default', 'pSpU': True}, r2['c']
        assert r2['unit'] == 1001000150, r2                       # 已选机体保留
        assert r2['f'] == {'tags': 0, 'series': 0}, r2            # 驾驶员标签/系列筛选清空
        assert r2['chipCritOff'], r2                              # UI 同步(暴击 关)
        print('[② 计算页重置(开关/数值/筛选回默认, 已选机体保留) 通过]')

        # ③ 排行页重置 (UI 设置标签筛选)
        tab('rank', 2600)
        click('#rtag', 1200)
        pg.evaluate("() => { const el=document.querySelector('#stlist [data-id]'); el.click(); }")
        pg.wait_for_timeout(300)
        click('#sapply', 2800)
        h = pg.evaluate("() => ({ n: filt('rank').tags.length, badge: document.getElementById('rtag').textContent.replace(/\\s+/g,' ') })")
        print('[③ 设标签筛选]', h)
        assert h['n'] == 1 and '1' in h['badge'], h
        for sel in ('[data-vg="max"]', '#rc', '#rsk', '#rca', '#rmp', '[data-star="0"]', '[data-rg="3"]', '[data-rterr="water"]', '[data-rar="5"]'):
            click(sel, 1800)
        pg.evaluate("""() => { Object.assign(state.rankCfg, { prole: 1, prar: 3, wat: '光束', atk: 'melee', urole: 1, targetDef: 40000 }); state.rankCache=null; pageRank(document.getElementById('view')); }""")
        pg.wait_for_timeout(2600)
        r3 = pg.evaluate("""() => ({ vg: state.rankCfg.vigor, crit: state.rankCfg.crit, skills: state.rankCfg.skills,
          ca: state.rankCfg.ca, mp: state.rankCfg.mp, star: state.rankCfg.star, range: state.rankCfg.range, terr: state.rankCfg.terr,
          rarity: state.rankCfg.rarity, prole: state.rankCfg.prole, prar: state.rankCfg.prar, wat: state.rankCfg.wat,
          atk: state.rankCfg.atk, urole: state.rankCfg.urole, targetDef: state.rankCfg.targetDef })""")
        print('[③ 改后]', r3)
        assert r3['vg'] == 'max' and r3['crit'] and not r3['skills'] and not r3['ca'] and not r3['mp'] and r3['star'] == 0 \
            and r3['range'] == 3 and r3['terr'] == 'water' and r3['rarity'] == 5 and r3['prole'] == 1 and r3['prar'] == 3 \
            and r3['wat'] == '光束' and r3['atk'] == 'melee' and r3['urole'] == 1 and r3['targetDef'] == 40000, r3
        click('#rstdef', 2800)
        r4 = pg.evaluate("""() => ({ cfg: { def: state.rankCfg.targetDef, cdef: state.rankCfg.targetCharDef, vg: state.rankCfg.vigor,
            crit: state.rankCfg.crit, passive: state.rankCfg.passive, cpassive: state.rankCfg.cpassive, skills: state.rankCfg.skills,
            ca: state.rankCfg.ca, mp: state.rankCfg.mp, star: state.rankCfg.star, range: state.rankCfg.range, wat: state.rankCfg.wat,
            atk: state.rankCfg.atk, urole: state.rankCfg.urole, rarity: state.rankCfg.rarity, prar: state.rankCfg.prar,
            prole: state.rankCfg.prole, terr: state.rankCfg.terr, spU: state.rankCfg.spU !== false, s3u: state.rankCfg.s3u !== false,
            sspU: state.rankCfg.sspU !== false, pSpU: state.rankCfg.pSpU !== false },
          f: { tags: filt('rank').tags.length, series: (filt('rank').series||[]).length, sp: filt('rank').sp, ssp: filt('rank').ssp },
          badge: document.getElementById('rtag').textContent.replace(/\\s+/g,' ') })""")
        print('[③ 重置后]', r4)
        exp = {'def': 10000, 'cdef': 750, 'vg': 'default', 'crit': False, 'passive': True, 'cpassive': True, 'skills': True,
               'ca': True, 'mp': True, 'star': 3, 'range': 'all', 'wat': None, 'atk': None, 'urole': None, 'rarity': None,
               'prar': None, 'prole': None, 'terr': '', 'spU': True, 's3u': True, 'sspU': True, 'pSpU': True}
        assert r4['cfg'] == exp, r4['cfg']
        assert r4['f'] == {'tags': 0, 'series': 0, 'sp': 1, 'ssp': 1} and '1' not in r4['badge'], r4
        print('[③ 排行页重置(cfg 回默认 + 标签筛选清空) 通过]')

        # ④ 组队页重置 (含战舰保留)
        tab('team', 2600)
        click('#picks', 1300)
        pg.evaluate("() => document.querySelector('#pkl [data-s]') || document.querySelector('[data-s]')")
        pg.evaluate("() => { const el=document.querySelector('[data-s]'); el.click(); }")
        pg.wait_for_timeout(2600)
        supp = pg.evaluate("() => state.team.suppId")
        print('[④ 已选战舰]', supp)
        assert supp, '战舰未选中'
        for sel in ('#m2', '[data-tstar="0"]', '[data-tterr="water"]', '[data-trar="5"]', '[data-prole="1"]', '[data-tprar="3"]',
                    '[data-rg="map"]', '[data-twat="光束"]', '[data-tatk="melee"]', '#ts3', '#tguard', '#tsdef'):
            click(sel, 1800)
        pg.evaluate("""() => { const el=document.getElementById('ttdef'); el.value=40000; el.dispatchEvent(new Event('change')); }""")
        pg.wait_for_timeout(2200)
        pg.evaluate("""() => { filt('team').tags=[1]; filt('team').series=[2]; filt('teamp').tags=[1109]; }""")
        t3 = pg.evaluate("""() => ({ skills: state.team.skills, star: state.team.star, terr: state.team.terr, rar: state.team.rar,
          prole: state.team.prole, prar: state.team.prar, range: state.team.range, wat: state.team.wat, atk: state.team.atk,
          s3u: state.team.s3u, guard: state.team.guard, sdef: state.team.sdef, tdef: state.team.tdef })""")
        print('[④ 改后]', t3)
        assert t3['skills'] and t3['star'] == 0 and t3['terr'] == 'water' and t3['rar'] == 5 and t3['prole'] == 1 and t3['prar'] == 3 \
            and t3['range'] == 'map' and t3['wat'] == '光束' and t3['atk'] == 'melee' and t3['s3u'] is False and t3['guard'] and t3['sdef'] and t3['tdef'] == 40000, t3
        click('#rstdef', 2800)
        t4 = pg.evaluate("""() => ({ t: { skills: state.team.skills, star: state.team.star, shipStar: state.team.shipStar, range: state.team.range,
            vigor: state.team.vigor, ca: state.team.ca, mp: state.team.mp, prole: state.team.prole, terr: state.team.terr, buffs: (state.team.buffs||[]).length,
            tdef: state.team.tdef, tcdef: state.team.tcdef, defup: state.team.defup, atkup: state.team.atkup, s3u: state.team.s3u !== false,
            spU: state.team.spU !== false, sspU: state.team.sspU !== false, pSpU: state.team.pSpU !== false, rar: state.team.rar,
            prar: state.team.prar, wat: state.team.wat, atk: state.team.atk, guard: state.team.guard, sdef: state.team.sdef },
          supp: state.team.suppId,
          f: { tags: filt('team').tags.length, series: (filt('team').series||[]).length, ptags: filt('teamp').tags.length,
               sp: filt('team').sp, ssp: filt('team').ssp },
          m1on: document.getElementById('m1').classList.contains('on') })""")
        print('[④ 重置后]', t4)
        texp = {'skills': False, 'star': 3, 'shipStar': 0, 'range': 'all', 'vigor': 'default', 'ca': True, 'mp': True, 'prole': None,
                'terr': '', 'buffs': 0, 'tdef': 10000, 'tcdef': 750, 'defup': 0, 'atkup': 0, 's3u': True, 'spU': True, 'sspU': True,
                'pSpU': True, 'rar': None, 'prar': None, 'wat': None, 'atk': None, 'guard': False, 'sdef': False}
        assert t4['t'] == texp, t4['t']
        assert t4['supp'] == supp, (t4['supp'], supp)                      # 战舰保留
        assert t4['f'] == {'tags': 0, 'series': 0, 'ptags': 0, 'sp': 1, 'ssp': 1}, t4
        assert t4['m1on'], t4                                              # UI 同步(第一击·被动MP)
        print('[④ 组队页重置(开关回默认+双筛选清空, 战舰保留) 通过]')

        # ⑤ 只对当前页重置: 排行改后 → 组队重置 → 排行配置不变
        tab('rank', 2600)
        click('[data-vg="max"]', 1800)
        click('#rc', 1800)
        tab('team', 2600)
        click('#rstdef', 2600)
        tab('rank', 2600)
        r5 = pg.evaluate("() => ({ vg: state.rankCfg.vigor, crit: state.rankCfg.crit })")
        print('[⑤ 组队重置后 排行配置]', r5)
        assert r5 == {'vg': 'max', 'crit': True}, r5
        # 滚动后按钮仍常驻
        pg.evaluate("() => { document.getElementById('view').scrollTop = 700; }")
        pg.wait_for_timeout(400)
        vis = pg.evaluate("""() => { const b=document.getElementById('rstdef').getBoundingClientRect();
          return b.width > 0 && b.top >= 0 && b.top < 60; }""")
        assert vis, '滚动后按钮应仍在标题栏可见'
        print('[⑤ 只对当前页重置 + 滚动常驻 通过]')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v90 全部通过 ===')
