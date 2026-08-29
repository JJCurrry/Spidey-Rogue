# HANDOFF-T001 · 交接棒

## 当前状态
- 整体进度：M1 已完成（治理脚手架 + 格子移动）；M2 已完成（战斗系统）；M3 已完成（怪物 AI）；M4 已完成（道具与背包）；**M5 已完成（程序化关卡）**。
- **产品目标（2026-08-29 新增，已明确为 MCU 荷兰弟版）**：最新蜘蛛侠（Spider-Man）风格，**以 MCU 荷兰弟（Tom Holland）版蜘蛛侠为主角**——红蓝战衣/蛛网发射器/纽约都市基调；所有里程碑的美术/剧情/机制均围绕此主题（非官方 IP，属风格致敬/个人学习项目）。
- 最近一次更新：2026-08-29（M5 完成）

## 已完成（含 commit）
- [x] 治理脚手架（七件套 + 流水线 seed-guard）— commit `fdfaa30716477ab5c7b7e6435b5ee716a4d8b402`
- [x] M1 格子地图 + 玩家移动 + 单测 — 同 commit
- [x] 门禁实证：seed-guard 拦截裸 random；gate 四道门全绿
- [x] 产品主题明确为 MCU 荷兰弟（Tom Holland）版蜘蛛侠（四件制品同步）— commit `b202213`
- [x] M2 战斗系统：玩家/怪物 HP、`player_attack`（蛛网拳，伤害=基础+Seed 浮动）、HP 钳制 #3、确定性 #2、随机仅经 `RandomSource` #1、`spawn_monster` 手摆怪物、移动不可穿怪、`tests/test_combat.py`（10 例）— commit `defb2c9`
- [x] M3 怪物 AI：chase（贪心追击，纯确定性）/ wander（随机游走，随机仅经 `RandomSource`）；相邻反击（固定伤害，HP 钳制 #3）；AI 移动不可越界/穿墙/踩玩家/踩怪（#4）；`monster_turn` 固定顺序推进（#2）；`tests/test_ai.py`（11 例），用例数 17→28，门禁四道门全绿 — commit `9d65c74f324ed3a0672df37eb566bc7e4e41d0f7`

- [x] M4 道具与背包：`Item` 实体 + 地面 `Game.items` / 背包 `Game.inventory`（容量 5）；`spawn_item` / `item_at` / `pick_up` / `use_item`；三件主题道具（梅姨的三明治 / 蛛网发射器备用芯 / 斯塔克纳米强化剂）；怪物阵亡掉落（rng.chance + rng.choice，#1/#2）；`Monster.stunned` 接入 `monster_act`（被缠住跳过整次行动、不消耗 rng）；新增不变量 #5 背包容量上限、#6 HP 不超上限；`tests/test_items.py`（23 例），用例数 28→51，门禁四道门全绿 — commit `32814981110dd8330ee3173824d00afb44f922ad`

- [x] M5 程序化关卡：新增 `src/rogue/level.py`（`Room` / `Level` / `generate_level`，拒绝采样摆房间 + L 形走廊成链 + 洪泛封填死口袋）与 `src/rogue/tiles.py`（格子字符常量，消除 game.py 与 level.py 的字面量重复）；`Game` 新增 `load_level` / `_populate_level` / `can_descend` / `descend` / `procedural` 工厂与 `depth` / `level_name` / `rooms` / `stairs`（**楼梯是坐标、不改写 grid**）；10 个纽约地标楼层名按层号循环；怪物登记表 6 种（按层解锁 + HP 随层成长）；新增不变量 **#7 地图连通性**（原「待生效」转正，机器判定 30 seed 洪泛）；`tests/test_level.py`（28 例），用例数 51→79，门禁四道门 + 评审流水线全绿 — commit `d1fe4f09da6e9eea7b02256674566e1b1d018989`

## 下一步指令（给下一个会话 / M6）
1. 读 `CLAUDE.md` → 拉 `docs/工单/T-006*`（视野 / 渲染层）或新建。
2. 视野/迷雾：玩家可见区域随移动更新；**不得引入裸随机**（红线 #1）；渲染层改造要保证既有 79 例规格（尤其 `test_level.py` 的连通性判定与 `render()` 相关用例）不被破坏。
3. 复用 M5 的 `Game.rooms` 做「进房间点亮整间」这类室内照明；楼梯 `>` 与道具 `!` 的渲染优先级已定（楼梯 < 道具 < 怪物 < 玩家），改动渲染时保持。
4. 跑 `python scripts/gate.py` 全绿 → 更新本文件（含 commit）→ 提交。
5. 主题贯穿：视野可做成「蜘蛛感应（Spider-Sense）」——能感知半径内的敌人轮廓，与本作 MCU 荷兰弟版设定契合；但不得破坏现有红线与门禁。
6. 已决（2026-08-29）：`.workbuddy/`（AI 工作记忆目录，非源码）已加入评审流水线「范围审计」白名单 + `.gitignore`。注意该审计走文件系统 `ROOT.iterdir()`、不看 git，所以**只加 .gitignore 并不能消除告警**。
7. 已决（2026-08-29）：**默认构造 `Game(rng=...)` 仍是 M1 的固定教学图**，程序化楼层必须显式走 `Game.procedural(rng, depth=1)`。M1~M4 的 51 例规格都依赖那张 7×5 小图，别把它换掉。
8. 已决（2026-08-29）：平衡基线——M3 规则是「相邻即每回合挨打」，所以怪物攻击值必须压在 1~3；演示种子 `SEED=19`（三层都有怪且能清场）。改动怪物表或撒点密度后，请重跑 `python main.py` 确认演示仍能走完三层。

## 当前生效假设
- 假设 A：坐标 (x,y)，x 横向、y 纵向，原点左上。
- 假设 B：墙 `#` 不可入，地板 `.` 可入，玩家 `@` 唯一——且 `@` 在本作中即**蜘蛛侠（MCU 荷兰弟 / Tom Holland 版）**（见术语表）。
- 假设 C（M4 起）：道具是**实体层**，不改写 `grid`（`grid` 只存地形与 `@`）；地面道具渲染为 `!`，玩家/怪物优先显示。
- 假设 D（M4 起）：一格最多一个道具；背包满时拾取失败、道具留在地面（不自动替换/丢弃）。
- 假设 E（M5 起）：`grid` 只存地形与 `@`；楼梯同道具一样是「实体层」坐标（`Game.stairs`），渲染时才画成 `>`，不改写 `grid`。
- 假设 F（M5 起）：程序化楼层是**可选路径**——`Game(rng=...)` 默认仍是固定教学图，`Game.procedural(rng, depth=N)` 才生成楼层。
- 假设 G（M5 起）：下潜保留玩家 HP / 背包 / 纳米加成，只重置地图与实体；固定教学图没有楼梯 ⇒ `descend()` 恒为 False。
