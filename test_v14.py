# -*- coding: utf-8 -*-
"""v0.14 验证: 排行与计算页口径统一（同一机体+驾驶员+靶 = 相同数值）"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8846
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

        # 排行页默认口径 chips
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('#rlist .rrow')
        chips = pg.evaluate("""() => ['rsk','rca','rmp'].map(id => document.getElementById(id).textContent.trim())""")
        print('[rank chips]', chips)
        assert '开' in chips[0] and '开' in chips[1] and '开' in chips[2], '排行默认应全开'

        # 排行 (页面口径) 取 神高达EX / AGE-1EX 的行
        rank = pg.evaluate("""() => {
          const c = state.rankCfg;
          const rows = buildRanking(filt('rank'), c, {passive:c.passive, cpassive:c.cpassive, skills:c.skills, condAll:!!c.ca, autoVigor:c.vigor==='default', multiPhase:!!c.mp, star:c.star});
          const pick = id => { const r = rows.find(x => x.unitId === id); return r && {unitId:r.unitId, pilotId:r.pilot.id, pilot:r.pilot.name, dmg:r.dmg, vigor:r.vigor, mp:r.mp}; };
          return {god: pick(1200003950), age: pick(1400000150)};
        }""")
        print('[rank]', json.dumps(rank, ensure_ascii=False))
        assert rank['god'] and rank['age'], '排行缺少目标机体'

        # 计算页逐一比对相同 机体+驾驶员 (默认口径)
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        for key, uname in (('god', '神高达'), ('age', '高达AGE-1')):
            r = rank[key]
            pg.click('#picku'); pg.fill('#pk', uname); pg.wait_for_timeout(500)
            pg.click(f"#pkl [data-pick='{r['unitId']}']"); pg.wait_for_timeout(900)
            hit = pg.evaluate("""(pid) => {
              const el = [...document.querySelectorAll('[data-pid]')].find(e => +e.dataset.pid === pid);
              return el ? el.textContent.replace(/\\s+/g,' ').trim() : null;
            }""", r['pilotId'])
            print(f"[calc {key}] rank={r['dmg']} pilot={r['pilot']} | calc row:", hit)
            assert hit is not None, '计算页列表中应包含该驾驶员'
            assert f"{r['dmg']:,}" in hit, f"{key}: 排行与计算数值不一致 (rank={r['dmg']})"
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/23a_consistency.png')

        # 组队默认口径也一致（攻撃型 TOP1 与排行同机体对比至少格式正常）
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow')
        tchips = pg.evaluate("""() => ['tca','tmp'].map(id => document.getElementById(id).textContent.trim())""")
        print('[team chips]', tchips)
        assert '开' in tchips[0] and '开' in tchips[1], '组队默认应含条件/多阶段开'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
