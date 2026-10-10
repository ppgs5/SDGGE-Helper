# -*- coding: utf-8 -*-
"""v0.26 验证: SD绑定驾驶员不能驾驶其他机体(组队防御目标/计算页选驾驶员过滤 + 失效自动清除)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8905
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

        # ---------- 0. 前置: 刘备独角兽高达 是 SD 绑定驾驶员 ----------
        bind = pg.evaluate("() => { const m = sdCharMap(); return m[1725000100] ? [...m[1725000100]] : null }")
        print('[SD绑定]', bind)
        assert bind and 1725000150 in bind, '刘备独角兽高达 应绑定 SD 机体 1725000150'

        # 全量检查: 每个SD绑定驾驶员 → 自己机体全部放行、任选普通机体全部拦截
        allchk = pg.evaluate("""() => {
          const m = sdCharMap();
          const sample = q1("SELECT u.id FROM units u WHERE u.id NOT IN (SELECT ut.unit_id FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE t.name='SD高达') LIMIT 1").id;
          const bad = [];
          let n = 0;
          for (const k in m) {
            n++;
            if (pilotCanDrive(+k, sample)) bad.push([+k, 'foreign-allow']);
            for (const uid of m[k]) if (!pilotCanDrive(+k, uid)) bad.push([+k, 'own-deny', uid]);
          }
          return {n, bad, sample};
        }""")
        print('[全SD驾驶员检查]', allchk)
        assert allchk['n'] >= 40 and not allchk['bad'], f'SD绑定校验异常: {allchk}'

        # ---------- 1. 组队: 选 SD 机体 刘备独角兽高达(EX) → 自动带出专属驾驶员并被允许 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow'); pg.wait_for_timeout(3000)
        pg.click('#dpick'); pg.wait_for_timeout(600)
        pg.fill('#pk', '刘备'); pg.wait_for_timeout(600)
        pg.click("#pkl [data-dpick='1725000150']"); pg.wait_for_timeout(900)
        d1 = pg.evaluate("() => state.team.dchar")
        own = pg.evaluate("() => !!document.querySelector(\"#pkl [data-dpickc='1725000100']\")")
        print('[SD机体] dchar=', d1, '专属驾驶员在列表:', own)
        assert d1 == 1725000100, 'SD机体应自动带出绑定驾驶员'
        assert own, 'SD机体下应允许其专属驾驶员'
        pg.click('#sx'); pg.wait_for_timeout(700)
        card1 = pg.evaluate("() => document.getElementById('dpick').textContent.replace(/\\s+/g,' ')")
        assert '刘备独角兽高达' in card1, '防御目标卡应显示专属驾驶员'

        # ---------- 2. 组队: 切回普通机体 独角兽高达 → 绑定驾驶员被清除且列表不可选 ----------
        pg.click('#dpick'); pg.wait_for_timeout(600)
        pg.fill('#pk', '独角兽高达'); pg.wait_for_timeout(600)
        pg.click("#pkl [data-dpick='1125000100']"); pg.wait_for_timeout(900)
        d2 = pg.evaluate("() => state.team.dchar")
        bad = pg.evaluate("() => !!document.querySelector(\"#pkl [data-dpickc='1725000100']\")")
        print('[切机体后] dchar=', d2, '刘备仍在列表:', bad)
        assert d2 is None, '切换机体后 SD 绑定驾驶员应被清除'
        assert not bad, '普通机体下不应出现 SD 绑定驾驶员'
        pg.fill('#pk', '刘备'); pg.wait_for_timeout(700)
        bad2 = pg.evaluate("() => document.querySelectorAll('#pkl [data-dpickc]').length")
        print('[搜索刘备] 结果数:', bad2)
        assert bad2 == 0, '搜索也不应出现 SD 绑定驾驶员'
        pg.fill('#pk', '阿姆罗'); pg.wait_for_timeout(700)
        ok2 = pg.evaluate("() => document.querySelectorAll('#pkl [data-dpickc]').length")
        assert ok2 > 0, '普通驾驶员应正常列出(对照组)'
        pg.click('#sx'); pg.wait_for_timeout(700)
        card2 = pg.evaluate("() => document.getElementById('dpick').textContent.replace(/\\s+/g,' ')")
        print('[防御目标卡]', card2[:90])
        assert '刘备独角兽高达' not in card2, '防御目标卡不应再显示 SD 绑定驾驶员'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/37a_team_sd_clear.png')

        # ---------- 3. 计算页: 普通机体下驾驶员列表过滤 SD 绑定驾驶员 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(300)
        pg.click('#picku'); pg.fill('#pk', '独角兽高达'); pg.wait_for_timeout(600)
        pg.click("#pkl [data-pick='1125000100']"); pg.wait_for_timeout(800)
        pg.click('#picku'); pg.wait_for_timeout(400)
        pg.click('#wchar'); pg.wait_for_timeout(400)
        pg.fill('#pk', '刘备'); pg.wait_for_timeout(700)
        n = pg.evaluate("() => document.querySelectorAll('#pkl [data-pickc]').length")
        print('[计算页 搜索刘备] 结果数:', n)
        assert n == 0, '计算页普通机体不应列出 SD 绑定驾驶员'

        # ---------- 4. 计算页: SD 机体下专属驾驶员可选 ----------
        pg.click('#wunit'); pg.wait_for_timeout(300)
        pg.fill('#pk', '刘备'); pg.wait_for_timeout(600)
        pg.click("#pkl [data-pick='1725000150']"); pg.wait_for_timeout(800)
        pg.click('#picku'); pg.wait_for_timeout(400)
        pg.click('#wchar'); pg.wait_for_timeout(400)
        pg.fill('#pk', '刘备'); pg.wait_for_timeout(700)
        own2 = pg.evaluate("() => !!document.querySelector(\"#pkl [data-pickc='1725000100']\")")
        print('[计算页 SD机体] 专属驾驶员在列表:', own2)
        assert own2, 'SD机体下应允许其专属驾驶员'
        pg.click("#pkl [data-pickc='1725000100']"); pg.wait_for_timeout(1500)
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/37b_calc_sd_own.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
