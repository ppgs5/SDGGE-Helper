#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补齐机体地形适性(五地形全空的机体): ①先用本体名(去【型态】/（状态）后缀)从 raw 单位表继承(opencc 繁→简)
   ②再用同名精确匹配。游戏内变形态与本体共享地形适性, 部分机体(如【MA】/【分离型态】)在数据源缺少地形。
用法: python3 data/fix_unit_terrain.py [--apply]   (默认直接写入 web/data/ggen.db; 幂等)"""
import os, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, '..', 'web', 'data', 'ggen.db')
RAW = os.path.join(HERE, '..', 'scrape', 'raw')

ter_pat = re.compile(r'"terrain":\{"id":\d+,"space":(\d+),"atmospheric":(\d+),"ground":(\d+),"surface":(\d+),"underwater":(\d+)\}')
name_pat = re.compile(r'"name":"([^"]{1,44})"')
norm = lambda n: re.sub(r'[\s·‧・\-–—]', '', n.replace('（', '(').replace('）', ')'))


def raw_map():
    """raw 单位表 → {归一化名: (space,atm,ground,surface,water)} (回扫: terrain 前最近 name, 繁→简)"""
    import opencc
    cv = opencc.OpenCC('t2s')
    m = {}
    for f in ('gget_unitlist.html', 'compare_zhCN.html', 'gget_ehp.html', 'gget_formula.html'):
        p = os.path.join(RAW, f)
        if not os.path.exists(p):
            continue
        s = open(p, encoding='utf-8', errors='ignore').read().replace('\\"', '"')
        for mt in ter_pat.finditer(s):
            nm = name_pat.findall(s[max(0, mt.start() - 8000):mt.start()])
            if not nm:
                continue
            key = norm(cv.convert(nm[-1]))
            m.setdefault(key, tuple(int(mt.group(i)) for i in range(1, 6)))
    return m


def candidates(name):
    """本体候选: 原名 → 去【..】/［..］ → 按/拆分(核心飞梭/胸部…类) → 去形态尾词(攻击机/加农型/L型/大砲…) → 去(..)"""
    out = [name]

    def add(x):
        x = (x or '').strip()
        if x and x not in out:
            out.append(x)
    for x in list(out):   # 括号后缀
        for y in (re.sub(r'【[^】]*】\s*$', '', x), re.sub(r'【[^】]*】', '', x),
                  re.sub(r'[\[［][^\]］]*[\]］]\s*$', '', x), re.sub(r'[\[［][^\]］]*[\]］]', '', x)):
            add(y)
    for x in list(out):   # 斜杠组合体拆分(如 核心飞梭/胸部飞行器/腿部飞行器)
        for y in re.split(r'\s*/\s*', x):
            add(y)
    for x in list(out):   # 形态尾词
        for suf in ('攻击机', '辅助机', '加农型', 'L型', '大砲'):
            if x.endswith(suf):
                add(x[:-len(suf)])
    for x in list(out):   # 圆括号(状态)后缀
        for y in (re.sub(r'[（(][^）)]*[）)]\s*$', '', x).strip(), re.sub(r'[（(][^）)]*[）)]', '', x).strip()):
            add(y)
    return out


MANUAL = {   # 无字面关联的脱出/变形形态 → 按其所属机体系列取本体地形(源: raw 单位表)
    'G要塞战机': (3, 1, 3, 1, 2),                      # ← raw「高达」(RX-78 脱出形态)
    '核心飞梭/胸部飞行器/腿部飞行器': (3, 3, 1, 1, 1),   # ← raw「核心战机」
    '再生大砲': (3, 3, 3, 1, 3),                        # ← raw「再生高达」(变形 Cannon)
}


def apply_fix(db, quiet=False):
    m = raw_map()
    resolved = 0
    rows = db.execute("""SELECT id,name FROM units WHERE COALESCE(terrain_space,0)=0 AND COALESCE(terrain_atm,0)=0
        AND COALESCE(terrain_ground,0)=0 AND COALESCE(terrain_surface,0)=0 AND COALESCE(terrain_water,0)=0""").fetchall()
    left = []
    for uid, name in rows:
        hit = MANUAL.get(norm(name)) or MANUAL.get(name)
        # ① DB 内非空行按候选名匹配(本体继承)
        if not hit:
            for c in candidates(name):
                r = db.execute("""SELECT terrain_space,terrain_atm,terrain_ground,terrain_surface,terrain_water FROM units
                    WHERE name=? AND COALESCE(terrain_space,0)!=0 LIMIT 1""", (c,)).fetchone()
                if r:
                    hit = r
                    break
        if not hit:
            # ② raw 单位表映射(候选名逐个查)
            for c in candidates(name):
                if norm(c) in m and len(m[norm(c)]) == 5:
                    hit = m[norm(c)]
                    break
        if hit:
            db.execute("UPDATE units SET terrain_space=?,terrain_atm=?,terrain_ground=?,terrain_surface=?,terrain_water=? WHERE id=?",
                       (hit[0], hit[1], hit[2], hit[3], hit[4], uid))
            resolved += 1
        else:
            left.append(name)
    db.commit()
    if not quiet:
        print(f'地形补齐: 解决 {resolved} / 剩余 {len(left)}')
        if left:
            print('剩余未解决(前15):', left[:15])
    return resolved, left


if __name__ == '__main__':
    db = sqlite3.connect(DB)
    apply_fix(db)
