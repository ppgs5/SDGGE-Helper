# -*- coding: utf-8 -*-
"""v0.13 验证: 多阶段增益(Multi-Phase Buff) + 与参考站精确对齐(刹那EX2=152,999)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8843
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

        # ---------- 引擎级: 刹那 EX2 = 参考站 152,999 ----------
        eng = pg.evaluate("""() => {
          const U = 1370005950, C = 1370003701, meta = metaOf(U);
          const mk = mp => charBonus(C, 'supercharged', {passive:true, cpassive:true, skills:true, unitId:U, upassive:true, multiPhase:mp}, meta);
          const bOn = mk(true), bOff = mk(false);
          const uAtk = Math.floor(Math.floor(6950*1.4 > 0 ? 0 : 0)); // placeholder
          const un = q1('SELECT * FROM units WHERE id=?', [U]);
          const uPct = unitPassiveAtkPct(U, 'supercharged', true) + unitSkillAtkPct(U);   // 被动(条件全开)+单位技能(技能开)
          const uBase = Math.floor((un.sp_max_atk || un.max_atk) * 1.4);
          const uAtkV = Math.floor(uBase * (1 + uPct/100));
          const w = q1("SELECT * FROM weapons WHERE unit_id=? AND name LIKE '%强化巨剑%'", [U]);
          const traits = q('SELECT * FROM weapon_traits WHERE weapon_id=?', [w.id]);
          const cAtkOn = Math.floor(670 * (1 + bOn.melee/100));
          const cAtkOff = Math.floor(670 * (1 + bOff.melee/100));
          const dOn = Engine.damageWithWeapon(uAtkV, cAtkOn, w, traits, 5, 10040, 703, {vigor:'supercharged', crit:false, ee: bOn.dmg});
          const dOff = Engine.damageWithWeapon(uAtkV, cAtkOff, w, traits, 5, 10040, 703, {vigor:'supercharged', crit:false, ee: bOff.dmg});
          return {uPct, uAtkV, bOn, bOff, cAtkOn, cAtkOff, on: dOn.final, off: dOff.final};
        }""")
        print('[engine]', json.dumps(eng, ensure_ascii=False))
        assert eng['uAtkV'] == 14008, '机体攻击应为14008'
        assert eng['cAtkOn'] == 1038 and eng['on'] == 152999, 'EX2(多阶段开) 应与参考站一致 152,999'
        assert eng['cAtkOff'] == 837 and eng['off'] < eng['on'], 'EX1(多阶段关) 应使用+20%阶段'

        # ---------- UI: 计算页 刹那+00 RaiserEX, 靶10040/703 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(200)
        pg.click('#picku'); pg.fill('#pk', '强化模组'); pg.wait_for_timeout(500)
        pg.click("#pkl [data-pick='1370005950']"); pg.wait_for_timeout(400)
        pg.fill('#tdef2', '10040'); pg.dispatch_event('#tdef2', 'change'); pg.wait_for_timeout(300)
        pg.fill('#tcdef2', '703'); pg.dispatch_event('#tcdef2', 'change'); pg.wait_for_timeout(600)
        chips = pg.eval_on_selector_all('.chip', "els => els.map(e => e.textContent.trim()).filter(t => /多阶段|主动技能|驾驶员被动/.test(t))")
        print('[chips]', chips)
        rows = pg.eval_on_selector_all('[data-pid]', "els => els.slice(0,3).map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        print('[pilot top3]', json.dumps(rows, ensure_ascii=False))
        sq = next((r for r in rows if '刹那' in r and '1038' in r), '')
        assert '152,999' in sq, f'刹那EX2 应为 152,999: {sq}'
        det = pg.evaluate("() => document.getElementById('detail').textContent.replace(/\\s+/g,' ').trim()")
        print('[detail]', det[-160:])
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/22a_mp_on.png')

        # 武士道: 被动MP6(trait43 敌方条件)+技能MP6 = MP12 超一击
        wsb = next((r for r in rows if '武士道' in r), '')
        print('[武士道 row]', wsb)
        assert '超一击(12)' in wsb.replace(' ', ''), '武士道应 MP12 超一击'

        # 关闭多阶段增益 → EX1 阶段
        pg.click('#mp'); pg.wait_for_timeout(1200)
        rows2 = pg.eval_on_selector_all('[data-pid]', "els => els.slice(0,3).map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        print('[mp off top3]', json.dumps(rows2, ensure_ascii=False))
        rows2txt = ' '.join(rows2)
        assert '152,999' not in rows2txt, '关闭多阶段后不应再有 EX2 数值'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/22b_mp_off.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
