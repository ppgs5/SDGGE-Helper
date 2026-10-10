# -*- coding: utf-8 -*-
"""v0.84 验证: 组队页新增「驾驶员标签/系列」筛选(picker 新语境 teamp), 作用于四个排行榜的驾驶员候选池
口径与计算页 pickc 一致: 标签按名称集合(mode=or 任一命中 / and 全部命中; 标签+系列 or=并集), 系列经 charSeriesMap
弹窗的稀有度/类型行与页面「驾驶员稀有度/类型」芯片同源(state.team.prar/prole)
① 按钮存在; 弹窗含 标签/作品系列 seg + 稀有度/类型行
② 标签=新人类(任一命中) → 各榜驾驶员全部含该标签(且不同于基线)
③ 系列 → 驾驶员 charSeriesMap 全部命中
④ 标签+系列 任一命中 → 并集(标签或系列)
⑤ 弹窗稀有度=UR → state.team.prar=5 + 页面芯片同步; 清除恢复基线
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8984

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

        TAG = pg.evaluate("() => (q1(\"SELECT id FROM tags WHERE name='新人类'\") || {}).id")
        SID = pg.evaluate("() => (q1(\"SELECT id FROM series WHERE name='机动战士高达'\") || {}).id")
        print('[准备] 新人类 tag =', TAG, '| 机动战士高达 series =', SID)
        assert TAG and SID

        pg.evaluate("""() => { window.__caps = []; const orig = buildRanking;
          buildRanking = function(f, cfg, P){ const r = orig(f, cfg, P);
            window.__caps.push({ rows: ['main','sup','def'].flatMap(k => (r[k]||[]).map(x => ({ pid: x.pilot.id, name: x.pilot.name, uid: x.unitId }))) }); return r; }; }""")

        def team(mut=''):
            pg.evaluate(f"() => {{ {mut} state.team.suppId = null; state.stack = []; window.__caps = []; setTab('team'); }}")
            pg.wait_for_timeout(6500)
            return pg.evaluate("() => (window.__caps || []).pop()")

        # ① 按钮与弹窗结构
        cap = team()
        btn = pg.evaluate("() => { const el = document.querySelector('#ttagp'); return el ? el.textContent.replace(/\\s+/g,' ') : null; }")
        print('[① 按钮]', btn)
        assert btn and '驾驶员' in btn, btn
        pg.evaluate("() => document.querySelector('#ttagp').click()")
        pg.wait_for_timeout(1200)
        struct = pg.evaluate("""() => ({ seg: [...document.querySelectorAll('#sheetPanel [data-lm]')].map(e => e.textContent),
          rr: !!document.querySelector('#sheetPanel [data-srar]') && !!document.querySelector('#sheetPanel [data-srole]'),
          n: document.querySelectorAll('#sheetPanel .trow2, #sheetPanel .trow').length })""")
        print('[① 弹窗]', struct)
        assert struct['seg'] == ['标签', '作品系列'] and struct['rr'] and struct['n'] > 0, struct
        base_pids = {x['pid'] for x in cap['rows']}
        print('[① 弹窗结构(标签/系列seg+稀有度/类型)] 通过')

        # ② 标签=新人类 任一命中
        pg.evaluate(f"""() => {{ const rows = [...document.querySelectorAll('#sheetPanel .trow2')];
          const el = rows.find(e => e.textContent.includes('新人类')); if (el) el.click();
          document.querySelector('#sheetPanel [data-m=\"or\"]').click(); }}""")
        pg.wait_for_timeout(600)
        pg.evaluate("() => document.querySelector('#sapply').click()")
        pg.wait_for_timeout(6500)
        cap = pg.evaluate("() => (window.__caps || []).pop()")
        pids = sorted({x['pid'] for x in cap['rows']})
        ok = pg.evaluate(f"() => {pids}.every(id => charMetaOf(id).tags.has('新人类'))")
        print('[② 标签筛后驾驶员数]', len(pids), '全含新人类:', ok, '| 有别于基线:', len(pids) != len(base_pids))
        assert ok and pids and set(pids) != base_pids, (len(pids), ok)
        assert len(pids) < len(base_pids), (len(pids), len(base_pids))
        btn = pg.evaluate("() => document.querySelector('#ttagp').textContent.replace(/\\s+/g,' ')")
        assert '1' in btn, btn
        print('[② 驾驶员标签筛选(新人类) 通过]')

        # ③ 系列筛(清除标签→选系列)
        pg.evaluate("() => document.querySelector('#ttagp').click()")
        pg.wait_for_timeout(1000)
        pg.evaluate("() => { document.querySelector('#sheetPanel [data-lm=\"series\"]').click(); }")
        pg.wait_for_timeout(600)
        pg.evaluate("() => document.querySelector('#sheetPanel #sclear').click()")
        pg.wait_for_timeout(400)
        pg.evaluate(f"""() => {{ const rows = [...document.querySelectorAll('#sheetPanel .trow2')];
          const el = rows.find(e => +e.dataset.sid === {SID}); if (el) el.click(); }}""")
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.querySelector('#sapply').click()")
        pg.wait_for_timeout(6500)
        cap = pg.evaluate("() => (window.__caps || []).pop()")
        pids = sorted({x['pid'] for x in cap['rows']})
        ok3 = pg.evaluate(f"() => {pids}.every(id => String(charSeriesMap()[String(q1('SELECT series_set_id FROM characters WHERE id=?', [id]).series_set_id)]) === '{SID}')")
        print('[③ 系列筛后驾驶员数]', len(pids), '全命中系列:', ok3)
        assert ok3 and pids, (len(pids), ok3)
        print('[③ 驾驶员系列筛选 通过]')

        # ④ 标签+系列 任一命中 = 并集
        pg.evaluate("() => document.querySelector('#ttagp').click()")
        pg.wait_for_timeout(1000)
        pg.evaluate("() => document.querySelector('#sheetPanel [data-lm=\"tag\"]').click()")
        pg.wait_for_timeout(400)
        pg.evaluate(f"""() => {{ const rows = [...document.querySelectorAll('#sheetPanel .trow2')];
          const el = rows.find(e => e.textContent.includes('新人类')); if (el) el.click();
          document.querySelector('#sheetPanel [data-m=\"or\"]').click(); }}""")
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#sapply').click()")
        pg.wait_for_timeout(6500)
        cap = pg.evaluate("() => (window.__caps || []).pop()")
        pids = sorted({x['pid'] for x in cap['rows']})
        ok4 = pg.evaluate(f"""() => {pids}.every(id => charMetaOf(id).tags.has('新人类') ||
          String(charSeriesMap()[String(q1('SELECT series_set_id FROM characters WHERE id=?', [id]).series_set_id)]) === '{SID}')""")
        some_tag = pg.evaluate(f"() => {pids}.some(id => charMetaOf(id).tags.has('新人类'))")
        some_ser = pg.evaluate(f"() => {pids}.some(id => String(charSeriesMap()[String(q1('SELECT series_set_id FROM characters WHERE id=?', [id]).series_set_id)]) === '{SID}' && !charMetaOf(id).tags.has('新人类'))")
        print('[④ 任一命中] n=', len(pids), '全部属于并集:', ok4, '| 含标签侧:', some_tag, '含系列侧:', some_ser)
        assert ok4 and some_tag and some_ser, (ok4, some_tag, some_ser)
        print('[④ 标签+系列 任一命中(并集) 通过]')

        # ⑤ 全部排行榜候选池: eHP「支防+2」推荐 + 进攻盾 TOP5 同受筛选(仅标签=新人类)
        pg.evaluate("() => document.querySelector('#ttagp').click()")
        pg.wait_for_timeout(1000)
        pg.evaluate("() => document.querySelector('#sheetPanel #sclear').click()")
        pg.wait_for_timeout(300)
        pg.evaluate("""() => { const rows = [...document.querySelectorAll('#sheetPanel .trow2')];
          const el = rows.find(e => e.textContent.includes('新人类')); if (el) el.click();
          document.querySelector('#sheetPanel [data-m="or"]').click(); }""")
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#sapply').click()")
        pg.wait_for_timeout(6500)
        r5 = pg.evaluate("""() => { const cards = [...document.querySelectorAll('#tarea .card')];
          const ehp = cards.find(c => c.querySelector('h4') && c.querySelector('h4').textContent.includes('有效耐久 eHP'));
          const cs = cards.find(c => c.querySelector('h4') && c.querySelector('h4').textContent.includes('进攻盾'));
          const sdefs = ehp ? [...ehp.querySelectorAll('.trow[data-sdef]')].map(e => +e.dataset.sdef) : [];
          return { sdefs, csRows: cs ? cs.querySelectorAll('.trow').length : -1,
            sdefOk: sdefs.every(id => charMetaOf(id).tags.has('新人类')),
            csAll: counterShieldDrivers().length,
            csNewtype: counterShieldDrivers().filter(d => charMetaOf(d.id).tags.has('新人类')).length }; }""")
        print('[⑤ 池筛选]', r5)
        assert r5['sdefOk'], r5['sdefs']
        if r5['csNewtype'] == 0:
            assert r5['csRows'] == 0, r5          # 无新人类 trait90 持有者 → 进攻盾无行
        else:
            assert r5['csRows'] > 0, r5
        print('[⑤ eHP支防推荐/进攻盾候选池同受筛选] 通过')

        # ⑥ 弹窗稀有度=UR 与页面芯片同步; 清除恢复基线
        pg.evaluate("() => document.querySelector('#ttagp').click()")
        pg.wait_for_timeout(1000)
        pg.evaluate("() => { document.querySelector('#sheetPanel #sclear').click(); document.querySelector('#sheetPanel [data-srar=\"5\"]').click(); }")
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#sapply').click()")
        pg.wait_for_timeout(6500)
        st = pg.evaluate("() => ({ prar: state.team.prar, chip: [...document.querySelectorAll('[data-tprar]')].filter(e => e.className.includes('gold') || e.className.includes('on')).map(e => e.textContent) })")
        cap = pg.evaluate("() => (window.__caps || []).pop()")
        pids = sorted({x['pid'] for x in cap['rows']})
        ok5 = pg.evaluate(f"() => {pids}.every(id => q1('SELECT rarity FROM characters WHERE id=?', [id]).rarity === 5)")
        print('[⑤ UR 弹窗→页面芯片]', st, '司机全UR:', ok5)
        assert st['prar'] == 5 and st['chip'] == ['UR'] and ok5, (st, ok5)
        pg.evaluate("() => document.querySelector('#ttagp').click()")
        pg.wait_for_timeout(1000)
        pg.evaluate("() => { document.querySelector('#sheetPanel #sclear').click(); }")
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#sapply').click()")
        pg.wait_for_timeout(6500)
        cap = pg.evaluate("() => (window.__caps || []).pop()")
        pids = {x['pid'] for x in cap['rows']}
        assert pids == base_pids, (len(pids), len(base_pids))
        btn = pg.evaluate("() => document.querySelector('#ttagp').textContent.replace(/\\s+/g,' ')")
        assert not any(c.isdigit() for c in btn), btn
        print('[⑥ 稀有度同步 + 清除恢复基线] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v84 全部通过 ===')
