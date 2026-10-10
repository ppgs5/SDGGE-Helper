# -*- coding: utf-8 -*-
"""v0.58 验证: 手动收录机体「极限高达 EXZELIA」+ 驾驶员「塞西娅」标签 + 武器/装置/系列
⓪ diff引擎: 主键变化(旧库无PK→新库有PK) → 整表重建, 否则旧库上会插出重复行
① 机体页数值: SP关=sp原始值 / SP开=SP三星面板(=截图90161/435/9352/8023/8999) / SSP开(=93525/451/9704/8325/9352, v0.65起增量加在★倍率之后与游戏完全一致)
② 驾驶员页: 标签3(宇宙世纪系列/独立世界观系列/高达驾驶员)
③ 机体: 标签8 / 系列GUNDAM EXA / 装置防护盾防御 / 能力3 / 原配驾驶员塞西娅
④ 武器5把: Lv5威力4080/4440/5040/4800/6000 + SSP标记 + 武器页使用限制/效果/改装核心
"""
import os, sqlite3, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
sys.path.insert(0, os.path.join(HERE, 'data'))
from publish_update import diff_db

# ---------- ⓪ 主键变化检测(单主键/复合主键/无主键三态) ----------
DDL_OLD = ('CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT); '
           'CREATE TABLE wf(weapon_id INT, level INT, sort INT, name TEXT); '
           'CREATE TABLE ok(id INTEGER PRIMARY KEY, v TEXT);')
DDL_NEW = ('CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT); '
           'CREATE TABLE wf(weapon_id INT, level INT, sort INT, name TEXT, PRIMARY KEY(weapon_id, level, sort)); '
           'CREATE TABLE ok(id INTEGER PRIMARY KEY, v TEXT);')
for p in ('/tmp/t58_old.db', '/tmp/t58_new.db'):
    if os.path.exists(p): os.remove(p)
o = sqlite3.connect('/tmp/t58_old.db'); o.executescript(DDL_OLD)
o.executescript("INSERT INTO meta VALUES('version','v1'),('built_at','100'); "
                "INSERT INTO wf VALUES(1,1,0,'a'),(1,2,0,'b'); INSERT INTO ok VALUES(1,'x');"); o.commit(); o.close()
n = sqlite3.connect('/tmp/t58_new.db'); n.executescript(DDL_NEW)
n.executescript("INSERT INTO meta VALUES('version','v2'),('built_at','200'); "
                "INSERT INTO wf VALUES(1,1,0,'a'),(1,2,0,'b'); INSERT INTO ok VALUES(1,'x');"); n.commit(); n.close()
sql = diff_db('/tmp/t58_old.db', '/tmp/t58_new.db', 200)
assert 'DROP TABLE IF EXISTS "wf"' in sql and 'PRIMARY KEY(weapon_id, level, sort)' in sql, f'主键变化应整表重建: {sql[:400]}'
assert sql.count("INSERT INTO \"wf\"") == 2, '重建应含全部行'
assert 'DROP TABLE IF EXISTS "ok"' not in sql, '主键未变的表不应重建'
print('[⓪ 主键变化检测] 通过(有PK变化→整表重建; 无变化→不动)')

