# HANDOFF-T001 · 交接棒

> **为什么一直叫 T001？** 因为接力文件是「一根棒子」，不是「一张任务卡」：
> 工单（T-001…T-005）一任务一卡、每里程碑新建；接力棒全程只有这一根，
> 每个里程碑完成时在**本文件**上追加（当前状态 / 已完成含 commit / 下一步指令 / 生效假设）。
> 文件名里的 `T001` 是这根棒的**起点编号**（建仓那棒就是 T001），不是「只服务于 M1」。
> 所以：**不要按里程碑新建 HANDOFF-M6 之类**，继续在本文件更新即可；
> 只有当项目出现并行推进的两条线时，才需要另开一根棒（如 `HANDOFF-<分支名>`）。

## 当前状态
- 整体进度：M1 已完成（治理脚手架 + 格子移动）；M2 已完成（战斗系统）；M3 已完成（怪物 AI）；M4 已完成（道具与背包）；M5 已完成（程序化关卡）；M6 已完成（视野 / 渲染层）；M7 已完成（怪物视野与潜行）；M8 已完成（噪音与听觉）；**M9 已完成（主动制造响动 / 皇后区垃圾桶盖）**；**M10 已完成（ANSI 颜色高亮）**；**M11 已完成（光照衰减 / 明暗梯度）**；**M12 已完成（随身手电 / 动态光源）**；**M13 已完成（光照影响玩家自身视野）**；**M14 已完成（可开关房间灯 / 蛛网射灯拉链）**；**M15 已完成（怪物追击修正与攻击配平）**。
- **产品目标（2026-08-29 新增，已明确为 MCU 荷兰弟版）**：最新蜘蛛侠（Spider-Man）风格，**以 MCU 荷兰弟（Tom Holland）版蜘蛛侠为主角**——红蓝战衣/蛛网发射器/纽约都市基调；所有里程碑的美术/剧情/机制均围绕此主题（非官方 IP，属风格致敬/个人学习项目）。
- 最近一次更新：2026-08-30（M15 完成）

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

- [x] M7 怪物视野与潜行：`fov.py` 增 `MONSTER_SIGHT_RADIUS=7` 与 `monster_can_see`（**双向** Bresenham 视线 + 同房间互通，纯几何、零随机）；`tiles.py` 增 `UNAWARE="m"`；`Monster` 增警觉状态机（`alerted` / `alert_turns` / `last_seen` / `home` + `alert()` / `calm()`）；`Game` 增 `stealth` 开关（**默认关闭**）、`update_awareness` / `monster_can_see_player` / `can_sneak_attack` / `web_strike` / `_strike_path` / `hidden` / `alerted_monsters` / `unaware_monsters`；`player_attack` 在未察觉时触发**倒挂突袭**（伤害 × `SNEAK_ATTACK_MULT=2`、不挨反击、命中后转已察觉）；未察觉的 `chase` 怪**回巢**、`wander` 怪照旧游荡；渲染区分 `m`（未察觉）/ `M`（已察觉）；新增不变量 **#9 感知/潜行确定性**；`tests/test_stealth.py`（47 例），用例数 121→168，门禁四道门 + 评审流水线全绿；`main.py` 增 `--stealth`（默认关闭），实证 `python main.py` 与 M6 逐字节一致（仅图例一行因新增 `m` 而变） — commit `9ce33f3`

