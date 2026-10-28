# -*- coding: utf-8 -*-
"""v161 验证: 战舰 Leader 技能结构化（复合型多效果）+ 条件关系
① 93 艘战舰全部能解析出效果（无空缺）
② 卡蒂‧马涅钦＆乌拉级: 指挥官机 +20% / 劲敌+指挥官机 +30%（组内 AND），主效果 30%
③ 文森特·派克＆斯巴达号: 空中用+水中用 25%（组内 AND）
④ 布莱德·诺亚＆白色基地: 作品系列「机动战士高达」25%
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9211

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1400}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        r = pg.evaluate("""() => {
          const ids = q('SELECT DISTINCT supporter_id id FROM supporter_leader').map(x => x.id);
          let empty = 0;
          for (const sid of ids) { const s = q1('SELECT * FROM supporters WHERE id=?', [sid]); if (!shipEffOf(s, 3).effects.length) empty++; }
          const eff = (sid) => { const s = q1('SELECT * FROM supporters WHERE id=?', [sid]); const e = shipEffOf(s, 0);
            return { pct: e.pct, effects: e.effects.map(x => ({ v: x.v, tags: x.tagSet, series: x.series, head: x.head })) }; };
          const cmd = q1("SELECT t1.unit_id FROM unit_tags t1 WHERE t1.tag_id=1092 AND t1.unit_id NOT IN (SELECT unit_id FROM unit_tags WHERE tag_id=1006) LIMIT 1");
          const both = q1("SELECT t1.unit_id FROM unit_tags t1 JOIN unit_tags t2 ON t1.unit_id=t2.unit_id AND t2.tag_id=1006 WHERE t1.tag_id=1092 LIMIT 1");
          return { total: ids.length, empty,
                   kati: eff(1370000750), spartan: eff(1031000250), bright: eff(1001000150),
                   pctCmd: cmd ? shipBuffPct(shipEffOf(q1('SELECT * FROM supporters WHERE id=?',[1370000750]),0), metaOf(cmd.unit_id)) : null,
                   pctBoth: both ? shipBuffPct(shipEffOf(q1('SELECT * FROM supporters WHERE id=?',[1370000750]),0), metaOf(both.unit_id)) : null }; }""")
        print('[① 覆盖]', r['total'], 'empty=', r['empty'])
        assert r['total'] == 93 and r['empty'] == 0, r
        print('[② 卡蒂]', json.dumps(r['kati'], ensure_ascii=False)[:200], '| 指挥官机', r['pctCmd'], '| 劲敌+指挥官机', r['pctBoth'])
        assert r['kati']['pct'] == 30, r['kati']
        assert r['pctCmd'] == 20 and r['pctBoth'] == 30, (r['pctCmd'], r['pctBoth'])
        print('[③ 斯巴达]', json.dumps(r['spartan']['effects'], ensure_ascii=False)[:160])
        assert any(set(e['tags']) == {'空中用', '水中用'} for e in r['spartan']['effects']), r['spartan']
        print('[④ 布莱德]', json.dumps(r['bright']['effects'], ensure_ascii=False)[:160])
        assert '机动战士高达' in (r['bright']['effects'][0]['series'] or []), r['bright']

        assert not errors, errors
        print('=== test_v161 全部通过 ===')
        b.close()
finally:
    srv.terminate()
