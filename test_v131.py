# -*- coding: utf-8 -*-
"""v131 验证: 自定义增强按「标签/系列 ID」精确匹配 (名称重名不再误命中)
问题: D高达3号机(EX) 既无「重击」也无「试作机」标签, 却在任一命中模式下吃到 +94%
根因: series 表里存在与标签同名的行(如 id=1010 名称「试作机」), units.series_id=1010 →
      meta.seriesList 含「试作机」, 按名匹配的 tbuffMatch 走 series 分支误命中
修复: cbuff 存 tagIds/seriesIds, 匹配用 ID (meta.tagIds / meta.seriesIds), 名称路径仅作旧数据兼容
① D高达3号机: tagIds=[试作机,重击] 任一/全部 均不命中
② 高达试做3号机(EX): 任一命中, 全部不命中
③ 按系列选 0083(id=600): GP03 命中, D高达不命中
④ 组队 eHP: D高达 开/关增强数值一致
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9095

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1400}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)

        r = pg.evaluate("""() => {
          const D = metaOf(1101000350), G = metaOf(1060000550);   // D高达3号机(EX, 支援型) / 高达试做3号机(EX)
          const or = { tagIds: [1010, 1134], seriesIds: [], mode: 'or' };   // 试作机 / 重击
          const and = { tagIds: [1010, 1134], seriesIds: [], mode: 'and' };
          const sr = { tagIds: [], seriesIds: ['600'], mode: 'or' };        // 系列 0083
          return {
            d_name: (q1('SELECT name FROM units WHERE id=?',[1101000350])||{}).name,
            g_name: (q1('SELECT name FROM units WHERE id=?',[1060000550])||{}).name,
            d_tags: [...D.tags], d_seriesIds: [...D.seriesIds],
            d_or: tbuffMatch(or, D), d_and: tbuffMatch(and, D),
            g_or: tbuffMatch(or, G), g_and: tbuffMatch(and, G),
            g_sr: tbuffMatch(sr, G), d_sr: tbuffMatch(sr, D)
          }; }""")
        print('[① 匹配]', json.dumps({k: r[k] for k in ('d_name','d_or','d_and','g_or','g_and','g_sr','d_sr')}, ensure_ascii=False))
        assert r['d_name'] == 'D高达3号机 (EX)' and r['g_name'] == '高达试做3号机 (EX)', r
        assert r['d_or'] is False and r['d_and'] is False, ('D高达不应命中', r)
        assert r['g_or'] is True and r['g_and'] is False, ('GP03 应仅任一命中', r)
        assert r['g_sr'] is True and r['d_sr'] is False, ('系列匹配', r)

        def dmg(uid, mode, on, pct=94, need=''):
            pg.evaluate("""([mode, on, pct]) => {
              const t = state.team;
              t.cbuff = { tags: ['试作机','重击'], tagIds: [1010, 1134], seriesIds: [], mode, pct };
              t.cbOn = on; state.teamCache = null; state.stack=[]; push({page:'team',title:'组队'}); render();
            }""", [mode, on, pct])
            pg.wait_for_timeout(3500)
            return pg.evaluate("""([uid, need]) => {
              const nm = (q1('SELECT name FROM units WHERE id=?', [uid]) || {}).name || '';
              const e = [...document.querySelectorAll('.trow')].find(x => x.innerText.includes(nm) && (!need || x.innerText.includes(need)));
              if (!e) return null; const v = e.querySelector('.val'); if (!v || !v.childNodes.length) return null;
              const line = v.childNodes[0].nodeValue || ''; let d = '';
              for (const ch of line) if (ch >= '0' && ch <= '9') d += ch;
              return d ? +d : null; }""", [uid, need])

        d_off = dmg(1101000350, 'or', False)
        d_and = dmg(1101000350, 'and', True)
        d_or = dmg(1101000350, 'or', True)
        print('[② D高达 输出] 关:', d_off, '| 全部:', d_and, '| 任一:', d_or)
        assert d_off and d_and == d_off, ('全部命中不应增强 D高达', d_off, d_and)
        assert d_or is None or d_or == d_off, ('任一命中不应增强 D高达', d_off, d_or)   # None=被其他增强机体挤出前10

        g_and = dmg(1060000550, 'and', True, 94, '耐久')
        g_or = dmg(1060000550, 'or', True, 94, '耐久')
        print('[③ GP03 eHP] 全部:', g_and, '| 任一:', g_or)
        assert g_and and g_or and g_or > g_and, (g_and, g_or)

        assert not errors, errors
        print('=== test_v131 全部通过 ===')
        b.close()
finally:
    srv.terminate()
