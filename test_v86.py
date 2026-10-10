# -*- coding: utf-8 -*-
"""v0.86 验证: 「武器效果收录不完整」修复 — soshage 缺失的武器固有「武装效果」手动收录(3把MAP武器) + 范围增益收录武器侧
背景: soshage 只收每级效果(weapon_traits), 不收武器固有武装効果(weapon_effect 字段文本);
      全库 5160 把中仅 3 把受影响: LACUS CLYNE LIVE / 补给机能 / 精神感应力场TWC(均为目标:己方 MAP)。
① 数据: 3 把武器各 5 个 level 的 fx 行(desc 正确); 其余武器 fx 不受影响(抽样 GN加农=5行)
② 武器页: LACUS CLYNE LIVE 显示「范围内的己方MP增加3」(每级数据效果列) + 使用限制
③ 范围增益: 8 条 = 4驾驶员 + 1机体单位技能(ν双翼状) + 3武器(渣古战士演唱会式样/比格·朗格EX/独角兽TWC)
④ 不收录战舰(行数=8, target 仅 char/unit)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8986

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

        # ① 数据层
        r = pg.evaluate("""() => {
          const one = w => q('SELECT level, sort, name, desc FROM weapon_fx WHERE weapon_id=? ORDER BY level', [w]);
          return {
            lacus: one(133000590003), twc: one(113900010004), supply: one(100900055006),
            gn: q('SELECT COUNT(*) c FROM weapon_fx WHERE weapon_id=137600080003')[0].c,
            gn2: q1('SELECT COUNT(*) c FROM weapons WHERE id=137600080003')
          };
        }""")
        for k in ('lacus', 'twc', 'supply'):
            assert len(r[k]) == 5 and all(x['name'] == '' for x in r[k]), (k, r[k])
        assert all(x['desc'] == '范围内的己方MP增加3' for x in r['lacus'] + r['twc']), r
        assert all('HP16%' in x['desc'] for x in r['supply']), r
        assert r['gn'] == 5, r['gn']
        print('[① 数据] LACUS/TWC=MP增加3(5级) 补给=HP16%(5级); GN加农fx不受影响(5行)')
        print('[① 缺失武器固有武装效果收录(3把) 通过]')

        # ② 武器页显示
        pg.evaluate("() => { state.stack = []; push({ page: 'weapon', title: 'x', id: 133000590003 }); }")
        pg.wait_for_timeout(1200)
        t = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '范围内的己方MP增加3' in t and '使用限制' in t and '仅限于移动前使用' in t, t[:400]
        pg.evaluate("() => { state.stack = []; push({ page: 'weapon', title: 'x', id: 100900055006 }); }")
        pg.wait_for_timeout(1200)
        t2 = pg.evaluate("() => document.querySelector('#view').textContent.replace(/\\s+/g,' ')")
        assert '范围内的己方恢复HP16%' in t2, t2[:300]
        print('[② 武器页显示武装效果(LACUS/补给机能)] 通过')

        # ③ 范围增益 8 条
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
          const wu = new Set(q("SELECT DISTINCT w.unit_id uid FROM weapon_fx f JOIN weapons w ON w.id=f.weapon_id WHERE f.desc LIKE '%范围内的%'").map(x => x.uid));
          return { chars: [...chars], units: [...units].filter(u => !wu.has(u)), weaponUnits: [...wu] };
        }""")
        print('[③ 期望] 驾驶员', len(exp['chars']), '机体(单位技能)', exp['units'], '武器机体', exp['weaponUnits'])
        assert len(exp['chars']) == 4 and exp['units'] == [1114000450] and sorted(exp['weaponUnits']) == [1009000550, 1139000100, 1330005900], exp

        pg.evaluate("() => { state.stack = []; setTab('feat'); }")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelector('[data-k=\"range_buff\"]').click()")
        pg.wait_for_timeout(2500)
        rows = pg.evaluate("""() => [...document.querySelectorAll('#farea .lrow')].map(e => ({ t: e.dataset.t, id: +e.dataset.id, txt: e.textContent.replace(/\\s+/g, ' ') }))""")
        print(f"[③ 行数] {len(rows)}")
        for x in rows: print('   ', x['t'], x['id'], '|', x['txt'][:96])
        assert len(rows) == 8, len(rows)
        by_id = {x['id']: x['txt'] for x in rows}
        assert '范围内的己方MP增加3' in by_id.get(1330005900, '') and 'LACUS' in by_id.get(1330005900, ''), by_id.get(1330005900)
        assert 'HP16%' in by_id.get(1009000550, '') and '补给机能' in by_id.get(1009000550, ''), by_id.get(1009000550)
        assert '范围内的己方MP增加3' in by_id.get(1139000100, '') and 'TWC' in by_id.get(1139000100, ''), by_id.get(1139000100)
        assert '防护罩' in by_id.get(1114000450, ''), by_id.get(1114000450)
        assert 'MP提升5' in by_id.get(1300003203, ''), by_id.get(1300003203)
        print('[③ 范围增益=8条(4驾驶员+1单位技能+3武器) 通过]')

        # ④ 不收录战舰
        assert all(x['t'] in ('char', 'unit') for x in rows), rows
        print('[④ 不收录战舰(target 仅 char/unit)] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v86 全部通过 ===')
