# -*- coding: utf-8 -*-
"""v151 验证: 首动技能优先度按官方顺序（射程/回HP/移动/减伤/MP/必中/命中闪避/爆裂/摇摆/增幅/暴击/EN）
① 无战场事实时: 爆裂优先于摇摆闪避（伊藤·剑 案例）
② unreachable=true: 高速(+移动) 抢在减伤之前
③ hitLow=true: 锁定(必中) 生效
④ 同时有「命中率、闪避率提升」与「攻击爆裂」且 fdth: 命中闪避优先（官方 7 < 8）
"""
import os, subprocess, time, json
from playwright.sync_api import sync_playwright
HERE = '/root/workspace/ggen_app'; PORT = 9141

srv = subprocess.Popen(['python3', '-m', 'http.server', str(PORT)], cwd=os.path.join(HERE, 'web'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2); errors = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 420, 'height': 1200}); pg.set_default_timeout(180000)
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html'); pg.wait_for_selector('#splash', state='hidden'); pg.wait_for_timeout(900)
        r = pg.evaluate("""() => {
          const mk = names => names.map(n => ({ name: n, desc: '' }));
          return {
            itoFdth: firstActOfRows(mk(['攻击爆裂 LV4','锁定 LV1','摇摆闪避 LV1']), ['melee'], true, 0).k,
            unreach: firstActOfRows(mk(['高速 LV1','威力抵御 LV1','摇摆闪避 LV1']), ['melee'], false, 0, {unreachable:true}).name,
            hitLow: firstActOfRows(mk(['锁定 LV1','攻击爆裂 LV4']), ['melee'], false, 0, {hitLow:true}).name,
            evaVsBurst: firstActOfRows(mk(['命中率、闪避率提升 LV2','攻击爆裂 LV4']), ['melee'], true, 0).k,
            mpOff: firstActOfRows(mk(['MP提升 LV5','摇摆闪避 LV1']), ['melee'], true, 2).k,
            mpOn: firstActOfRows(mk(['MP提升 LV5','摇摆闪避 LV1']), ['melee'], true, 3).k
          }; }""")
        print('[优先度]', json.dumps(r, ensure_ascii=False))
        assert r['itoFdth'] == 'burst', r
        assert r['unreach'].startswith('高速'), r
        assert r['hitLow'].startswith('锁定'), r
        assert r['evaVsBurst'] == 'eva', r
        assert r['mpOff'] == 'sway' and r['mpOn'] == 'mp', r
        assert not errors, errors
        print('=== test_v151 全部通过 ===')
        b.close()
finally:
    srv.terminate()
