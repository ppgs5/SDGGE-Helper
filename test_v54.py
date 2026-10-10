# -*- coding: utf-8 -*-
"""v0.54 验证: 增量更新体系
⓪差分引擎(改/增/删/无主键表)与幂等 ①启动时补丁叠加(仅应用比基础库新的, 过期补丁清理) ②更新中心: 检查→增量链校验→下载补丁→保存→重启
③链断裂→完整更新兜底 ④网页版(无桥)仅可检查 ⑤恢复内置数据(清补丁)"""
import hashlib, json, os, shutil, sqlite3, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
sys.path.insert(0, os.path.join(HERE, 'data'))
from publish_update import diff_db

# ---------- ⓪ 差分引擎自检(夹具: 单主键+复合主键+无主键+updated_at忽略) ----------
DDL = ('CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT); '
       'CREATE TABLE units(id INTEGER PRIMARY KEY, name TEXT, updated_at INT); '
       'CREATE TABLE unit_tags(unit_id INT, tag_id INT, PRIMARY KEY(unit_id, tag_id)); '
       'CREATE TABLE misc(a INT, b TEXT);')
for p in ('/tmp/t_old.db', '/tmp/t_new.db', '/tmp/t_apply.db'):
    if os.path.exists(p): os.remove(p)
o = sqlite3.connect('/tmp/t_old.db'); o.executescript(DDL)
o.executescript("INSERT INTO meta VALUES('version','v1'),('built_at','100'); "
                "INSERT INTO units VALUES(1,'A',100),(2,'B',100); "
                "INSERT INTO unit_tags VALUES(1,5); INSERT INTO misc VALUES(1,'x');"); o.commit()
n = sqlite3.connect('/tmp/t_new.db'); n.executescript(DDL)
n.executescript("INSERT INTO meta VALUES('version','v2'),('built_at','200'); "
                "INSERT INTO units VALUES(1,'A',999),(2,'B',100),(3,'C',200); "      # id1 仅 updated_at 变化(应忽略)
                "INSERT INTO unit_tags VALUES(1,5),(3,7); INSERT INTO misc VALUES(1,'x'),(2,'y');"); n.commit()
sql = diff_db('/tmp/t_old.db', '/tmp/t_new.db', 200)
assert 'INSERT OR REPLACE INTO "units" VALUES(3' in sql and 'VALUES(1' not in sql.split('"units"')[1][:200], f'updated_at 变化不应触发重写: {sql[:300]}'
assert 'DELETE FROM "unit_tags"' not in sql and 'unit_tags" VALUES(3,7)' in sql, f'复合主键应逐行差: {sql[:300]}'
assert 'DELETE FROM "misc"' in sql, '无主键表变化应整表重建'
def dump(p):
    c = sqlite3.connect(p); out = {}
    for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        cols = [r[1] for r in c.execute(f'PRAGMA table_info("{t}")') if r[1] != 'updated_at']
        out[t] = sorted(map(str, c.execute(f'SELECT {",".join(cols)} FROM "{t}"').fetchall()))
    return out
shutil.copy('/tmp/t_old.db', '/tmp/t_apply.db')
a = sqlite3.connect('/tmp/t_apply.db'); a.executescript(sql); a.commit()
assert dump('/tmp/t_apply.db') == dump('/tmp/t_new.db'), '⓪补丁应用不一致'
a.executescript(sql); a.commit()
assert dump('/tmp/t_apply.db') == dump('/tmp/t_new.db'), '⓪幂等失败'
print('[⓪ diff引擎] 通过(增/删/改 + 复合主键逐行 + 无主键重建 + updated_at忽略 + 幂等)')

# 基础库 built_at (App 将以此判断补丁新旧)
BASE_AT = int(sqlite3.connect(os.path.join(WEB, 'data', 'ggen.db')).execute("SELECT value FROM meta WHERE key='built_at'").fetchone()[0])
print('[基础库 built_at]', BASE_AT)

