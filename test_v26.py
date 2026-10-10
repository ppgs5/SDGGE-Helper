# -*- coding: utf-8 -*-
"""v0.27 验证: 战意限制「超强势以上」武器在强势及以下不可用（计算/排行/组队 + 机体页最大伤害）"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8911
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

        # ---------- 0. 数据层 ----------
        chk = pg.evaluate("""() => {
          return {
            needMax: weaponNeedMax(120000395005),                      // 石破天惊神威掌
            high: vigorAllows(120000395005, 'high'),                   // 强势 → 不可用
            max: vigorAllows(120000395005, 'max'),                     // 超强势 → 可用
            free: vigorAllows(120000395006, 'mid'),                    // 洗牌同盟拳EX 无限制 → 任何时候可用
            n: q("SELECT DISTINCT weapon_id FROM weapon_use WHERE text LIKE '%超强势%'").length,
          };
        }""")
        print('[数据]', chk)
        assert chk['needMax'] and not chk['high'] and chk['max'] and chk['free'], '战意限制判定异常'
        assert chk['n'] >= 1400, '超强势限定武器覆盖异常'

        # ---------- 1. 计算页: 强势隐藏 + 提示；超强势恢复 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '神高达'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pick='1200003950']"); pg.wait_for_timeout(800)   # 神高达 (EX)
        pg.click('[data-vg="high"]'); pg.wait_for_timeout(1600)
        t1 = pg.evaluate("() => document.querySelector('#view table.ctable').textContent.replace(/\\s+/g,' ')")
        note = pg.evaluate("() => { const n = document.querySelector('#view .subnote'); return n ? n.textContent.trim() : '' }")
        print('[计算 强势] 含限定武器:', '石破天惊神威掌' in t1, '| 提示:', note[:50])
        assert '石破天惊神威掌' not in t1, '强势下不应出现超强势限定武器'
        assert '石破天惊拳' in t1 or '洗牌同盟拳 EX' in t1, '无限制武器应保留'
        assert '已隐藏' in note and '强势' in note, '应提示已隐藏限定武器'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/39a_calc_high.png')
        pg.click('[data-vg="max"]'); pg.wait_for_timeout(1600)
        t2 = pg.evaluate("() => document.querySelector('#view table.ctable').textContent.replace(/\\s+/g,' ')")
        print('[计算 超强势] 含限定武器:', '石破天惊神威掌' in t2)
        assert '石破天惊神威掌' in t2, '超强势下限定武器应恢复'
        pg.click('[data-vg="mid"]'); pg.wait_for_timeout(1600)
        t3 = pg.evaluate("() => document.querySelector('#view table.ctable').textContent.replace(/\\s+/g,' ')")
        assert '石破天惊神威掌' not in t3, '无气势下不应出现限定武器'

        # ---------- 2. 排行页: 强势下不得使用限定武器 ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('#rlist .rrow', timeout=120000); pg.wait_for_timeout(2500)
        pg.click('[data-vg="high"]'); pg.wait_for_timeout(4000)
        r1 = pg.evaluate("() => document.getElementById('rlist').textContent.replace(/\\s+/g,' ')")
        print('[排行 强势] 含石破天惊神威掌:', '石破天惊神威掌' in r1)
        assert '石破天惊神威掌' not in r1, '排行强势下不应出现超强势限定武器'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/39b_rank_high.png')

        # ---------- 3. 组队页: 强势下 SSP/限定武器均不可用 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow'); pg.wait_for_timeout(3200)
        pg.click('[data-tvg="high"]'); pg.wait_for_timeout(3500)
        tt = pg.evaluate("() => document.getElementById('tarea').textContent.replace(/\\s+/g,' ')")
        print('[组队 强势] 神威掌:', '石破天惊神威掌' in tt, '| 强化巨剑SSP:', '强化巨剑 SSP' in tt)
        assert '石破天惊神威掌' not in tt and '强化巨剑 SSP' not in tt, '组队强势下不应出现超强势限定武器'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/39c_team_high.png')

        # ---------- 4. 机体页: 最大伤害卡（auto战意）同受限制 ----------
        n = pg.evaluate("""() => {
          const ws = q("SELECT id FROM weapons WHERE unit_id=1200003950 AND id IN (SELECT weapon_id FROM weapon_use WHERE text LIKE '%超强势%')");
          const rows = unitBestPilot(1200003950, 20000);
          const bad = rows.filter(r => r.weapon && r.weapon.id === ws.map(x => x.id)[0] && !(r.vigor === 'max' || r.vigor === 'supercharged'));
          return {rows: rows.length, bad: bad.length, topW: rows[0] ? rows[0].weapon.name : '', topV: rows[0] ? rows[0].vigor : ''};
        }""")
        print('[机体页最大伤害]', n)
        assert n['bad'] == 0, '战意不足时不应选到限定武器'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
