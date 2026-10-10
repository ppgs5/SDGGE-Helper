# -*- coding: utf-8 -*-
"""v0.39 验证: ①移动统计只看被动技能+防御型驾驶员(主动技能不计) ②武器条件效果(敌方含X标签时贯穿)按对手判定"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8973
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

        # ---------- 0. 移动统计: 只防御型驾驶员 ----------
        chk = pg.evaluate("""() => {
          const rows = q("SELECT target_id, params_json FROM features WHERE feature='move6'", []);
          const pilots = rows.map(r => JSON.parse(r.params_json).pilot).filter(Boolean);
          const roles = [...new Set(pilots.map(c => (q1('SELECT role FROM characters WHERE id=?', [c]) || {}).role))];
          const in6 = id => rows.some(r => r.target_id === id);
          return {
            n6: rows.length, roles,
            kata: pilots.filter(c => c === 1175000500).length,
            xinanzhou: in6(1125001250),   // 弗尔(支援型) → 不应有
            zunzhe: in6(1200001350),      // 东方不败(攻击型) → 不应有
            wuxian: in6(1330002850),      // 阿斯兰(攻击型) → 不应有
            dior: pilots.filter(c => c === 1219000201).length,   // 迪奥EW(防御型) 地狱死神行
            n7: q("SELECT COUNT(*) c FROM features WHERE feature='move7'", [])[0].c,
          };
        }""")
        print('[移动统计]', chk)
        assert chk['n6'] == 593, f'6移动应为593条: {chk["n6"]}'
        assert chk['roles'] == [2], f'驾驶员应全部为防御型: {chk["roles"]}'
        assert chk['kata'] == 16 and chk['dior'] == 1, '卡特吉娜16行+迪奥1行'
        assert not chk['xinanzhou'] and not chk['zunzhe'] and not chk['wuxian'], '非防御型驾驶员的机体不应入列'
        assert chk['n7'] == 36, f'7移动应为36条: {chk["n7"]}'

        # ---------- 1. 武器条件效果: 按对手判定 ----------
        chk2 = pg.evaluate("""() => {
          const wid = 137001015005;
          const cnt = (em, ca) => wTraitsOf(wid, em, ca).filter(t => t.trait_type === 9).length;
          const noTag = q("SELECT id FROM units WHERE id NOT IN (SELECT unit_id FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE t.name='高达') LIMIT 1", [])[0].id;
          return { on: cnt(null, true), off: cnt(null, false), god: cnt(metaOf(1200003950), false), notag: cnt(metaOf(noTag), false) };
        }""")
        print('[武器条件]', chk2)
        assert chk2['on'] == 10 and chk2['off'] == 5, '条件全开时含条件贯穿行, 关闭时仅无条件'
        assert chk2['god'] == 10 and chk2['notag'] == 5, '对高达标签敌人含条件贯穿, 对无标签不含'

        # ---------- 2. 集成: buildRanking 指定敌方 → 条件贯穿随对手变化 ----------
        chk3 = pg.evaluate("""() => {
          const run = enemyMeta => {
            const G = buildRanking(filt('team'), { targetDef: 10000, targetCharDef: 750, vigor: 'mid', crit: false, range: 'all' },
              { passive: true, cpassive: true, skills: false, condAll: true, autoVigor: false, multiPhase: true, allPct: 0, defReduce: 0, star: 3, enemyMeta,
                pilotGroups: { main: null } });
            const r = G.main.find(x => x.unitId === 1370010150);
            return r ? r.dmg : 0;
          };
          const noTag = q("SELECT id FROM units WHERE id NOT IN (SELECT unit_id FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE t.name='高达') LIMIT 1", [])[0].id;
          return { vsGod: run(metaOf(1200003950)), vsNoTag: run(metaOf(noTag)) };
        }""")
        print('[集成]', chk3)
        assert chk3['vsGod'] and chk3['vsNoTag'], '须佐之男应有结果'
        assert chk3['vsGod'] > chk3['vsNoTag'], '对高达标签敌人(条件贯穿生效)伤害应更高'
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
