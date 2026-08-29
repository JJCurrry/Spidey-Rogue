# HANDOFF-T001 · 交接棒

> **为什么一直叫 T001？** 因为接力文件是「一根棒子」，不是「一张任务卡」：
> 工单（T-001…T-005）一任务一卡、每里程碑新建；接力棒全程只有这一根，
> 每个里程碑完成时在**本文件**上追加（当前状态 / 已完成含 commit / 下一步指令 / 生效假设）。
> 文件名里的 `T001` 是这根棒的**起点编号**（建仓那棒就是 T001），不是「只服务于 M1」。
> 所以：**不要按里程碑新建 HANDOFF-M6 之类**，继续在本文件更新即可；
> 只有当项目出现并行推进的两条线时，才需要另开一根棒（如 `HANDOFF-<分支名>`）。

## 当前状态
- 整体进度：M1 已完成（治理脚手架 + 格子移动）；M2 已完成（战斗系统）；M3 已完成（怪物 AI）；M4 已完成（道具与背包）；M5 已完成（程序化关卡）；M6 已完成（视野 / 渲染层）；**M7 已完成（怪物视野与潜行）**。
- **产品目标（2026-08-29 新增，已明确为 MCU 荷兰弟版）**：最新蜘蛛侠（Spider-Man）风格，**以 MCU 荷兰弟（Tom Holland）版蜘蛛侠为主角**——红蓝战衣/蛛网发射器/纽约都市基调；所有里程碑的美术/剧情/机制均围绕此主题（非官方 IP，属风格致敬/个人学习项目）。
- 最近一次更新：2026-08-29（M7 完成）

## 已完成（含 commit）
- [x] 治理脚手架（七件套 + 流水线 seed-guard）— commit `fdfaa30716477ab5c7b7e6435b5ee716a4d8b402`
- [x] M1 格子地图 + 玩家移动 + 单测 — 同 commit
- [x] 门禁实证：seed-guard 拦截裸 random；gate 四道门全绿
- [x] 产品主题明确为 MCU 荷兰弟（Tom Holland）版蜘蛛侠（四件制品同步）— commit `b202213`
- [x] M2 战斗系统：玩家/怪物 HP、`player_attack`（蛛网拳，伤害=基础+Seed 浮动）、HP 钳制 #3、确定性 #2、随机仅经 `RandomSource` #1、`spawn_monster` 手摆怪物、移动不可穿怪、`tests/test_combat.py`（10 例）— commit `defb2c9`
- [x] M3 怪物 AI：chase（贪心追击，纯确定性）/ wander（随机游走，随机仅经 `RandomSource`）；相邻反击（固定伤害，HP 钳制 #3）；AI 移动不可越界/穿墙/踩玩家/踩怪（#4）；`monster_turn` 固定顺序推进（#2）；`tests/test_ai.py`（11 例），用例数 17→28，门禁四道门全绿 — commit `9d65c74f324ed3a0672df37eb566bc7e4e41d0f7`

- [x] M4 道具与背包：`Item` 实体 + 地面 `Game.items` / 背包 `Game.inventory`（容量 5）；`spawn_item` / `item_at` / `pick_up` / `use_item`；三件主题道具（梅姨的三明治 / 蛛网发射器备用芯 / 斯塔克纳米强化剂）；怪物阵亡掉落（rng.chance + rng.choice，#1/#2）；`Monster.stunned` 接入 `monster_act`（被缠住跳过整次行动、不消耗 rng）；新增不变量 #5 背包容量上限、#6 HP 不超上限；`tests/test_items.py`（23 例），用例数 28→51，门禁四道门全绿 — commit `32814981110dd8330ee3173824d00afb44f922ad`