- [x] M8 噪音与听觉：新增 `src/rogue/sound.py`（`noise_field` 在 grid 上跑 Dijkstra——空地 1 / 墙 3、声源 0、超响度不入場、**越界不传播**；`noise_cost` / `noise_reaches` / `step_cost`，**纯几何零随机**）；`tiles.py` 增 `HEARD="~"`；`Monster` 增 `alert_cause`（`sight` / `sound` / `None`，`alert(pos, cause=)` 记录、`calm()` 清空）；`Game` 增 `noise` 开关（**默认关闭**）、`emit_noise` / `monsters_hearing` / `can_hear` / `heard_monsters` / `_monster_glyph`；四个声源接入点：蛛网拳 `NOISE_PUNCH=6`（玩家处）、倒挂突袭 `NOISE_SNEAK=2`（玩家处）、蛛网弹命中 `NOISE_STRUGGLE=7`（**被缠住的怪处**）、下潜落地 `NOISE_LANDING=8`（只在 `descend()`，不在 `load_level`）；走路/拾取/吃三明治/注射纳米强化剂**无声**；声源未必是玩家 ⇒ **调虎离山**成立；视听同时以视觉为准；新增不变量 **#10 噪音/听觉确定性**；新增 ADR-004；`tests/test_noise.py`（47 例），用例数 168→215，门禁四道门 + 评审流水线全绿；`main.py` 增 `--noise`（隐含 `--stealth`），实证 `python main.py` 与 `python main.py --stealth` 与 M7 **玩法日志逐字节一致**（唯一差异是图例那一行多了 `~`） — commit `54a173d`
- [x] M9 主动制造响动：皇后区垃圾桶盖（诱饵道具）+ 投掷几何（`can_throw` / `throw_decoy`，纯几何零随机）+ 主动调虎离山；`use_item` 增 `target` 参数（诱饵专用，其余三件道具向后兼容）；诱饵只在 `noise` 开关下、开局脚边供给、不进 `ITEM_KEYS` 掉落池（零随机扰动）；`spawn_item` 在玩家脚下格允许「换掉脚下物」（仍保持一格一物 #5）；新增不变量 **#11 主动制造响动 / 投掷确定性**；ADR-005；`tests/test_decoy.py`（30 例），用例数 215→245，门禁四道门 + 评审流水线全绿；默认/潜行两条演示与 M8 逐字节一致、`--noise` 演示主动调虎离山（seed 19 下甩盖 3 次、引开 5/4 只敌人） — commit `f5eb8a9`