PORT = 8998
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
PATCH_DIR = os.path.join(WEB, 'patches')
VJ = os.path.join(WEB, 'version.json')
FAKE_DB = os.path.join(WEB, 'ggen.db')      # 完整更新走 base+'ggen.db'

BOOT_PATCH_FILE = f'p_{BASE_AT + 100}.sql'
BOOT_PATCH_SQL = "BEGIN;\nUPDATE meta SET value='v2099TEST' WHERE key='version';\nCOMMIT;\n"
FLOW_PATCH_FILE = f'p_{BASE_AT + 200}.sql'
FLOW_PATCH_SQL = "BEGIN;\nUPDATE meta SET value='v2099.02' WHERE key='version';\nCOMMIT;\n"

def write_manifest(patches, version='v2099.02', built_at=None):
    with open(FAKE_DB, 'wb') as f:
        f.write(b'FAKE-FULL-DB' + b'x' * 2048)
    m = {'version': version, 'built_at': built_at or (BASE_AT + 200), 'db_sha256': hashlib.sha256(open(FAKE_DB, 'rb').read()).hexdigest(),
         'db_size': os.path.getsize(FAKE_DB), 'db_url': f'http://127.0.0.1:{PORT}/ggen-test.db',
         'patch_url_base': f'http://127.0.0.1:{PORT}/patches/', 'patches': patches}
    json.dump(m, open(VJ, 'w', encoding='utf-8'), ensure_ascii=False)

def patch_entry(fname, frm, to, content):
    return {'built_at': to, 'from_built_at': frm, 'to': 'v2099.02', 'file': fname,
            'size': len(content.encode()), 'sha256': hashlib.sha256(content.encode()).hexdigest(),
            'images': [{'file': IMG_FILE, 'sha256': IMG_SHA, 'size': len(IMG_BYTES)}]}

os.makedirs(os.path.join(PATCH_DIR, 'img', 'thumb'), exist_ok=True)
IMG_FILE = 'thumb/testimg.webp'
IMG_BYTES = b'WEBP-FAKE-IMAGE-' + b'w' * 512
with open(os.path.join(PATCH_DIR, 'img', IMG_FILE), 'wb') as f:
    f.write(IMG_BYTES)
IMG_SHA = hashlib.sha256(IMG_BYTES).hexdigest()
with open(os.path.join(PATCH_DIR, FLOW_PATCH_FILE), 'w', encoding='utf-8') as f:
    f.write(FLOW_PATCH_SQL)

MOCK = """
window.__mock = {custom: true, dl: null, deleted: false, deletedPatches: [], saved: {}, cleared: false,
                 patches: ['p_1.sql', '%(boot)s']};
window.__UPD_AUTO = ['http://127.0.0.1:59999/dead/', 'http://127.0.0.1:%(port)s/'];
window.Android = {
  dbInfo: () => JSON.stringify({custom: window.__mock.custom, size: 999}),
  appInfo: () => JSON.stringify({versionCode: 55, versionName: '0.55'}),
  listPatches: () => JSON.stringify(window.__mock.patches),
  readPatch: n => { if (n === '%(boot)s') return %(bootsql)s; if (n === '%(flow)s') return %(flowsql)s; return 'THIS IS NOT SQL'; },
  deletePatch: n => { window.__mock.deletedPatches.push(n); },
  savePatch: (n, c) => { window.__mock.saved[n] = (c || '').length; return true; },
  saveImage: (n, b64) => { window.__mock.images = window.__mock.images || {}; window.__mock.images[n] = (b64 || '').length; return true; },
  clearPatches: () => { window.__mock.cleared = true; },
  clearImages: () => { window.__mock.clearedImages = true; },
  downloadDb: (url, sha) => { window.__mock.dl = {url: url, sha: sha, state: 'downloading', pct: 0};
    fetch(url).then(r => r.arrayBuffer()).then(buf => { window.__mock.dl.bytes = buf.byteLength; window.__mock.dl.state = 'done'; window.__mock.dl.pct = 100; })
      .catch(e => { window.__mock.dl.state = 'error'; window.__mock.dl.err = String(e); });
    return true; },
  updateState: () => { const d = window.__mock.dl || {state: 'idle', pct: 0, err: ''}; return JSON.stringify({state: d.state, pct: d.pct || 0, err: d.err || ''}); },
  deleteDb: () => { window.__mock.deleted = true; window.__mock.custom = false; },
};
""" % {'boot': BOOT_PATCH_FILE, 'bootsql': json.dumps(BOOT_PATCH_SQL), 'flow': FLOW_PATCH_FILE, 'flowsql': json.dumps(FLOW_PATCH_SQL), 'port': PORT}

