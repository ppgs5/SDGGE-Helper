#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 scrape/raw/ 构建 SQLite 数据库 data/ggen.db

包含:
  - 机体/驾驶员/武器/战舰/零件/能力/技能/效果/标签/系列 全量主数据
  - 武器每级效果(weapon_traits, 来自 growth.wtc)
  - 特性层自动提取 (extra_action / support / revive / team_buff / ally_buff_self / mechanisms)
  - 更新接口预留: source/updated_at/data_version 列 + update_log/staging_changes 表
"""
import json, re, os, sys, time, sqlite3, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'scrape', 'raw')
OUT = os.path.join(HERE, 'ggen.db')
VERSION = 'v' + datetime.date.today().strftime('%Y.%m.%d')
NOW = int(time.time())

CH_LEVEL_CAP = {1: 60, 2: 70, 3: 80, 4: 90, 5: 100}   # 驾驶员稀有度→等级上限(N/R/SR/SSR/UR), SP后100


def cap_val(base, mx, cap):
    """驾驶员/机体面板显示值(★0口径): 游戏/参考站按「稀有度等级上限」显示, 而非 Lv100 理论值.
    驾驶员(实证 soshage 页面 + 用户截图): 将校R 611=39+(857-39)*70//100; 凯·西汀R 294; 雪拉SR 503; 阿姆罗UR=原值(cap=100)。
    机体(实证 soshage 页面/网站模型 23 台): ★0=base+(max-base)*cap//100 (高达SR 41803), ★3面板=floor(★0×1.4)=58524。
    stats_json 仍保留 Lv100 原始值。"""
    if base is None or mx is None:
        return mx
    return base + (mx - base) * cap // 100

PAT = re.compile(r'\{"status":200,"statusText":"OK","headers":\{[^}]*\},"body":"')
DEC = json.JSONDecoder()


def bodies(fname):
    p = os.path.join(RAW, fname)
    if not os.path.exists(p):
        return
    s = open(p, encoding='utf-8', errors='replace').read()
    for m in PAT.finditer(s):
        try:
            yield json.loads(DEC.raw_decode(s[m.end() - 1:])[0])
        except Exception:
            pass


def find_list(fname, *keys):
    for arr in bodies(fname):
        if isinstance(arr, list) and arr and all(k in arr[0] for k in keys):
            return arr
    return None


def find_dict(fname, key):
    for arr in bodies(fname):
        if isinstance(arr, dict) and key in arr:
            return arr
    return None


def tagnames(cond):
    """从 condition 对象取标签/系列名列表"""
    if not cond:
        return []
    out = [t['name'] for t in (cond.get('tags') or []) if isinstance(t, dict)]
    if isinstance(cond.get('series'), dict) and cond['series'].get('name'):
        out.append(cond['series']['name'])
    return out


def cond_names(cond):
    """条件对象 → 具体标签/系列名列表（仅取有名字的）"""
    if not cond:
        return []
    out = [t['name'] for t in (cond.get('tags') or []) if isinstance(t, dict) and t.get('name')]
    s = cond.get('series')
    if isinstance(s, dict) and s.get('name'):
        out.append(s['name'])
    return out


def enrich_traits(trs):
    """把 desc 中的占位符替换为具体标签/系列/单位类型名
    （条件内联在 active_condition / trait_boost / target_condition 里）"""
    ROLE = {'1': '攻击型', '2': '防御型', '3': '支援型'}
    for t in (trs or []):
        tr = (t or {}).get('trait') or {}
        d = tr.get('desc') or ''
        if not d:
            continue
        ac = tr.get('active_condition') or {}
        tb = tr.get('trait_boost') or {}
        tc = tr.get('target_condition') or {}
        acn, tbn, tcn = cond_names(ac), cond_names(tb), cond_names(tc)
        ser = None
        for cc in (ac, tb, tc):
            s = cc.get('series')
            if isinstance(s, dict) and s.get('name'):
                ser = s['name']
                break
        role = None
        for cc in (ac, tb, tc):
            r = cc.get('unit_role')
            if str(r) in ROLE:
                role = ROLE[str(r)]
                break
        if '【條件1】' in d or '【条件1】' in d:
            names = acn or tcn
            if names:
                d = d.replace('【條件1】', '【' + '、'.join(names) + '】').replace('【条件1】', '【' + '、'.join(names) + '】')
        if '【條件2】' in d or '【条件2】' in d:
            names = tbn or tcn
            if names:
                d = d.replace('【條件2】', '【' + '、'.join(names) + '】').replace('【条件2】', '【' + '、'.join(names) + '】')
        names = acn or tbn or tcn
        # 标签／系列 组合
        if '「標籤／系列」' in d or '「标签／系列」' in d:
            parts = []
            if names:
                parts.append('「' + '、'.join(names) + '」標籤')
            if ser:
                parts.append('「' + ser + '」系列')
            if parts:
                rep = '／'.join(parts)
                d = d.replace('上述「標籤／系列」', rep).replace('上述「标签／系列」', rep)
        if names:
            nm_s = '、'.join(names)
            d = d.replace('上述「標籤」', '「' + nm_s + '」標籤')
            d = d.replace('上述「标签」', '「' + nm_s + '」标签')
            d = d.replace('上述標籤', '「' + nm_s + '」標籤')
            d = d.replace('上述标签', '「' + nm_s + '」标签')
        if role:
            d = d.replace('上述「類型」', '「' + role + '」類型').replace('上述「类型」', '「' + role + '」类型')
        if ser:
            d = d.replace('上述「系列」', '「' + ser + '」系列')
            d = d.replace('上述系列', '「' + ser + '」系列')
        tr['desc'] = d


DDL = '''
DROP TABLE IF EXISTS units; CREATE TABLE units(
 id INTEGER PRIMARY KEY, name TEXT, short_name TEXT, rarity INT, role INT, tr INT, ult INT,
 series_set_id TEXT, series_id TEXT, icon TEXT, models TEXT, body_type INT, area INT, defend INT, evade INT,
 hp INT, en INT, atk INT, def INT, mob INT, mov INT,
 max_hp INT, max_en INT, max_atk INT, max_def INT, max_mob INT, max_mov INT,
 sp_max_hp INT, sp_max_en INT, sp_max_atk INT, sp_max_def INT, sp_max_mob INT, sp_max_mov INT,
 terrain_space INT, terrain_atm INT, terrain_ground INT, terrain_surface INT, terrain_water INT,
 desc TEXT, stats_json TEXT, ssp_json TEXT, name_hant TEXT,
 source TEXT, updated_at INT, data_version TEXT, default_char_id INT, series_set_json TEXT);   -- default_char_id=官方设定驾驶员(gacha.bonus.character); series_set_json=全部系列id(条件匹配用, 参考站 unit_series 判定 series_set 全集)
DROP TABLE IF EXISTS unit_tags; CREATE TABLE unit_tags(unit_id INT, tag_id INT, PRIMARY KEY(unit_id, tag_id));
DROP TABLE IF EXISTS unit_abilities; CREATE TABLE unit_abilities(
 unit_id INT, ability_id INT, name TEXT, traits_json TEXT);
DROP TABLE IF EXISTS characters; CREATE TABLE characters(
 id INTEGER PRIMARY KEY, name TEXT, sort_name TEXT, rarity INT, role INT, series_set_id TEXT,
 icon TEXT, abbreviation TEXT, is_playable INT,
 ranged INT, melee INT, defense INT, reaction INT, awaken INT,
 max_ranged INT, max_melee INT, max_defense INT, max_reaction INT, max_awaken INT,
 sp_max_ranged INT, sp_max_melee INT, sp_max_defense INT, sp_max_reaction INT, sp_max_awaken INT,
 stats_json TEXT, name_hant TEXT, source TEXT, updated_at INT, data_version TEXT);
DROP TABLE IF EXISTS char_tags; CREATE TABLE char_tags(char_id INT, tag_id INT, PRIMARY KEY(char_id, tag_id));
DROP TABLE IF EXISTS char_skills; CREATE TABLE char_skills(
 char_id INT, sort INT, unlock_level INT, sp INT, name TEXT, desc TEXT, traits_json TEXT, skill_id INT, PRIMARY KEY(char_id, sort));
DROP TABLE IF EXISTS char_abilities; CREATE TABLE char_abilities(
 char_id INT, sort INT, ability_id INT, name TEXT, traits_json TEXT, PRIMARY KEY(char_id, sort));
DROP TABLE IF EXISTS char_skills_sp; CREATE TABLE char_skills_sp(
 char_id INT, sort INT, unlock_level INT, sp INT, name TEXT, desc TEXT, traits_json TEXT, skill_id INT, PRIMARY KEY(char_id, sort));
DROP TABLE IF EXISTS char_abilities_sp; CREATE TABLE char_abilities_sp(
 char_id INT, sort INT, ability_id INT, name TEXT, traits_json TEXT, PRIMARY KEY(char_id, sort));
DROP TABLE IF EXISTS weapons; CREATE TABLE weapons(
 id INTEGER PRIMARY KEY, unit_id INT, name TEXT, type INT, work_type INT,
 attack_attr INT, weapon_attr INT, power INT, en INT, ammo INT,
 range_min INT, range_max INT, hit_rate INT, crit_rate INT, is_ssp INT,
 wsc_json TEXT, wtc_json TEXT, name_hant TEXT, source TEXT, updated_at INT, data_version TEXT);
DROP TABLE IF EXISTS weapon_traits; CREATE TABLE weapon_traits(
 weapon_id INT, level INT, trait_type INT, trait_value INT, target_cond TEXT, desc TEXT, cond TEXT);
DROP TABLE IF EXISTS weapon_fx; CREATE TABLE weapon_fx(
 weapon_id INT, level INT, sort INT, name TEXT, desc TEXT);
DROP TABLE IF EXISTS weapon_use; CREATE TABLE weapon_use(
 weapon_id INT, sort INT, text TEXT);
DROP TABLE IF EXISTS weapon_flag; CREATE TABLE weapon_flag(
 weapon_id INT, sort INT, flag TEXT);
DROP TABLE IF EXISTS weapon_ssp_traits; CREATE TABLE weapon_ssp_traits(
 weapon_id INT, trait_type INT, trait_value INT, desc TEXT, name TEXT);
DROP TABLE IF EXISTS unit_abilities_ssp; CREATE TABLE unit_abilities_ssp(
 unit_id INT, before_ability_id INT, ability_id INT, name TEXT, traits_json TEXT, PRIMARY KEY(unit_id, before_ability_id, ability_id));
DROP TABLE IF EXISTS abilities; CREATE TABLE abilities(
 id INTEGER PRIMARY KEY, ability_type INT, name TEXT, icon TEXT, traits_json TEXT);
DROP TABLE IF EXISTS skills; CREATE TABLE skills(
 id INTEGER PRIMARY KEY, name TEXT, desc TEXT, sp INT, duration INT, rarity INT, traits_json TEXT);
DROP TABLE IF EXISTS effects; CREATE TABLE effects(id TEXT, name TEXT, desc TEXT);
DROP TABLE IF EXISTS supporters; CREATE TABLE supporters(
 id INTEGER PRIMARY KEY, name TEXT, rarity INT, icon TEXT, hp_support INT, atk_support INT,
 leader_desc TEXT, leader_target_json TEXT, support_skill_name TEXT, support_skill_desc TEXT,
 lb_json TEXT, source TEXT, updated_at INT, data_version TEXT);
DROP TABLE IF EXISTS mods; CREATE TABLE mods(
 id INTEGER PRIMARY KEY, name TEXT, rarity INT, icon TEXT, series_id TEXT, desc TEXT,
 traits_json TEXT, source TEXT, updated_at INT, data_version TEXT);
DROP TABLE IF EXISTS mod_tags; CREATE TABLE mod_tags(mod_id INT, tag_id INT, PRIMARY KEY(mod_id, tag_id));
DROP TABLE IF EXISTS supporter_tags; CREATE TABLE supporter_tags(supporter_id INT, name TEXT);
DROP TABLE IF EXISTS tags; CREATE TABLE tags(id INTEGER PRIMARY KEY, name TEXT);
DROP TABLE IF EXISTS series; CREATE TABLE series(id TEXT PRIMARY KEY, name TEXT);
DROP TABLE IF EXISTS features; CREATE TABLE features(
 target_type TEXT, target_id INT, feature TEXT, label TEXT, params_json TEXT);
DROP TABLE IF EXISTS update_log; CREATE TABLE update_log(
 id INTEGER PRIMARY KEY AUTOINCREMENT, version TEXT, applied_at INT, summary_json TEXT, snapshot_path TEXT);
DROP TABLE IF EXISTS staging_changes; CREATE TABLE staging_changes(
 id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, tbl TEXT, row_id TEXT, action TEXT,
 diff_json TEXT, status TEXT DEFAULT 'pending');
DROP TABLE IF EXISTS meta; CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX idx_utag ON unit_tags(tag_id); CREATE INDEX idx_ctag ON char_tags(tag_id);
CREATE INDEX idx_wunit ON weapons(unit_id); CREATE INDEX idx_wt ON weapon_traits(weapon_id); CREATE INDEX idx_wfx ON weapon_fx(weapon_id);
CREATE INDEX idx_wuse ON weapon_use(weapon_id);
CREATE INDEX idx_wflag ON weapon_flag(weapon_id);
CREATE INDEX idx_feat ON features(feature); CREATE INDEX idx_featid ON features(target_type,target_id);
CREATE INDEX idx_mtag ON mod_tags(tag_id); CREATE INDEX idx_stag ON supporter_tags(name); CREATE INDEX idx_cs ON char_skills(char_id);
CREATE INDEX idx_ca ON char_abilities(char_id); CREATE INDEX idx_ua ON unit_abilities(unit_id);
CREATE INDEX idx_csp ON char_skills_sp(char_id); CREATE INDEX idx_cap ON char_abilities_sp(char_id);
'''




CONV_COLS = [
    ('units', ['name', 'short_name', 'desc']),
    ('characters', ['name', 'sort_name']),
    ('weapons', ['name']),
    ('supporters', ['name', 'leader_desc', 'support_skill_name', 'support_skill_desc', 'lb_json']),
    ('mods', ['name', 'desc']),
    ('abilities', ['name']),
    ('skills', ['name']),
    ('tags', ['name']),
    ('series', ['name']),
    ('features', ['label', 'params_json']),
    ('unit_abilities', ['name', 'traits_json']),
    ('unit_abilities_ssp', ['name', 'traits_json']),
    ('weapon_ssp_traits', ['desc', 'name']),
    ('char_abilities', ['name', 'traits_json']),
    ('char_skills', ['name', 'desc', 'traits_json']),
    ('char_skills_sp', ['name', 'desc', 'traits_json']),
    ('char_abilities_sp', ['name', 'traits_json']),
    ('weapon_traits', ['desc']),
    ('weapon_fx', ['name', 'desc']),
    ('weapon_use', ['text']),
    ('effects', ['name', 'desc']),
    ('supporter_tags', ['name']),
]


def convert_to_simplified(db):
    """繁体 → 简体（原文保留在 name_hant）"""
    try:
        import opencc
    except ImportError:
        print('opencc 不可用，跳过简繁转换')
        return False
    cc = opencc.OpenCC('t2s')
    for tbl, cols in CONV_COLS:
        for col in cols:
            try:
                rows = db.execute(f'SELECT rowid, {col} FROM {tbl} WHERE {col} IS NOT NULL AND {col} != ""').fetchall()
            except Exception:
                continue
            upd = [(cc.convert(v), rid) for rid, v in rows if v]
            db.executemany(f'UPDATE {tbl} SET {col}=? WHERE rowid=?', upd)
    print('简繁转换完成')
    # zh-CN 标准名覆盖（取自 soshage zh-CN 站数据）
    for tbl, fn in (('characters', 'names_zhcn.json'), ('units', 'names_zhcn_units.json'),
                    ('weapons', 'names_zhcn_weapons.json'), ('supporters', 'names_zhcn_supporters.json'),
                    ('mods', 'names_zhcn_mods.json')):
        p2 = os.path.join(HERE, fn)
        if os.path.exists(p2):
            try:
                names = json.load(open(p2, encoding='utf-8'))
                db.executemany(f'UPDATE {tbl} SET name=? WHERE id=?', [(v, int(k)) for k, v in names.items()])
                print(f'zh-CN 名称覆盖 {tbl}: {len(names)} 条')
            except Exception as e:
                print(f'{tbl} 名称覆盖失败:', e)
    return True


def main():
    db = sqlite3.connect(OUT)
    db.executescript(DDL)
    counts = {}
    feats = []

    # ---------- 标签/系列字典 ----------
    tagdict = {}
    for arr in bodies('gget_compare.html'):
        if isinstance(arr, list) and arr and set(arr[0].keys()) == {'id', 'name'}:
            for t in arr:
                tagdict[t['id']] = t['name']
    db.executemany('INSERT OR REPLACE INTO tags VALUES(?,?)', list(tagdict.items()))
    counts['tags'] = len(tagdict)

    ser = {}
    for arr in bodies('gget_unitlist.html'):
        if not (isinstance(arr, list) and arr and isinstance(arr[0], dict)):
            continue
        ks = set(arr[0].keys())
        if ks == {'id', 'name'}:            # 124 系列表
            for x in arr:
                ser[str(x['id'])] = x['name']
        elif 'icon' in ks and 'desc' in ks and 'scenario_stages' in ks:  # 112 作品表
            for w in arr:
                ser.setdefault(str(w['id']), w['name'])
    db.executemany('INSERT OR REPLACE INTO series VALUES(?,?)', list((ser or {}).items()))
    counts['series'] = len(ser or {})

    # ---------- 机体 ----------
    units = find_list('gget_unitlist.html', 'mechanism', 'transform_to')
    # 补充 gget_weapon.html units 字典中缺失的机体（武器引用的 MA/形态机等, payload 1441 vs 主列表 1308）
    _have = set(u['id'] for u in (units or []))
    _wd = find_dict('gget_weapon.html', 'units') or {}
    _extra = [u for k, u in (_wd.get('units') or {}).items() if isinstance(u, dict) and u.get('id') not in _have]
    if _extra:
        units = (units or []) + _extra
        print(f'补充缺失机体: {len(_extra)} 台')
    n = 0
    for u in units or []:
        st = u.get('stats') or {}
        tr = u.get('terrain') or {}
        # max_* 存「等级上限插值」值(SP关★0): 游戏/网站按等级上限显示★0值, ★3面板=floor(★0×1.4); sp_max_* 保持Lv100口径
        _capu = CH_LEVEL_CAP.get(u.get('rarity'), 100)
        # series_set 数组顺序不可靠(如 [10(sort2),30(sort1)]), 主系列=sort=1 的作品系列
        # (原取 [0] 导致 437 台机体系列错位: THE ORIGIN→机动战士高达、EW→W(TV)、13个系列条件无法命中)
        _ss = sorted(u.get('series_set') or [], key=lambda x: x.get('sort') or 99)
        _sid = next((x.get('series_id') for x in _ss if x.get('sort') == 1), (_ss[0].get('series_id') if _ss else None))
        db.execute('''INSERT INTO units VALUES(
          :id,:name,:short_name,:rarity,:role,:tr,:ult,:series_set_id,:series_id,:icon,:models,:body_type,:area,:defend,:evade,
          :hp,:en,:atk,:df,:mob,:mov,:max_hp,:max_en,:max_atk,:max_def,:max_mob,:max_mov,
          :sp_max_hp,:sp_max_en,:sp_max_atk,:sp_max_def,:sp_max_mob,:sp_max_mov,
          :t_space,:t_atm,:t_ground,:t_surface,:t_water,:desc,:stats_json,:ssp_json,:name,
          'scrape',:now,:ver,:dcid,:ssj)''', dict(
            id=u['id'], name=u['name'], short_name=u.get('short_name'), rarity=u.get('rarity'),
            role=u.get('role'), tr=u.get('tr'), ult=1 if u.get('ult') else 0,
            series_set_id=str(u.get('series')), series_id=str(_sid if _sid is not None else ''), icon=u.get('icon'), models=u.get('models'),
            body_type=u.get('body_type'), area=u.get('area'),
            defend=1 if u.get('defend') else 0, evade=1 if u.get('evade') else 0,
            hp=st.get('hp'), en=st.get('en'), atk=st.get('attack'), df=st.get('defense'),
            mob=st.get('mobility'), mov=st.get('movement'),
            max_hp=cap_val(st.get('hp'), st.get('max_hp'), _capu), max_en=cap_val(st.get('en'), st.get('max_en'), _capu),
            max_atk=cap_val(st.get('attack'), st.get('max_attack'), _capu),
            max_def=cap_val(st.get('defense'), st.get('max_defense'), _capu),
            max_mob=cap_val(st.get('mobility'), st.get('max_mobility'), _capu), max_mov=st.get('max_movement'),
            sp_max_hp=st.get('sp_max_hp'), sp_max_en=st.get('sp_max_en'), sp_max_atk=st.get('sp_max_attack'),
            sp_max_def=st.get('sp_max_defense'), sp_max_mob=st.get('sp_max_mobility'), sp_max_mov=st.get('sp_max_movement'),
            t_space=tr.get('space'), t_atm=tr.get('atmospheric'), t_ground=tr.get('ground'),
            t_surface=tr.get('surface'), t_water=tr.get('underwater'),
            desc=u.get('desc'),
            stats_json=json.dumps(st, ensure_ascii=False),
            ssp_json=json.dumps(u.get('ssp_config'), ensure_ascii=False), now=NOW, ver=VERSION, dcid=None,
            ssj=json.dumps([str(x.get('series_id')) for x in (u.get('series_set') or []) if x.get('series_id') is not None], ensure_ascii=False)))
        n += 1
        for t in (u.get('tags') or []):
            db.execute('INSERT INTO unit_tags VALUES(?,?)', (u['id'], t['tag_id']))
        for a in (u.get('abilities') or []):
            ab = a.get('ability')
            if not ab:
                continue
            det = ab.get('detail') or {}
            nm = det.get('name') or ''
            trs = ab.get('traits') or []
            enrich_traits(trs)
            db.execute('INSERT INTO unit_abilities VALUES(?,?,?,?)',
                       (u['id'], a['ability_id'], nm, json.dumps(trs, ensure_ascii=False)))
            _scan_ability_features(feats, 'unit', u['id'], nm, trs)
        # 机制特性
        for mec in (u.get('mechanism') or []):
            m = mec.get('mechanism')
            if not m:
                continue
            if m.get('type') == 4:
                feats.append(('unit', u['id'], 'revive_escape', m['name'], {'value': m.get('value'), 'desc': m.get('desc')}))
            elif m.get('type') == 1:
                feats.append(('unit', u['id'], 'shield_defense', m['name'], {'value': m.get('value')}))
            elif m.get('type') in (2, 6):
                feats.append(('unit', u['id'], 'transform' if m.get('type') == 2 else 'swap', m['name'], {'desc': m.get('desc')}))
        # 单位技能
        for sk in (u.get('skills') or []):
            s2 = sk.get('skill') or {}
            feats.append(('unit', u['id'], 'unit_skill', s2.get('name'),
                          {'desc': s2.get('desc'), 'traits': s2.get('traits') or []}))
    counts['units'] = n

    # ---------- 驾驶员 ----------
    chars = find_list('gget_formula.html', 'character_status_id')
    # 每次重建先清手动收录行(source=manual), 稍后按 manual_chars.json 重新回填(官网收录同名后自动让位)
    for t2 in ('char_skills', 'char_abilities', 'char_tags'):
        db.execute(f"DELETE FROM {t2} WHERE char_id IN (SELECT id FROM characters WHERE source='manual')")
    db.execute("DELETE FROM characters WHERE source='manual'")
    # 手动收录机体(manual_units.json): 同样先清干净(含武器/特性/效果/使用限制/标签/能力/特性行)
    _mu_ids = "(SELECT id FROM units WHERE source='manual')"
    for t2 in ('weapon_traits', 'weapon_fx', 'weapon_use', 'weapon_flag'):
        db.execute(f"DELETE FROM {t2} WHERE weapon_id IN (SELECT id FROM weapons WHERE unit_id IN {_mu_ids})")
    db.execute(f"DELETE FROM weapons WHERE unit_id IN {_mu_ids}")
    for t2 in ('unit_tags', 'unit_abilities'):
        db.execute(f"DELETE FROM {t2} WHERE unit_id IN {_mu_ids}")
    db.execute(f"DELETE FROM features WHERE target_type='unit' AND target_id IN {_mu_ids}")
    db.execute("DELETE FROM units WHERE source='manual'")
    n = 0
    for c in chars or []:
        st = c.get('stats') or {}
        _cap = CH_LEVEL_CAP.get(c.get('rarity'), 100)   # max_* 存面板值=等级上限值(SP关); sp_max_* = Lv100(SP开), 0→NULL(无SP)
        db.execute('''INSERT INTO characters VALUES(
          :id,:name,:sort_name,:rarity,:role,:series_set_id,:icon,:abbr,:playable,
          :ranged,:melee,:defense,:reaction,:awaken,
          :max_ranged,:max_melee,:max_defense,:max_reaction,:max_awaken,
          :sp_r,:sp_m,:sp_d,:sp_re,:sp_a, :stats_json,:name,'scrape',:now,:ver)''', dict(
            id=c['id'], name=c['name'], sort_name=c.get('sort_name'), rarity=c.get('rarity'),
            role=c.get('role'), series_set_id=str(c.get('series_set_id')), icon=c.get('icon'),
            abbr=c.get('abbreviation'), playable=1 if c.get('is_playable') else 0,
            ranged=st.get('ranged'), melee=st.get('melee'), defense=st.get('defense'),
            reaction=st.get('reaction'), awaken=st.get('awaken'),
            max_ranged=cap_val(st.get('ranged'), st.get('max_ranged'), _cap),
            max_melee=cap_val(st.get('melee'), st.get('max_melee'), _cap),
            max_defense=cap_val(st.get('defense'), st.get('max_defense'), _cap),
            max_reaction=cap_val(st.get('reaction'), st.get('max_reaction'), _cap),
            max_awaken=cap_val(st.get('awaken'), st.get('max_awaken'), _cap),
            sp_r=st.get('sp_max_ranged') or None, sp_m=st.get('sp_max_melee') or None,
            sp_d=st.get('sp_max_defense') or None, sp_re=st.get('sp_max_reaction') or None,
            sp_a=st.get('sp_max_awaken') or None,
            stats_json=json.dumps(st, ensure_ascii=False), now=NOW, ver=VERSION))
        n += 1
        for t in (c.get('tags') or []):
            if t.get('tag_id'):
                db.execute('INSERT INTO char_tags VALUES(?,?)', (c['id'], t['tag_id']))
        for sk in (c.get('skills') or []):
            s2 = sk.get('skill')
            sp2 = sk.get('skill_sp')
            _s2raw = json.dumps(s2.get('trait_set') or [], sort_keys=True, ensure_ascii=False) if s2 else ''
            _sp2raw = json.dumps(sp2.get('trait_set') or [], sort_keys=True, ensure_ascii=False) if sp2 else ''
            if s2:
                enrich_traits(s2.get('trait_set'))
                db.execute('INSERT INTO char_skills VALUES(?,?,?,?,?,?,?,?)',
                           (c['id'], sk.get('sort'), sk.get('level'), s2.get('sp'), s2.get('name'),
                            s2.get('desc'), json.dumps(s2.get('trait_set'), ensure_ascii=False), s2.get('id')))
                nm = s2.get('name') or ''
                _ru2 = []
                for _t2 in (s2.get('trait_set') or []):
                    _ac2 = ((_t2 or {}).get('trait') or {}).get('active_condition') or {}
                    _ru2 += [x for x in str(_ac2.get('unit_ids') or '').split(',') if x]
                _ru2 = list(dict.fromkeys(_ru2))
                if '額外行動次數增加' in nm:
                    feats.append(('char', c['id'], 'extra_action', nm, {'required_units': _ru2, 'desc': s2.get('desc')}))
                if '支援攻擊次數增加' in nm:
                    feats.append(('char', c['id'], 'support_atk', nm, {'required_units': _ru2, 'desc': s2.get('desc')}))
                if '支援防禦次數增加' in nm:
                    feats.append(('char', c['id'], 'support_def', nm, {'required_units': _ru2, 'desc': s2.get('desc')}))
            if sp2 and sp2.get('id') and (not s2 or s2.get('id') != sp2.get('id') or _s2raw != _sp2raw):
                enrich_traits(sp2.get('trait_set'))
                db.execute('INSERT INTO char_skills_sp VALUES(?,?,?,?,?,?,?,?)',
                           (c['id'], sk.get('sort'), sk.get('level'), sp2.get('sp'), sp2.get('name'),
                            sp2.get('desc'), json.dumps(sp2.get('trait_set'), ensure_ascii=False), sp2.get('id')))
        # 能力特性提取（SP 版单独存 char_abilities_sp，仅存与基础版不同的槽位）
        for a in (c.get('abilities') or []):
            ab = a.get('ability')
            absp = a.get('ability_sp')
            _abRaw = json.dumps(ab.get('traits') or [], sort_keys=True, ensure_ascii=False) if ab else ''
            _abSpRaw = json.dumps(absp.get('traits') or [], sort_keys=True, ensure_ascii=False) if absp else ''
            if ab:
                det = ab.get('detail') or {}
                nm = det.get('name') or ''
                trs = ab.get('traits') or []
                enrich_traits(trs)
                db.execute('INSERT INTO char_abilities VALUES(?,?,?,?,?)',
                           (c['id'], a.get('sort'), a['ability_id'], nm, json.dumps(trs, ensure_ascii=False)))
                _scan_ability_features(feats, 'char', c['id'], nm, trs)
            if absp and absp.get('id') and (not ab or ab.get('id') != absp.get('id') or _abRaw != _abSpRaw):
                dsp = absp.get('detail') or {}
                trs2 = absp.get('traits') or []
                enrich_traits(trs2)
                db.execute('INSERT INTO char_abilities_sp VALUES(?,?,?,?,?)',
                           (c['id'], a.get('sort'), absp.get('id'), dsp.get('name') or '', json.dumps(trs2, ensure_ascii=False)))
    counts['characters'] = n

    # ---------- 武器 ----------
    wd = find_dict('gget_weapon.html', 'weapons')
    n = nt = 0
    for w in (wd or {}).get('weapons', []):
        g = w.get('growth') or {}
        db.execute('''INSERT INTO weapons VALUES(
          :id,:unit_id,:name,:type,:work_type,:aa,:wa,:power,:en,:ammo,:r1,:r2,:hit,:crit,:ssp,
          :wsc,:wtc,:name,'scrape',:now,:ver)''', dict(
            id=w['id'], unit_id=w['unit_id'], name=w['name'], type=w['type'], work_type=w.get('work_type'),
            aa=w.get('attack_attr'), wa=w.get('weapon_attr'), power=w.get('power'), en=w.get('en'),
            ammo=w.get('ammo'), r1=w.get('range_min'), r2=w.get('range_max'),
            hit=w.get('hit_rate'), crit=w.get('critical_rate'), ssp=1 if w.get('is_ssp') else 0,
            wsc=json.dumps(g.get('wsc'), ensure_ascii=False), wtc=json.dumps(g.get('wtc'), ensure_ascii=False),
            now=NOW, ver=VERSION))
        n += 1
        for t in (g.get('wtc') or []):
            tr = t.get('trait') or {}
            if not tr.get('trait_type'):
                continue
            db.execute('INSERT INTO weapon_traits VALUES(?,?,?,?,?,?,?)',
                       (w['id'], t.get('level'), tr.get('trait_type'), tr.get('trait_value'),
                        str(tr.get('target_condition_set_id') or ''), (tr.get('desc') or '').replace('\n', ' '), ''))
            nt += 1
    counts['weapons'] = n
    counts['weapon_traits'] = nt

    # ---------- 武器完整效果（SSR 解析: data/weapon_fx_ssr.json, 解析 wtc 引用的效果主表） ----------
    wfx = os.path.join(HERE, 'weapon_fx_ssr.json')
    nfx = 0
    if os.path.exists(wfx):
        try:
            fxm = json.load(open(wfx, encoding='utf-8'))
            for wid_s, lvs in fxm.items():
                wid = int(wid_s)
                for lv_s, arr in (lvs or {}).items():
                    for si, e in enumerate(arr or []):
                        db.execute('INSERT INTO weapon_fx VALUES(?,?,?,?,?)',
                                   (wid, int(lv_s), si, e.get('name') or '', e.get('desc') or ''))
                        nfx += 1
            # 自带额外行动: 武器效果含「额外行动」→ 该机体特性
            seen = set()
            for uid, wname, fname, fdesc in db.execute('''SELECT w.unit_id, w.name, f.name, f.desc
                    FROM weapon_fx f JOIN weapons w ON w.id=f.weapon_id
                    WHERE f.name LIKE '%额外行动%' OR f.desc LIKE '%额外行动%' '''):
                if (uid, wname) in seen: continue
                seen.add((uid, wname))
                feats.append(('unit', uid, 'auto_extra_action', wname + '（' + (fname or '额外行动') + '）', {'desc': fdesc or fname}))
            seen = set()
            for wid, uid, wname, power, wscj, fname, fdesc in db.execute('''SELECT w.id, w.unit_id, w.name, w.power, w.wsc_json, f.name, f.desc
                    FROM weapon_fx f JOIN weapons w ON w.id=f.weapon_id
                    WHERE f.name LIKE '%先发攻击%' OR f.desc LIKE '%先发攻击%' '''):
                if (uid, wname) in seen: continue
                seen.add((uid, wname))
                lvp = power
                try:
                    wsc = json.loads(wscj or '[]')
                    if wsc:
                        lvp = int(power * (wsc[-1].get('power') or 100) / 100)
                except Exception:
                    pass
                feats.append(('unit', uid, 'preemptive', wname + '（先发攻击）', {'desc': fdesc or fname, 'power': lvp, 'wid': wid}))
        except Exception as e:
            print('weapon_fx load warn:', e)
    # ---------- 手动收录: 官网缺失的武器固有「武装效果」(data/manual_weapon_fx.json) ----------
    mwx = os.path.join(HERE, 'manual_weapon_fx.json')
    if os.path.exists(mwx):
        try:
            mw = json.load(open(mwx, encoding='utf-8')) or {}
            for wid_s, e in (mw.get('effects') or {}).items():
                wid = int(wid_s)
                if db.execute('SELECT 1 FROM weapon_fx WHERE weapon_id=? LIMIT 1', (wid,)).fetchone():
                    continue          # 官网已有该武器效果行 → 让位
                for lv in (1, 2, 3, 4, 5):
                    db.execute('INSERT INTO weapon_fx VALUES(?,?,?,?,?)', (wid, lv, 0, e.get('name') or '', e.get('desc') or ''))
                    nfx += 1
        except Exception as e:
            print('manual_weapon_fx warn:', e)
    counts['weapon_fx'] = nfx

    # ---------- SSP 核心解放（满强化）: 武器效果词条追加（来自 gget_weapon units[].ssp_config.cores[].releases[].weapon_effect） ----------
    nssp = 0
    try:      # 简繁等价去重（抓取侧是简体, 核心解放 desc 可能为繁体, 转换前先对齐比较）
        import opencc as _oc2
        _cc2 = _oc2.OpenCC('t2s')
        _s2s = lambda s: _cc2.convert(s)
    except Exception:
        _s2s = lambda s: s
    _wd2 = find_dict('gget_weapon.html', 'units') or {}
    for _k, _uu in (_wd2.get('units') or {}).items():
        _ssp = (_uu or {}).get('ssp_config') or {}
        for _core in (_ssp.get('cores') or []):
            for _rel in (_core.get('releases') or []):
                _we = _rel.get('weapon_effect')
                if not _we:
                    continue
                _wt = _we.get('weapon_trait') or {}
                _tw = _we.get('target_weapon_id')
                _ds = (_wt.get('desc') or '').strip()
                if _tw and _ds:
                    lvs = [r[0] for r in db.execute('SELECT DISTINCT level FROM weapon_fx WHERE weapon_id=?', [_tw])]
                    if not lvs:
                        lvs = [1, 2, 3, 4, 5]
                    ex = db.execute('SELECT COUNT(*) FROM weapon_fx WHERE weapon_id=? AND (desc=? OR desc=?)', [_tw, _ds, _s2s(_ds)]).fetchone()[0]
                    if not ex:
                        for lv in lvs:
                            db.execute('INSERT INTO weapon_fx VALUES(?,?,?,?,?)', (_tw, lv, 90, '', _ds))
                            nssp += 1
    counts['ssp_fx'] = nssp

    # ---------- SSP核心「(且最大值提升3%)」: SSP武器 武装POWER效果+3（追加在既有全部POWER效果之上;
    #            非SSP的固有+3已包含在数值内, 不加——与soshage排行口径一致） ----------
    np3 = 0
    for (wid,) in db.execute("""SELECT DISTINCT w.id FROM weapons w JOIN weapon_fx f ON f.weapon_id=w.id
                                WHERE f.desc LIKE '%最大值提升3%' AND w.is_ssp=1"""):
        for (tt,) in db.execute('SELECT DISTINCT trait_type FROM weapon_traits WHERE weapon_id=?', [wid]).fetchall():
            if tt not in (44, 45, 81, 82, 91, 92):    # 与 engine.js POWER_TRAITS 一致
                continue
            lvs = [l for (l,) in db.execute('SELECT DISTINCT level FROM weapon_traits WHERE weapon_id=? AND trait_type=?', [wid, tt])]
            for lv in lvs:
                db.execute('INSERT INTO weapon_traits VALUES(?,?,?,?,?,?,?)', (wid, lv, tt, 3, '1000001', '', ''))
                np3 += 1
    counts['ssp_p3'] = np3

    # ---------- 武器使用限制（SSR 解析: data/weapon_use_ssr.json） ----------
    wuse = os.path.join(HERE, 'weapon_use_ssr.json')
    nuse = 0
    if os.path.exists(wuse):
        try:
            um = json.load(open(wuse, encoding='utf-8'))
            unmapped = set()
            for wid_s, lines in um.items():
                for si, t in enumerate(lines or []):
                    t2 = translate_use(t, unmapped)
                    db.execute('INSERT INTO weapon_use VALUES(?,?,?)', (int(wid_s), si, t2))
                    nuse += 1
            if unmapped:
                print('weapon_use unmapped EN:', sorted(unmapped)[:12])
        except Exception as e:
            print('weapon_use load warn:', e)
    counts['weapon_use'] = nuse
    # 注意: SSP武器本体没有「战意为超强势以上」限制(游戏实测 强化巨剑SSP vs 强化巨剑);
    # 该限制仅来自武器 tension>=4(抓取侧写入), 此处不再对 is_ssp 统一追加

    # ---------- 固有効果「武装效果的效果值UP(且最大值提升2%)」: effect=280010 且核心解放未覆盖时兜底 ----------
    nfu = 0
    try:
        _meta = json.load(open(os.path.join(HERE, 'weapon_meta_ssr.json'), encoding='utf-8'))
    except Exception:
        _meta = {}
    for _k, _mv in (_meta or {}).items():
        if (_mv or {}).get('effect') != 280010:
            continue
        _wid = int(_k)
        _ex = db.execute("SELECT COUNT(*) FROM weapon_fx WHERE weapon_id=? AND desc LIKE '%最大值提升%'", [_wid]).fetchone()[0]
        if _ex:
            continue
        _lvs = [r[0] for r in db.execute('SELECT DISTINCT level FROM weapon_traits WHERE weapon_id=?', [_wid])] or [1, 2, 3, 4, 5]
        for _lv in _lvs:
            db.execute('INSERT INTO weapon_fx VALUES(?,?,?,?,?)', (_wid, _lv, 91, '', '武装效果的效果值UP(且最大值提升2%)'))
            nfu += 1
    counts['fx280010'] = nfu

    # ---------- 武器特性标记（排行显示: 先发攻击/额外行动/降防/无视防御/降攻 等） ----------
    WFLAGS = [
        ('先发攻击', ('先发攻击',)),
        ('额外行动', ('额外行动',)),
        ('降防', ('防御力减少', '防御减少', '防御降低', '目标防御减少')),
        ('无视防御', ('减轻无效', '贯穿', '无视')),
        ('降攻', ('攻击力减少', '武装POWER下降', '攻击力降低')),
        ('降机动', ('机动力减少', '机动力降低')),
        ('降命中', ('命中率减少',)),
        ('降射程', ('最大射程降低', '最大射程减少')),
        ('降移动', ('移动力下降',)),
    ]
    wflags = {}
    try:
        for wid, fname, fdesc in db.execute("SELECT weapon_id, name, IFNULL(desc,'') FROM weapon_fx"):
            t = (fname or '') + ' ' + fdesc
            for fi, (flag, kws) in enumerate(WFLAGS):
                if any(k in t for k in kws):
                    wflags.setdefault(wid, {})[fi] = flag
    except Exception as e:
        print('weapon_flag scan warn:', e)
    nfl = 0
    for wid, fs in wflags.items():
        for si, fi in enumerate(sorted(fs)):
            db.execute('INSERT INTO weapon_flag VALUES(?,?,?)', (wid, si, fs[fi]))
            nfl += 1
    counts['weapon_flag'] = nfl

    # ---------- 能力/技能字典 ----------
    ab = find_list('gget_ability.html', 'ability_type')
    for a in ab or []:
        det = a.get('detail') or {}
        db.execute('INSERT OR REPLACE INTO abilities VALUES(?,?,?,?,?)',
                   (a['id'], a.get('ability_type'), det.get('name'), a.get('icon'),
                    json.dumps(a.get('traits'), ensure_ascii=False)))
    counts['abilities'] = len(ab or [])

    sk = find_list('gget_skill.html', 'sp')
    for a in sk or []:
        db.execute('INSERT OR REPLACE INTO skills VALUES(?,?,?,?,?,?,?)',
                   (a['id'], a.get('name'), a.get('desc'), a.get('sp'), a.get('duration'),
                    a.get('rarity'), json.dumps(a.get('trait_set'), ensure_ascii=False)))
    counts['skills'] = len(sk or [])

    # ---------- 武器效果字典（/effect 页表格解析） ----------
    ne = 0
    try:
        s = open(os.path.join(RAW, 'gget_effect.html'), encoding='utf-8', errors='replace').read()
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', s, re.S)
        for r in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)
            if len(cells) < 2:
                continue
            def clean(x):
                x = re.sub(r'<[^>]+>', '', x)
                return re.sub(r'\s+', ' ', x).strip()
            nm, ds = clean(cells[-2]), clean(cells[-1])
            if not nm:
                continue
            m = re.search(r'effect/(\d+)', r)
            eid = m.group(1) if m else ''
            db.execute('INSERT INTO effects VALUES(?,?,?)', (eid, nm, ds))
            ne += 1
    except Exception as e:
        print('effect parse warn:', e)
    counts['effects'] = ne

    # ---------- 战舰 ----------
    sup = find_list('gget_supporter.html', 'lb_skills')
    n = 0
    for p in sup or []:
        lb = p.get('lb_skills') or []
        leader_desc, leader_target, lbs = '', {}, []
        for step in lb:
            ls = step.get('leader_skill') or {}
            if ls.get('desc') and not leader_desc:
                leader_desc = ls.get('desc')
            for skc in (ls.get('skills') or []):
                for tc in (skc.get('trait_condition') or []):
                    for k in ('unit_tags', 'unit_series'):
                        if tc.get(k):
                            leader_target.setdefault(k, []).append(str(tc[k]))
                    if isinstance(tc.get('series'), dict):
                        leader_target.setdefault('series_name', []).append(tc['series'].get('name'))
            lbs.append({'step': step.get('limit_break_step'), 'leader': ls.get('desc')})
        # 详情页 Support Skill 文本
        sk_name = sk_desc = None
        dp = os.path.join(RAW, f'supp_{p["id"]}.html')
        if os.path.exists(dp):
            h = open(dp, encoding='utf-8', errors='replace').read()
            t = re.sub(r'<(script|style).*?</\1>', ' ', h, flags=re.S)
            t = re.sub(r'<[^>]+>', '\n', t)
            import html as H
            t = H.unescape(t)
            lines = [x.strip() for x in t.splitlines() if x.strip()]
            if 'Support Skills' in lines:
                i = lines.index('Support Skills')
                seg = lines[i + 1:i + 4]
                if seg:
                    sk_name = seg[0]
                    sk_desc = ' '.join(seg[1:])
        db.execute('''INSERT INTO supporters VALUES(
          :id,:name,:rarity,:icon,:hp,:atk,:ld,:lt,:sn,:sd,:lb,'scrape',:now,:ver)''', dict(
            id=p['id'], name=p['name'], rarity=p.get('rarity'), icon=p.get('icon'),
            hp=p.get('max_hp_addition_value'), atk=p.get('max_attack_addition_value'),
            ld=leader_desc, lt=json.dumps(leader_target, ensure_ascii=False),
            sn=sk_name, sd=sk_desc, lb=json.dumps(lbs, ensure_ascii=False), now=NOW, ver=VERSION))
        n += 1
        # 派生标签: Leader技能目标系列/标签 + Support技能类型
        stags = set()
        for tid in leader_target.get('unit_tags', []):
            nm = tagdict.get(int(tid)) if str(tid).isdigit() else None
            if nm:
                stags.add(nm)
        for sid in leader_target.get('unit_series', []):
            nm = ser.get(str(sid))
            if nm:
                stags.add(nm)
        for nm in leader_target.get('series_name', []):
            if nm:
                stags.add(nm)
        if sk_name:
            stags.add(sk_name)
        for nm in stags:
            db.execute('INSERT INTO supporter_tags VALUES(?,?)', (p['id'], nm))
    counts['supporters'] = n

    # ---------- 选择性零件 ----------
    mods = find_list('gget_formula.html', 'trait_set_id', 'series_id')
    n = 0
    for m in mods or []:
        det = m.get('detail') or {}
        db.execute('''INSERT INTO mods VALUES(:id,:name,:rarity,:icon,:series,:desc,:tr,'scrape',:now,:ver)''',
                   dict(id=m['id'], name=m.get('name'), rarity=m.get('rarity'), icon=m.get('icon'),
                        series=str(m.get('series_id')), desc=det.get('desc') or '',
                        tr=json.dumps(m.get('set'), ensure_ascii=False), now=NOW, ver=VERSION))
        n += 1
        for t in (m.get('tags') or []):
            if t.get('tag_id'):
                db.execute('INSERT INTO mod_tags VALUES(?,?)', (m['id'], t['tag_id']))
    counts['mods'] = n



    # ---------- 特性: 6移动 / 7移动（机体+驾驶员被动加成; 需特定驾驶员的行带 params.pilot 显示头像） ----------
    _tagid = {r[0]: r[1] for r in db.execute('SELECT id, name FROM tags')}
    _useries = {r[0]: str(r[1]) for r in db.execute('SELECT id, series_id FROM units')}
    _utags, _ctags = {}, {}
    for r in db.execute('SELECT ut.unit_id, t.name FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id'):
        _utags.setdefault(r[0], set()).add(r[1])
    for r in db.execute('SELECT ct.char_id, t.name FROM char_tags ct JOIN tags t ON t.id=ct.tag_id'):
        _ctags.setdefault(r[0], set()).add(r[1])

    def _ac_tags(ac):
        out = []
        for t in (ac.get('tags') or []):
            if isinstance(t, dict):
                nm = t.get('name') or (_tagid.get(t.get('id')) if t.get('id') else None)
                if nm:
                    out.append(nm)
        for x in str(ac.get('unit_tags') or '').split(','):
            x = x.strip()
            if x.isdigit() and int(x) in _tagid:
                out.append(_tagid[int(x)])
        return out

    def _ac_series(ac):
        s = ac.get('unit_series')
        if s:
            return str(s)
        sj = ac.get('series')
        return str(sj['id']) if isinstance(sj, dict) and sj.get('id') else ''

    _u_indep, _u_pilotcond, _u_cond, _pilot_side = {}, {}, {}, {}
    for _uid, _tj in db.execute('SELECT unit_id, traits_json FROM unit_abilities'):
        for _t in json.loads(_tj or '[]'):
            _tr = (_t or {}).get('trait') or {}
            _d = _tr.get('desc') or ''
            if not any(x in _d for x in ('移动力提升', '移動力提升', '移动范围提升', '移動範圍提升')):   # 简繁转换前运行; 含支援防御移动范围类
                continue
            _ac = _tr.get('active_condition') or {}
            if _ac.get('character_tags') or _ac.get('character_series') or _ac.get('character_ids'):
                _u_pilotcond.setdefault(_uid, _ac)      # 机体被动但需特定驾驶员(角色标签/系列)
                continue
            _tn = str(_ac.get('tension') or '')          # 战意/HP 条件被动: 计入但行内显示条件
            if 'SuperHigh' in _tn:
                _ct = '战意为「超强势」以上'
            elif 'Supercharged' in _tn:
                _ct = '战意为「超一击」以上'
            elif _ac.get('hp_rate_gte_threshold'):
                _ct = 'HP%d%%以上' % _ac['hp_rate_gte_threshold']
            elif _ac.get('hp_rate_lte_threshold') or _ac.get('use_hp_rate_lte_threshold'):
                _ct = 'HP%d%%以下' % (_ac.get('hp_rate_lte_threshold') or 0)
            elif _ac.get('en_rate_gte_threshold'):
                _ct = 'EN%d%%以上' % _ac['en_rate_gte_threshold']
            else:
                _ct = ''
            if _ct:
                _u_cond.setdefault(_uid, []).append(_ct)
            else:
                _u_indep[_uid] = _u_indep.get(_uid, 0) + 1   # 无条件 → 机体自身
    for _cid, _tj in db.execute('SELECT char_id, traits_json FROM char_abilities'):
        for _t in json.loads(_tj or '[]'):
            _tr = (_t or {}).get('trait') or {}
            _d = _tr.get('desc') or ''
            if not any(x in _d for x in ('移动力提升', '移動力提升', '移动范围提升', '移動範圍提升')):   # 简繁转换前运行; 含支援防御移动范围类
                continue
            _pilot_side.setdefault(_cid, []).append(_tr.get('active_condition') or {})

    def _unit_ok(uid, ac):
        ids = [int(x) for x in str(ac.get('unit_ids') or '').split(',') if x.strip()]
        if ids and uid not in ids:
            return False
        tn = _ac_tags(ac)
        if tn and not (set(tn) & _utags.get(uid, set())):
            return False
        ser = _ac_series(ac)
        if ser and ser != '0' and _useries.get(uid) != ser:
            return False
        return True

    def _pilot_for(ac):
        req = [t['name'] for t in (ac.get('character_tags') or []) if isinstance(t, dict) and t.get('name')]
        req_ids = [int(x) for x in str(ac.get('character_ids') or '').split(',') if x.strip()]
        if not req and not req_ids:
            return None
        for (cid,) in db.execute('SELECT id FROM characters ORDER BY id'):
            if req_ids and cid not in req_ids:
                continue
            if req and not (set(req) & _ctags.get(cid, set())):
                continue
            if _crole.get(cid) != 2:    # 只统计防御型驾驶员
                continue
            return cid
        return None

    _crole = {r[0]: r[1] for r in db.execute('SELECT id, role FROM characters')}   # 只统计防御型(role=2)驾驶员
    _def2 = lambda c: _crole.get(c) == 2
    _sd_unit_set = {r[0] for r in db.execute("SELECT u.id FROM units u JOIN unit_tags ut ON ut.unit_id=u.id JOIN tags t ON t.id=ut.tag_id WHERE t.name='SD高达'")}
    _sd_own = {}
    for _su in _sd_unit_set:
        _sn = db.execute('SELECT name FROM units WHERE id=?', [_su]).fetchone()[0]
        _sb = re.sub(r'\s*(\(|（)[^)）]*[)）]\s*$', '', _sn)
        for _cand in (_sn, _sb):
            _r2 = db.execute('SELECT id FROM characters WHERE name=?', [_cand]).fetchone()
            if _r2:
                _sd_own.setdefault(_r2[0], set()).add(_su)
                break

    _ssp_mov = {}   # SSP核心解放的移动力提升: release_function_type_index=3 且 status_up.unit_status_type_index=6 求和
    for _r3, _sj3 in db.execute("SELECT id, ssp_json FROM units WHERE ssp_json IS NOT NULL AND ssp_json != '' AND ssp_json != 'null'"):
        try:
            _d3 = json.loads(_sj3) or {}
            _mv3 = 0
            for _c3 in (_d3.get('cores') or []):
                for _rl3 in (_c3.get('releases') or []):
                    if _rl3.get('release_function_type_index') == 3:
                        _su3 = _rl3.get('status_up') or {}
                        if _su3.get('unit_status_type_index') == 6:
                            _mv3 += int(_su3.get('effect_value') or 0)
            if _mv3:
                _ssp_mov[_r3] = _mv3
        except Exception:
            pass

    for _uid, _base in db.execute('SELECT id, max_mov FROM units'):
        _ssp1 = _ssp_mov.get(_uid, 0)             # SSP强化 移动力+1 仅部分机体有(格拉布罗无; 里格·夏柯有)
        _gi = _u_indep.get(_uid, 0)
        _gpac = _u_pilotcond.get(_uid)
        _gp = 1 if _gpac else 0
        _pl = [cid for cid, acs in _pilot_side.items() if _def2(cid) and any(_unit_ok(_uid, a) for a in acs)]
        _psel = _pilot_for(_gpac) if _gpac else None
        _cands = {}
        if _uid in _sd_unit_set:                      # SD机体: 只能用专属驾驶员(不限角色)
            for _c2, _us in _sd_own.items():
                if _uid in _us:
                    _cands[_c2] = 1 if _c2 in _pl else 0
        else:                                          # 普通机体: 防御型驾驶员被动, 排除SD绑定驾驶员
            for _c2 in _pl:
                _cands[_c2] = _cands.get(_c2, 0) + 1
            if _psel and _def2(_psel) and not _sd_own.get(_psel):
                _cands[_psel] = _cands.get(_psel, 0) + _gp
        _best = max(_cands.values()) if _cands else 0
        _bpid = min([_c2 for _c2, _g2 in _cands.items() if _g2 == _best]) if _cands else None
        _conds = list(dict.fromkeys(_u_cond.get(_uid, [])))
        _ssp_txt = ' + SSP强化' if _ssp1 else ''
        _u_src = ' + '.join([x for x in (('机体被动' if _gi else ''), ('SSP强化' if _ssp1 else '')) if x])
        _c_src = ('机体被动(' + '、'.join(_conds) + ')' + _ssp_txt) if _conds else ''
        _unit_only = _base + _gi + _ssp1                        # 无条件(机体被动+SSP强化)
        _cond_only = _unit_only + len(_u_cond.get(_uid, []))    # 含战意/HP条件被动
        for _feat, _need in (('move6', 6), ('move7', 7)):
            if _unit_only >= _need:
                _lbl = f'移动{_base}' if _unit_only == _base else f'移动{_base}→{_unit_only}'   # 基础值已达标的行不显示 6→6
                feats.append(('unit', _uid, _feat, _lbl,
                              {'desc': (_u_src + '(无需特定驾驶员)') if _u_src else '机体(无需特定驾驶员)', 'pilot': 0, 'base': _base, 'total': _unit_only}))
            elif _bpid and _unit_only + _best >= _need:
                feats.append(('unit', _uid, _feat, f'移动{_base}→{_unit_only + _best}',
                              {'desc': '需驾驶员被动加成' + _ssp_txt, 'pilot': _bpid, 'base': _base, 'total': _unit_only + _best}))
            elif _conds and _cond_only >= _need:               # 需战意/HP条件被动
                feats.append(('unit', _uid, _feat, f'移动{_base}→{_cond_only}',
                              {'desc': _c_src + '(无需特定驾驶员)', 'pilot': 0, 'base': _base, 'total': _cond_only}))
            elif _conds and _bpid and _cond_only + _best >= _need:
                feats.append(('unit', _uid, _feat, f'移动{_base}→{_cond_only + _best}',
                              {'desc': '需驾驶员被动加成 + ' + _c_src, 'pilot': _bpid, 'base': _base, 'total': _cond_only + _best}))
    counts['move6'] = sum(1 for x in feats if x[2] == 'move6')
    counts['move7'] = sum(1 for x in feats if x[2] == 'move7')

    # ---------- 官方设定驾驶员: unit_default_char.json (gacha.bonus.character) ----------
    _dcf = os.path.join(HERE, 'unit_default_char.json')
    _dcn = 0
    if os.path.exists(_dcf):
        try:
            for _dk, _dv in json.load(open(_dcf, encoding='utf-8')).items():
                if _dv.get('char_id'):
                    db.execute('UPDATE units SET default_char_id=? WHERE id=?', (_dv['char_id'], int(_dk)))
                    _dcn += 1
        except Exception as _de:
            print('default_char load err:', _de)
    counts['default_char'] = _dcn

    # ---------- 写入特性 ----------
    db.executemany('INSERT INTO features VALUES(?,?,?,?,?)',
                   [(t, i, f, lb, json.dumps(pr, ensure_ascii=False)) for (t, i, f, lb, pr) in feats])
    counts['features'] = len(feats)

    # ---------- meta / update_log ----------
    db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('version', VERSION))
    db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('built_at', str(NOW)))
    db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('counts', json.dumps(counts, ensure_ascii=False)))
    db.execute('INSERT INTO update_log(version, applied_at, summary_json, snapshot_path) VALUES(?,?,?,?)',
               (VERSION, NOW, json.dumps({'type': 'full_build', 'counts': counts}, ensure_ascii=False), ''))

    # ---------- SSP 改装核心派生表(核心level≤10 + initial_release): 武器效果 / 能力变化 ----------
    # weapon_effect: 内层trait为数值类(9/10/25/26/39/44/45/81/82/91/92)且目标武器lv5无同型 → 计入(参考站合并规则: 同型仅并描述不改数值)
    # ability_change: before=0 新增 / before≠0 替换(参考站 F() 语义); traits 与 unit_abilities 同构
    _WE_TYPES = {9, 10, 25, 26, 39, 44, 45, 81, 82, 91, 92}
    we_rows, ua_rows = [], []
    for _uid, _sspj in db.execute("SELECT id, ssp_json FROM units WHERE ssp_json IS NOT NULL AND ssp_json != '' AND ssp_json != 'null'"):
        try:
            _d = json.loads(_sspj)
        except Exception:
            continue
        _rels = []
        if _d.get('initial_release'):
            _rels.append(_d['initial_release'])
        for _core in (_d.get('cores') or []):
            if (_core.get('level') or 0) <= 10:
                _rels += (_core.get('releases') or [])
        for _rel in _rels:
            _we = _rel.get('weapon_effect')
            if _we and _we.get('target_weapon_id'):
                _wt = _we.get('weapon_trait') or {}
                _it = _wt.get('trait') or {}
                _tt, _tv = _it.get('trait_type'), (_it.get('trait_value') or 0)
                if _tt in _WE_TYPES:
                    _dup = db.execute('SELECT 1 FROM weapon_traits WHERE weapon_id=? AND level=5 AND trait_type=?',
                                      (_we['target_weapon_id'], _tt)).fetchone()
                    if not _dup:
                        we_rows.append((_we['target_weapon_id'], _tt, _tv, _wt.get('desc') or '', _wt.get('name') or ''))
                elif _tt == 88:   # 武装效果值UP(88): 数值标记行, 供效果值显示叠加(引擎忽略)
                    we_rows.append((_we['target_weapon_id'], 88, _tv, _wt.get('desc') or '', _wt.get('name') or ''))
            _ac = _rel.get('ability_change')
            if _ac and (_ac.get('ability') or {}).get('traits'):
                _ab = _ac['ability']
                enrich_traits(_ab['traits'])
                ua_rows.append((_uid, _ac.get('before_ability_id') or 0, _ac.get('after_ability_id') or 0,
                                (_ab.get('detail') or {}).get('name') or '',
                                json.dumps(_ab['traits'], ensure_ascii=False)))
    db.executemany('INSERT OR REPLACE INTO weapon_ssp_traits VALUES(?,?,?,?,?)', we_rows)
    db.executemany('INSERT OR REPLACE INTO unit_abilities_ssp VALUES(?,?,?,?,?)', ua_rows)
    counts['weapon_ssp_traits'] = len(we_rows)
    counts['unit_abilities_ssp'] = len(ua_rows)

    convert_to_simplified(db)

    # ---------- 手动补充角色(官网尚未收录; 同名官方数据出现后自动让位) ----------
    # 必须放在 convert_to_simplified 之后: 克隆查找/同名去重都按简体名进行
    mc_path = os.path.join(HERE, 'manual_chars.json')
    if os.path.exists(mc_path):
        try:
            mc = json.load(open(mc_path, encoding='utf-8'))
        except Exception:
            mc = {}
        for m in mc.get('chars', []):
            if db.execute('SELECT 1 FROM characters WHERE name=?', [m['name']]).fetchone():
                continue                                   # 官网已收录 → 用官方数据
            mx = m['max']; spx = m.get('sp') or {}
            sj = {'ranged': round(mx['ranged'] / 6.5), 'melee': round(mx['melee'] / 6.5),
                  'defense': round(mx['defense'] / 6.5), 'reaction': round(mx['reaction'] / 6.5),
                  'awaken': round(mx['awaken'] / 6.5)}
            sj.update({'max_ranged': mx['ranged'], 'max_melee': mx['melee'], 'max_defense': mx['defense'],
                       'max_reaction': mx['reaction'], 'max_awaken': mx['awaken']})
            for k in ('ranged', 'melee', 'defense', 'reaction', 'awaken'):
                if spx.get(k) is not None:
                    sj['sp_max_' + k] = spx[k]
            db.execute('''INSERT INTO characters(id,name,sort_name,rarity,role,series_set_id,icon,abbreviation,is_playable,
              ranged,melee,defense,reaction,awaken,max_ranged,max_melee,max_defense,max_reaction,max_awaken,
              sp_max_ranged,sp_max_melee,sp_max_defense,sp_max_reaction,sp_max_awaken,
              stats_json,name_hant,source,updated_at,data_version)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (m['id'], m['name'], m.get('sort_name') or m['name'], m['rarity'], m['role'],
               str(m.get('series_set_id') or ''), m.get('icon') or '', '', 1,
               sj['ranged'], sj['melee'], sj['defense'], sj['reaction'], sj['awaken'],
               mx['ranged'], mx['melee'], mx['defense'], mx['reaction'], mx['awaken'],
               spx.get('ranged'), spx.get('melee'), spx.get('defense'), spx.get('reaction'), spx.get('awaken'),
               json.dumps(sj, ensure_ascii=False), m.get('name_hant') or m['name'], 'manual', NOW, VERSION))
            for sk in m.get('skills', []):
                src = db.execute('SELECT traits_json, skill_id FROM char_skills WHERE name=? LIMIT 1',
                                 [sk.get('clone') or sk['name']]).fetchone()
                db.execute('INSERT INTO char_skills VALUES(?,?,?,?,?,?,?,?)',
                           (m['id'], sk.get('sort'), sk.get('unlock_level'), sk.get('sp'), sk['name'], sk.get('desc'),
                            src[0] if src else json.dumps(sk.get('traits') or [], ensure_ascii=False),
                            src[1] if src else sk.get('skill_id')))
            for ab in m.get('abilities', []):
                src = db.execute('SELECT traits_json, ability_id FROM char_abilities WHERE name=? LIMIT 1',
                                 [ab.get('clone') or ab['name']]).fetchone()
                db.execute('INSERT INTO char_abilities VALUES(?,?,?,?,?)',
                           (m['id'], ab.get('sort'), src[1] if src else ab.get('ability_id'), ab['name'],
                            src[0] if src else json.dumps(ab.get('traits') or [], ensure_ascii=False)))
            _ntag = 0
            for tname in (m.get('tags') or []):            # 标签按名称查id(须在 convert_to_simplified 之后, 见上)
                trow = db.execute('SELECT id FROM tags WHERE name=?', [tname]).fetchone()
                if trow:
                    db.execute('INSERT OR REPLACE INTO char_tags VALUES(?,?)', (m['id'], trow[0]))
                    _ntag += 1
                else:
                    print(f"  manual char tag 未找到: {tname}")
            counts['characters'] = counts.get('characters', 0) + 1
            print(f"  manual char: {m['name']} (id {m['id']}, 技能{len(m.get('skills', []))} 能力{len(m.get('abilities', []))} 标签{_ntag})")

    # ---------- 手动补充机体(官网尚未收录; 同名官方数据出现后自动让位) ----------
    # 亦须在 convert_to_simplified 之后: 能力按简体名克隆、标签按简体名查id、系列按名新建
    mu_path = os.path.join(HERE, 'manual_units.json')
    if os.path.exists(mu_path):
        try:
            mu = json.load(open(mu_path, encoding='utf-8'))
        except Exception:
            mu = {}
        for m in mu.get('units', []):
            if db.execute('SELECT 1 FROM units WHERE name=?', [m['name']]).fetchone():
                continue                                   # 官网已收录 → 用官方数据
            mx = m.get('max') or m['sp']                   # max=等级上限插值目标(★0口径; ★3面板=floor(max×1.4)); 未提供时暂以 sp 占位
            spx = m.get('sp') or mx
            _tr = m.get('terrain') or {}
            _st = {'hp': 0, 'en': 0, 'attack': 0, 'defense': 0, 'mobility': 0, 'movement': m.get('mov'),
                   'max_hp': mx['hp'], 'max_en': mx['en'], 'max_attack': mx['atk'], 'max_defense': mx['def'],
                   'max_mobility': mx['mob'], 'max_movement': m.get('mov'),
                   'sp_max_hp': spx['hp'], 'sp_max_en': spx['en'], 'sp_max_attack': spx['atk'],
                   'sp_max_defense': spx['def'], 'sp_max_mobility': spx['mob'], 'sp_max_movement': m.get('mov')}
            _ssp = m.get('ssp') or {}
            _ssk = {'hp': 'ssp_max_hp', 'en': 'ssp_max_en', 'atk': 'ssp_max_attack',
                    'def': 'ssp_max_defense', 'mob': 'ssp_max_mobility'}
            _ssj = {'stats': {_ssk[k]: v for k, v in _ssp.items() if k in _ssk}, 'cores': m.get('ssp_cores') or []}
            if m.get('series_name'):                       # 临时段系列行(官方收录后原样保留, 不影响官方数据)
                db.execute('INSERT OR REPLACE INTO series VALUES(?,?)', (str(m.get('series_id') or ''), m['series_name']))
            db.execute('''INSERT INTO units VALUES(
              :id,:name,:short_name,:rarity,:role,:tr,:ult,:series_set_id,:series_id,:icon,:models,:body_type,:area,:defend,:evade,
              :hp,:en,:atk,:df,:mob,:mov,:max_hp,:max_en,:max_atk,:max_def,:max_mob,:max_mov,
              :sp_max_hp,:sp_max_en,:sp_max_atk,:sp_max_def,:sp_max_mob,:sp_max_mov,
              :t_space,:t_atm,:t_ground,:t_surface,:t_water,:desc,:stats_json,:ssp_json,:name_hant,
              'manual',:now,:ver,:dcid,:ssj)''', dict(
                id=m['id'], name=m['name'], short_name=m.get('short_name') or m['name'], rarity=m.get('rarity'),
                role=m.get('role'), tr=m.get('tr'), ult=1 if m.get('ult') else 0,
                series_set_id=str(m.get('series_set_id') or ''), series_id=str(m.get('series_id') or ''),
                icon=m.get('icon') or '', models=m.get('models') or '',
                body_type=m.get('body_type'), area=m.get('area'),
                defend=1 if m.get('defend') else 0, evade=1 if m.get('evade') else 0,
                hp=0, en=0, atk=0, df=0, mob=0, mov=m.get('mov'),
                max_hp=mx['hp'], max_en=mx['en'], max_atk=mx['atk'], max_def=mx['def'], max_mob=mx['mob'],
                max_mov=m.get('mov'),
                sp_max_hp=spx['hp'], sp_max_en=spx['en'], sp_max_atk=spx['atk'], sp_max_def=spx['def'],
                sp_max_mob=spx['mob'], sp_max_mov=m.get('mov'),
                t_space=_tr.get('space'), t_atm=_tr.get('atm'), t_ground=_tr.get('ground'),
                t_surface=_tr.get('surface'), t_water=_tr.get('water'),
                desc=m.get('desc') or '', stats_json=json.dumps(_st, ensure_ascii=False),
                ssp_json=json.dumps(_ssj, ensure_ascii=False), name_hant=m.get('name_hant') or m['name'],
                now=NOW, ver=VERSION, dcid=m.get('default_char_id'),
                ssj=json.dumps([str(x) for x in (m.get('series_set_ids') or ([str(m.get('series_id'))] if m.get('series_id') else []))], ensure_ascii=False)))
            _ntag = _nab = _nw = _nwt = _nfx = _nfu = _nfl = 0
            for tname in (m.get('tags') or []):            # 标签按名称查id
                trow = db.execute('SELECT id FROM tags WHERE name=?', [tname]).fetchone()
                if trow:
                    db.execute('INSERT OR REPLACE INTO unit_tags VALUES(?,?)', (m['id'], trow[0]))
                    _ntag += 1
                else:
                    print(f"  manual unit tag 未找到: {tname}")
            for ab in m.get('abilities', []):              # 能力按官方同名条目克隆 traits
                src = db.execute('SELECT traits_json, ability_id FROM unit_abilities WHERE name=? LIMIT 1',
                                 [ab.get('clone') or ab['name']]).fetchone()
                db.execute('INSERT INTO unit_abilities VALUES(?,?,?,?)',
                           (m['id'], src[1] if src else ab.get('ability_id'), ab['name'],
                            src[0] if src else json.dumps(ab.get('traits') or [], ensure_ascii=False)))
                if src:
                    _scan_ability_features(feats, 'unit', m['id'], ab['name'], json.loads(src[0]))
                _nab += 1
            if m.get('device'):                            # 装置(如防护盾防御) → features 行(feats 已落库, 此处直插)
                dv = m['device']
                db.execute('INSERT INTO features VALUES(?,?,?,?,?)',
                           ('unit', m['id'], dv['feature'], dv.get('label') or dv['feature'],
                            json.dumps({'value': dv.get('value')}, ensure_ascii=False)))
            for w in m.get('weapons', []):                 # 武器行: id=unit_id*100+seq(90+=SSP/变体, 同官方规则)
                wid = m['id'] * 100 + int(w.get('seq') or 1)
                db.execute('''INSERT INTO weapons VALUES(
                  :id,:unit_id,:name,:type,:work_type,:aa,:wa,:power,:en,:ammo,:r1,:r2,:hit,:crit,:ssp,
                  :wsc,:wtc,:name_hant,'manual',:now,:ver)''', dict(
                    id=wid, unit_id=m['id'], name=w['name'], type=w.get('type'), work_type=0,
                    aa=w.get('attack_attr'), wa=w.get('weapon_attr'), power=w.get('power'), en=w.get('en'),
                    ammo=w.get('ammo'), r1=w.get('range_min'), r2=w.get('range_max'),
                    hit=w.get('hit_rate'), crit=w.get('crit_rate'), ssp=1 if w.get('is_ssp') else 0,
                    wsc=json.dumps([{'level': lv, 'power': 100 + 5 * (lv - 1), 'en': 90 if lv == 5 else 100,
                                     'hit_rate': 100, 'crit_rate': 100} for lv in range(1, 6)], ensure_ascii=False),
                    wtc='[]', name_hant=w.get('name_hant') or w['name'], now=NOW, ver=VERSION))
                for lv in range(1, 6):
                    for t in (w.get('traits') or []):
                        db.execute('INSERT INTO weapon_traits VALUES(?,?,?,?,?,?,?)',
                                   (wid, lv, t['trait_type'], t['trait_value'], '1000001', '', t.get('cond') or ''))
                        _nwt += 1
                    for f in (w.get('fx') or []):
                        db.execute('INSERT INTO weapon_fx VALUES(?,?,?,?,?)',
                                   (wid, lv, f.get('sort') or 0, f.get('name') or '', f.get('desc') or ''))
                        _nfx += 1
                for si, tx in enumerate(w.get('use') or []):
                    db.execute('INSERT INTO weapon_use VALUES(?,?,?)', (wid, si, tx))
                    _nfu += 1
                _ft = (w.get('fx') or [])
                for fi, (flag, kws) in enumerate(WFLAGS):  # 武器标记(排行/图鉴chip): 同官方 fx 文本扫描
                    if any(k in ((f.get('name') or '') + ' ' + (f.get('desc') or '')) for f in _ft for k in kws):
                        db.execute('INSERT INTO weapon_flag VALUES(?,?,?)', (wid, _nfl, flag))
                        _nfl += 1
                _nw += 1
            counts['units'] = counts.get('units', 0) + 1
            print(f"  manual unit: {m['name']} (id {m['id']}, 标签{_ntag} 能力{_nab} 武器{_nw}"
                  f"(特性{_nwt} 效果{_nfx} 限制{_nfu} 标记{_nfl}))")

    # ---------- 武器条件效果标记: fx「发起对战的敌方包含「X」…防御力减少N%」→ 对应 type9 trait 标 cond ----------
    nwt = 0
    _tag_all = {r[0] for r in db.execute('SELECT name FROM tags')}
    _ser_all = {r[0] for r in db.execute('SELECT name FROM series')}
    _cre = re.compile(r'(?:发起|發起)对战的敌方包含[「"“]([^」"”]+)[」"”]\s*(系列)?')
    _vre = re.compile(r'防御力减少(\d+)%')
    for (_w, _lv, _d2) in db.execute("SELECT weapon_id, level, desc FROM weapon_fx WHERE desc LIKE '%对战的敌方包含%'").fetchall():
        _m = _cre.search(_d2 or '')
        if not _m:
            continue
        _v = _vre.search(_d2 or '')
        _cn = _m.group(1)
        _pool = _ser_all if _m.group(2) else _tag_all
        if _cn not in _pool:      # 文案译名归一(吉翁→自护 / 手臂→-ARM)
            for _cand in (_cn.replace('吉翁', '自护'), _cn.replace('自护', '吉翁'), _cn.replace('手臂', '-ARM'), _cn.replace('-ARM', '手臂')):
                if _cand in _pool:
                    _cn = _cand
                    break
        _cd = json.dumps({'series': {'name': _cn}} if _m.group(2) else {'tags': [{'name': _cn}]}, ensure_ascii=False)
        if _v:      # 「以敌方防御力减少N%的状态攻击」→ 标记同值的 type9 行
            _row = db.execute("SELECT rowid FROM weapon_traits WHERE weapon_id=? AND level=? AND trait_type=9 AND trait_value=? AND (cond IS NULL OR cond='') LIMIT 1",
                              (_w, _lv, -int(_v.group(1)))).fetchone()
            if _row:
                db.execute('UPDATE weapon_traits SET cond=? WHERE rowid=?', (_cd, _row[0]))
                nwt += 1
                continue
        # 「防御力减少的武装效果值增加N%」→ 标记数据中已存在的常量 -N 行(仅条件满足时生效)
        _mk = re.search(r'防御力减少的武装效果值增加(\d+)%', _d2 or '')
        if _mk:
            _row = db.execute("SELECT rowid FROM weapon_traits WHERE weapon_id=? AND level=? AND trait_type=9 AND trait_value=? AND (cond IS NULL OR cond='') LIMIT 1",
                              (_w, _lv, -int(_mk.group(1)))).fetchone()
            if _row:
                db.execute('UPDATE weapon_traits SET cond=? WHERE rowid=?', (_cd, _row[0]))
                nwt += 1
                continue
        # 「武装POWER提升的最大值增加N%」→ 标记功率类型常量 +N 行
        _mk2 = re.search(r'武装POWER提升的最大值增加(\d+)%', _d2 or '')
        if _mk2:
            _row = db.execute("SELECT rowid FROM weapon_traits WHERE weapon_id=? AND level=? AND trait_type IN (44,45,81,82,91,92) AND trait_value=? AND (cond IS NULL OR cond='') LIMIT 1",
                              (_w, _lv, int(_mk2.group(1)))).fetchone()
            if _row:
                db.execute('UPDATE weapon_traits SET cond=? WHERE rowid=?', (_cd, _row[0]))
                nwt += 1
    counts['wt_cond'] = nwt

    # ---------- gamekee 图鉴补充（使用限制/武装效果 兜底, 需在 zh-CN 名称覆盖之后） ----------
    gkp = os.path.join(HERE, 'gamekee_units.json')
    ngk_use = ngk_fx = 0
    gk_miss = []
    if os.path.exists(gkp):
        try:
            gk = json.load(open(gkp, encoding='utf-8'))

            def norm(s):
                s = re.sub(r'[【\[].*?[】\]]', '', (s or ''))
                for a, b in (('（', '('), ('）', ')'), ('／', '/'), ('·', '·')):
                    s = s.replace(a, b)
                return s.replace(' ', '').replace('　', '').strip()

            units_by_name = {}
            for uid, nm in db.execute('SELECT id, name FROM units'):
                units_by_name.setdefault(norm(nm), uid)
            wname_re = re.compile(r'<\w+>$')
            for eid, ent in gk.items():
                uid = units_by_name.get(norm(ent.get('name')))
                if not uid:
                    if ent.get('weapons'):
                        gk_miss.append(ent.get('name'))
                    continue
                our = {}
                for wid, wname in db.execute('SELECT id, name FROM weapons WHERE unit_id=?', [uid]):
                    our.setdefault(norm(wname), []).append(wid)
                for gw in ent.get('weapons') or []:
                    gname = norm(wname_re.sub('', gw.get('name') or ''))
                    wids = our.get(gname)
                    if not wids:
                        m = [w for k, v in our.items() if gname and (gname in k or k in gname) for w in v]
                        wids = m if len(set(m)) == 1 else []
                    attrs = gw.get('attrs') or {}
                    ul = (attrs.get('使用限制') or '').strip()
                    ef = (attrs.get('武装效果') or '').strip()
                    for wid in wids:
                        has_use = db.execute('SELECT COUNT(*) FROM weapon_use WHERE weapon_id=?', [wid]).fetchone()[0]
                        if not has_use and ul:
                            for si, t in enumerate(re.split(r'[\n、;；]+', ul)):
                                t = t.strip()
                                if t:
                                    db.execute('INSERT INTO weapon_use VALUES(?,?,?)', (wid, si, translate_use(t)))
                                    ngk_use += 1
                        has_fx = db.execute('SELECT COUNT(*) FROM weapon_fx WHERE weapon_id=?', [wid]).fetchone()[0]
                        if not has_fx and ef:
                            for lv in range(1, 6):
                                db.execute('INSERT INTO weapon_fx VALUES(?,?,?,?,?)', (wid, lv, 100, '', ef))
                                ngk_fx += 1
            if gk_miss:
                print('gamekee 未匹配机体:', len(gk_miss), gk_miss[:8])
        except Exception as e:
            print('gamekee load warn:', e)
    counts['gamekee_use'] = ngk_use
    counts['gamekee_fx'] = ngk_fx

    db.commit()
    db.execute('VACUUM')
    db.commit()
    size = os.path.getsize(OUT) / 1e6
    print(f'ggen.db built: {size:.1f} MB')
    for k, v in counts.items():
        print(f'  {k}: {v}')
    db.close()


USE_EN_MAP = [
    (re.compile(r'^Useable only before moving\.$'), '仅限于移动前使用'),
    (re.compile(r'^Can be used when consuming (\d+) MP\.$'), r'消耗\1MP即可使用'),
    (re.compile(r'^Can be used after moving\.$'), '移动后仍可使用'),
]


def translate_use(t, unmapped=None):
    """使用限制英文文本 → 中文（与游戏内 zh-CN 文案对齐）"""
    s = (t or '').strip()
    for pat, rep in USE_EN_MAP:
        m = pat.match(s)
        if m:
            return pat.sub(rep, s)
    if re.match(r'^[A-Za-z]', s) and unmapped is not None and '对水下' not in s:
        unmapped.add(s)
    return s


def _scan_ability_features(feats, tt, tid, nm, trs):
    """特性扫描: 额外行动/支援/复活/队伍增强/队友对自身增强"""
    seen_unc = False
    # 队伍增强(同部队条件授予)预扫: 官网 desc 在多条件授予时会把条件标签拍平(两条都写【高达】)
    # → 若该能力用了【】条件式文案, 则按各条件自身的 tags+grants 重建 desc(挂在每条件组的首条, 其余留空)
    _tb, _tb_halo, _tb_perm = {}, False, False
    for t in trs or []:
        tr = (t or {}).get('trait') or {}
        tc = tr.get('target_condition') or {}
        if tc.get('target') != 'SameGroup' or not (tr.get('granted_trait_set') or []):
            continue
        _d0 = tr.get('desc') or ''
        if '【' in _d0:
            _tb_halo = True
        if '(永久)' in _d0:
            _tb_perm = True
        g = _tb.setdefault(str(tc.get('id') or tc.get('trait_condition_set_id') or ''), {'tags': tagnames(tc), 'parts': [], 'used': False})
        for x in tr.get('granted_trait_set'):
            _gd = ((x or {}).get('trait') or {}).get('desc') or ''
            _m2 = re.search(r'(攻击力|攻擊力|防御力|防禦力|机动力|機動力|射击值|射擊值|格斗值|格鬥值|觉醒值|覺醒值|反应值|反應值|守备值|守備值|最大HP|最大EN)提升\s*(\d+)', _gd)
            if _m2 and (_m2.group(1) + '提升' + _m2.group(2) + '%') not in g['parts']:
                g['parts'].append(_m2.group(1) + '提升' + _m2.group(2) + '%')
    def _tb_desc(g):
        vals = {}
        for p in g['parts']:
            m3 = re.match(r'(.+?)提升(\d+)%$', p)
            if not m3:
                return '、'.join(g['parts'])
            vals.setdefault(m3.group(2), []).append(m3.group(1))
        return '、'.join('、'.join(v) + '提升' + k + '%' for k, v in vals.items())
    for t in trs or []:
        tr = (t or {}).get('trait') or {}
        d = tr.get('desc') or ''
        ty, tv = tr.get('trait_type'), tr.get('trait_value')
        _ru = [x for x in str((tr.get('active_condition') or {}).get('unit_ids') or '').split(',') if x]   # 需搭乘指定机体(固定搭配)
        if '無條件額外行動' in d:      # 无条件额外行动 → 自带额外行动（每能力一条, 取信息最全的首条）
            if not seen_unc:
                feats.append((tt, tid, 'auto_extra_action', nm, {'value': tv, 'required_units': _ru, 'desc': d.replace('\n', ' ')}))
                seen_unc = True
        elif ty == 19 and '額外行動' in d:
            feats.append((tt, tid, 'extra_action', nm, {'value': tv, 'required_units': _ru, 'desc': d.replace('\n', ' ')}))
        elif '自動額外行動' in d or ty == 85:
            feats.append((tt, tid, 'auto_extra_action', nm, {'value': tv, 'required_units': _ru, 'desc': d.replace('\n', ' ')}))
        if ty == 83 and ('HP為0%' in d or 'HP降至0%' in d):
            feats.append((tt, tid, 'revive_heal', nm, {'pct': tv, 'required_units': _ru, 'desc': d.replace('\n', ' ')}))
        tc = tr.get('target_condition') or {}
        grants = tr.get('granted_trait_set') or []
        if tc.get('target') == 'SameGroup' and grants:
            gv = [((g.get('trait') or {}).get('desc') or '') for g in grants]
            _desc = d.replace('\n', ' ')
            _g = _tb.get(str(tc.get('id') or tc.get('trait_condition_set_id') or ''))
            if _tb_halo and _g and _g['tags'] and _g['parts']:
                if not _g['used']:
                    _desc = '赋予同部队内持有' + '、'.join('【%s】标签' % x for x in _g['tags']) + '的单位，' + _tb_desc(_g) + ('(永久)' if _tb_perm else '')
                    _g['used'] = True
                else:
                    _desc = ''                    # 同条件组其余行留空(界面按『目标+标签』合并时取首条)
            feats.append((tt, tid, 'team_buff', nm, {
                'target_tags': tagnames(tc), 'grants': gv,
                'required_units': [x for x in (tr.get('active_condition') or {}).get('unit_ids', '').split(',') if x],
                'desc': _desc}))
        if '同部隊內每有1架' in d:
            feats.append((tt, tid, 'ally_buff_self', nm, {
                'target_tags': tagnames(tc) or tagnames(tr.get('active_condition') or {}),
                'required_units': [x for x in (tr.get('active_condition') or {}).get('unit_ids', '').split(',') if x],   # 固定搭配: 搭乘指定机体
                'desc': d.replace('\n', ' ')}))
    # 支援次数类按能力名判断
    if '支援防禦' in nm and not any(k in nm for k in ('時，', '提升', '反擊時')):
        feats.append((tt, tid, 'support_def', nm, {}))
    if '支援攻擊' in nm and not any(k in nm for k in ('時，', '提升')):
        feats.append((tt, tid, 'support_atk', nm, {}))


if __name__ == '__main__':
    main()
