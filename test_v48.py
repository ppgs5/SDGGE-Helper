# -*- coding: utf-8 -*-
"""v0.48 验证: ①排行筛选行拆分: 武器属性/类型/稀有度各占一行(标签不再悬挂) ②组队新增武器属性/类型筛选(接入计算) ③ULT固定★0与SSP/数值提示合并为一行"""
import subprocess, time
from playwright.sync_api import sync_playwright

PORT = 8991
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

        # ---------- ①排行: 筛选分行 + 提示合并 ----------
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('.rrow', timeout=180000); pg.wait_for_timeout(1500)
        geo = pg.evaluate("""() => {
          const H = t => [...document.querySelectorAll('#view .hint')].find(h => h.textContent.trim() === t);
          const R = el => el.getBoundingClientRect();
          const watL = H('武器属性:'), tyL = H('类型:'), rarL = H('稀有度:'), urL = H('机体类型:');
          const watA = document.querySelector('#view [data-wat="all"]'), atkA = document.querySelector('#view [data-atk="all"]');
          const rarA = document.querySelector('#view [data-rar="all"]'), urA = document.querySelector('#view [data-urole="all"]');
          const top = el => Math.round(R(el).top);
          const same = (a, b) => Math.abs((R(a).top + R(a).bottom) / 2 - (R(b).top + R(b).bottom) / 2) < 6;   // 标签 align-self:center → 比中心
          return {all: !!(watL && tyL && rarL && urL && watA && atkA && rarA && urA),
                  watSame: same(watL, watA), atkSame: same(tyL, atkA),
                  rarSame: same(rarL, rarA), urSame: same(urL, urA),
                  tyBelowWat: top(tyL) > R(watA).bottom - 2, rarBelowUr: top(rarL) > R(urA).bottom - 2};
        }""")
        print('[排行 筛选分行]', geo)
        assert geo['all'], '排行页面缺少 武器属性/类型/机体类型/稀有度 标签或chips'
        assert geo['watSame'] and geo['atkSame'] and geo['rarSame'] and geo['urSame'], f'标签应与各自chips同行: {geo}'
        assert geo['tyBelowWat'] and geo['rarBelowUr'], f'类型/稀有度应各占新行(标签不再悬挂上一行): {geo}'
        hint = pg.evaluate("""() => {
          const hs = [...document.querySelectorAll('#view .hint')].map(h => h.textContent);
          const ult = hs.filter(t => t.includes('ULT固定★0'));
          return {n: ult.length, txt: ult[0] || '', extra: hs.filter(t => t.includes('仅作用于SSR') && !t.includes('ULT固定★0')).length};
        }""")
        print('[排行 提示行]', hint)
        assert hint['n'] == 1 and 'SSR及以下按★3' in hint['txt'] and '数值/武器' in hint['txt'] and hint['extra'] == 0, f'排行提示应合并为一行: {hint}'

        # 功能: 武器属性=光束 → 全部行为光束武器; 再叠加 类型=格斗
        pg.click('#view [data-wat="光束"]')
        pg.wait_for_function("""() => { const w = [...document.querySelectorAll('#rlist .rrow .wattr')]; return w.length > 0 && w.every(e => e.textContent.includes('光束')); }""", timeout=300000)
        ok1 = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#rlist .rrow')];
          const wids = rows.map(el => +el.dataset.wid);
          return {n: rows.length, attrTxt: rows.every(el => (el.querySelector('.wattr') || {}).textContent.includes('光束')),
                  sql: wids.every(w => (AATTR[q1('SELECT weapon_attr FROM weapons WHERE id=?', [w]).weapon_attr] || '').includes('光束'))};
        }""")
        print('[排行 武器属性=光束]', ok1)
        assert ok1['n'] > 0 and ok1['attrTxt'] and ok1['sql'], f'光束筛选错误: {ok1}'
        pg.click('#view [data-atk="melee"]')
        pg.wait_for_function("""() => { const rows = [...document.querySelectorAll('#rlist .rrow')]; return rows.length > 0 && rows.every(el => { const w = q1('SELECT attack_attr FROM weapons WHERE id=?', [+el.dataset.wid]); return (WATTR[w.attack_attr] || ['melee']).includes('melee'); }); }""", timeout=300000)
        ok2 = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#rlist .rrow')];
          const wids = rows.map(el => +el.dataset.wid);
          return {n: rows.length, melee: wids.every(w => (WATTR[q1('SELECT attack_attr FROM weapons WHERE id=?', [w]).attack_attr] || ['melee']).includes('melee')),
                  beam: wids.every(w => (AATTR[q1('SELECT weapon_attr FROM weapons WHERE id=?', [w]).weapon_attr] || '').includes('光束'))};
        }""")
        print('[排行 类型=格斗(叠加光束)]', ok2)
        assert ok2['n'] > 0 and ok2['melee'] and ok2['beam'], f'格斗筛选错误: {ok2}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/54a_rank_filters.png')

        # ---------- ②组队: 新增武器属性/类型 + 提示合并 ----------
        pg.click('[data-tab="team"]'); pg.wait_for_selector('#tarea .card'); pg.wait_for_timeout(4000)
        geo2 = pg.evaluate("""() => {
          const H = t => [...document.querySelectorAll('#view .hint')].find(h => h.textContent.trim() === t);
          const R = el => el.getBoundingClientRect();
          const watL = H('武器属性:'), tyL = H('类型:');
          const watA = document.querySelector('#view [data-twat="all"]'), atkA = document.querySelector('#view [data-tatk="all"]');
          const rgA = document.querySelector('#view [data-rg="all"]');
          const top = el => el ? Math.round(R(el).top) : -1;
          const same = (a, b) => a && b && Math.abs((R(a).top + R(a).bottom) / 2 - (R(b).top + R(b).bottom) / 2) < 6;
          return {all: !!(watL && tyL && watA && atkA && rgA),
                  watSame: same(watL, watA), atkSame: same(tyL, atkA),
                  watBelowRg: top(watL) > R(rgA).bottom - 2, tyBelowWat: top(tyL) > R(watA).bottom - 2,
                  nWat: document.querySelectorAll('#view [data-twat]').length, nAtk: document.querySelectorAll('#view [data-tatk]').length};
        }""")
        print('[组队 新增筛选]', geo2)
        assert geo2['all'] and geo2['nWat'] == 4 and geo2['nAtk'] == 4, f'组队应有武器属性/类型筛选(各4项): {geo2}'
        assert geo2['watSame'] and geo2['atkSame'] and geo2['watBelowRg'] and geo2['tyBelowWat'], f'组队筛选行布局错误: {geo2}'
        hint2 = pg.evaluate("""() => {
          const hs = [...document.querySelectorAll('#view .hint')].map(h => h.textContent);
          const ult = hs.filter(t => t.includes('ULT固定★0'));
          return {n: ult.length, txt: ult[0] || '', extra: hs.filter(t => t.includes('SSP武器仅在SSP开时参与') && !t.includes('ULT固定★0')).length};
        }""")
        print('[组队 提示行]', hint2)
        assert hint2['n'] == 1 and 'SSR及以下按★3' in hint2['txt'] and 'SSP武器仅在SSP开时参与' in hint2['txt'] and hint2['extra'] == 0, f'组队提示应合并为一行: {hint2}'

        # 功能: 武器属性=光束 + 类型=格斗 → 攻击TOP10 生效(与页面同管线重算对比)
        pg.click('#view [data-twat="光束"]')
        pg.wait_for_function("""() => { if (state.team.wat !== '光束') return false;
          const cs = document.querySelectorAll('#tarea .card'); if (cs.length < 2) return false;
          const rows = [...cs[1].querySelectorAll('.trow')]; if (!rows.length) return false;
          return rows.every(el => { const s = [...el.querySelectorAll('small span')].find(x => (x.getAttribute('style') || '').includes('8fc4ff')); return s && s.textContent.includes('光束'); }); }""", timeout=300000)
        pg.click('#view [data-tatk="melee"]')
        pg.wait_for_function("() => state.team.atk === 'melee'", timeout=120000)
        pg.wait_for_timeout(500)
        chk = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#tarea .card')[1].querySelectorAll('.trow')];
          const domIds = rows.map(el => +el.dataset.id);
          const spans = rows.map(el => { const s = [...el.querySelectorAll('small span')].find(x => (x.getAttribute('style') || '').includes('8fc4ff')); return s ? s.textContent : ''; });
          const t = state.team; const f = filt('team');
          const G = buildRanking(f, { targetDef: (t.tdef ?? 10000), targetCharDef: (t.tcdef ?? 750), vigor: 'mid', crit: false, range: t.range, rarity: t.rar || null, wat: t.wat || null, atk: t.atk || null },
            { passive: true, cpassive: true, skills: !!t.skills, condAll: !!t.ca, autoVigor: true, multiPhase: !!t.mp, star: t.star ?? 3, spU: t.spU !== false, sspU: t.sspU !== false, pilotGroups: { main: t.prole || null, sup: 3, def: 2 } });
          const atk = G.main.filter(r => r.unit.role === 1).slice(0, 10);
          return {n: rows.length, domIds, expIds: atk.map(r => r.unitId),
                  beamTxt: spans.every(s => s.includes('光束')),
                  melee: atk.every(r => (WATTR[r.weapon.attack_attr] || ['melee']).includes('melee') && (AATTR[r.weapon.weapon_attr] || '').includes('光束')),
                  state: {wat: t.wat, atk: t.atk}};
        }""")
        print('[组队 光束+格斗]', {k: chk[k] for k in ('n', 'domIds', 'expIds', 'beamTxt', 'melee', 'state')})
        assert chk['n'] > 0 and chk['beamTxt'], f'组队武器属性筛选未生效: {chk}'
        assert chk['domIds'] == chk['expIds'], f'组队结果与同管线重算不一致(atk未接入?): {chk}'
        assert chk['melee'], f'组队类型筛选语义错误: {chk}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/54b_team_filters.png')
        # 复位
        pg.click('#view [data-twat="all"]'); pg.wait_for_timeout(300)
        pg.click('#view [data-tatk="all"]'); pg.wait_for_timeout(500)
        st = pg.evaluate("() => ({wat: state.team.wat, atk: state.team.atk})")
        print('[组队 复位]', st)
        assert st['wat'] is None and st['atk'] is None, f'复位后应为全部: {st}'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
