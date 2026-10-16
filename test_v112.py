# -*- coding: utf-8 -*-
"""v112 验证: charMpSkillOf 同名重复定义修复(曾 base+sp 拼接版覆盖 sp感知版 → 刹那SR 主动MP 4+5=9)
① charMpSkillOf(1370003702 刹那SR, true)=[5](SP版替换base版); (false)=[4]
② mpOf(00高达1370006200, 刹那SR): 被动3 + 技能5 = 8 (曾12) → 气势=超强势(max)
③ 特性页「有MP技能」: 刹那SR 行 主动MP+5 · MP+8, 不含 主动MP+9
④ 防同类回归: web/app.js 顶层 function 无重复定义(=0)
⑤ 对照: 阿斯兰×无限正义EX mpOf=12 不变
"""
import os, re, subprocess, time
from collections import Counter
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'

# ④ 静态扫描(先于浏览器)
src = open(os.path.join(HERE, 'web/app.js'), encoding='utf-8').read()
names = re.findall(r'^function\s+(\w+)\s*\(', src, re.M)
dup = {k: v for k, v in Counter(names).items() if v > 1}
print('[④ 顶层函数重复定义]', dup)
assert not dup, dup

PORT = 9020
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        r1 = pg.evaluate("""() => ({
          sp: charMpSkillOf(1370003702, true).map(x => x.v),
          base: charMpSkillOf(1370003702, false).map(x => x.v),
          ab: charMpAbilOf(1370003702, true).map(x => x.v) })""")
        print('[① 刹那SR MP技能]', r1)
        assert r1['sp'] == [5] and r1['base'] == [4] and r1['ab'] == [3], r1
        print('[① SP版替换base版(主动=5, 非4+5=9) 通过]')

        r2 = pg.evaluate("""() => ({
          pass: mpOf(1370006200, 1370003702, false, true, true, false),
          all: mpOf(1370006200, 1370003702, true, true, true, false),
          vigor: mpToVigor(mpOf(1370006200, 1370003702, true, true, true, false)),
          ast: mpOf(1330002850, 1330001804, true, true, true, false) })""")
        print('[② 刹那SR×00高达 MP]', r2)
        assert r2['pass'] == 3 and r2['all'] == 8 and r2['vigor'] == 'max', r2
        assert r2['ast'] == 12, r2
        print('[② 被动3+技能5=8→超强势; ⑤ 阿斯兰12不变 通过]')

        pg.evaluate("() => { state.stack = []; push({ page: 'feat', title: '特性' }); render(); }")
        pg.wait_for_timeout(1000)
        pg.evaluate("""() => { const c = document.querySelector('[data-k="mp_skill"], [data-k="mp"]'); if (c) c.click(); }""")
        pg.wait_for_timeout(1500)
        t = pg.evaluate("""() => { const rows = [...document.querySelectorAll('#farea .lrow')];
          const el = rows.find(e => e.innerText.includes('刹那·F·清英') && e.innerText.includes('SR'));
          return el ? el.innerText.replace(/\\n/g, ' | ') : null; }""")
        print('[③ 特性页 刹那SR]', t)
        assert t and '主动MP+5' in t and 'MP+8' in t and '主动MP+9' not in t, t
        print('[③ 特性页 主动MP+5 · MP+8 通过]')

        assert not errors, errors
        print('=== test_v112 全部通过 ===')
        b.close()
finally:
    srv.terminate()
