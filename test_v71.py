# -*- coding: utf-8 -*-
"""v0.71 验证: 全量武器特效显示 + 射程(最小-最大)/MAP 标注
① fxShort 全量覆盖: 绝对命中/敌MP-1/敌攻·机动·命中/POWER减/暴伤/暴击率/先发攻击/使用后可移动/
   额外行动/HP·EN吸收/移动力·射程减/命中固定/对水下/武装效果UP(且…)/效果值增加 — 5216条lv5 fx零遗漏
② 组队摘要: F91双V.S.B.R EX=「绝对命中 · 高HP+20%」/ 怪物黑龙EX=「绝对命中 · 敌MP-1 · 降防35%」(UR≥2种特效)
   武装饰UP行: SSP视图并入数值后不重复(米加粒子炮 on=降防30% / off=降防25%·武装效果UP·降防+5%)
③ 图鉴: 武器行显示全部特效; .wr 射程min-max + MAP 标注; SSP88并入同名效果值(降防25%→30%)
④ 组队/排行: 射程改为 min-max; MAP武器附 ·MAP 标注(排行保留红色MAP标)
⑤ 武器页: 射程1-4·MAP (原「射程 MAP」无数值)
回归: v17/v58/v59/v63/v64/v66/v67/v68/v69/v70
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8971
F91, F91W = 1163000150, 116300015004
HKK, HKKW = 1705000550, 170500055004
CORE, MPW = 1001000500, 100100050090

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

        # ---------- ① fxShort 全量覆盖 ----------
        r = pg.evaluate("""() => {
          const t = (n, d) => fxShort(n, d);
          let bad = 0, tot = 0;
          for (const f of q('SELECT name, desc FROM weapon_fx WHERE level=5')) {
            const raw = String(f.name || f.desc || '').split('\\n')[0].replace(/\\s*LV\\d+\\s*$/, '').trim();
            if (!raw || raw === '/' || raw.length < 2) continue;
            tot++; if (!fxShort(f.name, f.desc)) bad++;
          }
          return { bad, tot,
            hit: t('绝对命中', '绝对命中\\n武装属性损伤减轻无效'),
            mp: t('MP减少', '命中的敌方MP减少1'),
            atk: t('攻击力减少(1回合) LV4', '赋予敌方“攻击力减少25%”(1回合)'),
            pw: t('光束武装POWER下降(1回合) LV4', '赋予敌方“光束武装POWER减少25%”(1回合)'),
            cd: t('爆击损伤提升 LV4', '自身爆击损伤提升25%'),
            pre: t('先发攻击', '先发攻击'),
            mv: t('使用后可移动', '使用后可移动'),
            hp: t('HP吸收 LV4', '依造成损伤的40%恢复自身HP\\n(恢复量上限为自身最大HP的20%)'),
            rg: t('光束武装最大射程降低(1回合)', '赋予敌方“光束武装的最大射程减少1”(1回合)'),
            fxup: t('', '武装效果的效果值UP(且防御力减少5%)'),
            add: t('防御力减少效果值增加', '发起对战的敌方包含“大型机”标签时，\\n防御力减少的武装效果值增加3%'),
            near: t('', '距离敌方越近，武装POWER越为提升(最高提升5%)'),
            water: t('', '对水下敌人的伤害减半') };
        }""")
        print('[① 全量覆盖]', r)
        assert r['bad'] == 0, r                                     # lv5 fx 零遗漏
        assert r['hit'] == '绝对命中' and r['mp'] == '敌MP-1', r
        assert r['atk'] == '敌攻-25%' and r['pw'] == '敌·光束POWER-25%', r
        assert r['cd'] == '暴伤+25%' and r['pre'] == '先发攻击' and r['mv'] == '使用后可移动', r
        assert r['hp'] == 'HP吸收40%' and r['rg'] == '敌·光束射程-1', r
        assert r['fxup'] == '武装效果UP·降防+5%', r
        assert r['add'] == '对大型机·降防效果+3%', r
        assert r['near'] == '近距离+5%' and r['water'] == '对水下伤害减半', r
        print('[① fxShort 简化词(全模式)] 通过')

        # ---------- ② 组队摘要: UR≥2种特效 / SSP并入 ----------
        r = pg.evaluate(f"""() => {{
          const comp = (wid, ch, uid, ssp) => weaponFxCompactOf(q1('SELECT * FROM weapons WHERE id=?',[wid]), ch, q1('SELECT * FROM units WHERE id=?',[uid]), ssp, true, {{condAll:false, vigor:'supercharged'}});
          return {{
            f91: comp({F91W}, null, {F91}, false),
            hkk: comp({HKKW}, null, {HKK}, false),
            mp_on: comp({MPW}, null, {CORE}, true),
            mp_off: comp({MPW}, null, {CORE}, false)
          }};
        }}""")
        print('[② 摘要]', r)
        assert r['f91'] == '绝对命中 · 高HP+20%', r                # UR 两种特效
        assert r['hkk'] == '绝对命中 · 敌MP-1 · 降防35%', r        # UR 三种特效
        assert r['mp_on'] == '降防30%', r                          # 88并入数值后UP行不重复
        assert r['mp_off'] == '降防25% · 武装效果UP·降防+5%', r
        print('[② 组队摘要(全量特效/SSP并入)] 通过')

        # ---------- ③ 图鉴: 全量特效 + 射程/MAP + SSP合并 ----------
        pg.evaluate(f"() => {{ state.unit = {{star:0, star3:true, sp:true, ssp:false}}; state.stack=[]; push({{page:'unit', title:'x', id:{F91}}}); }}")
        pg.wait_for_timeout(700)
        rows = pg.evaluate("() => [...document.querySelectorAll('.wrow')].map(e => e.textContent.replace(/\\s+/g,' '))")
        print('[③ F91 武器行]', [x[:60] for x in rows])
        assert any('双V.S.B.R. EX1-4' in x and '绝对命中' in x and '高HP+20%' in x for x in rows), rows
        assert any('双V.S.B.R.1-6 MAP' in x for x in rows), rows          # MAP武器: 射程+MAP标注
        pg.evaluate(f"() => {{ state.unit.ssp = true; state.stack=[]; push({{page:'unit', title:'x', id:{CORE}}}); }}")
        pg.wait_for_timeout(700)
        rows = pg.evaluate("() => [...document.querySelectorAll('.wrow')].map(e => e.textContent.replace(/\\s+/g,' '))")
        print('[③ 核心战机 SSP行]', [x[:70] for x in rows])
        assert any('米加粒子炮 SSP' in x and '降防30%' in x and '武装效果UP·降防+5%' in x for x in rows), rows
        assert not any('防御力减少(1回合) LV5' in x for x in rows), rows   # 金标同理词去重(不再显示原始名)
        assert any('米加粒子炮2-5' in x and '光束-10%' in x for x in rows), rows  # SSP追加效果(82 → 光束-10%)
        print('[③ 图鉴(全量特效/射程MAP/SSP合并)] 通过')

        # ---------- ④ 组队支援型: 增伤/降防并集(附该武器射程min-max·MAP) / 其他区域不再显示特效 ----------
        r = pg.evaluate("""() => {
          const f = { sp: 1, ssp: 1 };
          const fxo = (uid, ch, ssp) => unitDamageFxOf(uid, ch, f, ssp, true, { condAll: true, vigor: 'high', sspU: true });
          return { age2: fxo(1400000550, 1400002000, false), zhang: fxo(1219000650, 1219000501, false), hkk: fxo(1705000550, null, false) };
        }""")
        print('[④ 支援型并集]', r)
        assert r['age2'] == '光束-40% 1-5 · 降防25% 2-5', r            # age-2: 光束-40% 1-5 + 降防25% 2-5(另一武器)
        assert r['zhang'].startswith('特殊-40% 1-4 · 物理-25% 3-5') and '物理-25% 3-5·MAP' in r['zhang'], r
        assert r['hkk'] == '降防35% 1-5 · 物理-25% 2-4', r
        pg.evaluate("() => { state.stack = []; setTab('team'); }")
        pg.wait_for_timeout(4000)
        txt = pg.evaluate("() => document.querySelector('#tarea').textContent.replace(/\\s+/g,' ')")
        for kw in ['光束-40% 1-5', '降防25% 2-5', '特殊-40% 1-4', '降防35% 1-5']:
            assert kw in txt, f'组队页缺 {kw}'
        for kw in ['绝对命中', '高HP+20%', '敌MP-1']:                     # 仅支援型区显示; 非增伤类特效不显示
            assert kw not in txt, f'组队页不应出现 {kw}'
        print('[④ 支援型并集(射程·MAP标注/其他区无特效)] 通过')
        pg.evaluate("() => { state.stack=[]; setTab('rank'); }")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => { state.rankCfg.range = 'map'; render(); }")
        pg.wait_for_timeout(2500)
        rr = pg.evaluate("() => [...document.querySelectorAll('#rlist .rtagrow')].slice(0, 3).map(e => e.textContent.replace(/\\s+/g,' '))")
        print('[④ 排行 MAP行]', rr)
        assert rr and all(('射程1-4' in x or '射程' in x) and 'MAP' in x for x in rr), rr
        print('[④ 组队/排行(射程min-max/MAP)] 通过')

        # ---------- ⑤ 武器页 MAP 射程 ----------
        pg.evaluate("() => push({page:'weapon', title:'x', id:185000485005})")
        pg.wait_for_timeout(700)
        t = pg.evaluate("() => document.querySelector('.model').textContent.replace(/\\s+/g,' ')")
        assert '射程1-4·MAP' in t and 'MAP武装' in t, t
        print('[⑤ 武器页(射程·MAP)] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v71 全部通过 ===')
