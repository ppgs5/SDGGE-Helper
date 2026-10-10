# SD高达永恒助手 (ggen_app) — 每轮必守纪律

> 本文件每轮自动加载。目的：防止单轮用量超限导致频繁换轮/压缩。
> 完整背景见 `/root/workspace/ggen_app-resume.md` 与记忆 `ggen-helper-project.md`。

## 一、硬约束（沿用）
- 只动本项目文件（`/root/workspace/ggen_app`）；不动其他会话目录（`tools/` 已 gitignore）。
- 数据变更只走 `data/publish_update.py` 增量补丁（ggen-data 公开仓）＋ jsDelivr purge，**不重打包 APK**；只有 app 代码变更才打新 APK。
- 不确定就问用户（AskUserQuestion），不要猜。
- shell cwd 常被重置：git/sqlite/测试命令前先 `cd /root/workspace/ggen_app`。
- git commit 末尾加 `Co-Authored-By: Claude Code <noreply@anthropic.com>`。
- APK 命名 `SD高达永恒助手-vX.Y.apk`，`/sdcard/Download` 只留最新两个。

## 二、用量纪律（防超限换轮；必守）
1. **输出限量**：所有命令输出必须截断（`| tail -30`、`head`、切片）；单条工具输出 ≤4KB。
   禁止整表/整 JSON/整文件 dump 或大段打印（历史事故：单条输出 80KB、300KB）。
2. **精准读文件**：大文件先用 grep 定位再 Read（带 offset/limit），绝不整读（如 app.js 3800+ 行）。
3. **回归只跑两套**：新测试 + 上一轮测试；每套输出 `| tail -5`。更早测试已过、不重复跑（除非改动涉及其断言点）。
4. **合并工具调用**：相关联的检查合并成一条命令一次跑完（`&&`/heredoc），减少往返次数与中间输出。
5. **定点验证**：sqlite 只查单字段/单行；界面验证合并进 `test_vNN.py` 脚本一次跑完，不多次交互式冒烟。
6. **不重复考古**：已验证结论（模型公式、口径、坑）记录在 resume/记忆，直接引用，不重新推导。
7. **一轮一收尾**：任务完成即「测试→(必要时)打包部署→commit→resume/记忆更新」结束；新发现写进 resume 遗留段，不在本轮顺带展开。
8. **回复简短**：要点式，不重复贴大段数据/代码；不复述已完成的全过程。

## 三、每轮工作流（不变）
用户需求 → 诊断（grep/单点查询）→ 改 `web/`+`data/` → 写 `test_vNN.py`（NN=轮次序号）
→ 跑 新测试+上一轮（tail -5）→ 升 `build.gradle` versionCode/Name → `bash android_app/build.sh`
→ 部署改名保两个 → 校验 APK assets MD5 ＝ `web/` → **`python3 data/publish_app.py`（上传 Releases + app_version.json + purge）** → `git commit+push` → 更新 resume §4/§5 与记忆。
