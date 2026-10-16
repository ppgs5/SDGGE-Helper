# -*- coding: utf-8 -*-
"""v105 验证: 暴击率达到100%(含必暴 trait94) → 无论暴击开关是否打开 均按暴击计算(计算/排行/组队)
① 计算页 必暴武器(连招@武斗家尼摩 1705002900): 暴击关 vs 暴击开 → 该武器行伤害相同; 页面提示「自动按暴击计算」
② 对照: 仅有暴击率(非必暴)的武器: 关/开 伤害不同(暴击开关对非100%仍有效)
③ 排行页 buildRanking(crit=false) 结果中存在 forceCrit 行(暴击关也按暴击计算)
"""
import os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 9013

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []

def cell_of(pg, wid):
    r = pg.evaluate("""(wid) => { const tr = document.querySelector('#view table.ctable tr[data-wid="' + wid + '"]');
      return tr && tr.cells.length > 1 ? tr.cells[1].innerText : null; }""", wid)
    return int(re.sub(r'[^0-9]', '', r)) if r else None

try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        # ① 必暴武器: 关/开同伤害 + 提示
        w94 = pg.evaluate("""() => { const r = q("SELECT wt.weapon_id wid, w.unit_id u FROM weapon_traits wt JOIN weapons w ON w.id=wt.weapon_id WHERE wt.trait_type=94 LIMIT 1")[0]; return r; }""")
        assert w94, '未找到必暴武器'
        pg.evaluate("""(r) => { const c = state.calc; c.unitId = r.u; c.charId = null; c.crit = false; c.vigor = 'supercharged';
          c.first = false; c.skills = false; c.mp = false; state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""", w94)
        pg.wait_for_timeout(900)
        d_off = cell_of(pg, w94['wid'])
        note = pg.evaluate("() => document.body.innerText.includes('自动按暴击计算')")
        rowm = pg.evaluate("""(wid) => { const tr = document.querySelector('#view table.ctable tr[data-wid="' + wid + '"]'); return tr ? tr.innerText.includes('必暴') : null; }""", w94['wid'])
        pg.evaluate("() => document.getElementById('crit').click()")
        pg.wait_for_timeout(700)
        d_on = cell_of(pg, w94['wid'])
        print('[① 必暴武器] off:', d_off, '→ on:', d_on, '| 页面提示:', note, '| 武器行标注:', rowm)
        assert d_off and d_off == d_on and note and rowm is True, (d_off, d_on, note, rowm)
        print('[① 必暴(暴击率100%) 无视暴击开关按暴击计算 + 提示 + 武器行「必暴」标注 通过]')

        # ①b 计算页必暴标注: 无限正义EX + 阿斯兰(主动技能开·超一击) 武器30+机体被动30+技能40=100%
        pg.evaluate("""() => { const c = state.calc; c.unitId = 1330002850; c.charId = 1330001804; c.crit = false; c.vigor = 'supercharged';
          c.first = false; c.skills = true; c.mp = false; state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""")
        pg.wait_for_timeout(1000)
        r1b = pg.evaluate("""() => { const tr = document.querySelector('#view table.ctable tr[data-wid="133000285007"]');
          const pr = document.querySelector('#view .trow[data-pid="1330001804"]');
          const anyPilot = [...document.querySelectorAll('#view .trow')].some(el => el.innerText.includes('必暴'));
          return { row: tr ? tr.innerText.includes('必暴') : null, pilot: pr ? pr.innerText.includes('必暴') : null, anyPilot,
                   note: document.body.innerText.includes('自动按暴击计算') }; }""")
        print('[①b 计算页必暴标注]', r1b)
        assert r1b['row'] is True and r1b['anyPilot'] is True and r1b['pilot'] is not False and r1b['note'] is True, r1b
        print('[①b 计算页必暴标注(武器行/驾驶员TOP行/公式提示) 通过]')

        # ② 对照: 非必暴但有暴击率的武器 关/开应有差异
        wc = pg.evaluate("""() => { const r = q("SELECT id wid, unit_id u FROM weapons WHERE crit_rate >= 25 AND id NOT IN (SELECT weapon_id FROM weapon_traits WHERE trait_type=94) ORDER BY crit_rate DESC LIMIT 1")[0]; return r; }""")
        assert wc, '未找到对照武器'
        pg.evaluate("""(r) => { const c = state.calc; c.unitId = r.u; c.charId = null; c.crit = false; c.vigor = 'supercharged';
          state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""", wc)
        pg.wait_for_timeout(900)
        c_off = cell_of(pg, wc['wid'])
        pg.evaluate("() => document.getElementById('crit').click()")
        pg.wait_for_timeout(700)
        c_on = cell_of(pg, wc['wid'])
        print('[② 对照(非必暴)] off:', c_off, '→ on:', c_on)
        assert c_off and c_on and c_on > c_off, (c_off, c_on)
        print('[② 非100%暴击率: 开关仍有效(开>关) 通过]')

        # ③ 排行路径: 无限正义EX(武器暴击30+机体被动30+机师爆击增幅50=100%) crit=false/true 伤害一致
        res = pg.evaluate("""() => {
          const f = filt('rank');
          const R = crit => buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit },
            { passive: true, cpassive: true, skills: true, condAll: true, autoVigor: true, multiPhase: false, star: 3,
              spU: true, s3u: true, sspU: true, pSpU: true });
          const off = R(false), on = R(true);
          const h1 = off.find(r => r.unitId === 1330002850), h2 = on.find(r => r.unitId === 1330002850);
          return h1 ? { uid: h1.unitId, pilot: h1.pilot.name, rate: h1.critRate, forceCrit: h1.forceCrit, d_off: h1.dmg, d_on: h2 ? h2.dmg : null } : null; }""")
        print('[③ 排行(暴击关) 无限正义EX]', res)
        assert res and res['forceCrit'] is True and res['rate'] == 100, res
        assert res['d_off'] == res['d_on'], res
        print('[③ 排行/组队路径: 暴击率100% 关/开同伤害 通过]')

        # ④ 消耗MP武器: 气势/MP不足不可用; 超一击恢复可用
        def row_exists(wid):
            return pg.evaluate("""(wid) => !!document.querySelector('#view table.ctable tr[data-wid="' + wid + '"]')""", wid)
        wmp = pg.evaluate("""() => q("SELECT wu.weapon_id wid, w.unit_id u, wu.text t FROM weapon_use wu JOIN weapons w ON w.id=wu.weapon_id WHERE wu.text LIKE '%消耗%MP%' ORDER BY w.power DESC LIMIT 1")[0]""")
        assert wmp, '未找到消耗MP武器'
        pg.evaluate("""(r) => { const c = state.calc; c.unitId = r.u; c.charId = null; c.crit = false; c.vigor = 'mid';
          c.first = false; c.skills = false; c.mp = false; state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""", wmp)
        pg.wait_for_timeout(900)
        hid = row_exists(wmp['wid'])
        note2 = pg.evaluate("() => document.body.innerText.includes('「战意/MP 条件」')")
        pg.evaluate("() => document.querySelector('[data-vg=supercharged]').click()")
        pg.wait_for_timeout(800)
        shown = row_exists(wmp['wid'])
        print('[④ MP武器]', wmp['t'], '| 气势0隐藏:', not hid, '| 超一击可用:', shown, '| 提示:', note2)
        assert (not hid) and shown and note2
        print('[④ 消耗MP武器 气势/MP不足不可用(超一击可用) 通过]')

        # ⑤ 超强势限定武器: 气势不足不可用(回归)
        pg.evaluate("""() => { const c = state.calc; c.unitId = 1705002900; c.charId = null; c.vigor = 'mid';
          c.first = false; c.skills = false; state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""")
        pg.wait_for_timeout(900)
        h1 = row_exists(170500290002)
        pg.evaluate("() => document.querySelector('[data-vg=max]').click()")
        pg.wait_for_timeout(800)
        s1 = row_exists(170500290002)
        print('[⑤ 超强势限定] mid隐藏:', not h1, '| 超强势可用:', s1)
        assert (not h1) and s1
        print('[⑤ 超强势限定武器 气势不足不可用 通过]')

        # ⑥ 回归: 排行固定超一击(多段增益关)下 无限正义 仍应是 阿斯兰(100%暴击) 259,477, 不能被罗·裘尔剪枝
        res = pg.evaluate("""() => {
          const f = filt('rank');
          const R = (vg, auto) => buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: vg, crit: false },
            { passive: true, cpassive: true, skills: true, condAll: true, autoVigor: auto, multiPhase: false, star: 3,
              spU: true, s3u: true, sspU: true, pSpU: true });
          const a = R('default', true).find(r => r.unitId === 1330002850);
          const bb = R('supercharged', false).find(r => r.unitId === 1330002850);
          const b2 = R('supercharged', false)[0];
          return { 默认: a && { p: a.pilot.name, dmg: a.dmg },
                   超一击: bb && { p: bb.pilot.name, dmg: bb.dmg, rate: bb.critRate, fc: bb.forceCrit },
                   超一击top1: b2 && { n: b2.unit.name, dmg: b2.dmg } }; }""")
        print('[⑥ 固定超一击]', res)
        assert res['默认']['dmg'] == 259477 and res['超一击']['dmg'] >= res['默认']['dmg'], res
        assert res['超一击']['fc'] is True and res['超一击']['rate'] == 100, res
        assert res['超一击top1']['dmg'] == 275741, res   # 与用户截图#1(固定超一击)一致
        print('[⑥ 排行固定超一击: 无限正义 259,477→' + str(res['超一击']['dmg']) + '(' + res['超一击']['p'][:4] + ') 100%暴击不被剪枝, top1=275,741 通过]')

        # ⑦ 回归: 组队开「全技能」列表正常渲染(曾有 cfg is not defined 崩溃: 必暴标记误用排行变量)
        pg.evaluate("() => { state.stack = []; push({ page: 'team', title: '组队' }); }")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => document.getElementById('m2').click()")   # 全技能·被动+主动MP
        pg.wait_for_timeout(3500)
        t7 = pg.evaluate("() => ({ len: (document.getElementById('tarea')||{innerText:''}).innerText.length, sk: state.team.skills })")
        print('[⑦ 组队全技能]', t7)
        assert t7['sk'] is True and t7['len'] > 500, t7
        assert not errors, errors[:4]
        print('[⑦ 组队开全技能 排行列表正常渲染 通过]')

        # ⑧ 回归: 尊者高达(EX)+东方不败 100%暴击(武器20+机体被动25+机师被动15+技能40), 剪枝不得误剪
        res = pg.evaluate("""() => {
          const f = filt('rank');
          const R = (vg, auto) => buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: vg, crit: false },
            { passive: true, cpassive: true, skills: true, condAll: true, autoVigor: auto, multiPhase: false, star: 3,
              spU: true, s3u: true, sspU: true, pSpU: true });
          const bd = R('default', true).find(r => r.unitId === 1200001350);
          const bp = R('supercharged', false).find(r => r.unitId === 1200001350);
          const b2 = R('supercharged', false)[0];
          return { 默认: bd && { p: bd.pilot.name.slice(0,6), dmg: bd.dmg, rate: bd.critRate, fc: bd.forceCrit },
                   超一击: bp && { p: bp.pilot.name.slice(0,6), dmg: bp.dmg, rate: bp.critRate, fc: bp.forceCrit },
                   超一击top1: b2 && { n: b2.unit.name, dmg: b2.dmg } }; }""")
        print('[⑧ 尊者EX]', res)
        assert '东方不败' in res['默认']['p'] and res['默认']['fc'] is True and res['默认']['rate'] == 100, res
        assert '东方不败' in res['超一击']['p'] and res['超一击']['fc'] is True, res
        assert res['超一击top1']['dmg'] == 275741, res   # 与⑥一致(剪枝关闭后精确解不变)
        print('[⑧ 尊者高达(EX)+东方不败: 100%暴击/必暴 且不再被剪枝 通过]')

        # ⑨ 特性页「必暴组合」: 机体+驾驶员清单(含多段增益标注)
        pg.evaluate("() => { state.featKind = 'baobi'; state.stack = []; push({ page: 'feat', title: '特性' }); }")
        pg.wait_for_timeout(1500)
        f9 = pg.evaluate("() => ({ txt: (document.getElementById('farea')||{innerText:''}).innerText, n: document.querySelectorAll('#farea .lrow').length, tot: baobiCombos().length })")
        print('[⑨ 必暴组合] 行数:', f9['n'])
        assert pg.evaluate("() => document.body.innerText.includes('必暴组合')"), '缺必暴组合chip'
        assert f9['n'] >= 8 and f9['n'] == f9['tot'], f9
        for kw in ('无限正义高达', '尊者高达', '东方不败', '武斗家尼摩', '真·飞鸟', '多段增益必暴'):
            assert kw in f9['txt'], kw
        print('[⑨ 必暴机体+驾驶员组合清单(含武器必暴) 通过]')

        # ⑨b 无限正义(EX): 实际计算结果 — 组成=30(超一击机体被动)+30(武器)+主动技能≥40=100%;
        #     有MP技能者排最前(MP量先, 气势最高), 再按主动技能值降序; 不做名单式排除(飞鸟除外=已知数据bug)
        inf = pg.evaluate("""() => baobiCombos().filter(x => x.uid === 1330002850).map(x => [x.pilotName, x.desc, x.pid])""")
        print('[⑨b 无限正义EX行]', [(x[0], x[1][:26]) for x in inf])
        assert [x[2] for x in inf] == [1200001200, 1431000100, 1330001804, 1430000109, 1080000101, 1219000201, 1166000100], inf
        assert all(('MP技能+6' in x[1] and '技能40' in x[1]) for x in inf[:3]), inf[:3]   # 东方/艾路吉/阿斯兰: MP技能者在前
        assert '技能50' in inf[3][1] and 'MP技能' not in inf[3][1], inf[3]                 # 三日月
        assert '技能50' in inf[4][1] and 'MP技能' not in inf[4][1], inf[4]                 # 卡缪
        assert all(('武器30' in x[1] and '机体被动30' in x[1] and '=100%' in x[1]) for x in inf), inf
        print('[⑨b 无限正义EX: 实际计算(30+30+主动技能≥40) + MP技能标注/排最前 通过]')

        # ⑨c 必暴组合行: 机师类型标记(攻击/防御/支援) — 阿斯兰=攻击型, 迪奥=防御型, 艾路吉=支援型; 机师副头像带类型角标
        dom = pg.evaluate("""() => { const rows = [...document.querySelectorAll('#farea .lrow')];
          const pick = n => { const el = rows.find(x => x.innerText.includes(n)); return el ? { t: el.innerText, rb: el.querySelectorAll('.roleb').length } : null; };
          return { a: pick('阿斯兰·萨拉'), d: pick('迪奥·麦克斯韦尔'), e: pick('艾路吉·米拉吉') }; }""")
        print('[⑨c 机师类型标记]', dom['a'] and '攻击' in dom['a']['t'], dom['d'] and '防御' in dom['d']['t'], dom['e'] and '支援' in dom['e']['t'], '| 角标数:', dom['a'] and dom['a']['rb'])
        assert dom['a'] and '攻击' in dom['a']['t'] and dom['d'] and '防御' in dom['d']['t'] and dom['e'] and '支援' in dom['e']['t'], dom
        assert dom['a']['rb'] >= 2 and dom['d']['rb'] >= 2, dom   # 机体头像 + 机师副头像 两个类型角标
        print('[⑨c 必暴组合行机师类型标记(攻击/防御/支援+头像角标) 通过]')

        # ⑨d 规则定死回归: 真·飞鸟(1330000103)二阶段必暴 对所有机体生效(多段增益开) — 不得加搭乗门
        b2 = pg.evaluate("""() => { const ry = { upassive: true, cpassive: true, skills: true, condAll: true, vigor: 'supercharged' };
          const g = (uid, mp) => pilotCritInfo(uid, 1330000103, metaOf(uid), Object.assign({ multiPhase: mp }, ry)).guar;
          return { uz: [g(1330002850, true), g(1330002800, true)], off: g(1330002850, false) }; }""")
        print('[⑨d 真·飞鸟二阶段必暴·全机体]', b2)
        assert b2['uz'] == [True, True] and b2['off'] is False, b2
        print('[⑨d 真·飞鸟二阶段必暴对所有机体生效(定死) 通过]')

        # ⑩ 对特定标签目标生效的条件注明(机体被动+机师被动+武器特效) + 组队防御机体匹配
        # 计算页: AGE-1素体型(优势:维根 攻+15%) + 阿姆罗(敌方含红色 增伤+10%)
        pg.evaluate("""() => { const c = state.calc; c.unitId = 1400008110; c.charId = 1001000100; c.crit = false; c.vigor = 'supercharged';
          c.first = false; c.skills = false; c.mp = false; c.ca = true; c.passive = true; c.cpassive = true; state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""")
        pg.wait_for_timeout(1200)
        c10 = pg.evaluate("""() => { const t = document.body.innerText;
          const top = document.querySelector('#picku').innerText;
          return { top: top.includes('条件:敌·维根'),
                   det: t.includes('对特定对手生效的加成') && t.includes('机体 敌「维根」攻击+15%') && t.includes('机师 敌「红色」增伤+10%'),
                   t10: [...document.querySelectorAll('#view .trow')].some(el => el.innerText.includes('条件:敌')) }; }""")
        print('[⑩ 计算页条件注明]', c10)
        assert c10['top'] and c10['det'] and c10['t10'], c10
        # 武器条件特效行: 全装甲高达(1007001160) 2连装光束步枪(条件:自护公国军)
        pg.evaluate("""() => { const c = state.calc; c.unitId = 1007001160; c.charId = null; c.ca = true; state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""")
        pg.wait_for_timeout(900)
        w10 = pg.evaluate("""() => { const tr = document.querySelector('#view table.ctable tr[data-wid="100700116003"]');
          return tr ? tr.innerText.includes('条件:敌·自护公国军') : null; }""")
        print('[⑩ 武器行条件特效注明]', w10)
        assert w10 is True, w10
        # 排行: notice 字段(条件全开计入 → 标注)
        r10 = pg.evaluate("""() => { const f = filt('rank');
          const R = buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'supercharged', crit: false },
            { passive: true, cpassive: true, skills: false, condAll: true, autoVigor: false, multiPhase: false, star: 3, spU: true, s3u: true, sspU: true, pSpU: true });
          const a = R.find(r => r.unitId === 1400008110);
          return a && a.notice; }""")
        print('[⑩ 排行行notice]', r10)
        assert r10 == '敌·维根', r10
        # 组队匹配: 防御机体标签命中→生效; 未命中且条件被动关→不生效; 通用+条件被动开→全部生效; 通用+关→不生效
        t10 = pg.evaluate("""() => { const f = filt('rank');
          const R = (em, ca) => buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'supercharged', crit: false },
            { passive: true, cpassive: true, skills: false, condAll: ca, autoVigor: false, multiPhase: false, star: 3, spU: true, s3u: true, sspU: true, pSpU: true, enemyMeta: em });
          const g = R2 => { const a = R2.find(r => r.unitId === 1400008110); return a ? a.notice : null; };
          return { 维根防: g(R(metaOf(1400003810), false)), 吉翁防: g(R(metaOf(1001003050), false)), 通用开: g(R(null, true)), 通用关: g(R(null, false)) }; }""")
        print('[⑩ 组队防御匹配]', t10)
        assert t10['维根防'] == '敌·维根' and t10['吉翁防'] == '' and t10['通用开'] == '敌·维根' and t10['通用关'] == '', t10
        # 组队支援型行 fxSup: 武器条件特效按防御机体标签匹配(全装甲高达: 自护公国军)
        f10 = pg.evaluate("""() => { const f = filt('team');
          const F = (ca, em) => unitDamageFxOf(1007001160, null, f, false, true, { condAll: ca, sspU: true, enemyMeta: em });
          return { 开: F(true, null).includes('条件:敌·自护公国军'), 关: F(false, null).includes('条件:敌·自护公国军'),
                   吉翁防: F(false, metaOf(1001003050)).includes('条件:敌·自护公国军'), 维根防: F(false, metaOf(1400003810)).includes('条件:敌·自护公国军'),
                   关态无特效: !F(false, null).includes('降防3%') }; }""")
        print('[⑩ 支援型行条件特效匹配]', f10)
        assert f10['开'] and not f10['关'] and f10['吉翁防'] and not f10['维根防'] and f10['关态无特效'], f10
        print('[⑩ 对特定标签目标生效的加成注明(机体/机师/武器) + 组队防御匹配 通过]')

        # ⑪ 特性「特攻」: 对特定对手(敌方标签/系列/驾驶员)生效的 机体+机师 清单
        pg.evaluate("() => { state.featKind = 'tekko'; state.stack = []; push({ page: 'feat', title: '特性' }); }")
        pg.wait_for_timeout(1500)
        k11 = pg.evaluate("""() => { const rows = tekkoList();
          const ultSet = new Set(q('SELECT id FROM units WHERE ult=1').map(r => r.id));
          const ultCnt = rows.filter(x => x.target_type === 'unit' && ultSet.has(x.target_id)).length;
          const n = document.querySelectorAll('#farea .lrow').length;
          const txt = (document.getElementById('farea')||{innerText:''}).innerText;
          const u = rows.filter(x => x.target_type === 'unit' && !ultSet.has(x.target_id)).length, c = rows.filter(x => x.target_type === 'char').length;
          const age = rows.find(x => x.target_id === 1400008110), amu = rows.find(x => x.target_id === 1001000100);
          return { n, tot: rows.length, ultCnt, shown: u + c, u, c, chip: document.body.innerText.includes('特攻'),
                   tk: !!document.getElementById('tkult'), tkOn: (document.getElementById('tkult')||{innerText:''}).innerText || '',
                   noUltInPage: !ultCnt || !txt.includes('β·阿吉尔'),
                   age: age && (age.label + '|' + age.desc), amu: amu && (amu.label + '|' + amu.desc), pageHas: txt.includes('敌·红色') }; }""")
        print('[⑪ 特性特攻]', k11)
        assert k11['n'] == k11['shown'] and k11['u'] >= 20 and k11['c'] >= 1 and k11['chip'] and k11['tk'] and '开' in k11['tkOn'], k11
        assert k11['noUltInPage'], k11   # 默认「屏蔽ULT」开: ULT机体(β·阿吉尔等)不入列表
        assert k11['age'] and '敌·维根' in k11['age'] and '攻击+15%' in k11['age'], k11
        assert k11['amu'] and '敌·红色' in k11['amu'] and '增伤+10%' in k11['amu'], k11
        assert k11['pageHas'], k11
        # 关闭「屏蔽ULT」→ 全量(含ULT机体)
        pg.evaluate("() => document.getElementById('tkult').click()")
        pg.wait_for_timeout(900)
        k11b = pg.evaluate("""() => ({ n: document.querySelectorAll('#farea .lrow').length,
          tkOn: (document.getElementById('tkult')||{innerText:''}).innerText || '', hasUlt: document.getElementById('farea').innerText.includes('β·阿吉尔') })""")
        print('[⑪b 屏蔽关]', k11b)
        assert k11b['n'] == k11['tot'] and '关' in k11b['tkOn'] and k11b['hasUlt'], k11b
        pg.evaluate("() => document.getElementById('tkult').click()")   # 恢复默认
        pg.wait_for_timeout(700)
        print('[⑪ 特性「特攻」列表(机体/机师+屏蔽ULT开关: 默认开=ULT不入列, 关=全量) 通过]')

        # ⑫ 组队 防御/支援防御生效(修复: _gkey漏guard/sdef → 开关后攻方伤害不变的缓存bug)
        #    防御目标 高达(EX)+阿姆罗·雷, 攻方 神高达(EX): 无选择防御(仅技能减伤15) > 选择防御(承伤-75) > +支援防御(承伤-115)
        pg.evaluate("""() => { const t = state.team;
          t.dunit = 1001000150; t.dchar = 1001000100; t.guard = true; t.sdef = false;
          state.stack = []; push({ page: 'team', title: '组队' }); }""")
        pg.wait_for_timeout(2800)
        d_off = pg.evaluate("() => { const G = state.teamCache.G; const f = G.main.find(x => x.unit.id === 1200003950); return f ? f.dmg : null; }")
        pg.evaluate("() => { state.team.sdef = true; render(); }")
        pg.wait_for_timeout(2800)
        d_on = pg.evaluate("() => { const G = state.teamCache.G; const f = G.main.find(x => x.unit.id === 1200003950); return f ? f.dmg : null; }")
        pg.evaluate("() => { state.team.sdef = false; state.team.guard = false; render(); }")
        pg.wait_for_timeout(2800)
        d_nog = pg.evaluate("() => { const G = state.teamCache.G; const f = G.main.find(x => x.unit.id === 1200003950); return f ? f.dmg : null; }")
        print('[⑫ 组队减伤开关] 无姿态防:', d_nog, '| 选择防御(承伤-75):', d_off, '| +支援防御(-115):', d_on)
        assert d_off and d_on and d_nog and d_on < d_off < d_nog, (d_nog, d_off, d_on)
        print('[⑫ 组队 选择防御/支援防御 开关驱动伤害变化(防御机体减伤生效) 通过]')

        # ⑬ 武器使用限制补全: 可变式杖型步枪 EX(150100225004) 显示「消耗10%HP即可使用」; 同族普通武器无此条
        pg.evaluate("() => { state.stack = []; push({ page: 'weapon', title: '', id: 150100225004 }); }")
        pg.wait_for_timeout(900)
        w13 = pg.evaluate("""() => { const t = (document.getElementById('view')||{innerText:''}).innerText;
          return { hp: t.includes('使用限制') && t.includes('消耗10%HP即可使用'), nm: t.includes('可变式杖型步枪 EX') }; }""")
        pg.evaluate("() => { state.stack = []; push({ page: 'weapon', title: '', id: 150100225001 }); }")
        pg.wait_for_timeout(900)
        w13b = pg.evaluate("() => (document.getElementById('view')||{innerText:''}).innerText.includes('消耗10%HP')")
        print('[⑬ 武器使用限制]', w13, '| 普通武器含HP限制:', w13b)
        assert w13['hp'] and w13['nm'] and not w13b, (w13, w13b)
        print('[⑬ 武器页使用限制补全(消耗HP) 通过]')

        # ⑬b 使用地点(in_*): 100100280002(水中×) → 「水中不可用」; 全场地可用武器无此行
        pg.evaluate("() => { state.stack = []; push({ page: 'weapon', title: '', id: 100100280002 }); }")
        pg.wait_for_timeout(900)
        a13 = pg.evaluate("""() => { const t = (document.getElementById('view')||{innerText:''}).innerText;
          return { area: t.includes('使用地点') && t.includes('水中不可用'), all: t.includes('宇宙/空中/地上/水面可用') }; }""")
        pg.evaluate("() => { state.stack = []; push({ page: 'weapon', title: '', id: 150100225004 }); }")
        pg.wait_for_timeout(900)
        a13b = pg.evaluate("() => (document.getElementById('view')||{innerText:''}).innerText.includes('使用地点')")
        print('[⑬b 使用地点]', a13, '| 全场地武器含地点行:', a13b)
        assert a13['area'] and a13['all'] and not a13b, (a13, a13b)
        print('[⑬b 武器页使用地点(不可用场地)显示 通过]')

        # ⑭ 组队「移动○筛选」: 选定水中 → 仅显示水中适性○(3)机体; 关 → 混入△/×外机体
        pg.evaluate("""() => { const t = state.team; t.terr = 'water'; t.terrO = true; t.dunit = null; t.dchar = null; t.guard = false; t.sdef = false;
          state.stack = []; push({ page: 'team', title: '组队' }); }""")
        pg.wait_for_timeout(3000)
        t14 = pg.evaluate("""() => { const G = state.teamCache.G;
          const bad = G.main.filter(r => { const g = q1('SELECT terrain_water w FROM units WHERE id=?', [r.unitId]); return !g || g.w !== 3; }).length;
          return { n: G.main.length, bad, chip: !!document.getElementById('tterro'), on: (document.getElementById('tterro')||{innerText:''}).innerText || '' }; }""")
        pg.evaluate("() => { state.team.terrO = false; render(); }")
        pg.wait_for_timeout(3000)
        t14b = pg.evaluate("""() => { const G = state.teamCache.G;
          const n3 = G.main.filter(r => { const g = q1('SELECT terrain_water w FROM units WHERE id=?', [r.unitId]); return g && g.w === 3; }).length;
          return { n: G.main.length, n3 }; }""")
        print('[⑭ 移动○筛选]', t14, '| 关:', t14b)
        assert t14['chip'] and t14['n'] > 0 and t14['bad'] == 0 and '开' in t14['on'], t14
        assert t14b['n'] >= t14['n'] and t14b['n3'] < t14b['n'], (t14, t14b)   # 关: 榜单混入非○机体
        pg.evaluate("() => { state.team.terr = ''; state.team.terrO = false; render(); }")
        print('[⑭ 组队 移动○筛选(选定场地仅○机体, 默认关) 通过]')

        # ⑮ 组队 防御盾标识+筛选(仅防御型TOP/进攻盾TOP): 地形下方显示 盾/无盾; 筛选后三列表全带盾, 攻击表不受影响
        pg.evaluate("""() => { const t = state.team; t.shieldF = false; t.terr = ''; t.terrO = false;
          state.stack = []; push({ page: 'team', title: '组队' }); }""")
        pg.wait_for_timeout(3000)
        s15 = pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
          const cd = ttl => cards.find(x => (x.querySelector('h4') || {innerText: ''}).innerText.includes(ttl));
          const defc = cd('防御型 TOP10 · 输出'), csc = cd('进攻盾');
          return { chip: !!document.getElementById('tshieldf'), on: (document.getElementById('tshieldf')||{innerText:''}).innerText || '',
                   defMark: defc ? (defc.innerText.includes('无盾') || defc.innerText.includes('盾')) : null,
                   csMark: csc ? (csc.innerText.includes('无盾') || csc.innerText.includes('盾')) : null }; }""")
        pg.evaluate("() => { state.team.shieldF = true; render(); }")
        pg.wait_for_timeout(3000)
        s15b = pg.evaluate("""() => { const sh = new Set(q("SELECT target_id FROM features WHERE target_type='unit' AND feature='shield_defense'").map(r => r.target_id));
          const cards = [...document.querySelectorAll('#tarea .card')];
          const ids = ttl => { const c = cards.find(x => (x.querySelector('h4') || {innerText: ''}).innerText.includes(ttl)); return c ? [...c.querySelectorAll('.trow')].map(el => +el.dataset.id) : null; };
          const defo = ids('防御型 TOP10 · 输出'), defe = ids('防御型 TOP10 · 有效耐久'), cs = ids('进攻盾');
          const all = a => !!a && a.length > 0 && a.every(id => sh.has(id));
          const atk = cards.find(x => (x.querySelector('h4') || {innerText: ''}).innerText.includes('攻击型 TOP10 · 单发'));
          return { defoOk: all(defo), defeOk: all(defe), csOk: all(cs), atkNodef: atk ? !atk.innerText.includes('无盾') : null,
                   n: { defo: defo && defo.length, defe: defe && defe.length, cs: cs && cs.length } }; }""")
        print('[⑮ 防御盾]', s15, '|', s15b)
        assert s15['chip'] and '关' in s15['on'] and s15['defMark'] and s15['csMark'], s15
        assert s15b['defoOk'] and s15b['defeOk'] and s15b['csOk'] and s15b['atkNodef'] is True, s15b
        pg.evaluate("() => { state.team.shieldF = false; render(); }")
        print('[⑮ 组队 防御盾标识(地形下方)+筛选(仅防御TOP/进攻盾TOP生效) 通过]')

        # ⑯ 组队目标化改版: 文案(选择目标机体和机师/目标全能力增加/我方全能力增加) + 防御机「受」(目标反击输出)
        #    选择防御/支援防御对我方防御机生效 → 开防御姿态后「受」应全面下降
        pg.evaluate("""() => { const t = state.team; t.terr = ''; t.terrO = false; t.shieldF = false;
          t.dunit = 1001000150; t.dchar = 1001000100; t.guard = false; t.sdef = false;
          state.stack = []; push({ page: 'team', title: '组队' }); }""")
        pg.wait_for_timeout(3200)
        r16 = pg.evaluate("""() => { const txt = document.getElementById('view').innerText;
          const cards = [...document.querySelectorAll('#tarea .card')];
          const pick = ttl => cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes(ttl));
          const recv = c => c ? [...c.querySelectorAll('.trow')].map(el => { const m = el.innerText.match(/受\\s*([\\d,]+)/); return m ? +m[1].replace(/,/g, '') : null; }) : [];
          const cv = recv(pick('进攻盾')).filter(v => v != null), ev = recv(pick('防御型 TOP10 · 有效耐久')).filter(v => v != null);
          return { 目标文案: txt.includes('目标:') && !txt.includes('防御目标:'), 目标全能: !!document.getElementById('tdatk') && !!document.getElementById('tddef') && !!document.getElementById('tdhp'), 我方全能: txt.includes('我方:') && txt.includes('攻击') && txt.includes('HP'),
                   cs: cv, eh: ev, atk受: recv(pick('攻击型 TOP10 · 单发')).some(v => v != null) }; }""")
        pg.evaluate("() => { state.team.guard = true; render(); }")
        pg.wait_for_timeout(3200)
        r16b = pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
          const cs = cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes('进攻盾'));
          return [...cs.querySelectorAll('.trow')].map(el => { const m = el.innerText.match(/受\\s*([\\d,]+)/); return m ? +m[1].replace(/,/g, '') : null; }).filter(v => v != null); }""")
        print('[⑯ 目标化+受]', r16, '| 选择防御开 cs受:', r16b)
        assert r16['目标文案'] and r16['目标全能'] and r16['我方全能'], r16
        assert len(r16['cs']) >= 3 and len(r16['eh']) >= 3 and not r16['atk受'], r16
        assert len(r16b) == len(r16['cs']) and all(a > b for a, b in zip(r16['cs'], r16b)), (r16['cs'], r16b)
        pg.evaluate("() => { state.team.guard = false; render(); }")
        print('[⑯ 组队目标化文案 + 防御机「受」伤害(目标反击输出, 随防御姿态生效) 通过]')

        # ⑰ 我方攻防(所有top生效·仅攻防) + 自定义增强(攻防hp机动)对后两top(HP↑受↓) + 增强后HP与受剩%显示
        def read17():
            return pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
          const pick = ttl => cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes(ttl));
          const num = (el, re) => { const m = el && el.innerText.match(re); return m ? +m[1].replace(/,/g, '') : null; };
          const csRows = [...(pick('进攻盾') ? pick('进攻盾').querySelectorAll('.trow') : [])];
          const ehRows = [...(pick('防御型 TOP10 · 有效耐久') ? pick('防御型 TOP10 · 有效耐久').querySelectorAll('.trow') : [])];
          const g0 = state.teamCache.G.main.find(x => x.unit.id === 1200003950);
          return { dmg: g0 && g0.dmg,
            cs: csRows.map(el => [+el.dataset.id, num(el, /受\\s*([\\d,]+) 剩/), num(el, /剩(\\d+)%/)]),
            eh: ehRows.map(el => [+el.dataset.id, num(el, /(?:^|[^A-Za-z])HP\\s*([\\d,]+)/), num(el, /eHP\\s*([\\d,]+)/), num(el, /受\\s*([\\d,]+) 剩/)]) }; }""")
        pg.evaluate("""() => { const t = state.team; t.terr = ''; t.terrO = false; t.shieldF = false; t.atkup = 0; t.cbOn = false; t.buffs = [];
          t.dunit = 1001000150; t.dchar = 1001000100; t.guard = true; t.sdef = false;
          state.stack = []; push({ page: 'team', title: '组队' }); }""")
        pg.wait_for_timeout(3200)
        base = read17()
        uidCs = base['cs'][0][0]; uidEh = base['eh'][0][0]
        assert base['cs'][0][1] and base['cs'][0][2] is not None and base['eh'][0][1], base
        # 我方攻击44: 输出↑, 防御列表不变
        pg.evaluate("() => { state.team.atkup = 44; render(); }")
        pg.wait_for_timeout(3200)
        a44 = read17()
        eh44 = next((x for x in a44['eh'] if x[0] == uidEh), None)
        print('[⑰ 我方攻击44%] 击伤:', base['dmg'], '→', a44['dmg'], '| eh不应变:', base['eh'][0], '→', eh44)
        assert a44['dmg'] > base['dmg'], ('我方攻击: 输出top生效', base['dmg'], a44['dmg'])
        assert eh44 and eh44[2] == base['eh'][0][2] and eh44[1] == base['eh'][0][1], '我方攻击不应影响防御列表'
        # 我方防御44: eHP↑/受↓, HP不变
        pg.evaluate("() => { state.team.atkup = 0; state.team.oDef = 44; render(); }")
        pg.wait_for_timeout(3200)
        d44 = read17()
        ehd44 = next((x for x in d44['eh'] if x[0] == uidEh), None)
        csd44 = next((x for x in d44['cs'] if x[0] == uidCs), None)
        print('[⑰ 我方防御44%] eh:', ehd44, '| cs受:', base['cs'][0][1], '→', csd44 and csd44[1])
        assert ehd44 and ehd44[2] > base['eh'][0][2] and csd44 and csd44[1] < base['cs'][0][1], '我方防御: eHP↑且受↓'
        assert ehd44[1] == base['eh'][0][1], '我方防御不应改HP'
        # 我方HP44: HP↑
        pg.evaluate("() => { state.team.oDef = 0; state.team.oHp = 44; render(); }")
        pg.wait_for_timeout(3200)
        h44 = read17()
        ehh44 = next((x for x in h44['eh'] if x[0] == uidEh), None)
        print('[⑰ 我方HP44%] HP:', base['eh'][0][1], '→', ehh44 and ehh44[1])
        assert ehh44 and ehh44[1] > base['eh'][0][1], '我方HP: HP↑'
        pg.evaluate("() => { state.team.oHp = 0; render(); }")
        pg.wait_for_timeout(1200)
        tag = pg.evaluate("""(uid) => { const r = q1('SELECT tg.name FROM unit_tags ut JOIN tags tg ON tg.id=ut.tag_id WHERE ut.unit_id=? LIMIT 1', [uid]); return r && r.name; }""", uidEh)
        pg.evaluate("""(tn) => { const t = state.team; t.cbuff = { tags: [tn], pct: 50 }; t.cbOn = true; render(); }""", tag)
        pg.wait_for_timeout(3200)
        c50 = read17()
        eh50 = next((x for x in c50['eh'] if x[0] == uidEh), None)
        print('[⑰ 自定义增强50%] 该机HP:', base['eh'][0][1], '→', eh50, '| 受:', base['eh'][0][3], '→', eh50 and eh50[3])
        assert eh50 and eh50[1] and eh50[1] > base['eh'][0][1], ('自定义增强: HP↑(增强后HP显示)', base['eh'][0], eh50)
        assert eh50[3] is not None and base['eh'][0][3] is not None and eh50[3] < base['eh'][0][3], '自定义增强应降低受(队伍增强对后两top生效)'
        pg.evaluate("() => { state.team.atkup = 0; state.team.cbOn = false; state.team.guard = false; render(); }")
        print('[⑰ 我方攻防(全top/仅攻防) + 自定义增强对后两top(HP↑/受↓) + 受剩%+增强后HP 通过]')

        # ⑱ 双向对称回归(用户报「首动下目标对我方防御机远低于我方对目标」): 同配置镜像对 — 神高达+多蒙 ⇄ 锡蒙力维达尔EX+浦木宏 两向数值应一致
        pg.evaluate("""() => { const t = state.team;
          Object.assign(t, { vigor:'default', first:true, fdth:false, skills:false, mp:false, ca:true, star:3,
            suppId:null, shipStar:0, buffs:[], cbOn:false, atkup:0, oDef:0, oHp:0, defup:0, terr:'', guard:false, sdef:false, shieldF:false, terrO:false });
          t.dunit=1430004850; t.dchar=1060000100; state.stack=[]; push({ page:'team', title:'组队' }); }""")
        pg.wait_for_timeout(3200)
        fwd18 = pg.evaluate("""() => { const G = state.teamCache.G; const r = G.main.find(x => x.unit.id === 1200003950); return r && r.dmg; }""")
        pg.evaluate("() => { state.team.dunit=1200003950; state.team.dchar=1200000103; render(); }")
        pg.wait_for_timeout(3200)
        rev18 = pg.evaluate("() => (state._recv || {})[1430004850] || null")
        print('[⑱ 双向对称] 正向(神高达→锡蒙力):', fwd18, '| 反向(锡蒙力受):', rev18)
        assert fwd18 and rev18 and abs(fwd18 - rev18) <= 2, (fwd18, rev18)
        pg.evaluate("() => { state.team.dunit = null; state.team.dchar = null; state.team.guard = false; render(); }")
        print('[⑱ 组队双向对称(首动镜像对: 正向伤害=反向受, 防御机搭配驾驶员守备/技能防御/减伤参与) 通过]')

        # ⑲ 后两top排序: 选定目标→按剩余HP(hp-受)由多到少; 未选目标→维持eHP排序
        pg.evaluate("""() => { const t = state.team; t.dunit = 1001000150; t.dchar = 1001000100; t.guard = false; t.sdef = false; t.shieldF = false; t.terr = ''; t.atkup = 0; t.oDef = 0; t.oHp = 0; t.cbOn = false; t.buffs = [];
          state.stack = []; push({ page: 'team', title: '组队' }); }""")
        pg.wait_for_timeout(3200)
        s19 = pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
          const pick = ttl => cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes(ttl));
          const num = (el, re) => { const m = el.innerText.match(re); return m ? +m[1].replace(/,/g, '') : null; };
          const rem = c => [...c.querySelectorAll('.trow')].map(el => { const hp = num(el, /(?:^|[^A-Za-z])HP\\s*([\\d,]+)/); const rv = num(el, /受\\s*([\\d,]+) 剩/); return (hp != null && rv != null) ? hp - rv : null; });
          const e = rem(pick('有效耐久')), c2 = rem(pick('进攻盾'));
          const desc = a => a.length > 0 && a.every((v, i) => v != null && (i === 0 || a[i-1] >= v));
          return { e: e, c: c2, eOk: desc(e), cOk: desc(c2) }; }""")
        pg.evaluate("() => { state.team.dunit = null; state.team.dchar = null; render(); }")
        pg.wait_for_timeout(3000)
        s19b = pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
          const eh = cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes('有效耐久'));
          const vals = [...eh.querySelectorAll('.trow')].map(el => { const m = el.innerText.match(/eHP\\s*([\\d,]+)/); return m ? +m[1].replace(/,/g, '') : null; });
          return vals.length > 0 && vals.every((v, i) => v != null && (i === 0 || vals[i-1] >= v)); }""")
        print('[⑲ 剩余HP排序]', s19['e'], '|', s19['c'], '| eOk/cOk:', s19['eOk'], s19['cOk'], '| 无目标eHP降序:', s19b)
        assert s19['eOk'] and s19['cOk'] and s19b, (s19, s19b)
        print('[⑲ 选定目标后 后两top按剩余HP由多到少; 未选目标维持eHP排序 通过]')

        # ⑳ 目标攻击/防御 增强: 目标=神高达+多蒙, tAtk 0→50 → 反击受(锡蒙力)上升; tDef 0→50 → 正向伤害下降
        pg.evaluate("""() => { const t = state.team; Object.assign(t, { vigor:'default', first:true, fdth:false, skills:false, mp:false, ca:true, star:3,
            suppId:null, shipStar:0, buffs:[], cbOn:false, atkup:0, oDef:0, oHp:0, tAtk:0, tDef:0, tHp:0, terr:'', guard:false, sdef:false, shieldF:false, terrO:false });
          t.dunit=1200003950; t.dchar=1200000103; state.stack=[]; push({ page:'team', title:'组队' }); }""")
        pg.wait_for_timeout(3200)
        r0 = pg.evaluate("() => (state._recv || {})[1430004850] || null")
        pg.evaluate("() => { state.team.tAtk = 50; render(); }")
        pg.wait_for_timeout(3200)
        r1 = pg.evaluate("() => (state._recv || {})[1430004850] || null")
        pg.evaluate("() => { const t = state.team; t.tAtk = 0; t.dunit = 1430004850; t.dchar = 1060000100; render(); }")
        pg.wait_for_timeout(3200)
        f0 = pg.evaluate("() => { const G = state.teamCache.G; const r = G.main.find(x => x.unit.id === 1200003950); return r && r.dmg; }")
        pg.evaluate("() => { state.team.tDef = 50; render(); }")
        pg.wait_for_timeout(3200)
        f1 = pg.evaluate("() => { const G = state.teamCache.G; const r = G.main.find(x => x.unit.id === 1200003950); return r && r.dmg; }")
        print('[⑳ 目标攻击/防御] 反击受(攻击+50):', r0, '→', r1, '| 正向伤害(防御+50):', f0, '→', f1)
        assert r0 and r1 and r1 > r0 * 1.2, ('目标攻击应对反击生效', r0, r1)
        assert f0 and f1 and f1 < f0, ('目标防御应降正向', f0, f1)
        pg.evaluate("() => { state.team.tAtk = 0; state.team.tDef = 0; state.team.dunit = null; state.team.dchar = null; render(); }")
        print('[⑳ 目标攻击(反击)/目标防御(正向) 分别生效 通过]')

        # ㉑ 目标三项增强(攻击/防御/HP)界面 + 后两top 盾标识后显示移动力
        pg.evaluate("""() => { const t = state.team; Object.assign(t, { tAtk:0, tDef:0, tHp:0, atkup:0, oDef:0, oHp:0, cbOn:false, buffs:[],
            dunit:1200003950, dchar:1200000103, guard:false, sdef:false, shieldF:false, terr:'' });
          state.stack = []; push({ page:'team', title:'组队' }); }""")
        pg.wait_for_timeout(3200)
        k21 = pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
          const pick = ttl => cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes(ttl));
          const rowTxt = pick('有效耐久').querySelectorAll('.trow')[0].innerText.replace(/\\n/g, '|');
          const i1 = rowTxt.indexOf('盾'), i2 = rowTxt.search(/移\d+/);
          const mv = +(rowTxt.match(/移(\d+)/) || [0, 0])[1];   // 移动力数值(应为3-8, 防★倍率误乘)
          const csTxt = pick('进攻盾').querySelectorAll('.trow')[0].innerText;
          return { inputs: !!document.getElementById('tdatk') && !!document.getElementById('tddef') && !!document.getElementById('tdhp'),
                   eh移: i1 >= 0 && i2 > i1, cs移: /移\d+/.test(csTxt), mvOk: mv >= 3 && mv <= 8, rowTxt: rowTxt.slice(0, 100) }; }""")
        pg.evaluate("() => { state.team.tHp = 50; render(); }")
        pg.wait_for_timeout(3200)
        k21b = pg.evaluate("""() => { const t = document.getElementById('dpick').innerText;
          return { hpArrow: /耐久\s*[\d,]+→/.test(t.replace(/\\n/g, ' ')), pick: t.replace(/\\n/g, '|').slice(0, 120) }; }""")
        print('[㉑ 目标三项+移动]', k21, '| 目标HP50:', k21b)
        assert k21['inputs'] and k21['eh移'] and k21['cs移'] and k21['mvOk'], k21
        assert k21b['hpArrow'], k21b
        pg.evaluate("() => { state.team.tHp = 0; state.team.dunit = null; state.team.dchar = null; render(); }")
        print('[㉑ 目标攻击/防御/HP 三项增强 + 后两top盾后移动力显示 通过]')

        # ㉒ 第5个top 单/双/全部 支援防御档位: 双=支防+2(默认); 单=支防+1; 全部=+1与+2均可
        def readModes():
            return pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
              const eh = cards.find(x => (x.querySelector('h4')||{innerText:''}).innerText.includes('有效耐久'));
              const ns = [...eh.querySelectorAll('.trow')].map(el => { const m = el.innerText.match(/支防\+(\\d+)/); return m ? +m[1] : 0; });
              const chips = [...eh.querySelectorAll('[data-smode]')].map(el => [el.dataset.smode, el.className.includes('gold')]);
              return { ns, chips }; }""")
        pg.evaluate("() => { const t = state.team; t.sdefMode = '2'; t.shieldF = false; t.dunit = 1200003950; t.dchar = 1200000103; t.ca = true; state.stack = []; push({ page:'team', title:'组队' }); }")   # 固定环境: 神高达EX+多蒙(全部档混合分布依赖目标标签与机师标签)
        pg.wait_for_timeout(3200)
        m2 = readModes()
        pg.evaluate("() => document.querySelector('[data-smode=\"1\"]').click()")   # 点击(曾绑定在redraw前致无效)
        pg.wait_for_timeout(3200)
        m1 = readModes()
        pg.evaluate("() => document.querySelector('[data-smode=\"all\"]').click()")
        pg.wait_for_timeout(3200)
        ma = readModes()
        print('[㉒ 档位] 双:', m2['ns'], '| 单:', m1['ns'], '| 全部:', ma['ns'])
        assert m2['chips'] and [c[0] for c in m2['chips'] if c[1]] == ['2'] and all(n == 2 for n in m2['ns'] if n), m2
        assert [c[0] for c in m1['chips'] if c[1]] == ['1'] and all(n == 1 for n in m1['ns'] if n), m1
        assert all(n in (1, 2) for n in ma['ns']) and any(n == 1 for n in ma['ns']) and any(n == 2 for n in ma['ns']), ma
        pg.evaluate("() => { state.team.sdefMode = '2'; state.team.dunit = null; state.team.dchar = null; render(); }")
        print('[㉒ 第5个top 单/双/全部 支援防御档位(搭配驾驶员+1/+2) 通过]')

        # ㉓ 队伍增强系列匹配修复(用户报: 选夜莺+多鲁基斯Ⅲ 时 红色生效、W系列不生效): 系列按 seriesList 全集匹配(含EW版子系列)
        x23 = pg.evaluate("""() => { const B = teamBuffGroups(); const bW = B.find(x => x.target_id === 1219000700);
          const names = ['飞翼高达 (EW版)', '飞翼高达 (EW版) [鸟型型态]', '多鲁基斯F', '多鲁基斯Ⅲ (EX)', '飞翼高达'];
          const out = names.map(n => { const u = q1('SELECT id FROM units WHERE name=?', [n]); return u ? tbuffMatch(bW, metaOf(u.id)) : null; });
          const f = filt('rank');
          const uEW = q1('SELECT id FROM units WHERE name=?', ['飞翼高达 (EW版)']).id;
          const R = tb => buildRanking(f, { targetDef: 10000, targetCharDef: 750, vigor: 'supercharged', crit: false },
            { passive: true, cpassive: true, skills: false, condAll: true, autoVigor: false, multiPhase: false, star: 3,
              spU: true, s3u: true, sspU: true, pSpU: true, teamBuffs: tb ? [tb] : [] });
          const g = R2 => { const r = R2.find(x => x.unitId === uEW); return r ? { dmg: r.dmg, hit: !!r.buffHit, atk: r.buffAtk } : null; };
          return { matches: out, no: g(R(null)), buff: g(R(bW)) }; }""")
        print('[㉓ 队伍增强W系列匹配]', x23)
        assert all(x is True for x in x23['matches']), x23
        assert x23['buff'] and x23['buff']['hit'] and x23['buff']['dmg'] > x23['no']['dmg'], x23
        print('[㉓ 队伍增强 系列set全集匹配(EW版等W系列机体生效) 通过]')

        # ㉔ 目标全能力增加保留(与三项叠加): 一个输入同时作用 攻(反击)/防(正向)/HP(耐久)
        pg.evaluate("""() => { const t = state.team; Object.assign(t, { defup:0, tAtk:0, tDef:0, tHp:0, atkup:0, oDef:0, oHp:0, cbOn:false, buffs:[],
            dunit:1200003950, dchar:1200000103, guard:false, sdef:false, shieldF:false, terr:'' });
          state.stack = []; push({ page:'team', title:'组队' }); }""")
        pg.wait_for_timeout(3200)
        r24a = pg.evaluate("() => (state._recv || {})[1430004850] || null")
        pg.evaluate("() => { state.team.defup = 50; render(); }")
        pg.wait_for_timeout(3200)
        r24b = pg.evaluate("""() => { const t = document.getElementById('dpick').innerText;
          return { recv: (state._recv || {})[1430004850] || null, hpArrow: /耐久\\s*[\\d,]+→/.test(t.replace(/\\n/g, ' ')) }; }""")
        pg.evaluate("() => { const t = state.team; t.defup = 0; t.dunit = 1430004850; t.dchar = 1060000100; render(); }")
        pg.wait_for_timeout(3200)
        f24a = pg.evaluate("() => { const G = state.teamCache.G; const r = G.main.find(x => x.unit.id === 1200003950); return r && r.dmg; }")
        pg.evaluate("() => { state.team.defup = 50; render(); }")
        pg.wait_for_timeout(3200)
        f24b = pg.evaluate("() => { const G = state.teamCache.G; const r = G.main.find(x => x.unit.id === 1200003950); return r && r.dmg; }")
        inp = pg.evaluate("() => ({ has: !!document.getElementById('tdefup'), val: (document.getElementById('tdefup')||{}).value })")
        print('[㉔ 目标全能力增加] 输入:', inp, '| 反击受:', r24a, '→', r24b['recv'], '| 正向:', f24a, '→', f24b, '| HP→:', r24b['hpArrow'])
        assert inp['has'] and inp['val'] == '50', inp
        assert r24a and r24b['recv'] and r24b['recv'] > r24a * 1.2, (r24a, r24b)
        assert f24a and f24b and f24b < f24a, (f24a, f24b)
        assert r24b['hpArrow'], r24b
        pg.evaluate("() => { const t = state.team; t.defup = 0; t.dunit = null; t.dchar = null; render(); }")
        print('[㉔ 目标全能力增加(保留·同时作用攻/防/HP) 通过]')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v105 全部通过 ===')
