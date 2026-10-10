# -*- coding: utf-8 -*-
"""v0.85 验证: 特性页新增「范围增益」分类 — 收录所有对己方范围增强的机体和驾驶员(不收录战舰)
驾驶员 = char_skills(_sp) desc 含「范围内的」(HP修复/威力抵御/MP提升/攻击爆裂 四类)
机体   = features 单位技能 desc 含「范围内的」或「己方」(ν高达(双翼状感应砲装备型)(EX) 防护罩)
① 特性 chips 含「范围增益」; 点击后 subnote = N条 · 范围增益
② 行集合 = 数据库中同口径扫描结果(4驾驶员+1机体), 每行简述增强效果(desc)
③ 不收录战舰: 行 target 仅 char/unit, 且不含 supporters 的「范围内的我方单位」条
④ 点击行可跳转(驾驶员→角色页 / 机体→机体页)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8985

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

        # 期望集合(与实现同口径直查 DB)
        exp = pg.evaluate("""() => {
          const chars = new Set();
          for (const t of ['char_skills', 'char_skills_sp'])
            for (const r of q(`SELECT char_id, desc FROM ${t}`))
              if ((r.desc || '').indexOf('范围内的') >= 0) chars.add(r.char_id);
          const units = new Set();
          for (const f of q("SELECT target_id, params_json FROM features WHERE feature='unit_skill'")) {
            let d = ''; try { d = JSON.parse(f.params_json || '{}').desc || ''; } catch (e) {}
            if (d.indexOf('范围内的') >= 0 || d.indexOf('己方') >= 0) units.add(f.target_id);
          }
          return { chars: [...chars], units: [...units] };
        }""")
        print('[期望] 驾驶员', exp['chars'], '| 机体', exp['units'])
        assert len(exp['chars']) == 4 and exp['units'] == [1114000450], exp

        pg.evaluate("() => { state.stack = []; setTab('feat'); }")
        pg.wait_for_timeout(2500)
        assert pg.evaluate("() => !!document.querySelector('[data-k=\"range_buff\"]')")
        pg.evaluate("() => document.querySelector('[data-k=\"range_buff\"]').click()")
        pg.wait_for_timeout(2500)

        # ① subnote
        sub = pg.evaluate("() => (document.querySelector('#farea .subnote') || {}).textContent || ''")
        print('[① subnote]', sub.replace('\\s+', ' ')[:60] if isinstance(sub, str) else sub)
        assert '范围增益' in sub, sub

        # ② 行集合与简述
        rows = pg.evaluate("""() => [...document.querySelectorAll('#farea .lrow')].map(e => ({ t: e.dataset.t, id: +e.dataset.id, txt: e.textContent.replace(/\\s+/g, ' ') }))""")
        print(f"[② 行数] {len(rows)}")
        for x in rows: print('   ', x['t'], x['id'], '|', x['txt'][:100])
        got_chars = sorted(x['id'] for x in rows if x['t'] == 'char')
        got_units = sorted(x['id'] for x in rows if x['t'] == 'unit')
        assert got_chars == sorted(exp['chars']) and got_units == exp['units'], (got_chars, got_units)
        txt_map = {x['id']: x['txt'] for x in rows}
        assert 'MP提升5' in txt_map[1300003203] and '恢复HP20%' in txt_map[1219000600], txt_map
        assert '损伤减轻12%' in txt_map[1230000200] and '损伤提升12%' in txt_map[1501000200], txt_map
        assert '防护罩' in txt_map[1114000450], txt_map
        assert '使用限制' not in txt_map[1114000450]  # 简述是效果不是枪械说明
        print('[② 五条(4驾驶员+1机体)与增强效果简述] 通过')

        # ③ 不收录战舰
        assert all(x['t'] in ('char', 'unit') for x in rows), rows
        assert len(rows) == 5, len(rows)          # 90 艘战舰支援技能未混入
        print('[③ 不收录战舰(行数=5, target 仅 char/unit)] 通过')

        # ④ 跳转
        pg.evaluate("() => { const el = [...document.querySelectorAll('#farea .lrow')].find(e => +e.dataset.id === 1300003203); el.click(); }")
        pg.wait_for_timeout(1200)
        t = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '拉克丝' in t, t[:200]
        pg.evaluate("() => { pop(); }")
        pg.wait_for_timeout(1500)
        pg.evaluate("() => { const el = [...document.querySelectorAll('#farea .lrow')].find(e => +e.dataset.id === 1114000450); el.click(); }")
        pg.wait_for_timeout(1500)
        t = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '双翼状' in t, t[:200]
        print('[④ 行跳转(驾驶员/机体)] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v85 全部通过 ===')
