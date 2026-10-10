# -*- coding: utf-8 -*-
"""v0.66 验证: 组队防御侧口径修复 + 系列全集匹配
① 支援防御门控: defenderSkills 的「支援防御时」技能(阿姆罗 防御力提升20×2) 仅在支援防御开时计入
   (与参考站源码一致: battleAction = 支援防御开关 ? 'SupportDefense' : undefined, 未给则条件不成立)
   组队: ★3 支援防御关 → 防御 10,040 不加技能 / 开 → 14,056+姿态; 命运型脉冲+真飞鸟伤害 155,084 ↔ 77,011
② 系列全集匹配: metaOf().seriesList = series_set 全集 (参考站 unit_series 判定 series_set 任一项):
   渣古II(THE ORIGIN) 同时匹配「机动战士高达」(父)与「THE ORIGIN」; 双头龙EW 同时匹配 W(TV)与无尽的华尔兹;
   显示主系列(series 字段)不变
③ 防御卡显示: 防御值无变化时不显示箭头
回归: test_v58 / test_v59 / test_v63 / test_v64 全过
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8974
ZAKU = 1003000200          # 夏亚专用渣古II (THE ORIGIN版): set=[10,30]
DRAGON = 1219000650        # 双头龙高达(EW版)(EX): set=[2100,2190]
IMPL, SHIN = 1333000100, 1330000103   # 命运型脉冲高达 + 真·飞鸟

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

        # ---------- ① 支援防御门控 ----------
        r = pg.evaluate("""() => ({
          off: defenderSkills(1001000150, 1001000100, false),
          on: defenderSkills(1001000150, 1001000100, true)
        })""")
        print('[① defenderSkills] 关:', r['off'], '| 开:', r['on'])
        assert r['off']['defPct'] == 0 and r['off']['cdefPct'] == 5 and r['off']['redPct'] == 15, r['off']
        assert r['on']['defPct'] == 40, r['on']          # 仅支援防御开时 阿姆罗两条(支援防御时)+20 计入
        def team(star, sdef):
            pg.evaluate(f"""() => {{
              state.team = Object.assign(state.team, {{dunit:1001000150, dchar:1001000100, vigor:'supercharged', skills:true, ca:true, mp:true, rar:4, star:{star}, sdef:{'true' if sdef else 'false'}, guard:false}});
              state.stack = []; setTab('team');
            }}""")
            pg.wait_for_timeout(2500)
            return pg.evaluate("""() => {
              const el = [...document.querySelectorAll('#tarea .trow')].find(e => e.textContent.includes('命运型脉冲高达'));
              const txt = document.querySelector('#tarea').textContent.replace(/\\s+/g,' ');
              return {dmg: el ? el.querySelector('.val').textContent : null,
                      noArrow: !/防御 10,040→10,040/.test(txt)};
            }""")
        t3off = team(3, False)
        print('[① 组队 支援防御关]', t3off)
        assert t3off['dmg'] == '155,084', t3off      # 10,040(★3基础) 无技能+40%
        assert t3off['noArrow'], '防御值未变化时不应显示箭头'
        t3on = team(3, True)
        print('[① 组队 支援防御开]', t3on)
        assert t3on['dmg'] == '77,011', t3on         # 14,056(+40%) + 支援防御姿态-40%
        print('[① 支援防御门控] 通过')

        # ---------- ② 系列全集匹配 ----------
        sr = pg.evaluate(f"""() => {{
          const cond = (tags, series) => ({{tensionReq:0, reqTags:tags, reqSeries:series, reqUnits:[]}});
          const m1 = metaOf({ZAKU}), m2 = metaOf({DRAGON});
          return {{
            list1: [...m1.seriesList], prim1: m1.series, list2: [...m2.seriesList], prim2: m2.series,
            g10: condOk(cond([], ['机动战士高达']), m1, {{condAll:false}}),
            g30: condOk(cond([], ['机动战士高达 THE ORIGIN']), m1, {{condAll:false}}),
            wtv: condOk(cond([], ['新机动战记高达W']), m2, {{condAll:false}}),
            wew: condOk(cond([], ['新机动战记高达W 无尽的华尔兹']), m2, {{condAll:false}})
          }};
        }}""")
        print('[② 系列全集]', sr)
        assert sr['prim1'] == '机动战士高达 THE ORIGIN' and sr['prim2'] == '新机动战记高达W 无尽的华尔兹', sr
        assert '机动战士高达' in sr['list1'] and sr['g10'] and sr['g30'], sr     # 父系列与主系列都能命中(参考站口径)
        assert '新机动战记高达W' in sr['list2'] and sr['wtv'] and sr['wew'], sr
        print('[② 系列全集匹配] 通过(父子系列均可命中; 主系列显示不变)')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v66 全部通过 ===')
