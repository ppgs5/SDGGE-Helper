# -*- coding: utf-8 -*-
"""v0.59 验证: ①队伍增强多条件desc修复(SD高达) ②特性-摇摆闪避(主动闪避技能驾驶员, 标签/系列/稀有度/类型筛选)
③更新中心: 头像校验补齐(已是最新也可自愈) + 头像下载失败软着陆(数据不丢) + 恢复内置按钮状态"""
import hashlib, json, os, shutil, sqlite3, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
sys.path.insert(0, os.path.join(HERE, 'data'))

PORT = 8997
BASE = f'http://127.0.0.1:{PORT}/'

# ---------- ⓪ 数据层: 队伍增强 desc 修复 + 闪避技能统计 ----------
db = sqlite3.connect(os.path.join(HERE, 'data', 'ggen.db'))
db.row_factory = sqlite3.Row
rows = {}
for r in db.execute("SELECT params_json FROM features WHERE feature='team_buff' AND target_type='char' AND target_id=1700000200"):
    p = json.loads(r['params_json'])
    if p.get('desc'):
        rows[p['target_tags'][0]] = p
assert rows['高达']['desc'] == '赋予同部队内持有【高达】标签的单位，攻击力、防御力提升2%(永久)', f"高达desc: {rows['高达']['desc']}"
assert rows['SD高达']['desc'] == '赋予同部队内持有【SD高达】标签的单位，攻击力、防御力提升3%(永久)', f"SD高达desc: {rows['SD高达']['desc']}"
assert '【高达】标签的单位，攻击力、防御力提升3%' not in rows['高达']['desc'], '高达组不应再出现被拍平的3%行'
print('[⓪ 队伍增强desc] 通过(高达2% / SD高达3% 各自正确)')

def evade_chars(use_sp):
    base, sp = {}, {}
    for tbl, tgt in [('char_skills', base), ('char_skills_sp', sp)]:
        for r in db.execute(f'SELECT char_id, sort, name, traits_json FROM {tbl}'):
            for t in json.loads(r['traits_json'] or '[]'):
                tr = t.get('trait') or {}
                if (tr.get('trait_type') == 6 and (tr.get('trait_value') or 0) > 0) or (tr.get('trait_type') == 14 and '闪避' in (tr.get('desc') or '')):
                    tgt.setdefault(r['char_id'], {})[r['sort']] = r['name']
                    break
    playable = {r['id'] for r in db.execute('SELECT id FROM characters WHERE COALESCE(is_playable,1)=1')}
    out = {}
    for cid in set(base) | (set(sp) if use_sp else set()):
        if cid not in playable: continue
        eff = dict(base.get(cid, {}))
        if use_sp: eff.update(sp.get(cid, {}))
        if eff: out[cid] = eff
    return out
N_SP, N_NOS = len(evade_chars(True)), len(evade_chars(False))
print(f'[⓪ 闪避技能] SP开 {N_SP} 位 / SP关 {N_NOS} 位')
assert 1999000100 in evade_chars(True), '塞西娅应在闪避技能驾驶员内'
assert N_SP > N_NOS, 'SP版应新增部分驾驶员(基础无闪避技能)'

# ---------- 更新流程夹具 ----------
PATCH_DIR = os.path.join(WEB, 'patches')
IMG_OK = 'thumb/v59_ok.webp'
IMG_MISS = 'thumb/v59_miss.webp'
IMG_BAD = 'thumb/v59_bad.webp'
os.makedirs(os.path.join(WEB, 'patches', 'img', 'thumb'), exist_ok=True)
OK_BYTES = b'WEBP-V59-OK' + b'o' * 300
with open(os.path.join(PATCH_DIR, 'img', 'thumb', 'v59_ok.webp'), 'wb') as f: f.write(OK_BYTES)
with open(os.path.join(PATCH_DIR, 'img', 'thumb', 'v59_miss.webp'), 'wb') as f: f.write(OK_BYTES)
BAD_BYTES = b'WEBP-V59-BAD' + b'b' * 300
with open(os.path.join(PATCH_DIR, 'img', 'thumb', 'v59_bad.webp'), 'wb') as f: f.write(BAD_BYTES)
# 本地已存在且一致(ok) / 本地缺失(miss) / 本地存在但不一致(bad: 本地放旧字节)
os.makedirs(os.path.join(WEB, 'img', 'thumb'), exist_ok=True)
with open(os.path.join(WEB, 'img', 'thumb', 'v59_ok.webp'), 'wb') as f: f.write(OK_BYTES)
with open(os.path.join(WEB, 'img', 'thumb', 'v59_bad.webp'), 'wb') as f: f.write(b'STALE-LOCAL')
for p in (os.path.join(WEB, 'img', 'thumb', 'v59_miss.webp'),):
    if os.path.exists(p): os.remove(p)