- [x] M5 程序化关卡：新增 `src/rogue/level.py`（`Room` / `Level` / `generate_level`，拒绝采样摆房间 + L 形走廊成链 + 洪泛封填死口袋）与 `src/rogue/tiles.py`（格子字符常量，消除 game.py 与 level.py 的字面量重复）；`Game` 新增 `load_level` / `_populate_level` / `can_descend` / `descend` / `procedural` 工厂与 `depth` / `level_name` / `rooms` / `stairs`（**楼梯是坐标、不改写 grid**）；10 个纽约地标楼层名按层号循环；怪物登记表 6 种（按层解锁 + HP 随层成长）；新增不变量 **#7 地图连通性**（原「待生效」转正，机器判定 30 seed 洪泛）；`tests/test_level.py`（28 例），用例数 51→79，门禁四道门 + 评审流水线全绿 — commit `d1fe4f09da6e9eea7b02256674566e1b1d018989`

- [x] M6 视野 / 渲染层：新增 `src/rogue/fov.py`（Bresenham 射线判遮挡 + `SIGHT_RADIUS=8` + 「进房间点亮整间」复用 `Game.rooms` + 蜘蛛感应 `SPIDER_SENSE_RADIUS=4` 穿墙只给 `?` 轮廓，**纯几何零随机、不消耗 rng**）；`tiles.py` 增 `UNSEEN` / `SENSE`；`Game` 增 `fov` 开关（**默认关闭** ⇒ 既有 79 例规格零改动全绿）、`visible` / `explored` / `update_fov` / `is_visible` / `is_explored` / `visible_monsters` / `spider_sense`，`render()` 拆成 `_render_full`（原路径）/ `_render_fog`（迷雾：未探索空白、记忆留地形+楼梯+道具、怪物只在可见时画）两条；换层清空记忆；新增不变量 **#8 渲染纯净性**；新增 ADR-002（视野设计决策）；`tests/test_fov.py`（42 例），用例数 79→121，门禁四道门 + 评审流水线全绿；`main.py` 默认开迷雾并印图例、`--no-fog` 切回全图，实证 `diff` 两种模式的行动日志**零差异**（视野不扰动随机序列 #2）— commit `ae5c7b6`

- [x] M7 怪物视野与潜行：`fov.py` 增 `MONSTER_SIGHT_RADIUS=7` 与 `monster_can_see`（**双向** Bresenham 视线 + 同房间互通，纯几何、零随机）；`tiles.py` 增 `UNAWARE="m"`；`Monster` 增警觉状态机（`alerted` / `alert_turns` / `last_seen` / `home` + `alert()` / `calm()`）；`Game` 增 `stealth` 开关（**默认关闭**）、`update_awareness` / `monster_can_see_player` / `can_sneak_attack` / `web_strike` / `_strike_path` / `hidden` / `alerted_monsters` / `unaware_monsters`；`player_attack` 在未察觉时触发**倒挂突袭**（伤害 × `SNEAK_ATTACK_MULT=2`、不挨反击、命中后转已察觉）；未察觉的 `chase` 怪**回巢**、`wander` 怪照旧游荡；渲染区分 `m`（未察觉）/ `M`（已察觉）；新增不变量 **#9 感知/潜行确定性**；`tests/test_stealth.py`（47 例），用例数 121→168，门禁四道门 + 评审流水线全绿；`main.py` 增 `--stealth`（默认关闭），实证 `python main.py` 与 M6 逐字节一致（仅图例一行因新增 `m` 而变） — commit `<待回填>`

## 下一步指令（给下一个会话 / M8）
0. 已完成的 M7 关键结论（**先读，能省半天**）：
   - **整数 Bresenham 不对称**：(1,1)→(3,2) 途经 (2,1)，(3,2)→(1,1) 途经 (2,2)。
     所以怪物感知必须**双向**判视线，否则会出现「隔着拐角看得见你、你却看不见它」的幽灵猎手。
     双向后换来硬性质：**怪物看得见你 ⇒ 你一定看得见它**（怪物半径 7 < 玩家视野 8）。
   - **只走一步摸不到「看不见你的怪」**：攻击要求切比雪夫相邻，而相邻格之间没有中间格 ⇒ 必被看见；
     只走一步则出发点到怪物曼哈顿距离恒为 2，那条线上唯一的中间格正是落脚点本身——
     要挡视线就得把落脚点变成墙。所以摆荡突袭射程 `WEB_STRIKE_RANGE=2`（推导见 ADR-003）。
   - **潜行成立靠「感知的更新时机」**：感知只在世界回合**开始**时更新一次，
     于是玩家回合内「从视野外扑到面前」天然构成突袭窗口，不需要朝向 / 背身几何。
   - **M3 的老追击有「原地打转」旧疾**：`_step_toward` 只比曼哈顿距离，平局时可能永远贴不上来。
     M7 的潜行分支已用切比雪夫二次关键字修正；**老路径刻意没改**——改了会改写 M6 既有演示行为。
     若要修，请单独开单并重新基线化 `python main.py` 的输出。
