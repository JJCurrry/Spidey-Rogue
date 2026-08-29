# HANDOFF-T001 · 交接棒

## 当前状态
- 整体进度：M1 已完成（治理脚手架 + 格子移动）；M2 已完成（战斗系统）。
- **产品目标（2026-08-29 新增，已明确为 MCU 荷兰弟版）**：最新蜘蛛侠（Spider-Man）风格，**以 MCU 荷兰弟（Tom Holland）版蜘蛛侠为主角**——红蓝战衣/蛛网发射器/纽约都市基调；所有里程碑的美术/剧情/机制均围绕此主题（非官方 IP，属风格致敬/个人学习项目）。
- 最近一次更新：2026-08-29

## 已完成（含 commit）
- [x] 治理脚手架（七件套 + 流水线 seed-guard）— commit `fdfaa30716477ab5c7b7e6435b5ee716a4d8b402`
- [x] M1 格子地图 + 玩家移动 + 单测 — 同 commit
- [x] 门禁实证：seed-guard 拦截裸 random；gate 四道门全绿
- [x] 产品主题明确为 MCU 荷兰弟（Tom Holland）版蜘蛛侠（四件制品同步）— commit `b202213`
- [x] M2 战斗系统：玩家/怪物 HP、`player_attack`（蛛网拳，伤害=基础+Seed 浮动）、HP 钳制 #3、确定性 #2、随机仅经 `RandomSource` #1、`spawn_monster` 手摆怪物、移动不可穿怪、`tests/test_combat.py`（10 例）— commit `defb2c9`

## 下一步指令（给下一个会话 / M3）
1. 读 `CLAUDE.md` → 拉 `docs/工单/T-003*`（怪物 AI）或新建。
2. 怪物 AI 草稿：简单追击 / 随机游走；随机必须走 `RandomSource`（红线 #1）。
3. 复用 M2 的 `Monster` 与 `player_attack`；AI 决策不得引入隐藏随机源（#2 确定性）。
4. 跑 `python scripts/gate.py` 全绿 → 更新本文件（含 commit）→ 提交。
5. 主题贯穿：M3 怪物命名 / 行为以蜘蛛侠风格落地，但不得破坏现有红线与门禁。

## 当前生效假设
- 假设 A：坐标 (x,y)，x 横向、y 纵向，原点左上。
- 假设 B：墙 `#` 不可入，地板 `.` 可入，玩家 `@` 唯一——且 `@` 在本作中即**蜘蛛侠（MCU 荷兰弟 / Tom Holland 版）**（见术语表）。
