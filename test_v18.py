# -*- coding: utf-8 -*-
"""v0.18 验证: EX能力具体标签生效 + 特性页"先发攻击"分组"""
import subprocess, time, json
from playwright.sync_api import sync_playwright

PORT = 8863
srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd='/root/workspace/ggen_app/web',
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 400, 'height': 860})
        pg.set_default_timeout(240000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append('console.' + m.type + ': ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        print('[boot] ok')

        # ---------- 1. EX能力标签解析（数据层） ----------
        chk = pg.evaluate("""() => {
          const g = id => (q1('SELECT traits_json t FROM char_abilities WHERE ability_id=?', [id]) || {}).t;
          const descs = id => JSON.parse(g(id) || '[]').map(t => ((t||{}).trait||{}).desc || '');
          const hugo = descs(2030001);            // 胡索 EX角色能力
          const iori = descs(2025701);            // 伊欧 EX角色能力(阿特拉斯)
          const doro = descs(2027901);            // 桃乐丝 (部队条件)
          return {hugo, iori, doro};
        }""")
        print('[胡索 EX]', json.dumps(chk['hugo'], ensure_ascii=False)[:180])
        print('[伊欧 EX]', json.dumps(chk['iori'], ensure_ascii=False)[:220])
        print('[桃乐丝]', json.dumps(chk['doro'], ensure_ascii=False)[:160])
        assert any('神圣军事同盟' in d for d in chk['hugo']), '胡索EX应显示神圣军事同盟'
        assert any('水中用' in d and '地面用' in d for d in chk['iori']), '伊欧EX应显示水中用/地面用'
        assert any('【W系列】' in d for d in chk['doro']), '桃乐丝应显示【W系列】'
        assert not any('上述' in d for d in chk['hugo'] + chk['doro']), '不应残留"上述"占位'

        # 驾驶员页显示
        owner = pg.evaluate("() => q1('SELECT char_id FROM char_abilities WHERE ability_id=2030001').char_id")
        pg.evaluate(f"() => push({{page:'char', title:'x', id:{owner}}})")
        pg.wait_for_timeout(600)
        ch = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        print('[胡索页片段]', ch[ch.find('EX角色能力'):ch.find('EX角色能力') + 120] if 'EX角色能力' in ch else ch[:120])
        assert '神圣军事同盟' in ch, '胡索页面应显示具体标签'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/26a_char_tags.png')

        # ---------- 2. 特性页 先发攻击 ----------
        pg.click('[data-tab="feat"]'); pg.wait_for_selector('.lrow')
        chips = pg.eval_on_selector_all('.chip[data-k]', "els => els.map(e => e.textContent.trim())")
        assert '先发攻击' in chips, '特性页缺少先发攻击分组'
        pg.click("[data-k='preemptive']"); pg.wait_for_timeout(600)
        ft = pg.evaluate("() => document.getElementById('farea').textContent.replace(/\\s+/g,' ')")
        print('[先发攻击]', ft[:160])
        assert '共 49 条' in ft, '先发攻击应为49条'
        assert '（先发攻击）' in ft, '标签应含武器名'
        n = pg.evaluate("() => q('SELECT * FROM features WHERE feature=?', ['preemptive']).length")
        assert n == 49, f'preemptive features={n}'
        pg.screenshot(path='/root/workspace/ggen_app/shots_app/26b_preemptive.png')

        # 点击一条 -> 进入机体页
        pg.click('#farea .lrow'); pg.wait_for_timeout(600)
        v = pg.evaluate("() => document.getElementById('view').textContent.slice(0, 120)")
        print('[click row]', v.replace('\n', ' ')[:100])

        # ---------- 3. 武器页显示先发攻击（艾比安光束剑） ----------
        pg.evaluate("() => push({page:'weapon', title:'x', id:121100121090})")
        pg.wait_for_timeout(600)
        w = pg.evaluate("() => document.getElementById('view').textContent.replace(/\\s+/g,' ')")
        has = '先发攻击' in w
        print('[艾比安光束剑 先发攻击]', has)
        b.close()
finally:
    srv.terminate()
print('[js errors]', errors if errors else 'none')