1. 读 `CLAUDE.md` → 拉 `docs/工单/T-008*`（光照衰减 / 颜色高亮 / 噪音系统）或新建。
2. 若要动渲染：**默认路径必须是「不改既有规格」的那条**——M6 的教训是「新能力默认 opt-in」
   （`fov=False` 走 `_render_full`，`fov=True` 才走 `_render_fog`）。加 ANSI 颜色也一样：
   默认着色必须保证 `test_game/test_items/test_level` 里 `assertIn("@"/"!"/">", render())`
   这类断言仍然成立（或另加开关）。
3. 渲染优先级已定：`?`（蜘蛛感应）< 楼梯 `>` < 道具 `!` < 怪物 `M` < 玩家 `@`；改渲染时保持。
4. 跑 `python scripts/gate.py` 全绿 → 更新本文件（含 commit）→ 提交。
5. 主题贯穿：本作是 MCU 荷兰弟版蜘蛛侠，新机制优先找对应设定（如潜行 → 蛛网暗杀 / 倒挂突袭）。
6. 已决（2026-08-29）：`.workbuddy/`（AI 工作记忆目录，非源码）已加入评审流水线「范围审计」白名单 + `.gitignore`。注意该审计走文件系统 `ROOT.iterdir()`、不看 git，所以**只加 .gitignore 并不能消除告警**。
7. 已决（2026-08-29）：**默认构造 `Game(rng=...)` 仍是 M1 的固定教学图**，程序化楼层必须显式走 `Game.procedural(rng, depth=1)`。M1~M4 的 51 例规格都依赖那张 7×5 小图，别把它换掉。
8. 已决（2026-08-29）：平衡基线——M3 规则是「相邻即每回合挨打」，所以怪物攻击值必须压在 1~3；演示种子 `SEED=19`（三层都有怪且能清场）。改动怪物表或撒点密度后，请重跑 `python main.py` 确认演示仍能走完三层。
9. 已决（2026-08-29，M6）：**视野默认关闭**（`Game(..., fov=False)` ⇒ `_render_full` 全图）。
   原因：`test_level.py::test_render_shows_stairs` 等既有规格断言「全图可见」，默认开迷雾会打破它们，
   而熔断②禁止改测试凑绿。新能力一律「显式 opt-in」，与第 7 条同一哲学。
10. 已决（2026-08-29，M6）：**视野是纯几何、零随机**（`src/rogue/fov.py`，Bresenham 射线 + 半径 + 房间照明），
    不消耗 `RandomSource` ⇒ 开不开视野玩法结果完全一致。实证方法：
    `python main.py | grep -E "^-- " > a.log` 与 `python main.py --no-fog | ... > b.log` 后 `diff`，应**零差异**。
    任何往视野里加随机的改动都要先跑这个 diff。
11. 已决（2026-08-29，M6）：新增不变量 **#8 渲染纯净性**——`render()` 只依赖地形 + 实体 + 玩家位置，
    不改写任何游戏状态（唯一例外：`explored` 记忆单调增长）。机器判定见 `tests/test_fov.py::TestRenderPurity`。
