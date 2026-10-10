# -*- coding: utf-8 -*-
"""v0.70 验证: 图鉴效果简化词 + 组队武器效果摘要(叠驾驶员88被动/SSP)
① 图鉴简化词: AGE-2EX 机体页武器行 AGE系统EX→「光束-35%」、超绝德斯步枪→「降防25%」(不再显示 效果#14 -35)
② 组队摘要: weaponFxCompactOf —
   基础(如实): AGE-2EX+阿瑟姆 超一击=光束-40%(阿瑟姆t88 -5 镭射范围) / 强势=光束-35%(t88条件超一击+机体门槛)
   张五飞+双头龙 龙爪伸缩臂EX 特殊-40%(超一击) / 35%(强势)
   SSP: 高推进型核心战机 米加粒子炮 降防25%→降防30%(SSP核心88 +5)
③ 组队页渲染: 支援型行含 「光束-40%」「特殊-40%」等; 条件开(默认假设满足)时t88计入
④ 回归: v58/v59/v63/v64/v66/v67/v68/v69 全过
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8954

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
        pg.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.wait_for_selector('#splash', state='hidden')

        # ---------- ① 图鉴简化词 ----------
        pg.evaluate("() => push({page:'unit', title:'x', id:1400000550})")
        pg.wait_for_timeout(800)
        rows = pg.evaluate("() => [...document.querySelectorAll('.wrow')].map(e => e.textContent.replace(/\\s+/g,' '))")
        print('[① AGE-2EX 武器行]', [r[:44] for r in rows])
        assert any('AGE系统 EX' in r and '光束-35%' in r for r in rows), rows
        assert any('超绝德斯步枪' in r and '降防25%' in r and '降防25%降防25%' not in r for r in rows), rows
        assert not any('效果#14' in r for r in rows), rows
        print('[① 图鉴简化词(光束-35%/降防25%)] 通过')

        # ---------- ② 摘要函数(含条件/SSP) ----------
        r = pg.evaluate("""() => {
          const au = q1('SELECT * FROM units WHERE id=1400000550');
          const aw4 = q1('SELECT * FROM weapons WHERE id=140000055004');
          const zu = q1('SELECT * FROM units WHERE id=1219000650');
          const zw4 = q1('SELECT * FROM weapons WHERE id=121900065004');
          const sspRow = q("SELECT weapon_id FROM weapon_ssp_traits WHERE trait_type=88 AND desc LIKE '%防御力减少%' LIMIT 1")[0];
          const sw = q1('SELECT * FROM weapons WHERE id=?', [sspRow.weapon_id]);
          const su = q1('SELECT * FROM units WHERE id=?', [sw.unit_id]);
          return {
            age_on: weaponFxCompactOf(aw4, 1400002000, au, false, true, {condAll:false, vigor:'supercharged'}),
            age_high: weaponFxCompactOf(aw4, 1400002000, au, false, true, {condAll:false, vigor:'high'}),
            def_w: weaponFxCompactOf(q1('SELECT * FROM weapons WHERE id=140000055003'), 1400002000, au, false, true, {condAll:false, vigor:'supercharged'}),
            zhang: weaponFxCompactOf(zw4, 1219000501, zu, true, true, {condAll:false, vigor:'supercharged'}),
            zhang_high: weaponFxCompactOf(zw4, 1219000501, zu, true, true, {condAll:false, vigor:'high'}),
            ssp_on: weaponFxCompactOf(sw, null, su, true, true, {condAll:true, vigor:'supercharged'}),
            ssp_off: weaponFxCompactOf(sw, null, su, false, true, {condAll:true, vigor:'supercharged'})
          };
        }""")
        print('[② 摘要]', r)
        assert r['age_on'] == '绝对命中 · 光束-40%' and r['age_high'] == '绝对命中 · 光束-35%', r   # v0.71: 全量特效(含绝对命中)
        assert r['def_w'] == '降防25%', r
        assert r['zhang'] == '绝对命中 · 特殊-40%' and r['zhang_high'] == '绝对命中 · 特殊-35%', r
        assert '降防30%' in r['ssp_on'] and '降防25%' in r['ssp_off'], r       # SSP核心88 +5
        print('[② 摘要(驾驶员88条件门控/SSP叠加)] 通过')

        # ---------- ③ 组队页渲染 ----------
        pg.evaluate("() => { state.stack = []; setTab('team'); }")
        pg.wait_for_timeout(2800)
        txt = pg.evaluate("() => document.querySelector('#tarea').textContent.replace(/\\s+/g,' ')")
        for kw in ['光束-40%', '特殊-40%', '降防25%']:
            assert kw in txt, f'组队页缺 {kw}'
        print('[③ 组队页效果摘要] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v70 全部通过 ===')
