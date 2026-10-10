# -*- coding: utf-8 -*-
"""v103 验证: 「首动」按钮(计算/组队/排行) — 按官方AI优先度只算首动那1个技能的伤害
① 计算页 刹那UR①(1370000100: MP提升+高速+攻击爆裂) → 开: 首动MP技→超一击(+30%), chip显示「首动:MP提升」
② 加岛勇(1022000100: 威力抵御+攻击爆裂) → 开: 首动减伤 → 伤害与关相同(不吃爆裂%)
③ 乔纳·巴修塔(1144000102: 命中率·闪避率提升+攻击爆裂) → 开: 爆裂加成; 再开「反死风险」→ 命中闪避挤掉爆裂 → 伤害回到无加成
④ 排行页 rfirst / 组队页 tfirst chip 存在可点, 开后可算出结果(标题含「首动」)
⑤ 更新中心「APP 更新说明」卡含 v0.103 与「首动」
"""
import os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 9010
UNIT = 1001000150          # 高达(EX)
P_MP, P_GUARD, P_EVA = 1370000100, 1022000100, 1144000102

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []

def cell_dmg(pg):
    r = pg.evaluate("""() => { const tr = document.querySelector('#view table.ctable tr[data-wid]');
      return tr && tr.cells.length > 1 ? tr.cells[1].innerText : null; }""")
    return int(re.sub(r'[^0-9]', '', r)) if r else None

