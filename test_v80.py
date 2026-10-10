# -*- coding: utf-8 -*-
"""v0.80 验证: 组队 eHP 列表显示跟随星级/SP开关 + 新增「进攻盾 TOP5」
① eHP 行 耐久/防御 = defStat 口径(UR按★/非UR按SP+SSP+三星), 与机体页一致:
   ★3+舰(朗多贝尔队★0): 锡蒙力维达尔 耐久116,395·防御11,683·舰+30% (非★0原始83,140)
② 点★0 → 116,395 消失(该行掉出TOP10), SSR行(AGE-1)不受★影响 115,858·9,700(与用户截图一致); 点★3恢复
③ 进攻盾 TOP5: 5行, 驾驶员∈trait90七人且条件匹配机体(锡蒙力维达尔=朱莉塔/加拉尔号角; F91=安娜玛丽/SERIES F91; 00强化模组=冯恩/天人);
   条件chips无重复(TAG 加拉尔号角 非 ·加拉尔号角·加拉尔号角)
仅回归最新版(用户口径)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8980

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(120000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.evaluate("() => { state.team.suppId = 1125000250; state.team.shipStar = 0; state.stack = []; setTab('team'); }")
        pg.wait_for_timeout(4500)

        def snap():
            return pg.evaluate("""() => {
              const ehp = [...document.querySelectorAll('#tarea .card')].find(c => c.querySelector('h4') && c.querySelector('h4').textContent.includes('有效耐久 eHP'));
              const rows = [...ehp.querySelectorAll('.trow')].map(r => ({ id: +r.dataset.id, t: r.textContent.replace(/\\s+/g,' ') }));
              const sm = rows.find(x => x.t.includes('锡蒙力维达尔'));
              const age = rows.find(x => x.t.includes('AGE-1'));
              return { star: state.team.star, rows, sm: sm && sm.t, age: age && age.t, full: ehp.textContent };
            }""")

        # ① ★3
        s3 = snap()
        print('[① ★3]', s3['sm'])
        assert s3['star'] == 3 and s3['sm'] and '耐久 116,395 · 防御 11,683' in s3['sm'] and '舰+30%' in s3['sm'], s3['sm']
        assert s3['rows'][0]['id'] == 1430004850, s3['rows'][:2]
        # ② ★0
        pg.evaluate("() => document.querySelector('[data-tstar=\"0\"]').click()"); pg.wait_for_timeout(6000)
        s0 = snap()
        print('[② ★0] AGE-1:', s0['age'], '| 锡蒙力:', s0['sm'])
        assert s0['star'] == 0, s0['star']
        assert '116,395' not in s0['full'], '★0下不应再显示★3数值'
        assert s0['age'] and '耐久 115,858 · 防御 9,700' in s0['age'], s0['age']      # SSR按SP/SSP口径, 不受★影响
        # ③ 回★3
        pg.evaluate("() => document.querySelector('[data-tstar=\"3\"]').click()"); pg.wait_for_timeout(6000)
        s3b = snap()
        assert '耐久 116,395 · 防御 11,683' in (s3b['sm'] or ''), s3b['sm']
        print('[① ② ③ eHP显示跟随星级开关(UR★) / 非UR按SP+SSP] 通过')

        # ④ 进攻盾 TOP5
        cs = pg.evaluate("""() => {
          const c = [...document.querySelectorAll('#tarea .card')].find(x => x.querySelector('h4') && x.querySelector('h4').textContent.includes('进攻盾'));
          return c ? [...c.querySelectorAll('.trow')].map(r => r.textContent.replace(/\\s+/g,' ')) : null;
        }""")
        print('[④ 进攻盾 TOP5]')
        for x in cs: print('   ', x[:96])
        assert cs and len(cs) == 5, cs
        assert '锡蒙力维达尔' in cs[0] and '朱莉塔' in cs[0] and 'TAG 加拉尔号角' in cs[0] and '加拉尔号角·加拉尔号角' not in cs[0], cs[0]
        assert any('F91 (EX)' in x and '安娜玛丽' in x and 'SERIES 机动战士高达F91' in x for x in cs), cs
        assert any('冯恩' in x and 'TAG 天人' in x for x in cs), cs
        print('[④ 进攻盾TOP5(条件匹配+chips无重复)] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v80 全部通过 ===')