- [x] M10 ANSI 颜色高亮：纯展示层上色（`src/rogue/color.py` 的 `colorize` / `should_color`）+ `main.py` 三处 `print(game.render())` 改为 `print(colorize(game.render(), color_on))`；`--color` / `--no-color` 显式开关，默认 TTY 自动上色、管道降级、遵守 NO_COLOR；图例/状态行不上色；`tests/test_color.py`（15 例）；ADR-006；测试数 245 → 260，门禁四道门 + 评审流水线全绿；三条演示动作日志与 M9 逐字节一致（颜色只包在地图网格外层）— commit `2d39de9`
- [x] M11 光照衰减：纯几何光照场（`src/rogue/light.py`：房间中心固定灯 `ROOM_LIGHT_RADIUS=9` + 玩家随身微光 `PLAYER_GLOW_RADIUS=4`，光遇墙即断、距离衰减，每格落「暗/昏暗/明」三档）+ 明暗梯度（`color.py` 的 `colorize` 按光照压暗暗处地板）+ 暗处缩短怪物感知半径（`Game.light_level_at` 按怪物所在格光照取 `MONSTER_SIGHT_DARK=2`/`DIM=4`/`LIT=7`，均 ≤ 7）；新 `light` 开关（**默认关闭、opt-in**，`Game(..., light=True)` / `main.py --light`）；`render()` 字形一字不差、默认/潜行/听觉三条演示不加 `--light` 时一字节不变；`tests/test_light.py`（28 例）；ADR-007；不变量 #12（光照衰减：纯几何零随机、默认关闭、只缩短不放大）；测试数 260 → 288，门禁四道门 + 评审流水线全绿（无 HIGH）— commit `a73fd31`
- [x] M12 随身手电：可开关动态光源（`src/rogue/game.py` 的 `toggle_flashlight`，默认关闭、opt-in；`--flashlight` 隐含 `--light`）+ 玩家处追加半径 `FLASHLIGHT_RADIUS=6` 的随身光源（开灯照亮四周、关灯摸黑潜行；**双刃剑**：照亮自己也让自己更易被暗处的怪察觉）+ 暗处只缩短怪物感知半径（恒 ≤ 7，#9 对称不破）；`render()` 字形一字不差、M1~M11 不加 `--flashlight` 时一字节不变；`tests/test_flashlight.py`（18 例）；ADR-008；不变量 #13（随身手电：纯几何零随机、默认关闭、只缩短不放大、toggle 零副作用）；测试数 288 → 306，门禁四道门 + 评审流水线全绿（无 HIGH），六条演示（` ` / `--stealth` / `--noise` / `--light` / `--flashlight` / `--flashlight --stealth`）均通关 — commit `a063389`
- [x] M13 光照影响玩家自身视野：`fov.py` 新增 `PLAYER_SIGHT_DARK=2` / `PLAYER_SIGHT_DIM=4` 常量与 `player_sight_radius(light_lvl)` 函数；`visible_tiles` 扩展可选 `light_field` 参数——光照开启时逐格按**目标格光照**算有效视野半径（亮处易见、暗处难见）；`Game.update_fov` 光照开启且视野开启时传 `light_field` 给 `visible_tiles`；**按目标格光照算**（不按玩家所在格——玩家微光让脚下恒 LIT，按玩家所在格算退化为「视野永远 8」）；走廊暗处玩家只能看清微光区（约 3~4 格）、房间亮处视野恢复（8 格）、手电开灯照亮暗处恢复视野（双刃性更立体）；复用 `light` 开关不新增开关、只在 `light=True` 且 `fov=True` 时生效；纯几何零随机、默认关闭（light=False 或 fov=False ⇒ M6 原逻辑，M1~M12 一字节不变）；有效半径恒 ≤ `SIGHT_RADIUS`(8)，同档位下 `player_r ≥ monster_r`（DARK 2=2 / DIM 4=4 / LIT 8>7）⇒ #9 硬性质不破；`render()` 字形一字不差（可见集合变小但不改字形，#8 延伸）；进房间点亮整间规则保留；`tests/test_light_fov.py`（36 例）；ADR-009；不变量 #14（光照影响玩家视野：纯几何零随机、默认关闭、按目标格光照、只缩短不放大、#9 对称不破）；测试数 306 → 342，门禁四道门 + 评审流水线全绿（无 HIGH），七条演示（默认 / `--stealth` / `--noise` / `--light` / `--light --stealth` / `--flashlight` / `--flashlight --stealth`）均通关 — commit `029f290`
- [x] M14 可开关房间灯：`Game` 新增 `switched_lights: set[Tile]`（已关灯的房间中心坐标）+ `can_toggle_light(x,y)` / `toggle_light(x,y)` / `light_is_on(x,y)`；蛛网射中房间中心灯的拉链翻转该房间的灯（关灯变暗 / 开灯恢复）；`_light_sources()` 跳过 `switched_lights` 里的房间 ⇒ 关灯只移除光源（不新增）⇒ 光照场只变暗或恢复、有效半径恒 ≤ `SIGHT_RADIUS`(8) ⇒ #9/#12/#14 不破；四条硬约束：光照开启 + 目标是房间中心 + 切比雪夫 ≤ `WEB_LIGHT_RANGE=6`（含脚下）+ 玩家看得见灯（`has_line_of_sight`）；M8 联动：拉链轻响 `NOISE_TOGGLE_LIGHT=3` 从**灯处**传出（不在玩家处）⇒ 调虎离山成立（比垃圾盖 9 轻、只惊动近处的人）；`toggle_light` 只翻集合 + 重算场（`update_fov`），不改写 `grid`/HP/背包/怪物状态（与 `toggle_flashlight` 同一零副作用哲学）；换层（`load_level`）重置 `switched_lights`；`render()` 字形一字不差（关灯只改光照场与可见集合，不改字形，#8 延伸）；复用 `light` 开关不新增开关、只在 `light=True` 时有意义（`light=False` ⇒ `toggle_light` 恒返回 False、no-op）；`main.py` 在 `--light --stealth` 下主动射灭未察觉敌人所在房间的灯（演示 seed 19 下共关 5 盏灯、三层均通关）；`tests/test_light_switch.py`（42 例，1 skip）；ADR-010；不变量 #15（可开关房间灯：纯几何零随机、默认关闭、只移除光源不新增、声源在灯处、toggle 零副作用、换层重置）；测试数 342 → 384，门禁四道门 + 评审流水线全绿（无 HIGH），七条演示均通关，不加 `--light` 的前三条与 M13 逐字节一致 — commit `a5b991d`

