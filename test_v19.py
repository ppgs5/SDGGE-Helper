# -*- coding: utf-8 -*-
"""v0.19 验证: SD驾驶员侧绑定/缺失机体/先发威力/排行稀有度+特性标记/组队靶防+防御机体+全能力"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8873
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

        # ---------- 1. 数据层: 缺失机体已补 / 先发威力 / 特性标记 ----------
        d = pg.evaluate("""() => ({
            units: q1('SELECT COUNT(*) c FROM units').c,
            missing_ref: q1('SELECT COUNT(DISTINCT unit_id) c FROM weapons WHERE unit_id NOT IN (SELECT id FROM units)').c,
            pre: q1("SELECT COUNT(*) c FROM features WHERE feature='preemptive'").c,
            pre_pw: (q1("SELECT params_json p FROM features WHERE feature='preemptive' LIMIT 1")||{}).p,
            flags: q1('SELECT COUNT(*) c FROM weapon_flag').c,
            u1310: (q1('SELECT name n FROM units WHERE id=1211001310')||{}).n,
            u1200003000: (q1('SELECT name n FROM units WHERE id=1200003000')||{}).n })""")
        print('[数据]', json.dumps(d, ensure_ascii=False)[:220])
        assert d['units'] >= 1441 and d['missing_ref'] == 0, '缺失机体未补齐'
        assert d['u1310'] and d['u1200003000'], '缺失机体无名称'
        assert '"power"' in (d['pre_pw'] or ''), '先发攻击威力缺失'
        assert d['flags'] > 1000, '武器特性标记缺失'

        # ---------- 2. SD绑定驾驶员不能驾驶其他机体 ----------
        sd = pg.evaluate("""() => {
          const m = sdCharMap();
          const hei = q1("SELECT id FROM characters WHERE name='怪物黑龙'");
          const owns = [...(m[hei.id] || [])];
          return {hei: hei.id, owns};
        }""")
        print('[黑龙绑定]', sd)
        assert sd['owns'] and 1705000550 in sd['owns'], '怪物黑龙应绑定怪物黑龙(EX)'
        # 组队列表中 怪物黑龙 只出现在自家机体
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow'); pg.wait_for_timeout(3000)
        rows = pg.eval_on_selector_all('#tarea .trow', "els => els.map(e => e.textContent.replace(/\\s+/g,' '))")
        bad = [r for r in rows if '怪物黑龙' in r and '怪物黑龙 (EX)' not in r]
        print('[黑龙行]', [r[:60] for r in rows if '怪物黑龙' in r][:3])
        assert not bad, f'SD绑定驾驶员仍驾驶其他机体: {bad[:1]}'

        # ---------- 3. 组队靶防御/防御增加/攻方全能力 ----------
        chips = pg.eval_on_selector_all('[data-tdef3]', "els => els.map(e => e.textContent.trim())")
        assert chips == ['低防 10k', '中防 20k', '高防 40k'], '靶防 chips 缺失'
        d1 = pg.evaluate("() => (document.querySelector('#tarea .trow .val')||{}).textContent")
        pg.fill('#tdefup', '50'); pg.dispatch_event('#tdefup', 'change'); pg.wait_for_timeout(3000)
        t2 = pg.evaluate("() => document.getElementById('tarea').textContent.replace(/\\s+/g,' ')")
        assert '防御增加50%' in t2, '防御增加未生效'
        d2 = pg.evaluate("() => (document.querySelector('#tarea .trow .val')||{}).textContent")
        assert d2 != d1, '防御增加后伤害应变化'
        print(f'[防御增加] {d1} -> {d2}')
        pg.fill('#tdefup', '0'); pg.dispatch_event('#tdefup', 'change'); pg.wait_for_timeout(2500)
        pg.fill('#tatkup', '20'); pg.dispatch_event('#tatkup', 'change'); pg.wait_for_timeout(3000)
        t3 = pg.evaluate("() => document.getElementById('tarea').textContent.replace(/\\s+/g,' ')")
        assert '攻方全能力+20%' in t3, '攻方全能力未生效'
        print('[攻方全能力+20%] top1:', pg.evaluate("() => (document.querySelector('#tarea .trow .val')||{}).textContent"))
        pg.fill('#tatkup', '0'); pg.dispatch_event('#tatkup', 'change'); pg.wait_for_timeout(2500)

        # ---------- 4. 指定防御机体+驾驶员 -> 最大伤害展示 ----------
        pg.click('#dpick'); pg.wait_for_timeout(700)
        pg.fill('#pk', '独角兽高达'); pg.wait_for_timeout(600)
        pg.click('#pkl [data-dpick]'); pg.wait_for_timeout(1000)
        pg.click('#pkl [data-dpickc]'); pg.wait_for_timeout(3000)
        t4 = pg.evaluate("() => document.getElementById('tarea').textContent.replace(/\\s+/g,' ')")
        seg = t4[t4.find('对防御目标最大伤害'):t4.find('对防御目标最大伤害') + 120]
        print('[指定防御]', seg)
        assert '独角兽' in seg and 'eHP' in seg, '指定防御机体未生效'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/28a_team_def.png')

        # ---------- 5. 排行: 稀有度 + 武器特性标记 ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('#rlist .rrow'); pg.wait_for_timeout(3000)
        rar = pg.eval_on_selector_all('#rlist .rrow:nth-child(1) .rar, #rlist .rrow:nth-child(1) span', "els => els.map(e=>e.className)")
        row1 = pg.evaluate("() => document.querySelector('#rlist .rrow').textContent.replace(/\\s+/g,' ').slice(0,150)")
        print('[排行行]', row1)
        assert 'UR' in row1 or 'SSR' in row1, '稀有度未显示'
        flags = pg.eval_on_selector_all('#rlist .wflag', "els => [...new Set(els.map(e=>e.textContent))]")
        print('[排行特性]', flags)
        assert flags and any(f in flags for f in ('先发攻击', '额外行动', '降防', '无视防御', '降攻')), '武器特性标记未显示'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/28b_rank.png')

        # ---------- 6. 特性页先发攻击威力 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow')
        pg.click("[data-k='preemptive']"); pg.wait_for_timeout(500)
        ft = pg.evaluate("() => document.getElementById('farea').textContent.replace(/\\s+/g,' ')")
        print('[先发攻击]', ft[:110])
        assert '威力' in ft, '先发攻击未显示威力'
        # 缺失机体名称显示
        assert '1211001310' not in ft and '1200003000' not in ft, '缺失机体仍显示ID'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
