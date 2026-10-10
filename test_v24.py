# -*- coding: utf-8 -*-
"""v0.25 验证: 计算/排行/组队 头像角色角标(剑=攻击/盾=耐久/子弹=支援) + 全量重抓数据(战意限制/效果值UP无重复)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8903
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

        # ---------- 数据层: 重抓后无重复 + 战意/效果值UP覆盖 ----------
        chk = pg.evaluate("""() => {
          const dup = q("SELECT weapon_id, level, desc FROM weapon_fx GROUP BY weapon_id, level, desc HAVING COUNT(*)>1", []).length;
          const sspAll = q1("SELECT COUNT(DISTINCT w.id) c FROM weapons w JOIN weapon_use u ON u.weapon_id=w.id AND u.text LIKE '%超强势%' WHERE w.is_ssp=1").c;
          const sspTot = q1("SELECT COUNT(*) c FROM weapons WHERE is_ssp=1").c;
          const nonSsp = q1("SELECT COUNT(DISTINCT w.id) c FROM weapons w JOIN weapon_use u ON u.weapon_id=w.id AND u.text LIKE '%超强势%' WHERE w.is_ssp=0").c;
          const fxUP = q1("SELECT COUNT(DISTINCT weapon_id) c FROM weapon_fx WHERE desc LIKE '%效果值UP%'").c;
          const one = q("SELECT * FROM weapon_fx WHERE weapon_id=137000590090 AND level=1 AND desc LIKE '%效果值UP%'", []).length;
          return {dup, sspAll, sspTot, nonSsp, fxUP, one};
        }""")
        print('[数据]', chk)
        assert chk['dup'] == 0, 'weapon_fx 存在重复词条'
        assert chk['sspAll'] == chk['sspTot'], 'SSP武器战意限制覆盖不全'
        assert chk['nonSsp'] >= 90, '普通武器战意限制(重抓新增)缺失'
        assert chk['fxUP'] >= 1500, '效果值UP覆盖异常'
        assert chk['one'] == 1, 'SSP武器效果值UP应恰好1条'

        # ---------- 1. 计算页: 角色角标 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '00强化模组'); pg.wait_for_timeout(700)
        pg.click("#pkl [data-pick='1370005950']"); pg.wait_for_timeout(3000)
        head = pg.evaluate("""() => {
          const rb = document.querySelector('#picku .roleb');
          return rb ? rb.className : '';
        }""")
        print('[计算 机体角标]', head)
        assert 'roleb def' in head, '计算页机体头像应有盾牌角标(该机体为耐久型)'
        rows = pg.evaluate("""() => [...document.querySelectorAll('#view .trow[data-pid]')].slice(0, 5).map(el => {
          const pid = +el.dataset.pid;
          const role = (q1('SELECT role FROM characters WHERE id=?', [pid]) || {}).role;
          const rb = el.querySelector('.roleb');
          return {pid, role, cls: rb ? rb.className : '', svg: rb ? (rb.querySelector('svg') ? 1 : 0) : 0};
        })""")
        print('[计算 TOP5]', rows)
        for r in rows:
            assert r['cls'], f"驾驶员 {r['pid']} 缺角标"
            want = {1: 'atk', 2: 'def', 3: 'sup'}[r['role']]
            assert r['cls'] == 'roleb ' + want, f"驾驶员 {r['pid']} 角标应为 {want}: {r['cls']}"
            assert r['svg'], '角标应含图标svg'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/36a_calc_roleb.png')

        # ---------- 2. 排行页: 机体+驾驶员 双角标 ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('#rlist .rrow'); pg.wait_for_timeout(3000)
        rk = pg.evaluate("""() => [...document.querySelectorAll('#rlist .rrow')].slice(0, 3).map(el => {
          const uid = +el.dataset.id;
          const role = (q1('SELECT role FROM units WHERE id=?', [uid]) || {}).role;
          const rbs = [...el.querySelectorAll('.roleb')];
          return {uid, role, cls: rbs.map(x => x.className)};
        })""")
        print('[排行 前3行]', rk)
        for r in rk:
            assert len(r['cls']) == 2, f"排行行应有2个角标: {r}"
            want = {1: 'atk', 2: 'def', 3: 'sup'}[r['role']]
            assert r['cls'][0] == 'roleb ' + want, f"排行机体角标应为 {want}: {r}"
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/36b_rank_roleb.png')

        # ---------- 3. 组队页: 行内双角标 + 防御目标卡 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow'); pg.wait_for_timeout(3500)
        n = pg.evaluate("() => document.querySelectorAll('#tarea .roleb').length")
        first = pg.evaluate("() => document.querySelectorAll('#tarea .card:first-child .roleb').length")
        print('[组队 角标总数]', n, '首卡', first)
        assert n >= 40 and first == 2, '组队行/最大伤害卡缺角标'
        pg.click('#dpick'); pg.wait_for_timeout(600)
        pg.fill('#pk', '独角兽高达'); pg.wait_for_timeout(600)
        pg.click('#pkl [data-dpick]'); pg.wait_for_timeout(800)
        pg.fill('#pk', ''); pg.wait_for_timeout(700)   # 清空搜索换选普通驾驶员(独角兽高达同名驾驶员=SD绑定的刘备，已被过滤)
        pg.click('#pkl [data-dpickc]'); pg.wait_for_timeout(2600)
        dico = pg.evaluate("() => [...document.querySelectorAll('#dpick .dico .roleb')].map(e => e.className)")
        print('[防御目标卡 角标]', dico)
        assert len(dico) == 2 and dico[0] == 'roleb atk', f'防御目标(独角兽高达=攻击型)角标异常: {dico}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/36c_team_roleb.png')

        # ---------- 4. 重抓新增数据: 普通武器战意限制 + 固有效果效果值UP ----------
        pg.evaluate("() => push({page:'weapon', title:'x', id:170500290002})")   # 连招 (非SSP, tension4)
        pg.wait_for_timeout(800)
        w1 = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        print('[连招]', w1[:120])
        assert '战意为超强势以上时即可使用' in w1, '连招应显示战意限制'
        pg.evaluate("() => push({page:'weapon', title:'x', id:102100010002})")   # 280010 固有効果武器
        pg.wait_for_timeout(800)
        w2 = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        print('[280010武器]', w2[:140])
        assert '武装效果的效果值UP(且最大值提升3%)' in w2, '280010武器应显示效果值UP'
        pg.evaluate("() => push({page:'weapon', title:'x', id:137000590090})")   # SSP 回归确认
        pg.wait_for_timeout(800)
        w3 = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        assert '武装效果的效果值UP(且最大值提升3%)' in w3 and '战意为超强势以上时即可使用' in w3, 'SSP武器数据回归失败'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/36d_weapon_lines.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
