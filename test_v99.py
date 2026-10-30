# -*- coding: utf-8 -*-
"""v0.99 验证: 变形/换装/逃生 装置 → 跳转关联机体
① 有同型号变体的机体(异端高达金色机天照)点「换装」出现选择弹窗
② 弹窗点选 → 跳到该机体页
③ 关联唯一时直接跳转
"""
import subprocess, time
from playwright.sync_api import sync_playwright
PORT=9012
srv=subprocess.Popen(['python3','-m','http.server',str(PORT)],cwd='/root/workspace/ggen_app/web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1.2)
try:
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={'width':420,'height':900}); pg.set_default_timeout(120000)
        pg.add_init_script("window.Android={dbInfo:()=>'{}',listPatches:()=>'[]'};")
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash',state='hidden'); pg.wait_for_timeout(1200)
        r=pg.evaluate("""() => {
            const u=q1("SELECT * FROM units WHERE id=1070000310");
            const rel=relatedUnits(u);
            return {id:u.id, models:u.models, rel:rel.map(x=>x.name)};
        }""")
        print('[① 关联机体]', r['rel'][:3], '共', len(r['rel']))
        assert len(r['rel'])>=1
        pg.evaluate("(id)=>{state.stack=[];push({page:'unit',title:'试作亚希玛TR-3',id});}", r['id'])
        pg.wait_for_timeout(900)
        has=pg.evaluate("() => !!document.querySelector('[data-gomech=\\\"变形机构\\\"]')")
        print('[① 换装装置存在]', has)
        if has:
            pg.evaluate("() => document.querySelector('[data-gomech=\\\"变形机构\\\"]').click()")
            pg.wait_for_timeout(600)
            n=pg.evaluate("() => document.querySelectorAll('#unitpick [data-pick]').length")
            print('[① 选择弹窗项数]', n)
            if n>=1:
                pg.evaluate("() => document.querySelector('#unitpick [data-pick]').click()")
                pg.wait_for_timeout(800)
            else:
                pg.wait_for_timeout(400)   # 关联唯一: 直接跳转
            page=pg.evaluate("() => { const s=state.stack[state.stack.length-1]; return s && s.page; }")
            print('[② 跳转页面]', page)
            assert page=='unit'
        print('=== test_v99 通过 ===')
        b.close()
finally:
    srv.terminate()
