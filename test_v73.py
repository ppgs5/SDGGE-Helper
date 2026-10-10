# -*- coding: utf-8 -*-
"""v0.73 验证: 计算页驾驶员TOP10接通「驾驶员筛选弹窗」的类型/稀有度/标签 (此前只有系列生效)
① pickc.role=3(支援型) → 神高达(EX) 的驾驶员TOP10 全为支援型, 塞西娅出现(应为第1)
② 恢复全部 → 基线 TOP10 (佐尔坦第一) 不变
③ pickc.rar=5(UR) → 全UR; pickc.tags=宇宙世纪系列 → 全含该标签(名称集合匹配)
④ 标签+系列+任一命中(mode=or) 组合筛选
⑤ 塞西娅被动生效条件核对: 神高达(攻击型) trait7(支援时+15%攻)不计/role门;
   AGE-2EX(支援型) 条件开假设满足 +15atk / 如实判定 0; 射击 20(无条件)+15(超强势EX·条件开)=35
回归: v58~v71 全过
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8973
GS, AG, CH = 1200003950, 1400000550, 1999000100   # 神高达(EX,攻击型) / AGE-2EX(支援型) / 塞西娅

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
        pg.evaluate(f"() => {{ state.calc = Object.assign(state.calc, {{unitId:{GS}, charId:null, s3u:true, spU:true, ssp:true, pSpU:true, pRar:4, tDef:10000, tCharDef:750, vigor:'default'}}); state.stack=[]; setTab('calc'); }}")
        pg.wait_for_timeout(3000)

        def top10(mut):
            if mut: pg.evaluate(mut)
            pg.evaluate("() => { state._prKey = null; render(); }")
            pg.wait_for_timeout(1200)
            return pg.evaluate("() => (state._prRows || []).map(r => ({name: r.name, role: r.role, rarity: r.rarity, dmg: r.dmg, id: r.id}))")

        # ---------- ② 基线 (驾驶员稀有度=SSR, 与截图同口径) ----------
        base = top10("() => { const f = filt('pickc'); f.role = null; f.rar = null; f.tags = []; f.series = []; }")
        print('[② 基线TOP5]', [(r['name'], r['dmg']) for r in base[:5]])
        assert base and base[0]['name'] == '佐尔坦·亚卡年' and base[0]['dmg'] == 189064, base[:3]

        # ---------- ① 类型=支援型 ----------
        sup = top10("() => { filt('pickc').role = 3; }")
        print('[① 支援型TOP5]', [(r['name'], r['dmg']) for r in sup[:5]])
        assert sup and all(r['role'] == 3 for r in sup), sup[:3]
        assert any(r['name'] == '塞西娅·阿维亚' for r in sup), sup
        txt = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '驾驶员伤害 TOP10' in txt and '佐尔坦' not in txt, txt[-300:]   # 筛选后攻击型驾驶员消失(塞西娅在候选内, 见上行)
        print('[① 类型=支援型筛选生效(攻击型消失/塞西娅在候选)] 通过')

        # ---------- ③ 稀有度UR / 标签 ----------
        ur = top10("() => { const f = filt('pickc'); f.role = null; f.rar = 5; state.calc.pRar = null; }")
        print('[③ UR驾驶员]', len(ur), [(r['name'], r['rarity']) for r in ur[:3]])
        assert ur and all(r['rarity'] == 5 for r in ur), ur[:3]
        tid = pg.evaluate("() => q1(\"SELECT id FROM tags WHERE name='宇宙世纪系列'\").id")
        tg = top10(f"() => {{ const f = filt('pickc'); f.rar = null; f.tags = [{tid}]; f.mode = 'and'; }}")
        print('[③ 标签=宇宙世纪系列]', len(tg), [r['name'] for r in tg[:4]])
        ids = [r['id'] for r in tg]
        ok = pg.evaluate(f"() => {ids}.every(id => charMetaOf(id).tags.has('宇宙世纪系列'))")
        assert tg and ok, (ids, tg[:3])
        print('[③ 稀有度/标签筛选生效] 通过')

        # ---------- ④ 标签+系列 任一命中 ----------
        sid = pg.evaluate("() => q1('SELECT series_id sid FROM units WHERE id=?', [1400000550]).sid")
        combo = top10(f"() => {{ const f = filt('pickc'); f.tags = [{tid}]; f.series = [{sid}]; f.mode = 'or'; }}")
        ids2 = pg.evaluate("() => (state._prRows || []).map(r => r.id)")
        ok2 = pg.evaluate(f"""() => {ids2}.every(id => charMetaOf(id).tags.has('宇宙世纪系列') || String(charSeriesMap()[String(q1('SELECT series_set_id FROM characters WHERE id=?',[id]).series_set_id)]) === '{sid}')""")
        print('[④ 标签或系列]', len(combo))
        assert combo and ok2, (ids2[:3], combo[:2])
        print('[④ 任一命中(标签或系列)] 通过')

        # ---------- ⑤ 塞西娅被动条件核对 ----------
        r = pg.evaluate(f"""() => {{
          const mk = (uid, ca, skills) => {{
            const b2 = charBonus({CH}, 'mid', {{ passive: true, cpassive: true, skills, condAll: ca, unitId: uid, upassive: true, multiPhase: false, pSpU: true, ussp: false }}, metaOf(uid));
            return {{ atk: b2.atk || 0, ranged: b2.ranged || 0 }};
          }};
          return {{
            gs_on: mk({GS}, true, false), gs_off: mk({GS}, false, false), gs_skill: mk({GS}, true, true),
            ag_on: mk({AG}, true, false), ag_off: mk({AG}, false, false),
            mp: mpOf({GS}, {CH}, false, true, true), sup: supCountsOf({CH}, {GS}, 'mid', true, true)
          }};
        }}""")
        print('[⑤ 塞西娅被动]', r)
        assert r['gs_on'] == {'atk': 0, 'ranged': 20} and r['gs_off']['ranged'] == 20, r     # 攻击型: 支援时+15atk被role门挡; 常驻射击+20%(LV3+15+LV1+5); 超强势EX被系列门挡
        assert r['gs_skill']['ranged'] == 35, r                                               # +射击值增幅LV3(主动技能)
        assert r['ag_on']['atk'] == 15 and r['ag_off']['atk'] == 0, r                         # 支援型: 条件开假设满足+15 / 如实判定0
        assert r['mp'] == 0 and r['sup'] == {'atk': 1, 'def': 0}, r                           # 无MP来源; 支攻+1(超强势EX的+1次被系列门挡)
        print('[⑤ 塞西娅被动生效条件(role门/bag条件/MP/支攻)] 通过')

        # ---------- ⑥ 超强势EX仅对 GUNDAM EXA 生效(数据修正 2026-10-10) ----------
        r6 = pg.evaluate(f"""() => {{
          const sv = (uid, vigor) => {{
            const b2 = charBonus({CH}, vigor, {{ passive: true, cpassive: true, skills: false, condAll: true, unitId: uid, upassive: true, multiPhase: true, pSpU: true, ussp: false }}, metaOf(uid));
            return {{ ranged: b2.ranged || 0, sup: supCountsOf({CH}, uid, vigor, true, true) }};
          }};
          return {{ gs: sv({GS}, 'supercharged'), ex: sv(1999000100, 'supercharged') }};
        }}""")
        print('[⑥ 超一击]', r6)
        assert r6['gs'] == {'ranged': 20, 'sup': {'atk': 1, 'def': 0}}, r6      # 神高达(非EXA): 超一击不计超强势EX; 常驻射击+20
        assert r6['ex'] == {'ranged': 35, 'sup': {'atk': 2, 'def': 0}}, r6      # EXZELIA(GUNDAM EXA): 超一击+超强势EX(+15) 共35/支攻+1次
        pg.evaluate("() => { Object.assign(state.calc, {unitId:1200003950, charId:null, vigor:'supercharged', skills:true, ca:true, mp:true, passive:true, cpassive:true, pSpU:true, pRar:null, crit:false}); const f=filt('pickc'); f.role=3; f.rar=null; f.tags=[]; f.series=[]; state._prKey=null; render(); }")
        pg.wait_for_timeout(1800)
        rows6 = pg.evaluate("() => (state._prRows||[]).map(r=>({name:r.name, dmg:r.dmg, sup:r.sup.atk}))")
        print('[⑥ 超一击·支援型榜]', [(x['name'][:6], x['dmg']) for x in rows6[:5]])
        assert rows6[0]['name'].startswith('巴纳吉') and rows6[0]['dmg'] == 249462, rows6[:2]   # 超一击下支援最高=巴纳吉(非塞西娅)
        sc6 = next(x for x in rows6 if x['name'].startswith('塞西娅'))
        assert sc6['dmg'] == 187069 and sc6['sup'] == 1, sc6                                   # v0.78(原值口径650, cAtk=floor(650×1.35)=877): 187,069, 支攻+1
        print('[⑥ 超强势EX仅对GUNDAM EXA生效(超一击验证)] 通过')

        # ---------- ⑦ 角色页能力条件chips: 超强势EX 显示 GUNDAM EXA 系列chip ----------
        pg.evaluate("() => { state.stack = []; push({page:'char', title:'x', id:1999000100}); }")
        pg.wait_for_timeout(900)
        txt = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '支援型类型' in txt and 'GUNDAM EXA' in txt, txt[:300]
        kv = pg.evaluate("() => { const el = [...document.querySelectorAll('#view .kv')].find(e => e.textContent.includes('超强势EX')); return el ? el.textContent.replace(/\\s+/g,' ') : null; }")
        assert kv and 'GUNDAM EXA' in kv, kv
        print('[⑦ 能力条件chip(超强势EX→GUNDAM EXA)] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v73 全部通过 ===')
