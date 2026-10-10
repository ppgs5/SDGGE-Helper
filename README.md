# SD高达永恒助手（SDGGE-Helper）

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

## 开源地址
- 源码 + 关键数据：https://github.com/ppgs5/SDGGE-Helper
- 数据更新仓库（App 内使用）：https://github.com/ppgs5/ggen-data
