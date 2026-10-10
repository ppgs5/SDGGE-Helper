# -*- coding: utf-8 -*-
"""v0.28 验证: 防御目标技能条件判定（搭乘单位标签不匹配时不生效; 敌方条件按攻击方标签逐行生效）"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8915
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

        # ---------- 0. 数据层: 条件判定 ----------
        chk = pg.evaluate("""() => {
          return {
            sf: defenderSkills(1330000150, 1001001800),      // 夏亚(自护公国军条件) × 突击自由(EX) → 不生效
            zeong: defenderSkills(1001003050, 1001001800),   // 夏亚 × 吉翁号(EX, 自护公国军) → -15%
            newZeong: defenderSkills(1001003050, 1110000200),// 新自护版夏亚 × 吉翁号(自护公国军≠新自护) → 0
            stack: defenderSkills(1095000350, null),         // 累计型"最高50%" → 50
            amuroX: defenderSkills(1330000150, 1001000100).x.length,   // 敌方条件规则存在
          };
        }""")
        print('[数据] redPct 突击自由:', chk['sf']['redPct'], '| 吉翁号:', chk['zeong']['redPct'],
              '| 新自护版×吉翁号:', chk['newZeong']['redPct'], '| 累计型def:', chk['stack']['defPct'], '| x规则:', chk['amuroX'])
        assert chk['sf']['redPct'] == 0, '夏亚减伤不应对突击自由生效'
        assert chk['zeong']['redPct'] == 15, '夏亚减伤应对自护公国军机体生效'
        assert chk['newZeong']['redPct'] == 0, '新自护条件不应匹配自护公国军机体'
        assert chk['stack']['defPct'] == 50, '累计型防御应为最高50%'
        assert chk['amuroX'] >= 1, '敌方条件规则应被记录'

        # ---------- 1. 组队页: 突击自由+夏亚 → 无减伤 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .trow'); pg.wait_for_timeout(3000)
        pg.click('#dpick'); pg.wait_for_timeout(600)
        pg.fill('#pk', '突击自由'); pg.wait_for_timeout(600)
        pg.click("#pkl [data-dpick='1330000150']"); pg.wait_for_timeout(900)
        pg.fill('#pk', '夏亚'); pg.wait_for_timeout(600)
        pg.click("#pkl [data-dpickc='1001001800']"); pg.wait_for_timeout(3000)
        card = pg.evaluate("() => document.getElementById('dpick').textContent.replace(/\\s+/g,' ')")
        note = pg.evaluate("""() => [...document.querySelectorAll('#view .hint')].map(e => e.textContent).find(t => t.indexOf('姿态-40%') >= 0) || ''""")
        print('[突击自由+夏亚]', card[:120])
        print('[提示行]', note)
        assert '夏亚' in card, '防御驾驶员应为夏亚'
        assert '承伤' not in card, '夏亚减伤不应显示在突击自由上'
        assert '技能减伤' not in note, '提示不应显示技能减伤'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/40a_sf_char.png')

        # ---------- 2. 切成吉翁号(EX) → 减伤生效 ----------
        pg.click('#dpick'); pg.wait_for_timeout(600)
        pg.fill('#pk', '吉翁号'); pg.wait_for_timeout(600)
        pg.click("#pkl [data-dpick='1001003050']"); pg.wait_for_timeout(3000)
        pg.click('#sx'); pg.wait_for_timeout(600)
        card2 = pg.evaluate("() => document.getElementById('dpick').textContent.replace(/\\s+/g,' ')")
        note2 = pg.evaluate("""() => [...document.querySelectorAll('#view .hint')].map(e => e.textContent).find(t => t.indexOf('姿态-40%') >= 0) || ''""")
        print('[吉翁号+夏亚]', card2[:120])
        print('[提示行2]', note2)
        assert '承伤-15%' in card2, '吉翁号(自护公国军)下夏亚减伤应生效'
        assert '技能减伤-15%' in note2, '提示应显示技能减伤-15%'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/40b_zeong_char.png')

        # ---------- 3. 最大伤害卡随攻击方标签变化(突击自由+夏亚): 伤害应比无减伤时高 ----------
        pg.click('#dpick'); pg.wait_for_timeout(600)
        pg.fill('#pk', '突击自由'); pg.wait_for_timeout(600)
        pg.click("#pkl [data-dpick='1330000150']"); pg.wait_for_timeout(3000)
        pg.click('#sx'); pg.wait_for_timeout(600)
        best = pg.evaluate("() => { const e = document.getElementById('tarea'); return e ? e.textContent.replace(/\\s+/g,' ').slice(0, 190) : '' }")
        print('[最大伤害卡]', best[:170])
        assert '承伤' not in best, '最大伤害卡不应含承伤'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
