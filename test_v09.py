# -*- coding: utf-8 -*-
"""v0.9 验证: 作品系列筛选(图鉴/排行/组队) / SD高达机体专属驾驶员 / 默认气势(按被动MP) / 组队气势显示"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8835
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

        # ---------- 1. 图鉴 作品系列筛选 ----------
        pg.click('#tbtn'); pg.wait_for_timeout(500)
        seg = pg.eval_on_selector_all('[data-lm]', "els => els.map(e => e.textContent.trim())")
        print('[picker seg]', seg)
        pg.click("[data-lm='series']"); pg.wait_for_timeout(300)
        rows = pg.eval_on_selector_all('#stlist [data-sid]', "els => els.slice(0,6).map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        print('[series list]', rows)
        pg.fill('#ssearch', '武斗传'); pg.wait_for_timeout(300)
        pg.click("#stlist [data-sid='2000']"); pg.wait_for_timeout(200)
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/18a_series_pick.png')
        pg.click('#sapply'); pg.wait_for_timeout(1200)
        res = pg.evaluate("""() => {
          const f = filt('unit');
          const u = unitWhere('unit', f);
          const n = q1(`SELECT COUNT(*) c FROM units u ${u.where}`, u.args).c;
          const ids = q(`SELECT DISTINCT series_id FROM units u ${u.where}`, u.args).map(r => r.series_id);
          return {series: f.series, n, ids};
        }""")
        print('[units filter]', json.dumps(res, ensure_ascii=False))
        assert res['series'] == ['2000'] and res['n'] == 48 and res['ids'] == ['2000'], '系列筛选错误'
        hit = pg.eval_on_selector('#hit', 'e => e.textContent')
        print('[units hit]', hit)
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/18b_units_series.png')

        # ---------- 2. 排行/组队 系列同样生效 + 默认气势 ----------
        rankres = pg.evaluate("""() => {
          filt('rank').series = ['2000']; filt('rank').tags = [];
          const rows = buildRanking(filt('rank'), state.rankCfg, {passive:true,cpassive:true,skills:false,condAll:false,autoVigor:true,star:3});
          const series = new Set(rows.map(r => r.unit.series_id));
          const god = rows.find(r => r.unitId === 1200003950);
          const zeta = rows.find(r => r.unitId === 1080000150);
          return {n: rows.length, series: [...series], top: rows.slice(0,2).map(r => ({n:r.unit.name, pilot:r.pilot.name, dmg:r.dmg, vigor:r.vigor, mp:r.mp})),
                  godInList: !!god, zetaInList: !!zeta};
        }""")
        print('[rank series=G]', json.dumps(rankres, ensure_ascii=False))
        assert rankres['series'] == ['2000'], '排行系列筛选错误'
        # 神高达EX 属于G高达(2000) → 在榜; Z高达EX(800) → 不在榜
        assert rankres['godInList'] and not rankres['zetaInList'], '系列筛选边界错误'
        # 默认气势: 随机抽一个带MP的 确认 vigor 随 MP
        mpchk = pg.evaluate("""() => {
          const rows = buildRanking(filt('rank'), state.rankCfg, {passive:true,cpassive:true,skills:false,condAll:false,autoVigor:true,star:3});
          const withMp = rows.filter(r => r.mp > 0).slice(0,3).map(r => r.unit.name + '|' + r.pilot.name + '|MP' + r.mp + '|' + r.vigor);
          const noMp = rows.filter(r => !r.mp).slice(0,2).map(r => r.unit.name + '|' + r.vigor);
          return {withMp, noMp};
        }""")
        print('[rank default vigor]', json.dumps(mpchk, ensure_ascii=False))
        assert all('supercharged' in x or 'max' in x or 'high' in x for x in mpchk['withMp']), 'MP>0 应映射到气势状态'
        pg.evaluate("() => { filt('rank').series = []; }")

        # ---------- 3. SD高达不能换乘 ----------
        sdres = pg.evaluate("""() => {
          const rows = buildRanking(filt('rank'), state.rankCfg, {passive:true,cpassive:true,skills:false,condAll:true,autoVigor:false,star:3});
          const pick = id => { const r = rows.find(x => x.unitId === id); return r ? r.pilot.name : '(未上榜)'; };
          const sdUnits = q(`SELECT u.id,u.name FROM units u JOIN unit_tags ut ON ut.unit_id=u.id JOIN tags t ON t.id=ut.tag_id WHERE t.name='SD高达'`).length;
          const listed = q(`SELECT u.id FROM units u JOIN unit_tags ut ON ut.unit_id=u.id JOIN tags t ON t.id=ut.tag_id WHERE t.name='SD高达'`).filter(r => rows.some(x => x.unitId === r.id)).length;
          return {knight: pick(1705002050), kn: pick(1705000100), sdUnits, listed};
        }""")
        print('[SD pilots]', json.dumps(sdres, ensure_ascii=False))
        assert sdres['knight'] == '全能骑士高达', 'SD机体应使用专属驾驶员'
        assert sdres['kn'] == '骑士高达', 'SD机体应使用专属驾驶员'
        assert sdres['listed'] == sdres['sdUnits'], f"SD机体应全部有专属驾驶员 ({sdres['listed']}/{sdres['sdUnits']})"
        # 排行页横幅: 非SD机体仍用顶级驾驶员
        god = pg.evaluate("""() => {
          const rows = buildRanking(filt('rank'), state.rankCfg, {passive:true,cpassive:true,skills:false,condAll:true,autoVigor:false,star:3});
          const r = rows.find(x => x.unitId === 1200003950); return r.pilot.name;
        }""")
        print('[god pilot]', god); assert god == '多蒙·卡修'

        # ---------- 4. 组队: 默认气势 + 显式气势 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow')
        tvg = pg.eval_on_selector_all('[data-tvg]', "els => els.map(e => e.textContent.trim() + (e.classList.contains('gold') ? '*' : ''))")
        print('[team vigor chips]', tvg)
        first = pg.eval_on_selector('#tarea .trow .nm small', 'e => e.textContent.replace(/\\s+/g," ").trim()')
        print('[team row default]', first)
        assert ('(MP' in first) or ('气势0' in first), '组队行气势显示不符'
        pg.click("[data-tvg='supercharged']"); pg.wait_for_timeout(1200)
        first2 = pg.eval_on_selector('#tarea .trow .nm small', 'e => e.textContent.replace(/\\s+/g," ").trim()')
        print('[team row supercharged]', first2)
        assert '气势超一击' in first2, '显式气势显示不符'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/18c_team_vigor.png')
        pg.click("[data-tvg='default']"); pg.wait_for_timeout(1000)

        # ---------- 5. 计算页 SD 提示 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(200)
        pg.click('#picku'); pg.fill('#pk', '全能骑士'); pg.wait_for_timeout(500)
        pg.click("#pkl [data-pick='1705002050']"); pg.wait_for_timeout(500)
        hint = pg.evaluate("() => [...document.querySelectorAll('#view .subnote')].map(e => e.textContent).join(' | ')")
        print('[calc SD hint]', hint)
        assert '不能换乘' in hint and '全能骑士高达' in hint, '计算页缺少SD提示'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/18d_calc_sd.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
