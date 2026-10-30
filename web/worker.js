/* 组队排名 · 多线程 Worker
   复用同一份 app.js 计算代码(importScripts), 每个 Worker 自带只读数据库副本;
   主线程只传「页面设置 + 筛选 + 机体区间」, 数据不出 Worker。 */
importScripts('vendor/sql-wasm.js', 'engine.js', 'app.js');

let ready = null;
let _dbBytes = null;
let _SQL = null;
function initDB() {
  if (ready) return ready;
  ready = (async () => {
    const t0 = performance.now();
    _SQL = _SQL || await initSqlJs({ locateFile: f => 'vendor/' + f });
    const t1 = performance.now();
    let bytes = _dbBytes;
    if (!bytes) { const buf = await (await fetch('data/ggen.db')).arrayBuffer(); bytes = new Uint8Array(buf); }
    const t2 = performance.now();
    db = new _SQL.Database(bytes);
    const t3 = performance.now();
    self.__dbTiming = { sqljs: Math.round(t1 - t0), fetch: Math.round(t2 - t1), open: Math.round(t3 - t2) };
    return true;
  })();
  return ready;
}

self.onmessage = async (ev) => {
  const msg = ev.data || {};
  if (msg.type === 'db') { try { _dbBytes = msg.bytes instanceof Uint8Array ? msg.bytes : new Uint8Array(msg.bytes); } catch (e) {} return; }
  if (msg.type === 'warm') {
    try {
      await initDB();
      /* 预热: 跑一个 2 台机体的极小排名, 把武器/驾驶员/标签等表缓存建好, 首次真实计算就不必再等 */
      try {
        state.team = Object.assign({ vigor: 'default', star: 3, buffs: [], range: [1, 2, 3, 4, 5, 6], tdef: 10000, tcdef: 750, defup: 0, tAtk: 0, tDef: 0, tHp: 0, tMob: 0, atkup: 0, oDef: 0, oHp: 0, oMob: 0, ca: true, mp: false, skills: false, first: false, fdth: false, s3u: true, spU: true, sspU: true, pSpU: true, prole: null, prar: null, rar: null, urole: null, wat: null, atk: null, terr: '', terrO: false, cbOn: false, cbuff: null, suppId: null, shipStar: 0, dunit: null, dchar: null, guard: false, sdef: false }, {});
        const f = filt('team');
        const { cfg, opts } = teamRankArgs(state.team, f);
        opts.unitSlice = [0, 2];
        buildRanking(f, cfg, opts);
      } catch (e) {}
      self.postMessage({ type: 'warmed', timing: self.__dbTiming || null });
    } catch (e) { self.postMessage({ type: 'warmErr', err: String(e) }); }
    return;
  }
  if (msg.type === 'ping') { self.postMessage({ type: 'pong', ok: true, hasBuild: typeof buildRanking === 'function' }); return; }
  if (msg.type === 'rank') {
    try {
      await initDB();
      /* 还原主线程的页面设置/筛选(纯数据), 使 teamRankArgs 复算出完全相同的 cfg/opts */
      state.team = msg.t;
      state.zoom = msg.zoom || state.zoom;
      state.uSk = msg.uSk; state.supAct = msg.supAct; state.maxOn = msg.maxOn; state.ultLv = msg.ultLv; state.ultSkill = msg.ultSkill || {};
      const { cfg, opts } = teamRankArgs(msg.t, msg.f);
      opts.unitSlice = msg.slice;
      const G = buildRanking(msg.f, cfg, opts);
      self.postMessage({ type: 'rankDone', token: msg.token, main: G.main || [], sup: G.sup || [], def: G.def || [] });
    } catch (e) {
      self.postMessage({ type: 'rankErr', token: msg.token, err: String((e && e.stack) || e) });
    }
  }
};
