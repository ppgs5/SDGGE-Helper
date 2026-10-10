# -*- coding: utf-8 -*-
"""v0.51 验证: ①驾驶员SP开关(计算/排行/组队/图鉴/特性) 非UR数值随开关变化 ②SR及以下SP后技能/能力变化(详情页)
③支援防御+2列表右侧显示驾驶员防御值 ④特性-有MP技能列表+主被动mp/单被动mp/主动mp筛选"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8996
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

        # ---------- ①a 排行: 驾驶员SP开关改变全表非UR驾驶员数值(引擎级) ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('.rrow', timeout=180000); pg.wait_for_timeout(800)
        chip0 = pg.evaluate("() => document.querySelector('#rpspu').textContent.replace(/\\s+/g,'')")
        assert '驾驶员SP开' in chip0, f'排行应有驾驶员SP开关(默认开): {chip0}'
        _vals = """() => (state.rankCache.rows || []).filter(r => (q1('SELECT rarity FROM characters WHERE id=?', [r.pilot.id]) || {}).rarity <= 4)
          .slice(0, 40).map(r => r.unitId + ':' + r.pilot.v).join(',')"""
        pick = pg.evaluate(_vals)
        print('[排行 全表非UR样本]', pick[:70])
        assert pick.count(',') > 3, '全表应有非UR驾驶员条目'
        pg.click('#rpspu')
        pg.wait_for_function(f"(old) => (({_vals})()) !== old && state.rankCfg.pSpU === false", arg=pick, timeout=300000)
        offv = pg.evaluate(_vals)
        print('[排行 SP关]', offv[:70])
        assert offv != pick, '关SP后非UR驾驶员数值应变化'
        pg.click('#rpspu')
        pg.wait_for_function(f"(old) => (({_vals})()) === old", arg=pick, timeout=300000)
        print('[排行 恢复SP开] ok  (注: 前100行全为UR驾驶员, 不受SP影响属正常)')

        # ---------- ①b 计算页: SR驾驶员数值随SP变化 ----------
        pg.evaluate("() => { state.calc.unitId = 1001000150; state.calc.charId = 1001000101; setTab('calc'); }")
        pg.wait_for_timeout(6000)
        t0 = pg.evaluate("() => (document.querySelector('#view') || {}).innerText || ''")
        c0 = pg.evaluate("() => document.querySelector('#cpspu').textContent.replace(/\\s+/g,'')")
        print('[计算 默认]', c0, '| 页面长度', len(t0))
        assert '驾驶员SP开' in c0 and len(t0) > 500, '计算页应有驾驶员SP开关'
        pg.click('#cpspu'); pg.wait_for_timeout(6000)
        t1 = pg.evaluate("() => (document.querySelector('#view') || {}).innerText || ''")
        c1 = pg.evaluate("() => document.querySelector('#cpspu').textContent.replace(/\\s+/g,'')")
        print('[计算 SP关]', c1, '| 变化', t0 != t1)
        assert '驾驶员SP关' in c1 and t0 != t1, '关SP后计算页(驾驶员数值/伤害)应变化'
        pg.click('#cpspu'); pg.wait_for_timeout(6000)
        c2 = pg.evaluate("() => document.querySelector('#cpspu').textContent.replace(/\\s+/g,'')")
        assert '驾驶员SP开' in c2, '恢复开SP'

        # ---------- ①c 组队: 防御目标守备值随SP变化 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_timeout(3000)
        pg.evaluate("() => { state.team.dunit = 1001000150; state.team.dchar = 1001000101; pageTeam(document.querySelector('#view')); }")
        pg.wait_for_timeout(5000)
        dc0 = pg.evaluate("() => (document.querySelector('#dpick').textContent.match(/守备[\\s\\S]{0,24}/) || [''])[0]")
        tc0 = pg.evaluate("() => document.querySelector('#tpspu').textContent.replace(/\\s+/g,'')")
        print('[组队 默认]', tc0, '|', dc0)
        assert '驾驶员SP开' in tc0 and '守备' in dc0, '组队应有驾驶员SP开关与守备值'
        pg.click('#tpspu'); pg.wait_for_timeout(5000)
        dc1 = pg.evaluate("() => (document.querySelector('#dpick').textContent.match(/守备[\\s\\S]{0,24}/) || [''])[0]")
        print('[组队 SP关]', dc1)
        assert dc1 != dc0, f'关SP后守备值应变化: {dc0} → {dc1}'
        pg.click('#tpspu'); pg.wait_for_timeout(4000)

        # ---------- ② 图鉴-驾驶员: SP开关 + SR技能/能力随SP变化 ----------
        pg.click('[data-tab="units"]'); pg.wait_for_timeout(400)
        pg.click('[data-k="char"]'); pg.wait_for_timeout(1000)
        assert pg.evaluate("() => !!document.querySelector('#cspu')"), '图鉴-驾驶员应有SP开关'
        _rows_txt = "() => [...document.querySelectorAll('#listarea .lrow small')].slice(0, 30).map(e => e.textContent).join('|')"
        row_txt = pg.evaluate(_rows_txt)
        pg.click('#cspu'); pg.wait_for_timeout(800)
        row_txt2 = pg.evaluate(_rows_txt)
        print('[图鉴 列表值变化]', row_txt != row_txt2)
        assert row_txt != row_txt2, '开SP后驾驶员列表数值应变化(非UR)'
        pg.click('#cspu'); pg.wait_for_timeout(600)
        # 详情页
        pg.evaluate("() => push({page:'char', title:'x', id:1001000101})"); pg.wait_for_timeout(1200)
        c_off = pg.evaluate("() => [...document.querySelectorAll('#view .card .kv')].map(el => el.textContent).join('\\n')")
        print(f"[详情 SR阿姆罗 SP关] 摇摆闪避={'摇摆闪避' in c_off} LV2={'支援攻击／支援反击 LV2' in c_off}")
        assert '摇摆闪避' not in c_off and '支援攻击／支援反击 LV2' in c_off, 'SP关时不应有摇摆闪避, 能力为LV2'
        pg.click('#cspu2'); pg.wait_for_timeout(1000)
        c_on = pg.evaluate("""() => ({ names: [...document.querySelectorAll('#view .card .kv')].map(el => el.textContent).join('\\n'),
          stat: document.querySelector('#view .statgrid') ? document.querySelector('#view .statgrid').textContent : '' })""")
        print(f"[详情 SR阿姆罗 SP开] 摇摆闪避={'摇摆闪避' in c_on['names']} LV3={'支援攻击／支援反击 LV3' in c_on['names']} 原标注={'原' in c_on['stat']}")
        assert '摇摆闪避' in c_on['names'] and '支援攻击／支援反击 LV3' in c_on['names'], 'SP开时应出现SP新技能与LV3能力'
        assert '原' in c_on['stat'], 'SP开时数值应标注"原"基础值'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/57a_char_sp.png')
        pg.click('#cspu2'); pg.wait_for_timeout(600)

        # ---------- ③ 特性-支援防御+2 右侧防御值 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow'); pg.wait_for_timeout(600)
        pg.click("[data-k='support_def']"); pg.wait_for_timeout(1200)
        dchk = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#farea .lrow')].slice(0, 6);
          return rows.map(el => { const t = el.querySelector('div[style*="text-align"]');
            const def = t ? (t.textContent.match(/防御 ([\\d,]+)/) || [])[1] : null;
            const id = +el.dataset.id; const c = q1('SELECT rarity, max_defense, sp_max_defense FROM characters WHERE id=?', [id]);
            const exp = ((c.rarity||0) <= 4 && c.sp_max_defense != null) ? c.sp_max_defense : c.max_defense;
            return {id, def, exp}; });
        }""")
        print('[支援防御+2 右侧防御值]', dchk[:4])
        assert dchk and all(x['def'] for x in dchk), f'每行应显示防御值: {dchk}'
        assert all(int(x['def'].replace(',', '')) == x['exp'] for x in dchk), f'防御值应为SP口径(非UR用sp_max): {dchk}'

        # ---------- ④ 特性-有MP技能 ----------
        pg.click("[data-k='mp_skill']"); pg.wait_for_timeout(1500)
        mp = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#farea .lrow')];
          return {n: rows.length, chips: [...document.querySelectorAll('#farea [data-mpf]')].map(el => el.textContent.trim()),
                  first: rows.length ? rows[0].textContent.replace(/\\s+/g,' ').slice(0, 70) : ''};
        }""")
        print('[有MP技能] 共', mp['n'], mp['chips'], '|', mp['first'])
        assert mp['n'] > 0 and mp['chips'] == ['全部', '主被动mp', '单被动mp', '主动mp'], mp
        cls = pg.evaluate("""() => {
          const out = {};
          for (const f of ['both', 'passive', 'active']) {
            document.querySelector(`[data-mpf="${f}"]`).click();
            out[f] = [...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id);
          }
          document.querySelector('[data-mpf=""]').click();
          out.all = [...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id);
          return out;
        }""")
        print('[筛选计数] all=%d both=%d passive=%d active=%d' % (len(cls['all']), len(cls['both']), len(cls['passive']), len(cls['active'])))
        assert len(cls['both']) > 0 and len(cls['passive']) > 0 and len(cls['active']) > 0, '三类应均有结果'
        assert set(cls['both']) | set(cls['passive']) | set(cls['active']) == set(cls['all']), '三类应构成全部的无重叠划分'
        assert not (set(cls['both']) & set(cls['passive'])) and not (set(cls['both']) & set(cls['active'])), '分类应互斥'
        # 行文本交叉
        pg.evaluate("() => document.querySelector('[data-mpf=\"both\"]').click()"); pg.wait_for_timeout(800)
        assert pg.evaluate("() => [...document.querySelectorAll('#farea .lrow')].every(el => /被动MP\\+/.test(el.textContent) && /主动MP\\+/.test(el.textContent))"), '主被动mp每行应同时含被动与主动'
        pg.evaluate("() => document.querySelector('[data-mpf=\"passive\"]').click()"); pg.wait_for_timeout(800)
        assert pg.evaluate("() => [...document.querySelectorAll('#farea .lrow')].every(el => /被动MP\\+/.test(el.textContent) && !/主动MP\\+/.test(el.textContent))"), '单被动mp每行应仅含被动'
        pg.evaluate("() => document.querySelector('[data-mpf=\"active\"]').click()"); pg.wait_for_timeout(800)
        assert pg.evaluate("() => [...document.querySelectorAll('#farea .lrow')].every(el => !/被动MP\\+/.test(el.textContent) && /主动MP\\+/.test(el.textContent))"), '主动mp每行应仅含主动'
        # SQL 交叉: 被动类驾驶员在 abilities(含sp) 应有 trait46/43
        sqlchk = pg.evaluate("""(ids) => {
          const scan = (tbl) => { const m = {};
            for (const r of q(`SELECT char_id, traits_json FROM ${tbl}`)) {
              let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) {}
              for (const t of ts) { const tr = (t||{}).trait||{};
                if ((tr.trait_type===46 || tr.trait_type===43) && tr.trait_value>0) m[r.char_id] = 1; } }
            return m; };
          const psv = Object.assign({}, scan('char_abilities'), scan('char_abilities_sp'));
          const bad = ids.filter(id => !psv[id]);
          return bad.slice(0, 5);
        }""", cls['passive'])
        print('[单被动mp SQL交叉] 异常', sqlchk)
        assert sqlchk == [], f'单被动类应以被动MP为主(数据交叉): {sqlchk}'
        pg.evaluate("() => document.querySelector('[data-mpf=\"\"]').click()"); pg.wait_for_timeout(600)
        # ⑤ 生效条件明细(标签/系列/敌方/机体 条件应具体列出, 而非泛泛的"含条件生效")
        any_cond = pg.evaluate("() => [...document.querySelectorAll('#farea .lrow small')].some(e => /搭乘含「/.test(e.textContent) || /敌方部队含「/.test(e.textContent))")
        assert any_cond, '条件型MP应列出生效条件'
        conds = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#farea .lrow')];
          const find = id => { const el = rows.find(e => +e.dataset.id === id); return el ? el.textContent.replace(/\\s+/g, ' ') : ''; };
          return {mihail: find(1017000400), musha: find(1370004501)};
        }""")
        print('[条件明细] 米海尔:', conds['mihail'][:90])
        print('[条件明细] 武士道:', conds['musha'][:90])
        assert '自护公国军' in conds['mihail'], f'米海尔应显示搭乘标签条件: {conds["mihail"]}'
        if conds['musha']:
            assert '敌方部队含「高达」' in conds['musha'], f'Mr.武士道应显示敌方条件: {conds["musha"]}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/57b_mp_skill.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
