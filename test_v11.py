# -*- coding: utf-8 -*-
"""v0.11 验证: 计算页 靶防御输入 + 低中高防快捷"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8839
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
        pg.click("#pkl [data-pickc='1200000103']"); pg.wait_for_timeout(600)

        hdr = pg.eval_on_selector_all('.ctable th', "els => els.map(e => e.textContent.trim())")
        chips = pg.eval_on_selector_all('[data-tdef]', "els => els.map(e => e.textContent.trim() + (e.classList.contains('on') ? '*' : ''))")
        row1 = pg.eval_on_selector_all('.ctable tr', "els => els[1].textContent.replace(/\\s+/g,' ').trim()")
        print('[header]', hdr, '[chips]', chips); print('[row1 default]', row1)
        assert hdr == ['武器 / 射程', '低防 10k', '中防 20k', '高防 40k'] and '低防 10k*' in chips, '默认列/高亮错误'

        # 高防 chip
        pg.click("[data-tdef='40000']"); pg.wait_for_timeout(700)
        hdr2 = pg.eval_on_selector_all('.ctable th', "els => els.map(e => e.textContent.trim())")
        chips2 = pg.eval_on_selector_all('[data-tdef]', "els => els.map(e => e.textContent.trim() + (e.classList.contains('on') ? '*' : ''))")
        vinput = pg.eval_on_selector('#tdef2', 'e => e.value')
        det = pg.evaluate("() => [...document.querySelectorAll('#view .card h4')].map(h => h.textContent)")
        print('[after 高防]', hdr2, chips2, 'input=', vinput, '|', det)
        assert vinput == '40000' and '高防 40k*' in chips2, '高防选择失败'
        assert any('靶 40k' in d for d in det), '目标防御未同步到驾驶员列表'

        # 自定义 15000
        pg.fill('#tdef2', '15000'); pg.dispatch_event('#tdef2', 'change'); pg.wait_for_timeout(800)
        hdr3 = pg.eval_on_selector_all('.ctable th', "els => els.map(e => e.textContent.trim())")
        print('[after custom]', hdr3)
        assert '当前 15k' in hdr3, '自定义列未出现'
        chk = pg.evaluate("""() => {
          const tds = [...document.querySelectorAll('.ctable tr')[1].querySelectorAll('td')];
          const t = Math.round(parseFloat(tds[tds.length - 1].textContent.replace(/,/g, '')));
          const w = q1('SELECT * FROM weapons WHERE unit_id=1200003950 ORDER BY power DESC LIMIT 1');
          const un = q1('SELECT * FROM units WHERE id=1200003950');
          const ch = q1('SELECT * FROM characters WHERE id=1200000103');
          const effV0 = state.calc.vigor === 'default' ? mpToVigor(mpOf(un.id, ch.id, state.calc.skills)) : state.calc.vigor;
          const b = charBonus(ch.id, effV0, {passive:true, skills:true, condAll:false}, metaOf(un.id));
          const uAtk = Math.floor((un.sp_max_atk||un.max_atk) * 1.4 * (1 + unitPassiveAtkPct(un.id, effV0, false)/100));
          const cAtk = Math.round(ch.max_melee * (1 + (b.melee||0)/100));
          const effV = state.calc.vigor === 'default' ? mpToVigor(mpOf(un.id, ch.id, state.calc.skills)) : state.calc.vigor;
          const expect = Engine.damageWithWeapon(uAtk, cAtk, w, q('SELECT * FROM weapon_traits WHERE weapon_id=?',[w.id]), 5, 15000, state.calc.tCharDef, {vigor:effV, crit:false, ee:b.dmg}).final;
          return {cell: t, expect};
        }""")
        print('[custom col value check]', chk)
        assert chk['cell'] == chk['expect'], '自定义防御列数值错误'
        detail = pg.evaluate("() => [...document.querySelectorAll('#view .card h4')].map(h => h.textContent).find(t => t.includes('公式明细'))")
        print('[detail header]', detail)
        assert '靶 15,000' in detail, '公式明细未使用自定义防御'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/20a_calc_def.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
