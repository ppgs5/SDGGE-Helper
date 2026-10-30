/* 伤害引擎 — 移植自 reference/engine.py（口径=soshage 引擎，已 50/50 回归验证）
   注意: correction 两项是系数不是百分比（corr ≈ +5×base，总伤 ≈ base×6~7） */
'use strict';
const Engine = (() => {
  const ceil = Math.ceil;
  const VIGOR = {
    'default':     { rate: 0,  crit: 10, label: '默认' },
    'mid':         { rate: 0,  crit: 10, label: '无气势' },
    'high':        { rate: 10, crit: 20, label: '强势' },
    'max':         { rate: 20, crit: 20, label: '超强势' },
    'supercharged':{ rate: 30, crit: 30, label: '超一击' },
  };

  function damage(o) {
    const ua = o.unitAtk, ca = o.charAtk, tu = o.tUnitDef, tc = o.tCharDef;
    const power = o.power, p = o.p || 0, m = o.m || 0, terrain = o.terrain ?? 100;
    const t = Math.max(0, ca - tc) / 5000;
    const n = Math.max(0, ceil(ua / 10 - tu / 10)) / 5000;
    const i = 1 / (Math.exp(250 * (tc - ca) / 1e5) + 1);
    const sig = 1 / (Math.exp(25 * (tu - ua) / 1e5) + 1);
    const base = ceil((t + n + i + sig) * power);
    const ac = ceil((ua + 2 * ca) / 10), dc = ceil((tu + 2 * tc) / 10);
    const corr = (100 / (Math.exp((5000 - ac) * 30 / 1e5) + 1)
                + (-40) / (Math.exp((5000 - dc) * 3 / 1e5) + 1)) * base;
    const battle = ceil((base + p + m + corr) * terrain / 100);
    const ee = o.ee || 0;
    const scaled = ceil(ee * battle / 100);
    let total = battle + (o.fixedAdd || 0) - (o.fixedSub || 0) + scaled;
    let combined = total * (o.defensive ?? 1);
    let fin = Math.max(0, ceil(combined * ((o.critCorr || 0) + 100) / 100));
    if (o.negation && fin <= o.negation) fin = 0;
    return { final: fin, base, battle, corrFactor: base ? +(corr / base).toFixed(3) : 0 };
  }

  /* 武器有效威力（按武器等级成长表 wsc） */
  const _wpCache = new Map();   // 性能: 组队全量计算时 weaponPower 占 ~30% CPU, 结果只与武器/等级相关, 直接缓存
  function weaponPower(w, lv) {
    const key = w.id + '|' + lv + '|' + (w.power || 0) + '|' + (w._sspAdd || 0) + '|' + (Array.isArray(w.wsc) ? 'a' : (w.wsc_json || '').length);
    const hit = _wpCache.get(key);
    if (hit !== undefined) return hit;
    let wsc = w.wsc;
    if (!Array.isArray(wsc)) {
      try { wsc = JSON.parse(w.wsc_json || '[]'); } catch (e) { wsc = []; }
    }
    const row = wsc.find(x => x.level === lv) || wsc[0];
    const pct = row ? row.power : 100;
    const v = Math.floor((w.power || 0) * pct / 100) + (w._sspAdd || 0);   // _sspAdd: 改装核心(SSP满10)威力平加
    if (_wpCache.size < 20000) _wpCache.set(key, v);
    return v;
  }

  /* 条件类武装POWER提升（引擎口径: 44,45,81,82,91,92 → 威力×(1+Σ%)） */
  const POWER_TRAITS = new Set([44, 45, 81, 82, 91, 92]);
  function powerBoostPct(wtraits, lv) {
    let pct = 0;
    for (const t of (wtraits || [])) {
      if (t.level === lv && t.trait_type && POWER_TRAITS.has(t.trait_type) && t.trait_value > 0) pct += t.trait_value;
    }
    return pct;
  }
  /* 39 = 暴击伤害提升%（暴击时计入增伤区，不参与威力） */
  function critDmgPct(wtraits, lv) {
    let pct = 0;
    for (const t of (wtraits || [])) {
      if (t.level === lv && t.trait_type === 39 && t.trait_value > 0) pct += t.trait_value;
    }
    return pct;
  }

  /* 武器效果层: 按等级汇总目标防御修正（贯穿: trait_type 9=百分比 / 10=固定） */
  function targetDefAdjust(wtraits, lv) {
    let pct = 0, flat = 0;
    for (const t of (wtraits || [])) {
      if (t.level !== lv) continue;
      if (t.trait_type === 9) pct += (t.trait_value || 0);
      else if (t.trait_type === 10) flat += (t.trait_value || 0);
    }
    return { pct, flat };
  }

  /* 单次伤害（含武器等级成长、武装POWER效果与贯穿效果） */
  function damageWithWeapon(unitAtk, charAtk, w, wtraits, lv, tUnitDef, tCharDef, o = {}) {
    const adj = targetDefAdjust(wtraits, lv);
    const def = (tUnitDef + adj.flat) * (1 + adj.pct / 100);
    const pb = (o.noPowerBoost ? 0 : powerBoostPct(wtraits, lv));
    const power = Math.floor(weaponPower(w, lv) * (1 + (pb + (o.powerAdd || 0)) / 100));   // o.powerAdd: 武器效果「远距离时POWER提升」按最大档计入
    const vg = VIGOR[o.vigor || 'default'];
    const cdmg = o.crit ? critDmgPct(wtraits, lv) + (o.critDmgAdd || 0) : 0;   // 武器/机体/驾驶员39: 暴击时增伤区加算
    const ee = (o.ee || 0) + vg.rate + cdmg - (o.defReduce || 0);   // 增伤区（含气势/暴击伤害; 承伤减免与增伤同池相减）
    const crit = o.crit ? vg.crit : 0;                   // 暴击独立乘区
    const r = damage({
      unitAtk, charAtk, power,
      tUnitDef: def, tCharDef,
      ee, critCorr: crit, defensive: o.defensive ?? 1, terrain: o.terrain ?? 100,
    });
    return { ...r, defUsed: Math.round(def), effPower: power, powerPct: pb, critDmg: cdmg };
  }

  return { damage, weaponPower, powerBoostPct, critDmgPct, targetDefAdjust, damageWithWeapon, VIGOR };
})();