PORT = 8999
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
UID, CID = 1999000100, 1999000100
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(120000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')

        # ---------- ① 机体页数值口径 ----------
        pg.evaluate("() => { state.unit = {star:0, star3:true, sp:false, ssp:false}; }")
        pg.evaluate(f"() => push({{page:'unit', title:'x', id:{UID}}})")
        pg.wait_for_selector('.statgrid')
        stats = lambda: pg.evaluate("() => [...document.querySelectorAll('.statgrid .v')].map(e => e.textContent)")
        s0 = stats()
        print('[① 三星开+SP关(游戏面板, =截图)]', s0)
        assert s0 == ['74,064', '363', '7,681', '6,589', '7,397', '5'], f'三星开+SP关(=max×1.27944): {s0}'
        assert pg.evaluate("() => !!document.querySelector('#us3')"), '应有三星按钮'
        pg.click('#us3'); pg.wait_for_timeout(300)                       # 三星关+SP关 → 上限等级★0值(=max)
        s0b = stats()
        print('[① 三星关+SP关(上限等级★0)]', s0b)
        assert s0b == ['57,888', '284', '6,004', '5,150', '5,782', '5'], f'三星关+SP关(=max): {s0b}'
        pg.click('#us3'); pg.wait_for_timeout(300)
        assert stats() == ['74,064', '363', '7,681', '6,589', '7,397', '5'], '三星开应回到游戏面板值'
        pg.click('#usp'); pg.wait_for_timeout(300)
        s1 = stats()
        print('[① 三星开+SP开(SP三星面板, =截图)]', s1)
        assert s1 == ['90,161', '435', '9,352', '8,023', '8,999', '5'], f'SP三星面板应与截图一致: {s1}'
        pg.click('#us3'); pg.wait_for_timeout(300)                       # 三星关+SP开 → sp_max(Lv100无星)
        s1b = stats()
        print('[① 三星关+SP开(sp_max)]', s1b)
        assert s1b == ['64,401', '311', '6,680', '5,731', '6,428', '5'], f'三星关+SP开=sp_max: {s1b}'
        pg.click('#uss'); pg.wait_for_timeout(300)                       # SSP需三星+SP → 自动补三星
        s2 = stats()
        print('[① SSP满10(=截图)]', s2)
        assert s2 == ['93,525', '451', '9,704', '8,325', '9,352', '5'], f'SSP面板应与游戏一致: {s2}'
        assert pg.evaluate("() => document.querySelector('#us3').className.includes('on')"), 'SSP应自动带三星'
        pg.click('#usp'); pg.wait_for_timeout(300)                       # SP关 → SSP联动取消
        assert stats() == ['74,064', '363', '7,681', '6,589', '7,397', '5'], 'SP关应联动关闭SSP'
        pg.click('#usp'); pg.wait_for_timeout(300)
        # 武器列表
        ws = pg.evaluate("() => [...document.querySelectorAll('.wrow')].map(e => e.textContent.replace(/\\s+/g,' ').trim())")
        for w in ws: print('[① 武器]', w)
        assert len(ws) == 5, f'应有5把武器: {len(ws)}'
        for pw in ['3,400→4,080', '3,700→4,440', '4,200→5,040', '4,000→4,800', '5,000→6,000']:
            assert any(pw in w for w in ws), f'武器Lv5威力缺 {pw}'
        assert any('南十字座 SSP' in w and 'SSP' in w for w in ws), 'SSP武器行应有SSP标记'
        # 系列/装置/能力/原配驾驶员
        assert pg.evaluate(f"() => metaOf({UID}).series") == 'GUNDAM EXA', '系列应为 GUNDAM EXA'
        body = pg.evaluate("() => document.querySelector('#view').textContent")
        assert '盾牌防御' in body, '应显示装置防护盾防御(features)'
        for ab in ['最大EN提升 LV2', '特殊损伤减轻 LV2', '(战意条件) 镭射武装最大射程提升 LV1']:
            assert ab in body, f'能力缺: {ab}'
        pg.wait_for_timeout(2500)                       # 原配/最高伤害驾驶员异步计算
        ub = pg.evaluate("() => document.getElementById('ubb').textContent")
        print('[① ubb]', ub.replace('\n', ' ')[:120])
        assert '塞西娅·阿维亚' in ub, f'原配驾驶员应为塞西娅: {ub[:200]}'
        # 标签8
        tg = pg.evaluate("() => [...document.querySelectorAll('[data-gotag]')].map(e => e.textContent.replace('›','').trim())")
        print('[③ 机体标签]', tg)
        for t in ['宇宙世纪系列', '独立世界观系列', '高达', '专用机', '一击必杀', '白色', '重击', 'SSR及以下']:
            assert t in tg, f'机体标签缺: {t}'
        assert len(tg) == 8, f'机体标签数={len(tg)}'

        # ---------- ④ 武器详情页 ----------
        pg.evaluate(f"() => push({{page:'weapon', title:'x', id:{UID * 100 + 1}}})"); pg.wait_for_timeout(500)
        wtxt = pg.evaluate("() => document.querySelector('#view').textContent")
        for t in ['4,080', '仅限于移动前使用', '对水下敌人的伤害减半', '绝对命中', '遭特殊武装攻击时，受到的损伤提升20%']:
            assert t in wtxt, f'MAP武器页缺: {t}'
        pg.evaluate(f"() => push({{page:'weapon', title:'x', id:{UID * 100 + 3}}})"); pg.wait_for_timeout(500)
        assert '赋予敌方“防御力减少30%”(1回合)' in pg.evaluate("() => document.querySelector('#view').textContent"), '南十字座效果'
        pg.evaluate(f"() => push({{page:'weapon', title:'x', id:{UID * 100 + 90}}})"); pg.wait_for_timeout(500)
        ssp_txt = pg.evaluate("() => document.querySelector('#view').textContent")
        for t in ['6,000', '武装效果的效果值UP(且受到的特殊武装损伤提升5%)', '遭特殊武装攻击时，受到的损伤提升25%', 'SSP']:
            assert t in ssp_txt, f'SSP武器页缺: {t}'
        print('[④ 武器详情] 通过(使用限制/效果/改装核心)')

        # ---------- ② 驾驶员页标签 ----------
        pg.evaluate(f"() => push({{page:'char', title:'x', id:{CID}}})"); pg.wait_for_timeout(800)
        ctxt = pg.evaluate("() => document.querySelector('#view').textContent")
        ctg = pg.evaluate("() => [...document.querySelectorAll('#view [data-gotag]')].map(e => e.textContent.replace('›','').trim())")
        print('[② 塞西娅标签]', ctg)
        for t in ['宇宙世纪系列', '独立世界观系列', '高达驾驶员']:
            assert t in ctg, f'驾驶员标签缺: {t} (got {ctg})'
        assert '塞西娅·阿维亚' in ctxt

        # ---------- ⑤ 数据层交叉 ----------
        chk = pg.evaluate(f"""() => {{
          const ut = [...document.querySelectorAll('[data-gotag]')].length;
          const ntag = q("SELECT COUNT(*) c FROM unit_tags WHERE unit_id={UID}")[0].c;
          const nctag = q("SELECT COUNT(*) c FROM char_tags WHERE char_id={CID}")[0].c;
          const sspw = q("SELECT COUNT(*) c FROM weapons WHERE unit_id={UID} AND is_ssp=1")[0].c;
          const flags = q("SELECT flag FROM weapon_flag WHERE weapon_id={UID*100+3}");
          const feat = q("SELECT COUNT(*) c FROM features WHERE target_type='unit' AND target_id={UID} AND feature='shield_defense'")[0].c;
          return {{ntag, nctag, sspw, flag: flags[0] && flags[0].flag, feat}};
        }}""")
        print('[⑤ 数据层]', chk)
        assert chk == {'ntag': 8, 'nctag': 3, 'sspw': 1, 'flag': '降防', 'feat': 1}, chk

        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:5]); sys.exit(1)
print('=== test_v58 全部通过 ===')
