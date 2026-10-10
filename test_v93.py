# -*- coding: utf-8 -*-
"""v0.93 验证: 数值提升档位(被动/主动/max) + 机体模型全面对齐网站/游戏
- 机体模型: max_*=等级上限插值(SP关★0), ★3=floor(x×1.4), SSP满10=(ssp_b+ssp_m)/2 加在★倍率前,
  能力%在★之后; 「被动」档=无条件能力(如网站显示), 「主动」=+技能, max=+条件型(视为满足)
① 高达SR(soshage网站逐位): 默认★3=58524/264/6120/5268/5850(+原41803); ★0=41803/189/4372/3763/4179;
   ★3+被动 EN=277(=网站默认态); ★3+SP+SSP+被动=93256/443/9753/8393/9324(=网站SP态)
② 档位chips交互: 被动/主动/max 互斥单选, 再点同档回原值
③ 条件型机体 1001003050: 被动含无条件(HP+5%/攻+15%), 不含(HP条件)攻+25%; max含 → 攻11571(原8265)
④ EXZELIA(手动): 原始74604/362/7681/6589/7397(EN±1注), SP三星90161/…, SSP满1093525/… 与游戏对齐
⑤ ULT机体: β·阿吉尔=插值固定值62135(=网站, 无★倍率); 阿姆罗UR机体不变
⑥ 驾驶员: 雪拉SSR被动=654/529/440/358/517(=网站逐位); 西布克 被动748/597/712/559/707 主动926/ max1033/;
   欧鲁卡 max含条件 守备453/反应469; 凯·西汀 SP开+被动 防御745(原621)
"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = '/root/workspace/ggen_app'
WEB = os.path.join(HERE, 'web')
PORT = 8994

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
        pg.evaluate("() => { state.unit={star:0,star3:true,sp:false,ssp:false,bst:0}; state.charSp=false; state.charBst=0; }")

        def stats():
            return pg.evaluate("""() => { const o={};
              document.querySelectorAll('.statgrid .stat').forEach(s => {
                const k = s.querySelector('.k').textContent.trim();
                const vEl = s.querySelector('.v');
                const small = [...s.children].filter(e => e !== s.querySelector('.k') && e !== vEl)
                                .map(e => e.innerText.trim()).join(' ');
                o[k] = vEl.innerText.replace(/\\s+/g,' ').trim() + (small ? ' ' + small.replace(/^原\\s*/, '原') : ''); });
              return o; }""")

        def open_unit(uid, wait=1800):
            pg.evaluate(f"() => {{ state.stack=[]; push({{page:'unit', title:'x', id:{uid}}}); }}")
            pg.wait_for_timeout(wait)

        def open_char(cid, wait=1600):
            pg.evaluate(f"() => {{ state.stack=[]; push({{page:'char', title:'x', id:{cid}}}); }}")
            pg.wait_for_timeout(wait)

        def ustate(**kw):
            js = ', '.join(f"state.unit.{k}={str(v).lower()}" for k, v in kw.items())
            pg.evaluate(f"() => {{ {js}; pageUnit(document.getElementById('view'), {{id:1001000100}}); }}")
            pg.wait_for_timeout(1000)

        # ① 高达SR 网站逐位
        open_unit(1001000100)
        st = stats()
        print('[① 高达SR ★3]', st)
        assert st == {'HP': '58,524 原41,803', 'EN': '264 原189', '攻击': '6,120 原4,372', '防御': '5,268 原3,763', '机动': '5,850 原4,179', '移动': '4'}, st
        ustate(star3=False)
        st = stats()
        print('[① 高达SR ★0]', st)
        assert st == {'HP': '41,803', 'EN': '189', '攻击': '4,372', '防御': '3,763', '机动': '4,179', '移动': '4'}, st
        ustate(bst=1)
        st = stats()
        print('[① 高达SR ★0+被动]', st)
        assert st['EN'] == '198 原189', st                      # = 网站★0态(189×1.05)
        ustate(star3=True)
        st = stats()
        print('[① 高达SR ★3+被动]', st)
        assert st['EN'] == '277 原264', st                      # = 网站默认态逐位(264×1.05)
        ustate(sp=True)
        st = stats()
        print('[① 高达SR ★3+SP+被动]', st)
        assert st == {'HP': '89,892', 'EN': '408 原389', '攻击': '9,401', '防御': '8,090', '机动': '8,971', '移动': '4'}, st
        ustate(ssp=True)
        st = stats()
        print('[① 高达SR ★3+SP+SSP+被动]', st)
        assert st == {'HP': '93,256', 'EN': '443 原403', '攻击': '9,753', '防御': '8,393', '机动': '9,324', '移动': '5 原4'}, st   # = 网站SP态逐位
        print('[① 机体模型网站逐位对齐 通过]')

        # ② 档位 chips 交互
        ustate(star3=True, sp=False, ssp=False, bst=0)
        pg.evaluate("() => document.getElementById('ubst1').click()")
        pg.wait_for_timeout(1000)
        r = pg.evaluate("""() => ({ bst: state.unit.bst, on1: document.getElementById('ubst1').classList.contains('gold'),
          on2: document.getElementById('ubst2').classList.contains('gold') })""")
        st = stats()
        assert r['bst'] == 1 and r['on1'] and not r['on2'] and st['EN'] == '277 原264', (r, st)
        pg.evaluate("() => document.getElementById('ubst3').click()")
        pg.wait_for_timeout(1000)
        r = pg.evaluate("() => ({ bst: state.unit.bst, on1: document.getElementById('ubst1').classList.contains('gold'), on3: document.getElementById('ubst3').classList.contains('gold') })")
        assert r == {'bst': 3, 'on1': False, 'on3': True}, r     # 互斥单选
        pg.evaluate("() => document.getElementById('ubst3').click()")
        pg.wait_for_timeout(1000)
        r = pg.evaluate("() => ({ bst: state.unit.bst })")
        st = stats()
        assert r['bst'] == 0 and st['EN'] == '264 原189', (r, st)  # 再点同档=回原值
        print('[② 档位 chips 互斥单选/同档回原值 通过]')

        # ③ 条件型机体
        open_unit(1001003050)
        st0 = stats()
        pg.evaluate("() => { state.unit.bst=1; pageUnit(document.getElementById('view'), {id:1001003050}); }")
        pg.wait_for_timeout(1000)
        st1 = stats()
        pg.evaluate("() => { state.unit.bst=3; pageUnit(document.getElementById('view'), {id:1001003050}); }")
        pg.wait_for_timeout(1000)
        st3 = stats()
        print('[③ 原值]', st0, '\n[③ 被动]', st1, '\n[③ max]', st3)
        assert st0['攻击'] == '8,265' and st1['攻击'] == '9,504 原8,265' and st1['HP'] == '75,358 原71,770', (st0, st1)
        assert st3['攻击'] == '11,571 原8,265' and st3['HP'] == st1['HP'] and st3['防御'] == st1['防御'], st3   # max含(HP条件)攻+25%
        print('[③ 被动=无条件(HP+5%/攻+15%) · max=+条件型(攻×1.40) 通过]')

        # ④ EXZELIA
        pg.evaluate("() => { state.unit={star:0,star3:true,sp:false,ssp:false,bst:0}; }")
        open_unit(1999000100)
        st = stats()
        print('[④ EXZELIA 原始★3]', st)
        assert st == {'HP': '74,064 原52,903', 'EN': '362 原259', '攻击': '7,681 原5,487', '防御': '6,589 原4,707', '机动': '7,397 原5,284', '移动': '5'}, st
        pg.evaluate("() => { state.unit.sp=true; pageUnit(document.getElementById('view'), {id:1999000100}); }")
        pg.wait_for_timeout(1000)
        st = stats()
        print('[④ EXZELIA SP三星]', st)
        assert st == {'HP': '90,161 原52,903', 'EN': '435 原259', '攻击': '9,352 原5,487', '防御': '8,023 原4,707', '机动': '8,999 原5,284', '移动': '5'}, st
        pg.evaluate("() => { state.unit.ssp=true; pageUnit(document.getElementById('view'), {id:1999000100}); }")
        pg.wait_for_timeout(1000)
        st = stats()
        print('[④ EXZELIA SSP满10]', st)
        assert st == {'HP': '93,525 原52,903', 'EN': '452 原259', '攻击': '9,704 原5,487', '防御': '8,325 原4,707', '机动': '9,352 原5,284', '移动': '5'}, st
        print('[④ EXZELIA 三态(游戏值) 通过, EN原始 363→362(±1, 新模型整数格点不可达)]')

        # ⑤ ULT / UR 机体
        pg.evaluate("() => { state.unit={star:0,star3:true,sp:false,ssp:false,bst:0}; }")
        open_unit(1114000800)
        st = stats()
        print('[⑤ β·阿吉尔 ULT]', st)
        assert st['HP'] == '62,135' and st['攻击'] == '5,986' and st['机动'] == '6,243', st   # = 网站ULT固定值(插值)
        pg.evaluate("() => { state.unit={star:0,star3:true,sp:false,ssp:false,bst:0}; }")
        open_unit(1001000150)
        st = stats()
        print('[⑤ 高达EX UR ★0]', st)
        assert st['攻击'] == '7,776' and st['HP'] == '94,162', st            # UR 默认★0(原值不变)
        pg.evaluate("() => { state.unit.star=3; pageUnit(document.getElementById('view'), {id:1001000150}); }")
        pg.wait_for_timeout(1000)
        st = stats()
        print('[⑤ 高达EX UR ★3]', st)
        assert st['攻击'] == '10,886 原7,776' and st['HP'] == '131,826 原94,162', st   # UR ★3=max×1.4(未变)
        print('[⑤ ULT插值固定值 + UR不变 通过]')

        # ⑥ 驾驶员
        open_char(1001000403)
        st = stats()
        pg.evaluate("() => document.getElementById('cbst1').click()")
        pg.wait_for_timeout(1000)
        st = stats()
        print('[⑥ 雪拉SSR 被动]', st)
        assert st == {'射击': '654 原623', '格斗': '529', '觉醒': '440 原383', '防御': '358', '反应': '517 原450'}, st   # = 网站逐位
        open_char(1162000102)
        pg.evaluate("() => { state.charBst=1; pageChar(document.getElementById('view'), {id:1162000102}); }")
        pg.wait_for_timeout(1000)
        st = stats()
        print('[⑥ 西布克 被动]', st)
        assert st == {'射击': '748 原713', '格斗': '597', '觉醒': '712 原570', '防御': '559', '反应': '707 原566'}, st
        pg.evaluate("() => { state.charBst=2; pageChar(document.getElementById('view'), {id:1162000102}); }")
        pg.wait_for_timeout(1000)
        st = stats()
        print('[⑥ 西布克 主动]', st)
        assert st['射击'] == '926 原713', st                     # 1.05(被动)+0.25(射击值增幅LV5) 加算
        pg.evaluate("() => { state.charBst=3; pageChar(document.getElementById('view'), {id:1162000102}); }")
        pg.wait_for_timeout(1000)
        st = stats()
        print('[⑥ 西布克 max]', st)
        assert st['射击'] == '1,033 原713', st                   # +15%(HP条件型EX, 视为满足)
        open_char(1300001400)
        pg.evaluate("() => { state.charBst=3; pageChar(document.getElementById('view'), {id:1300001400}); }")
        pg.wait_for_timeout(1000)
        st = stats()
        print('[⑥ 欧鲁卡 max]', st)
        assert st['射击'] == '501 原478' and st['防御'] == '453 原378' and st['反应'] == '469 原391', st   # 特化人条件型 守备·反应+20%
        # 凯·西汀 SP开+被动
        pg.evaluate("() => { state.charSp=true; state.charBst=1; state.stack=[]; push({page:'char', title:'x', id:1001000200}); }")
        pg.wait_for_timeout(1400)
        st = stats()
        print('[⑥ 凯·西汀 SP开+被动]', st)
        assert st['防御'] == '745 原621', st                     # SP版 守备值提升15%+5% 加算
        pg.evaluate("() => { state.charSp=false; state.charBst=0; }")
        print('[⑥ 驾驶员档位(网站逐位/条件型/SP联动) 通过]')
        print('=== test_v93 全部通过 ===')
        b.close()
finally:
    srv.terminate()
if errors:
    print('页面错误:', errors[:6]); sys.exit(1)
