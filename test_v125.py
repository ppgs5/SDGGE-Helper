# -*- coding: utf-8 -*-
"""v125 验证: 装置(機構)主数据接入
① DB: unit_mechanisms 1128 行 / 1027 台 / 5 种（防护盾防御 848、变形机构 260、逃生机能 6、逃生机能(超强势) 10、换装 4）
② 图鉴详情出现「装置:」区，含名称与说明（重生高达EX 1370011150 → 防护盾防御 减伤 20%）
③ 逃生机能机体（1060000450）详情含「逃生机能」与说明文本
④ 无装置机体（1001000200 钢加农）详情不出现「装置:」
"""
import os, subprocess, time, sqlite3
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9069
DB = os.path.join(HERE, 'data', 'ggen.db')

# ① 直连 DB 断言
c = sqlite3.connect(DB)
n = c.execute('SELECT COUNT(*) FROM unit_mechanisms').fetchone()[0]
u = c.execute('SELECT COUNT(DISTINCT unit_id) FROM unit_mechanisms').fetchone()[0]
names = dict(c.execute('SELECT name, COUNT(*) FROM unit_mechanisms GROUP BY name').fetchall())
print('[① DB]', n, u, names)
assert n == 1128 and u == 1027, (n, u)
assert names.get('防护盾防御') == 848 and names.get('变形机构') == 260, names
assert names.get('逃生机能') == 6 and names.get('逃生机能(超强势)') == 10 and names.get('换装') == 4, names
assert c.execute('SELECT value FROM unit_mechanisms WHERE unit_id=1370011150').fetchone()[0] == 20

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        def detail(uid):
            pg.evaluate("(id) => { state.stack=[]; push({page:'unit',title:'x',id:id}); render(); }", uid)
            pg.wait_for_timeout(700)
            return pg.evaluate("() => document.getElementById('view').innerText")

        t1 = detail(1370011150)                      # 重生高达EX
        print('[② 重生EX]', '装置:' in t1, '防护盾防御' in t1)
        assert '装置:' in t1 and '防护盾防御' in t1, t1[:600]
        assert '减少损伤' in t1 or '减轻' in t1, t1[:600]

        t2 = detail(1060000450)                      # 逃生机能机体
        print('[③ 逃生机能]', '装置:' in t2, '逃生机能' in t2)
        assert '装置:' in t2 and '逃生机能' in t2, t2[:600]

        t3 = detail(1001000200)                      # 钢加农（无装置）
        print('[④ 无装置]', '装置:' in t3)
        assert '装置:' not in t3, t3[:400]

        assert not errors, errors
        print('=== test_v125 全部通过 ===')
        b.close()
finally:
    srv.terminate()