SHA_OK = hashlib.sha256(OK_BYTES).hexdigest()
SHA_BAD = hashlib.sha256(BAD_BYTES).hexdigest()
BASE_AT = int(sqlite3.connect(os.path.join(WEB, 'data', 'ggen.db')).execute("SELECT value FROM meta WHERE key='built_at'").fetchone()[0])

PATCH_FILE = f'p_{BASE_AT + 100}.sql'
PATCH_SQL = "BEGIN;\nUPDATE meta SET value=value WHERE key='version';\nCOMMIT;\n"
with open(os.path.join(PATCH_DIR, PATCH_FILE), 'w', encoding='utf-8') as f: f.write(PATCH_SQL)

def write_manifest(patches, built_at=None):
    m = {'version': 'v2026.10.08', 'built_at': built_at or BASE_AT, 'patches': patches}
    with open(os.path.join(WEB, 'version.json'), 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False)

MOCK = """
window.__mock = {saved: {}, images: {}, deletedPatches: [], cleared: false};
window.__UPD_AUTO = ['http://127.0.0.1:59998/dead/', '%(base)s'];
window.Android = {
  dbInfo: () => JSON.stringify({custom: false, size: 999}),
  listPatches: () => JSON.stringify(Object.keys(window.__mock.saved)),
  readPatch: n => '',
  savePatch: (n, c) => { window.__mock.saved[n] = (c || '').length; return true; },
  saveImage: (n, b64) => { window.__mock.images[n] = (b64 || '').length; return true; },
  deletePatch: n => { window.__mock.deletedPatches.push(n); },
  clearPatches: () => { window.__mock.cleared = true; },
  clearImages: () => { window.__mock.clearedImages = true; },
  deleteDb: () => {},
  downloadDb: () => true,
  updateState: () => JSON.stringify({state: 'idle', pct: 0, err: ''}),
};
""" % {'base': BASE}

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(120000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.add_init_script(MOCK)

        # ---------- ① 队伍增强显示(sheet + 特性页) ----------
        pg.goto(BASE + 'index.html'); pg.wait_for_selector('#splash', state='hidden')
        gs = pg.evaluate("() => teamBuffGroups().filter(g => g.target_id === 1700000200).map(g => [g.tags.join('·'), g.atk, g.def, g.desc])")
        print('[① 队伍增强组]', gs)
        assert ['SD高达', 3, 3, '赋予同部队内持有【SD高达】标签的单位，攻击力、防御力提升3%(永久)'] in gs, gs
        assert ['高达', 2, 2, '赋予同部队内持有【高达】标签的单位，攻击力、防御力提升2%(永久)'] in gs, gs
        # 弹窗渲染
        pg.evaluate("() => showTeamBuffs()"); pg.wait_for_timeout(600)
        sheet_txt = pg.evaluate("() => document.getElementById('sheetPanel').textContent")
        assert 'SD高达' in sheet_txt and '【SD高达】标签' in sheet_txt, '队伍增强弹窗应显示SD高达条件'
        pg.evaluate("() => closeSheet()")

        # ---------- ② 摇摆闪避 特性 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_timeout(500)
        tks = pg.evaluate("() => [...document.querySelectorAll('[data-k]')].map(e => e.textContent)")
        assert '摇摆闪避' in tks, f'缺少摇摆闪避tab: {tks}'
        pg.evaluate("() => { state.featKind = 'sway_evade'; pageFeat(document.getElementById('view')); }"); pg.wait_for_timeout(800)
        n_on = pg.evaluate("() => document.querySelectorAll('#farea .lrow').length")
        print(f'[② 摇摆闪避] SP开 {n_on} 位')
        assert n_on == N_SP, f'SP开人数应={N_SP}: {n_on}'
        be = pg.evaluate("() => { const e = [...document.querySelectorAll('#farea .lrow')].find(x => x.textContent.includes('塞西娅')); return e ? e.textContent.replace(/\\s+/g, ' ').trim() : null; }")
        print('[② 塞西娅行]', be)
        assert be and '摇摆闪避' in be and '闪避+100%' in be, be
        # 筛选: 稀有度/类型/标签/系列 (走真实状态键)
        for cond, want, label in [
            ("filt('feat').rar = 5", 32, '稀有度UR'),
            ("filt('feat').rar = null; filt('feat').role = 3", 31, '支援型'),
            ("filt('feat').role = null; filt('feat').tags = [1001]", 54, '宇宙世纪系列'),
        ]:
            n = pg.evaluate(f"() => {{ {cond}; pageFeat(document.getElementById('view')); return document.querySelectorAll('#farea .lrow').length; }}")
            print(f'[② 筛选 {label}]', n)
            assert n == want, f'{label} 应={want}: {n}'
        exa = pg.evaluate("() => { filt('feat').tags = []; filt('feat').series = [1999000000]; pageFeat(document.getElementById('view')); return [...document.querySelectorAll('#farea .lrow')].map(e => e.textContent.replace(/\\s+/g,' ').trim()); }")
        print('[② 系列GUNDAM EXA]', exa)
        assert len(exa) == 1 and '塞西娅' in exa[0], exa
        pg.evaluate("() => { filt('feat').series = []; pageFeat(document.getElementById('view')); }")
        # SP关
        n_off = pg.evaluate("() => { state.featPSpU = false; pageFeat(document.getElementById('view')); const n = document.querySelectorAll('#farea .lrow').length; state.featPSpU = true; pageFeat(document.getElementById('view')); return n; }")
        print(f'[② 摇摆闪避] SP关 {n_off} 位')
        assert n_off == N_NOS, f'SP关人数应={N_NOS}: {n_off}'
        # 排序字段
        sf = pg.evaluate("() => sortOf('feat_sway_evade')")
        print('[② 默认排序]', sf)
        assert sf['f'] == 'ev' and sf['d'] == -1

        # ---------- ③ 更新: 已是最新 → 头像校验补齐 ----------
        imgs = [
            {'file': IMG_OK, 'sha256': SHA_OK, 'size': len(OK_BYTES)},
            {'file': IMG_MISS, 'sha256': SHA_OK, 'size': len(OK_BYTES)},
            {'file': IMG_BAD, 'sha256': SHA_BAD, 'size': len(BAD_BYTES)},
        ]
        write_manifest([{'built_at': BASE_AT, 'from_built_at': BASE_AT - 1, 'to': 'v2026.10.08', 'file': 'p_x.sql', 'size': 1, 'sha256': 'x', 'images': imgs}])
        pg.evaluate("() => push({ page: 'update', title: '更新中心' })"); pg.wait_for_timeout(400)
        pg.click('#upchk')
        saved, msg = None, ''
        for _ in range(14):                          # 补齐后会 1.4s 自动重载, 重载前取结果
            pg.wait_for_timeout(200)
            msg = pg.evaluate("() => (document.getElementById('upmsg') || {}).textContent || ''")
            if '已补齐头像' in msg or '头像补齐失败' in msg:
                saved = pg.evaluate("() => window.__mock.images"); break
        print('[③ 头像校验] 已保存:', list((saved or {}).keys()), '| msg:', msg.replace('\n', ' ')[:80])
        assert saved is not None and IMG_MISS in saved, '缺失头像应被补齐'
        assert IMG_BAD in saved, 'sha不符头像应被重下'
        assert IMG_OK not in saved, '校验通过的头像不应重下'
        assert '已补齐头像' in msg, msg

        # ---------- ④ 头像下载失败: 数据不丢 + 软着陆 ----------
        pg.wait_for_timeout(1600)                    # 等待可能的自动重载
        pg.goto(BASE + 'index.html'); pg.wait_for_selector('#splash', state='hidden')
        write_manifest([{'built_at': BASE_AT + 100, 'from_built_at': BASE_AT, 'to': 'v2026.10.08', 'file': PATCH_FILE,
                         'size': len(PATCH_SQL.encode()), 'sha256': hashlib.sha256(PATCH_SQL.encode()).hexdigest(),
                         'images': [{'file': 'thumb/dead.webp', 'sha256': '0' * 64, 'size': 9}]}], built_at=BASE_AT + 100)
        pg.evaluate("() => push({ page: 'update', title: '更新中心' })"); pg.wait_for_timeout(300)
        pg.click('#upchk'); pg.wait_for_timeout(1200)
        assert pg.evaluate("() => !!document.getElementById('updl')"), '应显示增量更新按钮'
        pg.click('#updl'); pg.wait_for_timeout(3000)
        saved2 = pg.evaluate("() => window.__mock.saved")
        msg2 = pg.evaluate("() => document.getElementById('upmsg').textContent")
        print('[④ 头像失败软着陆] saved:', list(saved2.keys()), '| msg:', msg2.replace('\n', ' ')[:90])
        assert PATCH_FILE in saved2, '补丁应已保存(数据不丢)'
        assert '头像下载失败' in msg2 and '重启生效' in msg2, msg2

        # ---------- ⑥ 计算/排行/组队: 三星+SP 两按钮 ----------
        pg.evaluate("() => { state.stack = []; state.calc.unitId = 1999000100; state.calc.charId = 1999000100; push({ page: 'calc', title: '计算' }); }")
        pg.wait_for_timeout(1500)
        cc = pg.evaluate("() => ['cal3','casp','ssp'].map(id => { const e = document.getElementById(id); return e ? e.textContent : null; })")
        print('[⑥ 计算页chips]', cc)
        assert cc[0] and '三星' in cc[0] and cc[1] and 'SP强化上限' in cc[1], cc
        pg.evaluate("() => { state.stack = []; setTab('rank'); }"); pg.wait_for_timeout(2500)
        rc = pg.evaluate("() => ['rs3','rspu','rsspu'].map(id => { const e = document.getElementById(id); return e ? e.textContent : null; })")
        print('[⑥ 排行页chips]', rc)
        assert rc[0] and '三星' in rc[0] and rc[1] and 'SP强化上限' in rc[1], rc
        pg.click('#rs3'); pg.wait_for_timeout(2500)                  # 三星关 → 重算不报错
        pg.evaluate("() => { state.stack = []; setTab('team'); }"); pg.wait_for_timeout(2500)
        tc = pg.evaluate("() => ['ts3','tspu','tsspu'].map(id => { const e = document.getElementById(id); return e ? e.textContent : null; })")
        print('[⑥ 组队页chips]', tc)
        assert tc[0] and '三星' in tc[0] and tc[1] and 'SP强化上限' in tc[1], tc

        # ---------- ⑤ 恢复内置数据按钮状态(有补丁保存后重进更新页) ----------
        pg.evaluate("() => { state.stack = []; push({ page: 'update', title: '更新中心' }); }"); pg.wait_for_timeout(300)
        nP = pg.evaluate("() => { const el = document.getElementById('upreset'); return el ? (el.getAttribute('style') || '') : 'NO'; }")
        print('[⑤ 恢复按钮style]', nP)
        assert 'opacity' not in (nP or ''), '有补丁时恢复内置按钮不应置灰'
        b.close()
finally:
    srv.terminate()
    for f in ('v59_ok.webp', 'v59_bad.webp', 'v59_miss.webp'):
        for p in (os.path.join(WEB, 'img', 'thumb', f), os.path.join(PATCH_DIR, 'img', 'thumb', f)):
            if os.path.exists(p): os.remove(p)
    vj = os.path.join(WEB, 'version.json')
    if os.path.exists(vj): os.remove(vj)
    if os.path.exists(os.path.join(PATCH_DIR, PATCH_FILE)): os.remove(os.path.join(PATCH_DIR, PATCH_FILE))
if errors:
    print('页面错误:', errors[:5]); sys.exit(1)
print('=== test_v59 全部通过 ===')
