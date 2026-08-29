# HANDOFF-T001 · 交接棒

## 当前状态
- 整体进度：M1 已完成（治理脚手架 + 格子移动）
- 最近一次更新：2026-08-29

## 已完成（含 commit）
- [x] 治理脚手架（七件套 + 流水线 seed-guard）— commit `fdfaa30716477ab5c7b7e6435b5ee716a4d8b402`
- [x] M1 格子地图 + 玩家移动 + 单测 — 同 commit
- [x] 门禁实证：seed-guard 拦截裸 random；gate 四道门全绿

## 下一步指令（给下一个会话 / M2）
1. 读 `CLAUDE.md` → 拉 `docs/工单/T-002*`（战斗）或新建。
2. 战斗系统草稿：玩家/怪物 HP（不变量 #3）、攻击结算确定性（#2）。
3. 随机必须走 `src/rogue/rng.py` 的 `RandomSource`（红线 #1）。
4. 跑 `python scripts/gate.py` 全绿 → 更新本文件（含 commit）→ 提交。

## 当前生效假设
- 假设 A：坐标 (x,y)，x 横向、y 纵向，原点左上。
- 假设 B：墙 `#` 不可入，地板 `.` 可入，玩家 `@` 唯一。
