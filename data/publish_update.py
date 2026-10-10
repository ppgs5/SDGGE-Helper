#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把当前数据库发布到公开数据仓库(ggen-data) — 供 App 内在线更新使用

产物:
  version.json   版本清单(含增量补丁链 patches[])
  ggen.db        完整数据库(大跨度兜底/新装)
  patches/p_<built_at>.sql  与上一版数据库的按表差分补丁(增量更新用)
用法: python3 data/publish_update.py     (需 gh 已登录; 仓库不存在时自动创建)
"""
import hashlib, json, os, shutil, sqlite3, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'ggen.db')
REPO = os.environ.get('GGEN_DATA_REPO', '/root/workspace/ggen-data')
REMOTE = 'https://github.com/ppgs5/ggen-data.git'
RAW = 'https://raw.githubusercontent.com/ppgs5/ggen-data/main'


def sh(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-500:], '\n', r.stderr[-500:])
        raise SystemExit(f'命令失败: {cmd}')
    return r.stdout.strip()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def collect_new_images(old_path, db_path):
    """新图标(或 z 标记的手工图标每版必带)且 web/img 有文件 → [(相对路径, sha256, size)]
    头像相对路径: units/characters/supporters → thumb/thum_<icon>.webp; mods → item/<icon>.webp"""
    img_root = os.path.join(HERE, '..', 'web', 'img')

    def icons(db):
        s = set()
        for t in ('units', 'characters', 'supporters'):
            for (ic,) in db.execute(f"SELECT DISTINCT icon FROM {t} WHERE icon IS NOT NULL AND icon!=''"):
                s.add('thumb/thum_' + str(ic) + '.webp')
        for (ic,) in db.execute("SELECT DISTINCT icon FROM mods WHERE icon IS NOT NULL AND icon!=''"):
            s.add('item/' + str(ic) + '.webp')
        return s

    n = sqlite3.connect(db_path)
    try:
        o = sqlite3.connect(old_path)
        old_icons = icons(o)
        o.close()
    except Exception:
        old_icons = set()
    out = []
    for rel in sorted(icons(n)):
        icon = rel.split('thum_')[-1].split('.')[0] if rel.startswith('thumb/') else rel.split('/')[-1].split('.')[0]
        if rel in old_icons and 'z' not in icon:
            continue                                  # 已发布过且非手工标记 → 跳过; z 图标每版刷新(方便重裁头像)
        fp = os.path.join(img_root, rel)
        if os.path.exists(fp):
            out.append((rel, sha256_file(fp), os.path.getsize(fp)))
    n.close()
    return out


def attach_images(repo, entry, imgs):
    if not imgs:
        return 0
    img_root = os.path.join(repo, 'patches', 'img')
    for rel, _h, _s in imgs:
        dst = os.path.join(img_root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(os.path.join(HERE, '..', 'web', 'img', rel), dst)
    entry['images'] = [{'file': rel, 'sha256': h, 'size': s} for rel, h, s in imgs]
    return len(imgs)


def sq(v):
    if v is None:
        return 'NULL'
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, bytes):
        return "X'" + v.hex() + "'"
    return "'" + str(v).replace("'", "''") + "'"


# 无主键大表的"键列": 差异按键列做范围重建(整表重建会让补丁达数MB, 且旧版App单次 db.run 重放会触发 WASM trap)
NOPK_KEYS = {
    'weapon_traits': ['weapon_id'], 'weapon_fx': ['weapon_id'], 'weapon_use': ['weapon_id'],
    'weapon_flag': ['weapon_id'], 'unit_abilities': ['unit_id'], 'features': ['target_type', 'target_id'],
}


def diff_db(old_path, new_path, new_built_at):
    """新旧库按表对比 → 幂等补丁 SQL(INSERT OR REPLACE / DELETE / 表级重建)"""
    o = sqlite3.connect(old_path)
    n = sqlite3.connect(new_path)
    t_old = {r[0] for r in o.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    out, n_ins = [], 0
    for (t,) in n.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        n_cols = [(r[1], r[5]) for r in n.execute(f'PRAGMA table_info("{t}")')]
        n_names = [c[0] for c in n_cols]
        o_cols = [(r[1], r[5]) for r in o.execute(f'PRAGMA table_info("{t}")')] if t in t_old else []
        o_names = [c[0] for c in o_cols]
        ddl = n.execute("SELECT sql FROM sqlite_master WHERE name=?", (t,)).fetchone()[0]
        idx = [r[0] for r in n.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (t,))]
        _o_pk = [c[1] for c in o_cols] if o_cols else None
        if t not in t_old or o_names != n_names or _o_pk != [c[1] for c in n_cols]:
            # 新表/列变化/主键变化 → 整表重建(含索引)。主键变化必须重建, 否则旧库(无该主键)上 INSERT OR REPLACE 会插出重复行
            # 新表 / 结构变化 → 整表重建(含索引)
            out.append(f'DROP TABLE IF EXISTS "{t}";')
            out.append(ddl + ';')
            for x in idx:
                out.append(x + ';')
            for row in n.execute(f'SELECT {",".join(n_names)} FROM "{t}"'):
                out.append(f'INSERT INTO "{t}" VALUES(' + ','.join(sq(v) for v in row) + ');')
                n_ins += 1
            continue
        pk = [c[0] for c in n_cols if c[1]]
        _skip = {'updated_at'}                       # 构建时间戳每版都变, 不参与差异比较(否则全表重写)
        _cmp_idx = [j for j, nm in enumerate(n_names) if nm not in _skip]
        _key = lambda row: tuple(str(row[j]) for j in _cmp_idx)
        if len(pk) == 1:
            k = pk[0]
            n_by = {r[0]: r for r in n.execute(f'SELECT {",".join(n_names)} FROM "{t}"')}
            o_by = {r[0]: r for r in o.execute(f'SELECT {",".join(n_names)} FROM "{t}"')}
            for kk, row in n_by.items():
                if kk not in o_by or _key(o_by[kk]) != _key(row):
                    out.append(f'INSERT OR REPLACE INTO "{t}" VALUES(' + ','.join(sq(v) for v in row) + ');')
                    n_ins += 1
            for kk in o_by:
                if kk not in n_by:
                    out.append(f'DELETE FROM "{t}" WHERE {k}={sq(kk)};')
        elif len(pk) > 1:
            ki = [n_names.index(cname) for cname in pk]
            n_by = {tuple(r[j] for j in ki): r for r in n.execute(f'SELECT {",".join(n_names)} FROM "{t}"')}
            o_by = {tuple(r[j] for j in ki): r for r in o.execute(f'SELECT {",".join(n_names)} FROM "{t}"')}
            for kk, row in n_by.items():
                if kk not in o_by or _key(o_by[kk]) != _key(row):
                    out.append(f'INSERT OR REPLACE INTO "{t}" VALUES(' + ','.join(sq(v) for v in row) + ');')
                    n_ins += 1
            for kk in o_by:
                if kk not in n_by:
                    cond = ' AND '.join(f'{cname}={sq(v)}' for cname, v in zip(pk, kk))
                    out.append(f'DELETE FROM "{t}" WHERE {cond};')
        else:
            n_rows = n.execute(f'SELECT {",".join(n_names)} FROM "{t}"').fetchall()
            o_rows = o.execute(f'SELECT {",".join(o_names)} FROM "{t}"').fetchall()
            if sorted(map(str, map(_key, n_rows))) != sorted(map(str, map(_key, o_rows))):
                keys = NOPK_KEYS.get(t)
                if keys and all(k in n_names for k in keys):
                    # 按键列范围重建: DELETE 该键全部 + INSERT 新行(幂等且补丁小)
                    ki = [n_names.index(k) for k in keys]
                    rk = lambda row: tuple(str(row[j]) for j in ki)
                    n_map, o_map = {}, {}
                    for r in n_rows: n_map.setdefault(rk(r), []).append(r)
                    for r in o_rows: o_map.setdefault(rk(r), []).append(r)
                    for kk in sorted(set(n_map) | set(o_map), key=str):
                        if sorted(map(str, n_map.get(kk, []))) == sorted(map(str, o_map.get(kk, []))):
                            continue
                        cond = ' AND '.join(f'{cn}={sq(v)}' for cn, v in zip(keys, kk))
                        out.append(f'DELETE FROM "{t}" WHERE {cond};')
                        for row in n_map.get(kk, []):
                            out.append(f'INSERT INTO "{t}" VALUES(' + ','.join(sq(v) for v in row) + ');')
                            n_ins += 1
                else:
                    out.append(f'DELETE FROM "{t}";')
                    for row in n_rows:
                        out.append(f'INSERT INTO "{t}" VALUES(' + ','.join(sq(v) for v in row) + ');')
                        n_ins += 1
    o.close(); n.close()
    body = '\n'.join(out)
    return f'-- ggen-data patch @{new_built_at} ({n_ins} rows)\nBEGIN;\n{body}\nCOMMIT;\n'


def main():
    db = sqlite3.connect(DB)
    meta = {k: v for k, v in db.execute('SELECT key, value FROM meta')}
    version, built_at = meta.get('version'), int(meta.get('built_at') or 0)
    size = os.path.getsize(DB)
    sha = sha256_file(DB)
    try:
        counts = json.loads(meta.get('counts') or '{}')
    except Exception:
        counts = {}
    # 仓库准备
    if not os.path.isdir(os.path.join(REPO, '.git')):
        r = subprocess.run(['gh', 'repo', 'view', 'ppgs5/ggen-data'], capture_output=True, text=True)
        if r.returncode != 0:
            sh('gh repo create ppgs5/ggen-data --public --description "SD高达永恒助手 数据更新源（仅数据文件，App在线更新用）"')
        os.makedirs(REPO, exist_ok=True)
        sh('git init -b main', cwd=REPO)
        sh(f'git remote add origin {REMOTE}', cwd=REPO)
    old_db = os.path.join(REPO, 'ggen.db')
    old_manifest = {}
    vj = os.path.join(REPO, 'version.json')
    if os.path.exists(vj):
        try:
            old_manifest = json.load(open(vj, encoding='utf-8'))
        except Exception:
            old_manifest = {}
    patches = list(old_manifest.get('patches') or [])
    old_at = int(old_manifest.get('built_at') or 0)
    if os.path.exists(old_db) and old_at:
        if built_at == old_at:
            print(f'数据未变化(built_at={built_at}), 保留既有补丁 {len(patches)} 个')
            if patches:                              # 数据未变也允许给最新补丁补/刷新头像(如手工 z 图重裁)
                nimg = attach_images(REPO, patches[-1], collect_new_images(old_db, DB))
                if nimg:
                    print(f'为补丁 {patches[-1]["file"]} 附带头像 {nimg} 张')
        elif built_at < old_at:
            print(f'警告: 新库更旧({built_at} < {old_at}), 重置补丁链')
            patches = []
        else:
            sql = diff_db(old_db, DB, built_at)
            pf = f'p_{built_at}.sql'
            pdir = os.path.join(REPO, 'patches')
            os.makedirs(pdir, exist_ok=True)
            with open(os.path.join(pdir, pf), 'w', encoding='utf-8') as f:
                f.write(sql)
            me = {'built_at': built_at, 'from_built_at': old_at, 'to': version, 'file': pf,
                  'size': len(sql.encode('utf-8')), 'sha256': hashlib.sha256(sql.encode('utf-8')).hexdigest()}
            nimg = attach_images(REPO, me, collect_new_images(old_db, DB))
            patches.append(me)
            print(f'生成增量补丁 {pf}: {me["size"]/1024:.1f} KB(相对上版)' + (f' + 头像 {nimg} 张' if nimg else ''))
    else:
        patches = []                                 # 首次发布: 无补丁链
    manifest = {'version': version, 'built_at': built_at, 'db_sha256': sha, 'db_size': size,
                'db_url': f'{RAW}/ggen.db', 'patch_url_base': f'{RAW}/patches/', 'patches': patches, 'counts': counts}
    with open(vj, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    shutil.copy(DB, old_db)
    with open(os.path.join(REPO, 'README.md'), 'w', encoding='utf-8') as f:
        f.write('# ggen-data\n\nSD高达永恒助手 数据更新源（仅数据文件，供 App 内「在线更新」使用）\n\n'
                '- `version.json` 版本清单（含增量补丁链）\n- `ggen.db` 完整数据库\n- `patches/` 增量补丁（SQL）\n')
    sh('git add -A', cwd=REPO)
    if not sh('git status --short', cwd=REPO):
        print('无变化，跳过')
        return
    sh(f'git commit -m "data {version} (built_at {built_at}) patches={len(patches)} sha256={sha[:12]}"', cwd=REPO)
    sh('git push -u origin main', cwd=REPO)
    print(f'已发布 {version} · {size/1e6:.1f}MB · 补丁链 {len(patches)} 个 → {REMOTE}')


if __name__ == '__main__':
    main()