## 下一步指令（给下一个会话 / M16）
0. 已完成的 M15 关键结论（**先读，能省半天**）：
   - **默认追击统一走 close_in=True**：`_step_toward` 现在调用 `_step_toward_point(candidates, (px,py), close_in=True)`，与潜行分支一致。曼哈顿平局时切比雪夫更小的那一步才是真的在逼近；只比曼哈顿会选「横跳」那步 ⇒ 玩家轴向往复时怪锁轴震荡、永不贴上（seed 19 实测锁死 30+ 回合）。
   - **配平各降 1（1~3 → 0~2）**：`MONSTER_TABLE = (0,0,1,1,2,1)`。修复让怪物更可靠地贴上 ⇒ 整体威胁上升；实测三态：旧追击+旧攻击 26/30（HANDOFF 现状）、新追击+旧攻击 **22/30**（只修不配平会掉）、新追击+新攻击 **默认 30/30 / 潜行 28/30**（配平后，≥ 基线）。
   - **0 伤害杂鱼是 harmless fodder**：街头小混混 / 迷途无人机攻击 0，仍占位、可被杀死、清场才能下潜，只是挠一下不破防（主题：街头小混混够不到你）。这是「各降 1」配平的代价，刻意保留。
   - **确定性不变**：修复与配平均纯几何、零随机，同 seed + 同输入 ⇒ 同结果（#2）。不变量 #9（感知对称）未触及、未破。
   - **默认追击行为改变是预期的**：此前 M1~M14 的「逐字节一致」保证只适用于 opt-in 开关（fov/stealth/noise/light）；默认追击是核心玩法，修正它就是本里程碑目的，不要求与旧演示逐字节相同。stealth 模式不受影响（它早已用 close_in=True）。
   - **验证四件套全绿**：`python scripts/gate.py`（389 例，+5）、`python scripts/balance_check.py`（默认 30/30、潜行 28/30）、`python main.py`（seed 19 第 171 回合清场 HP 18/20）、`python main.py --stealth`（第 225 回合 HP 18/20，均 ≤ 240 上限）。
1. 读 `CLAUDE.md` → 拉 `docs/工单/T-016*` 或新建。下一步候选（接 M15，均来自 HANDOFF 后续项登记）：
   - **让光照也影响蜘蛛感应半径**（目前 `SPIDER_SENSE_RADIUS=4` 穿墙预警不受光照约束；
     若要做需让感应半径随光照衰减，但感应是超能力——主题上是否该受光照约束需先定调）；
   - **环境光照场与完整光照场分离**（目前 `light_field` 含微光，M13 用它按目标格算视野半径；
     若分离出「不含微光」的环境光照场，可让「玩家在亮处看暗处」更精确——但复杂度翻倍）；
   - **可破坏的灯**（M14 是翻转式，可破坏 = 一次性不可恢复；主题上即蛛网射碎灯泡）；
   - **灯开关作为独立实体**（墙上的开关 tile，与灯分离——更真实但需新实体类型 + 新渲染字形）。
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
17. 已决（2026-08-29，M8）：**听觉默认关闭**（`Game(..., noise=False)` ⇒ `emit_noise` 是空操作、
    返回空表，只有视觉一条感知通道）。与第 7/9/12 条同一哲学。实测 `python main.py`
    与 `python main.py --stealth` 的**玩法日志**与 M7 逐字节一致（唯一差异是图例那一行多了 `~`）。
