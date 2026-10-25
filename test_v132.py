# -*- coding: utf-8 -*-
"""v132 验证: 标签与系列按游戏主数据核对修复
① series 表 = 主数据 114 个系列；不再有「标签同名假系列」被机体引用（8500 G GENERATION系列 为主数据正式系列，允许）
② D高达3号机 = DOUBLE FAKE UNDER THE GUNDAM；高达试做3号机 = 0083
③ unit_tags 与主数据 unit_tags 完全一致（多/少均为 0），且「大魔」等真实标签保留
④ 驾驶员 series_set_id → 系列 映射仍可用（无法映射 ≤10）
⑤ 自定义增强按 ID 匹配仍不误命中 D高达3号机（回归 v131 核心）
"""
import os, subprocess, time, csv, sqlite3, collections
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9097
DB = os.path.join(HERE, 'data', 'ggen.db')
M = '/root/workspace/ggen_master/master'

c = sqlite3.connect(DB)
n_series = c.execute('SELECT COUNT(*) FROM series').fetchone()[0]
extra_ser = c.execute('''SELECT s.id, s.name FROM series s WHERE s.id NOT IN (SELECT id FROM series WHERE 1=0)
                          AND s.id NOT IN (SELECT series_id FROM units)''').fetchall()
print('[① 系列数]', n_series)
assert 114 <= n_series <= 116, n_series      # 主数据114 + 极少数仅主数据未收录机体使用的系列(如 GUNDAM EXA)
fake_used = c.execute("""SELECT s.id, s.name, COUNT(*) FROM units u JOIN series s ON s.id=u.series_id
                         JOIN tags t ON t.name=s.name WHERE s.id<>'8500' GROUP BY s.id""").fetchall()
print('[① 被引用的同名假系列]', fake_used)
assert not fake_used, fake_used

r = c.execute("SELECT s.name FROM units u JOIN series s ON s.id=u.series_id WHERE u.id=1101000350").fetchone()
r2 = c.execute("SELECT s.name FROM units u JOIN series s ON s.id=u.series_id WHERE u.id=1060000550").fetchone()
print('[② 系列]', r, r2)
assert r and r[0] == 'DOUBLE FAKE UNDER THE GUNDAM', r
assert r2 and r2[0].startswith('机动战士高达0083'), r2

db = collections.defaultdict(set)
for uid, name in c.execute('SELECT ut.unit_id, t.name FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id'):
    db[str(uid)].add(name)
mst = collections.defaultdict(set)
for row in csv.DictReader(open(os.path.join(M, 'unit_tags.csv'), encoding='utf-8')):
    if row['tag_name']:
        mst[row['unit_id']].add(row['tag_name'])
cover = {r['<UnitId>k__BackingField'] for r in csv.DictReader(open(os.path.join(M, 'all', 'MUnitLineage.csv'), encoding='utf-8'))}
extra = sum(len(db[u] - mst.get(u, set())) for u in db if u in cover)   # 仅统计主数据覆盖的机体
miss = sum(len(mst.get(u, set()) - db[u]) for u in db if u in cover)
uncovered_keep = sum(len(db[u]) for u in db if u not in cover)
print('[③ 标签差] 覆盖单位 多:', extra, '少:', miss, '| 主数据未覆盖单位保留标签数:', uncovered_keep)
assert extra == 0 and miss == 0, (extra, miss)
assert c.execute("SELECT COUNT(*) FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE t.name='大魔'").fetchone()[0] > 0   # 大魔 是真实标签(主数据 lineage 1138)

mp = {str(x[0]) for x in c.execute('SELECT DISTINCT series_set_id FROM units')}
miss_c = sum(1 for cid, ss in c.execute('SELECT id, series_set_id FROM characters') if str(ss) not in mp)
print('[④ 驾驶员系列无法映射]', miss_c)
assert miss_c <= 10, miss_c

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)
        r5 = pg.evaluate("""() => {
          const D = metaOf(1101000350);
          return { d_series: D.series, d_sr: [...D.seriesList],
                   hit: tbuffMatch({ tagIds: [1010, 1134], seriesIds: [], mode: 'or' }, D) }; }""")
        print('[⑤ 自定义增强]', r5)
        assert r5['hit'] is False, r5
        assert not errors, errors
        print('=== test_v132 全部通过 ===')
        b.close()
finally:
    srv.terminate()
