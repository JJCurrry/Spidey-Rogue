# HANDOFF-T001 · 交接棒

## 当前状态
- 整体进度：M1 已完成（治理脚手架 + 格子移动）；M2 已完成（战斗系统）；M3 已完成（怪物 AI）；**M4 已完成（道具与背包）**。
- **产品目标（2026-08-29 新增，已明确为 MCU 荷兰弟版）**：最新蜘蛛侠（Spider-Man）风格，**以 MCU 荷兰弟（Tom Holland）版蜘蛛侠为主角**——红蓝战衣/蛛网发射器/纽约都市基调；所有里程碑的美术/剧情/机制均围绕此主题（非官方 IP，属风格致敬/个人学习项目）。
- 最近一次更新：2026-08-29（M4 完成）

## 已完成（含 commit）
- [x] 治理脚手架（七件套 + 流水线 seed-guard）— commit `fdfaa30716477ab5c7b7e6435b5ee716a4d8b402`
- [x] M1 格子地图 + 玩家移动 + 单测 — 同 commit
- [x] 门禁实证：seed-guard 拦截裸 random；gate 四道门全绿
- [x] 产品主题明确为 MCU 荷兰弟（Tom Holland）版蜘蛛侠（四件制品同步）— commit `b202213`
- [x] M2 战斗系统：玩家/怪物 HP、`player_attack`（蛛网拳，伤害=基础+Seed 浮动）、HP 钳制 #3、确定性 #2、随机仅经 `RandomSource` #1、`spawn_monster` 手摆怪物、移动不可穿怪、`tests/test_combat.py`（10 例）— commit `defb2c9`
- [x] M3 怪物 AI：chase（贪心追击，纯确定性）/ wander（随机游走，随机仅经 `RandomSource`）；相邻反击（固定伤害，HP 钳制 #3）；AI 移动不可越界/穿墙/踩玩家/踩怪（#4）；`monster_turn` 固定顺序推进（#2）；`tests/test_ai.py`（11 例），用例数 17→28，门禁四道门全绿 — commit `9d65c74f324ed3a0672df37eb566bc7e4e41d0f7`

- [x] M4 道具与背包：`Item` 实体 + 地面 `Game.items` / 背包 `Game.inventory`（容量 5）；`spawn_item` / `item_at` / `pick_up` / `use_item`；三件主题道具（梅姨的三明治 / 蛛网发射器备用芯 / 斯塔克纳米强化剂）；怪物阵亡掉落（rng.chance + rng.choice，#1/#2）；`Monster.stunned` 接入 `monster_act`（被缠住跳过整次行动、不消耗 rng）；新增不变量 #5 背包容量上限、#6 HP 不超上限；`tests/test_items.py`（23 例），用例数 28→51，门禁四道门全绿 — commit `32814981110dd8330ee3173824d00afb44f922ad`

## 下一步指令（给下一个会话 / M5）
1. 读 `CLAUDE.md` → 拉 `docs/工单/T-005*`（程序化关卡）或新建。
2. 房间+走廊生成（BSP 或房间随机放置）；**生成随机必须走 `RandomSource`**（红线 #1），并补上待生效红线「地图连通性：玩家起点可达所有地板格」的机器检查。
3. 复用 M4 的 `spawn_item` 撒道具、`spawn_monster` 撒怪（M5 起怪物不再手摆）；不得引入隐藏随机源（#2 确定性）。
4. 跑 `python scripts/gate.py` 全绿 → 更新本文件（含 commit）→ 提交。
5. 主题贯穿：M5 楼层命名以纽约都市地标落地（如「皇后区地铁隧道」「奥斯本大厦底层」），但不得破坏现有红线与门禁。
6. 可选清理：仓库根目录的 `.workbuddy/` 会被评审流水线「范围审计」判为 WARN（AI 工作记忆目录，非源码）；决定是否加入 `.gitignore` 或忽略该告警。

## 当前生效假设
- 假设 A：坐标 (x,y)，x 横向、y 纵向，原点左上。
- 假设 B：墙 `#` 不可入，地板 `.` 可入，玩家 `@` 唯一——且 `@` 在本作中即**蜘蛛侠（MCU 荷兰弟 / Tom Holland 版）**（见术语表）。
- 假设 C（M4 起）：道具是**实体层**，不改写 `grid`（`grid` 只存地形与 `@`）；地面道具渲染为 `!`，玩家/怪物优先显示。
- 假设 D（M4 起）：一格最多一个道具；背包满时拾取失败、道具留在地面（不自动替换/丢弃）。
