# -*- coding: utf-8 -*-
"""v0.64 验证: 被动技能全库审计的三类修复 + 次数技能整合 + 条件标签显示
① 系列映射修复(build_db取sort=1主系列): 437台机体系列归位——渣古Ⅱ(THE ORIGIN版)→机动战士高达 THE ORIGIN、
   双头龙(EW版)→无尽的华尔兹; 夏亚(THE ORIGIN版)EX能力(专用机+THE ORIGIN系列)现在能正确匹配
② 状态/场景条件(ctx: HP/EN阈值/距离/单挑)判定: 开·假设满足计入, 关·如实判定不计
   (吉翁号(EX) HP≤25%攻击+25: 开40 / 关15; 西布克EX HP≥75%损伤+15: 开计入/关不计)
③ 敌方驾驶员标签(character_tags)判定: AGE-2(EX) 优势：新人类×X行者 = 全库唯一同持有者互斥对(无驾驶员同持两标签),
   我方判定按敌方驾驶员标签硬门槛; 单位页显示 TAG 新人类/X行者 chips
④ 次数技能(支援攻击/反击+1次 type51/86)整合进计算/组队/排行: 阿瑟姆+AGE-2EX(超一击)=+3次; 张五飞+双头龙=+2次
回归: test_v58 / test_v59 / test_v63 全过
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8995
AGE2, ACSAM = 1400000550, 1400002000      # 高达AGE-2 基本型(EX) / 阿瑟姆·明日野
DRAGON, ZHANG = 1219000650, 1219000501    # 双头龙高达(EW版)(EX) / 张五飞(EW版)
ZAKU, CASAVAL = 1003000200, 1003000100    # 夏亚专用渣古Ⅱ(THE ORIGIN版) / 夏亚·阿兹纳布尔(THE ORIGIN版)
ZION = 1001003050                          # 吉翁号(EX) HP≤25%攻击+25
SEABOOK = 1162000102                       # 西布克·阿诺(EX) HP≥75%损伤+15/射击+15

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

        # ---------- ① 系列映射 ----------
        ser = pg.evaluate(f"""() => ({{
          zaku: metaOf({ZAKU}).series, dragon: metaOf({DRAGON}).series, ez8: metaOf(1013000350).series,
          casavalZaku: charBonus({CASAVAL}, 'supercharged', {{passive:true,cpassive:true,skills:true,condAll:true,unitId:{ZAKU},upassive:true,multiPhase:true,pSpU:true}}, metaOf({ZAKU})).dmg,
          casavalDragon: charBonus({CASAVAL}, 'supercharged', {{passive:true,cpassive:true,skills:true,condAll:true,unitId:{DRAGON},upassive:true,multiPhase:true,pSpU:true}}, metaOf({DRAGON})).dmg,
          exZ: charPsvOf({CASAVAL}, true, false).filter(p => (p.reqSeries||[]).includes('机动战士高达 THE ORIGIN')).map(p => condOk(p, metaOf({ZAKU}), {{condAll:true, vigor:'supercharged'}})),
          exD: charPsvOf({CASAVAL}, true, false).filter(p => (p.reqSeries||[]).includes('机动战士高达 THE ORIGIN')).map(p => condOk(p, metaOf({DRAGON}), {{condAll:true, vigor:'supercharged'}}))
        }})""")
        print('[① 系列]', ser)
        assert ser['zaku'] == '机动战士高达 THE ORIGIN', ser['zaku']
        assert ser['dragon'] == '新机动战记高达W 无尽的华尔兹', ser['dragon']
        assert ser['ez8'] == '机动战士高达 第08MS小队', ser['ez8']
        assert ser['casavalZaku'] - ser['casavalDragon'] == 15, ser            # EX +15 差值=仅THE ORIGIN匹配的EX
        assert ser['exZ'] == [True] and ser['exD'] == [False], ser             # 条目级: 系列条件对THE ORIGIN通过/对EW不通过
        # 系列筛选(图鉴)口径: 现按主系列归位
        fc = pg.evaluate("""() => ({
          n30: q("SELECT COUNT(*) c FROM units WHERE series_id='30'")[0].c,
          n10: q("SELECT COUNT(*) c FROM units WHERE series_id='10'")[0].c,
          charSer: charSeriesMap()['10000000000300010']
        })""")
        print('[① 系列筛选]', fc)
        assert fc['n30'] == 4 and fc['n10'] == 42 and fc['charSer'] == '30', fc    # 原系列10虚高238
        pg.evaluate(f"() => push({{page:'unit', title:'x', id:{ZAKU}}})"); pg.wait_for_selector('.statgrid')
        print('[① 系列映射] 通过(437台归位; 条件匹配恢复; 驾驶员系列映射同步)')

        # ---------- ② ctx 状态条件(HP阈值等) ----------
        ctx = pg.evaluate(f"""() => ({{
          zionOn: unitPassiveAtkPct({ZION}, 'supercharged', true),
          zionOff: unitPassiveAtkPct({ZION}, 'supercharged', false),
          sbOn: charBonus({SEABOOK}, 'supercharged', {{passive:true,cpassive:true,skills:false,condAll:true,unitId:null,upassive:true,multiPhase:true,pSpU:true}}, null),
          sbOff: charBonus({SEABOOK}, 'supercharged', {{passive:true,cpassive:true,skills:false,condAll:false,unitId:null,upassive:true,multiPhase:true,pSpU:true}}, null)
        }})""")
        print('[② HP条件] 吉翁号开/关:', ctx['zionOn'], '/', ctx['zionOff'], '| 西布克 开/关 dmg:', ctx['sbOn']['dmg'], '/', ctx['sbOff']['dmg'])
        assert ctx['zionOn'] == 40 and ctx['zionOff'] == 15, ctx      # HP≤25%的+25 仅假设满足计入
        assert ctx['sbOn']['dmg'] - ctx['sbOff']['dmg'] == 15, ctx    # HP≥75%的损伤+15 同理
        assert ctx['sbOn']['ranged'] - ctx['sbOff']['ranged'] == 15, ctx
        print('[② ctx 状态条件] 通过(开=假设满足计入 / 关=如实不计)')

        # ---------- ③ 敌方驾驶员标签 + 显示 ----------
        ct = pg.evaluate(f"""() => {{
          const mk = cts => ({{tags:new Set(), series:'', ctags: cts === null ? null : new Set(cts)}});
          return {{
            noEnemyOn: unitPassiveAtkPct({AGE2}, 'supercharged', true),
            noEnemyOff: unitPassiveAtkPct({AGE2}, 'supercharged', false),
            newtype: unitPassiveAtkPct({AGE2}, 'supercharged', true, mk(['新人类'])),
            xr: unitPassiveAtkPct({AGE2}, 'supercharged', true, mk(['X行者'])),
            both: unitPassiveAtkPct({AGE2}, 'supercharged', true, mk(['新人类','X行者'])),
            none: unitPassiveAtkPct({AGE2}, 'supercharged', true, mk(['主角'])),
            noPilot: unitPassiveAtkPct({AGE2}, 'supercharged', true, mk(null))
          }};
        }}""")
        print('[③ 敌方标签]', ct)
        assert ct['noEnemyOn'] == 40 and ct['noEnemyOff'] == 0, ct          # 计算页口径: 开计两条 / 关不计
        assert ct['newtype'] == 20 and ct['xr'] == 20, ct                   # 按敌方驾驶员标签逐条判定
        assert ct['both'] == 40, ct                                         # 双标签→两条同时生效(机制上可叠加)
        assert ct['none'] == 0 and ct['noPilot'] == 0, ct                   # 未指定驾驶员/标签不符→不计
        pg.evaluate(f"() => push({{page:'unit', title:'x', id:{AGE2}}})"); pg.wait_for_selector('.statgrid')
        vtxt = pg.evaluate("() => document.querySelector('#view').innerHTML")
        assert 'TAG 新人类' in vtxt and 'TAG X行者' in vtxt, '能力条件标签chips应显示'
        print('[③ 驾驶员标签判定+显示] 通过(全库唯一互斥对=AGE-2优势双标签)')

        # ---------- ④ 次数技能 ----------
        sup = pg.evaluate(f"""() => ({{
          acsam: supCountsOf({ACSAM}, {AGE2}, 'supercharged', true, true),
          acsamHigh: supCountsOf({ACSAM}, {AGE2}, 'high', false, true),
          zhang: supCountsOf({ZHANG}, {DRAGON}, 'supercharged', true, true),
          zhangNonSup: supCountsOf({ZHANG}, 1001003050, 'supercharged', true, true)
        }})""")
        print('[④ 次数技能]', sup)
        assert sup['acsam'] == {'atk': 3, 'def': 0}, sup        # 51+51+86(AGE-2EX&超一击)
        assert sup['acsamHigh'] == {'atk': 2, 'def': 0}, sup    # 非超一击+如实 → 86不计
        assert sup['zhang'] == {'atk': 2, 'def': 0}, sup
        assert sup['zhangNonSup'] == {'atk': 2, 'def': 0}, sup  # 51无条件→不随机体变化
        # 计算页标题显示
        pg.evaluate(f"() => {{ state.calc = Object.assign(state.calc, {{unitId:{AGE2}, charId:{ACSAM}, vigor:'default', ca:true}}); push({{page:'calc', title:'计算', id:null}}); }}")
        pg.wait_for_selector('.ctable')
        t1 = pg.evaluate("() => document.querySelector('#picku small').textContent")
        print('[④ 计算页标题]', t1.replace('\n', ' '))
        assert '支援攻击/反击+3次' in t1, t1
        # TOP列表徽章 + 组队/排行 smoke
        top = pg.evaluate("() => [...document.querySelectorAll('.trow')].map(e=>e.textContent).join(' ')")
        assert '支攻+' in top, top[:300]
        pg.evaluate("() => { state.stack = []; setTab('rank'); }"); pg.wait_for_timeout(2500)
        rl = pg.evaluate("() => document.querySelector('#rlist').textContent")
        assert '支攻+' in rl or '支防+' in rl, '排行页应含次数徽章'
        pg.evaluate("() => { state.stack = []; setTab('team'); }"); pg.wait_for_timeout(2500)
        ta = pg.evaluate("() => document.querySelector('#tarea').textContent")
        assert '支攻+' in ta or '支防+' in ta, '组队页应含次数徽章'
        print('[④ 次数技能整合] 通过(计算/组队/排行)')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v64 全部通过 ===')
