# -*- coding: utf-8 -*-
"""v0.37 验证: 敌方条件被动(发起对战的敌方含X标签/系列时自身攻防提升)按对手判定 — 指定防御目标时逐条匹配"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8967
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

        # ---------- 0. 数据层: 单位侧 ----------
        chk = pg.evaluate("""() => {
          const zion = metaOf(1001003050);      // 吉翁号(EX): 自护公国军标签
          const sf = metaOf(1330000150);        // 突击自由(EX): 无
          const uc = metaOf(1125000100);        // 独角兽: UC系列
          return {
            atlasOn: unitPassiveAtkPct(1031001250, 'mid', true, null),    // 擎天神: 条件全开计入+15
            atlasOff: unitPassiveAtkPct(1031001250, 'mid', false, null),
            atlasZion: unitPassiveAtkPct(1031001250, 'mid', false, zion),
            atlasSF: unitPassiveAtkPct(1031001250, 'mid', false, sf),
            dtOn: unitPassiveAtkPct(1133000301, 'mid', true, null),      // 德尔塔改: 敌方UC系列+25
            dtOff: unitPassiveAtkPct(1133000301, 'mid', false, null),
            dtUc: unitPassiveAtkPct(1133000301, 'mid', false, uc),
            dtSF: unitPassiveAtkPct(1133000301, 'mid', false, sf),
          };
        }""")
        print('[数据-机体]', chk)
        assert chk['atlasOn'] - chk['atlasOff'] == 15, '条件全开应计入敌方条件+15'
        assert chk['atlasZion'] - chk['atlasOff'] == 15, '对自护公国军机体应计入+15'
        assert chk['atlasSF'] == chk['atlasOff'], '对无标签机体不应计入'
        assert chk['dtOn'] - chk['dtOff'] == 25 and chk['dtUc'] - chk['dtOff'] == 25 and chk['dtSF'] == chk['dtOff'], '系列条件判定异常'

        # ---------- 1. 数据层: 驾驶员侧(阿姆罗 红色条件) ----------
        chk2 = pg.evaluate("""() => {
          const red = q("SELECT u.id FROM units u JOIN unit_tags ut ON ut.unit_id=u.id JOIN tags t ON t.id=ut.tag_id WHERE t.name='红色' LIMIT 1", [])[0].id;
          const base = metaOf(1200003950);
          const noE = charBonus(1001000100, 'mid', { passive: true, cpassive: true, skills: false, condAll: false }, base).dmg;
          const redE = charBonus(1001000100, 'mid', { passive: true, cpassive: true, skills: false, condAll: false, enemyMeta: metaOf(red) }, base).dmg;
          const allE = charBonus(1001000100, 'mid', { passive: true, cpassive: true, skills: false, condAll: true }, base).dmg;
          return {noE, redE, allE, red};
        }""")
        print('[数据-驾驶员]', chk2)
        assert chk2['redE'] - chk2['noE'] == 10 and chk2['allE'] - chk2['noE'] == 10, '阿姆罗红色条件+10应仅在指定红色对手/条件全开时生效'

        # ---------- 2. 集成: buildRanking 指定敌方 → 机体被动随对手变化 ----------
        chk3 = pg.evaluate("""() => {
          const run = enemyMeta => {
            const G = buildRanking(filt('team'), { targetDef: 10000, targetCharDef: 750, vigor: 'mid', crit: false, range: 'all' },
              { passive: true, cpassive: true, skills: false, condAll: true, autoVigor: false, multiPhase: true, allPct: 0, defReduce: 0, star: 3, enemyMeta,
                pilotGroups: { main: null } });
            const r = G.main.find(x => x.unitId === 1031001250);
            return r ? {dmg: r.dmg, pct: r.pct} : null;
          };
          return { vsZion: run(metaOf(1001003050)), vsSF: run(metaOf(1330000150)) };
        }""")
        print('[集成]', chk3)
        assert chk3['vsZion'] and chk3['vsSF'], '擎天神应出现在结果中'
        assert chk3['vsZion']['pct'] - chk3['vsSF']['pct'] == 15, f"对吉翁号vs突击自由 机体被动应差15%: {chk3}"
        assert chk3['vsZion']['dmg'] > chk3['vsSF']['dmg'], '对匹配对手伤害应更高'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