12. 已决（2026-08-29，M7）：**潜行默认关闭**（`Game(..., stealth=False)` ⇒ `Monster.alerted` 恒为 True，
    怪物仍是 M3 的全知追击）。与第 7/9 条同一哲学。实测 `python main.py` 的输出与 M6 逐字节一致
    （唯一差异是图例那一行多了 `m` 的说明），既有 121 例规格零改动全绿。
13. 已决（2026-08-29，M7）：**怪物感知纯几何、零随机**，且**双向**判视线（Bresenham 不对称，见上面第 0 条）。
    双向换来「怪物看得见你 ⇒ 你一定看得见它」，机器判定见
    `tests/test_stealth.py::TestMonsterSight::test_anything_that_sees_you_you_can_see`。
14. 已决（2026-08-29，M7）：**摆荡突袭射程 = 2 步**，不是手感调参而是几何推导的结果（见 ADR-003）。
    改动射程前请先重读那条推导，射程 1 会让主动潜行彻底失效。
15. 已决（2026-08-29，M7）：新增不变量 **#9 感知/潜行确定性**——感知不消耗 `RandomSource`、
    突袭倍率是确定性常数、潜行默认关闭。机器判定见 `tests/test_stealth.py::TestStealthDeterminism`。
16. 已决（2026-08-29，M7）：**平衡基线补充**——潜行开启后演示回合数会变长（怪物会跑、要摸哨，
    seed 19 下约 165 回合跑完三层，仍在 `TURNS_PER_LEVEL * MAX_DEPTH = 240` 上限内）。
    改动怪物表 / 撒点密度 / 摆荡射程后，请重跑 `python main.py` **与** `python main.py --stealth`
    确认两条路都能走完三层。

## 当前生效假设
- 假设 A：坐标 (x,y)，x 横向、y 纵向，原点左上。
- 假设 B：墙 `#` 不可入，地板 `.` 可入，玩家 `@` 唯一——且 `@` 在本作中即**蜘蛛侠（MCU 荷兰弟 / Tom Holland 版）**（见术语表）。
- 假设 C（M4 起）：道具是**实体层**，不改写 `grid`（`grid` 只存地形与 `@`）；地面道具渲染为 `!`，玩家/怪物优先显示。
- 假设 D（M4 起）：一格最多一个道具；背包满时拾取失败、道具留在地面（不自动替换/丢弃）。
- 假设 E（M5 起）：`grid` 只存地形与 `@`；楼梯同道具一样是「实体层」坐标（`Game.stairs`），渲染时才画成 `>`，不改写 `grid`。
- 假设 F（M5 起）：程序化楼层是**可选路径**——`Game(rng=...)` 默认仍是固定教学图，`Game.procedural(rng, depth=N)` 才生成楼层。
- 假设 G（M5 起）：下潜保留玩家 HP / 背包 / 纳米加成，只重置地图与实体；固定教学图没有楼梯 ⇒ `descend()` 恒为 False。
- 假设 H（M6 起）：视野是**渲染层**概念，不是玩法概念——它不参与移动/战斗/AI 的任何判定，
  只决定画面上画什么。怪物 AI 仍按 M3 行为追击，不存在「怪物看得见玩家才追」。
- 假设 I（M6 起）：`grid` 里只有 `#` / `.` / `@`（外加渲染层的 `M` / `m` / `!` / `>` / `?` / 空白，均不写回 grid）；
  `explored` / `visible` 是 `Game` 上的坐标集合，跟着地图走，**换层即清空**。
- 假设 J（M7 起）：`Monster.alerted` 是「怪物是否发现玩家」的**唯一**判定入口。
  潜行关闭时它恒为 True（怪物全知追击，M1~M6 行为不变）；潜行开启时由几何判定，
  且**只在世界回合开始时更新一次** ⇒ 玩家回合内的状态是「上一回合末的快照」，
  这就是倒挂突袭的时间窗口。
- 假设 K（M7 起）：未察觉 ≠ 无敌。相邻即被打（M3 规则不变）、同房间即被发现（房间里没处躲）；
  潜行的收益是「先手一击」，不是「敌人变瞎」。
