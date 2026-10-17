# -*- coding: utf-8 -*-
"""v113 验证: soshage zh-HK 全量刷新(2026-10-17) — 新增机体/机师/武器/支援(战舰)入库, 既有数值 0 变更
① 新增条目: 再生高达(EX) 1370011150 / 利保逊·阿路玛古 1370003501 / 卡蒂&乌拉级 1370000750; 武器 5235(≥70新)
② 再生高达(EX): 5 武器(4200/3900/4500/5500/3800), 3 能力; ★3面板 = max×1.4 与 GameWith 一致(HP101073/ATK10651/DEF9002/EN441)
③ 全库被動描述占位符残留仅 1 条(已知 NT-D 字面「标签」, 无新增残留)
④ 应用冒烟: 计算页选中再生高达(EX) 渲染武器行, 无 pageerror
⑤ 武器使用地点/消耗: weapon_area 156 / weapon_hpcost 11 (新武器无不可用场地/HP·MP消耗)
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9021
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        r1 = pg.evaluate("""() => ({
          u: q1("SELECT id,name,rarity,role,max_hp,max_atk,max_def,max_en FROM units WHERE id=1370011150"),
          c: q1("SELECT id,name,rarity FROM characters WHERE id=1370003501"),
          s: q1("SELECT id,name FROM supporters WHERE id=1370000750"),
          nw: q1("SELECT count(*) n FROM weapons").n })""")
        print('[① 新增条目]', r1)
        assert r1['u'] and r1['u']['name'] == '再生高达 (EX)' and r1['u']['role'] == 3, r1
        assert r1['c'] and '利保逊' in r1['c']['name'], r1
        assert r1['s'] and '乌拉级' in r1['s']['name'], r1
        assert r1['nw'] >= 5235, r1
        print('[① 新机体/机师/支援(战舰)/武器 已入库 通过]')

        r2 = pg.evaluate("""() => {
          const ws = q("SELECT id,name,power,range_min,range_max FROM weapons WHERE unit_id=1370011150 ORDER BY power DESC");
          const ab = q("SELECT name FROM unit_abilities WHERE unit_id=1370011150");
          const u = q1("SELECT max_hp,max_atk,max_def,max_en FROM units WHERE id=1370011150");
          return { ws, ab: ab.map(x => x.name), panel: { hp: Math.floor(u.max_hp * 1.4), atk: Math.floor(u.max_atk * 1.4), def: Math.floor(u.max_def * 1.4), en: Math.floor(u.max_en * 1.4) } }; }""")
        print('[② 再生高达] 武器:', r2['ws'], '| 能力:', r2['ab'], '| ★3面板:', r2['panel'])
        assert len(r2['ws']) == 5 and [w['power'] for w in r2['ws']] == [5500, 4500, 4200, 3900, 3800], r2['ws']
        assert r2['panel'] == {'hp': 101073, 'atk': 10651, 'def': 9002, 'en': 441}, r2['panel']
        print('[② 武器/能力/★3面板与 GameWith 一致 通过]')

        r3 = pg.evaluate("""() => { const bad = [];
          for (const [tbl, idc] of [['unit_abilities','unit_id'], ['char_abilities','char_id']])
            for (const r of q(`SELECT ${idc} uid, traits_json tj FROM ${tbl}`))
              for (const x of JSON.parse(r.tj || '[]')) {
                const d = ((x || {}).trait || {}).desc || '';
                if (/「系列」|「标签」|【条件|【條件|上述|「类型」|「類型」/.test(d)) bad.push([tbl, r.uid, d.slice(0, 60)]);
              }
          return bad; }""")
        print('[③ 占位符残留]', r3)
        assert len(r3) == 1 and 'NT-D' in r3[0][2], r3
        print('[③ 无新增占位符残留(仅已知NT-D字面) 通过]')

        # ④ 计算页冒烟
        pg.evaluate("""() => { const c = state.calc; c.unitId = 1370011150; c.charId = null; c.vigor = 'supercharged'; c.crit = false;
          state.stack = []; push({ page: 'calc', title: '计算' }); render(); }""")
        pg.wait_for_timeout(1500)
        r4 = pg.evaluate("""() => ({ rows: document.querySelectorAll('#view table.ctable tr[data-wid]').length,
          txt: (document.getElementById('view').innerText || '').includes('TRANS-AM') })""")
        print('[④ 计算页冒烟]', r4)
        assert r4['rows'] >= 5 and r4['txt'], r4

        r5 = pg.evaluate("""() => ({ area: q1("SELECT count(*) n FROM weapon_area").n, hp: q1("SELECT count(*) n FROM weapon_hpcost").n })""")
        print('[⑤ 使用限制表]', r5)
        assert r5['area'] >= 156 and r5['hp'] >= 11, r5

        assert not errors, errors
        print('=== test_v113 全部通过 ===')
        b.close()
finally:
    srv.terminate()
