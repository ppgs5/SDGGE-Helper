# -*- coding: utf-8 -*-
"""v0.40 验证: SSP强化移动力+1(游戏面板实测) — 7移动出现(支援防御移动可达7: SSP+1 + 卡特吉娜+1)"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8975
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

        # ---------- 0. 数据层 ----------
        chk = pg.evaluate("""() => {
          const get = (tid, feat) => {
            const r = q1('SELECT params_json FROM features WHERE feature=? AND target_id=?', [feat, tid]);
            return r ? JSON.parse(r.params_json) : null;
          };
          const r7rows = q("SELECT params_json FROM features WHERE feature='move7'", []).map(r => JSON.parse(r.params_json));
          return {
            n6: q("SELECT COUNT(*) c FROM features WHERE feature='move6'", [])[0].c,
            n7: q("SELECT COUNT(*) c FROM features WHERE feature='move7'", [])[0].c,
            kata7: r7rows.filter(p => p.pilot === 1175000500).length,
            konoe6: get(1175004910, 'move6'),   // 近卫师团用里格·夏柯: SSP 5→6 无驾驶员
            konoe7: get(1175004910, 'move7'),   // +卡特吉娜 → 7
            kyo7: get(1017000900, 'move7'),     // 京宝梵: 机体被动+SSP → 7 无驾驶员
            bing6: get(1370005900, 'move6'),    // 00R(SSP): 5→6 无驾驶员
          };
        }""")
        print('[数据]', {k: v for k, v in chk.items()})
        assert chk['n6'] == 270 and chk['n7'] == 13, f"6/7移动计数: {chk['n6']}/{chk['n7']}"
        assert chk['kata7'] == 13, f'卡特吉娜7移动行应为13: {chk["kata7"]}'
        assert chk['konoe6'] and chk['konoe6']['pilot'] == 0 and chk['konoe6']['total'] == 6, '里格·夏柯 SSP应到6(无驾驶员)'
        assert chk['konoe7'] and chk['konoe7']['pilot'] == 1175000500 and chk['konoe7']['total'] == 7, '里格·夏柯+卡特吉娜应到7'
        assert chk['kyo7'] is None, '京宝梵SSP无移动加成, 不应有7移动行'
        assert chk['bing6'] is None, '00R SSP无移动加成, 不应有移动行'

        # ---------- 1. 机体页: 移动 随SSP开关 +1 ----------
        pg.evaluate("() => push({page:'unit', title:'x', id:1370005900})"); pg.wait_for_timeout(800)
        def mov():
            return pg.evaluate("() => document.querySelector('#view .statgrid .stat:nth-child(6)').textContent.replace(/\\s+/g,' ')")
        m0 = mov()
        print('[00R 默认移动]', m0)
        assert m0.startswith('移动5'), f'默认移动应为5: {m0}'
        pg.click('#usp'); pg.wait_for_timeout(600)
        pg.click('#uss'); pg.wait_for_timeout(700)
        m1 = mov()
        print('[SSP开 移动]', m1)
        assert '移动5' in m1 and '原' not in m1, f'00R SSP无移动加成, 应仍为5: {m1}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/49a_unit_mov_ssp.png')

        # ---------- 2. 特性页 7移动 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow'); pg.wait_for_timeout(600)
        pg.click("[data-k='move7']"); pg.wait_for_timeout(1200)
        head = pg.evaluate("() => document.querySelector('#farea .subnote').textContent")
        print('[7移动]', head)
        assert '共 13 条' in head, '7移动应共13条'
        rows = pg.evaluate("""() => [...document.querySelectorAll('#farea .lrow')].map(el => ({
            name: el.querySelector('.nm').textContent.replace(/\\s+/g,' ').slice(0, 22),
            pip: !!el.querySelector('.picon'),
        }))""")
        konoe = [r for r in rows if '里格·夏柯' in r['name']]
        print('[里格·夏柯行]', konoe)
        assert konoe and konoe[0]['pip'], '里格·夏柯7移动行应显示卡特吉娜头像'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/49b_move7.png')

        # ---------- 3. 武器条件效果扩展检查: 防御力减少+3% / 武装POWER最大值+3% 类 ----------
        chk4 = pg.evaluate("""() => {
          const zion = metaOf(1001003050);      // 吉翁号(EX): 吉翁公国军
          const sf = metaOf(1330000150);        // 突击自由: 无
          const t9 = (wid, em, ca) => wTraitsOf(wid, em, ca).filter(t => t.trait_type === 9).map(t => t.trait_value).sort((a,b)=>a-b);
          const p82 = (wid, em, ca) => wTraitsOf(wid, em, ca).filter(t => t.trait_type === 82).map(t => t.trait_value).sort((a,b)=>a-b);
          // 卡特吉娜的移动只在渣斯卡路标签机体出现
          const rowsAll = q("SELECT f.feature, f.target_id, f.params_json FROM features f WHERE f.feature IN ('move6','move7')", []);
          const kata = rowsAll.map(r => ({tid: r.target_id, p: JSON.parse(r.params_json).pilot})).filter(x => x.p === 1175000500);
          const badTag = kata.filter(x => !q("SELECT 1 FROM unit_tags WHERE unit_id=? AND tag_id=1087", [x.tid]).length).length;
          return {
            t119off: t9(100700116004, null, false), t119on: t9(100700116004, null, true),
            t119zion: t9(100700116004, zion, false), t119sf: t9(100700116004, sf, false),
            p090off: p82(100700116090, null, false), p090zion: p82(100700116090, zion, false), p090sf: p82(100700116090, sf, false),
            kataN: kata.length, badTag,
          };
        }""")
        print('[武器条件扩展]', chk4)
        assert len(chk4['t119off']) == 5 and len(chk4['t119on']) == 10, '360mm加农炮: 条件关5行/开10行'
        assert len(chk4['t119zion']) == 10 and len(chk4['t119sf']) == 5, '360mm加农炮对吉翁含条件-3行, 对无标签不含'
        assert len(chk4['p090off']) == 18 and len(chk4['p090zion']) == 27, '360mmSSP: 功率条件+3行对吉翁才计'
        assert len(chk4['p090sf']) == 18, '360mmSSP对无标签不含条件+3'
        assert chk4['kataN'] > 0 and chk4['badTag'] == 0, '卡特吉娜的移动只应出现在渣斯卡路标签机体'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