18. 已决（2026-08-29，M8）：**声音沿走廊「绕」着走**（`src/rogue/sound.py`，Dijkstra 最短传播代价
    空地 1 / 墙 3）。与视线（遇墙即断）的本质差别：三格厚的墙不如绕下面的走廊便宜
    （实测 12 < 14）⇒ 拐角后面的房间听不见、一墙之隔只是「闷」（白丢 2 格传播距离）。
19. 已决（2026-08-29，M8）：**声源未必是玩家**——被蛛网弹缠住的怪自己挣扎出声（`NOISE_STRUGGLE=7`，
    声源在**它**那儿），同伴被引向它而不是你 ⇒ **调虎离山**。这是听觉唯一的「解法型」收益，
    别把它简化成「又一条让怪发现你的通道」。
20. 已决（2026-08-29，M8）：**视听同时发生时以视觉为准**——视觉给实时位置、听觉只给声源，
    `update_awareness` 在世界回合开始时跑，会把「只是听见」改写回「看见了」。
    否则会出现「隔着走廊明明看得见你、却朝反方向的声源走」的怪象。
21. 已决（2026-08-29，M8）：**落地声只在 `descend()`**，不在 `load_level`——
    开局那一层你已经在楼里了；放 `load_level` 会让「手搓一张图做单测」凭空多一次落地声。
22. 已决（2026-08-29，M8）：**走路无声**，只有动作会响（主题：蜘蛛侠落地无响）。
    响度是常量表、不掷骰（`NOISE_PUNCH=6` / `NOISE_SNEAK=2` / `NOISE_STRUGGLE=7` / `NOISE_LANDING=8`）。
    蛛网拳的响度（6）刻意略小于怪物感知半径（7），落地声（8）略大。
23. 已决（2026-08-29，M8）：**平衡基线再补一条**——听觉开启后演示回合数进一步变长
    （seed 19：默认 ~95、潜行 ~165、**听觉 ~208**），仍在 `TURNS_PER_LEVEL * MAX_DEPTH = 240` 上限内。
    改动怪物表 / 撒点密度 / 响度后，请重跑 `python main.py`、`--stealth`、`--noise` **三条**。
25. 已决（2026-08-29，M10）：**颜色是纯展示层**，只经 `colorize()` 包裹 `render()` 输出，
    不进 `Game` / `render()`（与 `fov`/`stealth`/`noise` 的「改变显示什么」区分：颜色只改变「怎么画」）。
    默认 TTY 自动上色、管道/重定向降级为纯文本、遵守 `NO_COLOR`；`--color` / `--no-color` 可强制。
    `render()` 输出一字不差 ⇒ 既有 245 例规格与三条演示（默认/潜行/听觉）动作日志逐字节一致，零风险。
24. 已决（2026-08-29，M8）：新增不变量 **#10 噪音/听觉确定性**——传播纯几何、不消耗 `RandomSource`；
    「是否被听到」只经 `Monster.alert(cause=CAUSE_SOUND)` 这一**唯一入口**生效；听觉默认关闭。
    机器判定见 `tests/test_noise.py::TestNoiseDeterminism` 与 `::TestNoiseSources`。

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
- 假设 L（M8 起）：`Monster.alert_cause` 是「它为什么被惊动」的**唯一**记录（`sight` / `sound` / `None`）。
  被**直接命中**的怪记成「看见」（它正在挨打，不可能不知道人在哪），只有听见动静的才记成「听见」
  ⇒ 画面上 `~` 只出现在「还没看见你」的敌人身上。
