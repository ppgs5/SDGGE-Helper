# -*- coding: utf-8 -*-
"""v0.6 功能验证: 组队MP气势/战舰星数与技能搜索/暴击能力门槛/排行校准/全页冒烟"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8823
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 400, 'height': 860})
        pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append('console.' + m.type + ': ' + m.text) if m.type == 'error' else None)

        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        print('[boot] ok')

        # ---------- 1. 排行校准（crit关，应与 196,708 口径一致） ----------
        pg.click('[data-tab="rank"]')
        pg.wait_for_selector('#rlist .rrow')
        top = pg.evaluate("""() => buildRanking(filt('rank'), state.rankCfg, {passive:true,cpassive:true,skills:false,condAll:true,star:3})
            .slice(0,2).map(r => ({n:r.unit.name, d:r.dmg, canCrit:r.canCrit, critRate:r.critRate}))""")
        print('[rank crit-off]', json.dumps(top, ensure_ascii=False))
        assert top[0]['n'] == '神高达 (EX)' and top[0]['d'] == 196708, 'calibration drifted!'

        # ---------- 2. 暴击开关: 神高达EX(扑克同盟拳EX 暴击15%)应变化 ----------
        pg.click('#rc')
        pg.wait_for_timeout(600)
        topc = pg.evaluate("""() => buildRanking(filt('rank'), state.rankCfg, {passive:true,cpassive:true,skills:false,condAll:true,star:3})
            .slice(0,4).map(r => ({n:r.unit.name, d:r.dmg, canCrit:r.canCrit, critRate:r.critRate}))""")
        print('[rank crit-on]', json.dumps(topc, ensure_ascii=False))
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/15a_rank_crit.png')
        # 行内是否有"无暴击能力"标记
        noCritTag = pg.evaluate("""() => [...document.querySelectorAll('#rlist .rmeta')].some(e => e.textContent.includes('无暴击能力'))""")
        print('[rank rows with 无暴击能力 tag]', noCritTag)
        pg.click('#rc')  # 关回
        pg.wait_for_timeout(300)

        # ---------- 3. 组队: 战舰星数 0~3 ----------
        pg.click('[data-tab="team"]')
        pg.wait_for_selector('#tarea .trow')
        pg.click('#picks'); pg.fill('#pk', '一击'); pg.wait_for_timeout(300)
        n_yiji = pg.eval_on_selector_all('#pkl .trow2', 'els => els.length')
        print('[search 一击] hits:', n_yiji)
        pg.fill('#pk', '王牌机'); pg.wait_for_timeout(300)
        pg.click("#pkl [data-s='1125000250']")
        pg.wait_for_timeout(600)
        chips = pg.eval_on_selector_all('[data-lb]', "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim() + (e.classList.contains('on') ? '*' : ''))")
        print('[ship star chips]', chips)
        d0 = pg.eval_on_selector('#tarea .trow .val', 'e => e.textContent')
        pg.click("[data-lb='3']"); pg.wait_for_timeout(600)
        d3 = pg.eval_on_selector('#tarea .trow .val', 'e => e.textContent')
        card3 = pg.eval_on_selector('#picks', "e => e.textContent.replace(/\\s+/g,' ').trim()")
        print(f'[ship ★0->★3] {d0} -> {d3}'); print('[card]', card3[:120])
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/15b_team_star3.png')
        pg.click("[data-lb='0']"); pg.wait_for_timeout(400)

        # ---------- 4. 计算页: 暴击能力门槛 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(200)
        pg.click('#picku'); pg.fill('#pk', '神高达'); pg.wait_for_timeout(400)
        try:
            pg.click("#pkl [data-pick='1200003950']", timeout=8000)
        except Exception:
            print('[pick debug] sheet open:', pg.evaluate("() => document.getElementById('sheet').classList.contains('open')"))
            print('[pick debug] pk value:', pg.evaluate("() => document.getElementById('pk').value"))
            print('[pick debug] pkl head:', pg.evaluate("() => document.getElementById('pkl').innerHTML.slice(0,300)"))
            print("[pick debug] pklist exists:", pg.evaluate("() => !!document.getElementById('pklist')"))
            pg.screenshot(path='/root/workspace/ggen_app/shots_app/dbg_pick.png')
            raise
        pg.wait_for_timeout(300)
        pg.click('#picku'); pg.wait_for_timeout(200)
        pg.fill('#pk', 'x'); pg.wait_for_timeout(200)
        pg.click('#wchar'); pg.wait_for_timeout(300)
        print('[toggle after search] char rows:', pg.eval_on_selector_all('#pkl [data-pickc]', 'els => els.length'))
        pg.fill('#pk', '杜门'); pg.wait_for_timeout(400)
        pg.click("#pkl [data-pickc='1200000103']"); pg.wait_for_timeout(500)
        off = pg.evaluate("() => ({chip: document.getElementById('crit').textContent, row: document.querySelectorAll('.ctable tr')[1].textContent.replace(/\\s+/g,' ').trim(), det: document.getElementById('detail').textContent.replace(/\\s+/g,' ').trim()})")
        pg.click('#crit'); pg.wait_for_timeout(400)
        on = pg.evaluate("() => ({chip: document.getElementById('crit').textContent, row: document.querySelectorAll('.ctable tr')[1].textContent.replace(/\\s+/g,' ').trim(), det: document.getElementById('detail').textContent.replace(/\\s+/g,' ').trim()})")
        print('[calc crit off]', json.dumps(off, ensure_ascii=False)[:260])
        print('[calc crit on] ', json.dumps(on, ensure_ascii=False)[:300])
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/15c_calc_crit.png')
        # 切到无暴击武器(AGE系统EX)的机体: 高达AGE-1基本型 (EX)
        pg.click('#picku'); pg.fill('#pk', 'AGE-1'); pg.wait_for_timeout(400)
        pg.click("#pkl [data-pick='1400000150']"); pg.wait_for_timeout(500)
        noC = pg.evaluate("() => ({chip: document.getElementById('crit').textContent, det: document.getElementById('detail').textContent.replace(/\\s+/g,' ').trim()})")
        print('[calc no-crit unit]', json.dumps(noC, ensure_ascii=False)[:240])

        # ---------- 5. 其它页冒烟 ----------
        for tab, sel in [('units', '.ucard'), ('feat', '.lrow')]:
            pg.click(f'[data-tab="{tab}"]'); pg.wait_for_selector(sel); print(f'[{tab}] ok')
        pg.click('[data-tab="units"]'); pg.wait_for_selector('.ucard')
        for k in ['char', 'weapon', 'supp', 'mod']:
            pg.click(f"#kinds [data-k='{k}']"); pg.wait_for_timeout(600)
        print('[units kinds] ok')
        b.close()
finally:
    srv.terminate()

print('[js errors]', errors if errors else 'none')
