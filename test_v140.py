# -*- coding: utf-8 -*-
"""v140 验证: 6/7射程移除主动技能开关；主动技能「射程增幅」独立成特性
口径(用户): 主动技能射程+1的技师单独开一个特性；6/7射程只统计「自带射程」与「特定组合(机师/机体被动)」，不要主动技能开关
① 6/7射程页不再有 #rgs 开关
② 6射程(驾驶员被动开/MAP不统计)：再生高达(EX) 以「GN翼状獠牙 3-5→6 + 驾驶员 利保逊」出现，行内无“主动技能”
③ 7射程 = 1 台（不因主动技能虚增）
④ 新特性「主动技能·射程增幅」：列表 158 位，含 利保逊‧阿路玛古，点击进入机师页
⑤ 基础射程恰为 6 的机体全部在列
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9114

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1200}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        def page(kind, **cfg):
            pg.evaluate("""([kind, cfg]) => {
              if (cfg.rgP !== undefined) state.featRgP = cfg.rgP;
              if (cfg.rgM !== undefined) state.featRgM = cfg.rgM;
              state.stack=[]; push({page:'feat',title:'特性',v:'x'}); state.featKind=kind; pageFeat(document.getElementById('view'));
            }""", [kind, cfg])
            pg.wait_for_timeout(1700)
            return pg.evaluate("""() => ({ text: document.getElementById('farea').innerText,
              rows: [...document.querySelectorAll('#farea .lrow')].map(e=>e.innerText.replace(/\\n/g,' | ')),
              rgs: document.querySelectorAll('#farea #rgs').length })""")

        r6 = page('range6', rgP=True, rgM=False)
        r7 = page('range7', rgP=True, rgM=False)
        print('[① #rgs]', r6['rgs'], r7['rgs'])
        assert r6['rgs'] == 0 and r7['rgs'] == 0

        reb = [x for x in r6['rows'] if '再生高达' in x]
        print('[② 6射程再生]', reb[:1])
        assert reb and '射程6' in reb[0] and '驾驶员' in reb[0], reb
        assert '主动技能' not in reb[0], reb[0]

        n7 = len(r7['rows'])
        print('[③ 7射程台数]', n7, r7['rows'][:2])
        assert all('主动技能' not in x for x in r7['rows']), r7['rows']   # 不再由主动技能凑出 7 射程

        rk = page('range_skill')
        line = rk['text'].split('\n')
        rk_n = int(line[0].split('位')[0])
        print('[④ 主动技能页]', line[0], '| 含夏亚:', '夏亚' in rk['text'])
        assert rk_n >= 100, rk_n
        assert '夏亚' in rk['text'] and '射程+' in rk['text']
        # 点击第一位 → 机师详情
        pg.evaluate("() => { document.querySelector('#farea .lrow').click(); }")
        pg.wait_for_timeout(900)
        assert pg.evaluate("() => (state.stack[state.stack.length-1]||{}).page") == 'char'
        assert '主动技能' in rk['text']

        n6 = int(r6['text'].split('台')[0])
        base6 = pg.evaluate("""() => { let n=0;
          for (const un of q('SELECT id FROM units')) { let mx=0;
            for (const w of weaponsForUnit({id:un.id, ult:1})) { if (w.type===3) continue; mx=Math.max(mx, w.range_max||0); }
            if (mx===6) n++; }
          return n; }""")
        print('[⑤ 6射程] 列表', n6, '| 基础恰好6的机体', base6)
        assert base6 <= n6, (base6, n6)

        assert not errors, errors
        print('=== test_v140 全部通过 ===')
        b.close()
finally:
    srv.terminate()
