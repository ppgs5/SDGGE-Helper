# -*- coding: utf-8 -*-
"""v148 验证: 特性新增「首动闪避」分类
① 特性页出现「首动闪避」分类，列表 91 位（按首动技能优先度模拟；伊藤·剑 因先放攻击爆裂被排除）
② 行内显示技能名（摇摆闪避 / 命中率、闪避率提升）
③ 点击行进入机师详情
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9136

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1400}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)
        pg.evaluate("() => { state.stack=[]; push({page:'feat',title:'特性',v:'x'}); state.featKind='first_evade'; pageFeat(document.getElementById('view')); }")
        pg.wait_for_timeout(1600)
        r = pg.evaluate("""() => { const t = document.getElementById('farea').innerText;
          const rows = [...document.querySelectorAll('#farea .lrow')];
          const kinds = [...document.querySelectorAll('#view [data-k]')].map(e=>e.innerText);
          return { head: t.split('\\n')[0], n: rows.length, kinds,
                   hasSway: t.includes('摇摆闪避'), hasHit: t.includes('命中率、闪避率提升'),
                   sample: rows.slice(0,2).map(e=>e.innerText.replace(/\\n/g,' | ')) }; }""")
        print('[① 分类]', r['head'], '| 行数', r['n'], '| 分类按钮含首动闪避:', '首动闪避' in r['kinds'])
        assert '首动闪避' in r['kinds'], r['kinds']
        assert r['n'] == 91, r['n']
        assert '伊藤·剑' not in json.dumps(r['sample'], ensure_ascii=False)
        assert r['hasSway'] and r['hasHit'], r
        print('[② 样例]', json.dumps(r['sample'], ensure_ascii=False)[:200])

        note = pg.evaluate("() => document.getElementById('farea').innerText.includes('本列表按「无被动 MP」口径')")
        print('[② 备注]', note)
        assert note
        exc = pg.evaluate("() => { const t=document.getElementById('farea').innerText; return t.includes('多蒙·卡修') && t.includes('明镜止水') && t.includes('MP+6'); }")
        print('[② 例外说明]', exc)
        assert exc
        tag = pg.evaluate("() => { const rows=[...document.querySelectorAll('#farea .lrow')]; const t=rows.filter(e=>e.innerText.includes('MP+')); return {n:t.length, domon:t.some(e=>e.innerText.includes('多蒙'))}; }")
        print('[② 有条件MP 标注]', tag)
        assert tag['n'] >= 3 and tag['domon'], tag
        cond = pg.evaluate("() => { const rows=[...document.querySelectorAll('#farea .lrow')]; const d=rows.find(e=>e.innerText.includes('多蒙')); return d ? d.innerText.split(String.fromCharCode(10)).join(' ') : ''; }")
        print('[② 条件显示]', cond[:80])
        assert '明镜止水' in cond and 'MP+6' in cond, cond

        pg.evaluate("() => { document.querySelector('#farea .lrow').click(); }")
        pg.wait_for_timeout(900)
        assert pg.evaluate("() => (state.stack[state.stack.length-1]||{}).page") == 'char'
        print('[③ 点击进入机师详情] ok')

        assert not errors, errors
        print('=== test_v148 全部通过 ===')
        b.close()
finally:
    srv.terminate()
