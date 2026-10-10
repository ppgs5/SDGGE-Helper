# -*- coding: utf-8 -*-
"""v0.45 验证: ①所有头像处显示稀有度角标 ②系列筛选打钩显示 ③队伍增强/队友对自身增强 固定搭配双头像 ④队伍增强机体条目标注与战舰对得上的标签 ⑤组队页战舰增益机体高亮"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8985
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

        # ---------- ① 稀有度角标 ----------
        # 计算页选择器(机体/驾驶员)
        pg.evaluate("() => openCalcPicker()"); pg.wait_for_selector('#pk')
        chk = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#pkl .trow2')].slice(0, 10);
          return {n: rows.length, badges: rows.filter(el => el.querySelector('.rarb')).length,
                  txt: (rows[0] && rows[0].querySelector('.rarb')) ? rows[0].querySelector('.rarb').textContent : ''};
        }""")
        print('[选择器-机体] 稀有度角标', chk)
        assert chk['n'] > 0 and chk['badges'] == chk['n'] and chk['txt'], f'选择器机体应全部带稀有度角标: {chk}'
        pg.evaluate("() => openCalcPicker(); state.calcPickWhich='char'")   # 切驾驶员
        pg.evaluate("() => openCalcPicker()"); pg.wait_for_timeout(400)
        chk2 = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#pkl .trow2')].slice(0, 10);
          return {n: rows.length, badges: rows.filter(el => el.querySelector('.rarb')).length};
        }""")
        print('[选择器-驾驶员]', chk2)
        assert chk2['n'] > 0 and chk2['badges'] == chk2['n'], f'选择器驾驶员应全部带角标: {chk2}'
        pg.evaluate("() => closeSheet()")

        # 排行行: 机体+驾驶员角标
        pg.click('[data-tab="rank"]'); pg.wait_for_selector('.rrow', timeout=180000); pg.wait_for_timeout(1000)
        chk3 = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#rlist .rrow')].slice(0, 5);
          return {n: rows.length, uB: rows.filter(el => el.querySelector('.ricon .rarb')).length,
                  pB: rows.filter(el => el.querySelector('.avw.avp .rarb')).length,
                  pRole: rows.filter(el => el.querySelector('.avw.avp .roleb')).length};
        }""")
        print('[排行行] 机体角标/驾驶员角标/驾驶员类型角标', chk3)
        assert chk3['n'] > 0 and chk3['uB'] == chk3['n'] and chk3['pB'] == chk3['n'] and chk3['pRole'] == chk3['n'], f'排行行角标缺失: {chk3}'

        # ---------- ② 系列筛选打钩 ----------
        pg.click('#rtag'); pg.wait_for_selector('#stlist')
        pg.click('#sheetPanel [data-lm="series"]'); pg.wait_for_timeout(400)
        pg.click('#sheetPanel [data-sid]'); pg.wait_for_timeout(400)
        chk4 = pg.evaluate("""() => ({
          on: document.querySelectorAll('#stlist .ck.on').length,
          foot: document.querySelector('#sapply').textContent.replace(/\\s+/g,' '),
          chips: document.querySelectorAll('#sheetPanel .tchip2').length,
        })""")
        print('[系列打钩]', chk4)
        assert chk4['on'] == 1, f'选中1个系列应有1个打钩: {chk4}'
        assert '+ 1 系列' in chk4['foot'] and chk4['chips'] == 1, f'底部应显示系列chip: {chk4}'
        pg.click('#sheetPanel [data-sid] >> nth=1'); pg.wait_for_timeout(300)
        on2 = pg.evaluate("() => document.querySelectorAll('#stlist .ck.on').length")
        assert on2 == 2, f'选中2个系列应有2个打钩: {on2}'
        # 应用后: 筛选已生效(状态+按钮计数)
        pg.click('#sapply'); pg.wait_for_timeout(1500)
        chk4b = pg.evaluate("""() => ({sel: (state.zoom.rank.series || []).length,
          btn: document.querySelector('#rtag').textContent.replace(/\\s+/g,' ')})""")
        print('[系列应用]', chk4b)
        assert chk4b['sel'] == 2 and '2' in chk4b['btn'], f'应用后应保留2个系列: {chk4b}'

        # ---------- ③④ 特性页 队伍增强 / 队友对自身增强 ----------
        pg.evaluate("() => { state.zoom.rank.series=[]; state.rankCache=null; }")
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow'); pg.wait_for_timeout(600)
        pg.click("[data-k='team_buff']"); pg.wait_for_timeout(900)
        chk5 = pg.evaluate("""() => {
          const rows = [...document.querySelectorAll('#farea .lrow')].map(el => ({
            nm: el.querySelector('.nm').textContent.replace(/\\s+/g,' ').slice(0, 40),
            pipe: el.querySelectorAll('.ticon-col .avw').length,   // 主头像+副头像
            badges: el.querySelectorAll('.rarb').length,
            shipTags: (el.querySelector('small') || {}).textContent || '',
          }));
          return {n: rows.length, rows: rows.slice(0, 12).filter(r => /\\(乘 /.test(r.nm) || r.pipe > 1 || /战舰标签/.test(r.shipTags))};
        }""")
        print('[队伍增强] 组数', chk5['n'])
        for r in chk5['rows'][:6]:
            print('   ', r['nm'][:26], '| 头像数', r['pipe'], '| 角标', r['badges'], '| 战舰标签' if '战舰标签' in r['shipTags'] else '')
        # 夏亚(乘夜莺) → 两个头像
        xia = pg.evaluate("""() => {
          const el = [...document.querySelectorAll('#farea .lrow')].find(x => x.textContent.includes('夏亚') && x.textContent.includes('夜莺'));
          return el ? {imgs: el.querySelectorAll('.ticon-col img').length, badges: el.querySelectorAll('.rarb').length} : null;
        }""")
        print('[夏亚×夜莺]', xia)
        assert xia and xia['imgs'] == 2 and xia['badges'] == 2, f'固定搭配应显示机体+驾驶员头像(含角标): {xia}'
        # 机体来源条目带战舰标签行(与 SQL 交集一致)
        chk6 = pg.evaluate("""() => {
          const st = new Set(q('SELECT DISTINCT name FROM supporter_tags').map(r => r.name));
          const rows = [...document.querySelectorAll('#farea .lrow')].filter(el => el.dataset.t === 'unit');
          const out = [];
          for (const el of rows) {
            const uid = +el.dataset.id;
            const tags = q('SELECT t.name n FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE ut.unit_id=?', [uid]).map(r => r.n).filter(x => st.has(x));
            const txt = el.querySelector('small').textContent;
            const shown = (txt.match(/战舰标签: (.*)/) || [])[1];
            out.push({uid, exp: tags.join(' · '), shown: shown || ''});
          }
          return out;
        }""")
        print('[机体条目 战舰标签]', chk6)
        assert chk6, '应有机体来源的队伍增强条目'
        assert all(x['shown'] == x['exp'] for x in chk6), f'战舰标签应与交集一致: {chk6}'

        # 队友对自身增强: 伊欧(乘阿特拉斯高达) → 双头像; 沙漠高达改(机体) → 无副头像
        pg.click("[data-k='ally_buff_self']"); pg.wait_for_timeout(900)
        chk7 = pg.evaluate("""() => {
          const find = kw => [...document.querySelectorAll('#farea .lrow')].find(x => x.textContent.includes(kw));
          const io = find('伊欧'); const desert = find('沙漠高达');
          const pip = el => el ? el.querySelectorAll('.ticon-col .avw.avsm').length : -1;
          return {ioPip: pip(io), desertPip: pip(desert),
                  ioRarb: io ? io.querySelectorAll('.rarb').length : 0,
                  ioN: document.querySelectorAll('#farea .lrow').length};
        }""")
        print('[队友对自身增强]', chk7)
        assert chk7['ioPip'] == 1, f'伊欧行应带机体副头像: {chk7}'
        assert chk7['desertPip'] == 0, f'沙漠高达改(机体本体)不应带副头像: {chk7}'
        assert chk7['ioRarb'] >= 1, '头像应带稀有度角标'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/53a_ally_pair.png')

        # ---------- ⑤ 组队页: 伤害排行不标绿框(v0.47 起绿框移至队伍增强弹窗) ----------
        pg.click('[data-tab="team"]'); pg.wait_for_timeout(2000)
        chk8 = pg.evaluate("""() => {
          const sup = q1('SELECT id,name FROM supporters WHERE name LIKE "%白色基地%" LIMIT 1');
          state.team.suppId = sup.id; pageTeam(document.querySelector('#view')); return sup.name;
        }""")
        pg.wait_for_timeout(4000)
        chk9 = pg.evaluate("""() => ({
          hl: document.querySelectorAll('#tarea .trow.hl').length,
          rows: document.querySelectorAll('#tarea .trow').length,
          shipTxt: [...document.querySelectorAll('#tarea .trow .nm')].filter(e => e.textContent.includes('舰+')).length,
        })""")
        print('[组队排行] 舰=' + chk8, chk9)
        assert chk9['hl'] == 0, f'伤害排行不应有绿框: {chk9}'
        assert chk9['shipTxt'] > 0, '舰+%文字标注应保留'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/53b_team_hl.png')
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
