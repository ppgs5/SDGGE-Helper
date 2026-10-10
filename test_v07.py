# -*- coding: utf-8 -*-
"""v0.7 验证: 队伍增强可选生效 / 组队射程MAP筛选 / 特性页增强合并 / 暴击率含被动与技能"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8831
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

        # ---------- 1. 暴击率含驾驶员被动（三日月 crit+20 · 阿赖耶识系统）----------
        ci = pg.evaluate("""() => {
          const un = q1("SELECT u.id FROM units u JOIN unit_tags ut ON ut.unit_id=u.id JOIN tags t ON t.id=ut.tag_id WHERE t.name='阿赖耶识系统' AND u.id=1430003450");
          const w = q1('SELECT * FROM weapons WHERE unit_id=? ORDER BY crit_rate DESC LIMIT 1', [1430003450]);
          const a = critInfo(1430003450, 1430000105, w, metaOf(1430003450), {upassive:true, cpassive:true, skills:false, condAll:true, vigor:'mid'});
          const b2 = critInfo(1430003450, 1430000105, w, metaOf(1430003450), {upassive:true, cpassive:false, skills:false, condAll:true, vigor:'mid'});
          const sk = charCritSkills(); const cid = +Object.keys(sk)[0];
          const c0 = critInfo(null, cid, {crit_rate:0}, null, {cpassive:true, skills:false, condAll:true});
          const c1 = critInfo(null, cid, {crit_rate:0}, null, {cpassive:true, skills:true, condAll:true});
          return {wName: w.name, wCrit: w.crit_rate, withPsv: a.rate, withoutPsv: b2.rate,
                  skillPilot: cid, skillSum: sk[cid], skillsOff: c0.rate, skillsOn: c1.rate};
        }""")
        print('[crit]', json.dumps(ci, ensure_ascii=False))
        assert ci['withPsv'] == ci['wCrit'] + 20, '驾驶员被动暴击率未计入'
        assert ci['withoutPsv'] == ci['wCrit'], '关闭驾驶员被动后暴击率应回落'
        assert ci['skillsOn'] == ci['skillsOff'] + sum(x['v'] for x in ci['skillSum']), '主动技能暴击率未计入'

        # ---------- 2. 计算页显示暴击能力明细 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(200)
        pg.click('#picku'); pg.fill('#pk', '巴巴托斯'); pg.wait_for_timeout(500)
        pg.click("#pkl [data-pick='1430003450']"); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.wait_for_timeout(200)
        pg.click('#wchar'); pg.fill('#pk', '三日月'); pg.wait_for_timeout(500)
        pg.click("#pkl [data-pickc='1430000105']"); pg.wait_for_timeout(400)
        pg.click('#crit'); pg.wait_for_timeout(500)
        det = pg.evaluate("() => document.getElementById('detail').textContent.replace(/\\s+/g,' ').trim()")
        print('[calc detail]', det[:220])
        assert '暴击能力' in det and '被动' in det, '计算页未显示暴击能力明细'

        # ---------- 3. 组队: 射程筛选(含MAP) ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow')
        rgchips = pg.eval_on_selector_all('[data-rg]', "els => els.map(e => e.textContent.trim())")
        print('[team range chips]', rgchips)
        pg.click("[data-rg='map']"); pg.wait_for_timeout(1200)
        allMap = pg.evaluate("""() => {
          const r = buildRanking(filt('team'), {targetDef:10000,targetCharDef:750,vigor:'mid',crit:false,range:'map'},
            {passive:true,cpassive:true,skills:false,condAll:false,autoVigor:true});
          return {n: r.length, ok: r.every(x => x.weapon.type === 3), sample: r.slice(0,2).map(x => x.unit.name + ' ' + x.weapon.name + ' ' + x.dmg)};
        }""")
        print('[team MAP filter]', json.dumps(allMap, ensure_ascii=False))
        assert allMap['ok'] and allMap['n'] > 0, 'MAP筛选错误'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/16a_team_map.png')
        pg.click("[data-rg='all']"); pg.wait_for_timeout(1000)

        # ---------- 4. 队伍增强 选择→生效 ----------
        base = pg.evaluate("""() => {
          const r = buildRanking(filt('team'), {targetDef:10000,targetCharDef:750,vigor:'mid',crit:false,range:'all'},
            {passive:true,cpassive:true,skills:false,condAll:false,autoVigor:true,ship:null,teamBuffs:[]});
          const m = {}; for (const x of r) m[x.unitId] = x.dmg;
          return {unicorn: m[1144000550], god: m[1200003950]};
        }""")
        print('[before buffs]', base)
        pg.click('#tbuff'); pg.wait_for_timeout(600)
        groups = pg.evaluate("""() => teamBuffGroups().map(g => ({key:g.key, owner:g.owner, tags:g.tags, atk:g.atk, def:g.def, req:g.reqName}))""")
        print(f"[buff groups] {len(groups)}:", json.dumps(groups, ensure_ascii=False)[:600])
        idx = next(i for i, g in enumerate(groups) if 'NT-D' in g['tags'])
        pg.locator('[data-g]').nth(idx).click(); pg.wait_for_timeout(200)
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/16b_teambuff_pick.png')
        pg.click('#tapply'); pg.wait_for_timeout(1200)
        chips = pg.eval_on_selector_all('[data-bdel]', "els => els.map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        print('[selected chips]', chips)
        after = pg.evaluate("""() => {
          const g = teamBuffGroups().find(x => x.tags.includes('NT-D'));
          const r = buildRanking(filt('team'), {targetDef:10000,targetCharDef:750,vigor:'mid',crit:false,range:'all'},
            {passive:true,cpassive:true,skills:false,condAll:false,autoVigor:true,ship:null,teamBuffs:[g]});
          const m = {}; for (const x of r) m[x.unitId] = {dmg:x.dmg, hit:x.buffHit, atk:x.buffAtk};
          return {unicorn: m[1144000550], god: m[1200003950]};
        }""")
        print('[after NT-D buff]', after)
        assert after['unicorn']['dmg'] > base['unicorn'] and after['unicorn']['hit'], 'NT-D增强未生效'
        assert after['god']['dmg'] == base['god'], '非NT-D机体不应变化'
        titletxt = pg.eval_on_selector('#tarea h4', 'e => e.textContent')
        print('[title]', titletxt)
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/16c_team_buff_on.png')

        # ---------- 5. 特性页 队伍增强合并 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow')
        pg.click("[data-k='team_buff']"); pg.wait_for_timeout(500)
        feat = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#farea .lrow .nm')].map(e => e.textContent.replace(/\\s+/g,' ').trim());
          return {n: rows.length, rows: rows.slice(0, 4)};
        }""")
        print('[feat team_buff]', json.dumps(feat, ensure_ascii=False))
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/16d_feat_teambuff.png')
        assert feat['n'] == len(groups), '特性页分组数不一致'

        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
