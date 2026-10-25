# -*- coding: utf-8 -*-
"""v130 验证: 组队「自定义增强」多选标签按筛选器口径(全部命中/任一命中)匹配
问题: 用户选「试作机 + 重击」(默认 全部命中) 增94%, 高达试做3号机(EX) 只带「试作机」却也吃到加成
根因: tbuffMatch 恒用 OR(some), 忽略 filt('tbuff').mode
① 全部命中: [试作机,重击] 对 GP03(只有试作机) = false
② 全部命中: [试作机] = true; [重击] = false
③ 任一命中: [试作机,重击] = true (保留旧行为)
④ 队伍增强(无 mode 的条目)仍按 OR 匹配(向后兼容)
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9090

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 900}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        r = pg.evaluate("""() => {
          const m = metaOf(1060000550);            // 高达试做3号机 (EX)：带 试作机，不带 重击
          const mk = (tags, mode) => ({ tags, mode });
          return {
            name: (q1('SELECT name FROM units WHERE id=?',[1060000550])||{}).name,
            tags: [...m.tags],
            and_both: tbuffMatch(mk(['试作机','重击'],'and'), m),
            and_one:  tbuffMatch(mk(['试作机'],'and'), m),
            and_miss: tbuffMatch(mk(['重击'],'and'), m),
            or_both:  tbuffMatch(mk(['试作机','重击'],'or'), m),
            legacy:   tbuffMatch({ tags: ['试作机','重击'] }, m)   // 无 mode → OR
          }; }""")
        print('[① 匹配口径]', json.dumps(r, ensure_ascii=False)[:320])
        assert '试作机' in r['tags'] and '重击' not in r['tags'], r['tags']
        assert r['and_both'] is False, ('全部命中时不应命中只有试作机的机体', r)
        assert r['and_one'] is True, r
        assert r['and_miss'] is False, r
        assert r['or_both'] is True, r
        assert r['legacy'] is True, r

        # ⑤ 组队页真实路径: 自定义增强走 selAll → 防御 eHP 行；GP03 在 and 下数值应与不开一致
        def ehp_of_gp03(mode, on=True, pct=94):
            pg.evaluate("""([mode,on,pct]) => {
              const t = state.team;
              t.cbuff = { tags: ['试作机','重击'], mode, pct };
              t.cbOn = on;
              state.stack=[]; push({page:'team',title:'组队'}); render();
            }""", [mode, on, pct])
            pg.wait_for_timeout(2200)
            return pg.evaluate("""() => { const e=[...document.querySelectorAll('.trow')].find(x=>x.innerText.includes('高达试做3号机') && x.innerText.includes('耐久')); if(!e) return null; const m=e.innerText.match(/eHP[\\s\\u00a0]*([\\d,]+)/); return m? +m[1].replace(/,/g,''):null; }""")
        off = ehp_of_gp03('and', False)
        and_on = ehp_of_gp03('and', True)
        or_on = ehp_of_gp03('or', True)
        print('[⑤ eHP] 不开:', off, '| 全部命中:', and_on, '| 任一命中:', or_on)
        assert off is not None and and_on is not None and or_on is not None, (off, and_on, or_on)
        assert and_on == off, ('全部命中不应给 GP03 加成', and_on, off)
        assert or_on > and_on, ('任一命中应给 GP03 加成', or_on, and_on)

        assert not errors, errors
        print('=== test_v130 全部通过 ===')
        b.close()
finally:
    srv.terminate()
