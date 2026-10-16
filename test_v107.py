# -*- coding: utf-8 -*-
"""v107 验证: 防御侧被动按生效条件如实判定 + 战意「以上」阈值口径
① 攻击侧口径: 1069000150「战意为超强势以上时攻防+10%」 unitPassiveAtkPct 强势=0 / 超强势=10 / 超一击=10 / 条件被动开@强势=10
② 目标防御侧(如实判定): 组队目标=1069000150 → 技能防御%: ca开@无气势=10, ca关@无气势=0, ca关@超强势=10, ca关@超一击=10
③ 我方防御机(defUnits 受): 玫瑰高达(超级模式)1200000610「超强势以上时防御+10%」—
   同气势(无气势)下 ca关受 > ca开受(条件不成立被剔除); 超强势下 ca关受 = ca开受(条件成立如实计入)
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
PORT = 9015
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        # ① 攻击侧
        a = pg.evaluate("""() => ({ h: unitPassiveAtkPct(1069000150, 'high', false, null, false),
          m: unitPassiveAtkPct(1069000150, 'max', false, null, false), s: unitPassiveAtkPct(1069000150, 'supercharged', false, null, false),
          ca: unitPassiveAtkPct(1069000150, 'high', true, null, false) })""")
        print('[① 攻击侧 超强势以上+10%]', a)
        assert a == {'h': 0, 'm': 10, 's': 10, 'ca': 10}, a
        print('[① 战意「以上」阈值=最低档(强势0/超强势10) + 条件被动开假设满足 通过]')

        # ② 目标防御侧
        def tsk(ca, vig):
            pg.evaluate("""([ca, vig]) => { const t = state.team; t.dunit = 1069000150; t.dchar = null; t.guard = false; t.sdef = false;
              t.vigor = vig; t.ca = ca; state.stack = []; push({ page:'team', title:'组队' }); render(); }""", [ca, vig])
            pg.wait_for_timeout(2400)
            return pg.evaluate("""() => { const tx = document.getElementById('view').innerText; const m = tx.match(/技能防御\\s*\\+(\\d+)%/); return m ? +m[1] : 0; }""")
        v_ = {'onMid': tsk(True, 'mid'), 'offMid': tsk(False, 'mid'), 'offMax': tsk(False, 'max'), 'offSc': tsk(False, 'supercharged')}
        print('[② 目标防御侧 技能防御%]', v_)
        assert v_ == {'onMid': 10, 'offMid': 0, 'offMax': 10, 'offSc': 10}, v_
        print('[② 目标防御侧 条件被动关·按当前气势如实判定 通过]')

        # ③ 我方防御机受
        def recv_of(ca, vig):
            pg.evaluate("""([ca, vig]) => { const t = state.team; t.dunit = 1001000150; t.dchar = null; t.guard = false; t.sdef = false;
              t.vigor = vig; t.ca = ca; state.stack = []; push({ page:'team', title:'组队' }); render(); }""", [ca, vig])
            pg.wait_for_timeout(2600)
            return pg.evaluate("() => (state._recv || {})[1200000610] || null")
        r = {'onMid': recv_of(True, 'mid'), 'offMid': recv_of(False, 'mid'), 'offMax': recv_of(False, 'max'), 'onMax': recv_of(True, 'max')}
        print('[③ 我方防御机 玫瑰高达(超级模式) 受]', r)
        assert r['onMid'] and r['offMid'] and r['offMid'] > r['onMid'], r
        assert r['offMax'] == r['onMax'], r
        print('[③ 防御机 受: 条件关+气势不足→防御不生效(受更高); 超强势→如实计入(与假设满足一致) 通过]')

        assert not errors, errors
        print('=== test_v107 全部通过 ===')
        b.close()
finally:
    srv.terminate()
