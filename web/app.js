/* SD高达永恒 助手 — 主程序 */
'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => (n == null ? '—' : Number(n).toLocaleString('en-US'));
const IMG_CDN = 'https://img.kusoge.xyz/ggenet/';           // 本地离线图缺失时(如日后数据更新出现新图)在线兜底
const thumb = icon => icon ? `img/thumb/thum_${icon}.webp` : '';
const modImg = icon => icon ? `img/item/${icon}.webp` : '';
const imgTag = (icon, cls='', src='') => {
  if (!icon && !src) return '';
  const remote = icon ? IMG_CDN + (src ? `item/${icon}.webp` : `thumb/thum_${icon}.webp`) : '';
  return `<img src="${src || thumb(icon)}" class="${cls}" loading="lazy" data-r="${remote}" onerror="if(this.dataset.r){this.src=this.dataset.r;this.dataset.r=''}else{this.style.visibility='hidden'}">`;
};
/* 驾驶员SP: 非UR(rarity≤4)在开关开时取 sp_max_* 数值; 技能/能力走 mergeSp 槽位替换(数据自带范围) */
function pStat(c, key, spOn) {
  if (!c) return 0;
  const v = (spOn !== false && (c.rarity || 0) <= 4) ? c['sp_max_' + key] : null;
  return (v != null ? v : c['max_' + key]) || 0;
}

let db = null;
function q(sql, params = []) {
  const st = db.prepare(sql);
  try { st.bind(params); const out = []; while (st.step()) out.push(st.getAsObject()); return out; }
  finally { st.free(); }
}
function q1(sql, params = []) { return q(sql, params)[0] || null; }

/* ------------ 常量映射 ------------ */
const ROLE = { 1: { t: '攻', cls: 'atk', n: '攻击型' }, 2: { t: '耐', cls: 'def', n: '耐久型' }, 3: { t: '支', cls: 'sup', n: '支援型' } };
/* 驾驶员类型标记(特性列表机师名旁): 与机体叫法不同 — 2=防御型 */
const PROLE = { 1: { t: '攻击', cls: 'red' }, 2: { t: '防御', cls: 'blue' }, 3: { t: '支援', cls: 'green' } };
/* 头像左下角角色角标: 剑=攻击型 / 盾=耐久型 / 子弹=支援型 */
const ROLE_ICO = {
  atk: '<svg viewBox="0 0 16 16"><g fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M2.6 13.4 12.2 3.8"/><path d="M5.7 7.1 9 10.4"/></g></svg>',
  def: '<svg viewBox="0 0 16 16"><path d="M8 1.1 13.5 3v4.35c0 3.05-2.15 5.9-5.5 7.05C4.65 13.25 2.5 10.4 2.5 7.35V3z" fill="currentColor"/></svg>',
  sup: '<svg viewBox="0 0 16 16"><path d="M8 1.4c1.6 1.8 2.4 3.4 2.4 5.15v2.95H5.6V6.55C5.6 4.8 6.4 3.2 8 1.4z" fill="currentColor"/><rect x="5.6" y="10.2" width="4.8" height="3.1" rx="1.2" fill="currentColor"/></svg>',
};
const roleBadge = role => { const r = ROLE[role]; return r ? `<span class="roleb ${r.cls}">${ROLE_ICO[r.cls]}</span>` : ''; };
const avWrap = (html, role) => (html && ROLE[role]) ? `<span class="avw">${html}${roleBadge(role)}</span>` : html;
const avTag = (icon, role, cls = '', src = '') => avWrap(imgTag(icon, cls, src), role);
const rarB = r => { if (!r) return ''; const x = RAR[r] || RAR[1]; return `<span class="rarb" style="color:${x[1]};border-color:${x[1]}88">${x[0]}</span>`; };
const ULT_STAGE_FULL = ['初始形态', 'ULT形态', 'ULT改造形态'];   // 终极机体三形态(按 id 尾数 0/1/2 与同族同名校验)
let _ultStageMap = null;
function ultStageMap() {
  if (_ultStageMap) return _ultStageMap;
  const m = {};
  let ok = false;
  try {   // 权威数据: data/master MUnitUltGroup (type_index 1/2/3 → 阶段 0/1/2; 含形态机经 main_unit_id 继承)
    for (const r of q('SELECT unit_id, type_index FROM ult_group')) { m[r.unit_id] = r.type_index - 1; ok = true; }
  } catch (e) { ok = false; }
  if (!ok) {   // 旧库无主数据表: 回退 id尾数0/1/2 + 同族同名推断
    const rows = q("SELECT id, name FROM units WHERE ult=1");
    const ids = new Set(rows.map(r => r.id)), names = {};
    for (const r of rows) names[r.id] = r.name;
    for (const r of rows) {
      const id = r.id, k = id % 10;
      const same = (x) => ids.has(x) && names[x] === r.name;
      if (k === 0 && same(id + 1) && same(id + 2)) m[id] = 0;
      else if (k === 1 && same(id - 1) && same(id + 1)) m[id] = 1;
      else if (k === 2 && same(id - 1) && same(id - 2)) m[id] = 2;
    }
  }
  return (_ultStageMap = m);
}
function ultStageOf(u) { return (u && u.ult && ultStageMap()[u.id] != null) ? ultStageMap()[u.id] : null; }
/* ULT改造口径: 阶段0/1(初始/ULT形态) → 同族阶段2(ULT改造形态) */
let _ultRedoMap = null;
function ultRedoMap() {
  if (_ultRedoMap) return _ultRedoMap;
  const m = {};
  let ok = false;
  try {   // 权威数据: ult_group.redo_unit_id (阶段0/1 → 改造后阶段2, 形态机经 main_unit_id 对应)
    for (const r of q('SELECT unit_id, redo_unit_id FROM ult_group WHERE redo_unit_id IS NOT NULL')) { m[r.unit_id] = r.redo_unit_id; ok = true; }
  } catch (e) { ok = false; }
  if (!ok) {   // 旧库回退: 同族同名 + id相邻推断
    const st = ultStageMap();
    const byName = {};
    for (const r of q("SELECT id, name FROM units WHERE ult=1")) if (st[r.id] === 2) (byName[r.name] = byName[r.name] || []).push(r.id);
    for (const r of q("SELECT id, name FROM units WHERE ult=1")) {
      const k = st[r.id];
      if (k !== 0 && k !== 1) continue;
      let best = null;
      for (const c of (byName[r.name] || [])) if (!best || Math.abs(c - r.id) < Math.abs(best - r.id)) best = c;
      if (best) m[r.id] = best;
    }
  }
  return (_ultRedoMap = m);
}
let _ultRedoRows = null;
function ultRedoRows() {
  if (_ultRedoRows) return _ultRedoRows;
  const ids = [...new Set(Object.values(ultRedoMap()))];
  const m = {};
  if (ids.length) for (const r of q(`SELECT * FROM units WHERE id IN (${ids.join(',')})`)) m[r.id] = r;
  return (_ultRedoRows = m);
}
/* ---------- ULT改造 (2.7.0): 三段(SSR/UR/UR)共用同一套改造等级 ----------
   数值: 单项 Lv 0-20, 加成 = floor(自身 max_* × Lv / 200) (满级=自身 max 的 10%)
   总 Lv = 5 项之和(0-100); ≥50 解锁 ULT 武器, =100 解锁三选一能力 (主数据 ult_custom/ult_skills/ult_weapons) */
const ULT_LV_FIELDS = ['hp', 'en', 'atk', 'def', 'mob'];
const ULT_LV_LABEL = { hp: 'HP', en: 'EN', atk: '攻击', def: '防御', mob: '机动' };
let _ultGroupOf = null, _ultSkills = null, _ultWeaponMap = null;
function ultGroupOf(id) {
  if (!_ultGroupOf) {
    _ultGroupOf = {};
    try { for (const r of q('SELECT unit_id, group_id FROM ult_group')) _ultGroupOf[r.unit_id] = r.group_id; } catch (e) {}
  }
  return _ultGroupOf[id];
}
function ultSkillsOf(group) {
  if (!_ultSkills) {
    _ultSkills = {};
    try { for (const r of q('SELECT * FROM ult_skills ORDER BY sort, skill_id')) (_ultSkills[r.group_id] = _ultSkills[r.group_id] || []).push(r); } catch (e) {}
  }
  return _ultSkills[group] || [];
}
let _ultGroupName = null;
function ultGroupName(group) {
  if (!_ultGroupName) {
    _ultGroupName = {};
    try { for (const r of q('SELECT group_id, MIN(unit_id) mid FROM ult_group GROUP BY group_id')) { const x = q1('SELECT name FROM units WHERE id=?', [r.mid]); if (x) _ultGroupName[r.group_id] = x.name; } } catch (e) {}
  }
  return _ultGroupName[group] || ('ULT ' + group);
}
function ultWeaponMap() {
  if (!_ultWeaponMap) {
    _ultWeaponMap = {};
    try { for (const r of q('SELECT unit_id, phase, weapon_id, name FROM ult_weapons ORDER BY phase')) _ultWeaponMap[r.unit_id] = r; } catch (e) {}
  }
  return _ultWeaponMap;
}
function ultTotal() { return +state.ultLv || 0; }
function ultActive(u) { return !!(ultTotal() > 0 && u && u.ult && ultSkillsOf(ultGroupOf(u.id)).length); }
function ultSkillOf(u) {
  if (!ultActive(u)) return null;
  const list = ultSkillsOf(ultGroupOf(u.id));
  if (!list.length) return null;
  const sel = state.ultSkill[ultGroupOf(u.id)];
  return list.find(x => String(x.skill_id) === String(sel)) || list[0];
}
let _ultTrCache = null;
function ultSkillTraits(u) {
  const s = ultSkillOf(u);
  if (!s || ultTotal() < 100) return [];
  _ultTrCache = _ultTrCache || {};
  const k = s.group_id + ':' + s.skill_id;
  if (_ultTrCache[k]) return _ultTrCache[k];
  try { return (_ultTrCache[k] = JSON.parse(s.traits_json || '[]')); } catch (e) { return []; }
}
function ultTraitSum(u, tt) { let v = 0; for (const t of ultSkillTraits(u)) if (+t.trait_type_index === tt) v += (+t.trait_value || 0); return v; }
function ultDmgPct(u) { return ultTraitSum(u, 14); }        // 攻击爆裂: 对敌方造成损伤+X%
function ultRedPct(u) { return ultTraitSum(u, 11); }        // 威力抵御: 受到损伤-X%
function ultSupportAdd(u, kind) { return ultTraitSum(u, kind === 'atk' ? 16 : 17); }   // 支援攻击/防御次数+Y
function ultAddOf(u, f) {   // 总Lv50 → 单项10级(=max×5%); 100 → 单项20级(=max×10%)
  if (!ultActive(u)) return 0;
  return Math.floor((u['max_' + f] || 0) * (+state.ultLv || 0) / 1000);
}
function effUnit(u) {   // ULT改造: 当前段直接加改造数值(不切形态); 三段各自保留
  if (!u || !ultActive(u)) return u;
  const v = Object.assign({}, u), add = {};
  for (const f of ULT_LV_FIELDS) {
    const a = ultAddOf(u, f);
    if (!a) continue;
    add[f] = a;
    v['max_' + f] = (u['max_' + f] || 0) + a;
    v['sp_max_' + f] = ((u['sp_max_' + f] ?? u['max_' + f]) || 0) + a;
    v[f] = (u[f] || 0) + a;
  }
  v._ultAdd = add;
  return v;
}
function dedupeUnits(list) { return list.map(effUnit); }   // 三段独立, 不合并(仅套用改造数值)
function weaponsForUnit(u, order) {   // 武器列表 + ULT改造武器(总Lv≥50解锁; 未解锁时隐藏该武器)
  if (!u) return [];
  let ws = q('SELECT * FROM weapons WHERE unit_id=?' + (order || ''), [u.id]);
  const uw = ultWeaponMap()[u.id];
  if (uw) {
    const on = ultActive(u) && ultTotal() >= 50;
    ws = ws.filter(w => w.id !== uw.weapon_id);
    if (on) { const row = q1('SELECT * FROM weapons WHERE id=?', [uw.weapon_id]); if (row) ws.push(row); }
    if (order && /power DESC/.test(order)) ws.sort((a, b) => (b.power || 0) - (a.power || 0));
  }
  return ws;
}
const ultB = u => {
  if (!u || !u.ult) return '';
  const st = ultStageOf(u);
  const t = st == null ? 'ULT' : (st === 0 ? 'ULT·初始' : (st === 2 ? 'ULT·改造' : 'ULT'));
  return ` <span class="rarb" style="color:#9fe8c0;border-color:#9fe8c088">${t}</span>`;   // 终极机体角标(含三形态阶段)
};
const avTagR = (icon, role, r, cls = '', src = '', drv = false) => {   // 头像 + 角色角标 + 稀有度角标(drv=驾驶员: 角标右下)
  const html = imgTag(icon, cls, src);
  if (!html) return '';
  const b = rarB(r);
  if (!ROLE[role] && !b) return html;
  return `<span class="avw${drv ? ' avdrv' : ''}">${html}${roleBadge(role)}${b}</span>`;
};
const avDrv = (icon, role, r, cls = '', src = '') => avTagR(icon, role, r, cls, src, true);
const FEAT = {
  revive_escape: '复活·换机', revive_heal: '复活·回血', extra_action: '额外行动+1', counter_shield: '进攻盾', range_buff: '范围增益',
  auto_extra_action: '自带额外行动', preemptive: '先发攻击', support_atk: '支援攻击+2', support_def: '支援防御+2', mp_skill: '有MP技能', sway_evade: '摇摆闪避',
  team_buff: '队伍增强', ally_buff_self: '队友对自身增强', unit_skill: '单位技能',
  shield_defense: '盾牌防御', transform: '变形机构', swap: '换装', first_hit_immune: '第一击损伤无效',
  move6: '6移动', move7: '支援防御范围7', baobi: '必暴组合', tekko: '特攻', range6: '6射程', range7: '7射程', range_up: '射程加',
};
const WATTR = { 1: ['ranged'], 2: ['melee'], 3: ['awaken'], 4: ['ranged', 'melee'], 5: ['ranged', 'awaken'], 6: ['melee', 'awaken'], 7: ['ranged', 'melee', 'awaken'] };
const TYATTR = { 1: '射击', 2: '格斗', 3: '觉醒', 4: '射击/格斗', 5: '射击/觉醒', 6: '格斗/觉醒', 7: '全属性(EX)' };
const AATTR = { 1: '物理', 2: '光束', 3: '特殊', 4: '光束/物理', 5: '物理/特殊', 6: '光束/特殊', 7: '全属性' };
const TTYPE = { 7: '攻击力提升', 9: '目标防御减少(贯穿)', 10: '目标防御减少', 11: '机动力变化', 19: '额外出动', 25: '机师防御提升', 26: '机师防御提升', 31: '最大HP提升', 39: '暴击伤害提升', 44: '近距离武装POWER提升', 45: '武装POWER提升', 81: '武装POWER提升', 82: '武装POWER提升', 92: '武装POWER提升', 78: '镭射武装POWER下降', 83: 'HP恢复', 13: '赋予队友' };
const STATNAME = { ranged: '射击', melee: '格斗', awaken: '觉醒', defense: '防御', reaction: '反应' };
const STAR_MULT = [1.0, 1.2, 1.3, 1.4];   // ★0/1/2/3 突破倍率（来自成长表 Lv100 lb0-3）
/* SSR及以下「三星」「SP」两独立开关 → 四态数值(全站统一口径; 与网站/游戏实测一致):
   数据: max_* = 等级上限插值值(N60/R70/SR80/SSR90: base+(max100−base)×cap//100, build_db 折算); sp_max_* = Lv100值
   三关+SP关 = max · 三开+SP关 = floor(max×1.4)(游戏「显示强化上限关」面板=原始数值)
   三关+SP开 = sp_max · 三开+SP开 = floor(sp_max×1.4)(SP三星面板) · SSP 需 三星+SP
   SSP满10 增量加在★倍率之前(网站实证 高达SR: floor((64209+2403)×1.4)=93256) */
function uStatBase(u, f, s3, sp) {
  const mx = u['max_' + f] || 0;
  if (sp) return { base: u['sp_max_' + f] || mx, mult: s3 ? 1.4 : 1 };
  return { base: mx, mult: s3 ? 1.4 : 1 };
}
function uStatVal(u, f, s3, sp, add) {
  const b = uStatBase(u, f, s3, sp);
  return Math.floor((b.base + (add || 0)) * b.mult);
}
/* ---------- 数值提升档位(被动/主动/max): 从 desc 解析「XX提升N%」并累加 ---------- */
const STATUP_KEY = { '最大HP': 'hp', '最大EN': 'en', '攻击力': 'atk', '防御力': 'def', '机动力': 'mob',
                     '射击值': 'ranged', '格斗值': 'melee', '觉醒值': 'awaken', '守备值': 'defense', '反应值': 'reaction' };
function statUpIsCond(name, tr) {   // 条件型判定: 名称前缀「(…条件)」/ desc 条件标记
  if (/^\(.*条件\)/.test(String(name || ''))) return true;
  return /含有|战意为|以上时|以下时|全满时|每有|每受到|对战时|受到|攻击目标|敌方|标签|系列/.test(String((tr || {}).desc || ''));
}
function statUpAcc(rows, includeCond, out, maxStack) {   // rows: [{name, desc?/traits_json?}] → {statKey: 合计%}; maxStack=满层(取最高N%)
  out = out || {};
  for (const r of rows || []) {
    let trs = [];
    if (r.traits_json) { try { trs = JSON.parse(r.traits_json || '[]'); } catch (e) { trs = []; } }
    if (!trs.length && r.desc) trs = [{ trait: { desc: r.desc } }];
    for (const t of trs) {
      const tr = (t || {}).trait || {};
      const ds = String(tr.desc || '');
      // 支持多数值并列: 「自身觉醒值及反应值提升15%」→ 觉醒+反应 各15%
      const ms = [...ds.matchAll(/([^\s，,。；;：:]{0,42}?)提升\s*(\d+)%/g)];
      const hits = [];
      for (const m of ms) for (const nm of m[1].matchAll(/(最大HP|最大EN|攻击力|防御力|机动力|射击值|格斗值|觉醒值|守备值|反应值)/g)) hits.push([nm[1], +m[2]]);
      if (!hits.length) continue;
      if (!includeCond && statUpIsCond(r.name, tr)) continue;
      const mx = maxStack ? /最高\s*(\d+)%/.exec(ds) : null;   // max档=满层: 每有/对战次数/受到损伤等叠层取最高N%
      if (mx) { const seen = {}; for (const [nm] of hits) { const k = STATUP_KEY[nm]; if (!seen[k]) { out[k] = (out[k] || 0) + (+mx[1]); seen[k] = 1; } } }
      else for (const [nm, pct] of hits) out[STATUP_KEY[nm]] = (out[STATUP_KEY[nm]] || 0) + pct;
    }
  }
  return out;
}
function statBoostOf(abilRows, skillRows, mode) {   // 1=被动(无条件能力) 2=主被动(+技能) 3=max(+条件型, 满层)
  if (!mode) return {};
  const out = {};
  statUpAcc(abilRows, mode === 3, out, mode === 3);
  if (mode >= 2) statUpAcc(skillRows, true, out, mode === 3);
  return out;
}
/* 图鉴列表「数值口径」档位(排序弹窗内设置, 默认原值): 显示与数值排序同口径 */
let _cpBst = null;
function charBstMaps() {      // {off|on: {charId: {1|2|3: {stat: pct}}}}
  if (_cpBst) return _cpBst;
  const grab = (tbl, cols) => { const m = {}; for (const r of q(`SELECT ${cols} FROM ${tbl}`)) (m[r.char_id] = m[r.char_id] || []).push(r); return m; };
  const abOff = grab('char_abilities', 'char_id, sort, name, traits_json');
  const abOn = grab('char_abilities_sp', 'char_id, sort, name, traits_json');
  const skOff = grab('char_skills', 'char_id, sort, name, desc, traits_json');
  const skOn = grab('char_skills_sp', 'char_id, sort, name, desc, traits_json');
  _cpBst = { off: {}, on: {} };
  for (const id of new Set([...Object.keys(abOff), ...Object.keys(abOn), ...Object.keys(skOff), ...Object.keys(skOn)])) {
    const A = abOff[id] || [], S = skOff[id] || [];
    const A2 = mergeSp(A, abOn[id] || []), S2 = mergeSp(S, skOn[id] || []);
    _cpBst.off[id] = { 1: statBoostOf(A, S, 1), 2: statBoostOf(A, S, 2), 3: statBoostOf(A, S, 3) };
    _cpBst.on[id] = { 1: statBoostOf(A2, S2, 1), 2: statBoostOf(A2, S2, 2), 3: statBoostOf(A2, S2, 3) };
  }
  return _cpBst;
}
function charListStat(c, k, mode, spOn) {   // 列表显示/排序值 = pStat × (1+档位%)
  const v = pStat(c, k, spOn);
  if (!mode) return v;
  const m = ((spOn !== false && (c.rarity || 0) <= 4) ? charBstMaps().on : charBstMaps().off)[c.id];
  const pct = m && m[mode] && m[mode][k];
  return pct ? Math.floor(v * (1 + pct / 100)) : v;
}
let _upBst = null;
let _upBstNoSk = null;
function unitBstMapsNoSk() {   // 机体技能关: 只算单位能力(不含单位技能)
  if (_upBstNoSk) return _upBstNoSk;
  const ab = {};
  for (const r of q("SELECT unit_id, name, traits_json FROM unit_abilities")) (ab[r.unit_id] = ab[r.unit_id] || []).push(r);
  _upBstNoSk = {};
  for (const id of Object.keys(ab)) { const A = ab[id] || []; _upBstNoSk[id] = { 1: statBoostOf(A, [], 1), 2: statBoostOf(A, [], 2), 3: statBoostOf(A, [], 3) }; }
  return _upBstNoSk;
}
function unitBstMaps() {      // {unitId: {1|2|3: {stat: pct}}} (单位能力+单位技能)
  if (_upBst) return _upBst;
  const ab = {};
  for (const r of q("SELECT unit_id, name, traits_json FROM unit_abilities")) (ab[r.unit_id] = ab[r.unit_id] || []).push(r);
  const sk = {};
  for (const r of q("SELECT target_id, label, params_json FROM features WHERE target_type='unit' AND feature='unit_skill'")) {
    let pr = {}; try { pr = JSON.parse(r.params_json || '{}'); } catch (e) {}
    if (pr.ult) continue;   // ULT改造能力: 三选一, 由 ultDmgPct/ultSkill 单独计入(不在此全量叠加)
    (sk[r.target_id] = sk[r.target_id] || []).push({ name: r.label, desc: pr.desc || '' });
  }
  _upBst = {};
  for (const id of new Set([...Object.keys(ab), ...Object.keys(sk)])) {
    const A = ab[id] || [], S = sk[id] || [];
    _upBst[id] = { 1: statBoostOf(A, S, 1), 2: statBoostOf(A, S, 2), 3: statBoostOf(A, S, 3) };
  }
  return _upBst;
}
function unitHpPassivePct(id) {   // 无条件「最大HP提升」类机体能力% (如 ULT 超级海伯瑞 LV3=+15%)
  const m = unitBstMaps()[id];
  return (m && m[1] && m[1].hp) || 0;
}
function unitStarSel() { return state.uStarList === undefined ? 3 : state.uStarList; }
function unitListStat(u, f, mode, star) {   // 机体列表口径: max_(★0) ×★倍率(ULT不乘) × (1+档位%); ULT改造口径时取改造后数值
  const eu = effUnit(u);
  let v = eu['max_' + f] || 0;
  if (!eu.ult && star) v = Math.floor(v * (STAR_MULT[star] || 1));
  if (!mode) return v;
  const m = (state.uSk === false ? unitBstMapsNoSk() : unitBstMaps())[eu.id] || {};
  const pct = m[mode] && m[mode][f];
  return pct ? Math.floor(v * (1 + pct / 100)) : v;
}
const SKILL_EFF = { 3: ['射程+', ''], 8: ['增伤+', '%'], 9: ['射击值+', '%'], 10: ['格斗值+', '%'],
  11: ['觉醒值+', '%'], 12: ['暴击率+', '%'], 14: ['闪避+', '%'], 15: ['EN消耗-', '%'], 17: ['减伤+', '%'] };
const RAR = { 1: ['N', '#8ea0c4'], 2: ['R', '#4cc9ff'], 3: ['SR', '#7b6cff'], 4: ['SSR', '#f5c451'], 5: ['UR', '#ff6ad5'] };
const rarTag = r => { const x = RAR[r] || RAR[1]; return `<span class="rar" style="color:${x[1]};border-color:${x[1]}88;background:${x[1]}1a">${x[0]}</span>`; };


function fxShort(name, desc) {   // 武器效果简化词(全量): 增伤/降防/减益/词条 — 覆盖 weapon_fx 全部词条模式
  const ds = String(desc || '');
  const d = String(name || '') + ' ' + ds;
  const bn = s => (s === '镭射' ? '光束' : s);   // 镭射≡光束(游戏口径)
  /* SSP核心/固有修饰行「武装效果的效果值UP(且X N%)」→ 「武装效果UP·X+N%」(X=被提升的原效果) */
  const up = d.match(/武装效果的效果值UP\(且([\s\S]*?)\)/);
  if (up) {
    const inner = up[1];
    let g = inner.match(/最大值提升\s*(\d+)%/);                                 if (g) return '武装效果UP·最大值+' + g[1] + '%';
    g = inner.match(/爆击损伤提升\s*(\d+)%/);                                   if (g) return '武装效果UP·暴伤+' + g[1] + '%';
    g = inner.match(/受到(?:的)?(光束|镭射|物理|特殊)武装损伤提升\s*(\d+)%/);   if (g) return '武装效果UP·' + bn(g[1]) + '+' + g[2] + '%';
    g = inner.match(/(光束|镭射|物理|特殊)武装POWER减少\s*(\d+)%/);             if (g) return '武装效果UP·敌' + bn(g[1]) + 'POWER-' + g[2] + '%';
    g = inner.match(/攻击力减少\s*(\d+)%/);                                     if (g) return '武装效果UP·敌攻-' + g[1] + '%';
    g = inner.match(/机动力减少\s*(\d+)%/);                                     if (g) return '武装效果UP·敌机动-' + g[1] + '%';
    g = inner.match(/命中率减少\s*(\d+)%/);                                     if (g) return '武装效果UP·敌命中-' + g[1] + '%';
    g = inner.match(/防御力减少\s*(\d+)%/);                                     if (g) return '武装效果UP·降防+' + g[1] + '%';
    return '武装效果UP';
  }
  const m = ds.match(/最高提升\s*(\d+)%/) || ds.match(/增加\s*(\d+)%/);
  const pct = m ? '+' + m[1] + '%' : '';
  if (/剩余HP越高|HP越高/.test(d)) return '高HP' + pct;
  if (/剩余HP越低|HP越低/.test(d)) return '低HP' + pct;
  if (/EN越高|剩余EN越高/.test(d)) return '高EN' + pct;
  if (/EN越低|剩余EN越低/.test(d)) return '低EN' + pct;
  if (/MP越高|剩余MP越高/.test(d)) return '高MP' + pct;
  if (/MP越低|剩余MP越低/.test(d)) return '低MP' + pct;
  if (/近距离|距离敌方越近/.test(d)) return '近距离' + pct;
  if (/远距离|距离敌方越远/.test(d)) return '远距离' + pct;
  /* 减益(赋予敌方) */
  let g = d.match(/赋予敌方[“"「]?攻击力减少\s*(\d+)%/);                           if (g) return '敌攻-' + g[1] + '%';
  g = d.match(/赋予敌方[“"「]?机动力减少\s*(\d+)%/);                               if (g) return '敌机动-' + g[1] + '%';
  g = d.match(/赋予敌方[“"「]?命中率减少\s*(\d+)%/);                               if (g) return '敌命中-' + g[1] + '%';
  g = d.match(/赋予敌方[“"「]?(光束|镭射|物理|特殊|觉醒)武装POWER减少\s*(\d+)%/);   if (g) return '敌·' + bn(g[1]) + 'POWER-' + g[2] + '%';
  g = d.match(/赋予敌方[“"「]?(光束|镭射|物理|特殊|觉醒)武装的最大射程减少\s*(\d+)/); if (g) return '敌·' + bn(g[1]) + '射程-' + g[2];
  g = d.match(/赋予敌方[“"「]?移动力下降\s*(\d+)/);                                if (g) return '敌移动-' + g[1];
  /* 词条 */
  if (/绝对命中/.test(d)) return '绝对命中';
  if (/先发攻击/.test(d)) return '先发攻击';
  if (/使用后可移动/.test(d)) return '使用后可移动';
  if (/额外行动/.test(d)) return '额外行动';
  g = d.match(/命中的敌方MP减少\s*(\d+)/);                                         if (g) return '敌MP-' + g[1];
  g = d.match(/自身爆击损伤提升\s*(\d+)%/);                                        if (g) return '暴伤+' + g[1] + '%';
  if (/爆击率提升/.test(d)) return '暴击率提升';
  g = d.match(/依造成损伤的(\d+)%恢复自身HP/);                                     if (g) return 'HP吸收' + g[1] + '%';
  g = d.match(/损伤值为敌方最大EN的(\d+)%/);                                       if (g) return 'EN吸收' + g[1] + '%';
  g = d.match(/命中率固定\s*(\d+)%/);                                              if (g) return '命中固定' + g[1] + '%';
  if (/对水下敌人的伤害减半/.test(d)) return '对水下伤害减半';
  /* 条件型「效果值/最大值增加」(敌方含XX标签) */
  g = d.match(/包含[“"「]([^”"」]+)[”"」]标签时[\s\S]*?(光束|镭射|物理|特殊|防御力减少|武装POWER|爆击损伤)[\s\S]*?(?:效果值|最大值)增加\s*(\d+)%/);
  if (g) return '对' + g[1] + '·' + (g[2] === '防御力减少' ? '降防' : g[2] === '武装POWER' ? 'POWER' : bn(g[2])) + '效果+' + g[3] + '%';
  const e2 = d.match(/对战的敌方包含[“"「]?([^”"」,，(（]+)/);
  if (e2) return '对' + e2[1].replace(/标签|系列/g, '') + pct;
  const e3 = d.match(/遭(光束|镭射|物理|特殊|全属性)武装攻击时[，,]?\s*受到的损伤提升\s*(\d+)%/);   // 光束-35%型(增伤)
  if (e3) return bn(e3[1]) + '-' + e3[2] + '%';
  const e4 = d.match(/防御力减少\s*(\d+)%/);   // 降防25%型
  if (e4) return (d.indexOf('贯穿') >= 0 ? '贯穿降防' : '降防') + e4[1] + '%';
  return null;
}
function effText(e, w) {
  const pct = [7, 9, 11, 25, 31, 39, 44, 45, 78, 81, 82, 83, 92].includes(e.trait_type);
  let nm = TTYPE[e.trait_type];
  if (e.trait_type === 7 && e.trait_value < 0) nm = '敌·攻击力减少';
  if (e.trait_type === 11 && e.trait_value < 0) nm = '敌·机动力减少';
  if (e.trait_type === 11 && e.trait_value > 0) nm = '自身机动力提升';
  if (e.trait_type === 78 && e.trait_value < 0) nm = '敌·镭射武装POWER下降';
  if (e.trait_type === 14) {                       // 「遭X武装攻击时受到损伤提升N%」→ X-N%(增伤, 值取原始负值)
    const en = String(e.effect_name || '');   // 效果文本优先用武器特质名(如 光束/特殊/物理损伤提升), 不能用武器自身属性
    const at = /光束/.test(en) ? '光束' : (/特殊/.test(en) ? '特殊' : (/物理/.test(en) ? '物理' : (AATTR[(w && w.weapon_attr) || 0] || '光束')));
    return at + (e.trait_value || 0) + '%';
  }
  if (e.trait_type === 9 && e.trait_value < 0) return '降防' + Math.abs(e.trait_value) + '%';
  if (!nm) nm = '效果#' + e.trait_type;
  const v = e.trait_value || 0;
  return nm + (v ? ' ' + (v > 0 ? '+' : '') + v + (pct ? '%' : '') : '');
}



/* ------------ SSP改装核心·能力变化(unit_abilities_ssp) ------------
   参考站 F() 语义: before_ability_id=0 → 新增; before≠0 → 替换对应能力; 满10=核心level≤10+initial_release */
let _unitAb = null;
function unitAbilitiesAll() {
  if (_unitAb) return _unitAb;
  _unitAb = { base: {}, ssp: {} };
  for (const r of q('SELECT unit_id, ability_id, name, traits_json FROM unit_abilities')) (_unitAb.base[r.unit_id] = _unitAb.base[r.unit_id] || []).push(r);
  for (const r of q('SELECT unit_id, before_ability_id, ability_id, name, traits_json FROM unit_abilities_ssp')) (_unitAb.ssp[r.unit_id] = _unitAb.ssp[r.unit_id] || []).push(r);
  return _unitAb;
}
function unitAbilitiesOf(uid, sspOn) {
  const o = unitAbilitiesAll();
  const base = o.base[uid] || [];
  const ssp = o.ssp[uid];
  if (sspOn === false || !ssp || !ssp.length) return base;
  const byBefore = {};
  for (const r of ssp) if (r.before_ability_id) byBefore[r.before_ability_id] = r;
  const out = [];
  for (const b of base) out.push(byBefore[b.ability_id] ? Object.assign({}, byBefore[b.ability_id], { _ssp: 'repl' }) : b);
  for (const r of ssp) if (!r.before_ability_id) out.push(Object.assign({}, r, { _ssp: 'add' }));
  return out;
}

/* ------------ 机体被动能力（type7=攻击力提升%）------------ */
const TENSION_RANK = { High: 1, SuperHigh: 2, Supercharged: 3 };
const VIGOR_RANK = { default: 0, mid: 0, high: 1, max: 2, supercharged: 3 };
let _unitPsv = null, _unitPsvEnemy = null, _unitPsvS = null, _unitPsvEnemyS = null;
function unitPassives(sspOn) {
  if (_unitPsv) return (sspOn && _unitPsvS) ? _unitPsvS : _unitPsv;
  _unitPsv = {}; _unitPsvEnemy = {}; _unitPsvS = {}; _unitPsvEnemyS = {};
  const parseRows = (rows, tgt, tgtE) => {
    for (const r of rows) {
      let trs = []; try { trs = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      for (const t of trs) {
        const tr = (t || {}).trait || {};
        const ds = String(tr.desc || '');
        let v = 0, stk = null;
        if (tr.trait_type === 7) {
          if (!(tr.trait_value > 0)) continue;
          v = tr.trait_value;
        } else if (tr.trait_type === 13 && /攻击力提升/.test(ds)) {   // 对战次数等叠层攻击(值字段为源id, 基础%在desc)
          const bm = /提升\s*(\d+)%/.exec(ds); if (!bm) continue;
          v = +bm[1]; stk = 'battle';
        } else continue;
        const ac = tr.active_condition || {};
        const cq = condTagsOf(ac);
        const mm = /最高\s*(\d+)%/.exec(ds);
        const mx = mm ? +mm[1] : null;
        if (!stk) stk = /对战次数|对战结束时/.test(ds) ? 'battle' : (/受到损伤/.test(ds) ? 'damage' : 'team');
        if ((ac.target || 'Owner') === 'AttackTarget') {   // 敌方条件(发起对战的敌方含X标签/系列/驾驶员标签): 按对手判定
          (tgtE[r.unit_id] = tgtE[r.unit_id] || []).push({ v, reqTags: cq.tags, reqSeries: cq.series, ctags: cq.ctags });
          continue;
        }
        let tensionReq = 0;
        if (ac.tension) { const _rs = String(ac.tension).split(',').map(x => TENSION_RANK[x.trim()] || 0).filter(Boolean); if (_rs.length) tensionReq = Math.min(..._rs); }   // 「超强势以上」编码为档位集合 → 阈值取最低档
        (tgt[r.unit_id] = tgt[r.unit_id] || []).push({ v, mx, stk, tensionReq, reqTags: cq.tags, reqSeries: cq.series, reqUnits: cq.units, roleReq: cq.role, bag: cq.bag, ctx: cq.ctx });
      }
    }
  };
  const all = unitAbilitiesAll();
  const uids = new Set([...Object.keys(all.base), ...Object.keys(all.ssp)].map(Number));
  for (const uid of uids) {
    const b = unitAbilitiesOf(uid, false), sp = unitAbilitiesOf(uid, true);
    parseRows(b, _unitPsv, _unitPsvEnemy);
    parseRows(sp, _unitPsvS, _unitPsvEnemyS);
  }
  return (sspOn && _unitPsvS) ? _unitPsvS : _unitPsv;
}
/* 敌方条件被动 (与 unitPassives 同口径的 SSP 视图) */
function unitPassivesEnemy(sspOn) { unitPassives(sspOn); return (sspOn && _unitPsvEnemyS) ? _unitPsvEnemyS : _unitPsvEnemy; }
/* condAll=true: 条件全开（排行/组队口径）; false: 战意条件按当前战意判定，标签条件不计
   enemyMeta: 指定了对手(组队防御目标)时, 敌方条件被动按对手标签/系列逐条判定 */
function unitPassiveAtkPct(unitId, vigorKey, condAll, enemyMeta, sspOn, first) {
  const meta = metaOf(unitId);
  let pct = 0;
  for (const p of (unitPassives(sspOn)[unitId] || [])) if (condOk(p, meta, { condAll, vigor: vigorKey })) pct += stackEff(p, { condAll, first });
  let _ctMax = 0;
  for (const p of (unitPassivesEnemy(sspOn)[unitId] || [])) {
    if (enemyMeta) {
      if (!reqOk(p.reqTags, p.reqSeries, enemyMeta)) continue;
      if (p.ctags && p.ctags.length && !(enemyMeta.ctags && p.ctags.some(t => enemyMeta.ctags.has(t)))) continue;   // 敌方驾驶员标签条件(如「优势：新人类」)
      pct += p.v;
    }
    else if (condAll !== false) {
      if (p.ctags && p.ctags.length) { if (p.v > _ctMax) _ctMax = p.v; }   // 驾驶员标签类条件互斥(同一敌方不可能同为新人类与X行者) → 假设模式只取最高一项
      else pct += p.v;
    }
  }
  return pct + _ctMax;
}


/* ------------ 驾驶员被动能力 & 主动技能 ------------ */
/* 官方已确认且不修复的游戏bug: 真飞鸟EX技能「搭乘命运高达(EX)时」的机体限制实际不生效 → 对所有机体生效 */
/* ★用户定死(不得改): 真·飞鸟(1330000103)「EX角色能力」的「搭乘命运高达(EX)时」限制实际不生效 ——
   二阶段必暴(多段增益EX赋予链第二层)与MP+2 对所有机体生效(官方bug, 确认不修复)。
   注意: 该描述只对应单条效果文本, 全机体生效已于此前核实正确。此豁免不得移除/不得按描述加搭乗门。 */
const UNIT_GATE_BUG_CHARS = new Set([1330000103]);
/* 能力 trait_type: 7=攻击力提升%(计入机体攻击) 17=损伤提升% 21=射击值% 23=格斗值% 29=觉醒值%
   技能 trait_type:  8=损伤提升%  9=射击值% 10=格斗值% 11=觉醒值% */
const ABIL_KIND = { 7: 'atk', 17: 'dmg', 21: 'ranged', 23: 'melee', 29: 'awaken' };
/* 出击场地适性: 3=○正常 / 2=△移动力减半 / 1=×不能出击 (soshage原始terrain字段) */
const terrOf = (u, k) => (k === 'space' ? u.terrain_space : k === 'atm' ? u.terrain_atm : k === 'ground' ? u.terrain_ground : k === 'surface' ? u.terrain_surface : k === 'water' ? u.terrain_water : 0) || 0;
/* 带盾(盾牌防御 feature)机体 id 集 — 组队 防御型TOP/进攻盾TOP 的盾标识与「防御盾筛选」 */
let _shieldSet = null;
function shieldUnitSet() {
  if (!_shieldSet) _shieldSet = new Set(q("SELECT target_id FROM features WHERE target_type='unit' AND feature='shield_defense'").map(r => r.target_id));
  return _shieldSet;
}
const shieldMark = uid => shieldUnitSet().has(uid) ? '<span style="color:#8fc4ff;font-weight:700">盾</span>' : '<span style="color:var(--dim)">无盾</span>';
/* 组队行右侧迷你地形适性: 宇○ 空△ 地○ 面× 中× (3=○ 2=△ 1=× 其他=—) */
function terrMini(uid) {
  const u = q1('SELECT terrain_space a, terrain_atm b, terrain_ground c, terrain_surface d, terrain_water e FROM units WHERE id=?', [uid]);
  if (!u) return '';
  const sy = v => v === 3 ? '○' : v === 2 ? '△' : v === 1 ? '×' : '—';
  const cl = v => v === 3 ? '#7df0a8' : v === 2 ? '#f5c451' : v === 1 ? '#ff6b6b' : 'var(--dim)';
  return [['宇', u.a], ['空', u.b], ['地', u.c], ['面', u.d], ['中', u.e]].map(([n, v]) => `${n}<b style="color:${cl(v)}">${sy(v)}</b>`).join(' ');
}
/* 水中场地武器倍率(来自 weapon_use 使用限制, 与 ssp_json 官方 capability 双轴一致):
   「对水下敌人的伤害减半」→50 / 「不能在水下使用」(in_underwater=false) 或「对水下敌人没有伤害」(damage_underwater=0) →0 不可用; 无限制默认100
   注: SSP版武器可能解除限制(如 GN加农SSP 无限制, 基础版减半) — weapon_use 按版本各存各的 */
let _uwM = null;
function uwMult(w) {
  if (w == null) return 100;
  const wid = (typeof w === 'object') ? w.id : w;
  if (!_uwM) {
    _uwM = {};
    for (const r of q("SELECT weapon_id, text FROM weapon_use WHERE text LIKE '%水下%'")) {
      const v = (r.text === '对水下敌人的伤害减半') ? 50 : 0;
      const cur = _uwM[r.weapon_id];
      if (cur == null || v < cur) _uwM[r.weapon_id] = v;   // 取最严格(减半+不能使用 → 不可用)
    }
  }
  return _uwM[wid] != null ? _uwM[wid] : 100;
}
function terrDamage(dmg, w, terr) {   // 出击场地=水中 时按武器水中倍率折算
  if (terr !== 'water') return dmg;
  const m = uwMult(w);
  return m === 100 ? dmg : Math.floor(dmg * m / 100);
}
const SKILL_KIND = { 8: 'dmg', 9: 'ranged', 10: 'melee', 11: 'awaken' };
let _charPsv = null, _charSk = null, _charPsvEnemy = null, _charPsvSp = null, _charPsvEnemySp = null;
/* 驾驶员SP: SP版行按槽位(sort)替换基础版 — 数值(rarity≤4用sp_max_*)/技能/能力/暴击/赋予 统一口径 */
function mergeSp(base, sp) {
  if (!sp || !sp.length) return base || [];
  const sorts = new Set(sp.map(x => x.sort));
  return (base || []).filter(x => !sorts.has(x.sort)).concat(sp);
}
function _parsePsvRows(rows, tgt, tgtEnemy) {
  for (const r of rows) {
    let trs = []; try { trs = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
    for (const t of trs) {
      const tr = (t || {}).trait || {};
      const kind = ABIL_KIND[tr.trait_type];
      if (!kind || !(tr.trait_value > 0)) continue;
      const ac = tr.active_condition || {};
      const cq = condTagsOf(ac);
      if ((ac.target || 'Owner') === 'AttackTarget') {   // 敌方条件被动: 按对手判定
        (tgtEnemy[r.char_id] = tgtEnemy[r.char_id] || []).push({ sort: r.sort || 0, kind, v: tr.trait_value, reqTags: cq.tags, reqSeries: cq.series });
        continue;
      }
      let tensionReq = 0;
      if (ac.tension) { const _rs = String(ac.tension).split(',').map(x => TENSION_RANK[x.trim()] || 0).filter(Boolean); if (_rs.length) tensionReq = Math.min(..._rs); }   // 「超强势以上」编码为档位集合 → 阈值取最低档
      const _ds = String(tr.desc || ''), _mm = /最高\s*(\d+)%/.exec(_ds);
      const mx = _mm ? +_mm[1] : null;
      const stk = /对战次数|对战结束时/.test(_ds) ? 'battle' : (/受到损伤/.test(_ds) ? 'damage' : 'team');
      (tgt[r.char_id] = tgt[r.char_id] || []).push({ sort: r.sort || 0, kind, v: tr.trait_value, mx, stk, tensionReq, reqTags: cq.tags, reqSeries: cq.series, reqUnits: UNIT_GATE_BUG_CHARS.has(r.char_id) ? [] : cq.units, roleReq: cq.role, bag: cq.bag, ctx: cq.ctx });
    }
  }
}
function charPassives() {
  if (_charPsv) return _charPsv;
  _charPsv = {}; _charPsvEnemy = {}; _charPsvSp = {}; _charPsvEnemySp = {};
  _parsePsvRows(q('SELECT char_id, sort, traits_json FROM char_abilities'), _charPsv, _charPsvEnemy);
  _parsePsvRows(q('SELECT char_id, sort, traits_json FROM char_abilities_sp'), _charPsvSp, _charPsvEnemySp);
  return _charPsv;
}
let _charPsvM = {};   // 性能: (id,sp,enemy) 合并结果缓存(免每次 mergeSp 重建数组)
function charPsvOf(id, spOn, enemy) {
  const _k = id + '|' + (spOn === false ? 0 : 1) + '|' + (enemy ? 1 : 0);
  const _hit = _charPsvM[_k];
  if (_hit) return _hit;
  charPassives();
  const base = ((enemy ? _charPsvEnemy : _charPsv)[id]) || [];
  return (_charPsvM[_k] = (spOn === false) ? base : mergeSp(base, (enemy ? _charPsvEnemySp : _charPsvSp)[id]));
}
function charSkills() {
  if (_charSk) return _charSk;
  _charSk = { base: {}, sp: {} };
  const parse = (rows, tgt) => {
    for (const r of rows) {
      let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      for (const set of ts) {
        const tr = (set || {}).trait || {};
        const kind = SKILL_KIND[tr.trait_type];
        if (!kind || !(tr.trait_value > 0)) continue;
        (tgt[r.char_id] = tgt[r.char_id] || []).push({ sort: r.sort || 0, kind, v: tr.trait_value });
      }
    }
  };
  parse(q('SELECT char_id, sort, traits_json FROM char_skills'), _charSk.base);
  parse(q('SELECT char_id, sort, traits_json FROM char_skills_sp'), _charSk.sp);
  return _charSk;
}
function charSkillOf(id, spOn) {
  const o = charSkills();
  const base = o.base[id] || [];
  if (spOn === false) return base;
  return mergeSp(base, o.sp[id]);
}
/* ------------ 次数技能: 支援攻击/反击+1次(type 51/86) / 支援防御+1次(type 52/87) ------------
   86/87为条件型(如 阿瑟姆「AGE-2 基本型(EX)&超一击」+1次); 86条数少(3条), 87暂无数据 */
let _charSup = null;
function charSupEntries() {
  if (_charSup) return _charSup;
  _charSup = { base: {}, sp: {} };
  const kinds = { 51: 'atk', 86: 'atk', 52: 'def', 87: 'def' };
  const parse = (rows, tgt) => {
    for (const r of rows) {
      let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      for (const t of ts) {
        const tr = (t || {}).trait || {};
        const kind = kinds[tr.trait_type];
        if (!kind) continue;
        const ac = tr.active_condition || {};
        const cq = condTagsOf(ac);
        let tensionReq = 0;
        if (ac.tension) { const _rs = String(ac.tension).split(',').map(x => TENSION_RANK[x.trim()] || 0).filter(Boolean); if (_rs.length) tensionReq = Math.min(..._rs); }   // 「超强势以上」编码为档位集合 → 阈值取最低档
        (tgt[r.char_id] = tgt[r.char_id] || []).push({ sort: r.sort || 0, kind, v: tr.trait_value || 1, tensionReq, reqTags: cq.tags, reqSeries: cq.series, reqUnits: cq.units, roleReq: cq.role, bag: cq.bag, ctx: cq.ctx });
      }
    }
  };
  parse(q('SELECT char_id, sort, traits_json FROM char_abilities'), _charSup.base);
  parse(q('SELECT char_id, sort, traits_json FROM char_abilities_sp'), _charSup.sp);
  return _charSup;
}
/* 驾驶员次数技能(按当前机体/战意/条件开关判定): → {atk, def} */
function supCountsOf(charId, unitId, vigorKey, condAll, spOn) {
  const o = charSupEntries();
  const list = mergeSp(o.base[charId] || [], spOn === false ? null : (o.sp[charId] || []));
  const meta = unitId ? metaOf(unitId) : null;
  const out = { atk: 0, def: 0 };
  for (const p of list) if (condOk(p, meta, { condAll, vigor: vigorKey })) out[p.kind] += (p.v || 1);
  if (unitId) {   // ULT改造能力「支援攻击/支援防御次数增加」三选一生效时
    out.atk += ultSupportAdd({ id: unitId, ult: 1 }, 'atk');
    out.def += ultSupportAdd({ id: unitId, ult: 1 }, 'def');
  }
  return out;
}
/* 特性芯片显示用: 驾驶员某类次数技能(+1次型)条目数(含SP槽位, 同特性页口径) → N */
function supFeatCountOf(charId, kind) {
  const o = charSupEntries();
  const list = mergeSp(o.base[charId] || [], state.featPSpU !== false ? (o.sp[charId] || []) : null);
  return list.filter(p => p.kind === kind).length;
}
function supCountsTxt(s) {
  const t = [];
  if (s && s.atk) t.push('支援攻击/反击+' + s.atk + '次');
  if (s && s.def) t.push('支援防御+' + s.def + '次');
  return t.join(' · ');
}
function supCountsBadge(s) {
  if (!s || (!s.atk && !s.def)) return '';
  return (s.atk ? ` <span style="color:#f5c451;font-weight:700" title="支援攻击/反击 +${s.atk}次">支攻+${s.atk}</span>` : '')
       + (s.def ? ` <span style="color:#8fc4ff;font-weight:700" title="支援防御 +${s.def}次">支防+${s.def}</span>` : '');
}
/* opts: {passive, skills, condAll} → {dmg, melee, ranged, awaken} */
function charBonus(charId, vigorKey, opts, meta) {
  const out = { dmg: 0, melee: 0, ranged: 0, awaken: 0, atk: 0 };
  const spOn = opts.pSpU !== false;
  if (opts.passive) for (const p of charPsvOf(charId, spOn, false)) {
    if (condOk(p, meta, { condAll: opts.condAll, vigor: vigorKey })) out[p.kind] += stackEff(p, opts);
  }
  if (opts.passive) { const _ctM = {}; for (const p of charPsvOf(charId, spOn, true)) {   // 敌方条件被动
    if (opts.enemyMeta) { if (reqOk(p.reqTags, p.reqSeries, opts.enemyMeta)) out[p.kind] += p.v; }
    else if (opts.condAll !== false) {
      if (p.ctags && p.ctags.length) { _ctM[p.kind] = Math.max(_ctM[p.kind] || 0, p.v); }   // 驾驶员标签类互斥: 假设模式每类只取最高
      else out[p.kind] += p.v;
    }
  } for (const k in _ctM) out[k] += _ctM[k]; }
  if (opts.skills) for (const p of charSkillOf(charId, spOn)) out[p.kind] += p.v;
  for (const g of grantedTraits(opts.unitId, charId, meta, { ...opts, vigor: vigorKey })) {   // 多阶段增益赋予
    const tt = g.trait_type, v = g.trait_value || 0;
    if (tt === 17 || tt === 8) out.dmg += v;
    else if (tt === 7) out.atk += v;
    else if (tt === 21) out.ranged += v;
    else if (tt === 23) out.melee += v;
    else if (tt === 29) out.awaken += v;
  }
  return out;
}
/* 敌方条件被动备注(「对特定标签目标生效」的加成注明; 覆盖 机体被动+机师被动):
   与计入口径一致 — 指定对手(enemyMeta, 组队防御目标)时仅列命中项; 未指定时按「条件全开」计入的也列出 */
function enemyCondNotes(unitId, charId, opts, sspOn, w) {
  const em = opts.enemyMeta;
  const hit = p => {
    if (em) {
      if (!reqOk(p.reqTags, p.reqSeries, em)) return false;
      if (p.ctags && p.ctags.length && !(em.ctags && p.ctags.some(t => em.ctags.has(t)))) return false;
      return true;
    }
    return opts.condAll !== false;
  };
  const KN = { atk: '攻击', dmg: '增伤', melee: '格斗', ranged: '射击', awaken: '觉醒' };
  const labels = [], detail = [];
  const lab = p => {
    const a = [];
    const tg = [...new Set(p.reqTags || [])], se = [...new Set(p.reqSeries || [])], ct = [...new Set(p.ctags || [])];
    if (tg.length) a.push('敌·' + tg.join('/'));
    if (se.length) a.push('敌·' + se.join('/'));
    if (ct.length) a.push('敌驾驶员·' + ct.join('/'));
    return a.join(' ');
  };
  const tname = p => [...new Set((p.reqTags || []).concat(p.reqSeries || [], p.ctags || []))].join('/');
  const pushNote = (src, p) => { const l = lab(p); if (l && labels.indexOf(l) < 0) labels.push(l); detail.push(src + ' 敌「' + tname(p) + '」' + (src === '机体' ? '攻击' : (KN[p.kind] || '')) + '+' + p.v + '%'); };
  if (unitId && opts.upassive !== false) { const bm = {}; for (const p of (unitPassivesEnemy(sspOn)[unitId] || [])) {
    if (!hit(p)) continue;
    if (!em && p.ctags && p.ctags.length) { const k = p.kind || ''; if (!bm[k] || p.v > bm[k].v) bm[k] = p; continue; }   // 假设模式: 驾驶员标签类互斥取最高
    pushNote('机体', p);
  } for (const k in bm) pushNote('机体', bm[k]); }
  if (charId && opts.passive !== false) { const bm = {}; for (const p of charPsvOf(charId, opts.pSpU !== false, true)) {
    if (!hit(p)) continue;
    if (!em && p.ctags && p.ctags.length) { if (!bm[p.kind] || p.v > bm[p.kind].v) bm[p.kind] = p; continue; }
    pushNote('机师', p);
  } for (const k in bm) pushNote('机师', bm[k]); }
  if (w) {   // 武器条件特效(weapon_traits.cond: 「发起对战的敌方包含X…」)
    const WKN = { 9: '防御力减少', 44: '威力上限', 45: '威力上限', 81: '威力上限', 82: '威力上限', 91: '威力上限', 92: '威力上限' };
    const wid = (w && typeof w === 'object') ? w.id : w;
    const seen = {};
    for (const x of _wtRowsOf(wid)) {
      if (!x.cq) continue;
      if (!_wCondOk(x.cq, em, opts.condAll)) continue;
      const key = x.tr.trait_type + '|' + x.tr.trait_value + '|' + x.cq.tags.join(',') + x.cq.series.join(',');
      if (seen[key]) continue; seen[key] = 1;   // 同效果多等级行去重
      const l = lab({ reqTags: x.cq.tags, reqSeries: x.cq.series, ctags: x.cq.ctags });
      if (l && labels.indexOf(l) < 0) labels.push(l);
      const eff = x.tr.trait_type === 9 ? ('防御力减少' + Math.abs(x.tr.trait_value) + '%') : ((WKN[x.tr.trait_type] || '效果') + '+' + x.tr.trait_value + '%');
      detail.push('武器 敌「' + tname({ reqTags: x.cq.tags, reqSeries: x.cq.series, ctags: x.cq.ctags }) + '」' + eff);
    }
  }
  return { labels, detail };
}

/* ------------ 气势 MP（口径=soshage引擎: MP≥4 强势 / ≥8 超强势 / ≥12 超一击）------------
   第一击 = 驾驶员/机体被动「MP提升」(trait 46)；技能全开再 + 主动技能 MpBoost (trait 4) */
const mpToVigor = mp => (mp >= 12 ? 'supercharged' : mp >= 8 ? 'max' : mp >= 4 ? 'high' : 'mid');
let _charMeta = null, _charMp = null, _unitMp = null, _skillMp = null, _charMpSp = null, _skillMpSp = null;
let _charSerMap = null;
function charSeriesMap() {      // 驾驶员 series_set_id → 系列id (经 units.series_set_id 映射; 低位数减 1e16 只对部分系列成立)
  if (_charSerMap) return _charSerMap;
  _charSerMap = {};
  for (const r of q('SELECT DISTINCT series_set_id ss, series_id sid FROM units')) _charSerMap[String(r.ss)] = String(r.sid);
  return _charSerMap;
}
function charMetaAll() {
  if (_charMeta) return _charMeta;
  _charMeta = {};
  for (const r of q('SELECT id FROM characters')) _charMeta[r.id] = { tags: new Set(), series: '' };
  for (const r of q('SELECT ct.char_id, t.name FROM char_tags ct JOIN tags t ON t.id=ct.tag_id')) {
    if (_charMeta[r.char_id]) _charMeta[r.char_id].tags.add(r.name);
  }
  const _sd2 = seriesNameDict();
  for (const r of q('SELECT id, series_set_id FROM characters')) {
    if (_charMeta[r.id]) _charMeta[r.id].series = _sd2[charSeriesMap()[String(r.series_set_id)]] || '';
  }
  return _charMeta;
}
const charMetaOf = id => charMetaAll()[id] || { tags: new Set(), series: '' };
function reqOk(reqTags, reqSeries, meta, reqUnits) {
  if (reqUnits && reqUnits.length && (!meta || !reqUnits.includes(meta.id))) return false;   // 搭乘指定机体
  const needTags = !!(reqTags && reqTags.length), needSer = !!(reqSeries && reqSeries.length);
  if (!needTags && !needSer) return true;
  if (!meta) return false;
  let tagHit = false, serHit = false;
  if (needSer && (meta.seriesList ? reqSeries.some(s => meta.seriesList.has(s)) : (meta.series && reqSeries.includes(meta.series)))) serHit = true;
  if (needTags && meta.tags) for (const t of reqTags) if (meta.tags.has(t)) { tagHit = true; break; }
  if (needTags && needSer) return tagHit && serHit;   // 「标签及系列」两者都要
  return needTags ? tagHit : serHit;
}
/* 驾驶员被动 MP提升: trait46(自身/标签/系列条件) 与 trait43(战斗开始时敌方含标签) */
function charMpAbilities() {
  if (_charMp) return _charMp;
  _charMp = {}; _charMpSp = {};
  const parse = (rows, tgt) => {
    for (const r of rows) {
      let trs = []; try { trs = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      for (const t of trs) {
        const tr = (t || {}).trait || {};
        if (!(tr.trait_value > 0)) continue;
        if (tr.trait_type === 46) {
          const ac = tr.active_condition || {};
          const cq = condTagsOf(ac);
          let tensionReq = 0;
          if (ac.tension) { const _rs = String(ac.tension).split(',').map(x => TENSION_RANK[x.trim()] || 0).filter(Boolean); if (_rs.length) tensionReq = Math.min(..._rs); }   // 「超强势以上」编码为档位集合 → 阈值取最低档
          (tgt[r.char_id] = tgt[r.char_id] || []).push({ sort: r.sort || 0, v: tr.trait_value, tensionReq, reqTags: cq.tags, reqSeries: cq.series, reqUnits: UNIT_GATE_BUG_CHARS.has(r.char_id) ? [] : cq.units, ctx: cq.ctx });
        } else if (tr.trait_type === 43) {   // 战斗开始时敌方部队含标签 → 自身MP提升(条件被动开时计入)
          const cq = condTagsOf(tr.active_condition || {});
          (tgt[r.char_id] = tgt[r.char_id] || []).push({ sort: r.sort || 0, v: tr.trait_value, enemy: true, reqTags: cq.tags, reqSeries: cq.series });
        }
      }
    }
  };
  parse(q('SELECT char_id, sort, traits_json FROM char_abilities'), _charMp);
  parse(q('SELECT char_id, sort, traits_json FROM char_abilities_sp'), _charMpSp);
  return _charMp;
}
function charMpAbilOf(id, spOn) {
  charMpAbilities();
  const base = _charMp[id] || [];
  if (spOn === false) return base;
  return mergeSp(base, _charMpSp[id]);
}
/* 机体被动 MP提升 trait46（条件=搭乘驾驶员标签/系列） */
let _unitMpS = null;
function unitMpAbilities(sspOn) {   // 机体MP提升: base 与 SSP能力变化 双视图
  if (!_unitMp) {
    _unitMp = {}; _unitMpS = {};
    const parse = (rows, tgt) => {
      const td = tagNameDict();
      for (const r of rows) {
        let trs = []; try { trs = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        for (const t of trs) {
          const tr = (t || {}).trait || {};
          if (tr.trait_type !== 46 || !(tr.trait_value > 0)) continue;
          const ac = tr.active_condition || {};
          const tags = [];
          for (const x of (ac.character_tags || [])) { const nm = x && (td[x.id] || x.name); if (nm) tags.push(nm); }
          for (const raw of String(ac.character_tags_id || '').split(',')) { const id = +raw; if (id && td[id]) tags.push(td[id]); }
          (tgt[r.unit_id] = tgt[r.unit_id] || []).push({ v: tr.trait_value, reqTags: tags, reqSeries: [], ctx: ctxOf(ac) });
        }
      }
    };
    const all = unitAbilitiesAll();
    const uids = new Set([...Object.keys(all.base), ...Object.keys(all.ssp)].map(Number));
    for (const uid of uids) { parse(unitAbilitiesOf(uid, false), _unitMp); parse(unitAbilitiesOf(uid, true), _unitMpS); }
  }
  return (sspOn && _unitMpS) ? _unitMpS : _unitMp;
}
/* 主动技能 MpBoost (trait 4，无条件) */
function charMpSkills() {
  if (_skillMp) return _skillMp;
  _skillMp = {}; _skillMpSp = {};
  const parse = (rows, tgt) => {
    for (const r of rows) {
      let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      for (const set of ts) {
        const tr = (set || {}).trait || {};
        if (tr.trait_type === 4 && tr.trait_value > 0) {
          const ac = tr.active_condition || {};
          const cq = condTagsOf(ac);
          let tensionReq = 0;
          if (ac.tension) { const _rs = String(ac.tension).split(',').map(x => TENSION_RANK[x.trim()] || 0).filter(Boolean); if (_rs.length) tensionReq = Math.min(..._rs); }   // 「超强势以上」编码为档位集合 → 阈值取最低档
          (tgt[r.char_id] = tgt[r.char_id] || []).push({ sort: r.sort || 0, v: tr.trait_value, tensionReq, reqTags: cq.tags, reqSeries: cq.series, reqUnits: cq.units, ctx: cq.ctx });
        }
      }
    }
  };
  parse(q('SELECT char_id, sort, traits_json FROM char_skills'), _skillMp);
  parse(q('SELECT char_id, sort, traits_json FROM char_skills_sp'), _skillMpSp);
  return _skillMp;
}
function charMpSkillOf(id, spOn) {
  charMpSkills();
  const base = _skillMp[id] || [];
  if (spOn === false) return base;
  return mergeSp(base, _skillMpSp[id]);
}
/* 主动闪避技能: 摇摆闪避(trait_type 14) / 命中率、闪避率提升(trait_type 6) — 双版本按槽位替换 */
let _evSk = null;
function charEvadeSkills() {
  if (_evSk) return _evSk;
  _evSk = { base: {}, sp: {} };
  const parse = (rows, tgt) => {
    for (const r of rows) {
      let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      let v = 0;
      for (const set of ts) {
        const tr = (set || {}).trait || {};
        if (tr.trait_type === 6 && tr.trait_value > 0) v = Math.max(v, tr.trait_value);              // 闪避率提升N%
        else if (tr.trait_type === 14 && (tr.desc || '').includes('闪避')) {                          // 摇摆闪避(数值为档位, 从文案取%)
          const m = /闪避率提升\s*(\d+)%/.exec(tr.desc || '');
          v = Math.max(v, m ? +m[1] : 100);
        }
      }
      if (v > 0) (tgt[r.char_id] = tgt[r.char_id] || []).push({ sort: r.sort || 0, name: r.name, desc: r.desc, v });
    }
  };
  parse(q('SELECT char_id, sort, name, desc, traits_json FROM char_skills'), _evSk.base);
  parse(q('SELECT char_id, sort, name, desc, traits_json FROM char_skills_sp'), _evSk.sp);
  return _evSk;
}
function charEvadeOf(id, spOn) {
  charEvadeSkills();
  const base = _evSk.base[id] || [];
  if (spOn === false) return base;
  return mergeSp(base, _evSk.sp[id]);
}
/* ------------ 竞技场「首动」(官方AI主动技能优先度图, 从上至下/条件不满足跳过) ------------
   假设: 满血满EN·够得着·命中充足 → 跳过 射程增幅/高速/HP修复/锁定
   图序: 威力抵御(减伤) > MP提升 > 命中率·闪避率提升(会被反死) > 攻击爆裂 > 摇摆闪避(会被反死)
        > 值增幅(用对应属性武装) > 爆击增幅 > 保留EN。每动只放1个技能, 只吃该技加成。 */
const FA_STAT = { ranged: '射击值增幅', melee: '格斗值增幅', awaken: '觉醒值增幅' };
let _faSk = null;
function charActSkillRows(id, spOn) {
  if (!_faSk) {
    _faSk = { base: {}, sp: {} };
    for (const r of q('SELECT char_id, sort, name, desc FROM char_skills')) (_faSk.base[r.char_id] = _faSk.base[r.char_id] || []).push(r);
    for (const r of q('SELECT char_id, sort, name, desc FROM char_skills_sp')) (_faSk.sp[r.char_id] = _faSk.sp[r.char_id] || []).push(r);
  }
  const base = _faSk.base[id] || [];
  const rows = ((spOn === false) ? base.slice() : mergeSp(base, _faSk.sp[id] || [])).slice();
  return rows.sort((a, b) => (a.sort || 0) - (b.sort || 0));
}
function firstActOfRows(rows, attrs, fdth, mp) {   // mp=自身被动MP: 「MP提升」仅自身MP≥3时释放(官方规则)
  const f = re => rows.find(r => re.test(r.name));
  let r, m;
  if ((r = f(/^威力抵御/))) return { k: 'guard', name: r.name };                              // 减伤(必用)
  if ((r = f(/^MP提升/)) && (mp || 0) >= 3) return { k: 'mp', name: r.name };                 // +MP (MP≥3)
  if (fdth && (r = f(/^命中率、闪避率提升/))) return { k: 'eva', name: r.name };               // +命中闪避(会被反死)
  if ((r = f(/^攻击爆裂/))) { m = /损伤提升\s*(\d+)%/.exec(r.desc || ''); return { k: 'burst', name: r.name, v: m ? +m[1] : 0 }; }
  if (fdth && (r = f(/^摇摆闪避/))) return { k: 'sway', name: r.name };                        // 摇摆闪避(会被反死)
  for (const a of (attrs || [])) {                                                             // 值增幅(用对应属性武装)
    if (!FA_STAT[a]) continue;
    if ((r = f(new RegExp('^' + FA_STAT[a])))) { m = /提升\s*(\d+)%/.exec(r.desc || ''); return { k: 'stat', stat: a, name: r.name, v: m ? +m[1] : 0 }; }
  }
  if ((r = f(/^爆击增幅/))) return { k: 'crit', name: r.name };
  if ((r = f(/^保留EN/))) return { k: 'en', name: r.name };
  return { k: 'none', name: null };
}
function firstActOf(id, spOn, attrs, fdth, mp) { return firstActOfRows(charActSkillRows(id, spOn), attrs, fdth, mp); }
/* 气势MP（机体+驾驶员组合）: 被动恒计; useSkills=true 时再计主动技能 */
function mpOf(unitId, charId, useSkills, condAll, pSpU, ussp) {
  let mp = 0;
  const uMeta = metaOf(unitId);
  for (const p of charMpAbilOf(charId, pSpU)) {
    if (p.enemy) { if (condAll !== false) mp += p.v; continue; }   // 敌方条件: 条件被动开时计入
    if (p.ctx && condAll === false) continue;                      // 状态条件(HP等): 仅条件开计入
    if (reqOk(p.reqTags, p.reqSeries, uMeta, p.reqUnits)) mp += p.v;
  }
  const cMeta = charMetaOf(charId);
  for (const p of (unitMpAbilities(ussp)[unitId] || [])) { if (p.ctx && condAll === false) continue; if (reqOk(p.reqTags, p.reqSeries, cMeta, p.reqUnits)) mp += p.v; }
  if (useSkills) for (const p of charMpSkillOf(charId, pSpU)) { if (p.ctx && condAll === false) continue; mp += p.v; }
  if (unitId && state.uSk !== false && ultGroupOf(unitId)) mp += ultTraitSum({ id: unitId, ult: 1 }, 12);   // ULT改造能力「MP提升」
  return mp;
}

/* ------------ 单位技能（主动技能开关控制）: trait_type_index 2=攻击力提升% ------------ */
let _usk = null;
function unitSkillAtkPct(unitId) {
  if (!_usk) {
    _usk = {};
    for (const r of q("SELECT target_id, params_json FROM features WHERE feature='unit_skill'")) {
      let pr = {}; try { pr = JSON.parse(r.params_json || '{}'); } catch (e) {}
      if (pr.ult) continue;   // ULT改造能力: 三选一, 走 ultSkill 选择
      let pct = 0;
      for (const t of (pr.traits || [])) if (t && t.trait_type_index === 2) pct += (t.trait_value || 0);
      if (pct) _usk[r.target_id] = pct;
    }
  }
  return _usk[unitId] || 0;
}

/* ------------ 暴击能力（39=暴击损伤% / 62=暴击率% / 94=必定暴击）------------
   无暴击率来源时，暴击开关不生效（与游戏一致） */
function _collectCrit(tbl, idCol, hasSort) {
  const out = {};
  for (const r of q(`SELECT ${idCol} id, ${hasSort ? 'sort,' : ''} traits_json FROM ${tbl}`)) {
    let trs = []; try { trs = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
    for (const t of trs) {
      const tr = (t || {}).trait || {};
      const tt = tr.trait_type;
      if (tt !== 39 && tt !== 62 && tt !== 94) continue;
      const ac = tr.active_condition || {};
      let tensionReq = 0;
      if (ac.tension) { const _rs = String(ac.tension).split(',').map(x => TENSION_RANK[x.trim()] || 0).filter(Boolean); if (_rs.length) tensionReq = Math.min(..._rs); }   // 「超强势以上」编码为档位集合 → 阈值取最低档
      const cq = condTagsOf(ac);
      (out[r.id] = out[r.id] || []).push({ sort: r.sort || 0, tt, v: tr.trait_value || 0, tensionReq, reqTags: cq.tags, reqSeries: cq.series, reqUnits: (idCol === 'char_id' && UNIT_GATE_BUG_CHARS.has(r.id)) ? [] : cq.units, ctx: cq.ctx });
    }
  }
  return out;
}
let _critU = null, _critC = null, _critSk = null;
let _critUS = null;
function unitCritAll(sspOn) {      // 机体暴击被动: base 与 SSP能力变化 双视图
  if (!_critU) {
    _critU = {}; _critUS = {};
    const parse = (rows, tgt) => {
      for (const r of rows) {
        let trs = []; try { trs = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        for (const t of trs) {
          const tr = (t || {}).trait || {};
          const tt = tr.trait_type;
          if (tt !== 39 && tt !== 62 && tt !== 94) continue;
          const ac = tr.active_condition || {};
          let tensionReq = 0;
          if (ac.tension) { const _rs = String(ac.tension).split(',').map(x => TENSION_RANK[x.trim()] || 0).filter(Boolean); if (_rs.length) tensionReq = Math.min(..._rs); }   // 「超强势以上」编码为档位集合 → 阈值取最低档
          const cq = condTagsOf(ac);
          (tgt[r.unit_id] = tgt[r.unit_id] || []).push({ tt, v: tr.trait_value || 0, tensionReq, reqTags: cq.tags, reqSeries: cq.series, reqUnits: cq.units, ctx: cq.ctx });
        }
      }
    };
    const all = unitAbilitiesAll();
    const uids = new Set([...Object.keys(all.base), ...Object.keys(all.ssp)].map(Number));
    for (const uid of uids) { parse(unitAbilitiesOf(uid, false), _critU); parse(unitAbilitiesOf(uid, true), _critUS); }
  }
  return (sspOn && _critUS) ? _critUS : _critU;
}
const charCritAll = () => (_critC = _critC || { base: _collectCrit('char_abilities', 'char_id', true), sp: _collectCrit('char_abilities_sp', 'char_id', true) });
function charCritOf(id, spOn) {
  const o = charCritAll();
  const base = o.base[id] || [];
  if (spOn === false) return base;
  return mergeSp(base, o.sp[id]);
}
function charCritSkills() {          // 主动技能: 12=暴击率% / 94=必暴
  if (_critSk) return _critSk;
  _critSk = { base: {}, sp: {} };
  const parse = (rows, tgt) => {
    for (const r of rows) {
      let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      for (const set of ts) {
        const tr = (set || {}).trait || {};
        if ((tr.trait_type === 12 && tr.trait_value > 0) || tr.trait_type === 94)
          (tgt[r.char_id] = tgt[r.char_id] || []).push({ sort: r.sort || 0, tt: tr.trait_type, v: tr.trait_value || 0 });
      }
    }
  };
  parse(q('SELECT char_id, sort, traits_json FROM char_skills'), _critSk.base);
  parse(q('SELECT char_id, sort, traits_json FROM char_skills_sp'), _critSk.sp);
  return _critSk;
}
function charCritSkillOf(id, spOn) {
  const o = charCritSkills();
  const base = o.base[id] || [];
  if (spOn === false) return base;
  return mergeSp(base, o.sp[id]);
}
/* 暴击信息(驾驶员/机体侧, 与武器无关): {rate, guar, cdmg}
   62=被动暴击率 / 12=技能暴击率 / 94=必暴 / 39=暴击损伤 */
function pilotCritInfo(unitId, charId, meta, opts) {
  let rate = 0, guar = false, cdmg = 0;
  const ck = list => { for (const p of (list || [])) if (condOk(p, meta, opts)) { if (p.tt === 62 || p.tt === 12) rate += p.v; else if (p.tt === 94) guar = true; else if (p.tt === 39) cdmg += p.v; } };
  if (unitId && opts.upassive !== false) ck(unitCritAll(opts.ussp)[unitId]);     // 机体被动(随SSP能力变化)
  if (charId && opts.cpassive !== false) ck(charCritOf(charId, opts.pSpU !== false));     // 驾驶员被动
  if (opts.skills && charId) ck(charCritSkillOf(charId, opts.pSpU !== false));            // 主动技能
  for (const g of grantedTraits(unitId, charId, meta, opts)) {          // 多阶段增益赋予(暴击率/必暴)
    if (g.trait_type === 62) rate += g.trait_value || 0;
    else if (g.trait_type === 94) guar = true;
    else if (g.trait_type === 39) cdmg += g.trait_value || 0;
  }
  return { rate: Math.max(0, Math.min(100, rate)), guar, cdmg };
}
/* 含武器基础暴击率 */
function critInfo(unitId, charId, w, meta, opts) {
  const pc = pilotCritInfo(unitId, charId, meta, opts);
  let wGuar = false;   // 武器侧必暴(trait 94, 含SSP合并)
  try { for (const t of wTraitsOf(w, null, (opts && opts.condAll) !== false)) if (t.trait_type === 94) { wGuar = true; break; } } catch (e) {}
  return { rate: Math.max(0, Math.min(100, ((w && w.crit_rate) || 0) + pc.rate)), guar: pc.guar || wGuar, cdmg: pc.cdmg };
}
const canCrit = ci => ci.guar || ci.rate > 0;

/* ------------ 多阶段增益（超一击EX1/EX2 赋予）------------
   来源: trait_type=13 且 action_timing=18 且 战意条件=Supercharged 的赋予类能力
   多阶段增益 关(depth1)=直接赋予(EX1)；开(depth2)=再展开一层(EX2)；仅 超一击 时生效 */
function _collectGrants(tbl, idCol, hasSort) {
  const out = {};
  for (const r of q(`SELECT ${idCol} id, ${hasSort ? 'sort,' : ''} traits_json FROM ${tbl}`)) {
    let trs = []; try { trs = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
    for (const t of trs) {
      const tr = (t || {}).trait || {};
      if (tr.trait_type !== 13 || tr.action_timing !== 18) continue;
      if ((tr.active_condition || {}).tension !== 'Supercharged') continue;
      const gts = tr.granted_trait_set || [];
      if (!gts.length) continue;
      const direct = gts.map(x => (x || {}).trait).filter(Boolean);
      const g1 = direct.filter(x => x.trait_type !== 13);
      const g2 = direct.filter(x => x.trait_type === 13)
        .flatMap(x => (x.granted_trait_set || []).map(y => (y || {}).trait).filter(Boolean))
        .filter(x => x.trait_type !== 13);
      const cq = condTagsOf(tr.active_condition || {});
      (out[r.id] = out[r.id] || []).push({ sort: r.sort || 0, g1, g2, reqTags: cq.tags, reqSeries: cq.series, reqUnits: cq.units, roleReq: cq.role, bag: cq.bag, ctx: cq.ctx, desc: tr.desc || '' });
    }
  }
  return out;
}
let _grantC = null, _grantU = null, _grantUS = null;
const charGrantsAll = () => (_grantC = _grantC || { base: _collectGrants('char_abilities', 'char_id', true), sp: _collectGrants('char_abilities_sp', 'char_id', true) });
function unitGrantsAll(sspOn) {   // 机体多阶段赋予: base 与 SSP能力变化 双视图
  if (!_grantU) {
    _grantU = {}; _grantUS = {};
    const mkParse = (tgt) => (rows, idCol) => {   // 复用 _collectGrants 的解析逻辑
      for (const r of rows) {
        let trs = []; try { trs = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        for (const t of trs) {
          const tr = (t || {}).trait || {};
          if (tr.trait_type !== 13 || tr.action_timing !== 18) continue;
          if ((tr.active_condition || {}).tension !== 'Supercharged') continue;
          const gts = tr.granted_trait_set || [];
          if (!gts.length) continue;
          const direct = gts.map(x => (x || {}).trait).filter(Boolean);
          const g1 = direct.filter(x => x.trait_type !== 13);
          const g2 = direct.filter(x => x.trait_type === 13)
            .flatMap(x => (x.granted_trait_set || []).map(y => (y || {}).trait).filter(Boolean))
            .filter(x => x.trait_type !== 13);
          const cq = condTagsOf(tr.active_condition || {});
          (tgt[r.unit_id] = tgt[r.unit_id] || []).push({ sort: r.sort || 0, g1, g2, reqTags: cq.tags, reqSeries: cq.series, reqUnits: cq.units, roleReq: cq.role, bag: cq.bag, ctx: cq.ctx, desc: tr.desc || '' });
        }
      }
    };
    const p1 = mkParse(_grantU), p2 = mkParse(_grantUS);
    const all = unitAbilitiesAll();
    const uids = new Set([...Object.keys(all.base), ...Object.keys(all.ssp)].map(Number));
    for (const uid of uids) { p1(unitAbilitiesOf(uid, false), 'unit_id'); p2(unitAbilitiesOf(uid, true), 'unit_id'); }
  }
  return (sspOn && _grantUS) ? _grantUS : _grantU;
}
function charGrantsOf(id, spOn) {
  const o = charGrantsAll();
  const base = o.base[id] || [];
  if (spOn === false) return base;
  return mergeSp(base, o.sp[id]);
}
/* 当前生效的赋予 traits（战意=超一击 且 条件匹配 且 对应开关开） */
function grantedTraits(unitId, charId, meta, opts) {
  if (opts.vigor !== 'supercharged') return [];
  const out = [];
  const take = list => { for (const p of (list || [])) if (condOk(p, meta, opts)) for (const g of (opts.multiPhase ? p.g2 : p.g1)) out.push(g); };
  if (charId && opts.cpassive !== false) take(charGrantsOf(charId, opts.pSpU !== false));
  if (unitId && opts.upassive !== false) take(unitGrantsAll(opts.ussp)[unitId]);
  return out;
}
/* 赋予效果文字 */
function grantTxt(g) {
  const v = g.trait_value || 0;
  const m = { 17: '增伤', 8: '增伤', 21: '射击值', 23: '格斗值', 29: '觉醒值', 27: '反应值', 62: '暴击率', 39: '暴击损伤', 7: '攻击力' };
  if (g.trait_type === 94) return '必定暴击';
  if (m[g.trait_type]) return m[g.trait_type] + '+' + v + '%';
  return null;
}


/* ------------ 单位标签/系列缓存 & 条件匹配 ------------ */
let _unitMeta = null, _tagNames = null;
function tagNameDict() {
  if (_tagNames) return _tagNames;
  _tagNames = {};
  for (const r of q('SELECT id, name FROM tags')) _tagNames[r.id] = r.name;
  return _tagNames;
}
let _seriesNames = null;
function seriesNameDict() {
  if (_seriesNames) return _seriesNames;
  _seriesNames = {};
  for (const r of q('SELECT id, name FROM series')) _seriesNames[r.id] = r.name;
  return _seriesNames;
}
function unitMetaAll() {
  if (_unitMeta) return _unitMeta;
  _unitMeta = {};
  const _sd0 = seriesNameDict();
  for (const r of q('SELECT u.id, u.role, u.series_id, u.series_set_json, s.name sname FROM units u LEFT JOIN series s ON s.id = u.series_id')) {
    /* series=主系列(显示/筛选); seriesList=series_set全集(条件匹配用 —— 参考站 unit_series 判定 series_set 任一项) */
    const list = new Set();
    const prim = r.sname || _sd0[String(r.series_id)] || '';
    if (prim) list.add(prim);
    try { for (const sid of JSON.parse(r.series_set_json || '[]')) { const nm = _sd0[String(sid)]; if (nm) list.add(nm); } } catch (e) {}
    _unitMeta[r.id] = { id: r.id, tags: new Set(), series: prim, seriesList: list, role: r.role || 0 };
  }
  for (const r of q('SELECT ut.unit_id, t.name FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id')) {
    if (_unitMeta[r.unit_id]) _unitMeta[r.unit_id].tags.add(r.name);
  }
  return _unitMeta;
}
const metaOf = id => unitMetaAll()[id] || { tags: new Set(), series: '', seriesList: new Set(), role: 0 };
/* 状态/场景条件检测(HP・EN阈值/攻击距离/回合/单挑/地形/体型/武装属性): 计算页无法核验 → 仅「假设满足」计入 */
function ctxOf(ac) {
  return !!(ac.hp_rate_lte_threshold || ac.hp_rate_gte_threshold || ac.hp_type ||
            ac.en_rate_lte_threshold || ac.en_rate_gte_threshold ||
            ac.en_value_lte_threshold || ac.en_value_gte_threshold || ac.use_hp_rate_lte_threshold ||
            ac.attack_distance_gte_threshold || ac.attack_distance_lte_threshold || ac.turn_number ||
            ac.is_in_one_on_one || ac.is_in_chance_step ||
            String(ac.unit_size || '').trim() || String(ac.standby_terrain || '').trim() ||
            String(ac.weapon_attribute || '').trim() || String(ac.weapon_attack_attribute || '').trim());
}
/* 条件解析: 一律按 ID 查名（原始文本为繁体，库里是简体，按名直配会漏） */
function condTagsOf(ac) {
  const tags = [], series = [];
  const td = tagNameDict();
  for (const t of (ac.tags || [])) { const nm = t && (td[t.id] || t.name); if (nm) tags.push(nm); }
  for (const raw of String(ac.unit_tags || '').split(',')) { const id = +raw; if (id && td[id]) tags.push(td[id]); }
  const sd = seriesNameDict();
  const sidRaw = String(ac.unit_series || (ac.series && ac.series.id) || '');
  let sidHit = false;
  for (const part of sidRaw.split(',')) { const sid = part.trim(); if (sid && sd[sid]) { series.push(sd[sid]); sidHit = true; } }   // 支持 "1100,1500" 多系列
  if (!sidHit && ac.series && ac.series.name) series.push(ac.series.name);
  const units = String(ac.unit_ids || '').split(',').map(x => +x.trim()).filter(Boolean);
  const role = +ac.unit_role || 0;                       // 搭乘机体类型要求(1攻/2耐/3支)
  const bag = String(ac.map_battle_action || '').trim(); // 战斗动作要求(如 SupportAttack,SupportCounter / Attack)
  const ctags = (ac.character_tags || []).map(x => x && (x.name || tagNameDict()[x.id])).filter(Boolean);   // 驾驶员标签条件(敌方角色/搭乘角色)
  const ctx = ctxOf(ac);
  return { tags, series, units, role, bag, ctags, ctx };
}
/* 驾驶员/机体被动条件判定: 特定机体/标签/系列条件必须与搭乘对象匹配; 战意条件按当前气势判定(condAll=条件全开) */
function condOk(p, meta, opts) {
  if (p.reqUnits && p.reqUnits.length && (!meta || !p.reqUnits.includes(meta.id))) return false;   // 搭乘指定机体
  const needTags = !!(p.reqTags && p.reqTags.length), needSer = !!(p.reqSeries && p.reqSeries.length);
  if (needTags || needSer) {
    if (!meta) return false;
    let tagHit = false, serHit = false;
    if (needSer && (meta.seriesList ? p.reqSeries.some(s => meta.seriesList.has(s)) : (meta.series && p.reqSeries.includes(meta.series)))) serHit = true;
    if (needTags && meta.tags) for (const t of p.reqTags) if (meta.tags.has(t)) { tagHit = true; break; }
    if (needTags && needSer) { if (!(tagHit && serHit)) return false; }   // 「标签及系列」两者都要满足
    else if (needTags) { if (!tagHit) return false; }
    else if (needSer) { if (!serHit) return false; }
  }
  if (p.roleReq && (!meta || meta.role !== p.roleReq)) return false;   // 搭乘机体类型(攻击/耐久/支援)不符 → 不生效
  if (p.bag) {   // 战斗动作条件: 「攻击时」在普通攻击口径即成立; 支援攻击/支援反击/反击由「支援攻击/反击」开关控制; 其他动作(支援防御/闪避)随条件全开
    const acts = String(p.bag).split(',').map(s => s.trim());
    const hasAttack = acts.includes('Attack');
    const hasSup = acts.some(a => a === 'SupportAttack' || a === 'SupportCounter' || a === 'Counter');
    if (hasSup && state.supAct === false && !hasAttack) return false;   // 关闭时不计算支援攻击/支援反击/反击被动
    if (!hasAttack && !hasSup && !opts.condAll) return false;
  }
  if (p.ctx && !opts.condAll) return false;   // 状态/场景条件(HP・EN阈值/距离/单挑等): 仅「假设满足」计入
  if (p.tensionReq) {
    if (opts.condAll) return true;
    return (VIGOR_RANK[opts.vigor] ?? 0) >= p.tensionReq;
  }
  return true;
}
/* 叠层被动取值: max开=最高N%(满层); 条件被动开=1层(base); 首动攻击次数型=0层 */
function stackEff(p, opts) {
  if (!p || p.mx == null) return p ? p.v : 0;
  if (p.stk === 'battle' && opts && opts.first) return 0;
  if (state.maxOn) return p.mx;
  if (opts && opts.condAll) return p.v;
  return 0;
}

/* 版本开关条件: weapon→含SP/SSP武器; unit→只看SP可强化/有SSP武器 */
function verCond(cat, f) {
  if (cat === 'weapon') {
    if (f.sp && f.ssp) return '';
    if (f.sp) return 'w.is_ssp=0';
    if (f.ssp) return 'w.is_ssp=1';
    return '1=0';
  }
  if (cat === 'unit') {
    const c = [];
    if (f.sp) c.push('(u.sp_max_atk IS NOT NULL AND u.sp_max_atk != u.max_atk)');
    if (f.ssp) c.push('EXISTS(SELECT 1 FROM weapons w WHERE w.unit_id=u.id AND w.is_ssp=1)');
    return c.join(' AND ');
  }
  return '';
}


/* ------------ 搜索别名（社区译名 ↔ 数据译名） ------------ */
const ALIAS_PAIRS = [['多蒙', '杜门'], ['阿姆罗', '阿宝'], ['夏亚', '马沙'], ['卡缪', '嘉美尤'], ['捷多', '杰多'], ['胡索', '伍索'], ['基拉', '煌'], ['阿斯兰', '亚斯兰']];
function aliasTerms(s) {
  let terms = [s];
  for (const [a, b] of ALIAS_PAIRS) {
    const next = [];
    for (const t of terms) {
      next.push(t);
      if (t.includes(a)) next.push(t.split(a).join(b));
      if (t.includes(b)) next.push(t.split(b).join(a));
    }
    terms = [...new Set(next)];
  }
  return terms;
}
function normQ(s) {                        // 输入归一: 全角→半角(中文输入法常出全角)
  return String(s == null ? '' : s).replace(/[！-～]/g, c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0)).replace(/　/g, ' ');
}
function nameLikeSql(col, qstr) {
  const terms = aliasTerms(normQ(qstr));
  return { sql: '(' + terms.map(() => col + ' LIKE ?').join(' OR ') + ')', args: terms.map(t => '%' + t + '%') };   // SQLite LIKE 对 ASCII 不区分大小写
}
function ciHas(hay, needle) {              // 大小写不敏感包含(弹窗内 JS 搜索用)
  if (!needle) return true;
  return normQ(hay).toLowerCase().includes(normQ(needle).toLowerCase());
}

/* ------------ 全局状态 ------------ */
const state = {
  tab: 'units', stack: [],          // 子页面栈
  uSk: true,                        // 机体技能(单位技能)计入开关 — 独立于驾驶员主动技能
  supAct: true,                     // 支援攻击/反击: 计入「支援攻击/支援反击/反击时」被动; 关=按普通攻击不计入
  maxOn: false,                     // max满层: 条件型叠层被动按最高N%; 关=条件被动按1层; 首动攻击次数型恒0层
  ultLv: 0,                         // ULT改造总等级: 0/50/100 三挡(三段共用; 50解锁武器, 100解锁能力)
  ultSkill: {},                     // group_id → 选中的三选一能力 skill_id (缺省=sort最小项)
  zoom: {},                          // 各分类过滤 {tags:[],mode:'and',search:''}
  calc: { unitId: null, charId: null, lv: 5, pRar: null, vigor: 'default', crit: false, star: true, s3u: true, spU: true, passive: true, cpassive: true, skills: true, mp: true, ca: true, tDef: 10000, tCharDef: 750, pSpU: true },
  team: { suppId: null, useBuff: true, pSpU: true, prar: null, spU: true, s3u: true },
  charSp: false,                     // 图鉴-驾驶员 SP 数值显示口径(默认基础值)
  rankCache: null, rankCfg: { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false, passive: true, cpassive: true, skills: true, ca: true, mp: true, star: 3, range: 'all', wat: null, atk: null, urole: null, rarity: null, prar: null, spU: true, s3u: true, sspU: true, pSpU: true },
  sort: {},                          // 各列表排序 { ctx: {f: 字段, d: 1顺序/-1倒序} }
  tabScroll: {},                     // 主标签页滚动位置(进入子页返回时恢复)
};
const filt = cat => (state.zoom[cat] = state.zoom[cat] || { tags: [], series: [], mode: 'and', search: '', rar: null, sp: ['weapon', 'rank', 'team'].includes(cat) ? 1 : 0, ssp: ['weapon', 'rank', 'team'].includes(cat) ? 1 : 0 });

/* ------------ 重置默认(计算/排行/组队): 标题栏中间按钮 ------------
   恢复本页全部黄/蓝选项开关与数值输入框为默认值 + 清空本页「标签/系列」筛选;
   保留已选机体/驾驶员(计算页 与 组队防御目标)与战舰; 只作用于当前页 */
function resetFiltOf(cat) {
  const f = filt(cat);
  f.tags = []; f.series = []; f.mode = 'and'; f.rar = null; f.role = null;
  if (['weapon', 'rank', 'team'].includes(cat)) { f.sp = 1; f.ssp = 1; }   // 版本筛选回默认(SP+SSP)
}
function resetPageDefaults() {
  if (state.tab === 'calc') {
    Object.assign(state.calc, { lv: 5, pRar: null, vigor: 'default', crit: false, star: true, s3u: true, spU: true, ssp: false,
      passive: true, cpassive: true, skills: true, first: false, fdth: false, mp: true, ca: true, tDef: 10000, tCharDef: 750, pSpU: true });
    resetFiltOf('pickc');
  } else if (state.tab === 'rank') {
    Object.assign(state.rankCfg, { targetDef: 10000, targetCharDef: 750, vigor: 'default', crit: false, passive: true, cpassive: true,
      skills: true, first: false, fdth: false, ca: true, mp: true, star: 3, range: 'all', wat: null, atk: null, urole: null, rarity: null, prar: null, prole: null, terr: '',
      spU: true, s3u: true, sspU: true, pSpU: true });
    resetFiltOf('rank');
    state.rankCache = null;
  } else if (state.tab === 'team') {
    Object.assign(state.team, { skills: false, first: false, fdth: false, cbuff: { tags: [], pct: 0 }, cbOn: false, shipStar: 0, range: 'all', vigor: 'default', ca: true, mp: false, prole: null, terr: '', buffs: [],
      tdef: 10000, tcdef: 750, defup: 0, tAtk: 0, tDef: 0, tHp: 0, atkup: 0, star: 3, spU: true, s3u: true, sspU: true, pSpU: true,
      prar: null, rar: null, wat: null, atk: null, urole: null, guard: false, sdef: false });
    resetFiltOf('team'); resetFiltOf('teamp'); resetFiltOf('tbuff');
  }
}

/* ------------ 排序: 字段表 / 状态 / SQL / 弹窗 ------------ */
const SORTFIELDS = {
  unit: [['id', '图鉴顺序'], ['name', '名称'], ['rarity', '稀有度'], ['max_atk', '攻击力'], ['max_def', '防御力'], ['max_mob', '机动'], ['max_hp', 'HP'], ['max_en', 'EN']],
  char: [['id', '图鉴顺序'], ['name', '名称'], ['rarity', '稀有度'], ['max_ranged', '射击'], ['max_melee', '格斗'], ['max_awaken', '觉醒'], ['max_defense', '防御力'], ['max_reaction', '反应']],
  weapon: [['id', '图鉴顺序'], ['name', '名称'], ['power', '威力'], ['en', 'EN'], ['range_max', '射程'], ['hit_rate', '命中']],
  supp: [['id', '图鉴顺序'], ['name', '名称'], ['rarity', '稀有度']],
  mod: [['id', '图鉴顺序'], ['name', '名称'], ['rarity', '稀有度']],
};
SORTFIELDS.picku = SORTFIELDS.unit;      // 选择器里的机体/驾驶员列表
SORTFIELDS.pickc = SORTFIELDS.char;
function sortOf(ctx) { return (state.sort[ctx] = state.sort[ctx] || { f: 'id', d: 1 }); }
function sortLabel(ctx) {
  const s = sortOf(ctx);
  const it = (SORTFIELDS[ctx] || []).find(x => x[0] === s.f);
  return (it ? it[1] : s.f) + (s.d < 0 ? ' ↓倒序' : ' ↑顺序');
}
function sortOrder(ctx, alias, idOrder, spOn) {   // SQL ORDER BY (alias 可空); spOn=驾驶员SP口径 → 数值字段按 sp_max_* 排
  const s = sortOf(ctx);
  const pre = alias ? alias + '.' : '';
  const ido = idOrder || (pre + 'id');
  if (s.f === 'id') return 'ORDER BY ' + ido.split(',').map(k => k.trim() + (s.d < 0 ? ' DESC' : ' ASC')).join(', ');   // 图鉴顺序也支持倒序(多列逐列反向)
  let col = pre + s.f;
  if (spOn && s.f.startsWith('max_')) col = `CASE WHEN ${pre}rarity<=4 THEN COALESCE(${pre}sp_${s.f}, ${pre}${s.f}) ELSE ${pre}${s.f} END`;
  return `ORDER BY ${col} ${s.d < 0 ? 'DESC' : 'ASC'}, ${ido} ASC`;
}
function jsSort(rows, ctx, getVal) {       // 内存数组排序(id/图鉴顺序=默认序不动)
  const s = sortOf(ctx);
  if (s.f === 'id' && s.d === 1) return rows;
  const dir = s.d < 0 ? -1 : 1;
  return rows.slice().sort((a, b) => {
    const va = getVal(a, s.f), vb = getVal(b, s.f);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    const c = (typeof va === 'string' || typeof vb === 'string') ? String(va).localeCompare(String(vb), 'zh') : va - vb;
    return c * dir || ((a.id || a.target_id || 0) - (b.id || b.target_id || 0));
  });
}
/* ------------ 列表: 回到最顶/最底按钮(sticky, 覆盖所有列表) ------------ */
function attachListFab(scroller) {
  if (!scroller) return;
  let fab = scroller.querySelector(':scope > .listfab');
  if (!fab) {
    fab = document.createElement('div');
    fab.className = 'listfab';
    fab.innerHTML = '<span data-fab="top">⇧</span><span data-fab="bottom">⇩</span>';
    fab.querySelector('[data-fab="top"]').onclick = e => { e.stopPropagation(); scroller.scrollTo({ top: 0, behavior: 'smooth' }); };
    fab.querySelector('[data-fab="bottom"]').onclick = e => { e.stopPropagation(); scroller.scrollTo({ top: scroller.scrollHeight, behavior: 'smooth' }); };
  }
  if (scroller.lastElementChild !== fab) scroller.appendChild(fab);   // 始终置于末尾; 防重入
  const update = () => { fab.style.display = (scroller.scrollHeight > scroller.clientHeight + 24) ? 'flex' : 'none'; };
  update(); setTimeout(update, 350);
}
new MutationObserver(() => {
  const v = document.getElementById('view'); if (v) attachListFab(v);
  const p = document.getElementById('sheetPanel'); if (p) { const tl = p.querySelector('.tlist'); if (tl) attachListFab(tl); }
}).observe(document.body, { childList: true, subtree: true });

let _sheetBack = null;                     // 从弹窗内打开筛选/排序时, 关闭后恢复原弹窗
function openSortPicker(ctx, onChange) {
  const back = _sheetBack; _sheetBack = null;   // 捕获并清空, 避免跨弹窗泄漏
  const s = sortOf(ctx);
  const fields = SORTFIELDS[ctx] || SORTFIELDS.unit;
  const panel = $('sheetPanel');
  const bstOf = () => ctx === 'char' ? (state.cBstList || 0) : (state.uBstList || 0);
  const starOf = () => unitStarSel();
  const draw = () => {
    panel.innerHTML = `
      <div class="sheet-h"><b>排序</b><span class="x" id="sx">✕</span></div>
      <div class="hint">当前：${esc(sortLabel(ctx))} · 数值字段默认从大到小</div>
      <div class="tlist">${fields.map(([f, l]) => `<div class="trow2" data-sf="${f}"><span class="ck ${s.f === f ? 'on' : ''}"></span>${l}</div>`).join('')}</div>
      <div class="seg">
        <span class="sgi ${s.d > 0 ? 'on' : ''}" data-sd="1">顺序 ↑</span>
        <span class="sgi ${s.d < 0 ? 'on' : ''}" data-sd="-1">倒序 ↓</span>
      </div>
      ${ctx === 'unit' ? `
      <div class="hint" style="margin-top:8px">星数（突破倍率；ULT固定值不受星数）</div>
      <div class="seg">
        ${[0, 1, 2, 3].map(b2 => `<span class="sgi ${starOf() === b2 ? 'on' : ''}" data-star="${b2}">★${b2}</span>`).join('')}
      </div>` : ''}
      ${['unit', 'char'].includes(ctx) ? `
      <div class="hint" style="margin-top:8px">数值口径（数值字段排序${ctx === 'char' ? '与列表数值' : ''}按此生效）</div>
      <div class="seg">
        ${[[0, '原值'], [1, '被动'], [2, '主被动'], [3, 'max']].map(([b, l]) => `<span class="sgi ${bstOf() === b ? 'on' : ''}" data-bst="${b}">${l}</span>`).join('')}
      </div>` : ''}
      <div class="sheet-f"><div class="btnrow"><span class="bp" id="sap2">应用</span></div></div>`;
    $('sx').onclick = () => { closeSheet(); if (back) back(); onChange && onChange(); };
    panel.querySelectorAll('[data-sf]').forEach(el => el.onclick = () => {
      s.f = el.dataset.sf;
      s.d = ['id', 'name'].includes(s.f) ? 1 : -1;    // 数值字段默认倒序(大→小)
      draw();
    });
    panel.querySelectorAll('[data-sd]').forEach(el => el.onclick = () => { s.d = +el.dataset.sd; draw(); });
    panel.querySelectorAll('[data-bst]').forEach(el => el.onclick = () => {
      if (ctx === 'char') state.cBstList = +el.dataset.bst; else state.uBstList = +el.dataset.bst;
      draw();
    });
    panel.querySelectorAll('[data-star]').forEach(el => el.onclick = () => { state.uStarList = +el.dataset.star; draw(); });
    $('sap2').onclick = () => { closeSheet(); if (back) back(); onChange && onChange(); };
  };
  draw();
  $('sheet').classList.add('open');
}
const nowStack = () => state.stack[state.stack.length - 1] || null;

/* ------------ 工具: 标签筛选 SQL ------------ */
function tagClause(cat, f, idCol, joinTbl, joinCol) {
  if (!f.tags.length) return { sql: '', args: [] };
  const ph = f.tags.map(() => '?').join(',');
  if (cat === 'weapon') {
    const inner = `SELECT 1 FROM unit_tags t JOIN weapons w2 ON w2.unit_id=t.unit_id WHERE w2.id=${idCol} AND t.tag_id IN (${ph})`;
    return f.mode === 'and'
      ? { sql: `(SELECT COUNT(DISTINCT t.tag_id) FROM unit_tags t JOIN weapons w2 ON w2.unit_id=t.unit_id WHERE w2.id=${idCol} AND t.tag_id IN (${ph}))=?`, args: [...f.tags, f.tags.length] }
      : { sql: `EXISTS(${inner})`, args: f.tags };
  }
  const inner = `SELECT 1 FROM ${joinTbl} t WHERE t.${joinCol}=${idCol} AND t.tag_id IN (${ph})`;
  return f.mode === 'and'
    ? { sql: `(SELECT COUNT(*) FROM ${joinTbl} t WHERE t.${joinCol}=${idCol} AND t.tag_id IN (${ph}))=?`, args: [...f.tags, f.tags.length] }
    : { sql: `EXISTS(${inner})`, args: f.tags };
}
function unitWhere(cat, f) {
  const w = [], a = [];
  const tc = tagClause(cat, f, 'u.id', 'unit_tags', 'unit_id');
  const serSql = (f.series && f.series.length) ? `u.series_id IN (${f.series.map(() => '?').join(',')})` : '';
  if (tc.sql && serSql && f.mode === 'or') {             // 并行模式: 标签任一 或 系列命中
    const ph = f.tags.map(() => '?').join(',');
    w.push(`(EXISTS(SELECT 1 FROM unit_tags t WHERE t.unit_id=u.id AND t.tag_id IN (${ph})) OR ${serSql})`);
    a.push(...f.tags, ...f.series);
  } else {
    if (tc.sql) { w.push(tc.sql); a.push(...tc.args); }
    if (serSql) { w.push(serSql); a.push(...f.series); }   // 串行: 标签与系列都要满足
  }
  if (f.search) { const nl = nameLikeSql('u.name', f.search); w.push(nl.sql); a.push(...nl.args); }
  if (cat === 'unitrole') { w.push('u.role=?'); a.push(f.role); }
  if (cat === 'unit' && f.rar) {
    if (f.rar === 'ult') w.push('u.ult=1');   // 终极机体(ULT)筛选: 全部稀有度的ULT机体
    else { w.push('u.rarity=?'); a.push(f.rar); }
  }
  if (cat === 'unit' && f.role) { w.push('u.role=?'); a.push(f.role); }
  const vc = verCond(cat === 'unitrole' ? 'unit' : cat, f);
  if (vc) w.push(vc);
  return { where: w.length ? 'WHERE ' + w.join(' AND ') : '', args: a };
}

/* ------------ 标签选择弹窗 ------------ */
/* 驾驶员标签/系列筛选(计算页 pickc / 组队 teamp 共用): 与选择器列表 pickWhere 同口径 — mode=or 时「标签或系列」任一命中 */
function pilotFilterOf(flt) {
  const tn = tagNameDict();
  const tags = (flt.tags || []).map(id => tn[id]).filter(Boolean);
  const sers = (flt.series || []).map(x => String(x));
  const tagM = p => {
    if (!tags.length) return true;
    const ts = charMetaOf(p.id).tags;
    return (flt.mode === 'or') ? tags.some(n => ts.has(n)) : tags.every(n => ts.has(n));
  };
  const serM = p => !sers.length || sers.includes(String(charSeriesMap()[String(p.series_set_id)]));
  return p => {
    if (flt.rar && p.rarity !== flt.rar) return false;
    if (flt.role && p.role !== flt.role) return false;
    if (tags.length && sers.length && flt.mode === 'or') return tagM(p) || serM(p);
    return tagM(p) && serM(p);
  };
}
async function openTagPicker(cat, onChange) {
  const back = _sheetBack; _sheetBack = null;
  const f = filt(cat);
  const buildCounts = () => {
    const vc = verCond(cat, f);
    let sql;
    if (cat === 'weapon') sql = `SELECT ut.tag_id, COUNT(DISTINCT w.id) c FROM weapons w JOIN unit_tags ut ON ut.unit_id=w.unit_id ${vc ? 'WHERE ' + vc : ''} GROUP BY ut.tag_id`;
    else if (cat === 'char' || cat === 'pickc' || cat === 'teamp') sql = 'SELECT tag_id, COUNT(*) c FROM char_tags GROUP BY tag_id';
    else if (cat === 'mod') sql = 'SELECT tag_id, COUNT(*) c FROM mod_tags GROUP BY tag_id';
    else if (cat === 'supp') sql = 'SELECT name AS tag_id, COUNT(*) c FROM supporter_tags GROUP BY name';
    else if (cat === 'feat') sql = 'SELECT tag_id, COUNT(*) c FROM (SELECT tag_id FROM unit_tags UNION ALL SELECT tag_id FROM char_tags) GROUP BY tag_id';   // 特性页含机体/驾驶员行: 标签并集(此前仅机体标签, 驾驶员专用标签无法筛选)
    else sql = `SELECT tag_id, COUNT(*) c FROM unit_tags WHERE unit_id IN (SELECT u.id FROM units u ${vc ? 'WHERE ' + vc : ''}) GROUP BY tag_id`;
    const counts = {}; q(sql).forEach(r => counts[r.tag_id] = r.c);
    return counts;
  };
  let counts = buildCounts();
  const tags = cat === 'supp'
    ? Object.keys(counts).sort((a, b) => counts[b] - counts[a]).map(n => ({ id: n, name: n }))
    : q('SELECT id,name FROM tags ORDER BY id').filter(t => counts[t.id]);
  let sel = [...f.tags], mode = f.mode, search = '';
  const hasSeries = ['unit', 'rank', 'team', 'char', 'weapon', 'mod', 'picku', 'pickc', 'teamp', 'feat', 'tbuff'].includes(cat);   // 系列筛选: 战舰无系列数据; tbuff=组队自定义增强
  let listMode = 'tag', selSeries = [...(f.series || [])].map(Number);
  const buildSeries = () => {
    const vc = verCond(cat === 'unit' || cat === 'picku' ? 'unit' : cat, f);
    if (cat === 'mod') return q(`SELECT m.series_id sid, s.name, COUNT(*) n FROM mods m JOIN series s ON s.id=m.series_id GROUP BY m.series_id ORDER BY n DESC`);
    if (cat === 'char' || cat === 'pickc' || cat === 'teamp') return q(`SELECT m.sid sid, s.name, COUNT(*) n FROM characters c JOIN (SELECT DISTINCT series_set_id ss, series_id sid FROM units) m ON m.ss=c.series_set_id JOIN series s ON s.id=m.sid GROUP BY m.sid ORDER BY n DESC`);
    if (cat === 'weapon') return q(`SELECT u.series_id sid, s.name, COUNT(DISTINCT w.id) n FROM weapons w JOIN units u ON u.id=w.unit_id JOIN series s ON s.id=u.series_id ${vc ? 'WHERE ' + vc : ''} GROUP BY u.series_id ORDER BY n DESC`);
    return q(`SELECT u.series_id sid, s.name, COUNT(*) n FROM units u JOIN series s ON s.id=u.series_id ${vc ? 'WHERE ' + vc : ''} GROUP BY u.series_id ORDER BY n DESC`);
  };
  let series = hasSeries ? buildSeries() : [];
  /* 稀有度/类型筛选(机体&驾驶员语境): rank→rankCfg, team→team, 其余→filt 字段; 应用时写入(与页面行共享状态) */
  const _unitLike = ['unit', 'rank', 'team', 'picku'].includes(cat);
  const _showRR = ['unit', 'char', 'rank', 'team', 'picku', 'pickc', 'teamp', 'feat'].includes(cat);
  const rarGet = () => cat === 'rank' ? state.rankCfg.rarity : (cat === 'team' ? state.team.rar : (cat === 'teamp' ? state.team.prar : f.rar));
  const rarSet = v => { if (cat === 'rank') state.rankCfg.rarity = v; else if (cat === 'team') state.team.rar = v; else if (cat === 'teamp') state.team.prar = v; else f.rar = v; };
  const roleGet = () => cat === 'rank' ? state.rankCfg.urole : (cat === 'team' ? state.team.urole : (cat === 'teamp' ? state.team.prole : f.role));
  const roleSet = v => { if (cat === 'rank') state.rankCfg.urole = v; else if (cat === 'team') state.team.urole = v; else if (cat === 'teamp') state.team.prole = v; else f.role = v; };
  let selRar = rarGet() || null, selRole = roleGet() || null;
  const ROLE_OPTS = [['all', '全部'], [1, '攻击型'], [2, _unitLike ? '耐久型' : '防御型'], [3, '支援型']];
  const panel = $('sheetPanel');
  let keepScroll = false;                     // 选中/取消等原地更新时保持列表滚动位置
  const draw = () => {
    const stPrev = keepScroll && $('stlist') ? $('stlist').scrollTop : 0;
    const list = tags.filter(t => ciHas(t.name, search));
    const slist = series.filter(s => ciHas(s.name, search));
    const catName = ({ unit: '机体', rank: '机体', team: '机体', char: '驾驶员', weapon: '武器', mod: '零件', supp: '战舰', picku: '机体', pickc: '驾驶员', teamp: '驾驶员', feat: '机体/驾驶员', tbuff: '机体' })[cat];
    panel.innerHTML = `
      <div class="sheet-h"><b>选择${hasSeries ? '标签 / 作品系列' : '标签'}</b><span class="x" id="sx">✕</span></div>
      <div class="hint">${listMode === 'series' ? `共 ${series.length} 个系列 · 计数=机体数` : `共 ${tags.length} 个标签 · 计数=当前分类命中数（${catName}）`}</div>
      <div class="search">🔍 <input id="ssearch" placeholder="${listMode === 'series' ? '搜索系列' : '搜索标签'}" value="${esc(search)}"></div>
      ${hasSeries ? `<div class="seg">
        <span class="sgi ${listMode === 'tag' ? 'on' : ''}" data-lm="tag">标签</span>
        <span class="sgi ${listMode === 'series' ? 'on' : ''}" data-lm="series">作品系列</span>
      </div>` : ''}
      ${['unit', 'weapon', 'rank', 'team'].includes(cat) ? `
      <div class="chips" style="align-items:center">
        <span class="hint" style="margin-right:2px">版本:</span>
        <span class="chip ${f.sp ? 'on' : ''}" data-v="sp">${cat === 'unit' ? '筛 · SP可强化' : 'SP · 常规武器'}</span>
        <span class="chip ${f.ssp ? 'on' : ''}" data-v="ssp">${cat === 'unit' ? '筛 · 有SSP武器' : 'SSP · 强化武器'}</span>
      </div>` : ''}
      ${cat === 'feat' ? `
      <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">出击场地:</span>
        ${[['', '无限制'], ['space', '宇宙'], ['atm', '空中'], ['ground', '地上'], ['surface', '水面'], ['water', '水中']].map(([kk, ll]) =>
          `<span class="chip ${(f.terr || '') === kk ? (kk === '' ? 'on' : 'gold') : ''}" data-fterr="${kk}">${ll}</span>`).join('')}
        <span class="hint" style="align-self:center;margin-left:2px">×不能出击的机体不入列</span>
      </div>` : ''}
      ${_showRR ? `
      <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">稀有度:</span>
        ${[['all', '全部'], [1, 'N'], [2, 'R'], [3, 'SR'], [4, 'SSR'], [5, 'UR']].map(([k, l]) =>
          `<span class="chip ${(selRar ?? 'all') === k ? (k === 'all' ? 'on' : 'gold') : ''}" data-srar="${k}">${l}</span>`).join('')}
      </div>
      <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">类型:</span>
        ${ROLE_OPTS.map(([k, l]) =>
          `<span class="chip ${(selRole ?? 'all') === k ? (k === 'all' ? 'on' : 'gold') : ''}" data-srole="${k}">${l}</span>`).join('')}
      </div>` : ''}
      ${listMode === 'tag' ? `<div class="seg">
        <span class="sgi ${mode === 'or' ? 'on' : ''}" data-m="or">任一命中</span>
        <span class="sgi ${mode === 'and' ? 'on' : ''}" data-m="and">全部命中</span>
      </div>` : ''}
      <div class="tlist" id="stlist">${listMode === 'series'
        ? slist.map(s => `<div class="trow2" data-sid="${esc(s.sid)}"><span class="ck ${selSeries.includes(+s.sid) ? 'on' : ''}"></span>${esc(s.name)}<span class="c">${fmt(s.n)}</span></div>`).join('')
        : list.map(t => `<div class="trow2" data-id="${t.id}"><span class="ck ${sel.includes(t.id) ? 'on' : ''}"></span>${esc(t.name)}<span class="c">${fmt(counts[t.id])}</span></div>`).join('')}
      </div>
      <div class="sheet-f">
        <div class="chips">${sel.map(id => { const t = tags.find(x => x.id === id); return t ? `<span class="tchip2" data-del="${id}">${esc(t.name)} <i>×</i></span>` : ''; }).join('')}
          ${selSeries.map(sid => { const s = series.find(x => +x.sid === sid); return s ? `<span class="tchip2" data-dels="${esc(sid)}">《${esc(s.name)}》 <i>×</i></span>` : ''; }).join('')}</div>
        <div class="btnrow"><span class="bs" id="sclear">清除</span><span class="bp" id="sapply">应用 · ${sel.length} 标签${selSeries.length ? ' + ' + selSeries.length + ' 系列' : ''}${listMode === 'tag' ? '（' + (mode === 'and' ? '全部命中' : '任一命中') + '）' : ''}</span></div>
      </div>`;
    $('sx').onclick = () => { closeSheet(); if (back) back(); };
    $('ssearch').oninput = e => { search = e.target.value; const pos = e.target.selectionStart; draw(); $('ssearch').focus(); $('ssearch').setSelectionRange(pos, pos); };
    panel.querySelectorAll('[data-lm]').forEach(el => el.onclick = () => { listMode = el.dataset.lm; draw(); });
    panel.querySelectorAll('[data-m]').forEach(el => el.onclick = () => { mode = el.dataset.m; draw(); });
    panel.querySelectorAll('[data-srar]').forEach(el => el.onclick = () => { selRar = el.dataset.srar === 'all' ? null : +el.dataset.srar; draw(); });
    panel.querySelectorAll('[data-srole]').forEach(el => el.onclick = () => { selRole = el.dataset.srole === 'all' ? null : +el.dataset.srole; draw(); });
    panel.querySelectorAll('[data-v]').forEach(el => el.onclick = () => {
      const v = el.dataset.v;
      f[v] = f[v] ? 0 : 1;
      if (['weapon', 'rank', 'team'].includes(cat) && !f.sp && !f.ssp) f[v] = 1; // 武器口径至少保留一个版本
      counts = buildCounts(); if (hasSeries) series = buildSeries(); draw();
    });
    panel.querySelectorAll('[data-fterr]').forEach(el => el.onclick = () => { f.terr = el.dataset.fterr; draw(); });   // feat: 出击场地筛选
    panel.querySelectorAll('[data-id]').forEach(el => el.onclick = () => {
      const id = cat === 'supp' ? el.dataset.id : +el.dataset.id;
      sel = sel.includes(id) ? sel.filter(x => x !== id) : [...sel, id]; keepScroll = true; draw();
    });
    panel.querySelectorAll('[data-sid]').forEach(el => el.onclick = () => {
      const sid = +el.dataset.sid;                 // 存为数值: 表达式列(如 char 系列换算)无类型亲和, 字符串参数匹配不上
      selSeries = selSeries.includes(sid) ? selSeries.filter(x => x !== sid) : [...selSeries, sid]; keepScroll = true; draw();
    });
    panel.querySelectorAll('[data-del]').forEach(el => el.onclick = () => {
      const id = cat === 'supp' ? el.dataset.del : +el.dataset.del;
      sel = sel.filter(x => x !== id); keepScroll = true; draw();
    });
    panel.querySelectorAll('[data-dels]').forEach(el => el.onclick = () => {
      selSeries = selSeries.filter(x => x !== +el.dataset.dels); keepScroll = true; draw();
    });
    $('sclear').onclick = () => { sel = []; selSeries = []; selRar = null; selRole = null; draw(); };
    $('sapply').onclick = () => { f.tags = sel; f.mode = mode; f.series = selSeries; rarSet(selRar); roleSet(selRole); closeSheet(); if (back) back(); onChange && onChange(); };
    if (keepScroll) { const st2 = $('stlist'); if (st2) st2.scrollTop = stPrev; keepScroll = false; }
  };
  draw();
  $('sheet').classList.add('open');
}
let _ultDirty = false;
function closeSheet() { $('sheet').classList.remove('open'); if (_ultDirty) { _ultDirty = false; render(); } }
/* ULT改造设置弹层: 0/50/100 三挡 + 100级时每组三选一能力 */
function openUltSheet() {
  _ultDirty = false;
  let lev = +state.ultLv || 0;
  const SK = Object.assign({}, state.ultSkill);
  ultSkillsOf(0);
  const groupList = Object.keys(_ultSkills || {}).map(Number).sort((a, b) => a - b);
  const panel = $('sheetPanel');
  const sname = s => String(s.name || '').replace(/^单位技能【/, '').replace(/】$/, '');
  function renderSheet() {
    const lvChips = [[0, '关闭'], [50, 'Lv50 · ULT武器'], [100, 'Lv100 · 武器+能力']]
      .map(([v, t]) => `<span class="chip ${lev === v ? 'gold' : ''}" data-ultlev="${v}">${t}</span>`).join('');
    const gHtml = groupList.map(g => {
      const list = ultSkillsOf(g), cur = String(SK[g] ?? (list[0] && list[0].skill_id));
      return `<div style="margin:8px 0 2px"><div style="font-size:11.5px;color:#9fb4d8;font-weight:700">${esc(ultGroupName(g))}</div>
        <div class="chips tight">${list.map(s => `<span class="chip ${cur === String(s.skill_id) ? 'gold' : ''}" data-ultsk="${g}:${s.skill_id}" ${lev === 100 ? '' : 'style="opacity:.5"'}>${esc(sname(s))}</span>`).join('')}</div></div>`;
    }).join('');
    panel.innerHTML = `<div class="sheet-h"><b>ULT改造</b><span class="x" id="sx">✕</span></div>
      <div class="hint">三段(SSR/UR/UR)共用同一套改造。Lv50：各项+max的5% + 解锁ULT武器；Lv100：各项+max的10% + 武器 + 能力三选一。</div>
      <div class="tlist"><div class="chips tight" style="margin:4px 0 6px">${lvChips}</div>
        ${lev ? `<div class="hint">当前加成：HP/EN/攻击/防御/机动 各 +max×${lev === 100 ? 10 : 5}%（向下取整）</div>` : '<div class="hint">未开启 ULT改造</div>'}
        <div class="hint" style="margin:8px 0 0">改造能力（总Lv=100生效；每组三选一，默认第1项）</div>
        ${gHtml}</div>
      <div class="sheet-f"><div class="btnrow"><span class="bs" id="uultreset">重置</span><span class="bp" id="uultapply">完成 · ${lev ? 'Lv' + lev : '关闭'}</span></div></div>`;
    $('sx').onclick = closeSheet;
    panel.querySelectorAll('[data-ultlev]').forEach(el => el.onclick = () => { lev = +el.dataset.ultlev; state.ultLv = lev; _ultDirty = true; renderSheet(); });
    panel.querySelectorAll('[data-ultsk]').forEach(el => el.onclick = () => {
      const i = el.dataset.ultsk.indexOf(':'), g = el.dataset.ultsk.slice(0, i), sid = el.dataset.ultsk.slice(i + 1);
      SK[g] = sid; state.ultSkill[g] = sid; _ultDirty = true; renderSheet();
    });
    $('uultreset').onclick = () => { lev = 0; state.ultLv = 0; state.ultSkill = {}; for (const k in SK) delete SK[k]; _ultDirty = true; renderSheet(); };
    $('uultapply').onclick = () => { state.ultLv = lev; state.ultSkill = Object.assign({}, SK); _ultDirty = false; closeSheet(); render(); };
  }
  renderSheet();
  $('sheet').classList.add('open');
}

/* ------------ 增量补丁: 启动时把已下载的补丁 SQL 叠加到基础库(幂等; 仅应用比基础库新的) ------------ */
function applyPatches() {
  if (typeof window.Android === 'undefined' || !window.Android.listPatches) return { applied: 0 };
  let names = [];
  try { names = JSON.parse(window.Android.listPatches() || '[]'); } catch (e) { return { applied: 0 }; }
  let baseAt = 0;
  try { baseAt = +(q1("SELECT value FROM meta WHERE key='built_at'") || {}).value || 0; } catch (e) {}
  let applied = 0;
  for (const n of names.sort()) {
    const m = /^p_(\d+)\.sql$/.exec(n);
    if (!m) continue;
    const at = +m[1];
    if (at <= baseAt) { try { window.Android.deletePatch(n); } catch (e) {} continue; }   // 基础库已含(新APK) → 清理旧补丁
    try {
      const sql = window.Android.readPatch(n);
      if (sql && sql.length > 10) { runSqlBatched(sql); applied++; }
    } catch (e) { console.warn('补丁应用失败(跳过): ' + n, e); }
  }
  return { applied };
}
/* 补丁重放: 小文件直接跑; 大补丁按语句切开分块 run —— 单次 db.run(数MB字串) 在真机 sql.js 上会触发
   "memory access out of bounds"(WASM trap), 且 trap 后整个连接报废 */
function runSqlBatched(sql) {
  if (sql.length <= 262144) { db.run(sql); return; }
  const parts = []; let cur = '', inS = false;      // 引号感知分句(值里可含 ; 与换行)
  for (let i = 0; i < sql.length; i++) {
    const ch = sql[i]; cur += ch;
    if (ch === "'") { if (inS && sql[i + 1] === "'") { cur += sql[++i]; } else inS = !inS; }
    else if (ch === ';' && !inS) { parts.push(cur); cur = ''; }
  }
  if (cur.trim()) parts.push(cur);
  let batch = '';
  for (const part of parts) {
    batch += part;
    if (batch.length > 262144) { db.run(batch); batch = ''; }
  }
  if (batch.trim()) db.run(batch);
}
document.querySelector('#sheet .backdrop').onclick = closeSheet;

/* ------------ 页面框架 ------------ */
const TABS = [
  { id: 'units', label: '图鉴', ic: 'grid' }, { id: 'calc', label: '计算', ic: 'tx', tx: '∑' },
  { id: 'rank', label: '排行', ic: 'bars' }, { id: 'team', label: '组队', ic: 'cir' },
  { id: 'feat', label: '特性', ic: 'tx', tx: '★' },
];
function icHTML(t) {
  if (t.ic === 'grid') return '<span class="gl ic-grid"><i></i><i></i><i></i><i></i></span>';
  if (t.ic === 'bars') return '<span class="gl ic-bars"><i style="height:7px"></i><i style="height:12px"></i><i style="height:16px"></i></span>';
  if (t.ic === 'cir') return '<span class="gl ic-cir"><i></i><i></i></span>';
  return `<span class="gl ic-tx">${t.tx}</span>`;
}
function setTab(id) { state.tab = id; state.stack = []; state.tabScroll && (state.tabScroll[id] = 0); render(); }
function push(page) {
  const cur = nowStack();
  if (cur) cur._sc = $('view').scrollTop;
  else { state.tabScroll = state.tabScroll || {}; state.tabScroll[state.tab] = $('view').scrollTop; }   // 从主标签页进入子页
  state.stack.push(page); render();
}
function pop() {
  state.stack.pop(); render();
  const cur = nowStack();
  const sc = cur ? (cur._sc || 0) : ((state.tabScroll || {})[state.tab] || 0);
  if (sc) requestAnimationFrame(() => { $('view').scrollTop = sc; setTimeout(() => { $('view').scrollTop = sc; }, 60); });
}

function render() {
  const sub = nowStack();
  const nav = $('nav');
  nav.innerHTML = TABS.map(t => `<div class="it ${!sub && state.tab === t.id ? 'on' : ''}" data-tab="${t.id}">${icHTML(t)}${t.label}</div>`).join('');
  nav.querySelectorAll('[data-tab]').forEach(el => el.onclick = () => setTab(el.dataset.tab));
  const bar = $('appbar');
  if (sub) {
    bar.innerHTML = `<span class="ic" id="back">‹ 返回</span><span class="t">${esc(sub.title)}<small>${esc(sub.sub || '')}</small></span><span class="ic" id="gear">⚙</span>`;
    $('back').onclick = pop;
  } else {
    const t = TABS.find(x => x.id === state.tab);
    const rst = ['calc', 'rank', 'team'].includes(state.tab) ? '<span class="rstbtn" id="rstdef">↺ 重置默认</span>' : '';   // 标题栏中间: 重置本页选项开关默认
    bar.innerHTML = `<span class="t">${t.label}<small>${state.tab === 'units' ? '数据 · 图鉴' : ''}</small></span>${rst}<span class="ic" id="gear">⚙</span>`;
    if (rst) $('rstdef').onclick = () => { resetPageDefaults(); render(); };
  }
  $('gear').onclick = () => push({ page: 'update', title: '更新中心' });
  const v = $('view'); v.scrollTop = 0;
  try {
    if (sub) PAGES[sub.page](v, sub); else PAGES[state.tab](v, null);
  } catch (e) { v.innerHTML = `<div class="err">页面错误: ${esc(e.message)}</div>`; console.error(e); }
}

/* ------------ 图鉴页 ------------ */
const KIND_TABS = [['unit', '机体'], ['char', '驾驶员'], ['weapon', '武器'], ['supp', '战舰'], ['mod', '零件']];
state.unitKind = 'unit';
const PAGE_SIZE = 60;
state.pageLimit = PAGE_SIZE;

function pageUnits(v) {
  const kind = state.unitKind;
  v.innerHTML = `
    <div class="chips" id="kinds">${KIND_TABS.map(([k, n]) => `<span class="chip ${kind === k ? 'on' : ''}" data-k="${k}">${n}</span>`).join('')}</div>
    <div class="search">🔍 <input id="sbox" placeholder="搜索${ (KIND_TABS.find(x => x[0] === kind) || [])[1] }名称…" value="${esc(filt(kind).search || '')}"></div>
    <div class="chips tight" id="rarf"><span class="hint" style="align-self:center;margin-right:2px">稀有度:</span>
      ${[['all', '全部'], [1, 'N'], [2, 'R'], [3, 'SR'], [4, 'SSR'], [5, 'UR']].concat(kind === 'unit' ? [['ult', 'ULT']] : []).map(([k, l]) =>
        `<span class="chip ${((filt(kind).rar || 'all') === k) ? 'on' : ''}" data-krar="${k}">${l}</span>`).join('')}
      ${kind === 'unit' ? `<span class="chip ${state.uSk !== false ? 'gold' : ''}" id="kusk" title="机体技能(单位技能)是否计入图鉴数值档位(主被动/max)">机体技能${state.uSk !== false ? ' 开' : ' 关'}</span><span class="chip ${state.ultLv ? 'gold' : ''}" id="kurd" title="ULT改造: 0/50/100级; ≥50解锁ULT武器, 100解锁三选一能力">ULT改造${state.ultLv ? ' Lv' + state.ultLv : ' 关'}</span>` : ''}
    </div>
    <div class="fbar" id="fbar"></div>
    <div id="listarea"></div>`;
  $('rarf').querySelectorAll('[data-krar]').forEach(el => el.onclick = () => {
    const kv = el.dataset.krar; filt(kind).rar = kv === 'all' ? null : (kv === 'ult' ? 'ult' : +kv);
    state.pageLimit = PAGE_SIZE; render();
  });
  if ($('kusk')) $('kusk').onclick = () => { state.uSk = !(state.uSk !== false); state.pageLimit = PAGE_SIZE; render(); };
  if ($('kurd')) $('kurd').onclick = () => openUltSheet();
  $('kinds').querySelectorAll('[data-k]').forEach(el => el.onclick = () => { state.unitKind = el.dataset.k; state.pageLimit = PAGE_SIZE; render(); });
  if (['unit', 'char', 'weapon', 'mod', 'supp'].includes(kind)) {
    const f = filt(kind);
    $('sbox').oninput = e => { f.search = e.target.value; state.pageLimit = PAGE_SIZE; drawList(); };
    drawFbar();
  } else { $('sbox').oninput = () => {}; $('fbar').innerHTML = ''; }
  drawList();

  function drawFbar() {
    const f = filt(kind);
    const vtxt = kind === 'unit' ? ((f.sp || f.ssp) ? `${f.sp ? 'SP可强化 ' : ''}${f.ssp ? '有SSP ' : ''}` : '') : (['weapon', 'rank', 'team'].includes(kind) ? `SP${f.sp ? '✓' : '✗'} SSP${f.ssp ? '✓' : '✗'}` : '');
    $('fbar').innerHTML = `
      <span class="fbtn" id="tbtn">☰ 标签${['unit', 'char', 'weapon', 'mod'].includes(kind) ? '/系列' : ''} <b>${(f.tags.length + ((f.series || []).length)) || ''}</b></span>
      ${f.tags.length ? `<span class="modewrap">${f.mode === 'and' ? '全部命中' : '任一命中'}</span>` : ''}
      <span class="fbtn" id="sbtn">↕ ${sortLabel(kind)}</span>
      ${kind === 'char' ? `<span class="fbtn" id="cspu" ${state.charSp ? 'style="color:#f5c451;border-color:#f5c451"' : ''}>驾驶员SP ${state.charSp ? '开' : '关'}</span>` : ''}
      ${vtxt ? `<span class="hint" style="font-size:10px">${vtxt}</span>` : ''}
      <span style="flex:1"></span><span style="font-size:11px;color:var(--dim)" id="hit"></span>`;
    $('tbtn').onclick = () => openTagPicker(kind, () => { state.pageLimit = PAGE_SIZE; render(); });   // 整页重绘: 稀有度行(#rarf)与列表同步
    $('sbtn').onclick = () => openSortPicker(kind, () => { state.pageLimit = PAGE_SIZE; drawFbar(); drawList(); });
    if ($('cspu')) $('cspu').onclick = () => { state.charSp = !state.charSp; state.pageLimit = PAGE_SIZE; drawFbar(); drawList(); };
  }

  function drawList() {
    const area = $('listarea');
    if (kind === 'unit') {
      const f = filt('unit');
      const cw = { search: f.search };
      const u = unitWhere('unit', f);
      const total = q1(`SELECT COUNT(*) c FROM units u ${u.where}`, u.args).c;
      if ($('hit')) $('hit').textContent = `命中 ${fmt(total)} 台`;
      const _uf = sortOf('unit').f;
      const _ufv = ['max_atk', 'max_def', 'max_mob', 'max_hp', 'max_en'].includes(_uf);
      const _ufk = _ufv ? _uf.slice(4) : null;
      const _ufl = _ufv ? (((SORTFIELDS.unit || []).find(x => x[0] === _uf) || [])[1] || '') : '';
      let rows;
      if (_ufv) {   // 数值排序=星数(突破)×数值口径(排序弹窗设置)
        rows = jsSort(q(`SELECT u.* FROM units u ${u.where}`, u.args), 'unit', r => unitListStat(r, _ufk, state.uBstList || 0, unitStarSel()));
      } else {
        rows = q(`SELECT u.* FROM units u ${u.where} ${sortOrder('unit', 'u')} LIMIT ? OFFSET 0`, [...u.args, state.pageLimit]);
      }
      rows = rows.slice(0, state.pageLimit);
      area.innerHTML = `<div class="ugrid">${rows.map(u => `
        <div class="ucard" data-id="${u.id}"><span class="role ${ROLE[u.role].cls}">${ROLE[u.role].t}</span>
        ${imgTag(u.icon)}<div class="nm">${esc(u.name)}</div><div class="stars">${rarTag(u.rarity)}${ultB(u)}</div>${_ufv ? `<div class="uval">${_ufl} ${unitListStat(u, _ufk, state.uBstList || 0, unitStarSel())}</div>` : ''}</div>`).join('')}
        </div>${state.pageLimit < total ? '<div class="btnrow"><span class="bp" id="more">加载更多（' + fmt(total - state.pageLimit) + '）</span></div>' : ''}`;
      area.querySelectorAll('.ucard').forEach(el => el.onclick = () => push({ page: 'unit', title: el.querySelector('.nm').textContent.trim(), id: +el.dataset.id }));
    } else if (kind === 'char') {
      const f = filt('char');
      const tc = tagClause('char', f, 'c.id', 'char_tags', 'char_id');
      const nl = f.search ? nameLikeSql('c.name', f.search) : null;
      const scSql = (f.series || []).length ? `c.series_set_id IN (SELECT series_set_id FROM units WHERE series_id IN (${f.series.map(() => '?').join(',')}))` : '';
      const sc = (scSql && tc.sql && f.mode === 'or') ? { sql: `(${tc.sql.replace(/=\?$/, '')}) OR ${scSql}`, args: [...tc.args, ...f.series] } : null;
      if (sc) tc.sql = '';
      const sc2 = (!sc && scSql) ? { sql: scSql, args: [...f.series] } : null;
      const rc = f.rar ? { sql: 'c.rarity=?', args: [f.rar] } : null;
      const rolc = f.role ? { sql: 'c.role=?', args: [f.role] } : null;
      const where = [tc.sql, sc ? sc.sql : (sc2 ? sc2.sql : ''), rc ? rc.sql : '', rolc ? rolc.sql : '', nl ? nl.sql : ''].filter(Boolean).join(' AND ');
      const args = [...(sc ? [] : tc.args), ...(sc ? sc.args : (sc2 ? sc2.args : [])), ...(rc ? rc.args : []), ...(rolc ? rolc.args : []), ...(nl ? nl.args : [])];
      const total = q1(`SELECT COUNT(*) c FROM characters c ${where ? 'WHERE ' + where : ''}`, args).c;
      if ($('hit')) $('hit').textContent = `命中 ${fmt(total)} 人`;
      const _sk = { max_ranged: 'ranged', max_melee: 'melee', max_awaken: 'awaken', max_defense: 'defense', max_reaction: 'reaction' }[sortOf('char').f];
      let rows = q(`SELECT c.* FROM characters c ${where ? 'WHERE ' + where : ''}`, args);
      if (_sk) rows = jsSort(rows, 'char', r => charListStat(r, _sk, state.cBstList || 0, state.charSp));   // 数值排序=档位口径(排序弹窗设置)
      else rows = q(`SELECT c.* FROM characters c ${where ? 'WHERE ' + where : ''} ${sortOrder('char', 'c', null, state.charSp)}`, args);
      rows = rows.slice(0, state.pageLimit);
      const _ckl = _sk ? (((SORTFIELDS.char || []).find(x => x[0] === 'max_' + _sk) || [])[1] || '') : '';
      area.innerHTML = rows.map(c => `<div class="lrow" data-id="${c.id}"><span class="avcol">${imgTag(c.icon)}${_sk ? `<span class="avval">${_ckl} ${charListStat(c, _sk, state.cBstList || 0, state.charSp)}</span>` : ''}</span><div class="nm">${rarTag(c.rarity)} ${esc(c.name)}
        <small>射击${charListStat(c, 'ranged', state.cBstList || 0, state.charSp)} 格斗${charListStat(c, 'melee', state.cBstList || 0, state.charSp)} 觉醒${charListStat(c, 'awaken', state.cBstList || 0, state.charSp)} 防御${charListStat(c, 'defense', state.cBstList || 0, state.charSp)} 反应${charListStat(c, 'reaction', state.cBstList || 0, state.charSp)}</small></div></div>`).join('')
        + (state.pageLimit < total ? '<div class="btnrow"><span class="bp" id="more">加载更多</span></div>' : '');
      area.querySelectorAll('.lrow').forEach(el => el.onclick = () => push({ page: 'char', title: el.querySelector('.nm').firstChild.textContent.trim(), id: +el.dataset.id }));
    } else if (kind === 'weapon') {
      const f = filt('weapon');
      const tc = tagClause('weapon', f, 'w.id', '', '');
      const nlw = f.search ? nameLikeSql('w.name', f.search) : null;
      const scw = (f.series || []).length ? `w.unit_id IN (SELECT id FROM units WHERE series_id IN (${f.series.map(() => '?').join(',')}))` : '';
      const rcw = f.rar ? `w.unit_id IN (SELECT id FROM units WHERE rarity=${+f.rar})` : '';
      let tcwSql = tc.sql;
      const orw = (tcwSql && scw && f.mode === 'or') ? `(${tcwSql.replace(/=\?$/, '')}) OR ${scw}` : '';
      const tcwArgs = tc.args, scwArgs = scw ? f.series : [];
      const where = [orw || tcwSql, verCond('weapon', f), orw ? '' : scw, rcw, nlw ? nlw.sql : ''].filter(Boolean).join(' AND ');
      const args = [...tcwArgs, ...(orw ? scwArgs : scwArgs), ...(nlw ? nlw.args : [])];
      const total = q1(`SELECT COUNT(*) c FROM weapons w ${where ? 'WHERE ' + where : ''}`, args).c;
      if ($('hit')) $('hit').textContent = `命中 ${fmt(total)} 把`;
      const rows = q(`SELECT w.*, u.name uname, u.icon uicon, u.rarity urarity FROM weapons w JOIN units u ON u.id=w.unit_id
        ${where ? 'WHERE ' + where : ''} ${sortOrder('weapon', 'w', 'w.unit_id, w.id')} LIMIT ?`, [...args, state.pageLimit]);
      area.innerHTML = rows.map(w => `<div class="lrow" data-id="${w.id}">${avTagR(w.uicon, null, w.urarity)}
        <div class="nm">${esc(w.name)} ${rarTag(w.urarity)} <span class="fx" style="font-size:10px">${TYATTR[w.attack_attr] || ''}</span> <span class="fx" style="font-size:10px">${AATTR[w.weapon_attr] || ''}</span>
        <small>${esc(w.uname)} · 射程${w.range_min}-${w.range_max} · 威力${fmt(Engine.weaponPower(w, 5))} · EN${w.en}</small></div>
        <span class="val" style="font-size:12px">${w.is_ssp ? 'SSP' : (w.type === 2 ? 'EX' : '')}</span></div>`).join('')
        + (state.pageLimit < total ? '<div class="btnrow"><span class="bp" id="more">加载更多</span></div>' : '');
      area.querySelectorAll('.lrow').forEach(el => el.onclick = () => push({ page: 'weapon', title: el.querySelector('.nm').textContent.trim().slice(0, 24), id: +el.dataset.id }));
    } else if (kind === 'supp') {
      const f = filt('supp');
      const w2 = [], a2 = [];
      if (f.tags.length) {
        const ph = f.tags.map(() => '?').join(',');
        if (f.mode === 'and') { w2.push(`(SELECT COUNT(*) FROM supporter_tags t WHERE t.supporter_id=s.id AND t.name IN (${ph}))=?`); a2.push(...f.tags, f.tags.length); }
        else { w2.push(`EXISTS(SELECT 1 FROM supporter_tags t WHERE t.supporter_id=s.id AND t.name IN (${ph}))`); a2.push(...f.tags); }
      }
      if (f.search) { w2.push('s.name LIKE ?'); a2.push('%' + f.search + '%'); }
      if (f.rar) { w2.push('s.rarity=?'); a2.push(f.rar); }
      const where = w2.length ? 'WHERE ' + w2.join(' AND ') : '';
      const total = q1(`SELECT COUNT(*) c FROM supporters s ${where}`, a2).c;
      if ($('hit')) $('hit').textContent = `命中 ${fmt(total)} 艘`;
      const rows = q(`SELECT s.* FROM supporters s ${where} ${sortOrder('supp', 's')} LIMIT ?`, [...a2, state.pageLimit]);
      area.innerHTML = rows.map(s => {
        const sh0 = shipEffOf(s, 0), sh3 = shipEffOf(s, 3);
        const tagTxt = sh3 ? [...new Set([...sh3.tags, ...sh3.series])].slice(0, 4).join('·') : '';
        return `<div class="lrow" data-id="${s.id}">${imgTag(s.icon)}
        <div class="nm">${rarTag(s.rarity)} ${esc(s.name)}<small>HP支援+${fmt(s.hp_support)} · 攻击支援+${fmt(s.atk_support)}${s.support_skill_name ? ' · ' + esc(s.support_skill_name) : ''}</small></div>
        <span style="flex:none;text-align:right;font-size:10px;line-height:1.45;color:var(--dim)">★0 <b style="color:#9fe8c0">${sh0 ? sh0.pct : 0}%</b> · ★3 <b style="color:#9fe8c0">${sh3 ? sh3.pct : 0}%</b>${tagTxt ? `<br><span style="color:#8fc4ff">${esc(tagTxt)}</span>` : ''}</span></div>`;
      }).join('')
        + (state.pageLimit < total ? '<div class="btnrow"><span class="bp" id="more">加载更多</span></div>' : '');
      area.querySelectorAll('.lrow').forEach(el => el.onclick = () => push({ page: 'supp', title: q1('SELECT name FROM supporters WHERE id=?', [+el.dataset.id]).name, id: +el.dataset.id }));
    } else if (kind === 'mod') {
      const f = filt('mod');
      const tc = tagClause('mod', f, 'm.id', 'mod_tags', 'mod_id');
      const nlm = f.search ? nameLikeSql('m.name', f.search) : null;
      const scm = (f.series || []).length ? `m.series_id IN (${f.series.map(() => '?').join(',')})` : '';
      const rcm = f.rar ? `m.rarity=${+f.rar}` : '';
      const orm = (tc.sql && scm && f.mode === 'or') ? `(${tc.sql.replace(/=\?$/, '')}) OR ${scm}` : '';
      const where = [orm || tc.sql, orm ? '' : scm, rcm, nlm ? nlm.sql : ''].filter(Boolean).join(' AND ');
      const args = [...tc.args, ...(scm ? f.series : []), ...(nlm ? nlm.args : [])];
      const total = q1(`SELECT COUNT(*) c FROM mods m ${where ? 'WHERE ' + where : ''}`, args).c;
      if ($('hit')) $('hit').textContent = `命中 ${fmt(total)} 个`;
      const rows = q(`SELECT m.* FROM mods m ${where ? 'WHERE ' + where : ''} ${sortOrder('mod', 'm')} LIMIT ?`, [...args, state.pageLimit]);
      area.innerHTML = rows.map(m => `<div class="lrow" data-id="${m.id}">${imgTag(m.icon, '', modImg(m.icon))}
        <div class="nm">${rarTag(m.rarity)} ${esc(m.name)}<small>${esc((m.desc || '').replace(/\n/g, ' ').slice(0, 46))}</small></div></div>`).join('')
        + (state.pageLimit < total ? '<div class="btnrow"><span class="bp" id="more">加载更多</span></div>' : '');
      area.querySelectorAll('.lrow').forEach(el => el.onclick = () => push({ page: 'mod', title: el.querySelector('.nm').firstChild.textContent.trim(), id: +el.dataset.id }));
    }
    const more = $('more');
    if (more) more.onclick = () => { state.pageLimit += PAGE_SIZE; drawList(); };
  }
}

/* ------------ 详情页 ------------ */
function pageUnit(v, sp) {
  const u0 = q1('SELECT * FROM units WHERE id=?', [sp.id]); if (!u0) { v.innerHTML = '<div class="err">未找到</div>'; return; }
  const u = effUnit(u0);   // ULT改造口径: 阶段0/1 → 改造后(002) 的能力/武器/数值
  const ultOnNote = ultActive(u0);
  sp.title = u.name;
  const tags = q('SELECT t.id, t.name FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE ut.unit_id=?', [u.id]);
  let abilities = [];   // sspOn 计算后取 unitAbilitiesOf (改装核心能力变化)
  let weapons = weaponsForUnit(u, ' ORDER BY type DESC, power DESC');
  const feats = q('SELECT feature,label,params_json FROM features WHERE target_type="unit" AND target_id=?', [u.id]);
  const _ultG = u.ult ? ultGroupOf(u0.id) : null;
  const ultSkList = _ultG ? ultSkillsOf(_ultG) : [];
  const featsView = feats.filter(f => { if (f.feature !== 'unit_skill') return true; let pr = {}; try { pr = JSON.parse(f.params_json || '{}'); } catch (e) {} return !pr.ult; });   // ULT能力单列(三选一), 不混入普通单位技能
  const r = ROLE[u.role];
  /* 数值口径: SSR及以下=三星(×1.4)/SP(强化上限)/SSP满10 三个独立开关; UR=突破星数选择 */
  state.unit = state.unit || { star: 0, star3: true, sp: false, ssp: false, bst: 0 };
  const uv = state.unit;
  if (uv.star3 === undefined) uv.star3 = true;      // 默认按★3(即游戏原始面板)
  if (uv.bst === undefined) uv.bst = 0;             // 数值提升档位: 0=原值 1=被动 2=主动 3=max(含条件)
  const ssrBelow = u.rarity <= 4 && !u.ult;
  const spOn = ssrBelow ? uv.sp : true;                    // SP: 强化上限(Lv上限→100的数值 sp_max)
  const s3On = ssrBelow ? uv.star3 : false;                // 三星: ★3(=★0×1.4)
  let _ss = {}; try { _ss = (JSON.parse(u.ssp_json || '{}').stats) || {}; } catch (e) {}
  const hasSsp = ssrBelow && !!(_ss.ssp_max_hp || _ss.ssp_max_attack);
  const sspOn = hasSsp && uv.ssp && s3On && spOn;          // SSP 必须 三星+SP 同时开
  const sspG = sspOn ? sspGainOf(u, 10) : { atk: 0, hp: 0, en: 0, def: 0, mob: 0 };
  const sspM = sspOn ? sspMovOf(u) : 0;   // SSP移动力加成(仅部分机体)
  if (sspOn) weapons = weapons.map(w => sspAdjW(w, u));   // 改装核心武器强化(威力/EN/弹药/射程)`
  abilities = unitAbilitiesOf(u.id, sspOn);   // 改装核心能力变化(替换/新增, 与SSP开关联动)
  /* 数值提升档位: 单位能力(含SSP版, 随SSP开关) + 单位技能; 被动=无条件能力 · 主动=+技能 · max=+条件型(视为满足) */
  const _bstSk = featsView.filter(x => x.feature === 'unit_skill').map(x => { let pr = {}; try { pr = JSON.parse(x.params_json || '{}'); } catch (e) {} return { name: x.label, desc: pr.desc || '' }; });
  const bstPct = statBoostOf(abilities, state.uSk === false ? [] : _bstSk, uv.bst);   // 机体技能关: 档位不含单位技能
  const statVal = f => {
    const raw0 = u['max_' + f] || 0;                         // 原 = ★0值(SP关, 游戏「显示强化上限关」关闭态)
    const raw = !ssrBelow ? (u.ult ? raw0 : Math.floor(raw0 * (STAR_MULT[uv.star] || 1)))
                          : uStatVal(u, f, s3On, spOn, (sspG[f] || 0));   // SSP增量加在★倍率之前(游戏口径)
    const pct = bstPct[f] || 0;
    const val = pct ? Math.floor(raw * (1 + pct / 100)) : raw;
    return { val, orig: uv.bst ? raw : raw0 };               // 档位开启时小字=增强前同态值; 否则原=★0值
  };
  const _lvCap = u.rarity >= 5 ? 'Lv100' : ['', 'Lv60', 'Lv70', 'Lv80', 'Lv90'][u.rarity];
  const bstChips = `<span class="chip ${uv.bst === 1 ? 'gold' : ''}" id="ubst1">被动</span><span class="chip ${uv.bst === 2 ? 'gold' : ''}" id="ubst2">主被动</span><span class="chip ${uv.bst === 3 ? 'gold' : ''}" id="ubst3">max</span>`;
  const bstHint = `<div class="hint" style="text-align:left;margin:3px 2px 0">被动=常驻能力 · 主被动=+单位技能数值增幅 · max=再含条件型被动(HP/敌方标签/对战次数等，叠层按最高N%满层)</div>`;
  const statChips = ssrBelow ? `<div class="chips">
      <span class="chip ${s3On ? 'on' : ''}" id="us3">三星</span>
      <span class="chip ${spOn ? 'gold' : ''}" id="usp">SP 强化上限</span>
      ${hasSsp ? `<span class="chip ${sspOn ? 'gold' : ''}" id="uss">SSP满10</span>` : ''}
      ${bstChips}
      <span class="hint" style="align-self:center">${s3On && spOn ? (sspOn ? '三星+SP+SSP满10(★3×1.4+Lv100+SSP)' : '三星+SP 面板(★3×1.4, Lv100)') : (s3On ? '原始数值(★3, ' + _lvCap + ')' : (spOn ? '★0 SP数值(Lv100)' : '★0数值(' + _lvCap + ')'))}</span>
    </div>` : `<div class="chips">
      ${u.ult ? '<span class="hint" style="align-self:center;margin-right:2px">ULT固定值:</span>' : `<span class="hint" style="align-self:center;margin-right:2px">突破星数:</span>
      ${[0, 1, 2, 3].map(s => `<span class="chip ${uv.star === s ? 'on' : ''}" data-ustar="${s}">★${s}</span>`).join('')}
      <span class="hint" style="align-self:center">★0×1.0 · ★1×1.2 · ★2×1.3 · ★3×1.4</span>`}
      ${bstChips}
    </div>`;
  v.innerHTML = `
    <div class="dhead">${imgTag(u.icon)}
      <div><div class="nm">${esc(u.name)} <span class="tagx cond">${r.n}</span></div>
      <div class="model">${rarTag(u.rarity)} ${esc(u.models || '')}${u.ult ? ' · ULT' + (ultStageOf(u) != null ? '（' + ULT_STAGE_FULL[ultStageOf(u)] + '）' : '') : ''}${ultOnNote ? ' · <span style="color:#9fe8c0">ULT改造 Lv' + state.ultLv + '</span>' : ''}</div>
      <div class="chips">${tags.map(t => `<span class="chip" data-gotag="${t.id}" style="padding:2px 8px;font-size:10px">${esc(t.name)} ›</span>`).join('')}</div></div></div>
    ${statChips}${bstHint}
    <div class="statgrid">
      ${[['HP', 'hp'], ['EN', 'en'], ['攻击', 'atk'], ['防御', 'def'], ['机动', 'mob']].map(([k, f]) => {
        const { val, orig } = statVal(f);
        return `<div class="stat"><div class="k">${k}</div><div class="v"${val !== orig ? ' style="color:#9fd8ff"' : ''}>${fmt(val)}</div>${val !== orig ? `<div style="font-size:9px;color:var(--dim)">原 ${fmt(orig)}</div>` : ''}</div>`;
      }).join('')}
      <div class="stat"><div class="k">移动</div><div class="v"${sspM ? ' style="color:#9fd8ff"' : ''}>${u.max_mov + sspM}</div>${sspM ? `<div style="font-size:9px;color:var(--dim)">原 ${u.max_mov}</div>` : ''}</div>
    </div>
    <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">地形:</span>
      ${[['宇宙', u.terrain_space], ['空中', u.terrain_atm], ['地上', u.terrain_ground], ['水面', u.terrain_surface], ['水中', u.terrain_water]].map(([nm2, v2]) => {
        const sym = v2 === 3 ? '○' : v2 === 2 ? '△' : v2 === 1 ? '×' : '—';
        const col = v2 === 3 ? '#7df0a8' : v2 === 2 ? '#f5c451' : v2 === 1 ? '#ff6b6b' : 'var(--dim)';
        return `<span class="chip" style="padding:2px 9px">${nm2} <b style="color:${col}">${sym}</b></span>`;
      }).join('')}
      <span class="hint" style="align-self:center">○正常移动 △移动力减半 ×不能出击</span>
    </div>
    ${(() => {
      const mechs = q('SELECT mechanism_id, name, desc, type, value FROM unit_mechanisms WHERE unit_id=? ORDER BY mechanism_id', [u.id]);
      if (!mechs.length) return '';
      return `<div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">装置:</span>${mechs.map(m => `<span class="chip" style="padding:2px 9px" title="${esc(m.desc || '')}">${esc(m.name)}${m.value ? ` <b>${m.value}%</b>` : ''}</span>`).join('')}</div>
      <div class="subnote" style="text-align:left;margin:-2px 0 8px">${mechs.map(m => `<div style="margin:2px 0"><b>${esc(m.name)}</b>：${esc(String(m.desc || '').replace(/\s*\n\s*/g, ' '))}</div>`).join('')}</div>`;
    })()}
    <div class="card"><h4>武器 · ${weapons.length}</h4>
      ${weapons.map(w => {
        const eff = q('SELECT trait_type, trait_value, desc, effect_name FROM weapon_traits WHERE weapon_id=? AND level=5', [w.id]);
        const fx5 = q('SELECT sort, name, desc FROM weapon_fx WHERE weapon_id=? AND level=5 ORDER BY sort', [w.id]);
        const used = new Set(), chips = [];
        for (const f of fx5) {   // 全部武器特效 → 简化词(增伤/降防/减益/词条/武装效果UP); SSP修饰行(90)仅SSP视图或SSP武器本体
          if (f.sort >= 90 && !(sspOn || w.is_ssp)) continue;
          let sh = fxShort(f.name, f.desc);
          if (!sh) {                                             // 未识别 → 原样兜底(取首行去LV后缀), 保证不漏显
            const raw = String(f.name || f.desc || '').split('\n')[0].replace(/\s*LV\d+\s*$/, '').trim();
            if (!raw || raw === '/' || raw.length < 2) continue;
            sh = raw.length > 20 ? raw.slice(0, 20) + '…' : raw;
          }
          if (chips.indexOf(sh) >= 0) continue;
          chips.push(sh);
          if (sh.indexOf('效果+') >= 0) continue;                // 效果值增加修饰行不消耗属性行
          let v = 0;
          const _up = sh.indexOf('武装效果UP·') === 0 ? sh.match(/[+-](\d+)%/) : null;
          const _ds = String(f.desc || '');
          const _dm = _ds.match(/最高提升\s*(\d+)%/) || _ds.match(/增加\s*(\d+)%/) || _ds.match(/受到的损伤提升\s*(\d+)%/) || _ds.match(/防御力减少\s*(\d+)%/) || _ds.match(/攻击力减少\s*(\d+)%/) || _ds.match(/机动力减少\s*(\d+)%/) || _ds.match(/命中率减少\s*(\d+)%/) || _ds.match(/POWER减少\s*(\d+)%/) || _ds.match(/爆击损伤提升\s*(\d+)%/) || _ds.match(/移动力下降\s*(\d+)/) || _ds.match(/最大射程减少\s*(\d+)/) || _ds.match(/造成损伤的(\d+)%恢复/) || _ds.match(/最大EN的(\d+)%/);
          v = _up ? +_up[1] : +((_dm || [0, 0])[1] || 0);
          if (v) {                                               // 消耗同值属性行(正向POWER类/负向减益类)
            const POS = [39, 44, 45, 81, 82, 91, 92], NEG = [1, 7, 9, 11, 14, 70, 72, 78];
            const idx = eff.findIndex((e, i2) => !used.has(i2) && ((POS.indexOf(e.trait_type) >= 0 && e.trait_value === v) || (NEG.indexOf(e.trait_type) >= 0 && e.trait_value === -v)));
            if (idx >= 0) used.add(idx);
          }
        }
        eff.forEach((e, i2) => {                                 // 未被 fx 消耗的POWER类 → 沿用本武器距离条件/威力, 其余原样
          if (used.has(i2)) return;
          if ([44, 45, 81, 82, 92].includes(e.trait_type) && e.trait_value) {
            const kw = chips.find(c => c.startsWith('近距离') || c.startsWith('远距离'));
            chips.push((kw ? kw.replace(/[+-]\d+%$/, '') : '威力') + (e.trait_value > 0 ? '+' : '') + e.trait_value + '%');
          } else chips.push(effText(e, w));
        });
        if (sspOn) {   // SSP视图: 88修饰行并入同名效果值(降防25%→30%)
          for (const r of ((weaponSspTraits()[w.id] || []).filter(x => x.trait_type === 88))) {
            const mm = String(r.desc || '').match(/(且)([^)）]*?)(光束|镭射|物理|特殊|防御力减少)[^0-9]*?(\d+)%/);
            if (!mm) continue;
            const sc = mm[3] === '防御力减少' ? '降防' : (mm[3] === '镭射' ? '光束' : mm[3]);
            for (let i2 = 0; i2 < chips.length; i2++) {
              let cm = chips[i2].match(/^(光束|物理|特殊)-(\d+)%$/);
              if (cm && cm[1] === sc) { chips[i2] = sc + '-' + (+cm[2] + +mm[4]) + '%'; continue; }
              cm = chips[i2].match(/^降防(\d+)%$/);
              if (cm && sc === '降防') chips[i2] = '降防' + (+cm[1] + +mm[4]) + '%';
            }
          }
        }
        const sspChips = [];
        for (const t of (w._sspTraits || [])) {   // SSP核心追加效果(金标), 同文案去重
          const x = fxShort(t.name, t.desc) || t.name || t.desc;
          if (x && chips.indexOf(x) < 0 && sspChips.indexOf(x) < 0) sspChips.push(x);
        }
        const effHtml = chips.map(x => `<span class="wfx">${esc(x)}</span>`).join('') + sspChips.map(x => `<span class="wfx" style="border-color:#f5c451;color:#f5c451">${esc(x)}</span>`).join('');
        return `<div class="wrow" data-id="${w.id}"><span class="wn">${esc(w.name)}${w.is_ssp ? ' <span class="tagx new" style="font-size:8.5px;padding:1px 4px">SSP</span>' : ''}${AATTR[w.weapon_attr] ? ' <span class="wattr a' + (w.weapon_attr || 0) + '">' + AATTR[w.weapon_attr] + '</span>' : ''}</span><span class="wr">${w.range_min}-${w.range_max}${w.type === 3 ? ' MAP' : ''}</span>
          <span class="wp">${fmt(Engine.weaponPower(w, 1))}<span style="color:var(--dim);font-size:10px">→${fmt(Engine.weaponPower(w, 5))}</span></span>
          <span style="flex:1;text-align:right">${effHtml}</span></div>`; }).join('')}
    </div>
    <div class="btnrow"><span class="bp" id="tocalc">加入伤害计算</span></div>
    <div class="card"><h4>对中防目标(20k)伤害 · 原配驾驶员 / 最高伤害驾驶员</h4><div class="kv" id="ubb" style="color:var(--dim);padding:0">计算中…</div></div>
    <div class="card"><h4>能力 · ${abilities.length}</h4>
      ${abilities.map(a => `<div class="kv">✦ ${esc(a.name)}${a._ssp ? ' <span class="tagx new" style="font-size:8.5px;padding:1px 4px">SSP</span>' : ''}<br>${abilityCondChips(a.traits_json)}<span style="color:#8ea0c4;font-size:10.5px">${traitDescsOf(a.traits_json).map(descHtml).join('<br>') || '—'}</span></div>`).join('') || '<div class="kv" style="color:var(--dim)">无</div>'}
    </div>
    ${ultSkList.length ? `<div class="card"><h4>ULT改造能力 · 三选一 <span class="fbtn" id="uultopen" style="font-size:10px;margin-left:6px">⚙ 设置</span></h4>
      ${ultSkList.map(sk => { const selId = String(state.ultSkill[_ultG] ?? (ultSkList[0] && ultSkList[0].skill_id)); const sel = selId === String(sk.skill_id); const on = sel && state.ultLv >= 100;
        return `<div class="kv" style="${on ? '' : 'opacity:.62'}"><b>${esc(String(sk.name || '').replace(/^单位技能【|】$/g, ''))}</b> <span style="color:#9fe8c0;font-size:9.5px;border:1px solid #9fe8c088;border-radius:6px;padding:0 5px">机体技能</span> <span style="color:#f5c451;font-size:9.5px;border:1px solid #f5c45188;border-radius:6px;padding:0 5px">ULT改造</span> ${on ? '<span style="color:#9fe8c0;font-size:9.5px;border:1px solid #9fe8c088;border-radius:6px;padding:0 5px">生效</span>' : (sel ? '<span style="color:#f5c451;font-size:9.5px;border:1px solid #f5c45188;border-radius:6px;padding:0 5px">Lv100解锁</span>' : '<span style="color:#6d82ab;font-size:9.5px;border:1px solid #2c4066;border-radius:6px;padding:0 5px">未选</span>')}<br><span style="color:#8ea0c4;font-size:10.5px">${esc(String(sk.desc || '').replace(/\n/g, ' ').slice(0, 120))}</span></div>`; }).join('')}
      <div class="hint">当前ULT改造 Lv${state.ultLv || 0}；三段共用同一套改造，Lv50解锁ULT武器，Lv100解锁能力。</div>
    </div>` : ''}
    ${featsView.length ? `<div class="card"><h4>特性 · 机制</h4>
      ${featsView.map(f => { let pr = {}; try { pr = JSON.parse(f.params_json || '{}'); } catch (e) {}
        const isUS = f.feature === 'unit_skill';
        const ttl = isUS ? esc(String(f.label || '').replace(/^单位技能【|】$/g, '')) : (FEAT[f.feature] || f.feature);
        return `<div class="kv"><b>${ttl}</b>${isUS ? ' <span style="color:#9fe8c0;font-size:9.5px;border:1px solid #9fe8c088;border-radius:6px;padding:0 5px">机体技能</span>' : ''}${pr.ult ? ' <span style="color:#f5c451;font-size:9.5px;border:1px solid #f5c45188;border-radius:6px;padding:0 5px">ULT改造</span>' : ''} ${isUS ? '' : esc(f.label || '')} <span style="color:var(--dim)">${esc((pr.desc || '').slice(0, 80))}</span></div>`; }).join('')}
    </div>` : ''}`;
  $('tocalc').onclick = () => { state.calc.unitId = u.id; state.stack = []; setTab('calc'); };
  if ($('uultopen')) $('uultopen').onclick = () => openUltSheet();
  v.querySelectorAll('[data-gotag]').forEach(el => el.onclick = () => {   // 标签 → 图鉴按该标签筛选
    const f = filt('unit'); f.tags = [+el.dataset.gotag]; f.mode = 'or'; f.series = [];
    state.unitKind = 'unit'; state.pageLimit = PAGE_SIZE; state.stack = []; setTab('units');
  });
  if ($('us3')) $('us3').onclick = () => { uv.star3 = !uv.star3; if (!uv.star3) uv.ssp = false; pageUnit(v, sp); };
  if ($('usp')) $('usp').onclick = () => { uv.sp = !uv.sp; if (!uv.sp) uv.ssp = false; pageUnit(v, sp); };
  if ($('uss')) $('uss').onclick = () => { uv.ssp = !uv.ssp; if (uv.ssp) { uv.sp = true; uv.star3 = true; } pageUnit(v, sp); };
  [1, 2, 3].forEach(i => { const el = $('ubst' + i);          // 档位互斥单选, 再点同档=回原值
    if (el) el.onclick = () => { uv.bst = (uv.bst === i ? 0 : i); pageUnit(v, sp); }; });
  v.querySelectorAll('[data-ustar]').forEach(el => el.onclick = () => { uv.star = +el.dataset.ustar; pageUnit(v, sp); });
  v.querySelectorAll('.wrow').forEach(el => el.onclick = () => { const w = q1('SELECT * FROM weapons WHERE id=?', [+el.dataset.id]); push({ page: 'weapon', title: w.name, id: w.id }); });
  setTimeout(() => {
    const el = document.getElementById('ubb'); if (!el) return;
    try {
      const rows = unitBestPilot(u.id, 20000);
      const b0 = rows[0];
      const dc = u.default_char_id ? q1('SELECT id,name,icon,role,rarity FROM characters WHERE id=?', [u.default_char_id]) : null;
      const dRow = dc ? rows.find(r => r.id === dc.id) : null;
      const prow = (label, ch, r) => `<div class="trow" data-ppick="${ch.id}">${avDrv(ch.icon, ch.role, ch.rarity)}
        <div class="nm">${label} <b>${esc(ch.name)}</b> ${rarTag(ch.rarity)}<small>${r ? esc(r.weapon.name) + ' · ' + Engine.VIGOR[r.vigor].label + (r.mp ? '(MP' + r.mp + ')' : '') : '（当前口径无结果）'}</small></div>
        <span class="val g">${r ? fmt(r.dmg) : '—'}</span></div>`;
      el.style.color = '';
      el.innerHTML = (dc ? prow('原配驾驶员', dc, dRow) : '')
        + (b0 ? prow('最高伤害', { id: b0.id, name: b0.name, icon: b0.icon, role: b0.role, rarity: b0.rarity }, b0) : '<div style="color:var(--dim)">—</div>');
      el.querySelectorAll('[data-ppick]').forEach(x => x.onclick = () => { state.calc.unitId = u.id; state.calc.charId = +x.dataset.ppick; state.stack = []; setTab('calc'); });
    } catch (e) { el.textContent = '—'; }
  }, 40);
}
/* 单机体 对靶最大伤害驾驶员（默认口径: Lv5/全技能/条件全开/多阶段, 用于图鉴页速览; 结果缓存） */
function unitBestPilot(uid, tDef = 20000, tCharDef = 750, pSpU) {
  const key = uid + '|' + tDef + '|' + tCharDef + '|' + (pSpU !== false ? 1 : 0) + '|' + (state.ultLv || 0) + '|' + JSON.stringify(state.ultSkill) + '|' + (state.supAct !== false ? 1 : 0) + '|' + (state.maxOn ? 1 : 0);
  state._ubMap = state._ubMap || {};
  if (state._ubMap[key]) return state._ubMap[key];
  const u = effUnit(q1('SELECT * FROM units WHERE id=?', [uid]));
  const meta = metaOf(uid);
  const isSD = meta.tags.has('SD高达');
  const sdMap = sdCharMap();
  const uBase = Math.floor((u.sp_max_atk || u.max_atk) * 1.4);
  const ws = weaponsForUnit(u);
  const traitsByW = {};
  for (const w of ws) traitsByW[w.id] = wTraitsOf(w.id, null, true);
  const cands = isSD
    ? [sdOwnChar(u)].filter(Boolean)
    : q('SELECT id,name,icon,rarity,role,max_melee,max_ranged,max_awaken,sp_max_melee,sp_max_ranged,sp_max_awaken FROM characters WHERE COALESCE(is_playable,1)=1')
        .filter(p => { const o = sdMap[p.id]; return !o || o.has(uid); });
  const rows = [];
  for (const p of cands) {
    const mp = mpOf(uid, p.id, true, true, pSpU, false);
    const vg = mpToVigor(mp);
    const b = charBonus(p.id, vg, { passive: true, cpassive: true, skills: true, condAll: true, first: false, unitId: uid, upassive: true, multiPhase: true, pSpU: pSpU !== false, ussp: false }, meta);
    const uAtk = Math.floor(uBase * (1 + (unitPassiveAtkPct(uid, vg, true, null, false, false) + (state.uSk !== false ? unitSkillAtkPct(uid) : 0) + (b.atk || 0)) / 100));
    let best = null;
    for (const w of ws) {
      if (!vigorAllows(w.id, vg, mp)) continue;   // 气势/MP 条件不足时不能使用
      const attrs = WATTR[w.attack_attr] || ['melee'];
      let statA = attrs[0], cAtk = -1;
      for (const a of attrs) { const val = Math.floor(pStat(p, a, pSpU) * (1 + (b[a] || 0) / 100)); if (val > cAtk) { cAtk = val; statA = a; } }
      const d = Engine.damageWithWeapon(uAtk, cAtk, w, traitsByW[w.id] || [], 5, tDef, tCharDef, { vigor: vg, crit: false, ee: b.dmg + ultDmgPct(u) });
      if (!best || d.final > best.dmg) best = { dmg: d.final, weapon: w, vigor: vg, mp };
    }
    if (best) rows.push(Object.assign({ id: p.id, name: p.name, icon: p.icon, rarity: p.rarity }, best));
  }
  rows.sort((a, b) => b.dmg - a.dmg);
  state._ubMap[key] = rows;
  return rows;
}

function pageWeapon(v, sp) {
  const w = q1('SELECT w.*, u.name uname, u.icon uicon, u.rarity urarity, u.role urole FROM weapons w JOIN units u ON u.id=w.unit_id WHERE w.id=?', [sp.id]);
  if (!w) { v.innerHTML = '<div class="err">未找到</div>'; return; }
  sp.title = w.name;
  const wsc = JSON.parse(w.wsc_json || '[]');
  const traits = q('SELECT * FROM weapon_traits WHERE weapon_id=? ORDER BY level, trait_type', [w.id]);
  const fx = q('SELECT * FROM weapon_fx WHERE weapon_id=? ORDER BY level, sort', [w.id]);
  let wuse = []; try { wuse = q('SELECT text FROM weapon_use WHERE weapon_id=? ORDER BY sort', [w.id]); } catch (e) {}
  let hpc = null; try { hpc = q1('SELECT hp, mp FROM weapon_hpcost WHERE weapon_id=?', [w.id]); } catch (e) {}   // HP/MP消耗使用限制(旧库无此表时忽略)
  let ware = null; try { ware = q1('SELECT * FROM weapon_area WHERE weapon_id=?', [w.id]); } catch (e) {}   // 使用地点(旧库无此表时忽略)
  const lvRows = wsc.map(r => {
    let effHtml;
    const fxr = fx.filter(f => f.level === r.level);
    if (fxr.length) {   // 完整效果名+说明（来自效果主表）
      effHtml = fxr.map(f => (f.name ? `<span class="wfx" title="${esc(f.desc || '')}">${esc(f.name)}</span>` : '') + (f.desc && f.desc !== f.name ? `<div class="wfxdesc">${esc(f.desc)}</div>` : '')).join('');
    } else {
      const eff = traits.filter(t => t.level === r.level && t.trait_type);
      effHtml = eff.map(e => `<span class="wfx">${e.desc ? esc(e.desc.slice(0, 22)) : effText(e, w)}</span>`).join('');
    }
    return `<tr><td class="l">Lv${r.level}</td><td class="v">${fmt(Math.floor(w.power * r.power / 100))}</td><td>${Math.floor((w.en || 0) * r.en / 100)}</td><td class="l" style="text-align:right">${effHtml}</td></tr>`;
  }).join('');
  v.innerHTML = `
    <div class="dhead">${avTagR(w.uicon, w.urole, w.urarity)}<div><div class="nm">${esc(w.name)}</div>
      <div class="model">${esc(w.uname)} ${rarTag(w.urarity)} · ${TYATTR[w.attack_attr] || ''} · ${AATTR[w.weapon_attr] || ''} · 射程${w.range_min}-${w.range_max}${w.type === 3 ? '·MAP' : ''} · ${w.type === 3 ? 'MAP武装' : (w.type === 2 ? 'EX武装' : '通常')}</div></div></div>
    <div class="card"><h4>每级数据（威力 / EN / 武装效果${fx.length ? ' · 完整效果' : ''}）</h4>
      <table class="ctable"><tr><th style="text-align:left">等级</th><th>威力</th><th>EN</th><th style="text-align:right">效果</th></tr>${lvRows}</table></div>
    ${(() => { const lines = wuse.map(u => u.text);
      if (hpc && hpc.hp > 0 && !lines.some(t => t.indexOf('消耗') >= 0 && t.indexOf('HP') >= 0)) lines.push('消耗' + hpc.hp + '%HP即可使用');
      if (hpc && hpc.mp > 0 && !lines.some(t => t.indexOf('消耗') >= 0 && t.indexOf('MP') >= 0)) lines.push('消耗' + hpc.mp + 'MP即可使用');
      if (ware && (ware.space === 0 || ware.atm === 0 || ware.ground === 0 || ware.surface === 0 || ware.water === 0)) {   // 使用地点: 不可用场地列出
        const areas = [['宇宙', ware.space], ['空中', ware.atm], ['地上', ware.ground], ['水面', ware.surface], ['水中', ware.water]];
        lines.push('使用地点: ' + areas.filter(a => a[1]).map(a => a[0]).join('/') + '可用 · ' + areas.filter(a => !a[1]).map(a => a[0] + '不可用').join(' '));
      }
      return lines.length ? `<div class="card"><h4>使用限制</h4>${lines.map(t => `<div class="kv">${esc(t)}</div>`).join('')}</div>` : ''; })()}
    <div class="kv" style="color:var(--dim)">命中 ${w.hit_rate}% · 暴击 ${w.crit_rate}% · 弹药 ${w.ammo || '∞'}</div>`;
}

function traitDescOf(traitsJson) {
  try {
    const ts = JSON.parse(traitsJson || '[]');
    for (const t of ts) { const d = ((t || {}).trait || {}).desc; if (d) return d.replace(/\n/g, ' '); }
  } catch (e) {}
  return '';
}
/* 能力完整描述: 汇总所有 trait 的描述（EX能力含「超一击EX1/EX2」多段赋予说明）; 无描述时退化为授予效果 */
function traitDescsOf(traitsJson) {
  const out = [];
  try {
    const ts = JSON.parse(traitsJson || '[]');
    for (const t of ts) {
      const d = (((t || {}).trait || {}).desc || '').trim();
      if (d && !out.includes(d)) out.push(d);
    }
    if (!out.length) for (const t of ts) for (const g of (((t || {}).trait || {}).granted_trait_set || [])) {
      const d = (((g || {}).trait || {}).desc || '').trim();
      if (d && !out.includes(d)) out.push(d);
    }
  } catch (e) {}
  return out;
}
/* 能力条件标签 chips: 从 active_condition 提取 标签/驾驶员标签/搭乘角色系列 的显示名
   (补足文案里「上述「标签」」占位符 —— 如「优势：新人类」需显示 TAG 新人类) */
function abilityCondChips(traitsJson) {
  const chips = [];   // {t: 文本, tag: 是否TAG图标} — 与游戏「角色/单位能力一览」同款: TAG xxx / 耐久型类型
  const add = (t, tag) => { if (t && !chips.some(c => c.t === t)) chips.push({ t, tag }); };
  const td = tagNameDict(), sd = seriesNameDict();
  try {
    for (const t of JSON.parse(traitsJson || '[]')) {
      const ac = ((t || {}).trait || {}).active_condition || {};
      for (const x of (ac.tags || [])) add(x && (x.name || td[x.id]), true);
      for (const raw of String(ac.unit_tags || '').split(',')) { const id = +raw; if (id && td[id]) add(td[id], true); }
      for (const x of (ac.character_tags || [])) add(x && (x.name || td[x.id]), true);
      const cs = ac.character_series; if (cs && (cs.name || sd[cs.id])) add(cs.name || sd[cs.id], false);
      for (const raw of String(ac.unit_series || '').split(',')) { const sid = raw.trim(); if (sid && sd[sid]) add('SERIES ' + sd[sid], false); }   // 搭乘系列条件(游戏「角色能力一览」SERIES chip, 如 超强势EX的 GUNDAM EXA)
      if (ac.unit_role) { const r = ROLE[+ac.unit_role]; if (r) add(r.n + '类型', false); }   // 搭乘类型条件(如 耐久型类型)
    }
  } catch (e) {}
  return chips.length ? chips.map(c => `<span class="tagx cond" style="margin:0 4px 2px 0">${c.tag ? 'TAG ' : ''}${esc(c.t)}</span>`).join('') + '<br>' : '';
}
const descHtml = d => d.split('\n').map(esc).join('<br>');
function skillEffTags(traitsJson) {
  const out = [];
  try {
    const ts = JSON.parse(traitsJson || '[]');
    for (const t of ts) {
      const tr = (t || {}).trait || {};
      const e = SKILL_EFF[tr.trait_type];
      if (!e || !tr.trait_value) continue;
      if (tr.trait_type === 14) {            // 摇摆闪避: 数值是次数, 提升百分比写在描述里
        const m = /(?:閃|闪)避率提升\s*(\d+)/.exec(tr.desc || '');
        out.push('闪避+' + (m ? m[1] : '?') + '%');
      } else out.push(e[0] + tr.trait_value + e[1]);
    }
  } catch (e) {}
  return out;
}
function pageChar(v, sp) {
  const c = q1('SELECT * FROM characters WHERE id=?', [sp.id]); if (!c) { v.innerHTML = '<div class="err">未找到</div>'; return; }
  sp.title = c.name;
  const tags = q('SELECT t.id, t.name FROM char_tags ct JOIN tags t ON t.id=ct.tag_id WHERE ct.char_id=?', [c.id]);
  const _mergeSpRows = (baseRows, spRows) => {           // SP版按槽位替换(技能/能力随SP变化)
    if (!state.charSp || !spRows.length) return baseRows;
    const m = {}; baseRows.forEach(r => m[r.sort] = r); spRows.forEach(r => m[r.sort] = r);
    return Object.values(m).sort((a, b) => (a.sort || 0) - (b.sort || 0));
  };
  const skills = _mergeSpRows(q('SELECT * FROM char_skills WHERE char_id=? ORDER BY sort', [c.id]),
                              q('SELECT * FROM char_skills_sp WHERE char_id=? ORDER BY sort', [c.id]));
  const abilities = _mergeSpRows(q('SELECT name, traits_json, sort FROM char_abilities WHERE char_id=?', [c.id]),
                                 q('SELECT name, traits_json, sort FROM char_abilities_sp WHERE char_id=?', [c.id]));
  const feats = q('SELECT feature,label,params_json FROM features WHERE target_type="char" AND target_id=?', [c.id]);
  if (state.charBst === undefined) state.charBst = 0;   // 数值提升档位: 0=原值 1=被动(常驻能力, 如网站) 2=+主动技能 3=max(+条件型)
  const cBstPct = statBoostOf(abilities, skills, state.charBst);
  const statCell = k => {
    const base = pStat(c, k, state.charSp);
    const pct = cBstPct[k] || 0;
    const v = pct ? Math.floor(base * (1 + pct / 100)) : base;
    const b0 = state.charBst ? base : (c['max_' + k] || 0);   // 档位开: 小字=增强前同态值; 否则原=SP关值
    return v !== b0 ? `<span style="color:#9fd8ff">${fmt(v)}</span><small style="color:var(--dim);font-size:9px"> 原${fmt(b0)}</small>` : fmt(v);
  };
  v.innerHTML = `
    <div class="dhead">${imgTag(c.icon)}
      <div><div class="nm">${esc(c.name)} ${rarTag(c.rarity)}</div>
      <div class="chips" style="margin-top:6px">${tags.map(t => `<span class="chip" data-gotag="${t.id}" data-gochar="1" style="padding:2px 8px;font-size:10px">${esc(t.name)} ›</span>`).join('')}</div></div></div>
    <div class="chips" style="margin-top:2px"><span class="chip ${state.charSp ? 'gold' : ''}" id="cspu2">驾驶员SP${state.charSp ? ' 开' : ' 关'}</span>
      <span class="chip ${state.charBst === 1 ? 'gold' : ''}" id="cbst1">被动</span>
      <span class="chip ${state.charBst === 2 ? 'gold' : ''}" id="cbst2">主被动</span>
      <span class="chip ${state.charBst === 3 ? 'gold' : ''}" id="cbst3">max</span>
      <span class="hint" style="align-self:center;font-size:10px">被动=常驻能力 · 主被动=+技能数值增幅 · max=再含条件型(满层)</span></div>
    <div class="statgrid">${[['射击', 'ranged'], ['格斗', 'melee'], ['觉醒', 'awaken'], ['防御', 'defense'], ['反应', 'reaction']]
      .map(([k, key]) => `<div class="stat"><div class="k">${k}</div><div class="v">${statCell(key)}</div></div>`).join('')}</div>
    <div class="card"><h4>技能 · ${skills.length}</h4>
      ${skills.map(s => `<div class="kv">⚡ ${esc(s.name)} <span style="color:var(--dim)">SP${s.sp}</span>${skillEffTags(s.traits_json).map(x => `<span class="wfx">${esc(x)}</span>`).join('')}<br><span style="color:#8ea0c4">${esc((s.desc || '').replace(/\n/g, ' '))}</span></div>`).join('')}</div>
    <div class="card"><h4>能力</h4>${abilities.map(a => `<div class="kv">✦ ${esc(a.name)}<br>${abilityCondChips(a.traits_json)}<span style="color:#8ea0c4;font-size:10.5px">${traitDescsOf(a.traits_json).map(descHtml).join('<br>') || '—'}</span></div>`).join('') || '<div class="kv" style="color:var(--dim)">无</div>'}</div>
    ${feats.length ? `<div class="card"><h4>特性</h4>${feats.map(f => { let pr = {}; try { pr = JSON.parse(f.params_json || '{}'); } catch (e) {}
      const fk = (f.feature === 'support_atk' || f.feature === 'support_def');
      const fnm = fk ? ((f.feature === 'support_atk' ? '支援攻击' : '支援防御') + '+' + supFeatCountOf(c.id, f.feature === 'support_atk' ? 'atk' : 'def') + '次') : (FEAT[f.feature] || f.feature);
      return `<div class="kv"><b>${fnm}</b> ${esc(f.label || '')} <span style="color:var(--dim)">${esc((pr.desc || '').slice(0, 70))}</span></div>`; }).join('')}</div>` : ''}
    <div class="btnrow"><span class="bp" id="tocalc">加入伤害计算</span></div>`;
  $('tocalc').onclick = () => { state.calc.charId = c.id; state.stack = []; setTab('calc'); };
  if ($('cspu2')) $('cspu2').onclick = () => { state.charSp = !state.charSp; pageChar(v, sp); };
  [1, 2, 3].forEach(i => { const el = $('cbst' + i);          // 档位互斥单选, 再点同档=回原值
    if (el) el.onclick = () => { state.charBst = (state.charBst === i ? 0 : i); pageChar(v, sp); }; });
  v.querySelectorAll('[data-gotag]').forEach(el => el.onclick = () => {   // 标签 → 图鉴按该标签筛选
    const f = filt('char'); f.tags = [+el.dataset.gotag]; f.mode = 'or'; f.series = [];
    state.unitKind = 'char'; state.pageLimit = PAGE_SIZE; state.stack = []; setTab('units');
  });
}

function pageSupp(v, sp) {
  const s = q1('SELECT * FROM supporters WHERE id=?', [sp.id]); if (!s) { v.innerHTML = '<div class="err">未找到</div>'; return; }
  sp.title = s.name;
  let lt = {}; try { lt = JSON.parse(s.leader_target_json || '{}'); } catch (e) {}
  v.innerHTML = `
    <div class="dhead">${imgTag(s.icon)}<div><div class="nm">${esc(s.name)}</div>
      <div class="model">${rarTag(s.rarity)}</div></div></div>
    <div class="statgrid"><div class="stat"><div class="k">HP支援</div><div class="v">+${fmt(s.hp_support)}</div></div>
      <div class="stat"><div class="k">攻击支援</div><div class="v">+${fmt(s.atk_support)}</div></div></div>
    <div class="card"><h4>Leader 技能</h4><div class="kv">${esc(s.leader_desc || '')}</div>
      <div class="kv" style="color:var(--dim);font-size:10.5px">适用: ${esc([...(lt.series_name || []), ...(lt.unit_tags || [])].join(' / ') || '—')}</div></div>
    <div class="card"><h4>Support 技能</h4><div class="kv"><b>${esc(s.support_skill_name || '—')}</b><br>${esc(s.support_skill_desc || '')}</div></div>`;
}

function pageMod(v, sp) {
  const m = q1('SELECT * FROM mods WHERE id=?', [sp.id]); if (!m) { v.innerHTML = '<div class="err">未找到</div>'; return; }
  sp.title = m.name;
  const traits = q('SELECT traits_json FROM mods WHERE id=?', [m.id]);
  let trs = []; try { trs = JSON.parse(m.traits_json || '[]'); } catch (e) {}
  const descs = [];
  (trs || []).forEach(x => { const t = (x || {}).trait; if (t && t.desc) descs.push(t.desc); });
  v.innerHTML = `<div class="dhead">${imgTag(m.icon, '', modImg(m.icon))}<div><div class="nm">${esc(m.name)}</div><div class="model">${rarTag(m.rarity)}</div></div></div>
    <div class="card"><h4>效果</h4>${descs.map(d => `<div class="kv">${esc(d)}</div>`).join('') || `<div class="kv">${esc((m.desc || '').replace(/\n/g, ' '))}</div>`}</div>`;
}

/* ------------ 计算页 ------------ */
function topPilots() {
  const st = ['max_melee', 'max_ranged', 'max_awaken'];
  const out = {};
  for (const s of st) out[s] = q(`SELECT id,name,icon,${s} v FROM characters WHERE rarity>=5 ORDER BY ${s} DESC LIMIT 5`);
  return out;
}
let _topPilots = null;
const getTopPilots = () => (_topPilots = _topPilots || topPilots());

const TIERS = [['低防 10k', 10000], ['中防 20k', 20000], ['高防 40k', 40000]];

function pageCalc(v) {
  const c = state.calc;
  if (c.charId && c.unitId && !pilotCanDrive(c.charId, c.unitId)) c.charId = null;   // SD绑定驾驶员不能驾驶其他机体
  const u = effUnit(c.unitId ? q1('SELECT * FROM units WHERE id=?', [c.unitId]) : null);   // ULT改造口径
  const ch = c.charId ? q1('SELECT * FROM characters WHERE id=?', [c.charId]) : null;
  const isSDUnit = !!(u && metaOf(u.id).tags.has('SD高达'));
  const sdOwn = isSDUnit ? sdOwnChar(u) : null;
  const ssrBelow = !!(u && u.rarity <= 4 && !u.ult);          // SSR及以下: 任何时候按三星
  const uSp = ssrBelow ? (c.spU !== false) : true;             // SP 强化上限(Lv100)
  const uS3 = ssrBelow ? (c.s3u !== false) : !!c.star;         // 三星(★3×1.4); UR用★3开关
  const sspOn = !!(u && c.ssp && uS3 && uSp);                  // SSP 必须 三星+SP
  const sspG = sspOn ? sspGainOf(u, 10) : null;                // SSP满10加成
  const uBase = u ? (u.ult ? (u.max_atk || 0)                                        // ULT固定值(不乘星, 与排行/图鉴一致)
                          : (ssrBelow ? uStatVal(u, 'atk', uS3, uSp, (sspG ? sspG.atk : 0))   // SSP增量加在★倍率之前(游戏口径)
                              : Math.floor((u.max_atk || 0) * (c.star ? 1.4 : 1)))) : 0;
  /* 默认战意: 按驾驶员/机体被动MP自动判定(≥4强势/≥8超强势/≥12超一击) */
  const autoMP = c.vigor === 'default' ? mpOf(u ? u.id : null, ch ? ch.id : -1, c.first ? false : c.skills, c.ca, c.pSpU, sspOn) : null;
  let eVigor = autoMP != null ? mpToVigor(autoMP) : c.vigor;
  /* 首动: 首动技能与武器无关的判定(减伤/MP技) — 首动放MP技(需自身MP≥3) → 该次攻击超一击(＋30%) */
  const mp0 = ch ? mpOf(u ? u.id : null, ch.id, false, c.ca, c.pSpU, sspOn) : 0;   // 被动MP: 首动MP提升释放条件用
  const faTop = (c.first && ch) ? firstActOf(ch.id, c.pSpU !== false, null, c.fdth, mp0) : null;
  if (faTop && faTop.k === 'mp') eVigor = 'supercharged';
  const uPctP = (u && c.passive) ? unitPassiveAtkPct(u.id, eVigor, c.ca, null, sspOn, c.first) : 0;   // c.ca: 条件被动全开; sspOn: 改装核心能力变化
  const uPctS = (u && state.uSk !== false) ? unitSkillAtkPct(u.id) : 0;   // 机体技能开关(独立于主动技能)
  const uPct = uPctP + uPctS;
  const uMeta = u ? metaOf(u.id) : null;
  const cBonus = ch ? charBonus(ch.id, eVigor, { passive: c.cpassive, cpassive: c.cpassive, skills: (c.first ? false : c.skills), condAll: c.ca, first: c.first, unitId: u ? u.id : null, upassive: c.passive, multiPhase: c.mp, pSpU: c.pSpU !== false, ussp: sspOn }, uMeta) : { dmg: 0, melee: 0, ranged: 0, awaken: 0, atk: 0 };
  const uAtk = Math.floor(uBase * (1 + (uPct + (cBonus.atk || 0)) / 100));   // 驾驶员「攻击力提升%」(如(支援时)攻击力提升)计入机体攻击
  const fmtBonus = b => { const parts = []; if (b.dmg) parts.push('增伤+' + b.dmg + '%'); if (b.atk) parts.push('攻击+' + b.atk + '%'); for (const a of ['melee', 'ranged', 'awaken']) if (b[a]) parts.push(STATNAME[a] + '+' + b[a] + '%'); return parts.join('·'); };
  const cBonusP = ch ? charBonus(ch.id, eVigor, { passive: true, cpassive: c.cpassive, skills: false, condAll: c.ca, first: c.first, unitId: u ? u.id : null, upassive: c.passive, multiPhase: c.mp, pSpU: c.pSpU !== false }, uMeta) : {};
  const cBonusS = (ch && c.skills && !c.first) ? charBonus(ch.id, eVigor, { passive: false, cpassive: c.cpassive, skills: true, condAll: c.ca, first: c.first, unitId: u ? u.id : null, upassive: c.passive, multiPhase: c.mp, pSpU: c.pSpU !== false }, uMeta) : {};
  const cpassiveTxt = !c.cpassive ? '关' : (fmtBonus(cBonusP) || '无伤害类');
  const cSup = ch ? supCountsOf(ch.id, u ? u.id : null, eVigor, c.ca, c.pSpU !== false) : null;   // 次数技能(当前所选 机体+驾驶员)
  const skillsTxt = c.first ? '由首动接管' : (!c.skills ? '关' : (fmtBonus(cBonusS) || '无伤害类'));
  const vigor = Engine.VIGOR[eVigor] || Engine.VIGOR['default'];
  const tDef = c.tDef ?? 10000;                       // 靶防御（可输入/低中高快捷）
  const cols = TIERS.slice();
  if (!cols.some(([, vv]) => vv === tDef)) cols.push([`当前 ${Math.round(tDef / 1000)}k`, tDef]);
  const ws = u ? weaponsForUnit(u, ' ORDER BY power DESC').map(w => sspOn ? sspAdjW(w, u) : w).filter(w => !w.is_ssp || sspOn) : [];   // SSP武器只在SSP开关打开时参与计算; 改装核心强化随SSP生效
  /* 首动标记: 值增幅按「本机体+驾驶员」实际武器的属性判定(换机体/换武器首动技会变) */
  const _wattrs = ws.length ? [...new Set(ws.flatMap(w => WATTR[w.attack_attr] || ['melee']))] : ['ranged', 'melee', 'awaken'];
  const faShow = (c.first && ch) ? firstActOf(ch.id, c.pSpU !== false, _wattrs, c.fdth, mp0) : null;
  let rows = [], hiddenN = 0;
  if (u) {
    const wsOk = ws.filter(w => vigorAllows(w.id, eVigor, autoMP));   // 气势/MP 条件不足时隐藏
    hiddenN = ws.length - wsOk.length;
    rows = wsOk.map(w => {
      const attrs = WATTR[w.attack_attr] || ['melee'];
      const faW = (c.first && ch) ? firstActOf(ch.id, c.pSpU !== false, attrs, c.fdth, mp0) : null;   // 首动技(值增幅按本武器属性)
      const cAtk = ch ? Math.max(...attrs.map(a => Math.floor(pStat(ch, a, c.pSpU) * (1 + ((cBonus[a] || 0) + (faW && faW.k === 'stat' && faW.stat === a ? faW.v : 0)) / 100)))) : 1500;
      const traits = wTraitsOf(w, null, c.ca);
      const ci = critInfo(u.id, ch ? ch.id : null, w, uMeta, { upassive: c.passive, cpassive: c.cpassive, skills: (c.first ? false : c.skills), condAll: c.ca, vigor: eVigor, multiPhase: c.mp, pSpU: c.pSpU !== false, ussp: sspOn });
      const critOn = canCrit(ci) && (c.crit || ci.guar || ci.rate >= 100);   // 暴击率100%/必暴: 无视开关按暴击计算
      const ee0 = cBonus.dmg + (faW && faW.k === 'burst' ? faW.v : 0) + ultDmgPct(u);   // 首动=攻击爆裂/ULT改造攻击爆裂 → 该次攻击+损伤%
      const dmgs = cols.map(([lbl, tier]) => Engine.damageWithWeapon(uAtk, cAtk, w, traits, c.lv, tier, c.tCharDef ?? 750, { vigor: eVigor, crit: critOn, ee: ee0, critDmgAdd: critOn ? ci.cdmg : 0 }).final);
      return { w, cAtk, dmgs, ci, critOn, canCrit: canCrit(ci), fa: faW };
    });
  }
  /* 该机体伤害前10驾驶员（按当前口径: 武装Lv5/气势/暴击/开关, 靶 中防20k）;
     筛选 = 页面「驾驶员稀有度」行(c.pRar) + 选择器「驾驶员的标签/系列」弹窗(pickc: 标签/系列/稀有度/类型) — 与选择器列表 pickWhere 同口径 */
  let pilotRows = [];
  if (u && ws.length) {
    const pfC = filt('pickc');
    const _tn2 = tagNameDict();
    const pTags = (pfC.tags || []).map(id => _tn2[id]).filter(Boolean);
    const pSerM = p => !(pfC.series || []).length || (pfC.series || []).map(x => String(x)).includes(String(charSeriesMap()[String(p.series_set_id)]));
    const pTagM = p => {
      if (!pTags.length) return true;
      const ts = charMetaOf(p.id).tags;   // 驾驶员标签名集合
      return pfC.mode === 'or' ? pTags.some(n => ts.has(n)) : pTags.every(n => ts.has(n));
    };
    const pOk = p => {
      if (c.pRar && p.rarity !== c.pRar) return false;      // 页面行: 驾驶员稀有度
      if (pfC.rar && p.rarity !== pfC.rar) return false;    // 弹窗: 稀有度
      if (pfC.role && p.role !== pfC.role) return false;    // 弹窗: 类型(攻击/防御/支援型)
      if (pTags.length && (pfC.series || []).length && pfC.mode === 'or') return pTagM(p) || pSerM(p);   // 任一命中: 标签或系列
      return pTagM(p) && pSerM(p);
    };
    const pkey = [u.id, c.lv, c.vigor, c.crit ? 1 : 0, c.passive ? 1 : 0, c.cpassive ? 1 : 0, c.skills ? 1 : 0, c.first ? 1 : 0, c.fdth ? 1 : 0, c.mp ? 1 : 0, c.ca ? 1 : 0, c.star ? 1 : 0, c.s3u !== false ? 1 : 0, c.spU !== false ? 1 : 0, c.ssp ? 1 : 0, tDef, c.tCharDef ?? 750, c.pRar || 0, pfC.role || 0, pfC.rar || 0, (pfC.series || []).join(','), (pfC.tags || []).join(','), pfC.mode || 'and', c.pSpU !== false ? 1 : 0, state.supAct !== false ? 1 : 0, state.maxOn ? 1 : 0, state.ultLv || 0, JSON.stringify(state.ultSkill)].join('|');
    if (state._prKey === pkey) pilotRows = state._prRows;
    else {
      const meta = metaOf(u.id);
      const sdMap = sdCharMap();
      const cands = isSDUnit
        ? (sdOwn ? [sdOwn] : [])
        : q('SELECT id,name,icon,rarity,role,series_set_id,max_melee,max_ranged,max_awaken,sp_max_melee,sp_max_ranged,sp_max_awaken FROM characters WHERE COALESCE(is_playable,1)=1')
            .filter(p => { const owned = sdMap[p.id]; return !owned || owned.has(u.id); })     // SD绑定驾驶员不能驾驶其他机体
            .filter(pOk);                                                                      // 标签/系列/稀有度/类型筛选
      const traitsByW = {};
      for (const w of ws) traitsByW[w.id] = wTraitsOf(w, null, c.ca);
      for (const p of cands) {
        const mp0 = mpOf(u.id, p.id, c.first ? false : c.skills, c.ca, c.pSpU, sspOn);   // 被动MP: 首动MP提升释放条件用
        const mp = c.vigor === 'default' ? mp0 : 0;
        let vg = c.vigor === 'default' ? mpToVigor(mp) : c.vigor;
        const faRows = c.first ? charActSkillRows(p.id, c.pSpU !== false) : null;
        const faT = c.first ? firstActOfRows(faRows, null, c.fdth, mp0) : null;
        if (faT && faT.k === 'mp') vg = 'supercharged';   // 首动MP技 → 超一击(＋30%)
        const b = charBonus(p.id, vg, { passive: c.cpassive, cpassive: c.cpassive, skills: (c.first ? false : c.skills), condAll: c.ca, first: c.first, unitId: u.id, upassive: c.passive, multiPhase: c.mp, pSpU: c.pSpU !== false, ussp: sspOn }, meta);
        const uAtkP = Math.floor(uBase * (1 + ((c.passive ? unitPassiveAtkPct(u.id, vg, c.ca, null, sspOn, c.first) : 0) + (state.uSk !== false ? unitSkillAtkPct(u.id) : 0) + (b.atk || 0)) / 100));
        let best = null;
        for (const w of ws) {
          if (!vigorAllows(w.id, vg, c.vigor === 'default' ? mp : null)) continue;   // 气势/MP 条件不足时不能使用
          const attrs = WATTR[w.attack_attr] || ['melee'];
          const faW = faRows ? firstActOfRows(faRows, attrs, c.fdth, mp0) : null;
          const statAdd = (faW && faW.k === 'stat') ? faW.v : 0;
          const ee0 = b.dmg + (faW && faW.k === 'burst' ? faW.v : 0) + ultDmgPct(u);
          let statA = attrs[0], cAtk = -1;
          for (const a of attrs) { const val = Math.floor(pStat(p, a, c.pSpU) * (1 + ((b[a] || 0) + (faW && faW.k === 'stat' && faW.stat === a ? statAdd : 0)) / 100)); if (val > cAtk) { cAtk = val; statA = a; } }
          const ci = critInfo(u.id, p.id, w, meta, { upassive: c.passive, cpassive: c.cpassive, skills: (c.first ? false : c.skills), condAll: c.ca, vigor: vg, multiPhase: c.mp, pSpU: c.pSpU !== false, ussp: sspOn });
          const critOn = canCrit(ci) && (c.crit || ci.guar || ci.rate >= 100);   // 暴击率100%/必暴: 无视开关按暴击计算
          const d = Engine.damageWithWeapon(uAtkP, cAtk, w, traitsByW[w.id] || [], c.lv, tDef, c.tCharDef ?? 750,
            { vigor: vg, crit: critOn, ee: ee0, critDmgAdd: critOn ? ci.cdmg : 0 });
          if (!best || d.final > best.dmg) best = { dmg: d.final, weapon: w, stat: statA, cAtk, pstat: (b[statA] || 0),   // 含被动=仅被动(首动值增幅单列)
            patk: (b.atk || 0), pdmg: b.dmg, vigor: vg, mp, fa: faW, forceCrit: (ci.guar || ci.rate >= 100),
            notice: enemyCondNotes(u.id, p.id, { upassive: c.passive, passive: c.cpassive, pSpU: c.pSpU !== false, condAll: c.ca, enemyMeta: null }, sspOn, w).labels.join('/') };
        }
        if (best) { best.sup = supCountsOf(p.id, u.id, vg, c.ca, c.pSpU !== false); pilotRows.push(Object.assign({ id: p.id, name: p.name, icon: p.icon, rarity: p.rarity, role: p.role }, best)); }
      }
      pilotRows.sort((x, y) => y.dmg - x.dmg);
      state._prKey = pkey; state._prRows = pilotRows;
    }
  }
  const tCharDefShown = ' / 守备 ' + fmt(c.tCharDef ?? 750);
  /* 对特定标签目标(敌方条件)生效的被动注明: 机体+机师 (计算页无对手选择 → 按条件全开口径列出) */
  const ecU = (u && c.passive) ? enemyCondNotes(u.id, null, { upassive: true, condAll: c.ca }, sspOn) : { labels: [], detail: [] };
  const ecC = (u && ch && c.cpassive) ? enemyCondNotes(null, ch.id, { passive: true, pSpU: c.pSpU !== false, condAll: c.ca }, sspOn) : { labels: [], detail: [] };
  const ecW = (rows && rows.length && c.ca) ? enemyCondNotes(null, null, { condAll: true }, sspOn, rows[0].w) : { labels: [], detail: [] };
  const ecDet = ecU.detail.concat(ecC.detail, ecW.detail);
  v.innerHTML = `
    <div class="card" style="padding:9px 12px; display:flex; gap:9px; align-items:center; cursor:pointer" id="picku">
      ${u ? avTagR(u.icon, u.role, u.rarity) : '<span style="width:38px;height:38px;border-radius:8px;background:#0c1424;display:inline-block"></span>'}
      <div style="flex:1; font-size:12.5px">${u ? esc(u.name) : '选择机体'} <span style="color:var(--dim)">+</span> ${ch ? esc(ch.name) : '选择驾驶员'}
        ${u ? `<br><small style="color:var(--dim);font-size:10.5px">攻击 ${fmt(uAtk)}（${c.star ? 'SP×3星' : 'Lv100'}${uPctP ? ' · 被动+'+uPctP+'%'+(ecU.labels.length ? '<span style="color:#f5c451">（条件:'+ecU.labels.join('/')+'）</span>' : '') : ''}${uPctS ? ' · 单位技能+'+uPctS+'%' : ''}${cBonus.atk ? ' · 驾驶员攻击+'+cBonus.atk+'%'+(ecC.labels.length ? '<span style="color:#f5c451">（条件:'+ecC.labels.join('/')+'）</span>' : '') : ''}）${ch ? ' · 机师攻击 ' + fmt(rows[0] ? rows[0].cAtk : 0) : ''}${supCountsTxt(cSup) ? ' · ' + supCountsTxt(cSup) : ''}</small>` : ''}</div>
      <span style="color:var(--dim)">▾</span>
    </div>
    ${isSDUnit ? `<div class="subnote" style="text-align:left">⚠ SD高达机体不能换乘${sdOwn ? `：专属驾驶员 ${esc(sdOwn.name)}${ch && ch.id !== sdOwn.id ? `（当前所选 ${esc(ch.name)} 非专属，结果仅供参考）` : ''}` : '（未找到同名专属驾驶员）'}</div>` : ''}
    <div class="chips">
      <span class="chip ${c.crit ? 'on' : ''}" id="crit">暴击${c.crit ? (rows.length && !rows[0].canCrit ? ' 开·无暴击' : ' 开') : ' 关'}</span>
      ${ssrBelow ? `<span class="chip ${uS3 ? 'on' : ''}" id="cal3">三星${uS3 ? ' 开' : ' 关'}</span>
      <span class="chip ${uSp ? 'gold' : ''}" id="casp">SP强化上限${uSp ? ' 开' : ' 关'}</span>` : `<span class="chip ${c.star ? 'on' : ''}" id="star">★3突破${c.star ? ' 开' : ' 关'}</span>`}
      <span class="chip ${sspOn ? 'gold' : ''}" id="ssp">SSP满10</span>
      <span class="chip ${c.pSpU !== false ? 'gold' : ''}" id="cpspu">驾驶员SP${c.pSpU !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${c.passive ? 'on' : ''}" id="passive">机体被动${uPct ? ' +' + uPct + '%' : (c.passive ? ' 开' : ' 关')}</span>
      <span class="chip ${c.cpassive ? 'on' : ''}" id="cpassive">驾驶员被动 ${cpassiveTxt}</span>
      <span class="chip ${c.skills ? 'gold' : ''}" id="skills">主动技能 ${skillsTxt}</span>
      <span class="chip ${c.first ? 'gold' : ''}" id="cfirst" title="竞技场AI首动(官方优先度): 每动只放1个技能 — 减伤(威力抵御)>+MP>+命中闪避(会被反死)>攻击爆裂>摇摆闪避>增幅(对应属性武装)>爆击增幅>保留EN; 假设满血满EN·够得着·命中充足(射程/移动/HP修复/必中跳过); 首动MP技=超一击+30%">首动${c.first ? ' 开' : ' 关'}${c.first && ch ? (() => { const lb = faShow && faShow.name ? faShow.name.replace(/ LV\d+/, '') : '无自动技'; return ' · 首动:' + lb + (faShow && (faShow.k === 'burst' || faShow.k === 'stat') ? ' +' + faShow.v + '%' : '') + (faShow && faShow.k === 'mp' ? '(超一击)' : ''); })() : ''}</span>
      ${c.first ? `<span class="chip ${c.fdth ? 'gold' : ''}" id="cfdth" title="开: 假设『会被反击杀死』条件成立 — 「命中率·闪避率提升」(图序在爆裂前)会挤掉攻击爆裂; 「摇摆闪避」(在爆裂后)不影响首动伤害">反死风险${c.fdth ? ' 开' : ' 关'}</span>` : ''}
      <span class="chip ${c.mp ? 'gold' : ''}" id="mp" ${c.first ? 'style="opacity:.45"' : ''} title="${c.first ? '首动模式下不可开启(多阶段增益=超一击EX赋予)' : '多阶段增益: 超一击时EX1/EX2赋予'}">多阶段增益${c.mp ? ' 开' : ' 关'}</span>
      <span class="chip ${c.ca ? 'gold' : ''}" id="ca" title="开: 假设 HP/标签/战意等条件被动满足(支援攻击/支援反击/反击另有开关); 关: 按普通攻击如实判定">条件被动${c.ca ? ' 开·假设满足' : ' 关·如实判定'}</span>
      <span class="chip ${state.supAct !== false ? 'gold' : ''}" id="csupact" title="开: 计入「支援攻击/支援反击/反击时」机体/驾驶员被动; 关: 按普通攻击不计入">支援攻击/反击${state.supAct !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${state.maxOn ? 'gold' : ''}" id="cmax" title="开: 条件型叠层被动按最高N%满层(含部队每有/对战次数等); 关: 条件被动按1层; 首动攻击次数型恒0层">max${state.maxOn ? ' 满层' : ' 1层'}</span>
      <span class="chip ${state.uSk !== false ? 'gold' : ''}" id="cusk" title="机体技能(单位技能, 如 攻击力提升25%(1回合))是否计入伤害 — 独立于驾驶员主动技能">机体技能${state.uSk !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${state.ultLv ? 'gold' : ''}" id="curd" title="ULT改造: 0/50/100级; ≥50解锁ULT武器, 100解锁三选一能力">ULT改造${state.ultLv ? ' Lv' + state.ultLv : ' 关'}</span>
    </div>
    <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">驾驶员稀有度:</span>
      ${[['all', '全部'], [1, 'N'], [2, 'R'], [3, 'SR'], [4, 'SSR'], [5, 'UR']].map(([k, l]) =>
        `<span class="chip ${(c.pRar || 'all') === k ? 'on' : ''}" data-prar="${k}">${l}</span>`).join('')}
      <span class="fbtn" id="cpser">☰ 驾驶员系列 <b>${(filt('pickc').series || []).length || ''}</b></span>
    </div>
    <div class="chips">
      <span class="hint" style="align-self:center">靶防御:</span>
      ${[['低防', 10000], ['中防', 20000], ['高防', 40000]].map(([l, val]) => `<span class="chip ${tDef === val ? 'on' : ''}" data-tdef="${val}">${l} ${val / 1000}k</span>`).join('')}
      <input id="tdef2" type="number" value="${tDef}" style="width:76px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">
      <span class="hint" style="align-self:center">靶守备</span>
      <input id="tcdef2" type="number" value="${c.tCharDef ?? 750}" style="width:60px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">
    </div>
    <div class="chips">
      ${[['default', '默认·按MP'], ['mid', '无气势'], ['high', '强势'], ['max', '超强势'], ['supercharged', '超一击']].map(([k, l]) =>
        `<span class="chip ${c.vigor === k ? 'gold' : ''}" data-vg="${k}">${l}</span>`).join('')}
      <span class="chip on">气势 ${vigor.label}${(c.vigor === 'default' && autoMP) ? '(MP' + autoMP + ')' : ''} · 增伤+${vigor.rate}% · 暴击补正 ${c.crit ? '+' + vigor.crit : '关'}</span>
    </div>
    <div class="card" style="padding:6px 10px">
      ${hiddenN ? `<div class="subnote" style="text-align:left;margin-bottom:4px">已隐藏 ${hiddenN} 把「战意/MP 条件」限定武器（当前：${vigor.label}${autoMP != null ? ' · MP' + autoMP : ''}）</div>` : ''}
      <table class="ctable"><tr><th style="text-align:left">武器 / 射程</th>${cols.map(([l]) => `<th>${l}</th>`).join('')}</tr>
      ${rows.map(({ w, dmgs, ci }) => {
        const best = Math.max(...dmgs);
        const wnot = c.ca ? enemyCondNotes(null, null, { condAll: true }, sspOn, w).labels.join('/') : '';
        return `<tr class="${dmgs[1] === best ? 'best' : ''}" data-wid="${w.id}" style="cursor:pointer"><td class="l">${esc(w.name)}${AATTR[w.weapon_attr] ? ' <span class="wattr a' + (w.weapon_attr || 0) + '">' + AATTR[w.weapon_attr] + '</span>' : ''} <span style="color:var(--dim);font-size:10px">${w.range_min}-${w.range_max}${w.type === 3 ? '·MAP' : ''}</span>${(ci.guar || ci.rate >= 100) ? ' <span style="color:#7df0a8;font-weight:700;font-size:10px">必暴</span>' : ''}${wnot ? ' <span style="color:#f5c451;font-size:10px">条件:' + esc(wnot) + '</span>' : ''}</td>
        ${dmgs.map(d => `<td class="v ${d === best ? 'hot' : ''}">${fmt(d)}</td>`).join('')}</tr>`; }).join('') || '<tr><td class="l" colspan="4" style="color:var(--dim)">请选择机体与驾驶员</td></tr>'}
      </table>
    </div>
    ${pilotRows.length ? `<div class="card"><h4>驾驶员伤害 TOP${Math.min(10, pilotRows.length)} · ${esc(u.name)}（${c.vigor === 'default' ? '默认战意·按MP' : Engine.VIGOR[c.vigor].label} · 靶 ${tDef >= 1000 ? (Math.round(tDef / 1000)) + 'k' : fmt(tDef)}${c.crit ? ' · 暴击开' : ''}${isSDUnit ? ' · SD专属' : ''}）</h4>
      ${pilotRows.slice(0, 10).map((r, i) => `<div class="trow" data-pid="${r.id}"><span class="rk ${i < 3 ? 'g' : ''}">${i + 1}</span>${avDrv(r.icon, r.role, r.rarity)}
        <div class="nm">${esc(r.name)} ${rarTag(r.rarity)} ${ch && ch.id === r.id ? '<span style="color:#7df0a8;font-size:10px">当前</span>' : ''}<small>${STATNAME[r.stat]} ${r.cAtk}${r.pstat ? ' 含被动+' + r.pstat + '%' : ''}${r.fa && r.fa.k === 'stat' ? '·首动+' + r.fa.v + '%' : ''}${r.patk ? ' 攻击+' + r.patk + '%' : ''} · <span style="color:#f5c451">${Engine.VIGOR[r.vigor].label}${c.vigor === 'default' ? '(' + (r.mp || 0) + ')' : ''}</span> · ${esc(r.weapon.name)}${r.forceCrit ? ' <span style="color:#7df0a8;font-weight:700">必暴</span>' : ''}${r.notice ? ' · <span style="color:#f5c451">条件:' + esc(r.notice) + '</span>' : ''}${supCountsBadge(r.sup)}</small></div>
        <span style="text-align:right;white-space:nowrap"><span class="val g">${fmt(r.dmg)}</span><div style="margin-top:2px;display:flex;gap:6px;justify-content:flex-end"><span class="fbtn" data-csel="${r.id}" style="padding:2px 10px;font-size:10.5px">选择</span><span class="fbtn" data-cdet="${r.id}" style="padding:2px 10px;font-size:10.5px">详情</span></div></span></div>`).join('')}
      <div class="subnote" style="text-align:left">点击「选择」选用驾驶员，「详情」查看驾驶员图鉴</div></div>` : ''}
    ${rows.length ? `<div class="card"><h4>公式明细 · ${esc(rows[0].w.name)}（靶 ${fmt(tDef)}${tCharDefShown}）</h4><div class="kv" id="detail"></div></div>` : ''}`;
  if (rows.length) {
    const { w, cAtk } = rows[0];
    const traits = wTraitsOf(w, null, c.ca);
    const det = Engine.damageWithWeapon(uAtk, cAtk, w, traits, c.lv, tDef, c.tCharDef ?? 750,
      { vigor: eVigor, crit: rows[0].critOn, ee: cBonus.dmg, critDmgAdd: rows[0].critOn ? rows[0].ci.cdmg : 0 });
    const eeTot = vigor.rate + cBonus.dmg + (det.critDmg || 0);
    $('detail').innerHTML = `威力 <b>${fmt(Engine.weaponPower(rows[0].w, c.lv))}</b>${det.powerPct ? ' → 修正威力 <b>' + fmt(det.effPower) + '</b>（效果+' + det.powerPct + '%）' : ''}<br>基础 <b>${fmt(det.base)}</b> × 修正系数 <b>${det.corrFactor}</b> → 战斗值 <b>${fmt(det.battle)}</b><br>
      增伤 +${eeTot}%（${vigor.label}${vigor.rate}${cBonus.dmg ? ' · 驾驶员+' + cBonus.dmg : ''}${det.critDmg ? ' · 暴击损伤+' + det.critDmg : ''}）${rows[0].critOn ? ' · 暴击 ×' + ((vigor.crit + 100) / 100).toFixed(2) : ''} → <span style="color:#7df0a8;font-weight:700">最终 ${fmt(det.final)}</span>
      ${c.crit ? (rows[0].canCrit ? `<br><span style="color:var(--dim)">暴击能力: 武器${w.crit_rate || 0}%${rows[0].ci.guar ? ' · 必定暴击' : (rows[0].ci.rate !== (w.crit_rate || 0) ? ' · 含被动技能+至' + rows[0].ci.rate + '%' : '')}${(!rows[0].ci.guar && rows[0].ci.rate >= 100) ? ' · <span style="color:#7df0a8">必暴</span>' : ''}</span>` : '<br><span style="color:#ff9f43">该武器/机师无暴击能力 → 暴击开关不生效</span>') : (rows.some(rw => rw.ci.guar || rw.ci.rate >= 100) ? '<br><span style="color:#7df0a8">含暴击率100%/必暴武器 → 自动按暴击计算</span>' : '')}
      ${(() => { const gs = grantedTraits(u.id, ch ? ch.id : null, uMeta, { cpassive: c.cpassive, upassive: c.passive, multiPhase: c.mp, condAll: c.ca, vigor: eVigor, ussp: sspOn }).map(grantTxt).filter(Boolean);
        return gs.length ? `<br><span style="color:#f5c451">多阶段增益(EX${c.mp ? 2 : 1}) 赋予: ${gs.join(' · ')}</span>` : ''; })()}${ecDet.length ? `<br><span style="color:#f5c451">对特定对手生效的加成(已计入): ${ecDet.join(' · ')}</span>` : ''}`;
  }
  $('picku').onclick = () => openCalcPicker();
  v.querySelectorAll('[data-csel]').forEach(el => el.onclick = (ev) => { ev.stopPropagation(); c.charId = +el.dataset.csel; render(); });
  v.querySelectorAll('[data-cdet]').forEach(el => el.onclick = (ev) => { ev.stopPropagation(); const id = +el.dataset.cdet; const cc = q1('SELECT name FROM characters WHERE id=?', [id]); push({ page: 'char', title: cc ? cc.name : '', id }); });
  v.querySelectorAll('table.ctable tr[data-wid]').forEach(tr => tr.onclick = () => { const id = +tr.dataset.wid; const ww = q1('SELECT name FROM weapons WHERE id=?', [id]); push({ page: 'weapon', title: ww ? ww.name : '', id }); });
  v.querySelectorAll('[data-vg]').forEach(el => el.onclick = () => { c.vigor = el.dataset.vg; render(); });
  $('crit').onclick = () => { c.crit = !c.crit; render(); };
  if ($('cal3')) $('cal3').onclick = () => { c.s3u = !(c.s3u !== false); if (!(c.s3u !== false)) c.ssp = false; render(); };
  if ($('casp')) $('casp').onclick = () => { c.spU = !(c.spU !== false); if (!(c.spU !== false)) c.ssp = false; render(); };
  if ($('star')) $('star').onclick = () => { c.star = !c.star; if (!c.star) c.ssp = false; render(); };
  $('ssp').onclick = () => { c.ssp = !c.ssp; if (c.ssp) { c.s3u = true; c.spU = true; c.star = true; } render(); };
  if ($('cpspu')) $('cpspu').onclick = () => { c.pSpU = !(c.pSpU !== false); render(); };
  $('passive').onclick = () => { c.passive = !c.passive; render(); };
  $('cpassive').onclick = () => { c.cpassive = !c.cpassive; render(); };
  $('skills').onclick = () => { c.skills = !c.skills; if (c.skills) c.first = false; render(); };   // 主动技能 ⇄ 首动 二选一
  $('cfirst').onclick = () => { c.first = !c.first; if (c.first) { c.skills = false; c.mp = false; } render(); };   // 首动: 关主动技能/多段增益
  if ($('cfdth')) $('cfdth').onclick = () => { c.fdth = !c.fdth; render(); };
  $('mp').onclick = () => { if (c.first) return; c.mp = !c.mp; render(); };   // 首动模式下不可开多段增益
  $('ca').onclick = () => { c.ca = !c.ca; render(); };
  $('csupact').onclick = () => { state.supAct = !(state.supAct !== false); render(); };
  $('cmax').onclick = () => { state.maxOn = !state.maxOn; render(); };
  if ($('cusk')) $('cusk').onclick = () => { state.uSk = !(state.uSk !== false); render(); };
  if ($('curd')) $('curd').onclick = () => openUltSheet();
  if ($('tcdef2')) $('tcdef2').onchange = () => { c.tCharDef = +$('tcdef2').value || 0; render(); };
  v.querySelectorAll('[data-prar]').forEach(el => el.onclick = () => { c.pRar = el.dataset.prar === 'all' ? null : +el.dataset.prar; render(); });
  if ($('cpser')) $('cpser').onclick = () => openTagPicker('pickc', () => render());
  v.querySelectorAll('[data-tdef]').forEach(el => el.onclick = () => { c.tDef = +el.dataset.tdef; render(); });
  if ($('tdef2')) $('tdef2').onchange = () => { c.tDef = +$('tdef2').value || 0; render(); };
}

function pickSheet(title, listHtml, onBind, searchFn, headHtml = '') {
  const panel = $('sheetPanel');
  panel.innerHTML = `<div class="sheet-h"><b>${esc(title)}</b><span class="x" id="sx">✕</span></div>
    ${headHtml}
    <div class="search">🔍 <input id="pk" placeholder="搜索…"></div>
    <div class="tlist" id="pkl">${listHtml}</div>`;
  $('sx').onclick = closeSheet;
  onBind(panel);
  $('pk').oninput = e => { const rows = searchFn(e.target.value); $('pkl').innerHTML = rows; onBind(panel); };
  $('sheet').classList.add('open');
}
/* 选择器列表条件(标签+系列): picku=机体 / pickc=驾驶员 */
function pickWhere(which, s) {
  const pf = filt(which === 'unit' ? 'picku' : 'pickc');
  const conds = [], args = [];
  if (pf.tags.length) {
    const tc = tagClause(which, pf, 'id', which === 'unit' ? 'unit_tags' : 'char_tags', which === 'unit' ? 'unit_id' : 'char_id');
    if (tc.sql) { conds.push(tc.sql); args.push(...tc.args); }
  }
  const serCl = (pf.series || []).length
    ? (which === 'unit' ? `series_id IN (${pf.series.map(() => '?').join(',')})`
                        : `series_set_id IN (SELECT series_set_id FROM units WHERE series_id IN (${pf.series.map(() => '?').join(',')}))`)
    : '';
  if (serCl && pf.tags.length && pf.mode === 'or') {        // 并行: 标签任一 或 系列
    const head = conds.pop();                                // 移除已推入的标签条件, 合并为 OR
    const headArgs = args.splice(args.length - pf.tags.length - (conds.length ? 0 : 0), pf.tags.length);
    conds.push(`((${head.replace(/=\?$/, '')}) OR ${serCl})`);
    args.push(...headArgs, ...pf.series);
  } else if (serCl) {
    conds.push(serCl); args.push(...pf.series);
  }
  if (pf.rar) { conds.push('rarity=?'); args.push(pf.rar); }
  if (pf.role) { conds.push('role=?'); args.push(pf.role); }
  if (s) { const nu = nameLikeSql('name', s); conds.push(nu.sql); args.push(...nu.args); }
  return { where: conds.length ? 'WHERE ' + conds.join(' AND ') : '', args };
}
function pickHeadHtml(which) {          // 选择器头部: 标签/系列筛选 + 排序 按钮行
  const pf = filt(which === 'unit' ? 'picku' : 'pickc');
  const ctx = which === 'unit' ? 'picku' : 'pickc';
  return `<div class="fbar">
    <span class="fbtn" id="pfil">☰ 标签/系列 <b>${(pf.tags.length + ((pf.series || []).length)) || ''}</b></span>
    <span class="fbtn" id="psort">↕ ${esc(sortLabel(ctx))}</span></div>`;
}
function bindPickHead(panel, which, reopen) {
  panel.querySelectorAll('#pfil').forEach(el => el.onclick = () => { _sheetBack = reopen; openTagPicker(which === 'unit' ? 'picku' : 'pickc', null); });
  panel.querySelectorAll('#psort').forEach(el => el.onclick = () => { _sheetBack = reopen; openSortPicker(which === 'unit' ? 'picku' : 'pickc', null); });
}
function openCalcPicker() {
  const f = { which: state.calcPickWhich || 'unit' };
  const drawList = (s) => {
    const pw = pickWhere(f.which, s);
    return f.which === 'unit'
      ? q(`SELECT id,name,icon,role,rarity FROM units ${pw.where} ${sortOrder('picku', '')} LIMIT 60`, pw.args).map(u =>
          `<div class="trow2" data-pick="${u.id}">${avTagR(u.icon, u.role, u.rarity, 'x')}<span style="flex:1">${esc(u.name)} ${rarTag(u.rarity)}${ultB(u)}</span><span class="c">${ROLE[u.role].n}</span></div>`).join('')
      : q(`SELECT id,name,icon,role,rarity,max_melee,max_ranged,max_awaken,sp_max_melee,sp_max_ranged,sp_max_awaken FROM characters ${pw.where} ${sortOrder('pickc', '', null, state.calc.pSpU !== false)} LIMIT 200`, pw.args).filter(c => pilotCanDrive(c.id, state.calc.unitId)).slice(0, 60).map(c =>
          `<div class="trow2" data-pickc="${c.id}">${avDrv(c.icon, c.role, c.rarity, 'x')}<span style="flex:1">${esc(c.name)} ${rarTag(c.rarity)}</span><span class="c">格${pStat(c, 'melee', state.calc.pSpU)} 射${pStat(c, 'ranged', state.calc.pSpU)}</span></div>`).join('');
  };
  const open = () => {
    pickSheet('选择机体 / 驾驶员', `<div id="pklist">${drawList('')}</div>`, (panel) => {
      const bind = () => {
        panel.querySelectorAll('[data-pick]').forEach(el => el.onclick = () => { state.calc.unitId = +el.dataset.pick; closeSheet(); const w = q1('SELECT * FROM weapons WHERE unit_id=? LIMIT 1', [state.calc.unitId]); render(); });
        panel.querySelectorAll('[data-pickc]').forEach(el => el.onclick = () => { state.calc.charId = +el.dataset.pickc; closeSheet(); render(); });
        panel.querySelectorAll('#wunit,#wchar').forEach(el => el.onclick = () => { f.which = el.id === 'wunit' ? 'unit' : 'char'; state.calcPickWhich = f.which; open(); });
        bindPickHead(panel, f.which, open);
      };
      const redraw = () => { $('pkl').innerHTML = drawList($('pk').value || ''); bind(); };
      bind();
    }, s => drawList(s), `<div class="btnrow"><span class="bs" id="wunit">机体</span><span class="bs" id="wchar">驾驶员</span></div>${pickHeadHtml(f.which)}`);
  };
  open();
}

/* SD高达机体专属驾驶员（同名角色; 去 (EX)/（…） 后缀再试） */
/* SSP满强化加成（ssp_config.stats）: 满10=中点 b+(m−b)/2 (网站实证: 229→4577 得 2403; 加在★倍率之前) */
let _sspGC = {};    // 性能: ssp_json 解析/计算缓存(每机体每lv一次)
function sspGainOf(u, lv) {
  const _k = u.id + '|' + (lv || 10);
  const _hit = _sspGC[_k];
  if (_hit) return _hit;
  let st = {};
  try { st = (JSON.parse(u.ssp_json || '{}').stats) || {}; } catch (e) {}
  const K = (b, m) => Math.floor((b || 0) + (((m || 0) - (b || 0)) * (lv || 10) / 20));
  return (_sspGC[_k] = {
    atk: K(st.ssp_attack, st.ssp_max_attack),
    hp: K(st.ssp_hp, st.ssp_max_hp),
    en: K(st.ssp_en, st.ssp_max_en),
    def: K(st.ssp_defense, st.ssp_max_defense),
    mob: K(st.ssp_mobility, st.ssp_max_mobility),
  });
}
/* 改装核心(SSP满10)武器强化: 核心(level≤10)与initial_release的 weapon_enhance
   参考站口径(chunks_2UCe/nodes_8): 1=威力平加(power=floor(lv%×基础)+Σ) / 2=EN减 / 3=弹药+ / 4=最大射程+ */
let _sspWMod = {};
function sspWeaponMods(u) {
  if (!u) return null;
  if (_sspWMod[u.id]) return _sspWMod[u.id];
  let d = {}; try { d = JSON.parse(u.ssp_json || '{}') || {}; } catch (e) {}
  const out = {};
  const take = rel => {
    const e = (rel || {}).weapon_enhance;
    if (!e || !e.target_weapon_id) return;
    const m = out[e.target_weapon_id] = out[e.target_weapon_id] || { pa: 0, em: 0, ammo: 0, rng: 0 };
    if (e.weapon_enhance_type_index === 1) m.pa += e.effect_value || 0;
    else if (e.weapon_enhance_type_index === 2) m.em += e.effect_value || 0;
    else if (e.weapon_enhance_type_index === 3) m.ammo += e.effect_value || 0;
    else if (e.weapon_enhance_type_index === 4) m.rng += e.effect_value || 0;
  };
  if (d.initial_release) take(d.initial_release);
  for (const c of (d.cores || [])) if ((c.level ?? 0) <= 10) for (const rel of (c.releases || [])) take(rel);   // 满10 = 核心level≤10
  _sspWMod[u.id] = out;
  return out;
}
/* ------------ 武器效果摘要(增伤/降防, 供组队行显示) ------------
   数值叠层: 基础(fx) + 驾驶员「武装效果值增加N%」(trait88, 同能力行文案含作用范围, 支持镭射≡光束) + SSP核心 weapon_effect(88) */
let _fxUpC = null;
function charFxUpsOf(charId, spOn) {   // 驾驶员88: 按(范围/条件)过滤 → [{scope, v, tensionReq, reqTags, reqSeries, reqUnits}]
  if (!_fxUpC) {
    _fxUpC = { base: {}, sp: {} };
    const parse = (rows, tgt) => {
      for (const r of rows) {
        let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        const trs = ts.map(t => (t || {}).trait || {});
        const has88 = trs.some(t => t.trait_type === 88);
        if (!has88) continue;
        const text = trs.map(t => t.desc || '').join(' ');
        if (text.indexOf('武装效果值增加') < 0) continue;
        let scope = null;
        if (/受到的特殊损伤提升/.test(text) || /特殊武装攻击/.test(text)) scope = '特殊';
        else if (/镭射|光束/.test(text)) scope = '光束';
        else if (/物理/.test(text)) scope = '物理';
        else if (/防御力减少/.test(text)) scope = '降防';
        for (const t88 of trs.filter(t => t.trait_type === 88 && t.trait_value < 0)) {
          const ac = t88.active_condition || {};
          const cq = condTagsOf(ac);
          let tensionReq = 0;
          if (ac.tension) { const _rs = String(ac.tension).split(',').map(x => TENSION_RANK[x.trim()] || 0).filter(Boolean); if (_rs.length) tensionReq = Math.min(..._rs); }   // 「超强势以上」编码为档位集合 → 阈值取最低档
          (tgt[r.char_id] = tgt[r.char_id] || []).push({ sort: r.sort || 0, scope, v: -t88.trait_value, tensionReq, reqTags: cq.tags, reqSeries: cq.series, reqUnits: cq.units });
        }
      }
    };
    parse(q('SELECT char_id, sort, traits_json FROM char_abilities'), _fxUpC.base);
    parse(q('SELECT char_id, sort, traits_json FROM char_abilities_sp'), _fxUpC.sp);
  }
  return mergeSp(_fxUpC.base[charId] || [], spOn === false ? null : (_fxUpC.sp[charId] || []));
}
function weaponFxCompactOf(w, charId, unit, sspOn, spOn, opts) {   // 武器全部特效摘要(简化词; 含驾驶员88/SSP叠加)
  if (!w) return '';
  const ents = [];   // {t:'attr'|'def',scope,v} | {t:'up',scope,s,when} | {t:'tok',s} — 按 fx sort 保序
  for (const f of q('SELECT sort, name, desc FROM weapon_fx WHERE weapon_id=? AND level=5 ORDER BY sort', [w.id])) {
    if (/发起对战的敌方包含/.test(String(f.desc || ''))) {   // 敌方条件特效: 指定对手按标签匹配; 通用时按条件被动开关(开=全部生效)
      const cr = _wtRowsOf(w.id).filter(x => x.cq);
      const ok = cr.length ? cr.some(x => _wCondOk(x.cq, opts && opts.enemyMeta, opts && opts.condAll)) : !(opts && opts.condAll === false);
      if (!ok) continue;
    }
    const sh = fxShort(f.name, f.desc);
    if (!sh) continue;
    let m = sh.match(/^(光束|物理|特殊|全属性)-(\d+)%$/);
    if (m) { ents.push({ t: 'attr', scope: m[1], v: +m[2] }); continue; }
    m = sh.match(/^(贯穿降防|降防)(\d+)%$/);
    if (m) { ents.push({ t: 'def', scope: '降防', v: +m[2] }); continue; }
    if (sh.indexOf('武装效果UP·') === 0) {   // SSP/固有修饰行: 数值已并入同名效果时不再单列
      m = sh.match(/^武装效果UP·(降防|光束|物理|特殊)[+-]\d+%$/);
      ents.push({ t: 'up', scope: m ? m[1] : null, s: sh, when: f.sort === 91 || sspOn || !!w.is_ssp });
      continue;
    }
    if (!ents.some(en => en.t === 'tok' && en.s === sh)) ents.push({ t: 'tok', s: sh });
  }
  for (const e of q('SELECT trait_type, trait_value, cond, effect_name FROM weapon_traits WHERE weapon_id=? AND level=5', [w.id])) {   // fx缺失兜底(14/9)
    if (e.cond) { let cq = null; try { cq = condTagsOf(JSON.parse(e.cond)); } catch (err) { cq = null; }
      if (cq && !_wCondOk(cq, opts && opts.enemyMeta, opts && opts.condAll)) continue; }
    if (e.trait_type === 14 && e.trait_value < 0 && !ents.some(en => en.t === 'attr' && en.v === -e.trait_value)) {
      const en = String(e.effect_name || '');
      const sc = /光束/.test(en) ? '光束' : (/特殊/.test(en) ? '特殊' : (/物理/.test(en) ? '物理' : (AATTR[w.weapon_attr] || '光束')));
      ents.push({ t: 'attr', scope: sc, v: -e.trait_value });
    }
    if (e.trait_type === 9 && e.trait_value < 0 && !ents.some(en => en.t === 'def' && en.v === -e.trait_value)) ents.push({ t: 'def', scope: '降防', v: -e.trait_value });
  }
  if (!ents.length) return '';
  /* 叠驾驶员88(条件按当前机体/战意判定) */
  const meta = unit ? metaOf(unit.id || unit) : null;
  for (const p of charFxUpsOf(charId, spOn)) {
    if (!condOk(p, meta, { condAll: opts && opts.condAll, vigor: opts && opts.vigor })) continue;
    for (const en of ents) if ((en.t === 'attr' || en.t === 'def') && (p.scope === en.scope || p.scope === null)) en.v += p.v;
  }
  /* 叠SSP核心 weapon_effect 88 (desc「(且…)N%」); 命中scope的UP修饰行不再单列 */
  const merged = {};
  if (sspOn) for (const r of ((weaponSspTraits()[w.id] || []).filter(x => x.trait_type === 88))) {
    const m = String(r.desc || '').match(/(且)([^)）]*?)(光束|镭射|物理|特殊|防御力减少)[^0-9]*?(\d+)%/);
    if (!m) continue;
    const scope = m[3] === '防御力减少' ? '降防' : (m[3] === '镭射' ? '光束' : m[3]);
    merged[scope] = 1;
    for (const en of ents) if ((en.t === 'attr' || en.t === 'def') && en.scope === scope) en.v += +m[4];
  }
  const out = [];
  const dmgOnly = !!(opts && opts.mode === 'dmg');   // 只取增伤(X-N%)/降防类(支援型行用)
  for (const en of ents) {
    if (en.t === 'attr') out.push((en.scope || '全属性') + '-' + en.v + '%');
    else if (en.t === 'def') out.push('降防' + en.v + '%');
    else if (dmgOnly) continue;
    else if (en.t === 'up') { if (en.when && !(en.scope && merged[en.scope])) out.push(en.s); }
    else out.push(en.s);
  }
  return out.join(' · ');
}
/* 进攻盾(trait90「反击时支援防御」)持有驾驶员: [{id,name,icon,role,rarity,ability,reqTags,reqSeries}] */
let _csDrv = null;
function counterShieldDrivers() {
  if (_csDrv) return _csDrv;
  _csDrv = [];
  const seen = new Set();
  const scan = rows => {
    for (const r of rows) {
      if (seen.has(r.char_id)) continue;
      let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      const hit = ts.filter(t => ((t || {}).trait || {}).trait_type === 90);
      if (!hit.length) continue;
      const c = q1('SELECT id,name,icon,role,rarity,series_set_id FROM characters WHERE id=?', [r.char_id]);
      if (!c) continue;
      const cq = condTagsOf(hit[0].trait.active_condition || {});
      seen.add(r.char_id);
      _csDrv.push({ id: r.char_id, name: c.name, icon: c.icon, role: c.role, rarity: c.rarity, series_set_id: c.series_set_id, ability: r.name, reqTags: [...new Set(cq.tags)], reqSeries: [...new Set(cq.series)] });
    }
  };
  scan(q('SELECT char_id, name, traits_json FROM char_abilities'));
  scan(q('SELECT char_id, name, traits_json FROM char_abilities_sp'));
  _csDrv.sort((a, b) => (b.rarity || 0) - (a.rarity || 0) || a.id - b.id);
  return _csDrv;
}
/* 支援型行: 机体全部可用武器的「增伤/降防」特效并集(按威力降序; 每项附该武器射程 min-max + MAP标识; 叠驾驶员88/SSP88) */
function unitDamageFxOf(unitId, charId, f, sspWOn, spOn, opts) {
  const u = q1('SELECT * FROM units WHERE id=?', [unitId]);
  if (!u) return '';
  const out = [], conds = [];
  for (const raw of weaponsForUnit(u, ' ORDER BY power DESC')) {
    if (raw.is_ssp && !(f.ssp && opts.sspU !== false)) continue;   // 版本筛选同 buildRanking
    if (!raw.is_ssp && !f.sp) continue;
    const w = sspWOn ? sspAdjW(raw, u) : raw;
    const tkn = weaponFxCompactOf(w, charId, u, sspWOn, spOn,
      { condAll: opts.condAll, vigor: opts.vigor, mode: 'dmg', enemyMeta: opts.enemyMeta });
    if (!tkn) continue;
    for (const l of enemyCondNotes(null, null, { condAll: opts.condAll, enemyMeta: opts.enemyMeta }, null, w).labels) {   // 敌方条件特效注明
      if (conds.indexOf(l) < 0) conds.push(l);
    }
    const lbl = tkn + ' ' + w.range_min + '-' + w.range_max + (w.type === 3 ? '·MAP' : '');
    if (out.indexOf(lbl) < 0) out.push(lbl);
  }
  return out.length ? (out.join(' · ') + (conds.length ? ' · 条件:' + conds.join('/') : '')) : '';
}
/* SSP满10视图的武器(威力/EN/弹药/射程强化的浅拷贝; 无强化则原样返回) */
let _wSspTr = null;
function weaponSspTraits() {   // weapon_effect(数值类且无同型合并) — 随SSP计入武器特性
  if (!_wSspTr) {
    _wSspTr = {};
    for (const r of q('SELECT weapon_id, trait_type, trait_value, desc, name FROM weapon_ssp_traits'))
      (_wSspTr[r.weapon_id] = _wSspTr[r.weapon_id] || []).push(r);
  }
  return _wSspTr;
}
function sspAdjW(w, u) {
  const mods = sspWeaponMods(u);
  const m = mods && mods[w.id];
  const ex = weaponSspTraits()[w.id] || null;
  if (!m && !ex) return w;
  const o = Object.assign({}, w);
  if (m) { o.en = (w.en || 0) - m.em; o.ammo = (w.ammo || 0) + m.ammo; o.range_max = (w.range_max || 0) + m.rng; o._sspAdd = m.pa; o._sspMod = m; }
  if (ex) o._sspTraits = ex;
  return o;
}
function sspMovOf(u) {   // SSP核心解放的移动力提升: 仅部分机体有(release type 3 + status_up index 6; 里格·夏柯+1, 格拉布罗/00R 无)
  try {
    const d = JSON.parse(u.ssp_json || '{}');
    let mv = 0;
    for (const c of (d.cores || [])) for (const r of (c.releases || [])) {
      if (r.release_function_type_index === 3) {
        const su = r.status_up || {};
        if (su.unit_status_type_index === 6) mv += (su.effect_value || 0);
      }
    }
    return mv;
  } catch (e) { return 0; }
}
let _sdCharMap = null;
/* 防御机体+驾驶员 配合生效的防御类能力: 防御力提升/守备值提升/受伤减轻(无条件) */
/* 防御目标技能: 防御力提升/守备值提升/受到的损伤减轻
   Owner条件(搭乘单位含有X标签/系列)必须与防御机体匹配;
   敌方条件(target=AttackTarget, 发起对战的敌方包含X标签)按每个攻击方单独判定 → x 列表 */
/* 该机体+驾驶员在当前设置下的战斗气势(攻防两侧共用; 默认按被动MP自动判定, 首动放MP技→超一击) */
function scenarioVigorOf(u, charId, t, sspOn) {
  let v = (t.vigor === 'default') ? mpToVigor((u && charId) ? mpOf(u.id, charId, t.first ? false : !!t.skills, t.ca, t.pSpU, sspOn) : 0) : t.vigor;
  if (t.first && charId) {
    const mpP = u ? mpOf(u.id, charId, false, t.ca, t.pSpU, sspOn) : 0;
    const f0 = firstActOfRows(charActSkillRows(charId, t.pSpU !== false), null, t.fdth, mpP);
    if (f0 && f0.k === 'mp') v = 'supercharged';
  }
  return v;
}
/* 防御侧被动(defPct 防御力%/cdefPct 守备%/redPct 减伤%): 条件按场景如实判定 —
   「进行支援防御时」=场景事实(sdefOn); 「攻击时/反击时」等动作条件与战意/场景条件仅在「条件被动=开·假设满足」时计入 */
/* 姿态减伤: 选择防御 与 支援防御 是同一场战斗的互斥动作(不可能同时发生), 只取一次 -40%; 带盾再 -20% */
function stanceReduceOf(t, hasShield) {
  const st = (t && (t.guard || t.sdef)) ? 40 : 0;
  return st + (st && hasShield ? 20 : 0);
}
function defenderSkills(unitId, charId, sdefOn, sspOn, vigor, condAll) {
  const out = { defPct: 0, cdefPct: 0, redPct: 0, x: [] };
  const meta = metaOf(unitId);
  const scan = rows => {
    for (const r of rows) {
      let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      for (const t of ts) {
        const tr = (t || {}).trait || {};
        const d = (tr.desc || '').replace(/\n/g, '');
        let v = tr.trait_value || 0;
        if (v > 100) {   // 累计型编码值 → max开=最高N%; 条件被动开=1层(base); 否则0
          const mx = /最高\s*(\d+)%/.exec(d), bs = /提升\s*(\d+)%/.exec(d);
          v = mx ? (state.maxOn ? +mx[1] : (condAll ? (bs ? +bs[1] : 0) : 0)) : 0;
        }
        if (v <= 0) continue;
        let kind = d.indexOf('防御力提升') >= 0 ? 'defPct'
          : (d.indexOf('守备值提升') >= 0 ? 'cdefPct'
            : (d.indexOf('受到的损伤减轻') >= 0 && d.indexOf('攻击时') < 0 ? 'redPct' : null));
        if (!kind && r._ssp) {   // 仅SSP能力变化行(desc常为空)按类型兜底: 9=防御力提升% / 25,26=守备提升%
          if (tr.trait_type === 9) kind = 'defPct';
          else if (tr.trait_type === 25 || tr.trait_type === 26) kind = 'cdefPct';
        }
        if (!kind) continue;
        const ac = tr.active_condition || {};
        const cq = condTagsOf(ac);
        const acts = cq.bag ? cq.bag.split(',').map(x => x.trim()).filter(Boolean) : [];
        const sdefAct = acts.includes('SupportDefense');
        if (sdefAct && !sdefOn) continue;                          // 「进行支援防御时」: 未做支援防御(场景事实)不计
        if (!sdefAct && acts.length && !condAll) continue;          // 「攻击时/反击时」等动作条件: 防御场景如实判定不成立, 仅条件全开时假设满足
        let tensionReq = 0;                                         // 战意条件: 条件全开假设满足; 关时按当前气势如实判定
        if (ac.tension) { const _rs = String(ac.tension).split(',').map(x => TENSION_RANK[x.trim()] || 0).filter(Boolean); if (_rs.length) tensionReq = Math.min(..._rs); }   // 「超强势以上」编码为档位集合 → 阈值取最低档
        if ((ac.target || 'Owner') === 'AttackTarget') {
          out.x.push({ tags: cq.tags, series: cq.series, ctags: cq.ctags, kind, v });   // 随攻击方标签/驾驶员标签生效
        } else {
          if (!condOk({ tensionReq, reqTags: cq.tags, reqSeries: cq.series, reqUnits: cq.units, roleReq: cq.role, ctx: cq.ctx }, meta, { condAll: !!condAll, vigor })) continue;
          out[kind] += v;
        }
      }
    }
  };
  scan(unitAbilitiesOf(unitId, sspOn));   // 随SSP能力变化(防御力提升 LV1→LV2 等)
  if (charId) scan(q('SELECT traits_json FROM char_abilities WHERE char_id=?', [charId]));
  out.redPct += ultRedPct({ id: unitId, ult: 1 });   // ULT改造能力「威力抵御」三选一生效时
  return out;
}
/* 武器条件效果(「发起对战的敌方包含「X」标签/系列时…」, cond 存 AttackTarget 条件):
   指定对手时按对手标签/系列匹配, 未指定时按条件全开 */
let _wtRows = {};   // 性能: 每武器 traits 行 + cond 解析结果缓存(排序/核算热路径)
function _wtRowsOf(wid) {   // 每武器 weapon_traits 行 + cond 解析缓存({tr, cq})
  let rows = _wtRows[wid];
  if (!rows) {
    rows = _wtRows[wid] = q('SELECT * FROM weapon_traits WHERE weapon_id=?', [wid]).map(tr => {
      if (!tr.cond) return { tr, cq: null };
      try { return { tr, cq: condTagsOf(JSON.parse(tr.cond)) }; } catch (e) { return { tr, cq: null }; }
    });
  }
  return rows;
}
function _wCondOk(cq, enemyMeta, condAll) {   // 敌方条件生效判定: 指定对手按标签/系列匹配; 未指定按条件被动开关(默认开=全部生效)
  return enemyMeta ? reqOk(cq.tags, cq.series, enemyMeta) : condAll !== false;
}
function wTraitsOf(w, enemyMeta, condAll) {
  const wid = (w && typeof w === 'object') ? w.id : w;
  const extra = (w && typeof w === 'object' && w._sspTraits) ? w._sspTraits.map(t => ({ weapon_id: wid, level: 5, trait_type: t.trait_type, trait_value: t.trait_value, desc: t.desc, cond: '' })) : [];
  return _wtRowsOf(wid).filter(x => {
    if (!x.cq) return true;
    return _wCondOk(x.cq, enemyMeta, condAll);
  }).map(x => x.tr).concat(extra);
}
/* 敌方条件规则匹配（按攻击方机体 meta） */
function skillRuleMatch(r, meta) {
  const hasReq = (r.tags && r.tags.length) || (r.series && r.series.length);
  if (!hasReq) return true;
  if (!meta) return false;
  if (r.series && r.series.length && (meta.seriesList ? r.series.some(s => meta.seriesList.has(s)) : (meta.series && r.series.includes(meta.series)))) return true;
  if (r.tags && r.tags.length) for (const t of r.tags) if (meta.tags && meta.tags.has(t)) return true;
  return false;
}
function xMatch(r, meta) {   // 敌方条件(对XX)匹配: 标签/系列 + 敌方驾驶员标签(ctags, 如「敌方包含「新人类」标签」)
  if (!skillRuleMatch(r, meta)) return false;
  if (r.ctags && r.ctags.length && !(meta && meta.ctags && r.ctags.some(x => meta.ctags.has(x)))) return false;
  return true;
}
function sdCharMap() {          // {charId: Set(unitId)} SD机体→绑定驾驶员反查（SD绑定驾驶员不能驾驶其他机体）
  if (_sdCharMap) return _sdCharMap;
  const m = {};
  q("SELECT u.id, u.name FROM units u JOIN unit_tags ut ON ut.unit_id=u.id JOIN tags t ON t.id=ut.tag_id WHERE t.name='SD高达'")
    .forEach(r => { const ch = sdOwnChar(r); if (ch) (m[ch.id] = m[ch.id] || new Set()).add(r.id); });
  _sdCharMap = m;
  return m;
}
/* SD绑定驾驶员只能驾驶自己的机体（unitId 为空=通用目标时只能选非SD绑定驾驶员） */
function pilotCanDrive(charId, unitId) {
  const owned = sdCharMap()[charId];
  return !owned || (unitId && owned.has(unitId));
}
/* 武器战意限制: 「战意为超强势以上时即可使用」→ 需 vigor 为 max(超强势)/supercharged(超一击) */
let _wUseLegacy = null;
/* 武器使用条件(weapon_use 文本): ①「战意为(超强势|强势)以上即可使用」→ 需对应气势
   ②「消耗N MP即可使用」→ 当前MP需≥N(气势档位折算: 超一击12/超强势8/强势4; 有精确MP时取 max(MP, 档位下限)) */
const TIER_MP = { high: 4, max: 8, supercharged: 12 };
let _wUseReq = null;
function weaponUseReq(wid) {
  if (!_wUseReq) {
    _wUseReq = {};
    for (const r of q('SELECT weapon_id, text FROM weapon_use')) {
      const t = r.text || '';
      const mp = /消耗\s*(\d+)\s*MP/.exec(t);
      const ten = /战意为(超强势|强势)以上/.exec(t);
      if (!mp && !ten) continue;
      _wUseReq[r.weapon_id] = { mp: mp ? +mp[1] : 0, tension: ten ? (ten[1] === '超强势' ? 'max' : 'high') : null };
    }
  }
  return _wUseReq[wid] || null;
}
function vigorAllows(wid, vigor, mp) {
  const req = weaponUseReq(wid);
  if (!req) return true;
  const rank = VIGOR_RANK[vigor] ?? 0;
  if (req.tension === 'max' && rank < 2) return false;
  if (req.tension === 'high' && rank < 1) return false;
  if (req.mp) {
    const tier = TIER_MP[vigor] || 0;
    const cur = mp != null ? Math.max(mp, tier) : tier;
    if (cur < req.mp) return false;
  }
  return true;
}
function sdOwnChar(u) {
  const cols = 'id,name,icon,rarity,role,max_melee,max_ranged,max_awaken,sp_max_melee,sp_max_ranged,sp_max_awaken';
  const base = u.name.replace(/\s*(\(|（)[^)）]*[)）]\s*$/, '');
  let ch = q1(`SELECT ${cols} FROM characters WHERE name=?`, [u.name]);
  if (!ch && base && base !== u.name) ch = q1(`SELECT ${cols} FROM characters WHERE name=?`, [base]);
  if (!ch) ch = q1(`SELECT ${cols} FROM characters WHERE replace(name,'型','')=replace(?,'型','')`, [base || u.name]);   // 全装甲(型)骑士高达 类差异
  return ch;
}

/* ------------ 排行/组队 通用计算 ------------
   opts.autoVigor: 气势按 MP 自动判定（组队页 第一击=被动 / 全技能=被动+主动）
   opts.ship: 战舰效果 {pct:全能力值%, atkFlat:攻击支援, hpFlat:HP支援, tags:[], series:[]} */
function buildRanking(f, cfg, opts = {}) {
  const P = { passive: opts.passive !== false, cpassive: opts.cpassive !== false, skills: !!opts.skills, condAll: opts.condAll !== false, mp: !!opts.multiPhase, star: opts.star ?? 3, spU: opts.spU !== false, s3u: opts.s3u !== false, sspU: opts.sspU !== false, pSpU: opts.pSpU !== false, uSk: opts.uSk !== false };   // spU/s3u/sspU: 非UR机体 SP/三星/SSP开关(SSP需三星+SP); pSpU: 驾驶员SP开关
  const auto = !!opts.autoVigor;
  const first = !!opts.first, fdth = !!opts.fdth;   // 首动: 只算首动那1个技能的加成; fdth=反死风险
  const allPct = opts.allPct || 0;   // 攻方全能力+xx%（标签/系列加成）
  const ship = opts.ship || null;
  const shipTags = ship ? new Set(ship.tags) : null;
  const tbuffs = opts.teamBuffs && opts.teamBuffs.length ? opts.teamBuffs : null;
  const u = unitWhere('unit', { ...f, sp: 0, ssp: 0 });
  const units = dedupeUnits(q(`SELECT u.* FROM units u ${u.where} ORDER BY u.id`, u.args));   // ULT改造口径: 阶段0/1→改造后(002)并按有效id去重
  /* 驾驶员候选 = 全部可上场角色（与计算页一致, 确保取到真正最高伤害组合） */
  const allPilots = q('SELECT id,name,icon,rarity,role,series_set_id,max_melee,max_ranged,max_awaken,sp_max_melee,sp_max_ranged,sp_max_awaken FROM characters WHERE COALESCE(is_playable,1)=1');
  const sdMap = sdCharMap();
  let pilotOk = null;                                  // 驾驶员标签/系列筛选(opts.pilotFn): 预扫一次
  if (opts.pilotFn) { pilotOk = new Set(); for (const p of allPilots) if (opts.pilotFn(p)) pilotOk.add(p.id); }
  /* 驾驶员类型口径: groups={key:role|null} 一次计算多份; 或 pilotRole 单口径过滤 */
  const groups = opts.pilotGroups || null;
  const singleRole = opts.pilotRole || null;
  const pilotRar = opts.pilotRar || null;   // 驾驶员稀有度过滤(排行榜全局; 组队作用于全部组: 攻击型/攻×支/支援型/防御型)
  const allW = q('SELECT * FROM weapons');
  const allWId = {};
  const wByUnit = {};
  allW.forEach(w => { allWId[w.id] = w; (wByUnit[w.unit_id] = wByUnit[w.unit_id] || []).push(w); });
  const ultWOn = ultTotal() >= 50;   // ULT改造武器: 总Lv≥50解锁(隐藏未解锁的该武器)
  const traitsByW = {};
  const sspTrByW = {};   // weapon_effect 合并行(SSP能力变化同层, 无同型才计数)
  for (const r of q('SELECT weapon_id, trait_type, trait_value, desc FROM weapon_ssp_traits')) {
    (sspTrByW[r.weapon_id] = sspTrByW[r.weapon_id] || []).push({ level: 5, trait_type: r.trait_type, trait_value: r.trait_value, desc: r.desc, cond: '' });
  }
  q('SELECT weapon_id, level, trait_type, trait_value, desc, cond FROM weapon_traits WHERE level=5').forEach(t => {
    if (t.cond) {                                   // 武器条件效果: 按对手判定(未指定时条件全开)
      let c = null; try { c = JSON.parse(t.cond); } catch (e) { c = null; }
      if (c) {
        const cq = condTagsOf(c);
        if (!(opts.enemyMeta ? reqOk(cq.tags, cq.series, opts.enemyMeta) : P.condAll !== false)) return;
      }
    }
    (traitsByW[t.weapon_id] = traitsByW[t.weapon_id] || []).push(t);
  });
  const ATTRS = ['melee', 'ranged', 'awaken'];
  const rows = groups ? null : [];
  const out = {};
  if (groups) for (const k in groups) out[k] = [];
  for (const un of units) {
    let wsRaw = wByUnit[un.id] || [];
    const uwRow = ultWeaponMap()[un.id];
    if (uwRow) {   // ULT改造换装武器: 按总Lv≥50解锁; 未解锁时从本体武器表隐藏
      wsRaw = wsRaw.filter(w => w.id !== uwRow.weapon_id);
      if (ultWOn && allWId[uwRow.weapon_id]) wsRaw = wsRaw.concat([allWId[uwRow.weapon_id]]);
    }
    if (!wsRaw.length) continue;
    if (cfg.urole && un.role !== cfg.urole) continue;      // 机体类型筛选
    if (cfg.rarity) {   // 稀有度筛选(含 ULT 终极机体系)
      if (cfg.rarity === 'ult') { if (!un.ult) continue; }
      else if (un.rarity !== cfg.rarity) continue;
    }
    if (cfg.terr && terrOf(un, cfg.terr) === 1) continue;  // 出击场地: ×不能出击 → 不入榜
    if (cfg.terr && cfg.terrO && terrOf(un, cfg.terr) !== 3) continue;   // 移动○筛选: 仅该场地○(3)
    const terrHalfU = cfg.terr ? terrOf(un, cfg.terr) === 2 : false;   // △移动力减半(红框标记)
    const sspWOn = un.rarity <= 4 && !un.ult && P.sspU !== false && (P.spU !== false) && (P.s3u !== false);   // 非UR 三星+SP+SSP开关
    const traitsOf = wid => (sspWOn && sspTrByW[wid]) ? (traitsByW[wid] || []).concat(sspTrByW[wid]) : (traitsByW[wid] || []);
    const ws = (sspWOn ? wsRaw.map(w => sspAdjW(w, un)) : wsRaw).filter(w => {   // 版本/射程/属性/类型筛选(改装核心强化随SSP生效)
      if (w.is_ssp && !(f.ssp && P.sspU !== false)) return false;   // SSP 武器: 弹窗版本筛选 × 排行SSP总开关
      if (!w.is_ssp && !f.sp) return false;
      if (cfg.wat && AATTR[w.weapon_attr] && !AATTR[w.weapon_attr].includes(cfg.wat)) return false;   // 武器属性
      if (cfg.atk && !(WATTR[w.attack_attr] || ['melee']).includes(cfg.atk)) return false;            // 射击/格斗/觉醒
      if (cfg.range && cfg.range !== 'all') {
        if (cfg.range === 'map') { if (w.type !== 3) return false; }
        else if (w.type === 3) return false;
        else if (cfg.range === 6) { if (w.range_max < 6) return false; }
        else if (w.range_max !== cfg.range) return false;
      }
      return true;
    });
    if (!ws.length) continue;
    const meta = metaOf(un.id);
    const tDefRow = opts.targetDefFn ? opts.targetDefFn(meta) : (cfg.targetDef ?? 10000);            // 防御目标技能可按攻击方标签变化
    const defReduceRow = opts.defReduceFn ? opts.defReduceFn(meta) : (opts.defReduce || 0);
    const cbOpts = vigor => ({ passive: P.cpassive, cpassive: P.cpassive, skills: first ? false : P.skills, condAll: P.condAll, first, unitId: un.id, upassive: P.passive, multiPhase: P.mp, vigor, enemyMeta: opts.enemyMeta, pSpU: P.pSpU, ussp: sspWOn });
    let cands = meta.tags.has('SD高达')
      ? [sdOwnChar(un)].filter(Boolean)     // SD机体只能本机驾驶员
      : allPilots.filter(p => { const owned = sdMap[p.id]; return !owned || owned.has(un.id); });   // SD绑定驾驶员不能驾驶其他机体
    if (pilotOk) cands = cands.filter(p => pilotOk.has(p.id));
    if (!cands.length) continue;
    const effStar = un.ult ? 0 : (un.rarity >= 5 ? P.star : 3);   // ULT最大0星; UR按选择; SSR及以下按3星
    const isNonUR = un.rarity <= 4 && !un.ult;                    // 非UR: 受 SP/SSP 开关控制
    const spOn = isNonUR ? (P.spU !== false) : true;
    const s3On = isNonUR ? (P.s3u !== false) : true;
    const _ub = isNonUR ? uStatBase(un, 'atk', s3On, spOn)
                        : { base: un.sp_max_atk || un.max_atk, mult: STAR_MULT[effStar] };
    const sspAdd = (isNonUR && P.sspU !== false && spOn && s3On) ? sspGainOf(un, 10).atk : 0;   // SSP满10 攻击加成(需三星+SP)
    const uBase = Math.floor((_ub.base + sspAdd) * _ub.mult);   // SSP加在★倍率之前(游戏口径); 攻方全能力%与舰长/队伍增强同口径(加算组, 见下方uAtk)
    const shipHit = !!(ship && ((shipTags.size && [...meta.tags].some(x => shipTags.has(x))) || (ship.series.length && meta.series && ship.series.includes(meta.series))));
    const shipPct = shipHit ? ship.pct : 0;
    const shipFlat = ship ? ship.atkFlat : 0;
    let bAtk = 0, bDef = 0, bHit = false;
    if (tbuffs) for (const b of tbuffs) if (tbuffMatch(b, meta)) { bAtk += b.atk; bDef += b.def; bHit = true; }
    /* —— 廉价预扫: 每驾驶员一次(MP/气势/被动/暴击侧) —— */
    const pool = [];
    for (const p of cands) {
      const skRows = first ? charActSkillRows(p.id, P.pSpU) : null;
      const mp0 = mpOf(un.id, p.id, first ? false : P.skills, P.condAll, P.pSpU, sspWOn);   // 被动MP: 首动MP提升释放条件(MP≥3)用
      const faTop = first ? firstActOfRows(skRows, null, fdth, mp0) : null;
      const mp = auto ? mp0 : 0;
      const vigor = (first && faTop.k === 'mp') ? 'supercharged' : (auto ? mpToVigor(mp) : cfg.vigor);   // 首动MP技(MP≥3) → 超一击(+30%)
      pool.push({ p, vigor, mp, mp0, skRows, b: charBonus(p.id, vigor, cbOpts(vigor), meta), pc: pilotCritInfo(un.id, p.id, meta, cbOpts(vigor)) });
    }
    const bestFor = (roleFilter, rarFilter) => {
    const sub = pool.filter(x => (!roleFilter || x.p.role === roleFilter) && (!rarFilter || (x.p.rarity || 0) === rarFilter));
    if (!sub.length) return null;
    let bestRow = null;
    for (const a of ATTRS) {
      const wsub = ws.filter(w => (WATTR[w.attack_attr] || ['melee']).includes(a));
      if (!wsub.length) continue;
      /* 帕累托前沿: 伤害对(cAtk,增伤,暴击)单调↑ → 剪除被支配者后精确比较 */
      const arr = sub.map(x => {
        const fa = first ? firstActOfRows(x.skRows, [a], fdth, x.mp0) : null;   // 首动技: 值增幅按该属性
        return { x, fa, cAtk: Math.floor(pStat(x.p, a, P.pSpU) * (1 + ((x.b[a] || 0) + (fa && fa.k === 'stat' ? fa.v : 0)) / 100)) };
      });
      arr.sort((m, n) => n.cAtk - m.cAtk);
      const front = [];
      let maxEe = -1, maxCrit = -1;
      /* 池内存在可能凑满100%暴击的机师时: 暴击使伤害对(cAtk,ee)不再单调, 剪枝可能误剪真最优(如尊者EX+东方不败曾输给数值更低的行) → 关闭剪枝取精确解 */
      const anyFcCap = sub.some(x2 => x2.pc.guar || x2.pc.rate >= 60);
      for (const it of arr) {
        const ee = it.x.b.dmg + (it.fa && it.fa.k === 'burst' ? it.fa.v : 0) + Engine.VIGOR[it.x.vigor].rate + ultDmgPct(un);
        /* 帕累托剪枝的暴击维度: 必暴/可能凑满100%暴击(机师率+武器暴击≥100)的机师, 即使暴击开关关也按暴击计 ——
           不能被无暴击机师剪掉(曾出 bug: 固定超一击下全员+30增伤把阿斯兰(100%暴击)的相对增伤差拉平, 被罗·裘尔剪掉) */
        const fcCap = it.x.pc.guar || it.x.pc.rate >= 60;
        const critScore = it.x.pc.guar ? 9e9 : fcCap ? 8e9 : (cfg.crit ? Engine.VIGOR[it.x.vigor].crit + (it.x.pc.rate > 0 ? 0.5 : 0) : 0);
        if (anyFcCap || ee > maxEe || critScore > maxCrit) { front.push({ x: it.x, fa: it.fa, cAtk: it.cAtk, ee }); maxEe = Math.max(maxEe, ee); maxCrit = Math.max(maxCrit, critScore); }
      }
      for (const w of wsub) {
        for (const it of front) {
          if (!vigorAllows(w.id, it.x.vigor, auto ? it.x.mp : null)) continue;   // 气势/MP 条件不足时不能使用
          const vigor = it.x.vigor;
          const uPct = (P.passive ? unitPassiveAtkPct(un.id, vigor, P.condAll, opts.enemyMeta, sspWOn, first) : 0) + (P.uSk ? unitSkillAtkPct(un.id) : 0);   // 机体技能独立开关(opts.uSk)
          const uAtk = Math.floor(uBase * (1 + (uPct + shipPct + bAtk + allPct + (it.x.b.atk || 0)) / 100)) + shipFlat;
          const rate = Math.min(100, (w.crit_rate || 0) + it.x.pc.rate);
          const w94 = traitsOf(w.id).some(t => t.trait_type === 94);   // 武器必暴(trait94)
          const forceCrit = it.x.pc.guar || w94 || rate >= 100;   // 暴击率100%/必暴: 无视暴击开关按暴击计算
          const critOn = (cfg.crit || forceCrit) && (it.x.pc.guar || w94 || rate > 0);
          const eeT = it.x.b.dmg + (it.fa && it.fa.k === 'burst' ? it.fa.v : 0) + ultDmgPct(un);
          const d = Engine.damageWithWeapon(uAtk, it.cAtk, w, traitsOf(w.id), 5, tDefRow, cfg.targetCharDef ?? 750,
            { vigor, crit: critOn, ee: eeT, critDmgAdd: critOn ? it.x.pc.cdmg : 0, defReduce: defReduceRow });
          const uw = cfg.terr === 'water' ? uwMult(w) : 100;   // 水中伤害减半/不可用
          const dmgF = uw === 100 ? d.final : Math.floor(d.final * uw / 100);
          if (!bestRow || dmgF > bestRow.dmg) bestRow = { unitId: un.id, unit: un,
            pilot: { id: it.x.p.id, name: it.x.p.name, icon: it.x.p.icon, role: it.x.p.role, rarity: it.x.p.rarity, v: it.cAtk, bonus: it.x.b, vigor, mp: it.x.mp },
            weapon: w, dmg: dmgF, uAtk: uAtk, uwMult: uw, stat: a, pct: uPct, pdmg: it.x.b.dmg, pstat: (it.x.b[a] || 0), fa: it.fa, star: effStar, effPower: d.effPower, powerPct: d.powerPct,
            vigor, mp: it.x.mp, shipPct, shipHit, critRate: rate, forceCrit, canCrit: (it.x.pc.guar || w94 || rate > 0), buffAtk: bAtk, buffDef: bDef, buffHit: bHit, terrHalf: terrHalfU,
            notice: enemyCondNotes(un.id, it.x.p.id, { upassive: P.passive, passive: P.cpassive, pSpU: P.pSpU !== false, condAll: P.condAll, enemyMeta: opts.enemyMeta }, sspWOn, w).labels.join('/') };
        }
      }
    }
    return bestRow;
    };
    if (groups) {
      for (const k in groups) { const r = bestFor(groups[k], pilotRar); if (r) out[k].push(r); }   // 驾驶员稀有度作用于全部组(攻击型/攻×支/支援型/防御型)
    } else {
      const r = bestFor(singleRole, pilotRar);
      if (r) rows.push(r);
    }
  }
  if (groups) { for (const k in out) out[k].sort((a, b) => b.dmg - a.dmg); return out; }
  rows.sort((a, b) => b.dmg - a.dmg);
  return rows;
}
function pageRank(v) {
  const f = filt('rank');
  const cfg = state.rankCfg;
  v.innerHTML = `
    <div class="chips tight" style="align-items:center">
      <span class="hint">目标防御</span><input id="tdef" type="number" value="${cfg.targetDef}" style="width:58px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:2px 6px;font-size:11px">
      <span class="hint">守备</span><input id="tcdef" type="number" value="${cfg.targetCharDef}" style="width:46px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:2px 6px;font-size:11px">
      <span class="chip" id="rap">应用</span>
      ${[10000, 20000, 40000].map(v => `<span class="chip" data-td="${v}">${v / 1000}k</span>`).join('')}
    </div>
    <div class="chips">
      ${[['default', '默认'], ['mid', '无气势'], ['high', '强势'], ['max', '超强势'], ['supercharged', '超一击']].map(([k, l]) => `<span class="chip ${cfg.vigor === k ? 'gold' : ''}" data-vg="${k}">${l}</span>`).join('')}
      <span class="chip ${cfg.crit ? 'on' : ''}" id="rc">暴击${cfg.crit ? ' 开' : ' 关'}</span>
      <span class="chip ${cfg.passive ? 'on' : ''}" id="rp">机体被动${cfg.passive ? ' 开' : ' 关'}</span>
      <span class="chip ${cfg.cpassive ? 'on' : ''}" id="rcp">驾驶员被动${cfg.cpassive ? ' 开' : ' 关'}</span>
      <span class="chip ${cfg.skills ? 'gold' : ''}" id="rsk">主动技能${cfg.first ? ' 由首动' : (cfg.skills ? ' 开' : ' 关')}</span>
      <span class="chip ${cfg.first ? 'gold' : ''}" id="rfirst" title="竞技场AI首动(官方优先度): 每动只放1个技能 — 减伤(威力抵御)>+MP>+命中闪避(会被反死)>攻击爆裂>摇摆闪避>增幅(对应属性武装)>爆击增幅>保留EN; 假设满血满EN·够得着; 首动MP技=超一击+30%">首动${cfg.first ? ' 开' : ' 关'}</span>
      ${cfg.first ? `<span class="chip ${cfg.fdth ? 'gold' : ''}" id="rfdth" title="开: 假设『会被反击杀死』成立 — 「命中率·闪避率提升」挤掉攻击爆裂; 「摇摆闪避」不影响首动伤害">反死风险${cfg.fdth ? ' 开' : ' 关'}</span>` : ''}
      <span class="chip ${cfg.ca ? 'gold' : ''}" id="rca" title="开: 假设 HP/标签/战意等条件被动满足(支援攻击/支援反击/反击另有开关); 关: 按普通攻击如实判定">条件被动${cfg.ca ? ' 开' : ' 关'}</span>
      <span class="chip ${state.supAct !== false ? 'gold' : ''}" id="rsupact" title="开: 计入「支援攻击/支援反击/反击时」机体/驾驶员被动; 关: 按普通攻击不计入">支援攻击/反击${state.supAct !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${state.maxOn ? 'gold' : ''}" id="rmax" title="开: 条件型叠层被动按最高N%满层; 关: 条件被动按1层; 首动攻击次数型恒0层">max${state.maxOn ? ' 满层' : ' 1层'}</span>
      <span class="chip ${state.uSk !== false ? 'gold' : ''}" id="rusk" title="机体技能(单位技能)是否计入伤害 — 独立于驾驶员主动技能">机体技能${state.uSk !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${state.ultLv ? 'gold' : ''}" id="rurd" title="ULT改造: 0/50/100级; ≥50解锁ULT武器, 100解锁三选一能力">ULT改造${state.ultLv ? ' Lv' + state.ultLv : ' 关'}</span>
      <span class="chip ${cfg.mp ? 'gold' : ''}" id="rmp" ${cfg.first ? 'style="opacity:.45"' : ''} title="${cfg.first ? '首动模式下不可开启(多阶段增益=超一击EX赋予)' : '多阶段增益: 超一击时EX1/EX2赋予'}">多阶段增益${cfg.mp ? ' 开' : ' 关'}</span>
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">UR星数(突破):</span>
      ${[0, 1, 2, 3].map(st => `<span class="chip ${cfg.star === st ? 'on' : ''}" data-star="${st}">★${st}</span>`).join('')}
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">非UR强化:</span>
      <span class="chip ${cfg.s3u !== false ? 'gold' : ''}" id="rs3">三星${cfg.s3u !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${cfg.spU !== false ? 'gold' : ''}" id="rspu">SP强化上限${cfg.spU !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${cfg.sspU !== false ? 'gold' : ''}" id="rsspu">SSP满10${cfg.sspU !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${cfg.pSpU !== false ? 'gold' : ''}" id="rpspu">驾驶员SP${cfg.pSpU !== false ? ' 开' : ' 关'}</span>
    </div>
    <div class="chips"><span class="hint" style="align-self:center;font-size:10px">ULT固定★0 · SSR及以下按★3 · 非UR强化仅作用于SSR及以下机体的数值/武器</span></div>
    <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">射程:</span>
      <span class="chip ${cfg.range === 'all' ? 'on' : ''}" data-rg="all">全部</span>
      ${[1, 2, 3, 4, 5].map(nn => `<span class="chip ${cfg.range === nn ? 'on' : ''}" data-rg="${nn}">${nn}</span>`).join('')}
      <span class="chip ${cfg.range === 6 ? 'on' : ''}" data-rg="6">6+</span>
      <span class="chip ${cfg.range === 'map' ? 'gold' : ''}" data-rg="map">MAP</span>
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">驾驶员类型:</span>
      ${[['all', '全部'], [1, '攻击型'], [3, '支援型'], [2, '防御型']].map(([k, l]) =>
        `<span class="chip ${(cfg.prole || 'all') === k ? 'gold' : ''}" data-prole="${k}">${l}</span>`).join('')}
    </div>
    <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">驾驶员稀有度:</span>
      ${[['all', '全部'], [1, 'N'], [2, 'R'], [3, 'SR'], [4, 'SSR'], [5, 'UR']].map(([k, l]) =>
        `<span class="chip ${(cfg.prar || 'all') == k ? (k === 'all' ? 'on' : 'gold') : ''}" data-prar="${k}">${l}</span>`).join('')}
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">武器属性:</span>
      ${[['all', '全部'], ['物理', '物理'], ['光束', '光束'], ['特殊', '特殊']].map(([k, l]) =>
        `<span class="chip ${(cfg.wat || 'all') === k ? (k === 'all' ? 'on' : 'gold') : ''}" data-wat="${k}">${l}</span>`).join('')}
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">类型:</span>
      ${[['all', '全部'], ['ranged', '射击'], ['melee', '格斗'], ['awaken', '觉醒']].map(([k, l]) =>
        `<span class="chip ${(cfg.atk || 'all') === k ? (k === 'all' ? 'on' : 'gold') : ''}" data-atk="${k}">${l}</span>`).join('')}
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">机体类型:</span>
      ${[['all', '全部'], [1, '攻击型'], [2, '耐久型'], [3, '支援型']].map(([k, l]) =>
        `<span class="chip ${(cfg.urole || 'all') == k ? (k === 'all' ? 'on' : 'gold') : ''}" data-urole="${k}">${l}</span>`).join('')}
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">出击场地:</span>
      ${[['', '无限制'], ['space', '宇宙'], ['atm', '空中'], ['ground', '地上'], ['surface', '水面'], ['water', '水中']].map(([k, l]) =>
        `<span class="chip ${(cfg.terr || '') === k ? (k === '' ? 'on' : 'gold') : ''}" data-rterr="${k}">${l}</span>`).join('')}
      <span class="hint" style="align-self:center">红框=移动力减半 · 不能出击的机体不入榜</span>
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">稀有度:</span>
      ${[['all', '全部'], [1, 'N'], [2, 'R'], [3, 'SR'], [4, 'SSR'], [5, 'UR'], ['ult', 'ULT']].map(([k, l]) =>
        `<span class="chip ${(cfg.rarity || 'all') == k ? (k === 'all' ? 'on' : 'gold') : ''}" data-rar="${k}">${l}</span>`).join('')}
    </div>
    <div class="fbar"><span class="fbtn" id="rtag">☰ 标签/系列 <b>${(f.tags.length + ((f.series || []).length)) || ''}</b></span>
      ${f.tags.length ? `<span class="modewrap">${f.mode === 'and' ? '全部命中' : '任一命中'}</span>` : ''}
      <span style="flex:1"></span><span style="font-size:11px;color:var(--dim)" id="rhit">计算中…</span></div>
    <div id="rlist"></div>`;
  const redraw = () => {
    const isAuto = cfg.vigor === 'default';      // 默认: 气势按被动MP自动判定
    const ckey = JSON.stringify([f.tags, f.series, f.mode, f.sp, f.ssp, cfg.targetDef, cfg.targetCharDef, cfg.vigor, cfg.crit, cfg.passive, cfg.cpassive, cfg.skills, cfg.first, cfg.fdth, cfg.ca, cfg.mp, cfg.star, cfg.range, cfg.prole || 0, cfg.prar || 0, cfg.wat || 0, cfg.atk || '', cfg.urole || 0, cfg.rarity || 0, cfg.terr || '', cfg.spU !== false, cfg.s3u !== false, cfg.sspU !== false, cfg.pSpU !== false, state.uSk !== false, state.supAct !== false, state.maxOn ? 1 : 0, state.ultLv || 0, JSON.stringify(state.ultSkill)]);
    let rows;
    if (state.rankCache && state.rankCache.key === ckey) rows = state.rankCache.rows;
    else {
      rows = buildRanking(f, Object.assign({}, cfg, { terr: cfg.terr || null }), { passive: cfg.passive, cpassive: cfg.cpassive, skills: cfg.skills, first: !!cfg.first, fdth: !!cfg.fdth, condAll: !!cfg.ca, autoVigor: isAuto, multiPhase: !!cfg.mp, star: cfg.star, pilotRole: cfg.prole || null, pilotRar: cfg.prar || null, spU: cfg.spU !== false, s3u: cfg.s3u !== false, sspU: cfg.sspU !== false, pSpU: cfg.pSpU !== false, uSk: state.uSk !== false });
      state.rankCache = { key: ckey, rows };
    }
    $('rhit').textContent = `共 ${fmt(rows.length)} 条 · 取前 100`;
    const flagMap = {};
    q('SELECT weapon_id, flag FROM weapon_flag ORDER BY sort').forEach(f => (flagMap[f.weapon_id] = flagMap[f.weapon_id] || []).push(f.flag));
    $('rlist').innerHTML = rows.slice(0, 100).map((r, i) => `
      <div class="rrow${r.terrHalf ? ' halfmove' : ''}" data-id="${r.unitId}" data-wid="${r.weapon.id}"><div class="rnum ${i < 3 ? 'n' + (i + 1) : ''}">${i + 1}</div>
        <div class="ricon-col"><div class="ricon">${avTagR(r.unit.icon, r.unit.role, r.unit.rarity)}</div><span class="avw avp"><span class="picon" title="${esc(r.pilot.name)}">${imgTag(r.pilot.icon)}</span>${roleBadge(r.pilot.role)}${rarB(r.pilot.rarity)}</span></div>
        <div class="rmid"><div class="rtop"><span class="uname">${esc(r.unit.name)}</span>${rarTag(r.unit.rarity)}${ultB(r.unit)}
          <span class="dmg">${fmt(r.dmg)}</span></div>
          <div class="rtagrow"><span class="tagx cond">${isAuto ? (r.mp ? Engine.VIGOR[r.vigor].label : '气势0') : Engine.VIGOR[cfg.vigor].label}</span><span class="tagx cond2">★${r.star}</span><span class="range r${Math.min(r.weapon.range_max, 5)}">射程${r.weapon.range_min}-${r.weapon.range_max}</span>${r.weapon.type === 3 ? '<span class="range r1">MAP</span>' : ''}<span class="wattr a${r.weapon.weapon_attr || 0}">${AATTR[r.weapon.weapon_attr] || ''}</span>${(flagMap[r.weapon.id] || []).map(f => `<span class="wflag">${esc(f)}</span>`).join('')}</div>
          <div class="rmeta">武器 <b>${esc(r.weapon.name)}</b> · 威力 ${fmt(Engine.weaponPower(r.weapon, 5))}${r.powerPct ? '→<span style="color:#9fd8ff">' + fmt(r.effPower) + '</span>（效果+' + r.powerPct + '%）' : ''}${r.pct ? ' · <span style="color:#9fe8c0">机体被动+' + r.pct + '%</span>' : ''}${r.pdmg ? ' · <span style="color:#9fe8c0">驾驶员增伤+' + r.pdmg + '%</span>' : ''}${r.notice ? ' · <span style="color:#f5c451">条件:' + esc(r.notice) + '</span>' : ''}${r.fa && r.fa.name ? ' · <span style="color:#7df0a8">首动 ' + esc(r.fa.name.replace(/ LV\d+/, '')) + (r.fa.k === 'burst' || r.fa.k === 'stat' ? ' +' + r.fa.v + '%' : '') + (r.fa.k === 'mp' ? ' 超一击' : '') + '</span>' : ''}${r.uwMult != null && r.uwMult < 100 ? ' · <span style="color:#ff9f43">' + (r.uwMult === 0 ? '水中不可用' : '水中伤害减半') + '</span>' : ''}<br>驾驶员 <b>${esc(r.pilot.name)}</b>${supCountsBadge(supCountsOf(r.pilot.id, r.unitId, r.vigor, cfg.ca, cfg.pSpU !== false))}（${STATNAME[r.stat]} ${r.pilot.v}${r.pstat ? ' 含被动+' + r.pstat + '%' : ''}${r.fa && r.fa.k === 'stat' ? '·首动+' + r.fa.v + '%' : ''}）${cfg.crit ? (r.canCrit ? ' · <span style="color:#7df0a8">可暴击' + (r.critRate ? ' ' + r.critRate + '%' : '') + '</span>' : ' · <span style="color:#ff9f43">无暴击能力</span>') : (r.forceCrit ? ' · <span style="color:#7df0a8">必暴(暴击率100%)</span>' : '')}</div></div>
        </div>`).join('');
    $('rlist').querySelectorAll('.rrow').forEach(el => el.onclick = () => { const u = q1('SELECT name FROM units WHERE id=?', [+el.dataset.id]); push({ page: 'unit', title: u.name, id: +el.dataset.id }); });
  };
  v.querySelectorAll('[data-td]').forEach(el => el.onclick = () => { cfg.targetDef = +el.dataset.td; pageRank(v); });
  $('rap').onclick = () => { cfg.targetDef = +$('tdef').value || 0; cfg.targetCharDef = +$('tcdef').value || 0; pageRank(v); };
  v.querySelectorAll('[data-vg]').forEach(el => el.onclick = () => { cfg.vigor = el.dataset.vg; pageRank(v); });
  $('rc').onclick = () => { cfg.crit = !cfg.crit; pageRank(v); };
  if ($('rs3')) $('rs3').onclick = () => { cfg.s3u = !(cfg.s3u !== false); if (!(cfg.s3u !== false)) cfg.sspU = false; pageRank(v); };
  if ($('rspu')) $('rspu').onclick = () => { cfg.spU = !(cfg.spU !== false); if (!(cfg.spU !== false)) cfg.sspU = false; pageRank(v); };
  if ($('rpspu')) $('rpspu').onclick = () => { cfg.pSpU = !(cfg.pSpU !== false); pageRank(v); };
  if ($('rsspu')) $('rsspu').onclick = () => { cfg.sspU = !(cfg.sspU !== false); if (cfg.sspU !== false) { cfg.spU = true; cfg.s3u = true; } pageRank(v); };
  $('rp').onclick = () => { cfg.passive = !cfg.passive; pageRank(v); };
  $('rcp').onclick = () => { cfg.cpassive = !cfg.cpassive; pageRank(v); };
  $('rsk').onclick = () => { cfg.skills = !cfg.skills; if (cfg.skills) cfg.first = false; pageRank(v); };   // 主动技能 ⇄ 首动 二选一
  $('rfirst').onclick = () => { cfg.first = !cfg.first; if (cfg.first) { cfg.skills = false; cfg.mp = false; } pageRank(v); };
  if ($('rfdth')) $('rfdth').onclick = () => { cfg.fdth = !cfg.fdth; pageRank(v); };
  $('rca').onclick = () => { cfg.ca = !cfg.ca; pageRank(v); };
  $('rsupact').onclick = () => { state.supAct = !(state.supAct !== false); pageRank(v); };
  $('rmax').onclick = () => { state.maxOn = !state.maxOn; pageRank(v); };
  if ($('rusk')) $('rusk').onclick = () => { state.uSk = !(state.uSk !== false); pageRank(v); };
  if ($('rurd')) $('rurd').onclick = () => openUltSheet();
  $('rmp').onclick = () => { if (cfg.first) return; cfg.mp = !cfg.mp; pageRank(v); };   // 首动模式下不可开多段增益
  v.querySelectorAll('[data-star]').forEach(el => el.onclick = () => { cfg.star = +el.dataset.star; pageRank(v); });
  v.querySelectorAll('[data-rg]').forEach(el => el.onclick = () => { const r = el.dataset.rg; cfg.range = r === 'all' ? 'all' : (r === 'map' ? 'map' : +r); pageRank(v); });
  v.querySelectorAll('[data-prole]').forEach(el => el.onclick = () => { const r = el.dataset.prole; cfg.prole = r === 'all' ? null : +r; pageRank(v); });
  v.querySelectorAll('[data-prar]').forEach(el => el.onclick = () => { const r = el.dataset.prar; cfg.prar = r === 'all' ? null : +r; pageRank(v); });
  v.querySelectorAll('[data-wat]').forEach(el => el.onclick = () => { const r = el.dataset.wat; cfg.wat = r === 'all' ? null : r; pageRank(v); });
  v.querySelectorAll('[data-atk]').forEach(el => el.onclick = () => { const r = el.dataset.atk; cfg.atk = r === 'all' ? null : r; pageRank(v); });
  v.querySelectorAll('[data-urole]').forEach(el => el.onclick = () => { const r = el.dataset.urole; cfg.urole = r === 'all' ? null : +r; pageRank(v); });
  v.querySelectorAll('[data-rterr]').forEach(el => el.onclick = () => { cfg.terr = el.dataset.rterr; pageRank(v); });
  v.querySelectorAll('[data-rar]').forEach(el => el.onclick = () => { const r = el.dataset.rar; cfg.rarity = r === 'all' ? null : (r === 'ult' ? 'ult' : +r); pageRank(v); });
  $('rtag').onclick = () => openTagPicker('rank', () => { pageRank(v); });
  setTimeout(redraw, 10);
}

/* ------------ 组队页 ------------ */
/* 战舰效果: Leader「全能力值X%」(星数=突破0~3, 按目标标签/系列) + 攻击/HP支援(全队) */
const lbPctOf = lbl => +((String(lbl || '').match(/全能力值\s*(\d+)/) || [])[1] || 0);
function shipEffOf(sup, star) {
  if (!sup) return null;
  let lbs = [];
  try { lbs = JSON.parse(sup.lb_json || '[]'); } catch (e) {}
  const st = Math.max(0, Math.min(3, star | 0));
  const step = lbs.find(x => x.step === st);
  const lbPcts = lbs.length ? lbs.map(x => lbPctOf(x.leader)) : [lbPctOf(sup.leader_desc)];
  const pct = step ? lbPctOf(step.leader) : lbPctOf(sup.leader_desc);
  let tags = [], series = [];
  try {
    const lt = JSON.parse(sup.leader_target_json || '{}');
    const td = tagNameDict(), sd = seriesNameDict();
    tags = [...new Set((lt.unit_tags || []).flatMap(x => String(x).split(',')).map(id => td[+id]).filter(Boolean))];
    series = [...new Set((lt.unit_series || []).filter(Boolean).map(id => sd[+id] || String(id)))];   // 按id取简体名(original series_name 为繁中, 与库内名不一致)
  } catch (e) {}
  return { pct, star: st, lbPcts, atkFlat: sup.atk_support || 0, hpFlat: sup.hp_support || 0, tags, series };
}
const shipMatch = (ship, meta) => !!(ship && ((ship.tags.length && [...meta.tags].some(x => ship.tags.includes(x))) || (ship.series.length && meta.series && ship.series.includes(meta.series))));   // 系列名(简体, 经id换算)与机体系列名匹配

/* ------------ 队伍增强（组队可选生效）------------
   来源: features(feature='team_buff')。原始记录按 攻击/防御 拆成多条 → 按 (来源,目标) 合并。
   效果: 同部队内持有目标标签/系列的机体 攻击力/防御力 +X% */
let _teamBuffs = null;
function teamBuffGroups() {
  if (_teamBuffs) return _teamBuffs;
  const rows = q("SELECT * FROM features WHERE feature='team_buff'");
  const map = {};
  for (const r of rows) {
    let pr = {}; try { pr = JSON.parse(r.params_json || '{}'); } catch (e) {}
    const tags = (pr.target_tags || []).filter(Boolean);
    const key = r.target_type + ':' + r.target_id + '|' + tags.join('·');
    let g = map[key];
    if (!g) g = map[key] = { key, target_type: r.target_type, target_id: r.target_id, label: r.label || '', tags, atk: 0, def: 0, desc: '', descs: [], req: (pr.required_units || []).map(String) };
    for (const gr of (pr.grants || [])) {
      const am = /攻击力提升\s*(\d+)/.exec(gr); if (am) g.atk = Math.max(g.atk, +am[1]);
      const dm = /防御力提升\s*(\d+)/.exec(gr); if (dm) g.def = Math.max(g.def, +dm[1]);
    }
    const d = (pr.desc || '').replace(/\s+/g, ' ').trim();
    if (d && !g.descs.includes(d)) g.descs.push(d);
  }
  Object.values(map).forEach(g => {
    g.desc = g.descs.sort((x, y) => ((y.includes('赋予') || y.includes('賦予')) ? 1 : 0) - ((x.includes('赋予') || x.includes('賦予')) ? 1 : 0)).join('；');
    delete g.descs;
  });
  const owners = {};
  const out = Object.values(map).map(g => {
    const isChar = g.target_type === 'char';
    const o = q1(isChar ? 'SELECT name,icon,role,rarity FROM characters WHERE id=?' : 'SELECT name,icon,role,rarity FROM units WHERE id=?', [+g.target_id]) || {};
    const reqInfo = g.req.map(id => q1('SELECT id,name,icon,role,rarity FROM units WHERE id=?', [+id])).filter(Boolean);
    const reqName = reqInfo.map(x => x.name).join('、');
    return Object.assign(g, { owner: o.name || String(g.target_id), icon: o.icon, role: o.role, rarity: o.rarity, isChar, reqName, reqInfo });
  });
  out.sort((a, b) => (b.atk + b.def) - (a.atk + a.def));
  return (_teamBuffs = out);
}
/* 与战舰对得上的标签: 机体自身标签 ∩ 全部战舰标签(领队技能按标签/系列增益) */
let _shipTagSet = null;
function shipTagSet() {
  if (!_shipTagSet) _shipTagSet = new Set(q('SELECT DISTINCT name FROM supporter_tags').map(r => r.name));
  return _shipTagSet;
}
function shipTagsOfUnit(uid) {
  const st = shipTagSet();
  return q('SELECT t.name FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE ut.unit_id=?', [uid]).map(r => r.name).filter(n => st.has(n));
}
const tbuffMatch = (b, meta) => !!(b.tags.length && (b.tags.some(t => meta.tags.has(t)) || (meta.seriesList ? b.tags.some(t => meta.seriesList.has(t)) : (meta.series && b.tags.includes(meta.series)))));   // 系列: 匹配 seriesList 全集(如 W系列 含 EW版等子系列), 修复只看主系列的漏配
/* 特性页标签/系列筛选 */
let _featRR = null;
function featRarRoleCache() {
  if (_featRR) return _featRR;
  _featRR = {};
  for (const r of q('SELECT id, rarity, role FROM units')) _featRR['u' + r.id] = r;
  for (const r of q('SELECT id, rarity, role FROM characters')) _featRR['c' + r.id] = r;
  return _featRR;
}
function featFilterMatch(tt, tid) {
  const ff = filt('feat');
  const wantRar = ff.rar || null, wantRole = ff.role || null;
  if (!ff.terr && !ff.tags.length && !(ff.series || []).length && !wantRar && !wantRole) return true;
  if (ff.terr && tt === 'unit') {   // 出击场地: ×不能出击的机体不入列(与排行/组队同口径)
    const tu = q1('SELECT terrain_space,terrain_atm,terrain_ground,terrain_surface,terrain_water FROM units WHERE id=?', [+tid]);
    if (terrOf(tu || {}, ff.terr) === 1) return false;
  }
  if (wantRar || wantRole) {
    const rr = featRarRoleCache()[(tt === 'char' ? 'c' : 'u') + tid];
    if (!rr || (wantRar && rr.rarity !== wantRar) || (wantRole && rr.role !== wantRole)) return false;
  }
  const m = (tt === 'char') ? charMetaOf(+tid) : metaOf(+tid);
  const td = tagNameDict(), sd = seriesNameDict();
  const hasT = ff.tags.length > 0;
  const serWant = (ff.series || []).map(id => sd[id]).filter(Boolean);
  const hasS = serWant.length > 0;
  if (!hasT && !hasS) return true;
  let tagHit = true;
  if (hasT) {
    const want = ff.tags.map(id => td[id]).filter(Boolean);
    tagHit = ff.mode === 'and' ? want.every(x => m.tags.has(x)) : want.some(x => m.tags.has(x));
  }
  const serHit = hasS ? (!!m.series && serWant.includes(m.series)) : true;
  if (hasT && hasS) return ff.mode === 'or' ? (tagHit || serHit) : (tagHit && serHit);
  return hasT ? tagHit : serHit;
}
function pageTeam(v) {
  const f = filt('team');
  const t = state.team;
  const sup = t.suppId ? q1('SELECT * FROM supporters WHERE id=?', [t.suppId]) : null;
  t.skills = t.skills || false;
  t.shipStar = t.shipStar || 0;
  t.range = t.range || 'all';
  t.vigor = t.vigor || 'default';
  if (t.ca === undefined) t.ca = true;
  if (t.mp === undefined) t.mp = false;     // 默认「第一击」模式下多阶段增益不可开(仅全技能模式可开)
  if (t.prole === undefined) t.prole = null;     // 驾驶员类型: null=全部 1=攻击型 3=支援型 2=防御型
  if (t.terr === undefined) t.terr = '';         // 出击场地: ''=无限制 / space/atm/ground/surface/water (△红框, ×剔除)
  t.buffs = t.buffs || [];
  t.terrO = t.terrO || false;    // 移动○筛选(需选定出击场地): 仅显示该场地适性○(3)的机体
  t.shieldF = t.shieldF || false;   // 防御盾筛选: 仅对 防御型TOP(输出/eHP) 与 进攻盾TOP 生效
  if (!t.sdefMode) t.sdefMode = '2';   // 第5个top 支援防御搭配档位: '1'=单(+1) '2'=双(+2, 默认) 'all'=全部(+1与+2取最优)
  t.oDef = t.oDef || 0;      // 我方防御+%（全top防御侧: eHP/进攻盾/受）
  t.oHp = t.oHp || 0;        // 我方HP+%（防御eHP/进攻盾）
  t.tdef = t.tdef ?? 10000;      // 靶防御（通用数值）
  t.tcdef = t.tcdef ?? 750;      // 守备
  t.defup = t.defup || 0;        // 目标全能力增加%(攻/防/HP 同时生效, 与三项叠加)
  t.tAtk = t.tAtk || 0;          // 目标攻击+%(作用于反击, 与全能力叠加)
  t.tDef = t.tDef || 0;          // 目标防御+%
  t.tHp = t.tHp || 0;            // 目标HP+%
  t.atkup = t.atkup || 0;        // 攻方 全能力+%
  if (t.star === undefined) t.star = 3;      // UR突破星数(与排行一致)
  if (t.spU === undefined) t.spU = true;     // 非UR SP强化上限
  if (t.s3u === undefined) t.s3u = true;     // 非UR 三星
  if (t.sspU === undefined) t.sspU = true;   // 非UR SSP满10(含SSP武器, 需三星+SP)
  t.dunit = t.dunit || null;     // 指定防御机体
  t.dchar = t.dchar || null;     // 防御方驾驶员
  if (t.dchar && !pilotCanDrive(t.dchar, t.dunit)) t.dchar = null;   // SD绑定驾驶员不能驾驶其他机体
  t.guard = t.guard || false;    // 选择防御(姿态-40%, 带盾再-20%)
  t.sdef = t.sdef || false;      // 支援防御(姿态-40%)
  const du = effUnit(t.dunit ? q1('SELECT * FROM units WHERE id=?', [t.dunit]) : null);   // ULT改造口径
  const dch = t.dchar ? q1('SELECT * FROM characters WHERE id=?', [t.dchar]) : null;
  const dSspOn = !!(du && du.rarity <= 4 && !du.ult && t.sspU !== false && (t.spU !== false) && (t.s3u !== false));
  const dSkill = du ? defenderSkills(du.id, t.dchar, !!t.sdef, dSspOn, scenarioVigorOf(du, t.dchar, t, dSspOn), !!t.ca) : { defPct: 0, cdefPct: 0, redPct: 0, x: [] };
  const hasShield = du ? !!q1("SELECT 1 x FROM features WHERE target_type='unit' AND target_id=? AND feature='shield_defense'", [du.id]) : false;
  const stancePct = stanceReduceOf(t, hasShield);   // 防御/支援防御互斥: 只取一次-40%, 盾牌-20%
  const defReduce = du ? (dSkill.redPct || 0) + stancePct : 0;
  const xSkillOf = (kind, meta) => (dSkill.x || []).reduce((s, r) => s + ((r.kind === kind && xMatch(r, meta)) ? r.v : 0), 0);   // 敌方条件技能按攻击方标签/驾驶员标签
  const dStat = (u, f) => {                                             // 防御方数值: 与排行同口径(SP/SSP/星数; ULT固定值); HP含无条件能力%
    const _hpPct = f === 'hp' ? unitHpPassivePct(u.id) : 0;
    const _hpMul = v => _hpPct ? Math.floor(v * (1 + _hpPct / 100)) : v;
    if (u.ult) return _hpMul(u['max_' + f] || 0);   // ULT: 固定值不乘星(与排行 effStar=0/图鉴「ULT固定值」一致)
    const isUR2 = u.rarity >= 5 && !u.ult;
    const spOn2 = isUR2 ? false : (t.spU !== false);
    const s3On2 = isUR2 ? true : (t.s3u !== false);
    const sspAdd = (!isUR2 && t.sspU !== false && spOn2 && s3On2) ? (sspGainOf(u, 10)[f] || 0) : 0;
    const v2 = isUR2 ? Math.floor((u['max_' + f] || 0) * (STAR_MULT[t.star ?? 3] || 1))
                     : uStatVal(u, f, s3On2, spOn2, sspAdd);   // SSP加在★倍率之前(游戏口径)
    return _hpMul(v2);
  };
  const dInfo = du ? (() => {
    const df0 = dStat(du, 'def');                                         // 非UR: SP×1.4 (+SSP); UR: 突破星数
    const df1 = Math.round(df0 * (1 + (dSkill.defPct + (t.tDef || 0) + (t.defup || 0)) / 100));
    const cdef0 = dch ? pStat(dch, 'defense', t.pSpU) : 0;
    const cdef1 = Math.round(cdef0 * (1 + dSkill.cdefPct / 100));
    const hp0 = dStat(du, 'hp');
    const hp1 = Math.round(hp0 * (1 + ((t.tHp || 0) + (t.defup || 0)) / 100));
    return { df0, df1, cdef0, cdef1, hp0, hp1, ehp: Math.round(hp1 * (1 + df1 / 1000)) };
  })() : null;
  const ship = shipEffOf(sup, t.shipStar);
  const shipTagTxt = ship ? [...ship.tags, ...ship.series].slice(0, 4).join('·') : '';
  const selBuffs = teamBuffGroups().filter(g => t.buffs.includes(g.key));
  const cbOn = !!(t.cbOn && t.cbuff && t.cbuff.tags && t.cbuff.tags.length && t.cbuff.pct > 0);   // 自定义增强: 勾选+多选标签/系列 + 全能力增强%
  const selAll = cbOn ? selBuffs.concat([{ key: '__custom', tags: t.cbuff.tags, atk: t.cbuff.pct, def: t.cbuff.pct, hp: t.cbuff.pct }]) : selBuffs;
  v.innerHTML = `
    <div class="card" style="padding:9px 12px; display:flex; gap:9px; align-items:center; cursor:pointer" id="picks">
      ${sup ? avTagR(sup.icon, null, sup.rarity) : '<span style="width:44px;height:44px;border-radius:9px;background:#0c1424;display:inline-block"></span>'}
      <div style="flex:1; font-size:12.5px">${sup ? esc(sup.name) + ' ' + rarTag(sup.rarity) : '选择战舰（支援人员）'}
        ${sup ? `<br><small style="color:var(--dim);font-size:10.5px">HP支援+${fmt(sup.hp_support)} · 攻击支援+${fmt(sup.atk_support)}${ship.pct ? ' · 队长 全能力+<span style="color:#9fe8c0">' + ship.pct + '%</span>（' + esc(shipTagTxt || '—') + ' · ★' + ship.star + '）' : ''}</small>` : ''}</div>
      <span style="color:var(--dim)">▾</span></div>
    ${sup ? `<div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">战舰突破:</span>
      ${ship.lbPcts.map((p, i) => `<span class="chip ${ship.star === i ? 'on' : ''}" data-lb="${i}">★${i} <b style="font-weight:800">${p}%</b></span>`).join('')}
    </div>` : ''}
    <div class="chips">
      <span class="chip ${!t.skills ? 'on' : ''}" id="m1">第一击 · 被动MP</span>
      <span class="chip ${t.skills ? 'gold' : ''}" id="m2">全技能 · 被动+主动MP</span>
      <span class="chip ${t.first ? 'gold' : ''}" id="tfirst" title="竞技场AI首动(官方优先度): 每动只放1个技能 — 减伤(威力抵御)>+MP>+命中闪避(会被反死)>攻击爆裂>摇摆闪避>增幅(用对应属性武装, 随机体武器变化)>爆击增幅>保留EN; 假设满血满EN·够得着; 首动MP技=超一击+30%">首动${t.first ? ' 开' : ' 关'}</span>
      ${t.first ? `<span class="chip ${t.fdth ? 'gold' : ''}" id="tfdth" title="开: 假设『会被反击杀死』成立 — 「命中率·闪避率提升」挤掉攻击爆裂; 「摇摆闪避」不影响首动伤害">反死风险${t.fdth ? ' 开' : ' 关'}</span>` : ''}
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">UR星数(突破):</span>
      ${[0, 1, 2, 3].map(st => `<span class="chip ${(t.star ?? 3) === st ? 'on' : ''}" data-tstar="${st}">★${st}</span>`).join('')}
    </div>
    <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">非UR强化:</span>
      <span class="chip ${t.s3u !== false ? 'gold' : ''}" id="ts3">三星${t.s3u !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${t.spU !== false ? 'gold' : ''}" id="tspu">SP强化上限${t.spU !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${t.sspU !== false ? 'gold' : ''}" id="tsspu">SSP满10${t.sspU !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${t.pSpU !== false ? 'gold' : ''}" id="tpspu">驾驶员SP${t.pSpU !== false ? ' 开' : ' 关'}</span>
    </div>
    <div class="chips"><span class="hint" style="align-self:center;font-size:10px">ULT固定★0 · SSR及以下按★3 · SSP武器仅在SSP开时参与</span></div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">气势:</span>
      ${[['default', '默认·按MP'], ['mid', '无气势'], ['high', '强势'], ['max', '超强势'], ['supercharged', '超一击']].map(([k, l]) => `<span class="chip ${t.vigor === k ? 'gold' : ''}" data-tvg="${k}">${l}</span>`).join('')}
      <span class="chip ${t.ca ? 'gold' : ''}" id="tca" title="开: 假设 HP/标签/战意等条件被动满足(支援攻击/支援反击/反击另有开关); 关: 按普通攻击如实判定">条件被动${t.ca ? ' 开' : ' 关'}</span>
      <span class="chip ${state.supAct !== false ? 'gold' : ''}" id="tsupact" title="开: 计入「支援攻击/支援反击/反击时」机体/驾驶员被动; 关: 按普通攻击不计入">支援攻击/反击${state.supAct !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${state.maxOn ? 'gold' : ''}" id="tmax" title="开: 条件型叠层被动按最高N%满层; 关: 条件被动按1层; 首动攻击次数型恒0层">max${state.maxOn ? ' 满层' : ' 1层'}</span>
      <span class="chip ${state.uSk !== false ? 'gold' : ''}" id="tusk" title="机体技能(单位技能)是否计入伤害 — 独立于驾驶员主动技能">机体技能${state.uSk !== false ? ' 开' : ' 关'}</span>
      <span class="chip ${state.ultLv ? 'gold' : ''}" id="turd" title="ULT改造: 0/50/100级; ≥50解锁ULT武器, 100解锁三选一能力">ULT改造${state.ultLv ? ' Lv' + state.ultLv : ' 关'}</span>
      <span class="chip ${t.mp ? 'gold' : ''}" id="tmp" ${(t.first || !t.skills) ? 'style="opacity:.45"' : ''} title="${(t.first || !t.skills) ? '第一击/首动模式下不可开启(多阶段增益=超一击EX赋予; 切「全技能」后可开)' : '多阶段增益: 超一击时EX1/EX2赋予'}">多阶段增益${t.mp ? ' 开' : ' 关'}</span>
    </div>
    <div class="subnote" style="text-align:left">气势「默认」按被动MP自动判定：≥4 强势 · ≥8 超强势 · ≥12 超一击（第一击=驾驶员/机体被动；全技能=再+主动技能）；固定气势时被动战意条件按所选气势判定</div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">出击场地:</span>
      ${[['', '无限制'], ['space', '宇宙'], ['atm', '空中'], ['ground', '地上'], ['surface', '水面'], ['water', '水中']].map(([k2, l2]) =>
        `<span class="chip ${(t.terr || '') === k2 ? (k2 === '' ? 'on' : 'gold') : ''}" data-tterr="${k2}">${l2}</span>`).join('')}
      ${t.terr ? `<span class="chip ${t.terrO ? 'gold' : ''}" id="tterro" title="仅显示所选出场场地适性为○(移动不受影响)的机体">移动○筛选${t.terrO ? ' 开' : ' 关'}</span>` : ''}
      <span class="hint" style="align-self:center">红框=移动力减半 · 不能出击的机体不入榜</span>
    </div>
    <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">机体稀有度:</span>
      ${[['all', '全部'], [1, 'N'], [2, 'R'], [3, 'SR'], [4, 'SSR'], [5, 'UR'], ['ult', 'ULT']].map(([k, l]) =>
        `<span class="chip ${((t.rar || 'all') == k) ? 'on' : ''}" data-trar="${k}">${l}</span>`).join('')}
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">驾驶员类型:</span>
      ${[['all', '全部'], [1, '仅攻击型'], [3, '仅支援型'], [2, '仅防御型']].map(([k, l]) =>
        `<span class="chip ${(t.prole || 'all') === k ? 'gold' : ''}" data-prole="${k}">${l}</span>`).join('')}
      <span class="hint" style="align-self:center">（作用于攻击型TOP10；支援/防御列固定用对应类型驾驶员）</span>
    </div>
    <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">驾驶员稀有度:</span>
      ${[['all', '全部'], [1, 'N'], [2, 'R'], [3, 'SR'], [4, 'SSR'], [5, 'UR']].map(([k, l]) =>
        `<span class="chip ${(t.prar || 'all') == k ? (k === 'all' ? 'on' : 'gold') : ''}" data-tprar="${k}">${l}</span>`).join('')}
    </div>
    <div class="chips tight"><span class="hint" style="align-self:center;margin-right:2px">射程:</span>
      <span class="chip ${t.range === 'all' ? 'on' : ''}" data-rg="all">全部</span>
      ${[1, 2, 3, 4, 5].map(nn => `<span class="chip ${t.range === nn ? 'on' : ''}" data-rg="${nn}">${nn}</span>`).join('')}
      <span class="chip ${t.range === 6 ? 'on' : ''}" data-rg="6">6+</span>
      <span class="chip ${t.range === 'map' ? 'gold' : ''}" data-rg="map">MAP</span>
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">武器属性:</span>
      ${[['all', '全部'], ['物理', '物理'], ['光束', '光束'], ['特殊', '特殊']].map(([k, l]) =>
        `<span class="chip ${(t.wat || 'all') === k ? (k === 'all' ? 'on' : 'gold') : ''}" data-twat="${k}">${l}</span>`).join('')}
    </div>
    <div class="chips"><span class="hint" style="align-self:center;margin-right:2px">类型:</span>
      ${[['all', '全部'], ['ranged', '射击'], ['melee', '格斗'], ['awaken', '觉醒']].map(([k, l]) =>
        `<span class="chip ${(t.atk || 'all') === k ? (k === 'all' ? 'on' : 'gold') : ''}" data-tatk="${k}">${l}</span>`).join('')}
    </div>
    <div class="chips" style="align-items:center"><span class="hint" style="align-self:center;margin-right:2px">靶防御:</span>
      ${[['低防', 10000], ['中防', 20000], ['高防', 40000]].map(([l, vv]) => `<span class="chip ${!t.dunit && t.tdef === vv ? 'on' : ''}" data-tdef3="${vv}">${l} ${vv / 1000}k</span>`).join('')}
      <input id="ttdef" type="number" value="${t.tdef}" style="width:74px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">
      <span class="hint">守备</span><input id="ttcdef" type="number" value="${t.tcdef}" style="width:58px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">
      <span class="hint">全能力</span><input id="tdefup" type="number" value="${t.defup || 0}" style="width:44px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">%
      <span class="hint">攻击</span><input id="tdatk" type="number" value="${t.tAtk || 0}" style="width:44px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">%
      <span class="hint">防御</span><input id="tddef" type="number" value="${t.tDef || 0}" style="width:44px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">%
      <span class="hint">HP</span><input id="tdhp" type="number" value="${t.tHp || 0}" style="width:44px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">%
    </div>
    <div class="chips" style="align-items:center"><span class="hint" style="align-self:center;margin-right:2px">我方:</span>
      <span class="hint">攻击</span><input id="tatkup" type="number" value="${t.atkup}" style="width:44px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">%
      <span class="hint">防御</span><input id="todef" type="number" value="${t.oDef || 0}" style="width:44px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">%
      <span class="hint">HP</span><input id="tohp" type="number" value="${t.oHp || 0}" style="width:44px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:4px 8px;font-size:12px">%
      <span class="hint" title="仅我方生效: 攻击→全部输出top(与舰长/队伍增强同口径加算组); 防御→防御eHP/进攻盾/受; HP→防御eHP/进攻盾">（仅我方生效·全top）</span>
    </div>
    <div class="chips" style="align-items:center"><span class="hint" style="align-self:center;margin-right:2px">目标:</span>
      <span class="chip ${t.guard ? 'gold' : ''}" id="tguard">选择防御${t.guard ? ' 开' : ' 关'}</span>
      <span class="chip ${t.sdef ? 'gold' : ''}" id="tsdef">支援防御${t.sdef ? ' 开' : ' 关'}</span>
      <span class="chip ${t.shieldF ? 'gold' : ''}" id="tshieldf" title="仅显示带盾(盾牌防御)机体 — 作用于 防御型TOP(输出/eHP) 与 进攻盾TOP">防御盾筛选${t.shieldF ? ' 开' : ' 关'}</span>
      <span class="hint">姿态-40%${hasShield ? ' · 盾牌防御-20%' : ''}${dSkill.redPct ? ' · 技能减伤-' + dSkill.redPct + '%' : ''}${(dSkill.x || []).length ? ' · 另有敌方条件技能' + dSkill.x.length + '项(按攻击方标签生效)' : ''}${du && !du.defend ? ' · 该机体不能防御' : ''}</span>
    </div>
    <div class="card" style="padding:9px 12px; display:flex; gap:9px; align-items:center; cursor:pointer" id="dpick">
      ${du ? `<span class="dico">${avTagR(du.icon, du.role, du.rarity)}</span>` : '<span style="width:38px;height:38px;border-radius:8px;background:#0c1424;display:inline-block"></span>'}${dch ? `<span class="dico">${avDrv(dch.icon, dch.role, dch.rarity)}</span>` : ''}
      <div style="flex:1; font-size:12.5px">${du ? esc(du.name) + ' ' + rarTag(du.rarity) + (dch ? ' + ' + esc(dch.name) + ' ' + rarTag(dch.rarity) : '') : '选择目标机体和机师（可选，计算目标承受与反击输出）'}
        ${du ? `<br><small style="color:var(--dim);font-size:10.5px">防御 ${fmt(dInfo.df0)}${dInfo.df1 !== dInfo.df0 ? '→<b style="color:#9fd8ff">' + fmt(dInfo.df1) + '</b>' : ''}${(t.tDef || dSkill.defPct) ? '（' + (t.tDef ? '+目标防御' + t.tDef + '%' : '') + (t.tDef && dSkill.defPct ? '，' : '') + (dSkill.defPct ? '技能防御+' + dSkill.defPct + '%' : '') + '）' : ''}${dch ? ' · 守备 ' + fmt(dInfo.cdef0) + (dInfo.cdef1 !== dInfo.cdef0 ? '→<b style="color:#9fd8ff">' + fmt(dInfo.cdef1) + '</b>' : '') : ''} · 耐久 ${fmt(dInfo.hp0)}${dInfo.hp1 !== dInfo.hp0 ? '→<b style="color:#9fe8c0">' + fmt(dInfo.hp1) + '</b>' : ''} · eHP ${fmt(dInfo.ehp)}${defReduce ? ' · <span style="color:#f5c451">承伤-' + defReduce + '%</span>' : ''}</small>` : ''}</div>
      ${du ? '<span id="dclr" style="padding:4px 8px;color:#f66;font-weight:700">✕</span>' : ''}
      <span style="color:var(--dim)">▾</span></div>
    <div class="fbar"><span class="fbtn" id="ttag">☰ 标签/系列 <b>${(f.tags.length + ((f.series || []).length)) || ''}</b></span>
      <span class="fbtn" id="ttagp" style="margin-left:6px">☰ 驾驶员标签/系列 <b>${((filt('teamp').tags || []).length + ((filt('teamp').series || []).length)) || ''}</b></span>
      <span class="ebtn" id="tbuff" style="font-size:11px;padding:4px 10px;border-radius:9px;background:#231a3d;border:1px solid #4a3a7a;color:#c9b8ff;font-weight:700;cursor:pointer">◈ 队伍增强${selBuffs.length ? ' · ' + selBuffs.length + ' 组' : ''}${cbOn ? ' · 自定义+' + t.cbuff.pct + '%' : ''} ›</span></div>
    ${selBuffs.length ? `<div class="chips"><span class="hint" style="align-self:center">已选增强:</span>
      ${selBuffs.map(g => `<span class="tchip2" data-bdel="${esc(g.key)}">${esc(g.tags.join('·'))} 攻+${g.atk}${g.def ? ' 防+' + g.def : ''} <i>×</i></span>`).join('')}</div>` : ''}
    <div id="tarea"></div>`;
  const redraw = () => {
    const isAuto = t.vigor === 'default';
    const pfT = filt('teamp');                       // 驾驶员标签/系列筛选: 作用于全部排行榜的驾驶员候选池
    const pfN = ((pfT.tags || []).length || (pfT.series || []).length) ? pilotFilterOf(pfT) : null;
    /* 一次计算三份驾驶员口径: main=所选类型, sup=仅支援型, def=仅防御型 */
    const du2 = t.dunit ? q1('SELECT * FROM units WHERE id=?', [t.dunit]) : null;
    const dch2 = t.dchar ? q1('SELECT * FROM characters WHERE id=?', [t.dchar]) : null;
    const defBase = dInfo ? dInfo.df0 : (t.tdef ?? 10000);
    const tDefUse = dInfo ? dInfo.df1 : Math.round((t.tdef ?? 10000) * (1 + ((t.tDef || 0) + (t.defup || 0)) / 100));   // 三星+全能力+防御技能
    const tcDefUse = dInfo ? (dInfo.cdef1 || 750) : (t.tcdef ?? 750);
    const _fk = o => JSON.stringify([o.tags || [], (o.series || []).slice().sort(), o.mode || 'and', o.rar ?? null, o.role ?? null]);
    const _gkey = JSON.stringify([   // 性能: 组队全量排名(842k 对)结果缓存 —— 显式列出全部影响输入(归一化为有效值, 防默认字段漂移)
      _fk(f), _fk(filt('teamp')),
      !!t.skills, !!t.first, !!t.fdth, !!t.cbOn, (t.cbuff && t.cbuff.tags) ? [t.cbuff.tags, t.cbuff.pct] : null, t.shipStar ?? 0, t.range ?? 'all', t.vigor || 'default', t.ca !== false, t.mp !== false,
      !!t.guard, !!t.sdef,   // 选择防御(姿态-40%/盾-20%)·支援防御(-40%+技能防御) — 影响 targetDef/defReduce, 必须入缓存键(曾漏→开关不生效)
      t.prole ?? null, t.terr || '', !!t.terrO, t.buffs || null, t.sdefMode || '2', t.tdef ?? 10000, t.tcdef ?? 750, t.defup ?? 0, t.tAtk ?? 0, t.tDef ?? 0, t.tHp ?? 0, t.atkup ?? 0, t.oDef ?? 0, t.oHp ?? 0,
      t.s3u !== false, t.spU !== false, t.sspU !== false, t.pSpU !== false, t.star ?? 3, t.rar ?? null, t.urole ?? null,
      t.wat ?? null, t.atk ?? null, t.suppId ?? null, t.dunit ?? null, t.dchar ?? null, t.prar ?? null, state.uSk !== false, state.supAct !== false, state.maxOn ? 1 : 0, state.ultLv || 0, JSON.stringify(state.ultSkill)]);
    let G;
    if (state.teamCache && state.teamCache.key === _gkey) G = state.teamCache.G;
    else {
      G = buildRanking(f, { targetDef: tDefUse, targetCharDef: tcDefUse, vigor: isAuto ? 'mid' : t.vigor, crit: false, range: t.range, rarity: t.rar || null, urole: t.urole || null, wat: t.wat || null, atk: t.atk || null, terr: t.terr || null, terrO: !!t.terrO },
      { passive: true, cpassive: true, skills: !!t.skills, first: !!t.first, fdth: !!t.fdth, condAll: !!t.ca, autoVigor: isAuto, multiPhase: !!t.mp, ship, teamBuffs: selAll, allPct: t.atkup || 0, defReduce,
        star: t.star ?? 3, spU: t.spU !== false, s3u: t.s3u !== false, sspU: t.sspU !== false, pSpU: t.pSpU !== false, pilotRar: t.prar || null,
        enemyMeta: du ? { ...metaOf(du.id), ctags: (dch && charMetaAll()[dch.id]) ? charMetaAll()[dch.id].tags : null } : null,
        defReduceFn: du ? (meta => defReduce + xSkillOf('redPct', meta)) : undefined,
        targetDefFn: dInfo ? (meta => Math.round(dInfo.df0 * (1 + (dSkill.defPct + (t.tDef || 0) + (t.defup || 0) + xSkillOf('defPct', meta)) / 100))) : undefined,
        pilotGroups: { main: t.prole || null, sup: 3, def: 2 },
        pilotFn: pfN, uSk: state.uSk !== false });
      state.teamCache = { key: _gkey, G };
    }
    const atk = G.main.filter(r => r.unit.role === 1).slice(0, 10);
    const sup3 = G.sup.filter(r => r.unit.role === 3).slice(0, 10);         // 支援型机体 × 仅支援型驾驶员(前10)
    const atkSup = G.sup.filter(r => r.unit.role === 1).slice(0, 10);      // 攻击型机体 × 仅支援型驾驶员
    const defOut = G.def.filter(r => r.unit.role === 2 && (!t.shieldF || shieldUnitSet().has(r.unitId))).slice(0, 10);      // 防御型机体 × 仅防御型驾驶员(输出, 前10; 防御盾筛选)
    const uw = unitWhere('unit', { ...f, sp: 0, ssp: 0, rar: t.rar || null, role: t.urole || null });   // 防御型eHP榜同稀有度/类型口径
    const dw = (uw.where ? uw.where + ' AND' : 'WHERE') + ' u.role=2';
    const defStat = (u, f) => {                                   // 与排行同口径: 非UR按 SP/SSP 开关, UR 按突破星数, ULT固定值; HP含无条件能力%
      const _hpPct = f === 'hp' ? unitHpPassivePct(u.id) : 0;
      const _hpMul = v => _hpPct ? Math.floor(v * (1 + _hpPct / 100)) : v;
      if (u.ult) return _hpMul(u['max_' + f] || 0);   // ULT: 固定值不乘星(与排行 effStar=0/图鉴「ULT固定值」一致; 曾误入SSR路径×1.4)
      const isUR = u.rarity >= 5 && !u.ult;
      const spOn = isUR ? false : (t.spU !== false);
      const s3On = isUR ? true : (t.s3u !== false);
      const sspAdd = (!isUR && t.sspU !== false && spOn && s3On) ? (sspGainOf(u, 10)[f] || 0) : 0;
      const v = isUR ? Math.floor((u['max_' + f] || 0) * (STAR_MULT[t.star ?? 3] || 1))
                     : uStatVal(u, f, s3On, spOn, sspAdd);   // SSP加在★倍率之前(游戏口径)
      return _hpMul(v);
    };
    const defUnits = dedupeUnits(q(`SELECT u.* FROM units u ${dw}`, uw.args)).map(u => {
      const meta = metaOf(u.id);
      const hit = shipMatch(ship, meta);
      let bDef = 0, bHp = 0, bHit = false;
      for (const b of selAll) if (tbuffMatch(b, meta)) { bDef += b.def; bHp += (b.hp || 0); bHit = true; }   // 队伍增强/自定义增强: 攻防+HP(自定义全能力=攻防hp机动, 不含EN)
      const hp0 = defStat(u, 'hp'), df0 = defStat(u, 'def');   // 星级(UR)/SP+SSP(非UR) 口径, 与机体页显示一致
      const hp = Math.floor(hp0 * (1 + ((hit ? ship.pct : 0) + bHp + (t.oHp || 0)) / 100)) + (ship ? ship.hpFlat : 0);
      const ub = defenderSkills(u.id, null, true, false, (isAuto ? 'mid' : t.vigor), !!t.ca);   // 机体侧被动防御%(含 max 满层)
      const df = Math.floor(df0 * (1 + ((hit ? ship.pct : 0) + bDef + (t.oDef || 0) + ub.defPct) / 100));   // 我方防御: 防御侧生效 + 被动防御%
      return { u, hp0, df0, hp, df, ub, defPct: ub.defPct, val: Math.round(hp * (1 + df / 1000)), shipHit: hit, buffDef: bDef, buffHit: bHit, terrHalf: t.terr ? terrOf(u, t.terr) === 2 : false };
    }).filter(r => (!t.terr || (terrOf(r.u, t.terr) !== 1 && (!t.terrO || terrOf(r.u, t.terr) === 3))) && (!t.shieldF || shieldUnitSet().has(r.u.id)));   // 排序在「受」计算后: 选目标→按剩余HP, 未选→eHP
    /* 双支援防御(支援防御+2次)驾驶员: eHP行推荐「综合防御能力」最高者 —
       支援防御时防御力提升(defPct, 作用于机体防御) + 守备值(含守备值提升) + 标签减伤(≈×10 防御点) */
    const _so2 = charSupEntries();
    const sdefCands = [];
    for (const cid of new Set([...Object.keys(_so2.base), ...Object.keys(_so2.sp)])) {
      const lst = mergeSp(_so2.base[cid] || [], t.pSpU !== false ? (_so2.sp[cid] || []) : null);
      const nDef = lst.filter(p => p.kind === 'def').length;
      if (t.sdefMode === '1' ? nDef !== 1 : t.sdefMode === 'all' ? nDef < 1 : nDef < 2) continue;   // 单(+1)/双(+2, 默认)/全部(+1与+2)
      const c = q1('SELECT id,name,icon,role,rarity,series_set_id,max_defense,sp_max_defense FROM characters WHERE id=?', [+cid]);
      if (!c || (t.prar && c.rarity !== t.prar)) continue;
      if (pfN && !pfN(c)) continue;
      sdefCands.push(c);
    }
    const vgDef = isAuto ? 'mid' : t.vigor;   // 我方防御机气势口径(与 supCountsOf 一致; auto 无该机MP模型取中档)
    /* 攻方(目标)meta 与 敌方条件被动判定: 「发起对战的敌方包含…」类(对XX增加攻击/防御)按对方标签/系列匹配;
       未选目标时按条件被动开关假设满足(xOfOn assume) */
    const metaAtk = du ? Object.assign({}, metaOf(du.id), { ctags: (dch && charMetaAll()[dch.id]) ? charMetaAll()[dch.id].tags : null }) : null;
    const xOfOn = (o, kind, meta, assume) => {   // 有目标按标签匹配; 无目标(假设模式)时驾驶员标签类条件互斥取最高
      let s = 0, cm = 0;
      for (const rr of (o.x || [])) {
        if (rr.kind !== kind) continue;
        if (meta) { if (xMatch(rr, meta)) s += rr.v; }
        else if (assume) { if (rr.ctags && rr.ctags.length) { if (rr.v > cm) cm = rr.v; } else s += rr.v; }
      }
      return s + cm;
    };
    /* 防御侧生效条件被动注明(5/6 TOP): 机体+搭配机师 「敌「XX」…」条目标注; 有目标按标签匹配, 无目标按条件被动假设满足(渲染加(假设)) */
    const xHitOf = e => metaAtk ? xMatch(e, metaAtk) : (t.ca !== false);
    const _K2TX = { defPct: v => '防+' + v + '%', cdefPct: v => '守备+' + v + '%', redPct: v => '减伤' + v + '%' };
    const xNote = (src, e) => {
      const uq = a => [...new Set(a || [])];
      const nm = (e.series && e.series.length) ? '「' + uq(e.series).join('/') + '」系列'
        : ((e.tags && e.tags.length) ? '「' + uq(e.tags).join('/') + '」标签'
          : ((e.ctags && e.ctags.length) ? '驾驶员「' + uq(e.ctags).join('/') + '」' : ''));
      return src + ' 敌' + nm + ' ' + ((_K2TX[e.kind] || (v => v + '%'))(e.v));
    };
    const xKey = e => JSON.stringify([e.kind, e.v, e.tags, e.series, e.ctags]);
    const cnoteOf = (ubx, dkx) => {   // 机体x + 机师x(dk多出部分), 仅列匹配生效条目
      const kb = {};
      for (const e of (ubx || [])) kb[xKey(e)] = (kb[xKey(e)] || 0) + 1;
      const dn = [];
      for (const e of (dkx || [])) { const k = xKey(e); if (kb[k]) { kb[k]--; continue; } dn.push(e); }
      const out = [];
      const addL = (src, list) => {
        const hit = list.filter(e => metaAtk ? xMatch(e, metaAtk) : (t.ca !== false));
        if (metaAtk) { for (const e of hit) out.push(xNote(src, e)); return; }
        const bm = {};   // 假设模式: 驾驶员标签类互斥, 每类只列最高一项(与计入一致)
        for (const e of hit) { if (e.ctags && e.ctags.length) { if (!bm[e.kind] || e.v > bm[e.kind].v) bm[e.kind] = e; } else out.push(xNote(src, e)); }
        for (const k in bm) out.push(xNote(src, bm[k]));
      };
      addL('机体', ubx || []); addL('机师', dn);
      return out.join('、');
    };
    for (const r of defUnits) {
      const ub = r.ub || defenderSkills(r.u.id, null, true, false, vgDef, !!t.ca);   // 机体侧(常数, 用于取驾驶员增量; 复用已算的被动防御%)
      let best = null;
      for (const c of sdefCands) {
        if (!pilotCanDrive(c.id, r.u.id)) continue;
        const nDef2 = supCountsOf(c.id, r.u.id, isAuto ? 'mid' : t.vigor, !!t.ca, t.pSpU !== false).def;
        if (t.sdefMode === '1' ? nDef2 !== 1 : t.sdefMode === 'all' ? nDef2 < 1 : nDef2 < 2) continue;
        const dk = defenderSkills(r.u.id, c.id, true, false, vgDef, !!t.ca);
        const _x = (o, k2) => xOfOn(o, k2, metaAtk, t.ca !== false);   // 敌方条件(对XX)防御类: 推荐机师评分计入(有目标按标签匹配, 无目标假设满足)
        const dPct = (dk.defPct - ub.defPct) + _x(dk, 'defPct') - _x(ub, 'defPct'),
              cPct = (dk.cdefPct - ub.cdefPct) + _x(dk, 'cdefPct') - _x(ub, 'cdefPct'),
              rPct = (dk.redPct - ub.redPct) + _x(dk, 'redPct') - _x(ub, 'redPct');
        const guardEff = Math.round(pStat(c, 'defense', t.pSpU !== false) * (1 + cPct / 100));
        const score = Math.round(r.df0 * dPct / 100) + guardEff + rPct * 10;
        if (!best || score > best.score) best = { c, dPct, cPct, rPct, guardEff, score, n: nDef2, dk };
      }
      if (best) r.sdef = best;
      const sspN = r.u.rarity <= 4 && !r.u.ult && t.sspU !== false && t.spU !== false && t.s3u !== false;   // recvOn 同口径
      const ubN = defenderSkills(r.u.id, null, !!t.sdef, sspN, vgDef, !!t.ca);
      const dkN = best ? defenderSkills(r.u.id, best.c.id, !!t.sdef, sspN, vgDef, !!t.ca) : null;
      r.cnote = cnoteOf(ubN.x, dkN ? dkN.x : null);
    }
    const modeTxt = (t.first ? '首动' : (t.skills ? '全技能·被动+主动MP' : '第一击·被动MP')) + (t.first && t.fdth ? '·反死风险' : '') + (ship ? ' +舰' : '') + (selBuffs.length ? ' +阵' : '') + (cbOn ? ' +自定义' : '');
    const _folded = k2 => !!(state.teamFold && state.teamFold[k2]);
    /* 进攻盾 TOP5: 可参与「反击时支援防御」(trait90, 需搭乘含对应标签/系列的机体) — 按有效耐久 eHP 排 */
    const csDrv = counterShieldDrivers().filter(d => (!t.prar || d.rarity === t.prar) && (!pfN || pfN(d)));
    let csTop = [], csAll = [];
    if (csDrv.length) {
      for (const u of dedupeUnits(q(`SELECT u.* FROM units u ${uw.where}`, uw.args))) {
        const meta = metaOf(u.id);
        const d = csDrv.find(d2 => pilotCanDrive(d2.id, u.id) &&
          ((d2.reqTags.length && d2.reqTags.some(x => meta.tags.has(x))) || (d2.reqSeries.length && d2.reqSeries.some(x => meta.seriesList.has(x)))));
        if (!d) continue;
        if (t.terr && terrOf(u, t.terr) === 1) continue;   // 出击不能不入榜
        if (t.terr && t.terrO && terrOf(u, t.terr) !== 3) continue;   // 移动○筛选
        if (t.shieldF && !shieldUnitSet().has(u.id)) continue;   // 防御盾筛选
        const hit = shipMatch(ship, meta);
        let bDef = 0, bHp = 0, bHit = false;
        for (const b of selAll) if (tbuffMatch(b, meta)) { bDef += b.def; bHp += (b.hp || 0); bHit = true; }   // 队伍增强/自定义增强: 攻防+HP
        const hp0 = defStat(u, 'hp'), df0 = defStat(u, 'def');
        const hp = Math.floor(hp0 * (1 + ((hit ? ship.pct : 0) + bHp + (t.oHp || 0)) / 100)) + (ship ? ship.hpFlat : 0);
        const ubPre = defenderSkills(u.id, null, !!t.sdef, false, vgDef, !!t.ca);
        const df = Math.floor(df0 * (1 + ((hit ? ship.pct : 0) + bDef + (t.oDef || 0) + ubPre.defPct) / 100));
        const o = { u, d, hp0, df0, hp, df, val: Math.round(hp * (1 + df / 1000)), shipHit: hit, buffDef: bDef, buffHit: bHit, terrHalf: t.terr ? terrOf(u, t.terr) === 2 : false };
        const sspC = u.rarity <= 4 && !u.ult && t.sspU !== false && t.spU !== false && t.s3u !== false;   // recvOn 同口径
        const ubC = defenderSkills(u.id, null, !!t.sdef, sspC, vgDef, !!t.ca);
        const dkC = defenderSkills(u.id, d.id, !!t.sdef, sspC, vgDef, !!t.ca);
        o.cnote = cnoteOf(ubC.x, dkC.x);
        csAll.push(o);
      }
    }   // csAll 排序在「受」计算后统一处理
    /* 目标(du+dch)对我方防御机体的最大攻击输出「受」: 开关口径与我方进攻一致(星数/SP/SSP/驾驶员SP/气势/首动·全技能/条件被动/多阶段);
       「选择防御/支援防御」对我方该机体防御时生效(姿态40 + 支援防御40 + 该机体带盾-20), 守备取 靶守备输入 */
    const recvOn = (r) => {
      const defU = r && r.u;
      if (!du || !defU) return null;
      const metaT = metaOf(du.id), metaD = metaOf(defU.id);
      const dchD = (r.sdef && r.sdef.c) ? r.sdef.c : (r.d || null);   // 防御机搭配驾驶员(支援防御推荐/进攻盾候选) — 与正向目标口径对称
      const metaDefX = Object.assign({}, metaD, { ctags: (dchD && charMetaAll()[dchD.id]) ? charMetaAll()[dchD.id].tags : null });   // 我方防御侧(含搭配驾驶员标签): 供目标(攻方)「对XX」类被动匹配
      const isNonURT = du.rarity <= 4 && !du.ult;
      const spOnT = isNonURT && t.spU !== false, s3OnT = isNonURT ? (t.s3u !== false) : true;
      const sspOnT = isNonURT && t.sspU !== false && spOnT && s3OnT;
      const _ub = du.ult ? { base: du.max_atk || 0, mult: 1 }   // ULT: 固定值(与排行 effStar=0 一致)
        : (isNonURT ? uStatBase(du, 'atk', s3OnT, spOnT) : { base: du.sp_max_atk || du.max_atk, mult: STAR_MULT[t.star ?? 3] || 1 });
      const uBaseT = Math.floor((_ub.base + (sspOnT ? sspGainOf(du, 10).atk : 0)) * _ub.mult);
      const skillsOn = t.first ? false : !!t.skills;
      const mpT = (isAuto && t.dchar) ? mpOf(du.id, t.dchar, skillsOn, t.ca, t.pSpU, sspOnT) : 0;
      const mpT0 = t.dchar ? mpOf(du.id, t.dchar, false, t.ca, t.pSpU, sspOnT) : 0;   // 被动MP: 首动MP提升释放条件用
      const vgT = scenarioVigorOf(du, t.dchar, t, sspOnT);
      const faRowsT = (t.first && t.dchar) ? charActSkillRows(t.dchar, t.pSpU !== false) : null;
      const bT = t.dchar ? charBonus(t.dchar, vgT, { passive: true, cpassive: true, skills: skillsOn, condAll: !!t.ca, first: !!t.first, unitId: du.id, upassive: true, multiPhase: !!(t.mp && !t.first), pSpU: t.pSpU !== false, ussp: sspOnT, enemyMeta: metaDefX }, metaT) : { dmg: 0, melee: 0, ranged: 0, awaken: 0, atk: 0 };   // 目标机师「对XX」增伤: 按我方防御机(+搭配机师)标签匹配
      const isNonURD = defU.rarity <= 4 && !defU.ult;
      const sspOnD = isNonURD && t.sspU !== false && (t.spU !== false) && (t.s3u !== false);
      const dSkillD = defenderSkills(defU.id, dchD ? dchD.id : null, !!t.sdef, sspOnD, vgDef, !!t.ca);
      const xD = kind => xOfOn(dSkillD, kind, metaAtk, t.ca !== false);   // 我方防御机/机师 敌方条件(对XX)防御类: 按攻方=目标标签匹配
      const stanceD = (t.guard ? 40 : 0) + (t.sdef ? 40 : 0) + ((t.guard || t.sdef) && shieldUnitSet().has(defU.id) ? 20 : 0);
      const defReduceD = (dSkillD.redPct || 0) + xD('redPct') + stanceD;
      const defD = Math.round((r.df || defStat(defU, 'def')) * (1 + ((dSkillD.defPct || 0) + xD('defPct')) / 100));   // r.df 已含 舰/队伍增强/我方攻防
      const cdefD = dchD ? Math.round(pStat(dchD, 'defense', t.pSpU) * (1 + ((dSkillD.cdefPct || 0) + xD('cdefPct')) / 100)) : (t.tcdef ?? 750);   // 守备: 搭配驾驶员守备(与正向目标守备对称), 无则取输入
      let best = 0;
      for (const w of weaponsForUnit(du)) {
        if (w.is_ssp && !sspOnT) continue;
        if (!vigorAllows(w.id, vgT, isAuto ? mpT : null)) continue;
        const attrs = WATTR[w.attack_attr] || ['melee'];
        const faT = faRowsT ? firstActOfRows(faRowsT, attrs, t.fdth, mpT0) : null;
        const statAdd = (faT && faT.k === 'stat') ? faT.v : 0;
        let cAtkT = 0;
        if (t.dchar) { cAtkT = attrs.reduce((m, a) => Math.max(m, Math.floor(pStat(dch, a, t.pSpU) * (1 + ((bT[a] || 0) + (faT && faT.k === 'stat' && faT.stat === a ? statAdd : 0)) / 100))), 0); }
        const uAtkT = Math.floor(uBaseT * (1 + (unitPassiveAtkPct(du.id, vgT, t.ca, metaDefX, sspOnT, !!t.first) + (state.uSk !== false ? unitSkillAtkPct(du.id) : 0) + (bT.atk || 0) + (t.tAtk || 0) + (t.defup || 0)) / 100));   // 目标攻击/全能力: 对反击生效; 「对XX(我方防御机+机师)」条件按标签匹配
        const pcT = pilotCritInfo(du.id, t.dchar, metaT, { passive: true, cpassive: true, skills: skillsOn, condAll: !!t.ca, vigor: vgT, multiPhase: !!(t.mp && !t.first), pSpU: t.pSpU !== false, ussp: sspOnT });
        const w94T = wTraitsOf(w.id, null, true).some(x => x.trait_type === 94);
        const rateT = Math.min(100, (w.crit_rate || 0) + pcT.rate);
        const critOn = (pcT.guar || w94T || rateT >= 100) && (pcT.guar || w94T || rateT > 0);
        const eeT = bT.dmg + (faT && faT.k === 'burst' ? faT.v : 0) + ultDmgPct(du);
        const d = Engine.damageWithWeapon(uAtkT, cAtkT, w, wTraitsOf(w, metaDefX, t.ca), 5, defD, cdefD, { vigor: vgT, crit: critOn, ee: eeT, defReduce: defReduceD });
        const uw = t.terr === 'water' ? uwMult(w) : 100;
        const dm = uw === 100 ? d.final : Math.floor(d.final * uw / 100);
        if (dm > best) best = dm;
      }
      return best || null;
    };
    /* 支援防御移动力: 基础(defStat+SSP) 与 move6/7 特性行(机体被动+搭配机师被动) 取最大适用值 */
    const _mvRows = (() => { const m = {}; for (const x of q("SELECT target_id, params_json FROM features WHERE feature IN ('move6','move7')")) { let p = {}; try { p = JSON.parse(x.params_json || '{}'); } catch (e) {} (m[x.target_id] = m[x.target_id] || []).push({ pilot: p.pilot || 0, total: p.total || 0, desc: p.desc || '' }); } return m; })();
    const supMoveOf = (u, pilotId) => {
      const sspOn2 = u.rarity <= 4 && !u.ult && t.sspU !== false && t.spU !== false && t.s3u !== false;
      let m = (u.max_mov || u.mov || 0) + (sspOn2 ? (sspMovOf(u) || 0) : 0);   // 移动力: 取原值(★突破倍率不作用于移动力; 曾误用defStat×倍率)
      for (const x of (_mvRows[u.id] || [])) {
        if (x.desc.indexOf('SSP') >= 0 && !sspOn2) continue;   // 该行依赖SSP强化, SSP关则不适用
        if (x.pilot && x.pilot !== (pilotId || 0)) continue;   // 需特定驾驶员被动: 搭配机师匹配才计
        m = Math.max(m, x.total);
      }
      return m;
    };
    defUnits.forEach(r => { r.recv = recvOn(r); r.mob = supMoveOf(r.u, r.sdef && r.sdef.c ? r.sdef.c.id : 0); });
    csAll.forEach(r => { r.recv = recvOn(r); r.mob = supMoveOf(r.u, r.d ? r.d.id : 0); });
    /* 选定目标: 后两top 按剩余HP(hp-受) 由多到少排序; 未选目标: 维持 eHP 排序 */
    const remSort = (a, b) => (du && a.recv != null && b.recv != null) ? ((b.hp - b.recv) - (a.hp - a.recv) || (b.val - a.val)) : (b.val - a.val);
    state._recv = {};
    for (const r of csAll) if (r.recv != null) state._recv[r.u.id] = r.recv;
    for (const r of defUnits) if (r.recv != null) state._recv[r.u.id] = r.recv;
    csAll.sort(remSort); csTop = csAll.slice(0, 5);
    defUnits.sort(remSort); defUnits.splice(10);
    const csCard = `<div class="card" style="padding:6px 12px">
      <h4 style="color:#f5c451;display:flex;justify-content:space-between;align-items:baseline;gap:8px"><span>进攻盾 TOP5 · 有效耐久 eHP（可参与「反击时支援防御」）</span><span class="foldbtn" data-fold="team_cs" style="cursor:pointer;font-size:10px;opacity:.85;flex:none">${_folded('team_cs') ? '▸ 展开' : '▾ 折叠'}</span></h4>
      <div data-fbody="team_cs"${_folded('team_cs') ? ' style="display:none"' : ''}>
      ${csTop.map((r, i) => `<div class="trow${r.terrHalf ? ' halfmove' : ''}" data-id="${r.u.id}" style="cursor:pointer"><span class="rk ${i < 3 ? 'g' : ''}">${i + 1}</span>
        <span class="ticon-col">${avTagR(r.u.icon, r.u.role, r.u.rarity)}<span class="avw avsm"><span class="picon sm">${imgTag(r.d.icon)}</span>${roleBadge(r.d.role)}${rarB(r.d.rarity)}</span></span>
        <div class="nm">${esc(r.u.name)} ${rarTag(r.u.rarity)}<small>${esc(r.d.name)} <span class="tagx cond" style="margin-left:2px">${esc(r.d.reqTags.length ? 'TAG ' + r.d.reqTags.join('·') : 'SERIES ' + r.d.reqSeries.join('·'))}</span><br>耐久 ${fmt(r.hp0)} · 防御 ${fmt(r.df0)}${r.shipHit ? ' · <span style="color:#9fe8c0">舰+' + ship.pct + '%</span>' : ''}${r.buffHit ? ' · <span style="color:#c9b8ff">阵 防+' + r.buffDef + '%</span>' : ''}${r.cnote ? ' · <span style="color:#f5c451">条件' + (du ? '' : '(假设)') + ':' + esc(r.cnote) + '</span>' : ''}</small></div>
        <span class="val g">eHP ${fmt(r.val)}<br><span style="font-size:9.5px;color:var(--dim);font-weight:400;white-space:nowrap">${terrMini(r.u.id)}</span><br><span style="font-size:9.5px;font-weight:400;white-space:nowrap">${shieldMark(r.u.id)}${r.defPct ? ' <span style="color:#7df0a8;font-weight:700">防+' + r.defPct + '%</span>' : ''}${r.mob != null ? ' <span style="color:#8fc4ff;font-weight:700;font-size:9.5px;white-space:nowrap">移' + r.mob + '</span>' : ''}</span>${r.recv != null ? '<br><span style="color:#ff9f43;font-weight:700;font-size:9.5px;white-space:nowrap">受 ' + fmt(r.recv) + ' 剩' + (r.hp ? Math.max(0, Math.round((r.hp - r.recv) / r.hp * 100)) : 0) + '%</span>' : ''}${r.hp ? '<br><span style="font-size:9.5px;color:var(--dim);font-weight:400;white-space:nowrap">HP ' + fmt(r.hp) + '</span>' : ''}</span></div>`).join('') || '<div class="kv" style="color:var(--dim)">无可选目标</div>'}
      </div>
    </div>`;
    if (sup3) for (const r of sup3) {   // 支援型行: 机体全部武器的增伤/降防特效并集(叠驾驶员88/SSP)
      const sspWOn2 = r.unit.rarity <= 4 && !r.unit.ult && t.sspU !== false && (t.spU !== false) && (t.s3u !== false);
      r.fxSup = unitDamageFxOf(r.unitId, r.pilot.id, f, sspWOn2, t.pSpU !== false,
        { condAll: !!t.ca, vigor: r.vigor, sspU: t.sspU !== false,
          enemyMeta: du ? { ...metaOf(du.id), ctags: (dch && charMetaAll()[dch.id]) ? charMetaAll()[dch.id].tags : null } : null });
    }
    const section = (title, color, arr, isDef, showFx, fkey, terrOn, extra) => `<div class="card" style="padding:6px 12px">
      <h4 style="color:${color};display:flex;justify-content:space-between;align-items:baseline;gap:8px"><span>${title}${extra || ''}</span>${fkey ? `<span class="foldbtn" data-fold="${fkey}" style="cursor:pointer;font-size:10px;opacity:.85;flex:none">${_folded(fkey) ? '▸ 展开' : '▾ 折叠'}</span>` : ''}</h4>
      <div data-fbody="${fkey || ''}"${fkey && _folded(fkey) ? ' style="display:none"' : ''}>
      ${arr.map((r, i) => `<div class="trow${r.terrHalf ? ' halfmove' : ''}" data-id="${isDef ? r.u.id : r.unitId}"${isDef && r.sdef ? ' data-sdef="' + r.sdef.c.id + '"' : ''} style="cursor:pointer"><span class="rk ${i < 3 ? 'g' : ''}">${i + 1}</span>
        ${isDef ? `<span class="ticon-col">${avTagR(r.u.icon, r.u.role, r.u.rarity)}${r.sdef ? `<span class="avw avsm"><span class="picon sm">${imgTag(r.sdef.c.icon)}</span>${roleBadge(r.sdef.c.role)}${rarB(r.sdef.c.rarity)}</span>` : ''}</span>` : `<span class="ticon-col">${avTagR(r.unit.icon, r.unit.role, r.unit.rarity)}<span class="avw avsm"><span class="picon sm">${imgTag(r.pilot.icon)}</span>${roleBadge(r.pilot.role)}${rarB(r.pilot.rarity)}</span></span>`}
        <div class="nm">${esc(isDef ? r.u.name : r.unit.name)} ${rarTag(isDef ? r.u.rarity : r.unit.rarity)}${ultB(isDef ? r.u : r.unit)}<small>${isDef
          ? '耐久 ' + fmt(r.hp0) + ' · 防御 ' + fmt(r.df0) + (r.shipHit ? ' · <span style="color:#9fe8c0">舰+' + ship.pct + '%</span>' : '') + (r.buffHit ? ' · <span style="color:#c9b8ff">阵 防+' + r.buffDef + '%</span>' : '') + (r.sdef ? ' · <span style="color:#8fc4ff">支防+' + (r.sdef.n || 2) + ' ' + esc(r.sdef.c.name) + (r.sdef.dPct ? ' 防+' + r.sdef.dPct + '%' : '') + ' 守备' + fmt(r.sdef.guardEff) + (r.sdef.cPct ? '(' + (r.sdef.cPct > 0 ? '+' : '') + r.sdef.cPct + '%)' : '') + (r.sdef.rPct ? ' 减伤' + r.sdef.rPct + '%' : '') + '</span>' : '') + (r.cnote ? ' · <span style="color:#f5c451">条件' + (du ? '' : '(假设)') + ':' + esc(r.cnote) + '</span>' : '')
          : esc(r.pilot.name) + supCountsBadge(supCountsOf(r.pilot.id, r.unitId, r.vigor, t.ca, t.pSpU !== false)) + ' · ' + (isAuto ? (r.mp ? Engine.VIGOR[r.vigor].label + '(MP' + r.mp + ')' : '气势0') : '气势' + Engine.VIGOR[r.vigor].label) + ' · ' + esc(r.weapon.name) + '<span style="color:#8fc4ff"> 射程' + r.weapon.range_min + '-' + r.weapon.range_max + (r.weapon.type === 3 ? '·MAP' : '') + (AATTR[r.weapon.weapon_attr] ? '·' + AATTR[r.weapon.weapon_attr] : '') + '</span>' + (r.uwMult != null && r.uwMult < 100 ? ' · <span style="color:#ff9f43">' + (r.uwMult === 0 ? '水中不可用' : '水中伤害减半') + '</span>' : '') + (showFx && r.fxSup ? ' · <span style="color:#f5c451">' + esc(r.fxSup) + '</span>' : '') + (r.shipHit ? ' · <span style="color:#9fe8c0">舰+' + r.shipPct + '%</span>' : '') + (r.buffHit ? ' · <span style="color:#c9b8ff">阵 攻+' + r.buffAtk + (r.buffDef ? '/防+' + r.buffDef : '') + '%</span>' : '') + (r.notice ? ' · <span style="color:#f5c451">条件:' + esc(r.notice) + '</span>' : '') + (r.forceCrit ? ' · <span style="color:#7df0a8">必暴</span>' : '')}</small></div>
        <span class="val g">${isDef ? 'eHP ' + fmt(r.val) : fmt(r.dmg)}${!isDef && r.uAtk ? '<br><span style="font-size:9.5px;color:var(--dim);font-weight:400;white-space:nowrap">攻击力 ' + fmt(r.uAtk) + '</span>' : ''}${terrOn ? '<br><span style="font-size:9.5px;color:var(--dim);font-weight:400;white-space:nowrap">' + terrMini(isDef ? r.u.id : r.unitId) + '</span><br><span style="font-size:9.5px;font-weight:400;white-space:nowrap">' + shieldMark(isDef ? r.u.id : r.unitId) + (r.mob != null ? ' <span style="color:#8fc4ff;font-weight:700;font-size:9.5px;white-space:nowrap">移' + r.mob + '</span>' : '') + '</span>' + (r.recv != null ? '<br><span style="color:#ff9f43;font-weight:700;font-size:9.5px;white-space:nowrap">受 ' + fmt(r.recv) + ' 剩' + (r.hp ? Math.max(0, Math.round((r.hp - r.recv) / r.hp * 100)) : 0) + '%</span>' : '') + (r.hp ? '<br><span style="font-size:9.5px;color:var(--dim);font-weight:400;white-space:nowrap">HP ' + fmt(r.hp) + '</span>' : '') : ''}</span></div>`).join('') || '<div class="kv" style="color:var(--dim)">无</div>'}
      </div>
    </div>`;
    const proleTxt = ({ 1: '仅攻击型驾驶员', 3: '仅支援型驾驶员', 2: '仅防御型驾驶员' })[t.prole] || '全部驾驶员';
    const best = atk[0] || G.main[0] || null;
    const defTxt = (du2 ? esc(du2.name) + (dch2 ? ' + ' + esc(dch2.name) : '') : '通用数值')
      + ' · 防御 ' + (du2 ? (defBase !== tDefUse ? fmt(defBase) + '→<b style="color:#9fd8ff">' + fmt(tDefUse) + '</b>' : fmt(tDefUse)) + ((t.tDef || t.defup) ? '（' + ((t.defup ? '+全能力' + t.defup + '%' : '') + (t.tDef ? (t.defup ? '，' : '') + '+防御' + t.tDef + '%' : '')) + '）' : '') : fmt(tDefUse) + ((t.tDef || t.defup) ? '（' + (t.defup ? '全能力+' + t.defup + '%' : '') + (t.tDef ? (t.defup ? '，' : '') + '防御+' + t.tDef + '%' : '') + '）' : ''))
      + ' / 守备 ' + fmt(tcDefUse)
      + (du2 ? ' · 耐久 ' + fmt(dInfo.hp0) + (dInfo.hp1 !== dInfo.hp0 ? '→<b style="color:#9fe8c0">' + fmt(dInfo.hp1) + '</b>' : '') + ' · eHP ' + fmt(dInfo.ehp) : '')
      + (defReduce ? ' · <span style="color:#f5c451">承伤-' + defReduce + '%</span>' : '')
      + (t.atkup ? ' · 我方攻击+' + t.atkup + '%' : '') + (t.oDef ? ' · 我方防御+' + t.oDef + '%' : '') + (t.oHp ? ' · 我方HP+' + t.oHp + '%' : '');
    const bestCard = `<div class="card" style="padding:8px 12px"><h4>目标承受最大伤害（${defTxt}）</h4>
      ${best ? `<div class="trow${best.terrHalf ? ' halfmove' : ''}" data-id="${best.unitId}" style="cursor:pointer"><span class="rk g">★</span>
        <span class="ticon-col">${avTagR(best.unit.icon, best.unit.role, best.unit.rarity)}<span class="avw avsm"><span class="picon sm">${imgTag(best.pilot.icon)}</span>${roleBadge(best.pilot.role)}${rarB(best.pilot.rarity)}</span></span>
        <div class="nm">${esc(best.unit.name)} ${rarTag(best.unit.rarity)}<small>驾驶员 <b>${esc(best.pilot.name)}</b>${supCountsBadge(supCountsOf(best.pilot.id, best.unitId, best.vigor, t.ca, t.pSpU !== false))} · ${esc(best.weapon.name)}<span style="color:#8fc4ff"> 射程${best.weapon.range_min}-${best.weapon.range_max}${best.weapon.type === 3 ? '·MAP' : ''}${AATTR[best.weapon.weapon_attr] ? '·' + AATTR[best.weapon.weapon_attr] : ''}</span> · ${isAuto ? (best.mp ? Engine.VIGOR[best.vigor].label + '(MP' + best.mp + ')' : '气势0') : '气势' + Engine.VIGOR[best.vigor].label}${best.shipHit ? ' · <span style="color:#9fe8c0">舰+' + best.shipPct + '%</span>' : ''}</small></div>
        <span class="val g">${fmt(best.dmg)}${best.uAtk ? '<br><span style="font-size:9.5px;color:var(--dim);font-weight:400;white-space:nowrap">攻击力 ' + fmt(best.uAtk) + '</span>' : ''}</span></div>` : '<div class="kv" style="color:var(--dim)">无</div>'}
    </div>`;
    $('tarea').innerHTML = bestCard
      + section('攻击型 TOP10 · 单发伤害（' + modeTxt + ' · ' + proleTxt + '）', 'var(--red)', atk, false, false, 'team_atk') +
      section('攻击型 × 支援型驾驶员 TOP10 · 输出（' + modeTxt + '）', 'var(--orange)', atkSup, false, false, 'team_atsup') +
      section('支援型 TOP10 · 输出（' + modeTxt + ' · 仅支援型驾驶员）', 'var(--green)', sup3, false, true, 'team_sup') +
      section('防御型 TOP10 · 输出（' + modeTxt + ' · 仅防御型驾驶员）', '#c9b8ff', defOut, false, false, 'team_defout', true) +
      section('防御型 TOP10 · 有效耐久 eHP' + ((ship || selBuffs.length) ? '（含' + (ship ? '舰' : '') + (selBuffs.length ? '阵' : '') + '）' : ''), 'var(--blue)', defUnits, true, false, 'team_dehp', true, `　<span class="chip ${t.sdefMode === '1' ? 'gold' : ''}" data-smode="1" style="font-size:9.5px;padding:1px 7px">单支援防御+1</span><span class="chip ${t.sdefMode === '2' ? 'gold' : ''}" data-smode="2" style="font-size:9.5px;padding:1px 7px">双支援防御+2</span><span class="chip ${t.sdefMode === 'all' ? 'gold' : ''}" data-smode="all" style="font-size:9.5px;padding:1px 7px">全部</span>`)
      + csCard;
    $('tarea').querySelectorAll('.trow').forEach(el => el.onclick = () => { const u = q1('SELECT name FROM units WHERE id=?', [+el.dataset.id]); if (u) push({ page: 'unit', title: u.name, id: +el.dataset.id }); });
    $('tarea').querySelectorAll('[data-fold]').forEach(el => el.onclick = ev => {
      ev.stopPropagation();
      const k2 = el.dataset.fold;
      state.teamFold = state.teamFold || {};
      state.teamFold[k2] = !state.teamFold[k2];
      const bd = $('tarea').querySelector('[data-fbody="' + k2 + '"]');
      if (bd) bd.style.display = state.teamFold[k2] ? 'none' : '';
      el.textContent = state.teamFold[k2] ? '▸ 展开' : '▾ 折叠';
    });
  };
  $('picks').onclick = () => openTeamSuppPicker(v);
  $('ttag').onclick = () => openTagPicker('team', () => pageTeam(v));
  $('ttagp').onclick = () => openTagPicker('teamp', () => pageTeam(v));
  $('m1').onclick = () => { t.skills = false; t.mp = false; pageTeam(v); };   // 第一击: 关多段增益
  $('m2').onclick = () => { t.skills = true; t.first = false; pageTeam(v); };   // 全技能 ⇄ 首动 二选一
  $('tfirst').onclick = () => { t.first = !t.first; if (t.first) { t.skills = false; t.mp = false; } pageTeam(v); };   // 首动: 关主动技能(转第一击)/多段增益
  if ($('tfdth')) $('tfdth').onclick = () => { t.fdth = !t.fdth; pageTeam(v); };
  v.querySelectorAll('[data-tstar]').forEach(el => el.onclick = () => { t.star = +el.dataset.tstar; pageTeam(v); });
  v.querySelectorAll('[data-tterr]').forEach(el => el.onclick = () => { t.terr = el.dataset.tterr; pageTeam(v); });
  if ($('tterro')) $('tterro').onclick = () => { t.terrO = !t.terrO; pageTeam(v); };
  if ($('tshieldf')) $('tshieldf').onclick = () => { t.shieldF = !t.shieldF; pageTeam(v); };
  v.querySelectorAll('[data-trar]').forEach(el => el.onclick = () => { const r = el.dataset.trar; t.rar = r === 'all' ? null : (r === 'ult' ? 'ult' : +r); pageTeam(v); });
  if ($('ts3')) $('ts3').onclick = () => { t.s3u = !(t.s3u !== false); if (!(t.s3u !== false)) t.sspU = false; pageTeam(v); };
  if ($('tspu')) $('tspu').onclick = () => { t.spU = !(t.spU !== false); if (!(t.spU !== false)) t.sspU = false; pageTeam(v); };
  if ($('tpspu')) $('tpspu').onclick = () => { t.pSpU = !(t.pSpU !== false); pageTeam(v); };
  if ($('tsspu')) $('tsspu').onclick = () => { t.sspU = !(t.sspU !== false); if (t.sspU !== false) { t.spU = true; t.s3u = true; } pageTeam(v); };
  v.querySelectorAll('[data-lb]').forEach(el => el.onclick = () => { t.shipStar = +el.dataset.lb; pageTeam(v); });
  v.querySelectorAll('[data-rg]').forEach(el => el.onclick = () => { const r = el.dataset.rg; t.range = r === 'all' ? 'all' : (r === 'map' ? 'map' : +r); pageTeam(v); });
  v.querySelectorAll('[data-twat]').forEach(el => el.onclick = () => { const r = el.dataset.twat; t.wat = r === 'all' ? null : r; pageTeam(v); });
  v.querySelectorAll('[data-tatk]').forEach(el => el.onclick = () => { const r = el.dataset.tatk; t.atk = r === 'all' ? null : r; pageTeam(v); });
  v.querySelectorAll('[data-tvg]').forEach(el => el.onclick = () => { t.vigor = el.dataset.tvg; pageTeam(v); });
  v.querySelectorAll('[data-prole]').forEach(el => el.onclick = () => { const r = el.dataset.prole; t.prole = r === 'all' ? null : +r; pageTeam(v); });
  v.querySelectorAll('[data-tprar]').forEach(el => el.onclick = () => { const r = el.dataset.tprar; t.prar = r === 'all' ? null : +r; pageTeam(v); });
  v.querySelectorAll('[data-tdef3]').forEach(el => el.onclick = () => { t.tdef = +el.dataset.tdef3; t.dunit = null; t.dchar = null; pageTeam(v); });
  if ($('ttdef')) $('ttdef').onchange = () => { t.tdef = +$('ttdef').value || 0; t.dunit = null; t.dchar = null; pageTeam(v); };
  if ($('ttcdef')) $('ttcdef').onchange = () => { t.tcdef = +$('ttcdef').value || 0; t.dunit = null; t.dchar = null; pageTeam(v); };
  if ($('tdefup')) $('tdefup').onchange = () => { t.defup = +$('tdefup').value || 0; pageTeam(v); };
  if ($('tdatk')) $('tdatk').onchange = () => { t.tAtk = +$('tdatk').value || 0; pageTeam(v); };
  if ($('tddef')) $('tddef').onchange = () => { t.tDef = +$('tddef').value || 0; pageTeam(v); };
  if ($('tdhp')) $('tdhp').onchange = () => { t.tHp = +$('tdhp').value || 0; pageTeam(v); };
  if ($('tatkup')) $('tatkup').onchange = () => { t.atkup = +$('tatkup').value || 0; pageTeam(v); };
  if ($('todef')) $('todef').onchange = () => { t.oDef = +$('todef').value || 0; pageTeam(v); };
  if ($('tohp')) $('tohp').onchange = () => { t.oHp = +$('tohp').value || 0; pageTeam(v); };
  if ($('dclr')) $('dclr').onclick = (ev) => { ev.stopPropagation(); t.dunit = null; t.dchar = null; pageTeam(v); };
  if ($('tguard')) $('tguard').onclick = () => { t.guard = !t.guard; if (t.guard) t.sdef = false; pageTeam(v); };   // 防御/支援防御 二选一(同一场战斗不可能同时发生)
  if ($('tsdef')) $('tsdef').onclick = () => { t.sdef = !t.sdef; if (t.sdef) t.guard = false; pageTeam(v); };
  $('dpick').onclick = () => openTeamDefPicker(v);
  $('tca').onclick = () => { t.ca = !t.ca; pageTeam(v); };
  $('tsupact').onclick = () => { state.supAct = !(state.supAct !== false); pageTeam(v); };
  $('tmax').onclick = () => { state.maxOn = !state.maxOn; pageTeam(v); };
  if ($('tusk')) $('tusk').onclick = () => { state.uSk = !(state.uSk !== false); pageTeam(v); };
  if ($('turd')) $('turd').onclick = () => openUltSheet();
  $('tmp').onclick = () => { if (t.first || !t.skills) return; t.mp = !t.mp; pageTeam(v); };   // 第一击/首动模式下不可开
  v.querySelectorAll('[data-bdel]').forEach(el => el.onclick = (ev) => { ev.stopPropagation(); t.buffs = t.buffs.filter(k => k !== el.dataset.bdel); pageTeam(v); });
  $('tbuff').onclick = () => showTeamBuffs();
  redraw();
  v.querySelectorAll('[data-smode]').forEach(el => el.onclick = () => { t.sdefMode = el.dataset.smode; pageTeam(v); });   // 绑定须在 redraw 填充 #tarea 之后
}
function openTeamSuppPicker(v) {
  const base = q('SELECT * FROM supporters ORDER BY id').sort((a, b) => lbPctOf(b.leader_desc) - lbPctOf(a.leader_desc) || (b.atk_support || 0) - (a.atk_support || 0));   // 默认按全能力%降序
  const rows = jsSort(base, 'supp', (r, f) => f === 'name' ? r.name : r[f]);
  const stags = {};
  q('SELECT supporter_id, name FROM supporter_tags').forEach(x => (stags[x.supporter_id] = stags[x.supporter_id] || []).push(x.name));
  const shipPctOf = r => ((String(r.leader_desc || '').match(/全能力值\s*(\d+)/) || [])[1] || 0);
  const item = r => `<div class="trow2" data-s="${r.id}">${avTagR(r.icon, null, r.rarity, 'x')}<span style="flex:1">${esc(r.name)} ${rarTag(r.rarity)}
    <span style="display:block;color:var(--dim);font-size:10px">攻击支援+${fmt(r.atk_support)} · ${esc((stags[r.id] || []).slice(0, 5).join('·'))}</span></span>
    <span class="c">${shipPctOf(r)}%</span></div>`;
  const draw = s => rows.filter(r => {
    if (!s) return true;
    return aliasTerms(s).some(x => ciHas(r.name, x))
      || (stags[r.id] || []).some(x => ciHas(x, s))
      || ciHas(r.support_skill_name, s)
      || ciHas(r.leader_desc, s);
  }).map(item).join('');
  const open = () => {
    pickSheet('选择战舰 · 可按技能/标签搜索', draw(''), panel => {
      panel.querySelectorAll('[data-s]').forEach(el => el.onclick = () => { state.team.suppId = +el.dataset.s; closeSheet(); pageTeam(v); });
      panel.querySelectorAll('#psort').forEach(el => el.onclick = () => { _sheetBack = open; openSortPicker('supp', null); });
      const clr = panel.querySelector('#ssclr');
      if (clr) clr.onclick = () => { state.team.suppId = null; closeSheet(); pageTeam(v); };   // 清除选择: 不再有战舰增益
    }, draw, `<div class="fbar"><span class="fbtn" id="psort">↕ ${esc(sortLabel('supp'))}</span><span class="fbtn" id="ssclr">✕ 清除选择</span></div>`);
  };
  open();
}
function openTeamDefPicker(v) {
  const t = state.team;
  const f2 = { which: state.defPickWhich || 'unit' };
  const drawList = s => {
    const pw = pickWhere(f2.which, s);
    return f2.which === 'unit'
      ? q(`SELECT id,name,icon,role,rarity FROM units ${pw.where} ${sortOrder('picku', '')} LIMIT 60`, pw.args).map(u => `<div class="trow2" data-dpick="${u.id}">${avTagR(u.icon, u.role, u.rarity, 'x')}<span style="flex:1">${esc(u.name)} ${rarTag(u.rarity)}${ultB(u)}</span><span class="c">${ROLE[u.role].n}</span></div>`).join('')
      : q(`SELECT id,name,icon,role,rarity,max_defense,sp_max_defense FROM characters ${pw.where} ${sortOrder('pickc', '', null, t.pSpU !== false)} LIMIT 200`, pw.args).filter(c => pilotCanDrive(c.id, t.dunit)).slice(0, 60).map(c => `<div class="trow2" data-dpickc="${c.id}">${avDrv(c.icon, c.role, c.rarity, 'x')}<span style="flex:1">${esc(c.name)} ${rarTag(c.rarity)}</span><span class="c">守备${pStat(c, 'defense', t.pSpU)}</span></div>`).join('');
  };
  const open = () => {
    pickSheet('选择防御机体 / 驾驶员', `<div id="pklist">${drawList('')}</div>`, panel => {
      const bind = () => {
        panel.querySelectorAll('[data-dpick]').forEach(el => el.onclick = () => {
          t.dunit = +el.dataset.dpick;
          const u2 = q1('SELECT * FROM units WHERE id=?', [t.dunit]);
          const own = u2 ? sdOwnChar(u2) : null;
          t.dchar = own ? own.id : t.dchar;   // 默认带出绑定驾驶员
          f2.which = 'char';
          state.defPickWhich = 'char';
          $('pkl').innerHTML = drawList($('pk').value || ''); bind();
          pageTeam(v);                        // 立即刷新背后卡片(含SD绑定驾驶员清除)
        });
        panel.querySelectorAll('[data-dpickc]').forEach(el => el.onclick = () => { t.dchar = +el.dataset.dpickc; closeSheet(); pageTeam(v); });
        panel.querySelectorAll('#dunit,#dchar').forEach(el => el.onclick = () => { f2.which = el.id === 'dunit' ? 'unit' : 'char'; state.defPickWhich = f2.which; open(); });
        bindPickHead(panel, f2.which, open);
      };
      bind();
    }, s => drawList(s), `<div class="btnrow"><span class="bs" id="dunit">机体</span><span class="bs" id="dchar">驾驶员</span></div>${pickHeadHtml(f2.which)}`);
  };
  open();
}
function showTeamBuffs() {
  const groups = teamBuffGroups();
  let sel = (state.team.buffs || []).slice();
  /* 自定义增强: 标签/系列多选(任一命中) + 全能力增强% → 持有者机体 攻击/防御+% */
  const fT = filt('tbuff');
  let cbPct = Math.max(0, +((state.team.cbuff || {}).pct) || 0);
  let tbCk = !!state.team.cbOn;
  const cbNames = () => {
    const td = tagNameDict(), smap = {};
    q('SELECT id,name FROM series').forEach(r => smap[r.id] = r.name);
    return [...fT.tags.map(id => td[id]).filter(Boolean), ...(fT.series || []).map(id => smap[id]).filter(Boolean)];
  };
  const cbPrev = () => { const n = cbNames(); return n.length ? '已选 ' + n.length + ' 项: ' + esc(n.slice(0, 4).join('·')) + (n.length > 4 ? '…' : '') : '未选择（点左侧按钮选择标签/系列, 可多选）'; };
  const commitCustom = () => { state.team.cbuff = { tagIds: [...fT.tags], seriesIds: [...(fT.series || [])], tags: cbNames(), pct: cbPct }; state.team.cbOn = tbCk; };
  groups.forEach(g => { if (!g.isChar && g.shipTags === undefined) g.shipTags = shipTagsOfUnit(+g.target_id); });
  const tbShip = state.team.suppId ? shipEffOf(q1('SELECT * FROM supporters WHERE id=?', [state.team.suppId]), state.team.shipStar || 0) : null;
  const tbShipHl = g => {                      // 条目里的机体被当前战舰加成 → 绿框
    const uid = g.isChar ? (g.reqInfo && g.reqInfo[0] ? g.reqInfo[0].id : null) : +g.target_id;
    return !!(tbShip && uid && shipMatch(tbShip, metaOf(uid)));
  };
  const item = g => `<div class="trow2${tbShipHl(g) ? ' hl' : ''}" data-g="${esc(g.key)}" style="align-items:flex-start"><span class="ck ${sel.includes(g.key) ? 'on' : ''}"></span>${(g.reqInfo && g.reqInfo[0]) ? `<span class="ticon-col">${g.isChar ? avDrv(g.icon, g.role, g.rarity, 'x') : avTagR(g.icon, g.role, g.rarity, 'x')}<span class="avw avsm">${avTagR(g.reqInfo[0].icon, g.reqInfo[0].role, g.reqInfo[0].rarity)}</span></span>` : (g.isChar ? avDrv(g.icon, g.role, g.rarity, 'x') : avTagR(g.icon, g.role, g.rarity, 'x'))}
    <span style="flex:1">${esc(g.owner)} ${rarTag(g.rarity)}${g.reqName ? ' <span style="color:var(--dim);font-size:10px">（乘 ' + esc(g.reqName) + '）</span>' : ''}
    <span style="display:block;color:var(--dim);font-size:10.5px">同部队『${esc(g.tags.join('·') || '—')}』: ${g.atk ? '攻击力+<b style="color:#9fe8c0">' + g.atk + '%</b>' : ''}${g.atk && g.def ? ' · ' : ''}${g.def ? '防御力+<b style="color:#8fc4ff">' + g.def + '%</b>' : ''}（永久）${g.desc ? '<br>' + esc(g.desc) : ''}</span></span></div>`;
  const draw = s => groups.filter(g => !s || ciHas(g.owner, s) || ciHas(g.tags.join('·'), s) || ciHas(g.reqName, s)).map(item).join('');
  const bind = panel => {
    const cp = panel.querySelector('#cbpct');
    if (cp) cp.oninput = () => { cbPct = Math.max(0, +cp.value || 0); };
    const ck = panel.querySelector('#cbck');
    if (ck) ck.onclick = () => { tbCk = !tbCk; ck.classList.toggle('on', tbCk); const hl = panel.querySelector('#cbckh'); if (hl) hl.textContent = tbCk ? '已启用' : '勾选后生效'; };
    const bt = panel.querySelector('#cbtag');
    if (bt) bt.onclick = () => { state.team.buffs = sel; commitCustom(); _sheetBack = () => showTeamBuffs(); openTagPicker('tbuff', null); };
    panel.querySelectorAll('[data-g]').forEach(el => el.onclick = () => {
      const k = el.dataset.g;
      sel = sel.includes(k) ? sel.filter(x => x !== k) : [...sel, k];
      el.querySelector('.ck').classList.toggle('on', sel.includes(k));
      const ap = panel.querySelector('#tapply'); if (ap) ap.textContent = '应用 · ' + sel.length + ' 组增强';
    });
  };
  const shipHint = tbShip ? ' · <span style="color:#7df0a8">绿框 = 该项机体被「' + esc(q1('SELECT name FROM supporters WHERE id=?', [state.team.suppId]).name) + '」加成</span>' : '';
  pickSheet('◈ 队伍增强 · ' + groups.length + ' 组（可多选）', draw(''), bind, draw,
    `<div style="margin:2px 2px 8px;padding:8px 10px;border:1px dashed #4a3a7a;border-radius:10px;background:#181030">
      <div style="font-size:12px;font-weight:700;color:#c9b8ff;display:flex;align-items:center;gap:6px"><span class="ck ${tbCk ? 'on' : ''}" id="cbck" title="勾选后生效"></span>◈ 自定义增强<span class="hint" id="cbckh">${tbCk ? '已启用' : '勾选后生效'}</span></div>
      <div class="btnrow" style="align-items:center;margin-top:5px;gap:6px">
        <span class="bs" id="cbtag">☰ 标签/系列</span>
        <span class="hint" style="margin-left:4px">全能力增强</span>
        <input id="cbpct" type="number" min="0" max="999" placeholder="0" value="${cbPct || ''}" style="width:54px;background:#0e1729;border:1px solid var(--line);border-radius:8px;color:var(--text);padding:2px 6px;font-size:11px">%
      </div>
      <div class="hint" id="cbprev" style="margin-top:4px">${cbPrev()}</div>
      <div class="hint">勾选标题左侧多选框后生效：对持有所选标签/系列的机体 攻击/防御同时 +X%（任一命中），计入组队全部 TOP 计算</div>
    </div>` +
    `<div class="hint">勾选后计入组队榜单：同部队内持有对应标签/系列的机体 攻击力/防御力提升${shipHint}</div>`);
  const panel = $('sheetPanel');
  const foot = document.createElement('div');
  foot.className = 'sheet-f';
  foot.innerHTML = `<div class="btnrow"><span class="bs" id="tclear">清空</span><span class="bp" id="tapply">应用 · ${sel.length} 组增强</span></div>`;
  panel.appendChild(foot);
  $('tclear').onclick = () => { sel = []; panel.querySelectorAll('.ck').forEach(ck => ck.classList.remove('on')); $('tapply').textContent = '应用 · 0 组增强'; };
  $('tapply').onclick = () => { state.team.buffs = sel; commitCustom(); closeSheet(); render(); };
}

/* ------------ 必暴组合(特性页): 武器暴击+机体被动+机师(被动/技能, 含多段增益EX授予) ≥100% 或武器/机体必暴 ------------
   口径: 气势=超一击、条件全开(含EX链: 真·飞鸟二阶段必暴对所有机体生效 — 定死规则勿改, 见 UNIT_GATE_BUG_CHARS)、非UR按SSP满10; 标「需多段增益」= 关多段增益时不足100 */
let _baobiRows = null, _g94Set = null;
function _hasGrant94(id) {   // 驾驶员被动/技能中存在嵌套(EX赋予链)trait94(必暴), 如 真·飞鸟
  if (!_g94Set) {
    _g94Set = new Set();
    for (const tbl of ['char_abilities', 'char_skills', 'char_skills_sp']) {
      for (const r of q(`SELECT char_id, traits_json FROM ${tbl}`)) {
        let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        const f = [false];
        (function w(x) { if (x && typeof x === 'object') { if (x.trait_type === 94) f[0] = true; for (const k in x) { const v = x[k]; if (v && typeof v === 'object') w(v); } } })(ts);
        if (f[0]) _g94Set.add(r.char_id);
      }
    }
  }
  return _g94Set.has(id);
}
function baobiCombos() {
  if (_baobiRows) return _baobiRows;
  const units = q('SELECT id,name,icon,rarity,role FROM units');
  const pilots = q('SELECT id,name FROM characters WHERE COALESCE(is_playable,1)=1');
  const capOf = id => {
    let v = 0, g = false;
    for (const x of (charCritSkillOf(id, true) || [])) { if (x.tt === 12) v += x.v || 0; else if (x.tt === 94) g = true; }
    for (const x of (charCritOf(id, true) || [])) { if (x.tt === 62) v += x.v || 0; else if (x.tt === 94) g = true; }
    return { v, g };
  };
  const caps = {}; for (const p of pilots) caps[p.id] = capOf(p.id);
  const maxCap = Math.max(0, ...Object.values(caps).map(x => x.v));   // 机师侧最高暴击源(动态, 用于机体级预筛)
  _hasGrant94(0);   // 预热嵌套94集合(如 真·飞鸟: 全机体必暴)
  const grant94Any = _g94Set.size > 0;
  const sdMap = sdCharMap();
  const out = [];
  for (const u of units) {
    const wsp = weaponsForUnit(u).map(w => ({ id: w.id, name: w.name, crit_rate: w.crit_rate }));
    if (!wsp.length) continue;
    const maxW = Math.max(...wsp.map(w => w.crit_rate || 0));
    const w94 = !!q1('SELECT 1 FROM weapon_traits WHERE trait_type=94 AND weapon_id IN (SELECT id FROM weapons WHERE unit_id=?) LIMIT 1', [u.id]);
    const meta = metaOf(u.id);
    const sspOn = u.rarity <= 4 && !u.ult;
    let upc = 0, uGuar = false;
    for (const x of (unitCritAll(sspOn)[u.id] || [])) { if (x.tt === 62) upc += x.v || 0; else if (x.tt === 94) uGuar = true; }
    if (!grant94Any && !w94 && !uGuar && maxW + upc + maxCap < 100) continue;   // 上界预筛; 存在嵌套94技师时不筛(其可无条件必暴)
    const cands = meta.tags.has('SD高达') ? [sdOwnChar(u)].filter(Boolean) : pilots.filter(p => { const o = sdMap[p.id]; return !o || o.has(u.id); });
    const hits = [];
    for (const p of cands) {
      const c0 = caps[p.id];
      const hasN = (c0 && c0.g) ? false : _hasGrant94(p.id);
      if (!c0 || (c0.v === 0 && !c0.g && !hasN)) continue;
      if (!c0.g && !hasN && !uGuar && !w94 && maxW + c0.v + upc < 100) continue;
      if (!pilotCanDrive(p.id, u.id)) continue;
      const skv = (charCritSkillOf(p.id, true) || []).filter(x => x.tt === 12).reduce((a, x) => a + (x.v || 0), 0);   // 主动技能暴击值
      const mpv = charMpSkillOf(p.id).reduce((a, x) => a + (x.v || 0), 0);   // MP技能量(先手冲超一击)
      const base = { upassive: true, cpassive: true, skills: true, condAll: true, unitId: u.id, pSpU: true, ussp: sspOn, vigor: 'supercharged' };
      const pc = pilotCritInfo(u.id, p.id, meta, Object.assign({ multiPhase: true }, base));
      const pcNo = pilotCritInfo(u.id, p.id, meta, Object.assign({ multiPhase: false }, base));
      const total = pc.guar ? 100 : Math.min(100, maxW + pc.rate);
      const totalNo = pcNo.guar ? 100 : Math.min(100, maxW + pcNo.rate);
      if (w94 || pc.guar || total >= 100) {
        const viaW = w94 && totalNo < 100 && !pc.guar;   // 纯靠武器必暴(机师无关)
        const pure = !pc.guar && !viaW && pc.rate === upc + skv && skv >= 40;   // 组成=超一击机体被动+主动技能(如 无限正义EX 30+30+技能≥40)
        hits.push({ pid: p.id, pilotName: p.name, rate: pc.rate, total: pc.guar ? 100 : total, skv, mpv,
          desc: (pc.guar ? '必暴(机师/机体)' : (viaW ? '武器必暴' : (pure ? ('武器' + maxW + '+机体被动' + upc + '+技能' + skv + '=100%') : ('武器' + maxW + '+机体被动/机师' + pc.rate + '=100%')))) + (mpv ? ' · 有MP技能+' + mpv + '(先放冲超一击)' : '') + (totalNo < 100 && !viaW ? '（需多段增益）' : ''), viaW });
      }
    }
    if (!hits.length) continue;
    if (w94) { const best = hits.sort((x, y) => y.rate - x.rate)[0]; out.push({ uid: u.id, uname: u.name, uicon: u.icon, urarity: u.rarity, urole: u.role, pid: best.pid, pilotName: best.pilotName + '(任意机师均可, 例)', desc: '武器必暴', ord: 0 }); continue; }
    /* 行序: 有MP技能者在前(按MP量降序=更快到气势最高), 再按主动技能暴击值降序 */
    hits.sort((a, b) => (b.mpv - a.mpv) || (b.skv - a.skv) || (a.pilotName || '').localeCompare(b.pilotName || ''));
    for (let i = 0; i < hits.length; i++) { const h = hits[i]; out.push({ uid: u.id, uname: u.name, uicon: u.icon, urarity: u.rarity, urole: u.role, pid: h.pid, pilotName: h.pilotName, desc: h.desc, ord: i }); }
  }
  // 多段增益必暴型技师(如真·飞鸟: EX赋予链第二层必暴, 全机体覆盖) → 收敛为一条「驾驶员」行
  const byP = {}; for (const x of out) (byP[x.pid] = byP[x.pid] || []).push(x);
  const final = [];
  for (const pid in byP) {
    const g = byP[pid];
    if (g.length > 50) {
      const c1 = q1('SELECT name,icon,rarity,role FROM characters WHERE id=?', [pid]) || {};
      final.push({ uid: +pid, target_type: 'char', uname: c1.name || pid, uicon: c1.icon, urarity: c1.rarity, urole: c1.role, pid: +pid,
        pilotName: '多段增益必暴（EX赋予·需开多段增益）', desc: '开「多段增益」后任意机体均必暴' });
    } else final.push(...g);
  }
  final.sort((a, b) => (b.urarity - a.urarity) || (a.uname || '').localeCompare(b.uname || '') || ((a.ord || 0) - (b.ord || 0)) || (a.pilotName || '').localeCompare(b.pilotName || ''));
  return (_baobiRows = final);
}
/* ------------ 特性「特攻」: 对特定对手(敌方标签/系列/驾驶员标签)生效的 机体被动 + 机师被动 ------------ */
let _tekkoRows = null;
function tekkoList() {
  if (_tekkoRows) return _tekkoRows;
  const KN = { 7: '攻击', 9: '防御', 17: '增伤', 21: '射击', 23: '格斗', 29: '觉醒' };
  const um = {}, cm = {};
  q('SELECT id, name, icon, rarity, role FROM units').forEach(r => um[r.id] = r);
  q('SELECT id, name, icon, rarity, role FROM characters').forEach(r => cm[r.id] = r);
  const out = [];
  const scan = (tbl, idCol, type, emap) => {
    for (const r of q(`SELECT ${idCol} id, traits_json FROM ${tbl}`)) {
      let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      const walk = x => {
        if (Array.isArray(x)) { for (const v of x) walk(v); return; }
        if (!x || typeof x !== 'object') return;
        if (x.trait_type && x.trait_value) {
          const ac = x.active_condition || {};
          if ((ac.target || 'Owner') === 'AttackTarget') {   // 对特定对手生效(敌方标签/系列/驾驶员标签)
            const cq = condTagsOf(ac);
            if (cq.tags.length || cq.series.length || cq.ctags.length) out.push({ target_type: type, target_id: r.id, ent: emap[r.id],
              reqTags: cq.tags, reqSeries: cq.series, ctags: cq.ctags, kind: x.trait_type, v: x.trait_value });
          }
        }
        for (const v of Object.values(x)) if (v && typeof v === 'object') walk(v);
      };
      walk(ts);
    }
  };
  scan('unit_abilities', 'unit_id', 'unit', um);
  scan('unit_abilities_ssp', 'unit_id', 'unit', um);
  scan('char_abilities', 'char_id', 'char', cm);
  scan('char_abilities_sp', 'char_id', 'char', cm);
  /* 同机体/机师+同目标+同类去重: 保留数值最高的一条(等级行) */
  out.sort((a, b) => Math.abs(b.v) - Math.abs(a.v));
  const seen = {}, fin = [];
  for (const x of out) {
    if (!x.ent) continue;
    const tg = [...new Set(x.reqTags)], se = [...new Set(x.reqSeries)], ct = [...new Set(x.ctags)];
    const parts = [];
    if (tg.length) parts.push('敌·' + tg.join('/'));
    if (se.length) parts.push('敌系列·' + se.join('/'));
    if (ct.length) parts.push('敌驾驶员·' + ct.join('/'));
    const lab = parts.join(' ');
    const key = x.target_type + x.target_id + '|' + lab + '|' + x.kind;
    if (seen[key]) continue; seen[key] = 1;
    fin.push({ target_type: x.target_type, target_id: x.target_id, nm: x.ent.name, ic: x.ent.icon, rr: x.ent.rarity, rl: x.ent.role, label: lab,
      desc: lab + '时 ' + (KN[x.kind] || '效果') + (x.v > 0 ? '+' + x.v : String(x.v)) + '%' });
  }
  fin.sort((a, b) => (b.rr || 0) - (a.rr || 0) || (a.nm || '').localeCompare(b.nm || '') || (a.label || '').localeCompare(b.label || ''));
  return (_tekkoRows = fin);
}
let _ultSet = null;
function ultUnitSet() {   // ULT 机体 id 集(「特攻」屏蔽ULT开关用)
  if (!_ultSet) _ultSet = new Set(q('SELECT id FROM units WHERE ult=1').map(r => r.id));
  return _ultSet;
}
/* ------------ 特性页 ------------ */
function pageFeat(v) {
  const kinds = ['revive_escape', 'revive_heal', 'extra_action', 'auto_extra_action', 'preemptive', 'first_hit_immune', 'support_atk', 'support_def', 'counter_shield', 'range_buff', 'mp_skill', 'sway_evade', 'team_buff', 'ally_buff_self', 'unit_skill', 'shield_defense', 'transform', 'swap', 'move6', 'move7', 'baobi', 'tekko', 'range6', 'range7', 'range_up'];
  if (!state.featKind) state.featKind = 'revive_escape';
  v.innerHTML = `<div class="chips">${kinds.map(k => `<span class="chip ${state.featKind === k ? (k.startsWith('revive') ? 'gold' : 'on') : ''}" data-k="${k}">${FEAT[k]}</span>`).join('')}
    <span class="chip ${state.featPSpU !== false ? 'gold' : ''}" id="fpspu">驾驶员SP${state.featPSpU !== false ? ' 开' : ' 关'}</span></div>
    <div id="farea"></div>`;
  v.querySelectorAll('[data-k]').forEach(el => el.onclick = () => { state.featKind = el.dataset.k; pageFeat(v); });
  if ($('fpspu')) $('fpspu').onclick = () => { state.featPSpU = !(state.featPSpU !== false); pageFeat(v); };
  const k = state.featKind;
  if (k === 'team_buff') {                       // 合并重复条目（原始数据按 攻/防 拆分）并显示完整信息
    const groups = teamBuffGroups();
    const tbIcon = g => {                        // 固定搭配: 驾驶员+机体两个头像; 机体来源显示与战舰对得上的标签
      const main = g.isChar ? avDrv(g.icon, g.role, g.rarity) : avTagR(g.icon, g.role, g.rarity);
      const req = g.reqInfo && g.reqInfo[0];
      return req ? `<span class="ticon-col">${main}<span class="avw avsm">${avTagR(req.icon, req.role, req.rarity)}</span></span>` : main;
    };
    const tbShipTags = g => (!g.isChar && g.shipTags && g.shipTags.length)
      ? `<br><span style="color:#8fc4ff">战舰标签: ${esc(g.shipTags.join(' · '))}</span>` : '';
    groups.forEach(g => { if (!g.isChar && g.shipTags === undefined) g.shipTags = shipTagsOfUnit(+g.target_id); });
    const tbShip = state.team.suppId ? shipEffOf(q1('SELECT * FROM supporters WHERE id=?', [state.team.suppId]), state.team.shipStar || 0) : null;
    const tbShipHl = g => {                         // 该条目的机体是否被当前所选战舰加成 → 绿框
      const uid = g.isChar ? (g.reqInfo && g.reqInfo[0] ? g.reqInfo[0].id : null) : +g.target_id;
      return !!(tbShip && uid && shipMatch(tbShip, metaOf(uid)));
    };
    const fctxb = 'feat_team_buff';
    SORTFIELDS[fctxb] = [['id', '图鉴顺序'], ['name', '名称'], ['rarity', '稀有度']];
    const gShown = groups.filter(g => featFilterMatch(g.target_type, g.target_id));
    const gSorted = jsSort(gShown, fctxb, (g, f) => f === 'id' ? g.target_id : (f === 'name' ? (g.owner || '') : (g.rarity || 0)));
    $('farea').innerHTML = `<div class="subnote" style="text-align:left;margin:2px 2px 6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px"><span>${gSorted.length}组 · 队伍增强</span>
      <span style="display:inline-flex;gap:8px;align-items:center;flex-wrap:nowrap"><span class="fbtn" id="ftag">☰ 标签/系列 <b>${(filt('feat').tags.length + ((filt('feat').series || []).length)) || ''}</b></span>
      <span class="fbtn" id="fsort">↕ ${esc(sortLabel(fctxb))}</span></span></div>` +
      gSorted.map(g => `<div class="lrow${tbShipHl(g) ? ' hl' : ''}" data-t="${g.target_type}" data-id="${g.target_id}">${tbIcon(g)}
        <div class="nm">${esc(g.owner)} ${rarTag(g.rarity)} <span style="color:var(--dim);font-size:10px">${esc(g.label)}</span>${g.reqName ? ` <span style="color:var(--dim);font-size:10px">（乘 ${esc(g.reqName)}）</span>` : ''}
        <small>同部队『${esc(g.tags.join('·'))}』：${g.atk ? '攻击力提升' + g.atk + '%' : ''}${g.atk && g.def ? '、' : ''}${g.def ? '防御力提升' + g.def + '%' : ''}（永久）${g.desc ? '<br>' + esc(g.desc) : ''}${tbShipTags(g)}</small></div></div>`).join('');
    $('farea').querySelectorAll('.lrow').forEach(el => el.onclick = () => {
      const t2 = el.dataset.t, id = +el.dataset.id;
      if (t2 === 'char') { const c = q1('SELECT name FROM characters WHERE id=?', [id]); push({ page: 'char', title: c ? c.name : '', id }); }
      else { const u = q1('SELECT name FROM units WHERE id=?', [id]); push({ page: 'unit', title: u ? u.name : '', id }); }
    });
    if ($('ftag')) $('ftag').onclick = () => openTagPicker('feat', () => pageFeat(v));
    if ($('fsort')) $('fsort').onclick = () => openSortPicker(fctxb, () => pageFeat(v));
    return;
  }
  const tkUlt = state.featTkUlt !== false;   // 「特攻」屏蔽ULT机体(默认开)
  let rows = (k === 'baobi')
    ? baobiCombos().map(x => ({ target_type: x.target_type || 'unit', target_id: x.uid, nm: x.uname, ic: x.uicon, rr: x.urarity, rl: x.urole, label: x.pilotName, params_json: JSON.stringify({ pilot: x.pid, desc: x.desc }) }))
    : (k === 'tekko')
    ? tekkoList().filter(x => !(tkUlt && x.target_type === 'unit' && ultUnitSet().has(x.target_id))).map(x => ({ target_type: x.target_type, target_id: x.target_id, nm: x.nm, ic: x.ic, rr: x.rr, rl: x.rl, label: x.label, params_json: JSON.stringify({ desc: x.desc }) }))
    : q(`SELECT f.*, CASE f.target_type WHEN 'char' THEN c.name ELSE u.name END nm,
      CASE f.target_type WHEN 'char' THEN c.icon ELSE u.icon END ic,
      CASE f.target_type WHEN 'char' THEN c.rarity ELSE u.rarity END rr,
      CASE f.target_type WHEN 'char' THEN NULL ELSE u.role END rl
    FROM features f LEFT JOIN characters c ON f.target_type='char' AND c.id=f.target_id
    LEFT JOIN units u ON f.target_type='unit' AND u.id=f.target_id WHERE f.feature=? ORDER BY f.target_type, f.target_id`, [k]);
  rows = rows.filter(r => featFilterMatch(r.target_type, r.target_id));   // 标签/系列筛选
  let sorted = rows;
  if (k === 'preemptive') {   // 按机体稀有度降序, 同级按武器威力降序
    const pw = r => { try { return JSON.parse(r.params_json || '{}').power || 0; } catch (e) { return 0; } };
    sorted = rows.slice().sort((a, b) => (b.rr || 0) - (a.rr || 0) || (pw(b) - pw(a)));
  }
  /* 排序弹窗: 字段按目标类型(机体/驾驶员/混合) */
  const _types = new Set(rows.map(r => r.target_type));
  const fctx = 'feat_' + k;
  SORTFIELDS[fctx] = _types.size === 1
    ? (_types.has('char') ? SORTFIELDS.char : SORTFIELDS.unit)
    : SORTFIELDS.unit.filter(([f]) => ['id', 'name', 'rarity'].includes(f));
  const _fs = sortOf(fctx);
  if (!(_fs.f === 'id' && _fs.d === 1)) {      // 非默认序时改用弹窗排序
    const _um = {}, _cm = {};
    q('SELECT id, name, rarity, max_atk, max_def, max_mob, max_hp, max_en FROM units').forEach(r => _um[r.id] = r);
    q('SELECT id, name, rarity, max_ranged, max_melee, max_awaken, max_defense, max_reaction, sp_max_ranged, sp_max_melee, sp_max_awaken, sp_max_defense, sp_max_reaction FROM characters').forEach(r => _cm[r.id] = r);
    sorted = jsSort(rows, fctx, (r, f) => {
      if (f === 'id') return r.target_id;
      if (f === 'name') return r.nm || '';
      if (f === 'rarity') return r.rr || 0;
      const o = (r.target_type === 'char' ? _cm : _um)[r.target_id];
      if (!o) return null;
      return (r.target_type === 'char' && f.startsWith('max_')) ? pStat(o, f.slice(4), state.featPSpU) : o[f];
    });
  }
  if (k === 'support_atk' || k === 'support_def') {          // 支援攻击/防御 +2: 按驾驶员聚合(+1 次数含条件型, 只显示2以上)
    const supName = k === 'support_atk' ? '支援攻击' : '支援防御';
    /* 统一用 charSupEntries(51/86 或 52/87; 含SP槽位合并, 按驾驶员SP开关口径) */
    const _so = charSupEntries();
    const _kind = k === 'support_atk' ? 'atk' : 'def';
    const cnt = {};
    const _ids = new Set([...Object.keys(_so.base), ...Object.keys(_so.sp)]);
    for (const cid of _ids) {
      const list = mergeSp(_so.base[cid] || [], state.featPSpU !== false ? (_so.sp[cid] || []) : null);
      const n = list.filter(p => p.kind === _kind).length;
      if (n) cnt[cid] = n;
    }
    const labels = {};
    rows.forEach(r => { (labels[r.target_id] = labels[r.target_id] || []).push(r.label || ''); });
    SORTFIELDS[fctx] = [['n', '次数'], ...SORTFIELDS.char];    // 次数 + 驾驶员参数(图鉴顺序/名称/稀有度/射击/格斗/觉醒/防御/反应)
    state._supInit = state._supInit || {};                    // 首次进入默认按次数降序(3次在前); 之后尊重用户选择
    if (!state._supInit[fctx]) { state._supInit[fctx] = 1; state.sort[fctx] = { f: 'n', d: -1 }; }
    const ss = sortOf(fctx);
    let list = Object.keys(cnt).map(cid => ({ cid: +cid, n: cnt[cid], labels: labels[cid] || [] }))
      .filter(x => x.n >= 2 && featFilterMatch('char', x.cid));
    const cInfo = {};
    list.forEach(x => { cInfo[x.cid] = q1('SELECT name, rarity, max_ranged, max_melee, max_awaken, max_defense, max_reaction, sp_max_ranged, sp_max_melee, sp_max_awaken, sp_max_defense, sp_max_reaction FROM characters WHERE id=?', [x.cid]) || {}; });
    if (ss.f === 'n') list.sort((a, b) => (ss.d < 0 ? b.n - a.n : a.n - b.n) || a.cid - b.cid);
    else list = jsSort(list, fctx, (x, f) => f === 'id' ? x.cid : (f.startsWith('max_') ? pStat(cInfo[x.cid], f.slice(4), state.featPSpU) : (cInfo[x.cid] || {})[f]));
    $('farea').innerHTML = `<div class="subnote" style="text-align:left;margin:2px 2px 6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px"><span>${list.length}位 · ${FEAT[k]}</span>
      <span style="display:inline-flex;gap:8px;align-items:center;flex-wrap:nowrap"><span class="fbtn" id="ftag">☰ 标签/系列 <b>${(filt('feat').tags.length + ((filt('feat').series || []).length)) || ''}</b></span>
      <span class="fbtn" id="fsort">↕ ${esc(sortLabel(fctx))}</span></span></div>` +
      list.map(x => {
        const c = q1('SELECT id,name,icon,role,rarity FROM characters WHERE id=?', [x.cid]) || {};
        return `<div class="lrow" data-t="char" data-id="${x.cid}">${avDrv(c.icon, c.role, c.rarity)}
          <div class="nm">${esc(c.name || x.cid)} ${rarTag(c.rarity)}<small>${supName} +${x.n} 次 · ${esc(x.labels.join('、').slice(0, 60))}</small></div>
          <div style="text-align:right"><span class="val" style="color:#9fe8c0;font-weight:800">+${x.n}</span>${k === 'support_def' ? `<br><span style="color:#8fc4ff;font-size:11px;font-weight:700">防御 ${fmt(pStat(cInfo[x.cid], 'defense', state.featPSpU))}</span>` : ''}</div></div>`;
      }).join('') + (list.length ? '' : '<div class="subnote" style="text-align:left">无满足条件的驾驶员</div>');
    $('farea').querySelectorAll('.lrow').forEach(el => el.onclick = () => { const c = q1('SELECT name FROM characters WHERE id=?', [+el.dataset.id]); push({ page: 'char', title: c ? c.name : '', id: +el.dataset.id }); });
    if ($('ftag')) $('ftag').onclick = () => openTagPicker('feat', () => pageFeat(v));
    if ($('fsort')) $('fsort').onclick = () => openSortPicker(fctx, () => pageFeat(v));
    return;
  }
  if (k === 'counter_shield') {    // 进攻盾: 「反击时支援防御」(己方部队在对战中发动攻击并受到敌方反击时, 可参与支援防御; trait 90)
    const fctx = 'feat_counter_shield';
    SORTFIELDS[fctx] = [['id', '图鉴顺序'], ['name', '名称'], ['rarity', '稀有度']];
    state._csInit = state._csInit || {};
    if (!state._csInit[fctx]) { state._csInit[fctx] = 1; state.sort[fctx] = { f: 'rarity', d: -1 }; }
    const all = [], seen = new Set();
    const scan = (rows, type) => {
      for (const r of rows) {
        if (!featFilterMatch(type, r.oid)) continue;
        let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        const hit = ts.filter(t => ((t || {}).trait || {}).trait_type === 90);
        if (!hit.length) continue;
        const key = type + ':' + r.oid + ':' + r.name;
        if (seen.has(key)) continue; seen.add(key);
        const o = type === 'char' ? q1('SELECT id,name,icon,role,rarity FROM characters WHERE id=?', [r.oid]) : q1('SELECT id,name,icon,role,rarity FROM units WHERE id=?', [r.oid]);
        if (!o) continue;
        all.push({ type, id: r.oid, o, ability: r.name, desc: String(hit[0].trait.desc || '').replace(/\n/g, ' '), condJson: JSON.stringify(hit) });
      }
    };
    scan(q('SELECT char_id oid, name, traits_json FROM char_abilities'), 'char');
    scan(q('SELECT char_id oid, name, traits_json FROM char_abilities_sp'), 'char');
    scan(q('SELECT unit_id oid, name, traits_json FROM unit_abilities'), 'unit');
    const csList = jsSort(all, fctx, (x, f) => f === 'id' ? x.id : (f === 'name' ? (x.o.name || '') : (x.o.rarity || 0)));
    $('farea').innerHTML = `<div class="subnote" style="text-align:left;margin:2px 2px 6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px"><span>${csList.length}位 · ${FEAT[k]}（己方部队在对战中发动攻击并受到敌方反击时, 可参与支援防御）</span>
      <span style="display:inline-flex;gap:8px;align-items:center;flex-wrap:nowrap"><span class="fbtn" id="ftag">☰ 标签/系列 <b>${(filt('feat').tags.length + ((filt('feat').series || []).length)) || ''}</b></span>
      <span class="fbtn" id="fsort">↕ ${esc(sortLabel(fctx))}</span></span></div>` +
      csList.map(x => `<div class="lrow" data-t="${x.type}" data-id="${x.id}">${x.type === 'char' ? avDrv(x.o.icon, x.o.role, x.o.rarity) : avTagR(x.o.icon, x.o.role, x.o.rarity)}
        <div class="nm">${esc(x.o.name)} ${rarTag(x.o.rarity)}<small>${esc(x.ability)}<br>${esc(x.desc)}</small>${abilityCondChips(x.condJson)}</div></div>`).join('') + (csList.length ? '' : '<div class="subnote" style="text-align:left">无满足条件的目标</div>');
    $('farea').querySelectorAll('.lrow').forEach(el => el.onclick = () => {
      const t2 = el.dataset.t, id = +el.dataset.id;
      if (t2 === 'char') { const c = q1('SELECT name FROM characters WHERE id=?', [id]); push({ page: 'char', title: c ? c.name : '', id }); }
      else { const u = q1('SELECT name FROM units WHERE id=?', [id]); push({ page: 'unit', title: u ? u.name : '', id }); }
    });
    if ($('ftag')) $('ftag').onclick = () => openTagPicker('feat', () => pageFeat(v));
    if ($('fsort')) $('fsort').onclick = () => openSortPicker(fctx, () => pageFeat(v));
    return;
  }
  if (k === 'range_buff') {        // 范围增益: 对范围内的己方单位生效的增强(含所属部队恢复) —
    /* 驾驶员主动技能「(范围)」族(desc 含「范围内的」) + 驾驶员能力(所属部队/范围内 恢复) +
       机体: 单位技能(features) + 武器固有武装效果(weapon_fx desc 含「范围内的」);
       补给类效果增强(「MAP兵器的MP/HP补给类型的…效果+N」) → 组合行显示 机体+驾驶员 双头像 并显示最高值 */
    const fctx = 'feat_range_buff';
    SORTFIELDS[fctx] = [['id', '图鉴顺序'], ['name', '名称'], ['rarity', '稀有度']];
    state._rbInit = state._rbInit || {};
    if (!state._rbInit[fctx]) { state._rbInit[fctx] = 1; state.sort[fctx] = { f: 'rarity', d: -1 }; }
    const all = [], seen = new Set();
    /* 最高值(按效果文本解析; 条件加成(如W系列+5%)计入) */
    const maxOf = d => {
      let m;
      if ((m = d.match(/MP(?:增加|提升)(\d+)/))) return 'MP+' + m[1];
      if ((m = d.match(/(?:恢复HP|HP恢复)(\d+)%/))) { let v = +m[1]; const m2 = d.match(/HP再恢复(\d+)%/); if (m2) v += +m2[1]; return 'HP+' + v + '%'; }
      if ((m = d.match(/EN恢复(\d+)%/))) return 'EN+' + m[1] + '%';
      if ((m = d.match(/减轻(\d+)%/))) return '减伤' + m[1] + '%';
      if ((m = d.match(/损伤提升(\d+)%/))) return '增伤' + m[1] + '%';
      if ((m = d.match(/最大HP(\d+)%/))) return 'HP+' + m[1] + '%';
      return '';
    };
    /* 补给类效果增强机制(机体能力「适性：歌姬」等 / 驾驶员能力「搭乘「X」时」) */
    const boosters = [];
    const scanBoost = (rows, key, kind) => {
      for (const r of rows) {
        let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        for (const t of ts) {
          const tr = (t || {}).trait || {};
          const d = String(tr.desc || '').replace(/\n/g, ' ');
          const m = d.match(/补给类型的(MP提升|HP恢复)效果\+(\d+)/);
          if (!m) continue;
          const cq = condTagsOf(tr.active_condition || {});
          if (kind === 'unit') boosters.push({ unitId: +r[key], n: +m[2], isMp: m[1] === 'MP提升', ctag: (cq.ctags || [])[0] || null });
          else if ((cq.units || []).length) boosters.push({ unitId: +cq.units[0], n: +m[2], isMp: m[1] === 'MP提升', charId: +r[key] });
        }
      }
    };
    scanBoost(q('SELECT unit_id, traits_json FROM unit_abilities'), 'unit_id', 'unit');
    scanBoost(q('SELECT unit_id, traits_json FROM unit_abilities_ssp'), 'unit_id', 'unit');
    scanBoost(q('SELECT char_id, traits_json FROM char_abilities'), 'char_id', 'char');
    scanBoost(q('SELECT char_id, traits_json FROM char_abilities_sp'), 'char_id', 'char');
    const boostOf = (uid, isMp) => boosters.find(b => b.unitId === uid && b.isMp === isMp) || null;
    const boostPilot = b => {
      if (!b) return null;
      if (b.charId) return q1('SELECT id,name,icon,role,rarity FROM characters WHERE id=?', [b.charId]);
      if (b.ctag) return q1('SELECT c.id,c.name,c.icon,c.role,c.rarity FROM char_tags ct JOIN characters c ON c.id=ct.char_id WHERE ct.tag_id=(SELECT id FROM tags WHERE name=?) ORDER BY c.rarity DESC LIMIT 1', [b.ctag]);
      return null;
    };
    const scanSk = rows => {
      for (const r of rows) {
        const d0 = String(r.desc || '');
        if (d0.indexOf('范围内的') < 0) continue;          // 仅收「范围内的己方/我方」类
        if (!featFilterMatch('char', r.char_id)) continue;
        const key = 'char:' + r.char_id + ':' + r.name;
        if (seen.has(key)) continue; seen.add(key);
        const o = q1('SELECT id,name,icon,role,rarity FROM characters WHERE id=?', [r.char_id]);
        if (!o) continue;
        all.push({ type: 'char', id: r.char_id, o, sub: r.name, desc: d0.replace(/\n/g, ' '), val: maxOf(d0) });
      }
    };
    scanSk(q('SELECT char_id, name, desc FROM char_skills'));
    if (state.featPSpU !== false) scanSk(q('SELECT char_id, name, desc FROM char_skills_sp'));
    /* 驾驶员能力: 所属部队/范围内 恢复类(如 岭司 所属部队EN恢复7% / 马克·吉尔达 所属部队HP恢复5%) */
    const scanAbil = rows => {
      for (const r of rows) {
        let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        for (const t of ts) {
          const tr = (t || {}).trait || {};
          const d = String(tr.desc || '').replace(/\n/g, ' ');
          if (!(d.indexOf('所属部队') >= 0 || d.indexOf('范围内') >= 0 || d.indexOf('全体') >= 0)) continue;
          if (!(d.indexOf('恢复') >= 0 || d.indexOf('回复') >= 0)) continue;
          if (!featFilterMatch('char', r.char_id)) continue;
          const key = 'char:' + r.char_id + ':' + d;
          if (seen.has(key)) continue; seen.add(key);
          const o = q1('SELECT id,name,icon,role,rarity FROM characters WHERE id=?', [r.char_id]);
          if (!o) continue;
          all.push({ type: 'char', id: r.char_id, o, sub: r.name || '', desc: d, val: maxOf(d) });
        }
      }
    };
    scanAbil(q('SELECT char_id, name, traits_json FROM char_abilities'));
    if (state.featPSpU !== false) scanAbil(q('SELECT char_id, name, traits_json FROM char_abilities_sp'));
    /* 机体: 武器固有武装效果(「范围内的己方…」, 如 LACUS CLYNE LIVE 的 MP增加3 / 补给机能 HP恢复20%) —
       补给类效果可被组合增强(歌姬搭乗 +2 / 奥利佛·梅 搭乗 +20%), 组合行显示 机体+驾驶员 双头像 */
    for (const r of q("SELECT DISTINCT w.unit_id uid, w.name wn, f.desc d FROM weapon_fx f JOIN weapons w ON w.id=f.weapon_id WHERE f.desc LIKE '%范围内的%'")) {
      if (!featFilterMatch('unit', r.uid)) continue;
      const key = 'unit:' + r.uid + ':' + r.wn + ':' + r.d;
      if (seen.has(key)) continue; seen.add(key);
      const o = q1('SELECT id,name,icon,role,rarity FROM units WHERE id=?', [r.uid]);
      if (!o) continue;
      const isMp = String(r.d).indexOf('MP') >= 0;
      const b = boostOf(r.uid, isMp);
      const bP = boostPilot(b);
      let val = maxOf(r.d), desc = String(r.d).replace(/\n/g, ' ');
      if (b && bP && val) {
        desc += '（' + (b.ctag || bP.name) + '搭乗 +' + b.n + (isMp ? '' : '%') + '）';
        const bv = isMp ? (val.match(/\d+/) ? 'MP+' + (+val.match(/\d+/)[0] + b.n) : val)
                        : (val.match(/\d+/) ? 'HP+' + (+val.match(/\d+/)[0] + b.n) + '%' : val);
        val = bv;
      }
      all.push({ type: 'unit', id: r.uid, o, sub: '武器 ' + r.wn, desc, val, pilot: b ? bP : null });
    }
    for (const f of q("SELECT target_id, label, params_json FROM features WHERE feature='unit_skill'")) {
      let pr = {}; try { pr = JSON.parse(f.params_json || '{}'); } catch (e) {}
      const d = String(pr.desc || '').replace(/\n/g, ' ');
      if (d.indexOf('范围内的') < 0 && d.indexOf('己方') < 0) continue;
      if (!featFilterMatch('unit', f.target_id)) continue;
      const o = q1('SELECT id,name,icon,role,rarity FROM units WHERE id=?', [f.target_id]);
      if (!o) continue;
      all.push({ type: 'unit', id: f.target_id, o, sub: String(f.label || '').replace(/^单位技能【|】$/g, ''), desc: d, val: maxOf(d), pilot: null });
    }
    const rbList = jsSort(all, fctx, (x, f) => f === 'id' ? x.id : (f === 'name' ? (x.o.name || '') : (x.o.rarity || 0)));
    $('farea').innerHTML = `<div class="subnote" style="text-align:left;margin:2px 2px 6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px"><span>${rbList.length}条 · ${FEAT[k]}（对范围内的己方单位生效的增强效果, 含所属部队恢复; 右侧为最高值）</span>
      <span style="display:inline-flex;gap:8px;align-items:center;flex-wrap:nowrap"><span class="fbtn" id="ftag">☰ 标签/系列 <b>${(filt('feat').tags.length + ((filt('feat').series || []).length)) || ''}</b></span>
      <span class="fbtn" id="fsort">↕ ${esc(sortLabel(fctx))}</span></span></div>` +
      rbList.map(x => `<div class="lrow" data-t="${x.type}" data-id="${x.id}">${x.pilot ? `<span class="ticon-col">${avTagR(x.o.icon, x.o.role, x.o.rarity)}<span class="avw avsm"><span class="picon sm">${imgTag(x.pilot.icon)}</span>${roleBadge(x.pilot.role)}${rarB(x.pilot.rarity)}</span></span>` : (x.type === 'char' ? avDrv(x.o.icon, x.o.role, x.o.rarity) : avTagR(x.o.icon, x.o.role, x.o.rarity))}
        <div class="nm">${esc(x.o.name)} ${rarTag(x.o.rarity)}<small>${esc(x.sub)}<br>${esc(x.desc)}</small></div>${x.val ? `<span class="val" style="color:#9fe8c0;font-weight:800;flex:none;margin-left:6px">${esc(x.val)}</span>` : ''}</div>`).join('') + (rbList.length ? '' : '<div class="subnote" style="text-align:left">无满足条件的目标</div>');
    $('farea').querySelectorAll('.lrow').forEach(el => el.onclick = () => {
      const t2 = el.dataset.t, id = +el.dataset.id;
      if (t2 === 'char') { const c = q1('SELECT name FROM characters WHERE id=?', [id]); push({ page: 'char', title: c ? c.name : '', id }); }
      else { const u = q1('SELECT name FROM units WHERE id=?', [id]); push({ page: 'unit', title: u ? u.name : '', id }); }
    });
    if ($('ftag')) $('ftag').onclick = () => openTagPicker('feat', () => pageFeat(v));
    if ($('fsort')) $('fsort').onclick = () => openSortPicker(fctx, () => pageFeat(v));
    return;
  }
  if (k === 'sway_evade') {        // 摇摆闪避: 有主动闪避技能的驾驶员(摇摆闪避 trait14 / 命中率、闪避率提升 trait6)
    const fctx = 'feat_sway_evade';
    SORTFIELDS[fctx] = [['ev', '闪避率'], ...SORTFIELDS.char];
    state._swInit = state._swInit || {};
    if (!state._swInit[fctx]) { state._swInit[fctx] = 1; state.sort[fctx] = { f: 'ev', d: -1 }; }
    const all = [];
    for (const r of q('SELECT id, name, icon, role, rarity, max_melee, max_ranged, max_awaken, max_defense, max_reaction, sp_max_melee, sp_max_ranged, sp_max_awaken, sp_max_defense, sp_max_reaction FROM characters WHERE COALESCE(is_playable,1)=1')) {
      if (!featFilterMatch('char', r.id)) continue;
      const sk = charEvadeOf(r.id, state.featPSpU);
      if (!sk.length) continue;
      all.push({ c: r, sk, ev: Math.max(...sk.map(x => x.v)) });
    }
    const sSw = sortOf(fctx);
    let swList = all;
    if (!(sSw.f === 'id' && sSw.d === 1)) swList = jsSort(all, fctx, (x, f) => {
      if (f === 'ev') return x.ev;
      if (f === 'id') return x.c.id;
      if (f === 'name') return x.c.name || '';
      if (f === 'rarity') return x.c.rarity || 0;
      return pStat(x.c, f.slice(4), state.featPSpU);
    });
    $('farea').innerHTML = `<div class="subnote" style="text-align:left;margin:2px 2px 6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px"><span>${swList.length}位 · ${FEAT[k]}</span>
      <span style="display:inline-flex;gap:8px;align-items:center;flex-wrap:nowrap"><span class="fbtn" id="ftag">☰ 标签/系列 <b>${(filt('feat').tags.length + ((filt('feat').series || []).length)) || ''}</b></span>
      <span class="fbtn" id="fsort">↕ ${esc(sortLabel(fctx))}</span></span></div>` +
      swList.map(x => {
        const skTxt = x.sk.map(s => esc(s.name) + ' · 闪避率+' + s.v + '%').join(' ｜ ');
        return `<div class="lrow" data-id="${x.c.id}">${avDrv(x.c.icon, x.c.role, x.c.rarity)}
          <div class="nm">${esc(x.c.name)} ${rarTag(x.c.rarity)}<small>${skTxt}</small></div>
          <span class="val" style="color:#8fc4ff;font-weight:800">闪避+${x.ev}%</span></div>`;
      }).join('') + (swList.length ? '' : '<div class="subnote" style="text-align:left">无满足条件的驾驶员</div>');
    $('farea').querySelectorAll('.lrow').forEach(el => el.onclick = () => { const c = q1('SELECT name FROM characters WHERE id=?', [+el.dataset.id]); push({ page: 'char', title: c ? c.name : '', id: +el.dataset.id }); });
    if ($('ftag')) $('ftag').onclick = () => openTagPicker('feat', () => pageFeat(v));
    if ($('fsort')) $('fsort').onclick = () => openSortPicker(fctx, () => pageFeat(v));
    return;
  }
  if (k === 'mp_skill') {          // 有MP技能: 被动MP提升(46/43含条件型) / 主动MpBoost(4)
    const fctx = 'feat_mp_skill';
    SORTFIELDS[fctx] = [['mp', 'MP合计'], ...SORTFIELDS.char];
    state._mpInit = state._mpInit || {};
    if (!state._mpInit[fctx]) { state._mpInit[fctx] = 1; state.sort[fctx] = { f: 'mp', d: -1 }; }
    state._mpFltr = state._mpFltr || null;                  // null=全部 / both=主被动 / passive=单被动 / active=仅主动
    charMpAbilities(); charMpSkills();
    const VIGN = { 1: '强势', 2: '超强势', 3: '超一击' };
    const _uName = {};
    const uNameOf = id => (_uName[id] = _uName[id] || ((q1('SELECT name FROM units WHERE id=?', [id]) || {}).name || id));
    const condTxt = entries => {                            // 汇总条件条目 → 文字(相同条件去重)
      const out = new Set();
      for (const e of entries) {
        const ps = [];
        const tg = [...new Set(e.reqTags || [])], sr = [...new Set(e.reqSeries || [])];
        if (tg.length) ps.push((e.enemy ? '敌方部队含' : '搭乘含') + '「' + tg.join('·') + '」' + (e.enemy ? '' : '标签'));
        if (sr.length) ps.push('搭乘「' + sr.join('·') + '」系列机体');
        if (e.reqUnits && e.reqUnits.length) ps.push('搭乘' + e.reqUnits.map(uNameOf).join('/'));
        if (e.tensionReq) ps.push('战意「' + (VIGN[e.tensionReq] || '') + '」以上');
        if (ps.length) out.add(ps.join(' + '));
      }
      return [...out].join(' / ');
    };
    const all = [];
    for (const r of q('SELECT id, name, icon, role, rarity, max_melee, max_ranged, max_awaken, max_defense, max_reaction, sp_max_melee, sp_max_ranged, sp_max_awaken, sp_max_defense, sp_max_reaction FROM characters WHERE COALESCE(is_playable,1)=1')) {
      if (!featFilterMatch('char', r.id)) continue;
      const pa = charMpAbilOf(r.id, state.featPSpU), ac = charMpSkillOf(r.id, state.featPSpU);
      if (!pa.length && !ac.length) continue;
      const pv = pa.reduce((s, x) => s + (x.v || 0), 0), av = ac.reduce((s, x) => s + (x.v || 0), 0);
      all.push({ c: r, pv, av, pa, ac });
    }
    const flt = state._mpFltr;
    const shown = all.filter(x => {
      const hasP = x.pv > 0, hasA = x.av > 0;
      if (flt === 'both') return hasP && hasA;
      if (flt === 'passive') return hasP && !hasA;
      if (flt === 'active') return !hasP && hasA;
      return true;
    });
    const sMp = sortOf(fctx);
    let mpList = shown;
    if (!(sMp.f === 'id' && sMp.d === 1)) mpList = jsSort(shown, fctx, (x, f) => {
      if (f === 'mp') return x.pv + x.av;
      if (f === 'id') return x.c.id;
      if (f === 'name') return x.c.name || '';
      if (f === 'rarity') return x.c.rarity || 0;
      return pStat(x.c, f.slice(4), state.featPSpU);
    });
    $('farea').innerHTML = `<div class="subnote" style="text-align:left;margin:2px 2px 6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px"><span>${mpList.length}位 · ${FEAT[k]}</span>
      <span style="display:inline-flex;gap:8px;align-items:center;flex-wrap:nowrap"><span class="fbtn" id="ftag">☰ 标签/系列 <b>${(filt('feat').tags.length + ((filt('feat').series || []).length)) || ''}</b></span>
      <span class="fbtn" id="fsort">↕ ${esc(sortLabel(fctx))}</span></span></div>
      <div class="chips tight"><span class="chip ${!flt ? 'on' : ''}" data-mpf="">全部</span>
        <span class="chip ${flt === 'both' ? 'gold' : ''}" data-mpf="both">主被动mp</span>
        <span class="chip ${flt === 'passive' ? 'gold' : ''}" data-mpf="passive">单被动mp</span>
        <span class="chip ${flt === 'active' ? 'gold' : ''}" data-mpf="active">主动mp</span></div>` +
      mpList.map(x => {
        const parts = [];
        if (x.pv > 0) { const c1 = condTxt(x.pa); parts.push('被动MP+' + x.pv + (c1 ? '（' + c1 + '）' : '')); }
        if (x.av > 0) { const c2 = condTxt(x.ac); parts.push('主动MP+' + x.av + (c2 ? '（' + c2 + '）' : '')); }
        return `<div class="lrow" data-id="${x.c.id}">${avDrv(x.c.icon, x.c.role, x.c.rarity)}
          <div class="nm">${esc(x.c.name)} ${rarTag(x.c.rarity)}<small>${parts.join(' · ')}</small></div>
          <span class="val" style="color:#9fe8c0;font-weight:800">MP+${x.pv + x.av}</span></div>`;
      }).join('') + (mpList.length ? '' : '<div class="subnote" style="text-align:left">无满足条件的驾驶员</div>') +
      (() => {   // 机体 MP: 线性扫 features 的 unit_skill, 有 MP 提升的按「主动MP」列出
        if (flt === 'passive') return '';
        const out = [];
        for (const r of q("SELECT target_id, label, params_json FROM features WHERE feature='unit_skill'")) {
          let p = {}; try { p = JSON.parse(r.params_json || '{}'); } catch (e) { continue; }
          let v = 0;
          for (const t of (p.traits || [])) if (t.trait_type_index === 12) v += (t.trait_value || 0);
          if (!v && /MP/i.test(String(p.desc || ''))) { const m = /MP[^\d]{0,6}(\d+)/i.exec(String(p.desc)); if (m) v = +m[1]; }
          if (v > 0 && featFilterMatch('unit', r.target_id)) out.push({ id: r.target_id, v, label: r.label });
        }
        const seen = new Set(out.map(x => x.id));
        for (const r of q("SELECT g.unit_id uid, s.name, s.traits_json FROM ult_skills s JOIN ult_group g ON g.group_id=s.group_id")) {   // ULT 三选一里的 MP 提升
          let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
          let v = 0;
          for (const t of ts) if (t.trait_type_index === 12) v += (t.trait_value || 0);
          if (v > 0 && !seen.has(r.uid) && featFilterMatch('unit', r.uid)) { seen.add(r.uid); out.push({ id: r.uid, v, label: r.name }); }
        }
        if (!out.length) return '';
        return '<div class="subnote" style="text-align:left;margin:10px 2px 4px;font-weight:700">机体（主动MP）</div>' + out.map(x => {
          const u = q1('SELECT name, icon, role, rarity FROM units WHERE id=?', [x.id]) || {};
          return `<div class="lrow" data-ut="1" data-id="${x.id}">${avTag(u.icon, u.role)}<div class="nm">${esc(u.name || '')} ${rarTag(u.rarity)}<small>${esc(x.label || '')}</small></div><span class="val" style="color:#9fe8c0;font-weight:800">主动MP+${x.v}</span></div>`;
        }).join('');
      })();
    $('farea').querySelectorAll('[data-mpf]').forEach(el => el.onclick = () => { state._mpFltr = el.dataset.mpf || null; pageFeat(v); });
    $('farea').querySelectorAll('.lrow[data-ut]').forEach(el => el.onclick = () => { const u = q1('SELECT name FROM units WHERE id=?', [+el.dataset.id]); push({ page: 'unit', title: u ? u.name : '', id: +el.dataset.id }); });
    $('farea').querySelectorAll('.lrow:not([data-ut])').forEach(el => el.onclick = () => { const c = q1('SELECT name FROM characters WHERE id=?', [+el.dataset.id]); push({ page: 'char', title: c ? c.name : '', id: +el.dataset.id }); });
    if ($('ftag')) $('ftag').onclick = () => openTagPicker('feat', () => pageFeat(v));
    if ($('fsort')) $('fsort').onclick = () => openSortPicker(fctx, () => pageFeat(v));
    return;
  }
  if (k === 'range6' || k === 'range7') {   // 6/7射程: 武器可达最大射程 —
    /* 加成来源: 基础射程 / SSP満10(武器行本身) / 机体被动(trait72) / 驾驶员被动(trait72, 需指定机体或系列) / 主动技能「射程增幅」(trait3)
       驾驶员被动 与 主动技能 各有开关(默认全开); 加成可叠层(机体被动+驾驶员+主动技能) */
    const T = k === 'range6' ? 6 : 7, exactly = (k === 'range6');
    const fctx = 'feat_' + k;
    SORTFIELDS[fctx] = [['id', '图鉴顺序'], ['name', '名称'], ['rarity', '稀有度']];
    state._rgInit = state._rgInit || {};
    if (!state._rgInit[fctx]) { state._rgInit[fctx] = 1; state.sort[fctx] = { f: 'id', d: 1 }; }
    const rgP = state.featRgP !== false, rgS = state.featRgS !== false, rgM = state.featRgM !== false;   // 开关(默认开): 驾驶员被动 / 主动技能 / MAP武器(关=不统计)
    const CATTR = { 1: [1], 2: [2], 3: [3], 4: [1, 2], 5: [1, 3], 6: [2, 3], 7: [1, 2, 3] };
    const attrsOf = d => { const a = []; if (d.indexOf('物理') >= 0) a.push(1); if (d.indexOf('镭射') >= 0 || d.indexOf('光束') >= 0) a.push(2); if (d.indexOf('特殊') >= 0) a.push(3); return a; };
    const attrHit = (d, wa) => { const a = attrsOf(d), c = CATTR[wa] || []; return a.length && c.length && a.some(x => c.includes(x)); };
    /* 机体被动 trait72 */
    const unitUp = {};
    for (const r of q('SELECT unit_id, name, traits_json FROM unit_abilities')) {
      let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
      for (const t of ts) {
        const tr = (t || {}).trait || {};
        if (tr.trait_type !== 72) continue;
        const d = String(tr.desc || '').replace(/\n/g, ' ');
        (unitUp[r.unit_id] = unitUp[r.unit_id] || []).push({ d });
      }
    }
    /* 驾驶员被动 trait72: 需指定机体(unit_ids) → 组合; 系列条件型 → 按机体系列 */
    const pilotUp = {};
    const scanPilot = rows => {
      for (const r of rows) {
        let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        for (const t of ts) {
          const tr = (t || {}).trait || {};
          if (tr.trait_type !== 72) continue;
          const d = String(tr.desc || '').replace(/\n/g, ' ');
          const cq = condTagsOf(tr.active_condition || {});
          const c = q1('SELECT id,name,icon,role,rarity FROM characters WHERE id=?', [r.char_id]);
          if (!c) continue;
          for (const u of (cq.units || [])) (pilotUp[u] = pilotUp[u] || []).push({ c, d });
          if (!(cq.units || []).length && (cq.series || []).length) for (const sn of cq.series) (pilotUp['s:' + sn] = pilotUp['s:' + sn] || []).push({ c, d });
        }
      }
    };
    scanPilot(q('SELECT char_id, name, traits_json FROM char_abilities'));
    if (state.featPSpU !== false) scanPilot(q('SELECT char_id, name, traits_json FROM char_abilities_sp'));
    /* 主动技能「射程增幅」(trait3): 所有持有该技能的驾驶员(任意机体可用) */
    const skillPilots = new Set();
    const scanSkill = rows => {
      for (const r of rows) {
        let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        for (const t of ts) {
          const tr = (t || {}).trait || {};
          if (tr.trait_type === 3 && String(tr.desc || '').indexOf('射程') >= 0) skillPilots.add(r.char_id);
        }
      }
    };
    scanSkill(q('SELECT char_id, traits_json FROM char_skills'));
    if (state.featPSpU !== false) scanSkill(q('SELECT char_id, traits_json FROM char_skills_sp'));
    const all = [];
    for (const un of q('SELECT id, name, icon, role, rarity FROM units')) {
      if (!featFilterMatch('unit', un.id)) continue;
      const meta = metaOf(un.id);
      const pils = (pilotUp[un.id] || []).concat(meta.seriesList ? [...meta.seriesList].flatMap(sn => pilotUp['s:' + sn] || []) : []);
      let best = null;
      for (const w of weaponsForUnit({ id: un.id, ult: 1 })) {
        const isMap = (w.type === 3);
        if (isMap && !rgM) continue;                                         // MAP武器开关: 关=不统计
        const b0 = w.range_max || 0;
        const u = isMap ? null : ((unitUp[un.id] || []).find(x => attrHit(x.d, w.weapon_attr)) || null);   // 主被动/主动技能不增加MAP武器射程
        const p = (rgP && !isMap) ? (pils.find(x => attrHit(x.d, w.weapon_attr)) || null) : null;
        const sk = (rgS && !isMap && skillPilots.size) ? true : false;
        let reach = b0 + (u ? 1 : 0) + (p ? 1 : 0) + (sk ? 1 : 0);
        const rank = (w.is_ssp ? 1 : 0) + (u ? 2 : 0) + (p ? 4 : 0) + (sk ? 8 : 0);
        if (!best || reach > best.reach || (reach === best.reach && rank < best.rank)) best = { reach, rank, w, u, p, sk };
      }
      if (!best) continue;
      if (exactly ? best.reach === 6 : best.reach >= 7) all.push({ un, ...best });
    }
    const rgList = jsSort(all, fctx, (x, f) => f === 'id' ? x.un.id : (f === 'name' ? (x.un.name || '') : (x.un.rarity || 0)));
    const MAPT = w => (w.type === 3 ? '·MAP' : '');
    $('farea').innerHTML = `<div class="subnote" style="text-align:left;margin:2px 2px 6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px"><span>${rgList.length}台 · ${FEAT[k]}（武器可达最大射程；基础/SSP満10 + 机体被动 / 驾驶员被动 / 主动技能可叠层；主被动/主动技能不作用于MAP武器${exactly ? '；可达7的机体在7射程' : ''}）</span>
      <span style="display:inline-flex;gap:8px;align-items:center;flex-wrap:nowrap"><span class="fbtn" id="ftag">☰ 标签/系列 <b>${(filt('feat').tags.length + ((filt('feat').series || []).length)) || ''}</b></span>
      <span class="fbtn" id="fsort">↕ ${esc(sortLabel(fctx))}</span></span></div>
      <div class="chips"><span class="chip ${rgP ? 'gold' : ''}" id="rgp">驾驶员被动+1${rgP ? ' 开' : ' 关'}</span>
      <span class="chip ${rgS ? 'gold' : ''}" id="rgs">主动技能·射程增幅+1${rgS ? ' 开' : ' 关'}（${skillPilots.size}位持有）</span>
      <span class="chip ${rgM ? 'gold' : ''}" id="rgm">MAP武器${rgM ? ' 统计' : ' 不统计'}</span></div>` +
      rgList.map(x => {
        const w = x.w;
        const base = '射程' + w.range_min + '-' + w.range_max + MAPT(w);
        const tail = x.reach > (w.range_max || 0) ? '→' + x.reach : '';
        const parts = [w.is_ssp ? 'SSP満10' : '基础射程'];
        if (x.u) parts.push('机体被动：' + x.u.d);
        if (x.p) parts.push('驾驶员 ' + (x.p.c.name || '') + '：' + x.p.d);
        if (x.sk) parts.push('主动技能 射程增幅+1（任意持有驾驶员）');
        return `<div class="lrow" data-t="unit" data-id="${x.un.id}">${x.p ? `<span class="ticon-col">${avTagR(x.un.icon, x.un.role, x.un.rarity)}<span class="avw avsm"><span class="picon sm">${imgTag(x.p.c.icon)}</span>${roleBadge(x.p.c.role)}${rarB(x.p.c.rarity)}</span></span>` : avTagR(x.un.icon, x.un.role, x.un.rarity)}
          <div class="nm">${esc(x.un.name)} ${rarTag(x.un.rarity)}<small>${esc(w.name)} ${base}${tail}（${esc(parts.join(' + '))}）</small></div>
          <span class="val" style="color:#9fe8c0;font-weight:800;flex:none;margin-left:6px">射程${x.reach}</span></div>`;
      }).join('') + (rgList.length ? '' : '<div class="subnote" style="text-align:left">无满足条件的机体</div>');
    $('farea').querySelectorAll('.lrow').forEach(el => el.onclick = () => {
      const u = q1('SELECT name FROM units WHERE id=?', [+el.dataset.id]); push({ page: 'unit', title: u ? u.name : '', id: +el.dataset.id });
    });
    if ($('rgp')) $('rgp').onclick = () => { state.featRgP = !(state.featRgP !== false); pageFeat(v); };
    if ($('rgs')) $('rgs').onclick = () => { state.featRgS = !(state.featRgS !== false); pageFeat(v); };
    if ($('rgm')) $('rgm').onclick = () => { state.featRgM = !(state.featRgM !== false); pageFeat(v); };
    if ($('ftag')) $('ftag').onclick = () => openTagPicker('feat', () => pageFeat(v));
    if ($('fsort')) $('fsort').onclick = () => openSortPicker(fctx, () => pageFeat(v));
    return;
  }
  if (k === 'range_up') {   // 射程加: 驾驶员被动/主动技能的射程提升(+1/+2, 合计值; 复用6/7射程的开关)
    const fctx = 'feat_range_up';
    SORTFIELDS[fctx] = [['total', '合计'], ['id', '图鉴顺序'], ['name', '名称'], ['rarity', '稀有度']];
    state._ruInit = state._ruInit || {};
    if (!state._ruInit[fctx]) { state._ruInit[fctx] = 1; state.sort[fctx] = { f: 'total', d: -1 }; }
    const rgP = state.featRgP !== false, rgS = state.featRgS !== false;
    const map = {};
    const ent = cid => {
      if (!map[cid]) { const c = q1('SELECT id,name,icon,role,rarity FROM characters WHERE id=?', [cid]); if (!c) return null; map[cid] = { c, ps: [], as: [] }; }
      return map[cid];
    };
    /* 驾驶员被动 trait72(需指定机体或系列) */
    const scanP = rows => {
      for (const r of rows) {
        if (!featFilterMatch('char', r.char_id)) continue;
        let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        for (const t of ts) {
          const tr = (t || {}).trait || {};
          if (tr.trait_type !== 72) continue;
          const e = ent(r.char_id); if (!e) continue;
          const cq = condTagsOf(tr.active_condition || {});
          const key = 'P' + (tr.desc || '');
          if (e.ps.some(x => x.key === key)) continue;
          e.ps.push({ key, d: String(tr.desc || '').replace(/\n/g, ' '), unitId: (cq.units || [])[0] || null, series: (cq.series || [])[0] || null, v: tr.trait_value || 1 });
        }
      }
    };
    scanP(q('SELECT char_id, traits_json FROM char_abilities'));
    if (state.featPSpU !== false) scanP(q('SELECT char_id, traits_json FROM char_abilities_sp'));
    /* 驾驶员主动技能「射程增幅」trait3 */
    const scanA = rows => {
      for (const r of rows) {
        if (!featFilterMatch('char', r.char_id)) continue;
        let ts = []; try { ts = JSON.parse(r.traits_json || '[]'); } catch (e) { continue; }
        for (const t of ts) {
          const tr = (t || {}).trait || {};
          if (tr.trait_type !== 3 || String(tr.desc || '').indexOf('射程') < 0) continue;
          const e = ent(r.char_id); if (!e) continue;
          const key = 'A' + (r.name || '');
          if (e.as.some(x => x.key === key)) continue;
          e.as.push({ key, name: r.name || '射程增幅', v: tr.trait_value || 1 });
        }
      }
    };
    scanA(q('SELECT char_id, name, traits_json FROM char_skills'));
    if (state.featPSpU !== false) scanA(q('SELECT char_id, name, traits_json FROM char_skills_sp'));
    const rows = [];
    for (const cid in map) {
      const e = map[cid];
      const pv = rgP ? e.ps.reduce((s2, x) => s2 + x.v, 0) : 0;
      const av = rgS ? e.as.reduce((s2, x) => s2 + x.v, 0) : 0;
      if (!(pv + av)) continue;
      rows.push({ c: e.c, ps: e.ps, as: e.as, pv, av, total: pv + av });
    }
    const ruList = jsSort(rows, fctx, (x, f) => f === 'total' ? x.total : (f === 'id' ? x.c.id : (f === 'name' ? (x.c.name || '') : (x.c.rarity || 0))));
    const partsOf = x => {
      const ps = rgP ? x.ps.map(pp => {
        const req = pp.unitId ? ('搭乘「' + ((q1('SELECT name FROM units WHERE id=?', [pp.unitId]) || {}).name || '') + '」') : (pp.series ? ('「' + pp.series + '」系列') : '');
        return '被动 ' + (req ? req + '：' : '') + pp.d + ' +' + pp.v;
      }) : [];
      const as = rgS ? x.as.map(a2 => '主动技能 ' + a2.name + ' +' + a2.v) : [];
      return ps.concat(as);
    };
    $('farea').innerHTML = `<div class="subnote" style="text-align:left;margin:2px 2px 6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px"><span>${ruList.length}位 · ${FEAT[k]}（驾驶员被动/主动技能的射程提升；右侧为合计值；需指定机体的显示机体小头像）</span>
      <span style="display:inline-flex;gap:8px;align-items:center;flex-wrap:nowrap"><span class="fbtn" id="ftag">☰ 标签/系列 <b>${(filt('feat').tags.length + ((filt('feat').series || []).length)) || ''}</b></span>
      <span class="fbtn" id="fsort">↕ ${esc(sortLabel(fctx))}</span></span></div>
      <div class="chips"><span class="chip ${rgP ? 'gold' : ''}" id="rgp">被动技能+1${rgP ? ' 开' : ' 关'}</span>
      <span class="chip ${rgS ? 'gold' : ''}" id="rgs">主动技能·射程增幅+1${rgS ? ' 开' : ' 关'}</span></div>` +
      ruList.map(x => {
        const uNeed = x.ps.find(pp => pp.unitId);
        const uo = (rgP && uNeed) ? q1('SELECT icon, role, rarity FROM units WHERE id=?', [uNeed.unitId]) : null;
        const parts = partsOf(x);
        const txt = parts.join(' · ') || '（当前开关下无加成）';
        return `<div class="lrow" data-t="char" data-id="${x.c.id}">${uo ? `<span class="ticon-col">${avDrv(x.c.icon, x.c.role, x.c.rarity)}<span class="avw avsm">${avTagR(uo.icon, uo.role, uo.rarity)}</span></span>` : avDrv(x.c.icon, x.c.role, x.c.rarity)}
          <div class="nm">${esc(x.c.name)} ${rarTag(x.c.rarity)}<small>${esc(txt)}</small></div>
          <span class="val" style="color:#9fe8c0;font-weight:800;flex:none;margin-left:6px">射程+${x.total}</span></div>`;
      }).join('') + (ruList.length ? '' : '<div class="subnote" style="text-align:left">无满足条件的驾驶员</div>');
    $('farea').querySelectorAll('.lrow').forEach(el => el.onclick = () => {
      const c2 = q1('SELECT name FROM characters WHERE id=?', [+el.dataset.id]); push({ page: 'char', title: c2 ? c2.name : '', id: +el.dataset.id });
    });
    if ($('rgp')) $('rgp').onclick = () => { state.featRgP = !(state.featRgP !== false); pageFeat(v); };
    if ($('rgs')) $('rgs').onclick = () => { state.featRgS = !(state.featRgS !== false); pageFeat(v); };
    if ($('ftag')) $('ftag').onclick = () => openTagPicker('feat', () => pageFeat(v));
    if ($('fsort')) $('fsort').onclick = () => openSortPicker(fctx, () => pageFeat(v));
    return;
  }
  $('farea').innerHTML = `<div class="subnote" style="text-align:left;margin:2px 2px 6px;display:flex;flex-wrap:wrap;align-items:center;gap:6px"><span>${fmt(sorted.length)}条 · ${FEAT[k]}</span>
    <span style="display:inline-flex;gap:8px;align-items:center;flex-wrap:nowrap"><span class="fbtn" id="ftag">☰ 标签/系列 <b>${(filt('feat').tags.length + ((filt('feat').series || []).length)) || ''}</b></span>
    <span class="fbtn" id="fsort">↕ ${esc(sortLabel(fctx))}</span>${k === 'tekko' ? `<span class="chip ${tkUlt ? 'gold' : ''}" id="tkult" title="屏蔽ULT机体(特攻列表中占比很高)">屏蔽ULT${tkUlt ? ' 开' : ' 关'}</span>` : ''}</span></div>` +
    sorted.map(r => {
      let pr = {}; try { pr = JSON.parse(r.params_json || '{}'); } catch (e) {}
      let sub = pr.desc ? pr.desc : (pr.pct != null ? `恢复 ${pr.pct}%` : (pr.grants ? '赋予: ' + (pr.grants || []).join('/') + ' → ' + (pr.target_tags || []).join('·') : ''));
      if (pr.power) sub = '威力 ' + fmt(pr.power) + ' · ' + sub;
      if (pr.wid) { try { const ww = q1('SELECT type t, range_min mn, range_max r FROM weapons WHERE id=?', [pr.wid]); if (ww) sub = '射程' + ww.mn + '-' + ww.r + (ww.t === 3 ? '·MAP' : '') + ' · ' + sub; } catch (e) {} }
      let pipHtml = '', pilRole = 0;
      if ((k === 'move6' || k === 'move7' || k === 'baobi') && pr.pilot) {   // 机师副头像 + 类型角标(剑/盾/子弹)
        const pi = q1('SELECT icon, rarity, role FROM characters WHERE id=?', [pr.pilot]) || {};
        pilRole = pi.role || 0;
        if (pi.icon) pipHtml = `<span class="avw avsm"><span class="picon sm">${imgTag(pi.icon)}</span>${roleBadge(pi.role)}${rarB(pi.rarity)}</span>`;
      } else if ((pr.required_units || []).length) {   // 需搭乘指定机体(固定搭配): 显示机体副头像
        const rq = q1('SELECT icon, role, rarity FROM units WHERE id=?', [+pr.required_units[0]]);
        if (rq && rq.icon) pipHtml = `<span class="avw avsm">${avTagR(rq.icon, rq.role, rq.rarity)}</span>`;
      }
      const roleMark = (pilRole && PROLE[pilRole]) ? `<b style="color:var(--${PROLE[pilRole].cls});font-weight:800">${PROLE[pilRole].t}</b> ` : '';   // 机师类型文字标记
      const avF = r.target_type === 'char' ? avDrv(r.ic, r.rl, r.rr) : avTagR(r.ic, r.rl, r.rr);
      return `<div class="lrow" data-t="${r.target_type}" data-id="${r.target_id}">${pipHtml ? `<span class="ticon-col">${avF}${pipHtml}</span>` : avF}
        <div class="nm" style="flex:1">${esc(r.nm || r.target_id)} ${r.rr ? rarTag(r.rr) : ''} ${k === 'unit_skill' ? `<div style="color:var(--dim);font-size:10px;margin-top:1px">${roleMark}${esc(r.label || '')}</div>` : `<span style="color:var(--dim);font-size:10px">${roleMark}${esc(r.label || '')}</span>`}
        <small>${esc((sub || '').slice(0, 60))}</small>${(k === 'move6' || k === 'move7') && r.target_type === 'unit' ? (() => {   // 6移动/支援防御范围7: 文字下方显示地形适性
          const tu = q1('SELECT terrain_space a, terrain_atm b, terrain_ground c, terrain_surface d, terrain_water e FROM units WHERE id=?', [r.target_id]);
          if (!tu) return '';
          const tt = [['宇宙', tu.a], ['空中', tu.b], ['地上', tu.c], ['水面', tu.d], ['水中', tu.e]].map(([nm2, v2]) => {
            const sym = v2 === 3 ? '○' : v2 === 2 ? '△' : v2 === 1 ? '×' : '—';
            const col = v2 === 3 ? '#7df0a8' : v2 === 2 ? '#f5c451' : v2 === 1 ? '#ff6b6b' : 'var(--dim)';
            return `${nm2}<b style="color:${col}">${sym}</b>`;
          }).join(' ');
          return `<div style="color:var(--dim);font-size:10px;margin-top:1px">地形 ${tt}</div>`;
        })() : ''}</div>${k === 'preemptive' ? `<span class="prebest" data-uid="${r.target_id}" style="flex:none;text-align:right;color:var(--dim);font-size:10px;line-height:1.35;max-width:33%;margin-left:6px">…</span>` : ''}</div>`; }).join('');
  if ($('fsort')) $('fsort').onclick = () => openSortPicker(fctx, () => pageFeat(v));
  if ($('ftag')) $('ftag').onclick = () => openTagPicker('feat', () => pageFeat(v));
  if ($('tkult')) $('tkult').onclick = () => { state.featTkUlt = !(state.featTkUlt !== false); pageFeat(v); };
  $('farea').querySelectorAll('.lrow').forEach(el => el.onclick = () => {
    const t = el.dataset.t, id = +el.dataset.id;
    if (t === 'char') { const c = q1('SELECT name FROM characters WHERE id=?', [id]); push({ page: 'char', title: c ? c.name : '', id }); }
    else { const u = q1('SELECT name FROM units WHERE id=?', [id]); push({ page: 'unit', title: u ? u.name : '', id }); }
  });
  if (k === 'preemptive') {   // 右侧小字: 对中防目标(20k)最大伤害及驾驶员（逐条后台计算, 结果缓存）
    state._preDmg = state._preDmg || {};
    const uids = [...new Set(sorted.filter(r => r.target_type === 'unit').map(r => r.target_id))];
    let ii = 0;
    const pTick = () => {
      if (!document.querySelector('.prebest[data-uid]')) return;    // 已切页
      if (ii >= uids.length) return;
      const uid = uids[ii++];
      try {
        const _pk = uid + '|' + (state.featPSpU !== false ? 1 : 0);
        if (!(_pk in state._preDmg)) state._preDmg[_pk] = (unitBestPilot(uid, 20000, 750, state.featPSpU)[0] || null);
        const b = state._preDmg[_pk];
        const el = document.querySelector(`.prebest[data-uid="${uid}"]`);
        if (el) {
          el.style.color = '';
          el.innerHTML = b ? `${esc(b.name)} <b style="color:#7df0a8">${fmt(b.dmg)}</b><br><span style="font-size:9px;color:#5f7196">${esc(b.weapon.name)}</span>` : '—';
        }
      } catch (e) {}
      setTimeout(pTick, 0);
    };
    setTimeout(pTick, 60);
  }
}

/* ------------ 更新中心 ------------ */
/* APP 版本更新说明(更新中心展示, 只保留最新版) */
const APP_CHANGELOG = [   // 更新说明(=最新版) / 更新日志(更新中心按钮, v0.103起每版一项)
  ['0.108', '综合更新：① 装置(機構)主数据接入 — 1128条/1027台/5种(防护盾防御848、变形机构260、逃生机能6、逃生机能(超强势)10、换装4)，图鉴详情新增「装置」区(名称/数值/完整说明) ② 第一击损伤无效标记(不限ULT：高达F91双V.S.B.R(EX)、超级海伯瑞安)，仅标记、伤害照常计算，特性页新增该分类 ③ 特性页MP新增「机体(主动MP)」区块 — 线性扫机体技能，V2突击暴风EX +3、卡斯巴尔专用高达 +6 ④ 防御eHP纳入机体被动防御%(含max满层，行内显示「防+X%」)，并修复条件被动1层判定bug(原恒为0层) ⑤ 主数据对账：地形1455台全一致、标签1454台中18台差异(wiki多出机体族标签) ⑥ 组队「选择防御/支援防御」改为二选一 — 原两者同开减伤叠加到100%(重复计算)，现互斥只取一次-40%；盾牌-20%对两者均生效'],
  ['0.107', '综合更新：① ULT改造系统 — ULT机体三段(SSR/UR/UR)共用同一套改造，0/50/100 三挡；Lv50 解锁该段 ULT 改造武器，Lv100 解锁每组三选一能力(攻击爆裂+20%伤害 / 威力抵御-20%受伤 / 支援攻防次数+1 / MP+6 等)，选择即时保存，图鉴新增 ULT改造能力卡。② 组队：攻击行绿色伤害下显示攻击力；防御 eHP 计入机体「最大HP提升」能力(超级海伯瑞 Lv100 HP 136,620)。计算/排行/组队新增「支援攻击/反击」开关：开=计入「支援攻击/支援反击/反击时」机体/驾驶员被动，关=按普通攻击不计入。③ 计算页修复 best 对象被行内注释吞字段导致的页面错误。④ 主数据与游戏 2.7.0 导出逐项核对，修正防御/回避标志、形态机地形、零件系列名；数据更新至 2026.10.17(新增机体13/机师9/武器70/支援3)；补齐45台机体原配机师；图鉴数值档位增加说明(max 含条件型被动/满层)；计算/排行/组队新增 max 满层开关(条件被动按1层，首动攻击次数型恒0层)；修正武器效果文本按武器特质名取属性(再生EX GN翼状獠牙=特殊、TRANS-AM EX=光束，不再按武器属性猜测)。'],
  ['0.105', '计算/排行/组队: 暴击率达到100%(含必暴)的武器/组合 无论暴击开关是否打开 均按暴击计算, 并标注「必暴」；对特定对手生效的机体/机师被动与武器特效在计算/排行/组队中注明条件(组队按所选防御机体标签匹配, 通用+条件被动开=全部生效)；特性新增「特攻」清单(可屏蔽ULT机体)；武器页补全「使用限制」(消耗HP/MP等)。'],
  ['0.104', '组队页「队伍增强」新增自定义增强，修复组队页全能力增强对基础值错误生效的bug，7移动标签改名支援防御范围7。'],
  ['0.103', '新增「首动」按钮(计算/组队/排行)：按官方AI优先度只算首动那1个技能 — 减伤(威力抵御)>+MP(首动超一击+30%)>+命中闪避>攻击爆裂(+损伤%)>摇摆闪避>增幅(按对应属性武器，随机体变化)>爆击增幅>保留EN；假设满血满EN·够得着；「反死风险」独立开关；主动技能⇄首动二选一；首动/第一击下多段增益锁定(仅全技能可开)。'],
];
function pageUpdate(v) {
  const meta = {}; q('SELECT * FROM meta').forEach(m => meta[m.key] = m.value);
  const log = q('SELECT * FROM update_log ORDER BY id DESC LIMIT 5');
  let counts = {}; try { counts = JSON.parse(meta.counts || '{}'); } catch (e) {}
  const when = meta.built_at ? new Date(meta.built_at * 1000).toLocaleString('zh-CN') : '—';
  const UPD_KEY = 'ggen_update_base';
  /* 多线路自动切换: 国内可直连镜像优先, GitHub 原线兜底(需梯子); window.__UPD_AUTO 可覆盖(测试用) */
  const UPD_AUTO = window.__UPD_AUTO || [
    'https://gh-proxy.com/https://raw.githubusercontent.com/ppgs5/ggen-data/main/',
    'https://ghproxy.net/https://raw.githubusercontent.com/ppgs5/ggen-data/main/',
    'https://cdn.jsdelivr.net/gh/ppgs5/ggen-data@main/',
    'https://raw.githubusercontent.com/ppgs5/ggen-data/main/',
  ];
  try { localStorage.removeItem(UPD_KEY); } catch (e) {}   // 已去掉自定义更新源, 清理遗留键
  const baseLabel = b => b.includes('cdn.jsdelivr') ? 'jsDelivr CDN' : (b.startsWith('https://raw.githubusercontent') ? 'GitHub 官方' : '镜像线路');
  const hasBridge = typeof window.Android !== 'undefined';
  let dbInfo = {}; try { dbInfo = hasBridge ? JSON.parse(window.Android.dbInfo()) : {}; } catch (e) {}
  let nPatches = 0; try { nPatches = hasBridge ? JSON.parse(window.Android.listPatches() || '[]').length : 0; } catch (e) {}
  v.innerHTML = `
    <div class="card"><h4>在线更新 · 数据仓库</h4>
      <div style="font-size:12px;line-height:1.7">数据版本 <b style="color:#bcd0f2">${esc(meta.version || '—')}</b> · 构建于 ${esc(when)}<br>
      <small style="color:var(--dim);font-size:10.5px">机体 ${fmt(counts.units)} · 武器 ${fmt(counts.weapons)} · 驾驶员 ${fmt(counts.characters)} · 战舰 ${fmt(counts.supporters)} · 零件 ${fmt(counts.mods)}</small></div>
      <div class="kv" style="margin-top:6px;color:var(--dim);font-size:10.5px">当前数据库：${dbInfo.custom ? '<b style="color:#9fe8c0">已下载更新（' + fmt(Math.round((dbInfo.size || 0) / 1e6)) + ' MB）</b>' : '内置数据'}${nPatches ? ' · <b style="color:#9fe8c0">' + nPatches + ' 个增量补丁已应用</b>' : ''}</div>
      <div class="btnrow" style="margin-top:9px"><span class="bp" id="upchk">检查更新</span>
        <span class="bs" id="upreset" style="${(dbInfo.custom || nPatches) ? '' : 'opacity:.5'}">恢复内置数据</span></div>
      <div id="upmsg" class="subnote" style="text-align:left;margin-top:6px">点击「检查更新」联网比对最新数据版本，发现新版可就地下载替换（无需重装 APK）</div>
    </div>
    <div class="card"><h4>APP 版本</h4>
      <div style="font-size:12px;line-height:1.7">当前版本 <b style="color:#bcd0f2" id="appver">—</b><span id="appnew"></span></div>
      <div class="kv" style="color:var(--dim);font-size:10px;margin-top:2px;word-break:break-all">安装包 SHA256：<span id="apksha" style="font-weight:400">读取中…</span></div>
      <div class="kv" id="appnote" style="color:var(--dim);font-size:10.5px;margin-top:4px">检测中…</div>
      <div class="btnrow" style="margin-top:9px"><span class="bp" id="appupd" style="display:none">下载并安装新版本</span></div>
    </div>
    <div class="card"><h4>APP 更新说明 <span class="fbtn" id="updlog" style="margin-left:6px;font-size:10.5px">📋 更新日志</span></h4>
      ${APP_CHANGELOG.slice(0, 1).map(([v2, s2]) => `<div class="kv" style="line-height:1.5"><b style="color:#bcd0f2">v${v2}</b> <span style="color:var(--dim);font-size:10.5px">${esc(s2)}</span></div>`).join('')}
    </div>
    <div class="card"><h4>更新历史</h4>
      ${log.map(l => { let s = {}; try { s = JSON.parse(l.summary_json || '{}'); } catch (e) {}
        return `<div class="kv">${esc(l.version)} · ${new Date(l.applied_at * 1000).toLocaleString('zh-CN')} · ${esc(s.type || '')}</div>`; }).join('') || '<div class="kv" style="color:var(--dim)">无</div>'}
    </div>
    <div class="card"><h4>备份与恢复</h4><div class="kv" style="color:var(--dim)">数据库文件即备份：web/data/ggen.db（${fmt(Math.round((window.__dbSize || 0) / 1e6))} MB）。重建前保留旧版即可回滚；App 内下载的更新库可用「恢复内置数据」清除。</div></div>
    <div class="card"><h4>关于</h4>
      <div class="kv" style="color:var(--dim)">作者：<b style="color:#cfe0ff">DeepSeek</b> · SD高达永恒助手</div>
      <div class="kv" style="color:var(--dim)">开源地址（源代码 + 关键数据 + APK 下载）：<b id="osurl" style="color:#9fd8ff;text-decoration:underline">github.com/ppgs5/SDGGE-Helper</b></div>
      <div class="kv" style="color:var(--dim)">免VPN镜像（无需梯子即可打开）：<b id="osurl2" style="color:#9fd8ff;text-decoration:underline">gh-proxy.com/https://github.com/ppgs5/SDGGE-Helper</b></div>
      <div class="kv" style="color:var(--dim)">数据来源：soshage / gamekee · 数据仓库：github.com/ppgs5/ggen-data</div>
      <div class="kv" style="color:var(--dim);margin-top:5px;line-height:1.65;border-top:1px dashed var(--line);padding-top:5px"><b style="color:#f5c451">免责条款</b>：本工具为第三方非官方作品，与 Bandai Namco（万代）无任何关联；使用存在账号风控与设备安全风险，使用者风险自担；仅供数据查询与伤害计算的学习交流。游戏内容版权归原权利方所有，数据整理自公开资料站（soshage / gamekee）。</div></div>`;
  const msg = html => { const el = $('upmsg'); if (el) el.innerHTML = html; };
  const MB = n => (n / 1048576).toFixed(n > 10485760 ? 1 : 2) + ' MB';
  /* —— APP 自更新: app_version.json(数据仓库) → Android.downloadApk → 系统安装 —— */
  function cmpVer(a, b) { const pa = String(a).split('.').map(Number), pb = String(b).split('.').map(Number); for (let i = 0; i < Math.max(pa.length, pb.length); i++) { const d = (pa[i] || 0) - (pb[i] || 0); if (d) return d > 0 ? 1 : -1; } return 0; }
  let appVer = ''; try { appVer = hasBridge && window.Android.appInfo ? (JSON.parse(window.Android.appInfo() || '{}').versionName || '') : ''; } catch (e) {}
  $('appver').textContent = appVer ? ('v' + appVer) : '网页版';
  if ($('apksha')) {   // 安装包 SHA256(动态读取当前 APK; 与 Release 页资产哈希一致)
    let sha = '';
    try { sha = (typeof window.Android !== 'undefined' && window.Android.apkSha256) ? window.Android.apkSha256() : ''; } catch (e) {}
    $('apksha').textContent = sha || '（网页版无安装包）各版本 SHA256 见 Releases 页';
  }
  const checkApp = async () => {
    if (!appVer) { $('appnote').textContent = '网页模式无 APP 更新（安装 APK 后可用）；作者：DeepSeek'; return; }
    /* 并行探测各线路取最高版本(镜像/CDN 可能缓存旧清单——顺序取第一条会误报已是最新) */
    const results = await Promise.allSettled(UPD_AUTO.map(b =>
      fetch(b + 'app_version.json?t=' + Date.now(), { cache: 'no-store' }).then(r => r.ok ? r.json() : null)));
    let av = null;
    for (const r of results) {
      if (r.status === 'fulfilled' && r.value && r.value.version && (!av || cmpVer(r.value.version, av.version) > 0)) av = r.value;
    }
    if (av) {
        if (cmpVer(av.version, appVer) > 0) {
          $('appnew').innerHTML = ' → <b style="color:#9fe8c0">v' + esc(av.version) + '</b> 可更新' + (av.size ? '（' + MB(av.size) + '）' : '');
          $('appnote').textContent = (av.note ? av.note + ' ' : '') + '下载完成后系统会弹出安装界面；未弹出可在通知栏或「下载」里手动安装。';
          $('appupd').style.display = '';
          $('appupd').onclick = () => {
            if (typeof window.Android === 'undefined' || !window.Android.downloadApk) { msg('请在 App 内下载新版本'); return; }
            const urls = (av.apk_urls && av.apk_urls.length) ? av.apk_urls : [av.apk_url, av.apk_mirror].filter(Boolean);
            if (!window.Android.downloadApk(JSON.stringify(urls), av.version)) { msg('已有下载任务进行中…'); return; }
            $('appupd').style.display = 'none';
            const t = setInterval(() => {
              let st2 = {}; try { st2 = JSON.parse(window.Android.apkState() || '{}'); } catch (e) {}
              if (st2.state === 'downloading') $('appnote').textContent = '正在下载新版本 APK… ' + (st2.pct || 0) + '%';
              else if (st2.state === 'installing') { $('appnote').innerHTML = '<b style="color:#9fe8c0">下载完成，已调起安装界面</b>；如未显示请到通知栏点击安装。'; clearInterval(t); }
              else if (st2.state === 'error') { $('appnote').innerHTML = '<b style="color:#f66">下载失败：' + esc(st2.err || '') + '</b> 可重试'; $('appupd').style.display = ''; clearInterval(t); }
            }, 800);
          };
        } else {
          $('appnew').innerHTML = ' <span style="color:#9fe8c0">已是最新</span>';
          $('appnote').textContent = '当前已是最新版本，无需更新。';   // 修: 此前停在「检测中…」
        }
    } else {
      $('appnote').textContent = '未能获取 APP 版本信息（网络原因，可稍后重试）';
    }
  };
  checkApp();
  if ($('updlog')) $('updlog').onclick = () => {
    const panel = $('sheetPanel');
    panel.innerHTML = `<div class="sheet-h"><b>更新日志</b><span class="x" id="sx">✕</span></div>
      <div style="padding:4px 14px 16px">${APP_CHANGELOG.map(([v2, s2]) => `<div class="kv" style="line-height:1.55;margin:8px 0"><b style="color:#bcd0f2">v${v2}</b><br><span style="color:var(--dim);font-size:11px">${esc(s2)}</span></div>`).join('')}</div>`;
    $('sx').onclick = closeSheet;
    $('sheet').classList.add('open');
  };
  if ($('osurl')) $('osurl').onclick = () => { if (window.Android && window.Android.openUrl) window.Android.openUrl('https://' + $('osurl').textContent); };
  if ($('osurl2')) $('osurl2').onclick = () => { if (window.Android && window.Android.openUrl) window.Android.openUrl('https://' + $('osurl2').textContent); };
  /* 完整更新（兜底）: Java 侧下载整库并热替换 */
  const startFullDl = (b, m) => {
    if (typeof window.Android === 'undefined') { msg('请在 App 内更新（网页版仅支持检查）'); return; }
    const url = b + 'ggen.db';
    if (!window.Android.downloadDb(url, m.db_sha256 || '')) { msg('已有下载任务在进行…'); return; }
    const sizeTxt = m.db_size ? MB(m.db_size) : '';
    msg('完整下载中 0%…');
    const timer = setInterval(() => {
      let st = {}; try { st = JSON.parse(window.Android.updateState()); } catch (e) {}
      if (st.state === 'downloading') msg(`完整下载中 ${st.pct || 0}%…${sizeTxt ? '（' + sizeTxt + '，请保持前台）' : ''}`);
      else if (st.state === 'done') { clearInterval(timer); msg('✅ 更新完成，正在重启…'); setTimeout(() => location.reload(), 1200); }
      else if (st.state === 'error') { clearInterval(timer); msg(`<span style="color:#f66">下载失败：${esc(st.err || '未知错误')}</span> <span class="bp" id="updl2" style="padding:3px 10px;font-size:11px">重试</span>`); $('updl2').onclick = () => startFullDl(b, m); }
    }, 500);
  };
  /* 增量更新: 逐个下载补丁(小文件)+新头像图片 → 存本地 → 重启后叠加生效 */
  const sha256hex = async bytes => {
    const dg = await crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(dg)].map(x => x.toString(16).padStart(2, '0')).join('');
  };
  const b64of = bytes => btoa(Array.from(bytes, c => String.fromCharCode(c)).join(''));
  const startPatches = async (b, m, patches, bases) => {
    if (typeof window.Android === 'undefined' || !window.Android.savePatch) { msg('请在 App 内更新（网页版仅支持检查）'); return; }
    const pbase = b + 'patches/';
    const imgs = patches.reduce((a, p) => a.concat(p.images || []), []);
    const fail = e => {
      msg(`<span style="color:#f66">增量下载失败：${esc(String((e && e.message) || e))}</span> <span class="bp" id="updl" style="padding:3px 10px;font-size:11px">重试</span>`);
      $('updl').onclick = () => startPatches(b, m, patches, bases);
    };
    for (let i = 0; i < patches.length; i++) {
      const p = patches[i];
      msg(`下载补丁 ${i + 1}/${patches.length} …（${MB(+p.size || 0)}）`);
      try {
        const r = await fetch(pbase + p.file + '?t=' + Date.now(), { cache: 'no-store' });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const text = await r.text();
        if (p.sha256 && window.crypto && crypto.subtle) {
          const hex = await sha256hex(new TextEncoder().encode(text));
          if (hex !== p.sha256) throw new Error('补丁校验失败');
        }
        if (!window.Android.savePatch(p.file, text)) throw new Error('补丁保存失败');
      } catch (e) { fail(e); return; }
    }
    let imgFail = 0;
    const tries = [...new Set([b, ...(bases || [])].filter(Boolean))];
    for (let i = 0; i < imgs.length; i++) {
      const im = imgs[i];
      msg(`下载头像 ${i + 1}/${imgs.length} …`);
      let ok = false;
      for (const bb of tries) {                       // 单张失败换线路重试(镜像可能对刚发布的文件短时 404/缓存旧)
        try {
          const r = await fetch(bb + 'patches/img/' + im.file + '?t=' + Date.now(), { cache: 'no-store' });
          if (!r.ok) continue;
          const bytes = new Uint8Array(await r.arrayBuffer());
          if (im.sha256 && window.crypto && crypto.subtle && (await sha256hex(bytes)) !== im.sha256) continue;
          if (window.Android.saveImage && window.Android.saveImage(im.file, b64of(bytes))) { ok = true; break; }
        } catch (e) {}
      }
      if (!ok) imgFail++;
    }
    if (imgFail) {                                    // 数据已保存: 不因头像失败整体重来, 之后「检查更新」会自动补齐
      msg(`✅ 数据更新已就绪（${patches.length} 个补丁）；<span style="color:#f6b656">⚠️ ${imgFail} 张头像下载失败</span>（可稍后在「检查更新」时自动补齐）
        <span class="bp" id="upre" style="padding:3px 10px;font-size:11px">重启生效</span>`);
      $('upre').onclick = () => location.reload();
      return;
    }
    msg(`✅ 增量更新完成（${patches.length} 个补丁${imgs.length ? ' · ' + imgs.length + ' 张头像' : ''}），正在重启…`);
    setTimeout(() => location.reload(), 1200);
  };
  /* 头像校验/补齐: 本地(优先已下载→内置)取图比对 sha256, 缺失/不符则依次走各线路重下 → 「已是最新」时也可自愈 */
  const repairImages = async (m, used, bases) => {
    if (typeof window.Android === 'undefined' || !window.Android.saveImage) return { fixed: 0, fail: 0 };
    const imap = {};
    for (const p of (m.patches || [])) for (const im of (p.images || [])) imap[im.file] = im;
    const tries = [...new Set([used, ...(bases || [])].filter(Boolean))];
    let fixed = 0, fail = 0;
    for (const im of Object.values(imap)) {
      let need = false;
      try {
        const r = await fetch('img/' + im.file + '?t=' + Date.now(), { cache: 'no-store' });
        if (!r.ok) need = true;
        else {
          const bytes = new Uint8Array(await r.arrayBuffer());
          if (im.sha256 && window.crypto && crypto.subtle && (await sha256hex(bytes)) !== im.sha256) need = true;
        }
      } catch (e) { need = true; }
      if (!need) continue;
      let ok = false;
      for (const bb of tries) {
        try {
          const r = await fetch(bb + 'patches/img/' + im.file + '?t=' + Date.now(), { cache: 'no-store' });
          if (!r.ok) continue;
          const bytes = new Uint8Array(await r.arrayBuffer());
          if (im.sha256 && window.crypto && crypto.subtle && (await sha256hex(bytes)) !== im.sha256) continue;
          if (window.Android.saveImage(im.file, b64of(bytes))) { ok = true; fixed++; break; }
        } catch (e) {}
      }
      if (!ok) fail++;
    }
    return { fixed, fail };
  };
  const fetchManifest = async b => {
    const ctl = new AbortController();
    const tmr = setTimeout(() => ctl.abort(), 8000);
    try {
      const r = await fetch(b + 'version.json?t=' + Date.now(), { cache: 'no-store', signal: ctl.signal });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return await r.json();
    } finally { clearTimeout(tmr); }
  };
  $('upchk').onclick = async () => {
    msg('检查中（自动选择线路）…');
    const bases = UPD_AUTO.slice();
    let m = null, used = null, lastErr = '';
    /* 并行探测各线路, 取 built_at 最新的清单(镜像/CDN 可能缓存旧清单——只取"最快"会误报已是最新) */
    const results = await Promise.allSettled(bases.map(b => fetchManifest(b).then(mm => ({ mm: mm, b: b }))));
    for (const r of results) {
      if (r.status !== 'fulfilled' || !r.value || !r.value.mm) continue;
      if (!m || (+r.value.mm.built_at || 0) > (+m.built_at || 0)) { m = r.value.mm; used = r.value.b; }
    }
    if (!m) {
      lastErr = results.map(r => r.status === 'rejected' ? String((r.reason && r.reason.message) || r.reason) : '')
                       .filter((v, i, a) => v && a.indexOf(v) === i).slice(0, 2).join('; ');
    }
    if (!m) {
      msg(`<span style="color:#f66;font-weight:700">❌ 检查更新失败</span><span style="color:#f66">：所有线路均无法连接</span>
        <br><span style="color:var(--dim);font-size:10.5px">（${esc(lastErr)}）请检查网络后重试（镜像线路均不可达时请连 VPN 或稍后再试）</span>`);
      return;
    }
    const via = `（线路：${baseLabel(used)}）`;
    const localAt = +meta.built_at || 0;
    try {                                   // 链重写后: 本地比基础库新、但不在清单链里的补丁 → 清理(否则启动时仍会重放旧文件)
      const chainFiles = new Set((m.patches || []).map(p => p.file));
      for (const n of JSON.parse(window.Android.listPatches() || '[]')) {
        const mm2 = /^p_(\d+)\.sql$/.exec(n);
        if (mm2 && +mm2[1] > localAt && !chainFiles.has(n) && window.Android.deletePatch) window.Android.deletePatch(n);
      }
    } catch (e) {}
    if (!(+m.built_at > localAt)) {
      msg(`✅ 已是最新数据（${esc(meta.version || '')}）<span style="color:var(--dim)">${via}</span>
        <br><span style="color:var(--dim);font-size:10.5px">正在校验头像图片…</span>`);
      const fr = await repairImages(m, used, bases);
      if (fr.fixed) { msg(`✅ 已是最新数据 · 已补齐头像 <b style="color:#9fe8c0">${fr.fixed}</b> 张，正在重启…`); setTimeout(() => location.reload(), 1400); }
      else if (fr.fail) msg(`✅ 已是最新数据（${esc(meta.version || '')}）<span style="color:var(--dim)">${via}</span>
        <br><span style="color:#f6b656">⚠️ 有 ${fr.fail} 张头像补齐失败（线路异常？稍后可再试）</span>`);
      else msg(`✅ 已是最新数据（${esc(meta.version || '')}）<span style="color:var(--dim)">${via} · 头像已校验</span>`);
      return;
    }
    /* 增量链校验: 补丁须从当前版本逐级衔接(cumulative diff) */
    const patches = (m.patches || []).filter(p => +p.built_at > localAt).sort((a, c) => a.built_at - c.built_at);
    let cur = localAt, chainOk = patches.length > 0;
    for (const p of patches) {
      if (+p.from_built_at !== cur) { chainOk = false; break; }
      cur = +p.built_at;
    }
    chainOk = chainOk && cur === +m.built_at;
    const fullBtn = `<span class="bp" id="upfull" style="padding:3px 10px;font-size:11px;background:#2a3a5c">完整更新${m.db_size ? '(' + MB(m.db_size) + ')' : ''}</span>`;
    if (chainOk) {
      const total = patches.reduce((s, p) => s + (+p.size || 0), 0);
      const nImg = patches.reduce((s, p) => s + ((p.images || []).length), 0);
      msg(`发现新版本 <b style="color:#9fe8c0">${esc(m.version || '')}</b> · <b>增量 ${patches.length} 个补丁 · ${MB(total)}${nImg ? ' · 新头像 ' + nImg + ' 张' : ''}</b> ${via}
        <span class="bp" id="updl" style="padding:3px 10px;font-size:11px">增量更新</span> ${fullBtn}
        <br><span style="color:var(--dim);font-size:10.5px">增量仅下载变化的数据与头像，几秒钟即可完成</span>`);
      $('updl').onclick = () => startPatches(used, m, patches, bases);
    } else {
      msg(`发现新版本 <b style="color:#9fe8c0">${esc(m.version || '')}</b>${m.db_size ? '（' + MB(m.db_size) + '）' : ''} ${via}
        <span class="bp" id="upfull" style="padding:3px 10px;font-size:11px">完整更新</span>
        <br><span style="color:var(--dim);font-size:10.5px">版本跨度较大，需完整更新一次</span>`);
    }
    $('upfull').onclick = () => startFullDl(used, m);
  };
  $('upreset').onclick = () => {
    if (typeof window.Android === 'undefined') { msg('当前为内置数据'); return; }
    let di = {}; try { di = JSON.parse(window.Android.dbInfo()); } catch (e) {}
    let nP = 0; try { nP = JSON.parse(window.Android.listPatches() || '[]').length; } catch (e) {}
    if (!di.custom && !nP) { msg('当前已是内置数据'); return; }
    if (!confirm('删除已下载的更新数据（含增量补丁），恢复为内置版本？')) return;
    window.Android.deleteDb();
    if (window.Android.clearPatches) window.Android.clearPatches();
    if (window.Android.clearImages) window.Android.clearImages();
    msg('已恢复内置数据，正在重启…');
    setTimeout(() => location.reload(), 800);
  };
}

/* ------------ 路由表 ------------ */
const PAGES = {
  units: pageUnits, calc: pageCalc, rank: pageRank, team: pageTeam, feat: pageFeat, update: pageUpdate,
  unit: pageUnit, char: pageChar, weapon: pageWeapon, supp: pageSupp, mod: pageMod,
};


/* ------------ 安卓返回键钩子 ------------ */
window.__appBack = () => {
  if ($('sheet').classList.contains('open')) { closeSheet(); return true; }
  if (state.stack.length) { pop(); return true; }
  return false;
};

/* ------------ 启动 ------------ */
(async function boot() {
  const log = m => { $('splashlog').textContent = m; };
  try {
    setInterval(() => { const d = new Date(); $('clock').textContent = `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`; }, 1000);
    log('加载 sql.js…');
    const SQL = await initSqlJs({ locateFile: f => 'vendor/' + f });
    log('加载数据库（42MB）…');
    const buf = await (await fetch('data/ggen.db')).arrayBuffer();
    window.__dbSize = buf.byteLength;
    db = new SQL.Database(new Uint8Array(buf));
    applyPatches();                      // 增量补丁: 叠加到基础库(内存), 幂等可重放
    log('就绪');
    $('splash').style.display = 'none';
    $('app').style.visibility = 'visible';
    render();
    /* 空闲预热(一次性, 自动化环境跳过避免测试时序): 离屏渲染 组队/排行 → 填结果缓存, 使首次点击秒开 */
    const _prewarm = () => {
      const warm = fn => { try { const off = document.createElement('div'); off.style.display = 'none'; document.body.appendChild(off); fn(off); setTimeout(() => off.remove(), 4000); } catch (e) { console.warn('prewarm', e); } };
      if (state.tab !== 'team') warm(pageTeam);
      if (state.tab !== 'rank') warm(pageRank);
    };
    window.__prewarm = _prewarm;
    if (!navigator.webdriver) setTimeout(() => { if (!state._preWarm) { state._preWarm = 1; _prewarm(); } }, 2600);
  } catch (e) {
    log('启动失败: ' + e.message);
    console.error(e);
  }
})();
