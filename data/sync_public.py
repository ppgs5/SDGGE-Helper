#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步「源代码 + 关键数据」到公开仓 ppgs5/SDGGE-Helper（私有开发仓 ggen-helper 不动）

用法: python3 data/sync_public.py
内容清单（只发布源码与关键数据, 不含抓取原始页/构建产物/APK 历史）:
  web/           前端全部（index/app/engine/styles + vendor + img 头像 + data/ggen.db 完整库）
  data/          建库与发布脚本 + 手动收录 json + 名称表（不含 ggen.db 副本/抓取中间产物）
  android_app/   安卓壳源码（build.sh/gradle/java/res/manifest；不含 assets 与 build 产物）
  CLAUDE.md + test_v*.py + README.md（自动生成）
"""
import glob, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PUB = os.environ.get('GGEN_PUBLIC_REPO', '/root/workspace/SDGGE-Helper')
GH_REPO = 'ppgs5/SDGGE-Helper'


def sh(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-600:]); print(r.stderr[-600:])
        raise SystemExit(f'命令失败: {cmd}')
    return r.stdout.strip()


def copy_tree(src, dst, excludes=()):   # 镜像目录(git 按内容差异提交, 无 rsync 依赖)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', *excludes))


README = """# SD高达永恒助手（SDGGE-Helper）

《SD高达永恒》（SD Gundam G Generation ETERNAL）图鉴 + 伤害计算器 —— 安卓 App（WebView 壳 + 单页应用 SQLite/WASM）。

**作者：DeepSeek**

## 结构
- `web/` 前端单页应用（图鉴/计算/排行/组队/特性 + 更新中心），`web/data/ggen.db` 为完整数据库
- `data/` 数据管线：`build_db.py` 建库、`publish_update.py` 数据增量补丁发布、`publish_app.py` APK 发布、`sync_public.py` 本仓同步
- `android_app/` 安卓壳（WebView + JS 桥：数据库热更新 / APP 自更新 / 图片落盘）
- `test_v*.py` Playwright 回归测试

## 数据更新
App 内「更新中心」联网比对增量补丁（无需重装）；数据随补丁更新，新功能需更新 APK（App 内可一键下载安装）。

## 数据来源与声明
- 游戏数据整理自 soshage / gamekee 等公开资料站，仅供学习交流；
- 非官方作品，与 Bandai Namco 无关联；游戏内容版权归原权利方所有。

## 安全与完整性
- **SHA256 校验**：每个 Release 页附 APK 的 SHA256（与源码构建产物一致）；校验：`sha256sum 文件名`（Linux/安卓终端）或 `certutil -hashfile 文件名 SHA256`（Windows）
- **权限**：APK 仅申请 INTERNET（联网检查数据更新/下载新版 APK）与 REQUEST_INSTALL_PACKAGES（App 内下载后调起系统安装）；不申请存储/通讯录/短信/剪贴板等敏感权限
- **免责声明**：本工具为第三方非官方作品，与 Bandai Namco（万代）无任何关联；使用存在账号风控与设备安全风险，使用者风险自担；仅供数据查询与伤害计算的学习交流

## 开源地址
- 源码 + 关键数据：https://github.com/ppgs5/SDGGE-Helper
- 数据更新仓库（App 内使用）：https://github.com/ppgs5/ggen-data
"""


def main():
    # 仓库不存在则创建并克隆
    if not os.path.isdir(os.path.join(PUB, '.git')):
        try:
            sh(f'gh repo view {GH_REPO} --json name')
        except SystemExit:
            sh(f'gh repo create {GH_REPO} --public --description "SD高达永恒助手 — 图鉴+伤害计算器 源代码与关键数据(作者 DeepSeek)"')
        if os.path.isdir(PUB):
            shutil.rmtree(PUB)
        sh(f'gh repo clone {GH_REPO} "{PUB}"')
    # 同步清单
    copy_tree(os.path.join(ROOT, 'web'), os.path.join(PUB, 'web'),
              excludes=['patches', 'version.json'])
    os.makedirs(os.path.join(PUB, 'data'), exist_ok=True)
    for f in ('build_db.py', 'publish_update.py', 'publish_app.py', 'sync_public.py',
              'manual_chars.json', 'manual_units.json', 'manual_weapon_fx.json'):
        shutil.copy2(os.path.join(ROOT, 'data', f), os.path.join(PUB, 'data', f))
    for f in glob.glob(os.path.join(ROOT, 'data', 'names_zhcn*.json')):
        shutil.copy2(f, os.path.join(PUB, 'data', os.path.basename(f)))
    copy_tree(os.path.join(ROOT, 'android_app'), os.path.join(PUB, 'android_app'),
              excludes=['build', '.gradle', 'local.properties', 'assets'])
    shutil.copy2(os.path.join(ROOT, 'CLAUDE.md'), os.path.join(PUB, 'CLAUDE.md'))
    for f in glob.glob(os.path.join(ROOT, 'test_v*.py')):
        shutil.copy2(f, os.path.join(PUB, os.path.basename(f)))
    with open(os.path.join(PUB, 'README.md'), 'w', encoding='utf-8') as fh:
        fh.write(README)
    with open(os.path.join(PUB, '.gitignore'), 'w', encoding='utf-8') as fh:
        fh.write('__pycache__/\n*.pyc\n')
    sh('git add -A', cwd=PUB)
    if sh('git status --short', cwd=PUB):
        sh(f'git commit -m "sync 源码+关键数据 ({time.strftime("%Y-%m-%d")})"', cwd=PUB)
        sh('git push -u origin main', cwd=PUB)
        print('已同步并推送公开仓')
    else:
        print('无变化')


if __name__ == '__main__':
    main()
