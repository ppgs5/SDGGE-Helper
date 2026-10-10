# -*- coding: utf-8 -*-
"""v0.52 验证: 标签弹窗新增 稀有度 + 攻击/防御(耐久)/支援类型 筛选, 覆盖全部机体与驾驶员筛选
(特性/图鉴/排行/组队/选择器) ①弹窗两行chips与页面行共享状态 ②应用后列表按稀有度/类型过滤(SQL交叉) ③清除复位"""
import subprocess, time
from playwright.sync_api import sync_playwright

PORT = 8994
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

        # ---------- ① 特性-有MP技能: 弹窗含稀有度+类型行 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow'); pg.wait_for_timeout(500)
        pg.click("[data-k='mp_skill']"); pg.wait_for_timeout(1200)
        pg.click('#ftag'); pg.wait_for_selector('#stlist')
        rows_ui = pg.evaluate("""() => ({
          rar: [...document.querySelectorAll('#sheetPanel [data-srar]')].map(e => e.textContent.trim()),
          role: [...document.querySelectorAll('#sheetPanel [data-srole]')].map(e => e.textContent.trim())})""")
        print('[弹窗行]', rows_ui)
        assert rows_ui['rar'] == ['全部', 'N', 'R', 'SR', 'SSR', 'UR'], rows_ui
        assert rows_ui['role'] == ['全部', '攻击型', '防御型', '支援型'], rows_ui   # 特性=驾驶员语境
        all_mp = pg.evaluate("() => [...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id)")
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/58a_tag_sheet_rr.png')
        # 类型=支援型 → 应用
        pg.click('#sheetPanel [data-srole="3"]'); pg.click('#sapply'); pg.wait_for_timeout(1000)
        chk = pg.evaluate("""() => ({ ids: [...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id),
          f: { rar: filt('feat').rar || null, role: filt('feat').role || null } })""")
        exp = set(all_mp) & set(r['id'] for r in pg.evaluate("() => q('SELECT id FROM characters WHERE role=3').map(r => ({id: r.id}))"))
        print('[特性 类型=支援型]', chk['f'], len(chk['ids']), 'vs exp', len(exp))
        assert chk['f']['role'] == 3 and set(chk['ids']) == exp and len(exp) > 0, f'类型筛选错误: {len(chk["ids"])} vs {len(exp)}'
        # 稀有度=SR(3) 叠加 → 与 SQL+MP判定 全量交叉
        pg.click('#ftag'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-srar="3"]'); pg.click('#sapply'); pg.wait_for_timeout(900)
        sr_chk = pg.evaluate("""() => ({
          ids: [...document.querySelectorAll('#farea .lrow')].map(e => +e.dataset.id),
          exp: q('SELECT id FROM characters WHERE rarity=3 AND role=3 AND COALESCE(is_playable,1)=1').map(r => r.id)
            .filter(id => charMpAbilOf(id, state.featPSpU).length || charMpSkillOf(id, state.featPSpU).length) })""")
        print('[特性 SR+支援] 行数', len(sr_chk['ids']), 'vs exp', len(sr_chk['exp']))
        assert set(sr_chk['ids']) == set(sr_chk['exp']) and len(sr_chk['exp']) > 0, f'SR+支援型交叉不符: {sr_chk}'
        # 清除 → 复位
        pg.click('#ftag'); pg.wait_for_selector('#stlist')
        pg.click('#sclear'); pg.click('#sapply'); pg.wait_for_timeout(900)
        chk2 = pg.evaluate("() => ({ n: document.querySelectorAll('#farea .lrow').length, f: { rar: filt('feat').rar || null, role: filt('feat').role || null } })")
        print('[特性 清除复位]', chk2)
        assert chk2['f']['rar'] is None and chk2['f']['role'] is None and chk2['n'] == len(all_mp), f'清除后应复位: {chk2}'

        # ---------- ② 图鉴-驾驶员: 弹窗与页面稀有度行共享状态 ----------
        pg.click('[data-tab="units"]'); pg.wait_for_timeout(400)
        pg.click('[data-k="char"]'); pg.wait_for_timeout(1000)
        pg.click('#tbtn'); pg.wait_for_selector('#stlist')
        rr = pg.evaluate("""() => ({ rar: [...document.querySelectorAll('#sheetPanel [data-srar]')].map(e => e.textContent.trim()),
          role: [...document.querySelectorAll('#sheetPanel [data-srole]')].map(e => e.textContent.trim()) })""")
        assert rr['role'] == ['全部', '攻击型', '防御型', '支援型'], f'驾驶员语境类型标签: {rr}'
        pg.click('#sheetPanel [data-srar="5"]'); pg.click('#sapply'); pg.wait_for_timeout(900)
        chk3 = pg.evaluate("""() => ({ rar: filt('char').rar,
          urOn: [...document.querySelectorAll('#rarf [data-krar]')].some(e => e.dataset.krar === '5' && e.classList.contains('on')),
          bad: [...document.querySelectorAll('#listarea .lrow')].filter(e => (q1('SELECT rarity FROM characters WHERE id=?', [+e.dataset.id]) || {}).rarity !== 5).length,
          n: document.querySelectorAll('#listarea .lrow').length })""")
        print('[图鉴 稀有度=UR 共享]', chk3)
        assert chk3['rar'] == 5 and chk3['urOn'] and chk3['bad'] == 0 and chk3['n'] > 0, f'图鉴稀有度应过滤且页面行同步打勾: {chk3}'
        # 类型=防御型 → 应用
        pg.click('#tbtn'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-srole="2"]'); pg.click('#sapply'); pg.wait_for_timeout(900)
        chk4 = pg.evaluate("""() => ({ role: filt('char').role, n: document.querySelectorAll('#listarea .lrow').length,
          bad: [...document.querySelectorAll('#listarea .lrow')].filter(e => (q1('SELECT role FROM characters WHERE id=?', [+e.dataset.id]) || {}).role !== 2).length })""")
        print('[图鉴 UR+防御型]', chk4)
        assert chk4['role'] == 2 and chk4['n'] > 0 and chk4['bad'] == 0, f'类型过滤错误: {chk4}'
        # 复位(用页面稀有度行清 + 弹窗类型清)
        pg.click('#rarf [data-krar="all"]'); pg.wait_for_timeout(400)
        pg.click('#tbtn'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-srole="all"]'); pg.click('#sapply'); pg.wait_for_timeout(600)

        # ---------- ③ 排行: 弹窗写 rankCfg 与页面行联动 ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('.rrow', timeout=180000); pg.wait_for_timeout(800)
        pg.click('#rtag'); pg.wait_for_selector('#stlist')
        rr3 = pg.evaluate("() => [...document.querySelectorAll('#sheetPanel [data-srole]')].map(e => e.textContent.trim())")
        assert rr3 == ['全部', '攻击型', '耐久型', '支援型'], f'排行(=机体语境)类型标签: {rr3}'
        pg.click('#sheetPanel [data-srole="1"]'); pg.click('#sapply')
        pg.wait_for_function("() => state.rankCfg.urole === 1 && document.querySelectorAll('#rlist .rrow').length > 0", timeout=300000)
        pg.wait_for_timeout(500)
        chk5 = pg.evaluate("""() => ({ n: document.querySelectorAll('#rlist .rrow').length,
          bad: [...document.querySelectorAll('#rlist .rrow')].slice(0, 20).filter(e => (q1('SELECT role FROM units WHERE id=?', [+e.dataset.id]) || {}).role !== 1).length,
          pageRow: [...document.querySelectorAll('#view [data-urole]')].filter(e => e.classList.contains('gold')).map(e => e.textContent.trim()) })""")
        print('[排行 类型=攻击型]', chk5)
        assert chk5['bad'] == 0 and chk5['n'] > 0 and chk5['pageRow'] == ['攻击型'], f'排行类型过滤/页面行联动错误: {chk5}'
        # 弹窗复位
        pg.click('#rtag'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-srole="all"]'); pg.click('#sapply')
        pg.wait_for_function("() => state.rankCfg.urole === null", timeout=120000)
        pg.wait_for_timeout(400)

        # ---------- ④ 计算选择器: 稀有度过滤 ----------
        pg.click('[data-tab="calc"]'); pg.wait_for_timeout(800)
        pg.evaluate("() => openCalcPicker()"); pg.wait_for_selector('#pfil')
        pg.click('#pfil'); pg.wait_for_selector('#stlist')
        hasr = pg.evaluate("() => document.querySelectorAll('#sheetPanel [data-srar]').length")
        assert hasr == 6, '选择器弹窗应有稀有度行'
        pg.click('#sheetPanel [data-srar="4"]'); pg.click('#sapply'); pg.wait_for_timeout(900)
        chk6 = pg.evaluate("""() => ({ f: filt('picku').rar, n: document.querySelectorAll('#pkl .trow2').length,
          bad: [...document.querySelectorAll('#pkl .trow2')].filter(e => (q1('SELECT rarity FROM units WHERE id=?', [+e.dataset.pick]) || {}).rarity !== 4).length })""")
        print('[选择器 稀有度=SSR]', chk6)
        assert chk6['f'] == 4 and chk6['n'] > 0 and chk6['bad'] == 0, f'选择器稀有度过滤错误: {chk6}'
        pg.click('#pfil'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-srar="all"]'); pg.click('#sapply'); pg.wait_for_timeout(600)
        pg.evaluate("() => closeSheet()")
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
