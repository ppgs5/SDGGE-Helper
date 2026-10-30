# -*- coding: utf-8 -*-
"""v0.106 候选池 K 的正确性断言:
   K=300 时 TOP10 必须与全量一致; K=120 已知会改变 TOP10(因此禁止在默认路径使用)
"""
import subprocess, time, sys
from playwright.sync_api import sync_playwright
PORT = 9173
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
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(2500)
        r = pg.evaluate("""async () => {
            const t = state.team, f = filt('team');
            const top = async K => (await teamRankChunked(t, f, null, K)).main.slice(0, 10).map(x => x.unit.name + '|' + x.pilot.name);
            const full = await top(0), k300 = await top(300), k120 = await top(120);
            return { same300: JSON.stringify(full) === JSON.stringify(k300),
                     same120: JSON.stringify(full) === JSON.stringify(k120),
                     top1: full[0], k120top1: k120[0] };
        }""")
        check('K=300 的 TOP10 与全量一致', r['same300'], r['top1'])
        # 说明: 早前「K=120 改变 TOP10」实为「先分片后过滤」的顺序 bug; 修复后 K=120/200/300 的 TOP10 均与全量一致
        check('K=120 的 TOP10 也与全量一致(顺序 bug 修复后)', r['same120'], {'full': r['top1'], 'k120': r['k120top1']})
        print('errors:', errs[:1])
        b.close()
finally:
    srv.terminate()
print('\n' + ('=== test_v106 通过 ===' if not FAIL else f'=== 失败: {FAIL} ==='))
sys.exit(0 if not FAIL else 1)
