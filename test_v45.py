# -*- coding: utf-8 -*-
"""v0.46 验证: ①回到顶/底按钮+列表选中保持滚动 ②机体页 原配驾驶员/最高伤害驾驶员(小头像) ③详情页标签点击跳图鉴筛选 ④组队舰增益绿框高亮+夜莺可见 ⑤驾驶员小头像稀有度角标缩小"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8997
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
        pg.wait_for_timeout(700)
        print('[boot] ok')

        # ---------- ① 回到顶/底按钮 + 滚动保持 ----------
        fab = pg.evaluate("""() => {
          const v = document.getElementById('view');
          const f = v.querySelector(':scope > .listfab');
          return {has: !!f, display: f ? f.style.display : null};
        }""")
        print('[主视图 FAB]', fab)
        assert fab['has'] and fab['display'] == 'flex', f'主视图应有回到顶/底按钮: {fab}'
        pg.evaluate("() => document.getElementById('view').scrollTo({top: 400})")
        pg.click('#view .listfab [data-fab="top"]'); pg.wait_for_timeout(700)
        assert pg.evaluate("() => document.getElementById('view').scrollTop") < 40, '回顶失效'
        pg.click('#view .listfab [data-fab="bottom"]'); pg.wait_for_timeout(900)
        assert pg.evaluate("() => { const v = document.getElementById('view'); return v.scrollTop > v.scrollHeight - v.clientHeight - 60; }"), '回底失效'
        pg.evaluate("() => document.getElementById('view').scrollTo({top: 0})")
        # 标签弹窗: 选中保持滚动
        pg.click('#tbtn'); pg.wait_for_selector('#stlist')
        sfab = pg.evaluate("() => !!document.querySelector('#sheetPanel .tlist > .listfab')")
        assert sfab, '弹窗列表应有回到顶/底按钮'
        sc = pg.evaluate("""() => {
          const l = document.getElementById('stlist');
          l.scrollTop = 300;
          document.querySelectorAll('#stlist [data-id]')[20].click();
          return {after: document.getElementById('stlist').scrollTop, on: document.querySelectorAll('#stlist .ck.on').length};
        }""")
        print('[标签选中保持滚动]', sc)
        assert sc['after'] == 300 and sc['on'] == 1, f'选中后应保持滚动位置: {sc}'
        pg.evaluate("() => closeSheet()")

        # ---------- ② 机体页 原配/最高伤害 驾驶员 ----------
        pg.evaluate("() => push({page:'unit', title:'x', id:1001000150})"); pg.wait_for_timeout(3000)
        chk = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#ubb .trow')].map(r => ({
            nm: r.querySelector('.nm').textContent.replace(/\\s+/g,' '),
            dmg: r.querySelector('.val').textContent,
            w: r.querySelector('.avw img') ? r.querySelector('.avw img').getBoundingClientRect().width : 0,
            badge: r.querySelector('.rarb') ? r.querySelector('.rarb').textContent : '',
          }));
          return rows;
        }""")
        print('[高达EX 驾驶员]', [(r['nm'][:18], r['dmg'], r['badge']) for r in chk])
        assert len(chk) == 2, f'应有 原配+最高伤害 两行: {chk}'
        assert '原配驾驶员' in chk[0]['nm'] and '阿姆罗·雷' in chk[0]['nm'] and chk[0]['dmg'] != '—', f'原配行错误: {chk[0]}'
        assert '最高伤害' in chk[1]['nm'], f'最高伤害行错误: {chk[1]}'
        assert all(r['w'] < 60 for r in chk), f'头像不应过大: {chk}'

        # ---------- ③ 详情页标签跳转 ----------
        pg.evaluate("() => push({page:'unit', title:'x', id:1144000550})"); pg.wait_for_timeout(1200)
        chips = pg.evaluate("() => [...document.querySelectorAll('#view .dhead .chip[data-gotag]')].length")
        assert chips > 0, '机体页标签应可点击'
        pg.evaluate("() => document.querySelector('#view .dhead .chip[data-gotag]').click()")
        pg.wait_for_timeout(1000)
        out = pg.evaluate("""() => ({tab: state.tab, kind: state.unitKind, tags: state.zoom.unit.tags.slice(),
          n: document.querySelectorAll('#listarea .ucard').length})""")
        print('[标签跳转]', out)
        assert out['tab'] == 'units' and out['kind'] == 'unit' and len(out['tags']) == 1 and out['n'] > 0, f'跳转错误: {out}'
        bad = pg.evaluate("""(tid) => [...document.querySelectorAll('#listarea .ucard')].filter(el =>
            !q('SELECT 1 FROM unit_tags WHERE unit_id=? AND tag_id=?', [+el.dataset.id, tid]).length).length""", out['tags'][0])
        assert bad == 0, '跳转结果应全为该标签机体'
        # 驾驶员页
        pg.evaluate("() => { state.zoom.unit.tags = []; push({page:'char', title:'x', id:1001000100}); }"); pg.wait_for_timeout(1200)
        pg.evaluate("() => document.querySelector('#view .dhead .chip[data-gotag]').click()")
        pg.wait_for_timeout(1000)
        out2 = pg.evaluate("() => ({kind: state.unitKind, tags: state.zoom.char.tags.slice(), n: document.querySelectorAll('#listarea .lrow').length})")
        print('[驾驶员标签跳转]', out2)
        assert out2['kind'] == 'char' and len(out2['tags']) == 1 and out2['n'] > 0, f'驾驶员标签跳转错误: {out2}'
        bad2 = pg.evaluate("""(tid) => [...document.querySelectorAll('#listarea .lrow')].filter(el =>
            !q('SELECT 1 FROM char_tags WHERE char_id=? AND tag_id=?', [+el.dataset.id, tid]).length).length""", out2['tags'][0])
        assert bad2 == 0, '驾驶员跳转结果应全为该标签'
        pg.evaluate("() => { state.zoom.char.tags = []; }")

        # ---------- ④ 队伍增强弹窗: 被战舰加成的机体绿框(排行不标) ----------
        pg.click('[data-tab="team"]'); pg.wait_for_timeout(1200)
        pg.evaluate("""() => {
          const sup = q1("SELECT * FROM supporters WHERE name LIKE '%永恒号%' AND name LIKE '%拉克丝%'");
          state.team.suppId = sup.id; pageTeam(document.querySelector('#view'));
        }""")
        pg.wait_for_timeout(6000)
        chk4 = pg.evaluate("""() => {
          const hl = document.querySelectorAll('#tarea .trow.hl').length;
          const secs = [...document.querySelectorAll('#tarea .card h4')].map(h => h.textContent.trim());
          return {hl, hasShipSec: secs.some(t => t.includes('战舰加成机体'))};
        }""")
        print('[伤害排行不标绿框]', chk4)
        assert chk4['hl'] == 0 and not chk4['hasShipSec'], f'伤害排行不应有绿框: {chk4}'
        pg.click('#tbuff'); pg.wait_for_selector('#pk', timeout=15000); pg.wait_for_timeout(800)
        tb = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#sheetPanel .trow2[data-g]')];
          const exp = {};
          const sup = q1('SELECT * FROM supporters WHERE id=?', [state.team.suppId]);
          const ship = shipEffOf(sup, state.team.shipStar || 0);
          const isHl = g => { const uid = g.isChar ? (g.reqInfo && g.reqInfo[0] ? g.reqInfo[0].id : null) : +g.target_id;
            return !!(uid && shipMatch(ship, metaOf(uid))); };
          const groups = {}; teamBuffGroups().forEach(g => groups[g.key] = g);
          return rows.map(el => ({txt: el.textContent.replace(/\\s+/g,' ').slice(0, 20),
                                  hl: el.classList.contains('hl'),
                                  exp: isHl(groups[el.dataset.g])}));
        }""")
        print('[队伍增强弹窗] 绿框', sum(1 for r in tb if r['hl']), '/', len(tb))
        for r in tb[:8]: print('   ', '✔' if r['hl'] else ' ', r['txt'])
        assert sum(1 for r in tb if r['hl']) > 0, '应有被战舰加成的条目绿框'
        assert all(r['hl'] == r['exp'] for r in tb), f'绿框应与战舰匹配一致: {[r for r in tb if r["hl"] != r["exp"]]}'
        pg.evaluate("() => closeSheet()")

        # ---------- ⑤ 小头像稀有度角标缩小 ----------
        sz = pg.evaluate("""() => {
          const el = document.querySelector('#tarea .avw.avsm .rarb');
          if (!el) return null;
          const cs = getComputedStyle(el);
          return {fs: cs.fontSize, lh: cs.lineHeight};
        }""")
        print('[小头像角标]', sz)
        assert sz and sz['fs'] == '6px', f'驾驶员小头像角标应为6px: {sz}'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
