# -*- coding: utf-8 -*-
"""v0.101 验证: 默认设置下「计算页」与「组队页」对同一机体+机师+武器的伤害是否一致(对账口径回归)"""
import subprocess, time, sys
from playwright.sync_api import sync_playwright
PORT = 9060
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errs = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(240000)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("window.Android={dbInfo:()=>'{}',listPatches:()=>'[]'};")
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(1500)

        # 默认设置: 组队页先算一次
        pg.evaluate("() => { state.stack=[]; setTab('team'); render(); }")
        pg.wait_for_timeout(9000)
        row = pg.evaluate("""() => {
            const G = state.teamCache && state.teamCache.G; if (!G) return null;
            const r = (G.main || [])[0]; if (!r) return null;
            return { uid: r.unitId, u: r.unit.name, pilot: r.pilot.name, pid: r.pilot.id,
                     weapon: r.weapon.name, wid: r.weapon.id, dmg: r.dmg, uAtk: r.uAtk,
                     ee: r.ee, defReduce: r.defReduce, vigor: r.vigor };
        }""")
        assert row, '组队无数据'
        print('[组队]', row['u'], '+', row['pilot'], '|', row['weapon'], '| 伤害', row['dmg'],
              '| 攻击', row['uAtk'], '| 增伤', row['ee'], '| 减伤', row['defReduce'])

        # 计算页: 同机体 + 同机师
        pg.evaluate("""(a) => { state.stack=[]; setTab('calc'); state.calc.unitId=a.uid; state.calc.charId=a.pid; render(); }""", row)
        pg.wait_for_timeout(9000)
        calc = pg.evaluate("""(a) => {
            const t = document.querySelector('.ctable'); if (!t) return null;
            const tr = [...t.querySelectorAll('tr')].find(x => x.dataset.wid === String(a.wid));
            const plain = [...t.querySelectorAll('tr')].find(x => x.innerText.includes(a.weapon));
            const el = tr || plain; if (!el) return null;
            const tds = [...el.querySelectorAll('td')]; return { dmg: tds[1] ? tds[1].innerText.trim() : null };
        }""", row)
        print('[计算]', row['weapon'], '| 伤害', calc['dmg'] if calc else '未找到')
        assert calc and calc['dmg'], '计算页未找到该武器行'

        # 计算页口径(气势/增伤/减伤)从页面文本抓取
        txt = pg.evaluate("() => document.getElementById('view').innerText")
        import re as _re
        mv = _re.search(r'气势[^\n]*?增伤\+(\d+)%', txt)
        mr = _re.search(r'减伤\s*(\d+)%', txt)
        print('[计算口径] 增伤', mv.group(1) if mv else '?', '| 减伤', mr.group(1) if mr else '?')
        print('[组队口径] 增伤', row['ee'], '| 减伤', row['defReduce'], '| 气势', row['vigor'])
        c = int(calc['dmg'].replace(',', ''))
        t = int(str(row['dmg']).replace(',', ''))
        diff = abs(c - t) / max(1, t)
        print(f'[对比] 组队 {t:,} vs 计算 {c:,} → 差异 {diff*100:.2f}%')
        assert diff < 0.02, f'两页差异过大: {diff*100:.1f}%'
        print('=== test_v101 通过（默认设置两页一致）===')
        b.close()
    assert not errs, errs[:2]
finally:
    srv.terminate()
