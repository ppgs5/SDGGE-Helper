# -*- coding: utf-8 -*-
"""v0.12 验证: 计算页 默认战意(按驾驶员被动MP) + 驾驶员列表战意显示"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8841
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

        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(200)
        pg.click('#picku'); pg.fill('#pk', '神高达'); pg.wait_for_timeout(500)
        pg.click("#pkl [data-pick='1200003950']"); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.wait_for_timeout(200)
        pg.click('#wchar'); pg.fill('#pk', '杜门'); pg.wait_for_timeout(400)
        pg.click("#pkl [data-pickc='1200000103']"); pg.wait_for_timeout(800)

        chips = pg.eval_on_selector_all('[data-vg]', "els => els.map(e => e.textContent.trim() + (e.classList.contains('gold') ? '*' : ''))")
        print('[vigor chips]', chips)
        assert '默认·按MP*' in chips, '默认战意未选中'
        status = pg.evaluate("() => [...document.querySelectorAll('.chip')].find(c => c.textContent.includes('暴击补正')).textContent")
        print('[status chip]', status)
        assert '气势超一击(MP13)' in status.replace(' ', ''), '默认状态显示错误(应为 超一击(MP13), 技能开时MP=6+7)'

        # 主表数值 = 自动气势(强势)下的重算
        chk = pg.evaluate("""() => {
          const tds = [...document.querySelectorAll('.ctable tr')[1].querySelectorAll('td')];
          const cell = Math.round(parseFloat(tds[1].textContent.replace(/,/g,'')));
          const w = q1('SELECT * FROM weapons WHERE unit_id=1200003950 ORDER BY power DESC LIMIT 1');
          const un = q1('SELECT * FROM units WHERE id=1200003950'), ch = q1('SELECT * FROM characters WHERE id=1200000103');
          const vg = mpToVigor(mpOf(un.id, ch.id, state.calc.skills));
          const b = charBonus(ch.id, vg, {passive:true, skills:true, condAll:false}, metaOf(un.id));
          const uAtk = Math.floor((un.sp_max_atk||un.max_atk)*1.4*(1+unitPassiveAtkPct(un.id, vg, false)/100));
          const cAtk = Math.round(ch.max_melee*(1+(b.melee||0)/100));
          const expect = Engine.damageWithWeapon(uAtk, cAtk, w, q('SELECT * FROM weapon_traits WHERE weapon_id=?',[w.id]), 5, state.calc.tDef, state.calc.tCharDef, {vigor:vg, crit:false, ee:b.dmg}).final;
          return {vg, cell, expect};
        }""")
        print('[main table auto]', chk)
        assert chk['vg'] == 'supercharged' and chk['cell'] == chk['expect'], '默认战意主表数值错误'

        # 驾驶员列表战意显示
        rows = pg.eval_on_selector_all('[data-pid]', "els => els.slice(0,5).map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        print('[pilot rows]', json.dumps(rows, ensure_ascii=False))
        assert '(' in rows[1] and ')' in rows[1], '驾驶员列表未显示战意(MP)'
        dum = next(r for r in rows if '多蒙' in r)
        assert '超一击(13)' in dum.replace(' ', ''), f'杜门战意显示错误: {dum}'

        # 切 超一击 固定
        pg.click("[data-vg='supercharged']"); pg.wait_for_timeout(900)
        rows2 = pg.eval_on_selector_all('[data-pid]', "els => els.slice(0,3).map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        print('[fixed supercharged]', json.dumps(rows2, ensure_ascii=False))
        assert '超一击' in rows2[0] and '(' not in rows2[0].split('·')[1], '固定战意显示错误'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/21a_calc_auto_vigor.png')
        pg.click("[data-vg='default']"); pg.wait_for_timeout(900)
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/21b_calc_default_vigor.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
