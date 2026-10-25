# -*- coding: utf-8 -*-
"""v138 验证: 手工录入条目按游戏主数据合并（含默认驾驶员）
① 不再有 source='manual' 的机体/驾驶员
② 旧 id 1999000100 的机体与驾驶员均已不存在
③ 极限高达 EXZELIA = 1795000100，名称取主数据；默认驾驶员 = 1795000101
④ 该驾驶员名称取主数据「塞西娅·阿维亚」，面板按 cap 90 折算(ranged 557 / awaken 293)
⑤ 机体面板与主数据一致(max_hp 52903 / max_atk 5487)
"""
import os, sqlite3
DB = os.path.join('/root/workspace/ggen_app', 'data', 'ggen.db')
c = sqlite3.connect(DB)

m_u = c.execute("SELECT COUNT(*) FROM units WHERE source='manual'").fetchone()[0]
m_c = c.execute("SELECT COUNT(*) FROM characters WHERE source='manual'").fetchone()[0]
print('[① 手工条目] units:', m_u, 'chars:', m_c)
assert m_u == 0 and m_c == 0, (m_u, m_c)

old_u = c.execute('SELECT COUNT(*) FROM units WHERE id=1999000100').fetchone()[0]
old_c = c.execute('SELECT COUNT(*) FROM characters WHERE id=1999000100').fetchone()[0]
print('[② 旧 id]', old_u, old_c)
assert old_u == 0 and old_c == 0, (old_u, old_c)

u = c.execute('SELECT id, name, default_char_id, max_hp, max_atk FROM units WHERE id=1795000100').fetchone()
print('[③ 机体]', u)
assert u and u[1] == '极限高达 EXZELIA' and u[2] == 1795000101, u
assert u[3] == 52903 and u[4] == 5487, u

ch = c.execute('SELECT id, name, rarity, max_ranged, max_awaken FROM characters WHERE id=1795000101').fetchone()
print('[④ 驾驶员]', ch)
assert ch and ch[1] == '塞西娅·阿维亚' and ch[2] == 4, ch
assert ch[3] == 557 and ch[4] == 293, ch

assert c.execute('SELECT COUNT(*) FROM char_tags WHERE char_id=1999000100').fetchone()[0] == 0
assert c.execute('SELECT COUNT(*) FROM weapons WHERE unit_id=1999000100').fetchone()[0] == 0
print('=== test_v138 全部通过 ===')
