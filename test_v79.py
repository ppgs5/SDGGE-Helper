# -*- coding: utf-8 -*-
"""v0.79 验证: 特性新增「进攻盾」分类 — 收集拥有「反击时支援防御」(trait 90)的驾驶员/机体
语义(能力desc): 搭乘单位含有「X」标签/系列时, 己方部队在对战中发动攻击并受到敌方反击时, 可(以)进行/参与支援防御
① 分类chip存在且可切换; 列表恰好7位: 克莉丝蒂娜·马坎基/安娜玛丽·布洛吉亚/安德鲁·巴尔特菲尔德/朱莉塔·朱里斯/剑士Z高达/冯恩·史帕克(EX角色能力)/斯莱塔·墨丘利(EX角色能力)
② 标准标注发动条件: 行内显示条件chips (TAG 奥布/加拉尔号角/SD高达/天人/GUND-ARM; SERIES 机动战士高达0080…/F91)
③ 行内展示能力名+desc; 点击跳转角色页; 默认稀有度降序
仅回归最新版(用户口径)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8979

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
        pg.evaluate("() => { state.featKind = 'counter_shield'; state.stack = []; setTab('feat'); }")
        pg.wait_for_timeout(1500)
        chips = pg.evaluate("() => [...document.querySelectorAll('.chip')].map(e => e.textContent)")
        assert '进攻盾' in chips, chips[:40]
        head = pg.evaluate("() => document.querySelector('#farea .subnote').textContent.replace(/\\s+/g,' ')")
        rows = pg.evaluate("""() => [...document.querySelectorAll('#farea .lrow')].map(e => ({
          t: e.dataset.t, id: +e.dataset.id,
          txt: e.textContent.replace(/\\s+/g,' '), chips: [...e.querySelectorAll('.tagx.cond')].map(x => x.textContent) }))""")
        print('[① 列表]', len(rows), '|', head[:60])
        names = [r['txt'] for r in rows]
        assert len(rows) == 7, names
        assert '7位' in head and '反击' in head, head
        for nm in ('克莉丝蒂娜', '安娜玛丽', '安德鲁·巴尔特菲尔德', '朱莉塔', '剑士Z高达', '冯恩·史帕克', '斯莱塔·墨丘利'):
            assert any(nm in t for t in names), (nm, names)
        assert all(r['t'] == 'char' for r in rows), rows
        print('[① 7位驾驶员全收集] 通过')
        # ② 条件 chips
        allch = [c for r in rows for c in r['chips']]
        print('[② 条件chips]', sorted(set(allch)))
        for kw in ('TAG 奥布', 'TAG 加拉尔号角', 'TAG SD高达', 'TAG 天人', 'TAG GUND-ARM', 'SERIES 机动战士高达0080 口袋中的战争', 'SERIES 机动战士高达F91'):
            assert any(kw in c for c in allch), (kw, allch)
        assert all('受到敌方反击时' in r['txt'] for r in rows), [r['txt'][:80] for r in rows]
        print('[② 标准标注发动条件(标签/系列) + desc] 通过')
        # ③ 跳转
        pg.evaluate("() => document.querySelector('#farea .lrow').click()")
        pg.wait_for_timeout(700)
        t = pg.evaluate("() => document.querySelector('#view').textContent")
        assert '角色' in t or '返回' in t, t[:120]
        print('[③ 行点击跳角色页] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v79 全部通过 ===')
