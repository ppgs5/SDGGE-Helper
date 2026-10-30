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
→ 部署改名保两个 → 校验 APK assets MD5 ＝ `web/` → **`python3 data/publish_app.py`（上传 Releases + app_version.json + purge）** → **`python3 data/sync_public.py`（同步公开仓 SDGGE-Helper）** → `git commit+push` → 更新 resume §4/§5 与记忆。

## 全局规则（必须遵守）
见 `map_tools/全局规则.md`：用户指令优先；不得写死未确认数值（格子尺寸/颜色/阈值/棋盘尺寸/验收格数）；不得自造验算指标；改数据需截图证据或用户指示；打包发布需用户许可；每轮报告改动/依据/未确认项。

## 四、不变量纪律（2026-10 起，最高优先级）
- **已定口径总表见 `docs/规则总表.md`（首动技能顺序 / MAP 形状算法 / 伤害公式 / 两页一致性 / 数据脚本 / 版本号）——改任何一条前必须先问用户。**
- 规则清单见 `docs/不变量.md`（L0 规则级 / L1 数据级 / L2 存档缓存级）。
- **每轮改动前后都必须跑 `python3 test_invariants.py`，必须全绿**；不绿先修，不许提交。
- 改任何口径：① 先在 `docs/不变量.md` 登记或更新条目 ② 加/改断言 ③ 再改代码 ④ 缓存键版本号 +1。
- 禁止用「大量字符串替换」盲改计算逻辑：改前先 grep 出全部调用点（`Engine.damageWithWeapon`、`defReduce`、`effStar` 等），逐点确认后再改。

## 五、心态纪律（每次行动前默念，写入文件以长期生效）
- **没有预算压力、没有时间紧张、没有回合倒计时。** 这些不是判断依据，也不得出现在回复里。
- **禁止出现的表述**：「预算」「回合快用尽」「时间很紧」「先收尾」「一次专注」等一切催促性说法。
- 每轮只问三件事：这条规则对不对？测试过了没有？有没有改坏别的地方？
- 做不完就直说「这步没做完，还差 X」，**不许用降质交付换取步数**。
- 若真到会话上限：明确说「需要继续」，不写半成品、不省略测试。
