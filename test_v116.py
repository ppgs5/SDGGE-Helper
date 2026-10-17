# -*- coding: utf-8 -*-
"""v116 验证: 系列字典修复(数据刷新后 series 表丢31个系列 → 按系列条件的机师/机体被动失效)
① series 表含 1100/2100/3300; 机体引用系列缺失=0; 条件引用系列缺失=0
② metaOf(W系列机体 双头龙EX).seriesList 含「新机动战记高达W」
③ 迪奥EW(W条件被动: 增伤15%/反击时攻击+20%) × 双头龙EX → dmg15/atk20 生效; × 非W机体(高达) → dmg0/atk0 不生效
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9024
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

        r1 = pg.evaluate("""() => {
          const ids = new Set(q("SELECT id FROM series").map(r => String(r.id)));
          const missU = new Set();
          for (const u of q("SELECT series_id, series_set_json FROM units")) {
            for (const i of String(u.series_set_json || '').replace(/[\\[\\]" ]/g, '').split(',')) if (i) missU.add(i);
            if (u.series_id) missU.add(String(u.series_id));
          }
          const missC = new Set();
          for (const t of ['char_abilities', 'char_abilities_sp', 'unit_abilities'])
            for (const r of q(`SELECT traits_json FROM ${t}`))
              for (const x of JSON.parse(r.traits_json || '[]')) {
                const ac = ((x || {}).trait || {}).active_condition || {};
                for (const i of String(ac.unit_series || '').split(',')) if (i.trim()) missC.add(i.trim());
              }
          return { n: ids.size, has1100: ids.has('1100'), has2100: ids.has('2100'), has3300: ids.has('3300'),
            missU: [...missU].filter(i => !ids.has(i)).length, missC: [...missC].filter(i => !ids.has(i)).length }; }""")
        print('[① series字典]', r1)
        assert r1['has1100'] and r1['has2100'] and r1['has3300'] and r1['missU'] == 0 and r1['missC'] == 0, r1
        print('[① 1100/2100/3300 齐全 · 引用缺失=0 通过]')

        r2 = pg.evaluate("""() => {
          const mW = metaOf(1219000650), mG = metaOf(1001000150);
          const opt = { passive: true, cpassive: true, skills: false, condAll: true, unitId: 1219000650 };
          return { seriesW: mW.seriesList.has('新机动战记高达W'),
            bW: charBonus(1219000201, 'mid', opt, mW),
            bG: charBonus(1219000201, 'mid', Object.assign({}, opt, { unitId: 1001000150 }), mG) }; }""")
        print('[②③ 迪奥EW系列被动]', r2)
        assert r2['seriesW'] is True, r2
        assert r2['bW']['dmg'] == 15 and r2['bW']['atk'] == 20, r2
        assert r2['bG']['dmg'] == 0 and r2['bG']['atk'] == 0, r2
        print('[② W在seriesList · ③ W条件被动生效/非W不生效 通过]')

        assert not errors, errors
        print('=== test_v116 全部通过 ===')
        b.close()
finally:
    srv.terminate()