- 假设 M（M8 起）：噪音**只惊动、不增伤**。听觉是感知层不是战斗层，被声音引来的怪
  仍要走过来才打得到你，与目视发现的怪完全同权。
- 假设 N（M8 起）：声音传播**越界不参与**（声源在界外 ⇒ 谁也听不见），且**墙是闷不是隔音**
  （代价 3 而非 ∞）——完全隔音会让「一墙之隔」变成绝对安全，听觉就退化成第二套视线。
- 假设 O（M11 起）：光照是**纯几何、零随机**（`src/rogue/light.py`：光源 = 房间中心固定灯 + 玩家微光，
  光遇墙即断、距离衰减）；它**只缩短怪物感知半径**（暗 2 / 昏暗 4 / 明 7，恒 ≤ 7），
  不放大、不引入随机 ⇒ 「怪看得见你 ⇒ 你看得见它」的硬性质不破；明暗梯度只在 `color.py`
  的 `colorize` 上色层（不改 `render()` 字形）；光照**默认关闭**（`light=False` ⇒ 一字节不变）。
- 假设 P（M12 起）：随身手电是**纯几何、零随机**（`src/rogue/game.py` 的 `toggle_flashlight`：
  翻标志 + 重算 `light_field`，不消耗 `RandomSource`、不改写玩法状态、换层保留，与 HP / 背包同属跨层状态）；
  它**只在玩家处追加一个半径 `FLASHLIGHT_RADIUS` 的光源**，同样只缩短怪物感知半径（恒 ≤ 7），
  不放大、不引入随机 ⇒ #9 对称硬性质不破；手电是**双刃剑**——开灯照亮自己也让自己更易被暗处的怪察觉，
  关灯退回微光、摸黑潜行更稳；手电**默认不装备**（`flashlight=False` ⇒ 即使 `light=True` 也与 M11 逐字节一致）。
- 假设 Q（M13 起）：光照影响玩家自身视野是**纯几何、零随机**（`fov.visible_tiles` 的 `light_field` 分支：
  逐格查目标格光照 + 算 `player_sight_radius` + 判 `has_line_of_sight`，不消耗 `RandomSource`、不改写任何状态）；
  它**按目标格光照算**玩家视野半径（不是玩家所在格——微光让脚下恒 LIT，按所在格算退化为「视野永远 8」）；
  只在 `light=True` 且 `fov=True` 时生效（`fov=False` 时全图渲染不用 `visible`，`light=False` 时无光照场）；
  有效半径恒 ≤ `SIGHT_RADIUS`(8)（暗处缩短、亮处不变），同档位下 `player_r ≥ monster_r` ⇒ #9 对称硬性质不破；
  走廊暗处玩家只能看清微光区（约 3~4 格）、房间亮处视野恢复（8 格）；手电开灯照亮暗处恢复视野（双刃性更立体）。
- 假设 R（M14 起）：可开关房间灯是**纯几何、零随机**（`game.py` 的 `toggle_light`：
  翻 `switched_lights` 集合 + 重算光照场/可见集合（`update_fov`）+ 发出轻响（`emit_noise`），
  不消耗 `RandomSource`、不改写 `grid`/HP/背包/怪物状态，与 `toggle_flashlight` 同一零副作用哲学）；
  它**只移除光源**（`_light_sources` 跳过 `switched_lights` 里的房间中心），不新增光源
  ⇒ 光照场只变暗或恢复，有效半径恒 ≤ `SIGHT_RADIUS`(8) ⇒ #9/#12/#14 对称硬性质不破；
  关灯是**双刃**——暗处的怪看不远、你也看不远（M11+M13 联动）；拉链轻响从**灯处**传出
  （不在玩家处）⇒ 调虎离山成立（M8 联动）；可开关房间灯**默认无意义**（`light=False` ⇒
  `toggle_light` 恒返回 False、no-op，与 M1~M13 逐字节一致）；换层（`load_level`）重置 `switched_lights`。
