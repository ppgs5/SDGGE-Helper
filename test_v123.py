# -*- coding: utf-8 -*-
"""v123 验证: max满层开关 + 条件被动1层 + 首动攻击次数0层
① 图鉴max档: 再生EX 1370011150 攻击 原10651/主被动13313/max15230 (对战次数+18%满层)
② max开关: 机体对战次数叠层 关=3%(1层) 开=18%(满层); 首动=0层(即使max开)
③ 组队型叠层: 1031000102(擎天神高达EX) 每有最高15%: 条件被动开+max关=3, max开=15, 条件被动关=0
④ 计算/排行/组队 cmax/rmax/tmax chip存在可切换
"""
import os, subprocess, time
from playwright.sync_api import sync_playwright
HERE='/root/workspace/ggen_app'; PORT=9066
srv=subprocess.Popen(['python3','-m','http.server',str(PORT)],cwd=os.path.join(HERE,'web'),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1.2); errors=[]
try:
  with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':420,'height':900}); pg.set_default_timeout(180000)
    pg.on('pageerror',lambda e:errors.append(str(e)))
    pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash',state='hidden'); pg.wait_for_timeout(900)
    r1=pg.evaluate("""() => { const u=q1('SELECT * FROM units WHERE id=1370011150'); const v={}; for(const m of [1,2,3]) v[m]=unitListStat(u,'atk',m,3); return v; }""")
    print('[① max档]',r1); assert r1=={'1':10651,'2':13313,'3':15230},r1
    r2=pg.evaluate("""() => {
      state.maxOn=false; const off=unitPassiveAtkPct(1370011150,'default',true,null,false,false);
      state.maxOn=true; const on=unitPassiveAtkPct(1370011150,'default',true,null,false,false);
      const first=unitPassiveAtkPct(1370011150,'default',true,null,false,true);
      state.maxOn=false; return {off,on,first}; }""")
    print('[② 机体叠层]',r2); assert r2=={'off':3,'on':18,'first':0},r2
    r3=pg.evaluate("""() => {
      const opts=ca=>({passive:true,cpassive:true,skills:false,condAll:ca,first:false,unitId:1031001250,upassive:true,multiPhase:false,pSpU:true});
      state.maxOn=false; const a=charBonus(1031000102,'default',opts(true),metaOf(1031001250)).atk;
      state.maxOn=true; const b=charBonus(1031000102,'default',opts(true),metaOf(1031001250)).atk;
      state.maxOn=false; const c=charBonus(1031000102,'default',opts(false),metaOf(1031001250)).atk;
      return {a,b,c}; }""")
    print('[③ 组队型叠层]',r3); assert r3=={'a':3,'b':15,'c':0},r3
    r4=pg.evaluate("""() => {
      const f=filt('rank'); const cfg={targetDef:10000,targetCharDef:750,vigor:'default',crit:false};
      const opts={passive:true,cpassive:true,skills:false,condAll:true,autoVigor:true,multiPhase:false,star:3,spU:true,s3u:true,sspU:true,pSpU:true,uSk:true};
      state.maxOn=false; const A=buildRanking(f,cfg,opts).find(x=>x.unitId===1370011150);
      state.maxOn=true; const B=buildRanking(f,cfg,opts).find(x=>x.unitId===1370011150);
      const F={passive:true,cpassive:true,skills:false,condAll:true,autoVigor:true,multiPhase:false,star:3,spU:true,s3u:true,sspU:true,pSpU:true,uSk:true,first:true};
      const C=buildRanking(f,cfg,F).find(x=>x.unitId===1370011150);
      state.maxOn=false; const D=buildRanking(f,cfg,F).find(x=>x.unitId===1370011150);
      state.maxOn=false;
      return {p0:A&&A.pct,p1:B&&B.pct,f0:C&&C.pct,f1:D&&D.pct,d0:A&&A.dmg,d1:B&&B.dmg}; }""")
    print('[③b 排行max/首动]',r4)
    assert r4['p1']-r4['p0']==15 and r4['d1']>r4['d0'],r4
    assert r4['f0']==r4['f1'],r4
    pg.evaluate("() => { state.calc.unitId=1370011150; state.stack=[]; push({page:'calc',title:''}); render(); }")
    for cid in ('cmax',):
      pg.wait_for_selector('#'+cid,timeout=120000)
    was=pg.evaluate('() => state.maxOn'); pg.click('#cmax'); pg.wait_for_timeout(900)
    assert pg.evaluate('() => state.maxOn')!=was
    for page,cid in (('rank','rmax'),('team','tmax')):
      pg.evaluate("(p2)=>{state.stack=[];push({page:p2,title:''});render();}",page)
      pg.wait_for_selector('#'+cid,timeout=180000)
    print('[④ 三页max开关] 通过')
    assert not errors, errors
    print('=== test_v123 全部通过 ===')
    b.close()
finally: srv.terminate()
