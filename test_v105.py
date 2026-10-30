# -*- coding: utf-8 -*-
"""v0.105 更新流程回归:
   A. 计算页点「更新」必须在 60 秒内完成(不再永久「更新中」), 且完成后 dirty=false / 签名一致
   B. 组队页改开关后, 点「一次」更新就必须清掉提示(dirty=false, 无「设置已改动」)
   C. Worker 池被破坏(模拟设备内存不足)时, 更新仍能在超时后结束, 不会卡死
"""
import subprocess, time, sys
from playwright.sync_api import sync_playwright
PORT = 9160
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
FAIL = []
def check(name, ok, detail=''):
    print(('  ✅ ' if ok else '  ❌ ') + name + ('' if ok else '  ' + str(detail)))
    if not ok: FAIL.append(name)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(900000)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("window.Android={dbInfo:()=>'{}',listPatches:()=>[]};")
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(1500)

        # A. 计算页更新
        pg.evaluate("""() => { const u = q1("SELECT id FROM units WHERE name LIKE '无限正义高达 (EX)%' LIMIT 1");
            state.stack = []; setTab('calc'); state.calc.unitId = u.id; state.calc.charId = 1330001804; render(); }""")
        pg.wait_for_timeout(8000)
        pg.evaluate("() => { state.team.atkup = 106; markRankDirty(); render(); }")
        pg.wait_for_timeout(400)
        t0 = time.time()
        pg.evaluate("() => document.getElementById('btnupd').click()")
        try:
            pg.wait_for_function("() => !state._parRunning && !rankDirtyNow()", timeout=60000)
            okA = True; el = time.time() - t0
        except Exception:
            okA = False; el = -1
        check(f'A 计算页更新 60s 内完成(实际 {el:.1f}s)' if el > 0 else 'A 计算页更新 60s 内完成', okA)

        # B. 组队页一次点击清提示
        pg.evaluate("() => { state.stack = []; setTab('team'); }")
        pg.wait_for_timeout(1500)
        pg.evaluate("() => { const e = [...document.querySelectorAll('[data-rg]')].find(x => x.dataset.rg === '5'); if (e) e.click(); }")
        pg.wait_for_timeout(400)
        dirtyBefore = pg.evaluate("() => rankDirtyNow()")
        pg.evaluate("() => document.getElementById('btnupd').click()")
        try:
            pg.wait_for_function("() => !state._parRunning && !rankDirtyNow()", timeout=60000)
            okB = dirtyBefore and True
        except Exception:
            okB = False
        hintLeft = pg.evaluate("() => /设置已改动/.test(document.getElementById('view').innerText)")
        check('B 组队页一次点击后提示消失', okB and not hintLeft, {'dirtyBefore': dirtyBefore, 'hintLeft': hintLeft})

        # C. 破坏 Worker 池后仍能结束
        pg.evaluate("() => { try { (window.__pool || []).forEach(w => w.terminate()); } catch(e) {} window.__pool = []; }")
        pg.evaluate("() => { state.team.atkup = 90; markRankDirty(); render(); }")
        pg.wait_for_timeout(400)
        t1 = time.time()
        pg.evaluate("() => document.getElementById('btnupd').click()")
        try:
            pg.wait_for_function("() => !state._parRunning", timeout=120000)
            okC = True; elC = time.time() - t1
        except Exception:
            okC = False; elC = -1
        check(f'C Worker 池被破坏后仍能结束(实际 {elC:.1f}s)' if elC > 0 else 'C Worker 池被破坏后仍能结束', okC)
        # C2. 失败后必须仍有组队数据(单线程兜底), 且状态回到「已更新」
        st = pg.evaluate("() => ({ cache: !!state.teamCache, n: state.teamCache ? state.teamCache.G.main.length : 0, dirty: rankDirtyNow() })")
        check('C2 兜底后仍对账有数据且无「有改动」', st['cache'] and st['n'] > 0 and not st['dirty'], st)
        print('errors:', errs[:1])
        b.close()
finally:
    srv.terminate()
print('\n' + ('=== test_v105 通过 ===' if not FAIL else f'=== 失败: {FAIL} ==='))
sys.exit(0 if not FAIL else 1)
