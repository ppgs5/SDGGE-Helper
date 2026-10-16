# -*- coding: utf-8 -*-
"""v104 验证: 组队页「队伍增强」自定义增强(标签/系列多选 + 全能力增强%)计入全部TOP计算
① 组队页「◈ 队伍增强」按钮存在
② 弹窗内出现「自定义增强」区块(☰标签/系列按钮 + 全能力增强输入框)
③ 标签选择器勾选 TOP1 机体持有的标签 → 应用 → 弹窗显示已选
④ 输入全能力增强 50% → 应用 → 重算: 原TOP1 伤害上升 且 buffHit 生效
⑤ 再次打开弹窗: 已选标签与 50% 保留显示
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 9012

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=WEB,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 420, 'height': 900})
        pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')
        pg.wait_for_timeout(900)

        # 组队页(首次全量计算较慢)
        pg.evaluate("() => { state.stack = []; push({ page: 'team', title: '组队' }); }")
        pg.wait_for_timeout(1500)
        assert pg.evaluate("() => !!document.getElementById('tbuff')"), '组队页缺队伍增强按钮'
        base = pg.evaluate("""() => { const G = state.teamCache.G; const r = G.main[0];
          const tag = q('SELECT t.id, t.name FROM unit_tags ut JOIN tags t ON t.id=ut.tag_id WHERE ut.unit_id=? LIMIT 1', [r.unitId])[0];
          return { dmg: r.dmg, uid: r.unitId, tagId: tag.id, tagName: tag.name, n: G.main.length }; }""")
        print('[① 组队基准]', base['dmg'], '标签:', base['tagName'], '#' + str(base['tagId']))
        assert base['dmg'] > 0 and base['tagId'], base

        # ② 打开增强弹窗 → 自定义区块
        pg.evaluate("() => document.getElementById('tbuff').click()")
        pg.wait_for_timeout(600)
        t = pg.evaluate("() => document.body.innerText")
        assert '自定义增强' in t and '全能力增强' in t, t[:80]
        assert pg.evaluate("() => !!document.getElementById('cbtag') && !!document.getElementById('cbpct') && !!document.getElementById('cbck')")
        print('[② 自定义增强区块(标签/系列按钮+全能力增强输入框) 通过]')

        # ③ 进标签选择器: 勾选 TOP1 的标签 → 应用 → 回弹窗
        pg.evaluate("() => document.getElementById('cbtag').click()")
        pg.wait_for_timeout(600)
        assert pg.evaluate("() => !!document.getElementById('stlist')"), '标签选择器未打开'
        pg.evaluate("""(tid) => { const el = document.querySelector('#stlist [data-id="' + tid + '"]');
          if (!el) throw new Error('标签行不存在'); el.click(); }""", base['tagId'])
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.getElementById('sapply').click()")
        pg.wait_for_timeout(800)
        prev = pg.evaluate("() => (document.getElementById('cbprev')||{}).textContent || ''")
        print('[③ 选择器应用后]', prev[:40])
        assert base['tagName'] in prev, prev

        # ④ 勾选 → 输入 50% → 应用 → 重算
        pg.evaluate("() => document.getElementById('cbck').click()")
        pg.wait_for_timeout(300)
        pg.evaluate("""() => { const el = document.getElementById('cbpct'); el.value = '50'; el.dispatchEvent(new Event('input')); }""")
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.getElementById('tapply').click()")
        pg.wait_for_timeout(2500)
        after = pg.evaluate("""(uid) => { const G = state.teamCache.G; const r = G.main.find(x => x.unitId === uid);
          return { dmg: r ? r.dmg : null, buffHit: r ? !!r.buffHit : null, label: (document.getElementById('tbuff')||{}).textContent || '' }; }""", base['uid'])
        print('[④ 应用50%后]', after['dmg'], 'buffHit:', after['buffHit'], '| 按钮:', after['label'][:34])
        assert after['dmg'] and after['dmg'] > base['dmg'], (base['dmg'], after['dmg'])
        assert after['buffHit'] is True, 'buffHit 未生效'
        assert '自定义' in after['label'] and '50%' in after['label'], after['label']
        print('[④ 全能力增强50% → TOP伤害上升 + buffHit + 按钮标注 通过]')

        # ⑤ 重开弹窗: 已选保留
        pg.evaluate("() => document.getElementById('tbuff').click()")
        pg.wait_for_timeout(600)
        keep = pg.evaluate("""() => ({ prev: (document.getElementById('cbprev')||{}).textContent || '',
          pct: (document.getElementById('cbpct')||{}).value || '', ck: (document.getElementById('cbck')||{}).className || '' })""")
        print('[⑤ 重开]', keep['prev'][:34], '| pct:', keep['pct'])
        assert base['tagName'] in keep['prev'] and keep['pct'] == '50' and 'on' in keep['ck'], keep
        print('[⑤ 已选标签/50% 保留 通过]')

        # ⑥ 自定义增强44% ⇔ 攻方全能力44% 同口径(伤害应一致)
        pg.evaluate("() => document.getElementById('sx').click()")
        pg.wait_for_timeout(400)
        pg.evaluate("""(tn) => { state.team.atkup = 0; state.team.cbuff = { tags: [tn], pct: 44 }; state.team.cbOn = true; render(); }""", base['tagName'])
        pg.wait_for_timeout(2500)
        c44 = pg.evaluate("""(uid) => { const G = state.teamCache.G; const r = G.main.find(x => x.unitId === uid);
          return r ? r.dmg : null; }""", base['uid'])
        pg.evaluate("() => { state.team.atkup = 44; state.team.cbuff = { tags: [], pct: 0 }; state.team.cbOn = false; render(); }")
        pg.wait_for_timeout(2500)
        a44 = pg.evaluate("""(uid) => { const G = state.teamCache.G; const r = G.main.find(x => x.unitId === uid);
          return r ? r.dmg : null; }""", base['uid'])
        print('[⑥ 自定义增强44]', c44, 'vs 攻方全能力44:', a44)
        assert c44 and a44 and abs(c44 - a44) <= 1, (c44, a44)
        print('[⑥ 自定义增强44% ⇔ 攻方全能力44% 同口径(伤害一致) 通过]')

        # ⑦ 未勾选多选框 → 不生效(伤害回到基准)
        pg.evaluate("""(tn) => { state.team.atkup = 0; state.team.cbuff = { tags: [tn], pct: 44 }; state.team.cbOn = false; render(); }""", base['tagName'])
        pg.wait_for_timeout(2500)
        off = pg.evaluate("""(uid) => { const G = state.teamCache.G; const r = G.main.find(x => x.unitId === uid);
          return r ? r.dmg : null; }""", base['uid'])
        print('[⑦ 未勾选]', off, 'vs 基准:', base['dmg'])
        assert off == base['dmg'], (off, base['dmg'])
        print('[⑦ 自定义增强未勾选不生效(回到基准伤害) 通过]')

        # ⑧ 特性页 move7 标签改名「支援防御范围7」
        pg.evaluate("() => { state.stack = []; push({ page: 'feat', title: '特性' }); }")
        pg.wait_for_timeout(1200)
        ft = pg.evaluate("() => document.body.innerText")
        assert '支援防御范围7' in ft and '7移动' not in ft, ft[:80]
        print('[⑧ 特性页「7移动」→「支援防御范围7」 通过]')

        # ⑨ 更新中心: 更新说明=最新版文案 + 「更新日志」按钮(0.103起每版一项)
        pg.evaluate("() => { state.stack = []; push({ page: 'update', title: '更新中心' }); }")
        pg.wait_for_timeout(1000)
        ut = pg.evaluate("() => document.body.innerText")
        import re as _re
        assert 'APP 更新说明' in ut and _re.search(r'v0\.\d+', ut), ut[:0]   # 说明卡显示最新版(版本号随轮次更新)
        assert pg.evaluate("() => !!document.getElementById('updlog')"), '缺更新日志按钮'
        pg.evaluate("() => document.getElementById('updlog').click()")
        pg.wait_for_timeout(500)
        lt = pg.evaluate("() => document.getElementById('sheetPanel').innerText")
        assert '更新日志' in lt and 'v0.104' in lt and 'v0.103' in lt, lt[:90]
        assert lt.count('v0.1') == pg.evaluate("() => APP_CHANGELOG.length"), lt[:90]   # 每个版本一项(条数=changelog长度)
        pg.evaluate("() => document.getElementById('sx').click()")
        assert '免责条款' in ut and '与 Bandai Namco' in ut, ut[:0]   # 关于卡免责条款
        shaf = pg.evaluate("() => document.getElementById('apksha').textContent")   # 网页版回退文案
        assert 'Releases 页' in shaf, shaf
        pg.evaluate("""() => { window.Android = Object.assign(window.Android || {}, { apkSha256: () => 'abc123def456' });
          state.stack = []; push({ page: 'update', title: '更新中心' }); }""")
        pg.wait_for_timeout(700)
        shav = pg.evaluate("() => document.getElementById('apksha').textContent")
        assert shav == 'abc123def456', shav
        pg.evaluate("() => { try { delete window.Android; } catch (e) {} }")
        print('[⑨b 版本号下 安装包SHA256(桥) 通过]')
        print('[⑨ 更新中心: 更新说明(最新版)+更新日志按钮(v0.103/v0.104各一项)+关于免责条款 通过]')

        # ⑩ 特性页「支援防御范围7」: 机体文字下方显示地形适性
        pg.evaluate("() => { state.featKind = 'move7'; state.stack = []; push({ page: 'feat', title: '特性' }); }")
        pg.wait_for_timeout(1500)
        fa = pg.evaluate("() => { const el = document.getElementById('farea'); return el ? el.innerText : ''; }")
        assert '地形' in fa and ('○' in fa or '△' in fa or '×' in fa), fa[:120]
        print('[⑩ 支援防御范围7 行内显示地形适性(文字下方) 通过]')

        # ⑩b 6移动 同样显示地形适性
        pg.evaluate("() => { state.featKind = 'move6'; state.stack = []; push({ page: 'feat', title: '特性' }); }")
        pg.wait_for_timeout(1200)
        fa2 = pg.evaluate("() => { const el = document.getElementById('farea'); return el ? el.innerText : ''; }")
        assert '地形' in fa2 and ('○' in fa2 or '△' in fa2 or '×' in fa2), fa2[:120]
        print('[⑩b 6移动 行内显示地形适性 通过]')

        # ⑪ 特性「标签/系列」弹窗: 出击场地筛选(水中×不能出击的机体不入列)
        n0 = pg.evaluate("() => document.querySelectorAll('#farea .lrow').length")
        pg.evaluate("() => document.getElementById('ftag').click()")
        pg.wait_for_timeout(600)
        pt = pg.evaluate("() => document.getElementById('sheetPanel').innerText")
        assert '出击场地' in pt and '水中' in pt, pt[:80]
        pg.evaluate("() => document.querySelector('[data-fterr=water]').click()")
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.getElementById('sapply').click()")
        pg.wait_for_timeout(1200)
        n1 = pg.evaluate("() => document.querySelectorAll('#farea .lrow').length")
        bad = pg.evaluate("""() => { let bad = 0; document.querySelectorAll('#farea .lrow').forEach(el => {
          if (el.dataset.t !== 'unit') return;
          const tu = q('SELECT terrain_water w FROM units WHERE id=?', [+el.dataset.id])[0];
          if (tu && tu.w === 1) bad++; }); return bad; }""")
        print('[⑪ 场地筛选] 前:', n0, '后:', n1, '水中×残留:', bad)
        assert pg.evaluate("() => filt('feat').terr") == 'water'
        assert n0 and n1 <= n0 and bad == 0, (n0, n1, bad)
        pg.evaluate("() => { filt('feat').terr = ''; }")
        print('[⑪ 特性弹窗出击场地筛选(×不入列) 通过]')

        # ⑫ 组队: 防御型TOP(输出/eHP) 与 进攻盾TOP 绿色数值下显示迷你地形
        pg.evaluate("() => { state.stack = []; push({ page: 'team', title: '组队' }); }")
        pg.wait_for_timeout(2500)
        m = pg.evaluate("() => { const el = document.getElementById('tarea'); return el ? (el.innerText.match(/宇[○△×—]/g) || []).length : 0; }")
        print('[⑫ 组队地形行]', m, '处')
        assert m >= 10, m
        print('[⑫ 防御型TOP/进攻盾TOP 绿色数值下地形显示 通过]')

        # ⑬ 形态机(【MA】/【分离型态】)地形继承本体(补齐)
        tr = pg.evaluate("""() => ['密达斯【MA】','亚别哥【MA型态】'].map(n => {
            const r = q('SELECT terrain_space s, terrain_water w FROM units WHERE name=? LIMIT 1', [n])[0]; return r || null; })
            .concat([q("SELECT terrain_space s FROM units WHERE name LIKE '%佐罗%分离%' AND terrain_space IS NOT NULL LIMIT 1")[0] || null])""")
        print('[⑬ 形态机地形]', tr)
        assert all(x and x['s'] is not None for x in tr), tr
        tr2 = pg.evaluate("""() => ['改装型龙飞攻击机 / 改装型龙飞辅助机','G要塞战机','再生大砲','高达F90Ⅱ L型','GN-XⅡ加农型'].map(n => {
            const r = q('SELECT terrain_space s FROM units WHERE name=? LIMIT 1', [n])[0]; return r ? r.s : null; })""")
        print('[⑬b 脱出/变形形态]', tr2)
        assert all(x is not None for x in tr2), tr2
        print('[⑬ MA/分离/脱出/变形形态机体地形已继承本体 通过]')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v104 全部通过 ===')