try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(120000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        def calc_setup(cid, first=False, fdth=False):
            pg.evaluate("""([cid]) => { const c = state.calc;
              c.unitId = %d; c.charId = cid; c.skills = false; c.first = false; c.fdth = false; c.mp = false;
              state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""" % UNIT, [cid])
            pg.wait_for_timeout(700)
            if first:
                pg.evaluate("() => document.getElementById('cfirst').click()")   # 走真实交互(含自动关多段增益)
                pg.wait_for_timeout(500)
            if fdth:
                pg.evaluate("() => document.getElementById('cfdth').click()")
                pg.wait_for_timeout(500)

        # ① 刹那UR①: 首动MP技 → 超一击+30%
        calc_setup(P_MP)
        d0 = cell_dmg(pg)
        chip0 = pg.evaluate("() => document.getElementById('cfirst').textContent")
        assert chip0.strip() == '首动 关', chip0   # 关态不带「首动:xxx」标注
        calc_setup(P_MP, first=True)
        d1 = cell_dmg(pg)
        chip = pg.evaluate("() => document.getElementById('cfirst').textContent")
        print('[① 刹那 首动MP] off:', d0, '→ on:', d1, '| chip:', chip[:34])
        assert '首动:MP提升' in chip and '超一击' in chip, chip
        assert d1 and d0 and 1.15 < d1 / d0 < 1.45, (d0, d1)
        assert pg.evaluate("() => !!document.getElementById('cfdth')"), '首动开时应显示反死风险开关'
        print('[① 首动MP技→超一击(+30%) 且 反死开关出现 通过]')

        # ①b 主动技能 ⇄ 首动 二选一 + 首动下多段增益锁定
        st = pg.evaluate("() => ({ skills: state.calc.skills, first: state.calc.first, mp: state.calc.mp })")
        assert st['skills'] is False and st['first'] is True and st['mp'] is False, st
        pg.evaluate("() => document.getElementById('mp').click()")   # 锁定: 点了也不开
        pg.wait_for_timeout(300)
        assert pg.evaluate("() => state.calc.mp") is False
        pg.evaluate("() => document.getElementById('skills').click()")
        pg.wait_for_timeout(500)
        st = pg.evaluate("() => ({ skills: state.calc.skills, first: state.calc.first })")
        assert st['skills'] is True and st['first'] is False, st
        pg.evaluate("() => document.getElementById('mp').click()")   # 解除后可开
        pg.wait_for_timeout(300)
        assert pg.evaluate("() => state.calc.mp") is True
        print('[①b 主动技能⇄首动互斥 + 首动下多段增益锁定(解除后可开) 通过]')

        # ② 加岛勇: 首动=减伤 → 伤害与关相同
        calc_setup(P_GUARD)
        g0 = cell_dmg(pg)
        calc_setup(P_GUARD, first=True)
        g1 = cell_dmg(pg)
        chipg = pg.evaluate("() => document.getElementById('cfirst').textContent")
        print('[② 加岛勇 首动减伤] off:', g0, '→ on:', g1, '| chip:', chipg[:34])
        assert '首动:威力抵御' in chipg, chipg
        assert g0 == g1, (g0, g1)
        print('[② 首动减伤不改变伤害(不吃爆裂) 通过]')

        # ③ 乔纳: 爆裂加成 vs 反死风险挤掉爆裂
        calc_setup(P_EVA)
        e0 = cell_dmg(pg)
        calc_setup(P_EVA, first=True)
        e1 = cell_dmg(pg)
        chip3 = pg.evaluate("() => document.getElementById('cfirst').textContent")
        calc_setup(P_EVA, first=True, fdth=True)
        e2 = cell_dmg(pg)
        print('[③ 乔纳] base:', e0, '| 爆裂:', e1, '| 反死挤掉爆裂:', e2, '| chip:', chip3[:26])
        assert '首动:攻击爆裂' in chip3, chip3
        assert e1 > e0, (e0, e1)
        assert e2 == e0, (e0, e2)
        print('[③ 爆裂+损伤% / 反死风险→命中闪避挤掉爆裂 通过]')

        # ④ 排行页
        pg.evaluate("""() => { state.rankCfg.rarity = 5; state.rankCfg.urole = 1; state.rankCfg.first = false;
          state.stack = []; push({ page: 'rank', title: '排行' }); }""")
        pg.wait_for_timeout(1200)
        assert pg.evaluate("() => !!document.getElementById('rfirst')"), '排行页缺首动chip'
        pg.evaluate("() => document.getElementById('rfirst').click()")
        pg.wait_for_timeout(1500)
        rr = pg.evaluate("""() => ({ chip: document.getElementById('rfirst').textContent,
          has: !!document.getElementById('rfdth'), hit: (document.getElementById('rhit')||{}).textContent || '',
          skills: state.rankCfg.skills, mp: state.rankCfg.mp, rsk: document.getElementById('rsk').textContent })""")
        print('[④ 排行]', rr)
        assert '开' in rr['chip'] and rr['has'] and '共' in rr['hit'], rr
        assert rr['skills'] is False and rr['mp'] is False and '由首动' in rr['rsk'], rr
        pg.evaluate("() => document.getElementById('rmp').click()")   # 首动下多段增益锁定
        pg.wait_for_timeout(800)
        assert pg.evaluate("() => state.rankCfg.mp") is False
        pg.evaluate("() => document.getElementById('rsk').click()")   # 主动技能 ⇄ 首动 互斥
        pg.wait_for_timeout(1500)
        ex = pg.evaluate("() => ({ first: state.rankCfg.first, skills: state.rankCfg.skills })")
        assert ex['first'] is False and ex['skills'] is True, ex
        pg.evaluate("() => document.getElementById('rmp').click()")   # 解除后可开
        pg.wait_for_timeout(1500)
        assert pg.evaluate("() => state.rankCfg.mp") is True
        pg.evaluate("() => { state.rankCfg.first = false; state.rankCfg.mp = false; }")
        print('[④ 排行页首动chip(可开/反死开关出现/有结果/关多段增益/⇄主动技能互斥) 通过]')

        # ⑤ 组队页
        pg.evaluate("() => { state.stack = []; push({ page: 'team', title: '组队' }); }")
        pg.wait_for_timeout(1500)
        assert pg.evaluate("() => !!document.getElementById('tfirst')"), '组队页缺首动chip'
        # 默认: 第一击(m1)选中 + 多段增益默认关; 第一击下多段增益锁定
        d0 = pg.evaluate("() => ({ skills: state.team.skills, mp: state.team.mp, tmp: document.getElementById('tmp').textContent })")
        assert d0['skills'] is False and d0['mp'] is False and '关' in d0['tmp'], d0
        pg.evaluate("() => document.getElementById('tmp').click()")
        pg.wait_for_timeout(800)
        assert pg.evaluate("() => state.team.mp") is False, '第一击下多段增益应锁定'
        # 全技能下可开
        pg.evaluate("() => document.getElementById('m2').click()")
        pg.wait_for_timeout(1500)
        pg.evaluate("() => document.getElementById('tmp').click()")
        pg.wait_for_timeout(1500)
        assert pg.evaluate("() => state.team.mp") is True, '全技能下应可开多段增益'
        # 切回第一击 → 自动关+锁定
        pg.evaluate("() => document.getElementById('m1').click()")
        pg.wait_for_timeout(1500)
        assert pg.evaluate("() => state.team.mp") is False
        # 首动
        pg.evaluate("() => document.getElementById('tfirst').click()")
        pg.wait_for_timeout(2500)
        ttxt = pg.evaluate("() => document.body.innerText")
        assert '首动' in ttxt and '（首动' in ttxt, ttxt[:0]
        assert pg.evaluate("() => !!document.getElementById('tfdth')")
        st5 = pg.evaluate("() => ({ skills: state.team.skills, first: state.team.first, mp: state.team.mp })")
        assert st5['first'] is True and st5['skills'] is False and st5['mp'] is False, st5
        pg.evaluate("() => document.getElementById('tmp').click()")   # 首动下多段增益锁定
        pg.wait_for_timeout(800)
        assert pg.evaluate("() => state.team.mp") is False
        pg.evaluate("() => document.getElementById('m2').click()")   # 全技能 ⇄ 首动 互斥
        pg.wait_for_timeout(2500)
        st5b = pg.evaluate("() => ({ first: state.team.first, skills: state.team.skills })")
        assert st5b['first'] is False and st5b['skills'] is True, st5b
        pg.evaluate("() => { state.team.first = false; state.team.fdth = false; state.team.mp = false; state.team.skills = false; }")
        print('[⑤ 组队页: 默认第一击+多段增益关(锁定) / 全技能可开 / 首动关多段增益+锁定 / ⇄互斥 通过]')

        # ⑥ 更新中心: APP更新说明
        pg.evaluate("() => { state.stack = []; push({ page: 'update', title: '更新中心' }); }")
        pg.wait_for_timeout(1500)
        utxt = pg.evaluate("() => document.body.innerText")
        assert 'APP 更新说明' in utxt and '0.103' in utxt and '首动' in utxt
        print('[⑥ 更新中心 APP更新说明(v0.103·首动) 通过]')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v103 全部通过 ===')
