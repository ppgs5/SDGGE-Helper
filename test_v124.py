# -*- coding: utf-8 -*-
"""v124 验证: 武器增伤属性按 weapon_attr(元素)而非 attack_attr(射击/格斗/觉醒) 显示
① 再生高达EX 1370011150: GN翼状獠牙(特殊) → 特殊-25%, 不再显示光束; TRANS-AM EX(武器属性光束/特殊, 特效=光束) → 光束-35%
② 图鉴详情两行武器文本包含正确属性
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright
HERE='/root/workspace/ggen_app'; PORT=9068
srv=subprocess.Popen(['python3','-m','http.server',str(PORT)],cwd=os.path.join(HERE,'web'),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1.2); errors=[]
try:
  with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':420,'height':900}); pg.set_default_timeout(180000)
    pg.on('pageerror',lambda e:errors.append(str(e)))
    pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash',state='hidden'); pg.wait_for_timeout(900)
    r=pg.evaluate("""() => {
      const fx=id=>{const w=q1('SELECT * FROM weapons WHERE id=?',[id]); return weaponFxCompactOf(w,null,null,false,true,{condAll:true});};
      return { a: fx(137001115003), b: fx(137001115006), e3: effText({trait_type:14,trait_value:-25},{weapon_attr:3}) }; }""")
    print('[① 武器属性]',r)
    assert '特殊-25%' in r['a'] and '光束-25%' not in r['a'], r
    assert '光束-35%' in r['b'] and '光束/特殊-35%' not in r['b'], r
    assert r['e3'] == '特殊-25%', r
    pg.evaluate("() => { state.stack=[]; push({page:'unit',title:'x',id:1370011150}); render(); }")
    pg.wait_for_timeout(900)
    t=pg.evaluate("() => document.getElementById('view').innerText")
    assert '特殊-25%' in t and '光束-35%' in t, t[:500]
    print('[② 图鉴武器文本 通过]')
    assert not errors, errors
    print('=== test_v124 全部通过 ===')
    b.close()
finally: srv.terminate()
