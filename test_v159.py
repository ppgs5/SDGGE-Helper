# -*- coding: utf-8 -*-
"""v159 验证: 计算页选定目标机体后与组队同口径 + 距离被动标注
① 选目标机体(高达EX+阿姆罗, 全能力106%, 支援防御)时, 计算页 神高达EX+多蒙 洗牌同盟拳 = 262,547（与组队一致）
② 页面标注「已选目标机体：实际防御 24,698 / 守备 704 / 减伤 75%」
③ 距离条件被动在攻击力下方标注「距离≤1 攻击+20%」
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9187

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1600}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        pg.evaluate("""() => { const c=state.calc, t=state.team;
          c.unitId=1200003950; c.charId=1200000103; c.ca=false; c.first=true; c.allup=106; c.tDef=10000;
          t.defup=106; t.tDef=0; t.guard=false; t.sdef=true; t.dunit=1001000150; t.dchar=1001000100;
          state._prKey=null; state.stack=[]; push({page:'calc',title:'计算'}); render(); }""")
        pg.wait_for_timeout(2200)
        r = pg.evaluate("""() => { const t=document.getElementById('view').innerText;
          const tr=[...document.querySelectorAll('#view table.ctable tr')].find(x=>x.innerText.includes('洗牌同盟拳'));
          const dmg = tr ? +[...tr.querySelectorAll('td')][2].innerText.replace(/,/g,'') : null;
          return { dmg, sub: (t.match(/已选目标机体[^\\n]*/)||[''])[0], dist: t.includes('距离被动') }; }""")
        print('[① 伤害/② 标注]', r['dmg'], '|', r['sub'][:60])
        assert r['dmg'] == 262547, r['dmg']
        assert '24,698' in r['sub'] and '704' in r['sub'] and '75%' in r['sub'], r['sub']

        pg.evaluate("""() => { const c=state.calc; c.unitId=1376000300; c.charId=null; c.ca=false; c.first=false;
          state.stack=[]; push({page:'calc',title:'计算'}); render(); }""")
        pg.wait_for_timeout(1600)
        d = pg.evaluate("""() => { const t=document.getElementById('view').innerText; const m=t.match(/距离被动：([^\\n（]*)/); return m?m[1]:''; }""")
        print('[③ 距离被动]', d)
        assert '距离≤1' in d and '攻击+20%' in d, d

        assert not errors, errors
        print('=== test_v159 全部通过 ===')
        b.close()
finally:
    srv.terminate()