try:
    write_manifest([patch_entry(FLOW_PATCH_FILE, BASE_AT, BASE_AT + 200, FLOW_PATCH_SQL)])
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 400, 'height': 860})
        pg.set_default_timeout(240000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append('console.' + m.type + ': ' + m.text)
              if (m.type == 'error' and 'ERR_CONNECTION_REFUSED' not in m.text and 'Failed to load resource' not in m.text) else None)
        pg.on('dialog', lambda d: d.accept())
        pg.add_init_script(MOCK)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')

        # ① 启动补丁叠加: 新补丁生效 + 过期补丁清理
        v = pg.evaluate("() => q1(\"SELECT value FROM meta WHERE key='version'\").value")
        dele = pg.evaluate("() => window.__mock.deletedPatches")
        print('[① 启动叠加] meta.version =', v, '| 已清理过期补丁:', dele)
        assert v == 'v2099TEST', f'启动补丁未生效: {v}'
        assert 'p_1.sql' in dele, f'过期补丁应被清理: {dele}'
        assert BOOT_PATCH_FILE not in dele, '有效补丁不应被误删'

        # ② 增量更新流程
        pg.evaluate("() => push({page:'update', title:'更新中心'})"); pg.wait_for_timeout(600)
        status = pg.evaluate("() => document.querySelector('#view .card').textContent")
        assert '增量补丁已应用' in status, f'应显示补丁状态: {status[:80]}'
        pg.fill('#upbase', f'http://127.0.0.1:{PORT}/')
        pg.click('#upchk')
        pg.wait_for_function("() => document.querySelector('#upmsg').textContent.includes('增量')", timeout=60000)
        m2 = pg.evaluate("() => document.querySelector('#upmsg').textContent.replace(/\\s+/g,' ').slice(0, 70)")
        print('[② 检查更新]', m2)
        assert '增量 1 个补丁' in m2, f'应显示增量补丁: {m2}'
        pg.screenshot(path=os.path.join(HERE, 'shots_app', '60a_update_incr.png'))
        pg.click('#updl')
        pg.wait_for_function(f"() => window.__mock.saved['{FLOW_PATCH_FILE}'] > 0", timeout=60000)
        pg.wait_for_function(f"() => window.__mock.images && window.__mock.images['{IMG_FILE}'] > 0", timeout=60000)
        sv = pg.evaluate("() => window.__mock.saved")
        svimg = pg.evaluate("() => window.__mock.images")
        pg.wait_for_function("() => document.querySelector('#upmsg').textContent.includes('增量更新完成') && document.querySelector('#upmsg').textContent.includes('头像')", timeout=60000)
        print('[② 增量下载+保存]', sv, '| 头像:', svimg)
        assert sv.get(FLOW_PATCH_FILE) == len(FLOW_PATCH_SQL.encode()), f'补丁内容长度不符(应含sha校验): {sv}'
        assert svimg.get(IMG_FILE) and svimg[IMG_FILE] > 0, f'头像应下载保存: {svimg}'
        with pg.expect_navigation(timeout=30000):      # 1.2s 后自动真实重启
            pass
        pg.wait_for_selector('#splash', state='hidden', timeout=180000)
        print('[② 自动重启] 页面已重载完成')

        # ③ 链断裂 → 完整更新兜底
        write_manifest([patch_entry('p_x.sql', BASE_AT + 999, BASE_AT + 200, 'x')])
        pg.evaluate("() => push({page:'update', title:'更新中心'})"); pg.wait_for_timeout(500)
        pg.fill('#upbase', f'http://127.0.0.1:{PORT}/')
        pg.click('#upchk')
        pg.wait_for_function("() => document.querySelector('#upmsg').textContent.includes('完整更新')", timeout=60000)
        pg.click('#upfull')
        pg.wait_for_function("() => window.__mock.dl && window.__mock.dl.state === 'done'", timeout=60000)
        print('[③ 完整更新兜底] url=', pg.evaluate("() => window.__mock.dl.url")[-22:])

        # ⑤ 恢复内置数据(清库+清补丁)
        pg.evaluate("() => push({page:'update', title:'更新中心'})"); pg.wait_for_timeout(500)
        pg.click('#upreset')
        pg.wait_for_function("() => window.__mock.deleted === true && window.__mock.cleared === true && window.__mock.clearedImages === true", timeout=10000)
        print('[⑤ 恢复内置] deleted=', pg.evaluate("() => window.__mock.deleted"), 'cleared=', pg.evaluate("() => window.__mock.cleared"), 'images cleared=', pg.evaluate("() => window.__mock.clearedImages"))
        pg.close()

        # ④ 网页版(无桥)仅可检查; ⑥ 自动线路切换(第一条死线 → 第二条本地成功)
        write_manifest([patch_entry(FLOW_PATCH_FILE, BASE_AT, BASE_AT + 200, FLOW_PATCH_SQL)])
        pg2 = b.new_page(viewport={'width': 400, 'height': 860})
        pg2.set_default_timeout(120000)
        pg2.add_init_script(f"window.__UPD_AUTO = ['http://127.0.0.1:59999/dead/', 'http://127.0.0.1:{PORT}/'];")
        pg2.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg2.wait_for_selector('#splash', state='hidden')
        pg2.evaluate("() => push({page:'update', title:'更新中心'})"); pg2.wait_for_timeout(500)
        pg2.fill('#upbase', '')      # 留空 → 自动线路(第一条不通 → 切第二条)
        pg2.click('#upchk')
        pg2.wait_for_function("() => document.querySelector('#upmsg').textContent.includes('增量')", timeout=60000)
        msg2 = pg2.evaluate("() => document.querySelector('#upmsg').textContent.replace(/\\s+/g,' ')")
        print('[⑥ 自动线路切换]', msg2[:80])
        assert '线路：镜像线路' in msg2, f'应显示切换后的线路: {msg2}'
        # ④ 无桥点击增量更新 → 提示需在App内
        pg2.click('#updl'); pg2.wait_for_timeout(400)
        msg2b = pg2.evaluate("() => document.querySelector('#upmsg').textContent")
        print('[④ 网页版拦截]', msg2b[:36])
        assert '请在 App 内' in msg2b, f'网页版应提示在App内: {msg2b}'
        pg2.close()

        # ⑦ 全部线路失败 → 明确显示「检查更新失败」
        pg3 = b.new_page(viewport={'width': 400, 'height': 860})
        pg3.set_default_timeout(120000)
        pg3.add_init_script("window.__UPD_AUTO = ['http://127.0.0.1:59999/dead/'];")
        pg3.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg3.wait_for_selector('#splash', state='hidden')
        pg3.evaluate("() => push({page:'update', title:'更新中心'})"); pg3.wait_for_timeout(500)
        pg3.fill('#upbase', '')
        pg3.click('#upchk')
        pg3.wait_for_function("() => document.querySelector('#upmsg').textContent.includes('检查更新失败')", timeout=60000)
        msg3 = pg3.evaluate("() => document.querySelector('#upmsg').textContent.replace(/\\s+/g,' ').slice(0, 70)")
        print('[⑦ 全部线路失败]', msg3)
        assert '所有线路均无法连接' in msg3, f'应说明原因: {msg3}'
        pg3.close()
        b.close()
finally:
    srv.terminate()
    for f in (VJ, FAKE_DB):
        try: os.remove(f)
        except OSError: pass
    shutil.rmtree(PATCH_DIR, ignore_errors=True)
print('[js errors]', errors if errors else 'none')
