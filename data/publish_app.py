#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布 APP 新版本: APK 上传到 ggen-data Releases + 写 app_version.json(App 内「APP 版本」自更新用) + purge jsDelivr

用法: python3 data/publish_app.py [/sdcard/Download/SD高达永恒助手-vX.Y.apk] [--no-upload]
  无参数: 自动取 /sdcard/Download 里最新的 SD高达永恒助手-v*.apk
  --no-upload: 只写 app_version.json(不上传 release, 调试用)
产物 app_version.json: {version,size,sha256,apk_url,apk_mirror,note,updated_at} (仓库根, 走与数据同一套镜像线路被 App 拉取)
"""
import glob, hashlib, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('GGEN_DATA_REPO', '/root/workspace/ggen-data')
GH_REPO = 'ppgs5/SDGGE-Helper'        # Release 发布到公开开源仓(直接下载入口)
DATA_REPO = 'ppgs5/ggen-data'        # app_version.json 仍写数据仓(走镜像链被 App 拉取)
NOTE = os.environ.get('GGEN_RELEASE_NOTE', '').strip()   # 更新日志(更新说明): 发布时用环境变量传入 → 写入 Release 说明 + app_version.json note(App 更新提示)


def sh(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-600:]); print(r.stderr[-600:])
        raise SystemExit(f'命令失败: {cmd}')
    return r.stdout.strip()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    no_upload = '--no-upload' in sys.argv
    apk = args[0] if args else max((os.path.getmtime(p), p) for p in glob.glob('/sdcard/Download/SD高达永恒助手-v*.apk'))[1]
    name = os.path.basename(apk)
    m = re.search(r'v(\d+(?:\.\d+)+)\.apk$', name)
    if not m:
        raise SystemExit(f'文件名未含版本号(vX.Y.apk): {name}')
    ver = m.group(1)
    tag = 'v' + ver
    size = os.path.getsize(apk)
    sha = hashlib.sha256(open(apk, 'rb').read()).hexdigest()
    asset = f'SDGGE-Helper-{tag}.apk'   # gh 会把非ASCII文件名清洗为 '.', 上传用 ASCII 名(手机端保存名由 App 指定, 不受影响)
    url = f'https://github.com/{GH_REPO}/releases/download/{tag}/{asset}'
    mirror = 'https://gh-proxy.com/' + url
    if not no_upload:
        tmp = os.path.join('/tmp', asset)
        import shutil
        shutil.copy(apk, tmp)
        notes = ((NOTE + '\n\n') if NOTE else '') + f'APK {tag} · {size} 字节 · sha256 {sha[:16]}。数据仍走增量补丁在线更新, 不重装即可生效。'
        rels = sh(f'gh release list --repo {GH_REPO} --limit 100')
        if tag in rels:
            sh(f'gh release upload {tag} "{tmp}" --repo {GH_REPO} --clobber')
            sh(f'gh release edit {tag} --repo {GH_REPO} --notes "{notes}"')
        else:
            sh(f'gh release create {tag} "{tmp}" --repo {GH_REPO} --title "SD高达永恒助手 {tag}" --notes "{notes}"')
        print(f'Release {tag} 已上传 ({size/1e6:.1f} MB, asset={asset})')
    av = {'version': ver, 'size': size, 'sha256': sha, 'apk_url': url, 'apk_mirror': mirror,
          'apk_urls': [url, mirror, 'https://ghproxy.net/' + url, 'https://gh.llkk.cc/' + url],   # 多线路备选(免VPN镜像已实测)
          'repo': f'https://github.com/{GH_REPO}', 'mirror_page': f'https://gh-proxy.com/https://github.com/{GH_REPO}',
          'note': (((NOTE + '\n') if NOTE else '') + f'v{ver} 更新包（{size/1e6:.1f} MB），下载完成后弹系统安装界面。'), 'updated_at': int(time.time())}
    with open(os.path.join(REPO, 'app_version.json'), 'w', encoding='utf-8') as f:
        json.dump(av, f, ensure_ascii=False, indent=1)
    sh('git add app_version.json', cwd=REPO)
    if sh('git status --short', cwd=REPO):
        sh(f'git commit -m "app {tag} ({size} bytes sha256={sha[:12]})"', cwd=REPO)
        sh('git push -u origin main', cwd=REPO)
    try:
        r = subprocess.run(['curl', '-s', f'https://purge.jsdelivr.net/gh/{DATA_REPO}@main/app_version.json'],
                           capture_output=True, text=True, timeout=40)
        print('purge jsDelivr:', 'ok' if 'finished' in (r.stdout or '') else (r.stdout or '')[:80])
    except Exception as e:
        print('purge skip:', e)
    print(f'APP 发布完成: {tag} · {size} bytes · sha256 {sha[:16]} · app_version.json 已更新')


if __name__ == '__main__':
    main()
