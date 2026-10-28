# -*- coding: utf-8 -*-
"""v142 验证: 驾驶员能力不再重复显示同一条被动
问题: 利保逊(1370003501) 的 4 条能力在数据里带完全相同的 trait 列表(网站重复),
      详情页把「特殊武装的最大射程提升1」等效果重复显示 4 次; 且 86 型长文本已含射程+1, 又与 72 型重复
修复: 详情渲染时 ①跨能力按 (type,value,desc,condition) 去重 ②同能力内 desc 被更长 desc 包含的短条目不再显示
① 详情页「特殊武装的最大射程提升1」只出现 1 次
② 4 条能力各显示自己的效果（源数据本就按能力分组; 仅去掉 72 型射程短行）
③ 特性「支援攻击+3次」（能力1 +1、EX 无条件 +1、EX 条件 +1）
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9119

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1200}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)
        pg.evaluate("() => { state.stack=[]; push({page:'char',title:'x',id:1370003501}); render(); }")
        pg.wait_for_timeout(900)
        r = pg.evaluate("""() => { const t = document.getElementById('view').innerText;
          const cnt = (t.match(/特殊武装的最大射程提升1/g) || []).length;
          const blocks = (t.match(/✦/g) || []).length;
          return { cnt, blocks, skills: (t.match(/⚡/g) || []).length }; }""")
        print('[① 重复次数/能力块/技能]', r)
        assert r['cnt'] == 1, r
        assert r['blocks'] == 4, r
        assert r['skills'] == 3, r
        assert '+3次' in pg.evaluate("() => document.getElementById('view').innerText"), '支援攻击次数'
        assert not errors, errors
        print('=== test_v142 全部通过 ===')
        b.close()
finally:
    srv.terminate()
