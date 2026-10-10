# -*- coding: utf-8 -*-
"""v0.63 验证: 「支援攻击/反击时」条件被动(战斗动作条件 map_battle_action) + 驾驶员「攻击力提升%」(trait 7)
用户报告: 双头龙(EW版)(EX)+张五飞(EW版) 计算页 条件被动开/关 伤害完全相同,「支援攻击技能没有生效」
根因: ① 驾驶员能力 type7(攻击力提升%) 完全未解析 → (支援时)+25% 从未计入;
      ② 机体 type7 未判 map_battle_action → (支援时)+15% 被无条件计入;
      ③ unit_role(搭乘支援型)门槛未判。
口径: 开·假设满足 → 支援/反击类动作条件视为满足(计入); 关·如实判定 → 普通攻击口径不计入;
      「攻击时(※反击、支援攻击除外)」类在两种模式均计入(本计算即自身发动攻击)。
① 判定层: 张五飞 +25% / 双头龙机体 +15% 仅条件开计入; 支援型门槛(换攻击型机体→0); 「攻击时」类两模式一致
② 计算页: 开 攻击15,387(=floor(10991×1.40)) 伤害162,675/95,502/68,462; 关 10,991 → 96,724/59,462/48,322
③ 机体页最高伤害(unitBestPilot, 条件全开): 张五飞 95,502 与计算页中防列一致
④ 排行/组队页 smoke(渲染无错误, 条件被动chip可切换)
回归: test_v58 / test_v59 全过
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8996
UID, CID = 1219000650, 1219000501   # 双头龙高达(EW版)(EX) / 张五飞(EW版)

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

        # ---------- ① 判定层 ----------
        r = pg.evaluate(f"""() => {{
          const meta = metaOf({UID});
          const mk = (c, uid) => ({{passive:true, cpassive:true, skills:true, condAll:c, unitId:uid, upassive:true, multiPhase:true, pSpU:true}});
          const on = charBonus({CID}, 'supercharged', mk(true, {UID}), meta);
          const off = charBonus({CID}, 'supercharged', mk(false, {UID}), meta);
          const gid = 1001003050;   // 吉翁号(EX) 攻击型: 支援型门槛应挡掉
          const g = charBonus({CID}, 'supercharged', mk(true, gid), metaOf(gid));
          return {{
            on, off, g,
            upOn: unitPassiveAtkPct({UID}, 'supercharged', true),
            upOff: unitPassiveAtkPct({UID}, 'supercharged', false),
            atkOn: unitPassiveAtkPct(1375001550, 'supercharged', true),   // 「自身发动攻击的对战中+10% ※反击/支援除外」
            atkOff: unitPassiveAtkPct(1375001550, 'supercharged', false),
            mp: mpOf({UID}, {CID}, true, true, true),
            role: meta.role
          }};
        }}""")
        print('[① 判定] 条件开:', r['on'])
        print('[① 判定] 条件关:', r['off'])
        print('[① 判定] 机体被动 开/关:', r['upOn'], '/', r['upOff'], '| 攻击型机体:', r['g'], '| role:', r['role'], 'MP:', r['mp'])
        assert r['on'] == {'dmg': 15, 'melee': 65, 'ranged': 0, 'awaken': 0, 'atk': 25}, r['on']
        assert r['off']['atk'] == 0 and r['off']['melee'] == 65, r['off']
        assert r['upOn'] == 15 and r['upOff'] == 0, (r['upOn'], r['upOff'])
        assert r['g']['atk'] == 0 and r['g']['melee'] == 50, r['g']           # 非支援型: +25%被门槛挡掉, EX机体条件也失效
        assert r['atkOn'] == r['atkOff'] >= 10, (r['atkOn'], r['atkOff'])     # 「攻击时」类两模式一致
        assert r['mp'] == 12 and r['role'] == 3
        print('[① 判定层] 通过(支援型门槛/开-关区分/「攻击时」类恒计入)')

        # ---------- ② 计算页 ----------
        pg.evaluate(f"() => {{ state.calc = Object.assign(state.calc, {{unitId:{UID}, charId:{CID}, vigor:'default', ca:true}}); push({{page:'calc', title:'计算', id:null}}); }}")
        pg.wait_for_selector('.ctable')
        def read():
            return pg.evaluate("""() => ({
              title: document.querySelector('#picku small') ? document.querySelector('#picku small').textContent.replace(/\\s+/g,' ') : '',
              chips: [...document.querySelectorAll('.chips .chip')].map(e=>e.textContent.replace(/\\s+/g,' ')),
              rows: [...document.querySelectorAll('.ctable tr')].slice(1).map(tr => [...tr.querySelectorAll('td')].map(td=>td.textContent.trim())),
              top: document.querySelectorAll('.trow')[0] ? document.querySelectorAll('.trow')[0].textContent.replace(/\\s+/g,' ') : ''
            })""")
        a = read(); cs = ' | '.join(a['chips'])
        print('[② 开]', a['title'])
        print('[② 开chips]', cs)
        print('[② 开伤害]', a['rows'][0])
        assert '攻击 15,387' in a['title'] and '被动+15%' in a['title'] and '驾驶员攻击+25%' in a['title'], a['title']
        assert '机体被动 +15%' in cs, cs
        assert '驾驶员被动 增伤+15%·攻击+25%·格斗+40%' in cs, cs
        assert a['rows'][0][0].startswith('龙爪伸缩臂 EX') and a['rows'][0][1:] == ['162,675', '95,502', '68,462'], a['rows'][0]
        assert '张五飞' in a['top'] and '攻击+25%' in a['top'] and '162,675' in a['top'], a['top']

        pg.click('#ca'); pg.wait_for_timeout(400)
        c = read(); cs2 = ' | '.join(c['chips'])
        print('[② 关]', c['title'])
        print('[② 关chips]', cs2)
        print('[② 关伤害]', c['rows'][0])
        assert '攻击 10,991' in c['title'] and '驾驶员攻击' not in c['title'] and '被动+15%' not in c['title'], c['title']
        assert '机体被动 开' in cs2 and '攻击+25%' not in cs2, cs2
        assert c['rows'][0][1:] == ['96,724', '59,462', '48,322'], c['rows'][0]
        assert '96,724' in c['top'] and '攻击+25%' not in c['top'], c['top']

        pg.click('#ca'); pg.wait_for_timeout(400)    # 切回开
        assert read()['rows'][0][1:] == ['162,675', '95,502', '68,462'], '切回开应恢复'
        print('[② 计算页] 通过(开/关伤害随支援攻击条件联动)')

        # ---------- ③ 机体页最高伤害(条件全开口径) ----------
        ub = pg.evaluate(f"() => unitBestPilot({UID}, 20000).slice(0,3).map(x => [x.id, x.name, x.dmg])")
        print('[③ unitBestPilot TOP3]', ub)
        assert ub[0][0] == CID and ub[0][2] == 95502, ub[0]     # = 计算页中防20k列, 口径一致
        print('[③ 机体页最高伤害] 通过(张五飞 95,502)')

        # ---------- ④ 排行/组队 smoke ----------
        pg.evaluate("() => { state.stack = []; setTab('rank'); }"); pg.wait_for_timeout(2500)
        rca = pg.evaluate("() => { const el = document.querySelector('#rca'); return el ? el.textContent : null; }")
        print('[④ 排行页 条件被动chip]', rca)
        assert rca and rca.startswith('条件被动'), rca
        pg.click('#rca'); pg.wait_for_timeout(1500)
        rca2 = pg.evaluate("() => document.querySelector('#rca').textContent")
        assert rca2 != rca, '排行页条件被动应可切换'
        pg.click('#rca'); pg.wait_for_timeout(1500)
        pg.evaluate("() => { state.stack = []; setTab('team'); }"); pg.wait_for_timeout(2500)
        tca = pg.evaluate("() => { const el = document.querySelector('#tca'); return el ? el.textContent : null; }")
        print('[④ 组队页 条件被动chip]', tca)
        assert tca and tca.startswith('条件被动'), tca
        pg.click('#tca'); pg.wait_for_timeout(2000)
        assert pg.evaluate("() => !!document.querySelector('#view').textContent.trim()"), '组队页应正常渲染'
        print('[④ 排行/组队] 通过')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
print('=== test_v63 全部通过 ===')
