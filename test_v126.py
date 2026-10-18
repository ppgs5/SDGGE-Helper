# -*- coding: utf-8 -*-
"""v126 验证: 「第一击损伤无效」通用标记
口径(用户): 只做标记, 伤害照常计算; 不限 ULT 机体(其他机体有此技能同样标记)
① DB: features(feature='first_hit_immune') = 2 条 → 1163000150 高达F91(双V.S.B.R.装备)(EX)、1308000502 ULT机体
② 特性页「第一击损伤无效」分类可见, 列出这两台
③ 详情页仍展示各自单位技能原文(伤害计算不受影响)
④ 高速/射程增幅未计入(无 first_hit 之外的改动): ULT 能力里 10/18 不产生任何 feature
"""
import os, subprocess, time, sqlite3
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9070
DB = os.path.join(HERE, 'data', 'ggen.db')

c = sqlite3.connect(DB)
rows = c.execute("SELECT target_id FROM features WHERE feature='first_hit_immune' ORDER BY target_id").fetchall()
ids = [r[0] for r in rows]
print('[① DB]', ids)
assert ids == [1163000150, 1308000502], ids
assert c.execute("SELECT COUNT(*) FROM features WHERE feature='first_hit_immune'").fetchone()[0] == 2

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        # ② 特性页
        pg.evaluate("() => { state.stack=[]; push({page:'feat',title:'特性',v:'x'}); state.featKind='first_hit_immune'; pageFeat(document.getElementById('view')); }")
        pg.wait_for_timeout(900)
        t = pg.evaluate("() => document.getElementById('farea').innerText")
        print('[② 特性页]', t[:200].replace('\n', ' | '))
        assert '第一击损伤无效' in t and '高达F91' in t and '2条' in t, t[:400]

        # ③ 详情
        pg.evaluate("() => { state.stack=[]; push({page:'unit',title:'x',id:1308000502}); render(); }")
        pg.wait_for_timeout(700)
        d = pg.evaluate("() => document.getElementById('view').innerText")
        assert '第一击损伤无效' in d, d[:500]
        print('[③ 详情] 含单位技能文本 ok')

        # ④ 高速/射程增幅未建模(ULT trait 10/18 不生成 feature)
        n = pg.evaluate("() => q(\"SELECT COUNT(*) n FROM features WHERE feature IN ('high_speed','range_boost_ult')\")[0].n")
        print('[④ 高速/射程未计入]', n)
        assert n == 0
        assert not errors, errors
        print('=== test_v126 全部通过 ===')
        b.close()
finally:
    srv.terminate()
