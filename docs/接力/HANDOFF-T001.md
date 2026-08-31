# HANDOFF-T001 · 交接棒

> **为什么一直叫 T001？** 因为接力文件是「一根棒子」，不是「一张任务卡」：
> 工单（T-001…T-005）一任务一卡、每里程碑新建；接力棒全程只有这一根，
> 每个里程碑完成时在**本文件**上追加（当前状态 / 已完成含 commit / 下一步指令 / 生效假设）。
> 文件名里的 `T001` 是这根棒的**起点编号**（建仓那棒就是 T001），不是「只服务于 M1」。
> 所以：**不要按里程碑新建 HANDOFF-M6 之类**，继续在本文件更新即可；
> 只有当项目出现并行推进的两条线时，才需要另开一根棒（如 `HANDOFF-<分支名>`）。

## 当前状态
- 整体进度：M1 已完成（治理脚手架 + 格子移动）；M2 已完成（战斗系统）；M3 已完成（怪物 AI）；M4 已完成（道具与背包）；M5 已完成（程序化关卡）；M6 已完成（视野 / 渲染层）；M7 已完成（怪物视野与潜行）；M8 已完成（噪音与听觉）；**M9 已完成（主动制造响动 / 皇后区垃圾桶盖）**；**M10 已完成（ANSI 颜色高亮）**；**M11 已完成（光照衰减 / 明暗梯度）**；**M12 已完成（随身手电 / 动态光源）**；**M13 已完成（光照影响玩家自身视野）**；**M14 已完成（可开关房间灯 / 蛛网射灯拉链）**；**M15 已完成（怪物追击修正与攻击配平）**；**M16 已完成（可破坏的房间灯 / 蛛网射碎灯泡，一次性不可逆）**；**M17 已完成（环境光照场与完整光照场分离 / ambient_field 与 light_field 双场，行为零回归）**；**M18 已完成（怪物感知改用环境场 / 仅房间灯+手电、排除被动微光，行为零回归）**；**M19 已完成（灯开关独立实体 / 墙边开关与天花板灯具分离，`LightSwitch` 实体 + 平行 switch API 翻同一份 `switched_lights`/`destroyed_lights`，行为零回归）**；**M20 已完成（光照影响蜘蛛感应半径 / M6 穿墙预警 `SPIDER_SENSE_RADIUS=4` 改为随目标格光照衰减——暗 2 / 昏暗 3 / 明 4，与 M11 怪物感知、M13 玩家视野形成「黑暗三重削弱」对称；纯几何零随机、默认关闭、零回归；28 例测试全绿（478→506））**；**M21 已完成（可键盘操作玩法 / `--play` 进入交互模式，bump-to-attack + 操作说明内置，纯几何零随机、默认仍是脚本 demo 零回归；15 例测试全绿（506→521））**；**M22 已完成（Pygame GUI 渲染层 / `src/rogue/render_pygame.py` 的 `PygameRenderer` 只读 `Game` 公开状态、逐帧画窗口、`run(_handle_key)` 与 `--play` 终端路径同构；`main.py` 新增 `--gui`（延迟 import、opt-in），`--play` 终端模式保留作 headless 回归基线；引入首个第三方依赖 `pygame`（`requirements.txt`）；纯几何零随机、不改 `Game` 一字（#1/#2/#8 延伸）、GUI 与终端对同 seed+同输入序列产生同结果（#2）；12 例测试全绿（521→533））**；**M23 已完成（Spider-Man 主题化 GUI 渲染 / 纯程序化美术，8 例测试全绿 533→541）**；**M24 已完成（主题美术再升级 · 动画+美术+音效 / `self.frame` 驱动帧动画 + 程序化音效，9 例测试全绿 541→550）**；**M25 已完成（Boss 战与胜利条件闭环 / `--boss` 最终层刷绿魔、击败才算通关；`Monster.boss` + `Game.boss_depth` opt-in、纯几何零随机不占 rng、14 例测试全绿 550→564）**；**M26 已完成（存档 / 读档 / `Game.to_dict`/`apply_state`/`from_dict`/`save`/`load`/`load_into` + `RandomSource.get_state/set_state` + `main.py` 大写 `S`/`L` 交互存读档；保存「seed + PRNG 内部状态 + 全部玩法状态」，确定性不破（同存档+同后续输入⇒同终态），opt-in 默认零回归；10 例测试全绿 564→574）**；**M27 已完成（序列帧 Sprite / `tiles/*.png` 确定性烘焙 20 张地形序列帧，运行时优先加载、缺文件回退同款程序化，视觉与 M24 逐像素一致、零回归；4 例测试全绿 574→578）**；**M28 已完成（网页化 Pygbag / `web.py` 浏览器入口 + `PygameRenderer.async_run` 异步主循环 + 构建脚本 + 测试，游戏核心零改动、gate 578→580）**；**M29 已完成（网页版 localStorage 存档 / `src/rogue/web_storage.py` 可插拔后端——浏览器 `platform.window.localStorage`（固定键）替代 pygbag `/data` 直写、桌面回退文件、序列化仍走 M26 `to_dict`/`apply_state` 确定性等价；`main.SAVE_BACKEND` 接线 + `play_web.bat`/`play_web.sh` 启动入口；11 例测试全绿 580→591）**；**M30 已完成（交互式射灯 / 碎灯 UI / `src/rogue/aim_state.py` 控制层视图状态 + `main._handle_key` 瞄准模式分支 + `render_pygame._draw_aim_cursor` 准星；T 进入瞄准 / 方向键移动光标 / Enter 射灭 / X 射碎 / T·Q·Esc 退出；瞄准不耗回合、确认才耗、复用 M19 几何约束、opt-in 默认零回归；27 例测试全绿 591→618）**。
- **产品目标（2026-08-29 新增，已明确为 MCU 荷兰弟版）**：最新蜘蛛侠（Spider-Man）风格，**以 MCU 荷兰弟（Tom Holland）版蜘蛛侠为主角**——红蓝战衣/蛛网发射器/纽约都市基调；所有里程碑的美术/剧情/机制均围绕此主题（非官方 IP，属风格致敬/个人学习项目）。
- 最近一次更新：2026-08-30（M30 完成 · 交互式射灯 / 碎灯 UI · 瞄准模式交还玩家决策权）

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
- [x] M16 可破坏的房间灯：在 M14 翻转式灯开关之上加「蛛网射碎灯泡，一次性不可逆」——新增 `destroyed_lights` 集合 + `can_destroy_light` / `destroy_light`（纯几何、零随机、默认关闭、换层重置）；`_light_sources` 同时跳过 `switched_lights` 与 `destroyed_lights`（只移除光源、不新增 ⇒ 光照场只变暗、有效半径恒 ≤ `SIGHT_RADIUS`(8) ⇒ #9/#12/#14 不破）；已碎灯不可再 toggle（`can_toggle_light` 对已破坏者返 False）、破坏可作用于已关灯房间 ⇒ 永久黑暗、不可恢复；碎裂轻响 `NOISE_SHATTER_BULB=3` 从灯处传出（M8 调虎离山，与 M14 拉链轻响同值）；`render()` 字形一字不差（破坏只改光照场与可见集合）；`main.py --light --stealth` 下蜘蛛侠改为射碎未察觉敌人所在房间的灯泡（永夜降临），三层仍通关；`tests/test_destructible_light.py`（43 例，1 skip）；ADR-012；不变量 #16（可破坏的灯：纯几何零随机、默认关闭、只移除光源不新增、已碎不可 toggle、可作用于已关灯房间、声源在灯处、destroy 零副作用、换层重置）；测试数 384 → 432，门禁四道门 + 评审流水线全绿（无 HIGH）；默认/潜行两条演示（`python main.py` / `--stealth`）与 M15 逐字节一致（默认 30/30、潜行 28/30） — commit `8f071d7`
- [x] M17 环境光照场与完整光照场分离：在 M11 的 `light_field`（房间灯 + 玩家微光 + 手电）之外，由 `update_light()` 同源、幂等再算一份 `ambient_field`（仅房间中心固定灯，不含玩家微光/手电）；新增 `_ambient_sources()`（房间灯集合，跳过 switched/destroyed）与只读查询 `ambient_level_at(x, y)`（与 `light_level_at` 对称，光照关闭恒「明亮」）；**默认所有玩法/渲染判定仍走完整场**（`light_level_at` / `light_field` ⇒ M11 怪物感知、M13 玩家视野、colorize 渲染梯度全部不变）⇒ 行为零回归；`render()` 字形一字不差，`light=False` 时两份场皆空、M1~M16 一字节不变；`tests/test_ambient_light.py`（11 例）；ADR-013；不变量 #17（环境场与完整场分离：纯几何零随机、默认关闭、只移除光源不新增、环境场仅暴露查询、改用环境场的玩法改动留作后续 opt-in）；测试数 432 → 443，门禁四道门 + 评审流水线全绿（无 HIGH）；默认/潜行/光线/手电四条演示（`python main.py` / `--stealth` / `--light --stealth` / `--flashlight`）均通关、与 M16 逐字节一致（平衡 默认 30/30、潜行 28/30 经 balance_check 复刻）；新测试 11 例 — commit `f96cb84`
- [x] M18 怪物感知改用环境场：把 M11 怪物感知半径判定从完整场 `light_level_at` 改走「怪物感知光场」`monster_light_level_at`（**仅房间灯 + 随身手电、不含玩家被动微光**），修正「被动微光把附近暗处怪照成近视眼反面」的隐性副作用；新增 `_monster_light_sources()` / `monster_light_field` / `monster_light_level_at`，由 `update_light()` 与 `light_field`/`ambient_field` 同源、幂等重算；有效半径恒 ≤ `MONSTER_SIGHT_RADIUS`(7) ⇒ #9 对称硬性质不破、手电双刃（M12）保留；`light=False` 三条演示（默认/`--stealth`/`--noise`）与 M17 逐字节一致、`--light`/`--flashlight` 四条仍通关；改写 `tests/test_light.py::test_player_glow_lights_nearby_monster` 为「被动微光不再照亮怪」而非删测试凑绿、新增 `tests/test_ambient_light.py::TestMonsterPerceptionUsesAmbientExcludingGlow`；`render()`/`colorize` 仍走完整场（#8 延伸）；测试数 443 → 445，门禁四道门 + 评审流水线全绿（无 HIGH），平衡 默认 30/30、潜行 28/30 经 balance_check 复刻 — commit `1ecf826`
- [x] M19 灯开关独立实体：新增 `LightSwitch` 实体（`src/rogue/game.py`，墙边开关，与天花板灯具 `room.center` 分离的独立控制手柄）+ `tiles.SWITCH="="`（亮黄配色 `color.py`）+ 确定性摆位 `_place_switches`/`_switch_position_for`（每房间外沿首个命中墙格、零随机）+ 平行 switch API（`switch_at` / `can_toggle_switch` / `toggle_switch` / `can_destroy_switch` / `destroy_switch` / `switch_light_is_on`，纯几何零随机）；**保留 M14 `toggle_light` / M16 `destroy_light` API 不动**，`toggle_switch`/`destroy_switch` 翻同一份 `switched_lights`/`destroyed_lights`（按 `room.center` 记录）⇒ 完全复用 M14/M16 光照场逻辑、行为零回归；几何约束瞄准「开关格」的 `has_line_of_sight` + 切比雪夫 ≤ `WEB_LIGHT_RANGE=6`（含脚下）+ 开关未碎 + 开关/光照双开关启用；声源仍在灯具处（`NOISE_TOGGLE_LIGHT=3` / `NOISE_SHATTER_BULB=3` 从 `room.center` 传出，M8 调虎离山成立）；`main.py` 设 `switches=light`，`--light --stealth` 下 `step 0b` 改为蛛网射碎未察觉敌人所在房间**墙边开关**的灯泡（永夜摸黑接近，行为等价于 M18 射碎灯具）；`render()` 全图/迷雾画 `=`、已碎退回 `#`、不改写 world state（#8 延伸）；opt-in（默认关闭 ⇒ 默认/潜行/听觉三条演示与 M18 逐字节一致）；新增 `tests/test_light_switch_entity.py`（33 例）；不变量 #19（灯开关独立实体：纯几何零随机、默认关闭、翻同一份状态、声源在灯具处、render 只加字形）；测试数 445 → 478，门禁四道门 + 评审流水线全绿（无 HIGH），平衡 默认 30/30、潜行 28/30 经 balance_check 复刻，`--light --stealth` 与 M18 灯具基线同 7/10 通关（无回归）、`--flashlight --stealth` 10/10 — commit `3280641`
- [x] M20 光照影响蜘蛛感应半径：`fov.py` 新增 `SPIDER_SENSE_DARK=2` / `SPIDER_SENSE_DIM=3` 常量与纯函数 `spider_sense_radius(light_lvl)`（暗 2 / 昏暗 3 / 明 4 = `SPIDER_SENSE_RADIUS`，只缩短不放大、恒 ≤ 4）；`game.py::spider_sense()` 在 `light_enabled` 时按怪物所在格光照算有效半径（`spider_sense_radius(self.light_level_at(m.x, m.y))`，与 M13 同一盏灯的定义、按目标格光照），`light=False` 时半径恒为 4（与 M1~M19 逐字节一致）；纯几何零随机、opt-in 默认关闭、`render()` 字形一字不差（#8 延伸）、暗处保留最小半径 2 避免彻底无预警；新增 `tests/test_spider_sense_light.py`（28 例）；不变量 #20；测试数 478 → 506，门禁四道门 + 评审流水线全绿（无 HIGH），平衡 默认 30/30、潜行 28/30 经 balance_check 复刻（与 M19 逐字节一致），不加 `--light` 演示与 M19 逐字节一致 — commit `01e3cb6`
- [x] M21 可键盘操作玩法：把「只能看脚本 demo」变成「能自己上手玩、开发中可实测」——`main.py` 新增 `_handle_key`（按键→动作，撞怪即攻击 bump-to-attack、`g` 拾取、`1~5` 用道具、`e` 蛛网摆荡突袭、`f` 手电、`>` 下潜、空格/`.`/回车等待、`?` 帮助、`q` 退出）+ `_player_interactive`（渲染→读键→执行→怪物回合，判定 win/dead/quit）+ `main()` 的 `--play` 开关（默认仍走 `_player_act` 自动驾驶 demo，零回归）；纯几何零随机（只调 Game 既有方法、不新增随机）、move 保持 4 向（#4）、有效动作耗回合 / 无效键不耗（#2）、操作说明内置；`tests/test_interactive.py`（15 例）钉死 bump 攻击 / 无效键不耗回合 / 核心动作 / 循环结局 / 确定性（同 seed+同按键序列⇒同结果）；gate 四道门全绿：测试 506→521 — commit `f32b674`
- [x] M22 Pygame GUI 渲染层：把「ASCII 终端视图」换成「真实 Pygame 窗口」——新增 `src/rogue/render_pygame.py` 的 `PygameRenderer`（只读 `Game` 公开状态、逐帧画窗口、主循环 `run(_handle_key)` 与 `--play` 终端路径同构；调色板镜像 `color.py`；坐标↔像素等纯函数便于单测）；`main.py` 新增 `--gui` 开关（延迟 import `PygameRenderer`、opt-in），`--play` 终端模式保留作 headless 回归基线；引入首个第三方依赖 `pygame`（`requirements.txt`）+ 新增 `play_gui.bat`（双击进窗口）；纯几何零随机、不改 `Game` 一字（#1/#2/#8 延伸）、GUI 与终端对同 seed+同输入序列产生同结果（#2，机器判定 `tests/test_gui.py::test_apply_keys_parity_with_terminal`）；`tests/test_gui.py`（12 例，headless dummy driver + pygame 缺失 skip）钉死纯函数 / 键位映射 / 确定性回归；gate 四道门全绿：测试 521→533 — commit `180452e`
- [x] M23 Spider-Man 主题化 GUI 渲染：把 M22 的「纯色块」升级为**程序化蜘蛛侠主题**——`render_pygame.py` 的 `PygameRenderer` 重写为：①预渲染主题贴图（地板=暗蓝+蛛网纹理、墙=纽约砖缝+红蓝描边、未探索=近黑+极淡蛛网），按可见性给明/暗两版；②玩家 `@` 画成蜘蛛侠面具（红底+黑蛛网放射线+两只白眼）；③怪物按字形 `M`（亮红眼）/ `m`（暗红眼）/ `~`（蓝眼+声波弧）主题化、并按 `game.monster_at` 取实体；④道具 `!` 按 `item.key` 画不同图标（蛛网弹=青色蛛球 / 三明治=琥珀方 / 纳米强化剂=蓝滴 / 垃圾桶盖=灰罐）；⑤楼梯 `>` 画成绿色下行门、墙边开关 `=` 画成黄色开关块；⑥蜘蛛感应 `?` 画成红色脉冲光晕（彼得「蜘蛛感应 tingling」的视觉化，按帧轻微脉动）；⑦攻击时生成淡出**蛛网特效**（玩家→目标一缕白蛛丝，10 帧 TTL）+ 命中白闪，存于 `self.effects`（renderer 自身视图状态、按帧衰减、**不回写 `Game`**）；⑧合成音效（蛛网发射 thwip / 命中闷响，`wave`+`array` 内存合成、`pygame.mixer` 懒初始化、整段 `try/except` 包裹、不可用则 `sound_on=False` 静默，音效从不读写游戏状态）；⑨主题化 HUD（红蓝标题条「SPIDER-MAN」+ 蛛网分隔线 + 红色血条 + 按道具上色的背包格 + 模式旗标 + 操作提示）。**保持 M22 契约**：`tile_color` / `pixel_pos` / `translate_key` 行为不变（实体字形仍返回 M22 的字面颜色元组，既有 12 例零破）；`run` 主循环仍与 `--play` 终端路径同构（共用 `_handle_key`）；`--gui` 仍 opt-in，默认仍是脚本 demo / `--play` 终端，零回归。**美术全程序化、零素材依赖**（确定性满分、自包含）。`tests/test_gui.py` 扩至 20 例（新增 8 例覆盖蛛网特效生成与衰减 / 攻击检测 / 大 cell 整场景绘制 / 各字形 helper 不报错，全绿）；gate 四道门全绿：测试 533→541 — commit `f9b55a0`；**M23 已完成（Spider-Man 主题化 GUI 渲染 / `src/rogue/render_pygame.py` 的 `PygameRenderer` 重写为程序化蜘蛛侠主题——预渲染蛛网地板 / 纽约砖墙 / 近黑未探索贴图、玩家画蜘蛛侠面具（红底+黑蛛网放射线+白眼）、怪物 `M`/`m`/`~` 主题图标、道具按 `item.key` 画图标、楼梯 / 墙边开关主题化、蜘蛛感应 `?` 红色脉冲光晕；攻击生成淡出蛛网特效+命中白闪（renderer 自身视图状态、按帧衰减、不回写 `Game`）+ 合成音效（蛛网 thwip / 命中闷响，`pygame.mixer` 懒初始化、失败静默、不碰游戏状态）+ 主题 HUD（红蓝标题条「SPIDER-MAN」+ 蛛网分隔 + 红色血条 + 按道具上色的背包格）；纯几何零随机、不改 `Game` 一字（#1/#2/#8 延伸）、GUI 与终端对同 seed+同输入序列产生同结果（#2）；8 例测试全绿（533→541））**
- [x] M24 Spider-Man 主题美术再升级（动画+美术+音效 / `src/rogue/render_pygame.py` 的 `PygameRenderer` 在 M23 程序化美术上叠加帧动画与音效升级）：①动画框架（`self.frame` 计数器驱动、每帧 +1、纯几何零随机、纯视图）；②地形多帧预渲染（蛛网轻闪 / 砖缝呼吸，按帧在预渲染帧间切换）；③玩家待机呼吸 / 攻击突进 / 受击红闪、怪物待机浮动 + 眨眼；④攻击蛛网从玩家向目标**行进** + 命中**火花迸发**（`burst` 特效）、蜘蛛感应 `?` 改为**扩散同心环**；⑤氛围层（暗角 vignette + 开灯房间光晕 `BLEND_ADD`）；⑥音效升级（脚步 / 摆荡 whoosh / 感应刺痛 / 胜负 stings，全程序化 `wave` 合成、懒初始化、失败静默、不碰游戏状态）。红线不变：只读 Game、零随机、不改 `Game` 一字（#1/#2/#8 延伸）；`tile_color`/`pixel_pos`/`translate_key`/`apply_keys` 契约不变（M22/M23 测试钉死字面仍成立）；GUI 与终端对同 seed+同输入序列产生同结果（#2，机器判定 `tests/test_gui.py`）；`tests/test_gui.py` 20→29 例、gate 541→550 全绿（不变量 #24）；实现 commit `e0cc471`。
- [x] M25 Boss 战与胜利条件闭环（`src/rogue/game.py` 的 `Monster.boss` 标志 + `Game.boss` / `Game.boss_depth` 开关 + `_spawn_boss` / `_free_boss_tile` / `is_victory`，`src/rogue/tiles.py` 增 `BOSS="B"`，`src/rogue/color.py` 增 `"B": 亮绿`；`main.py` 增 `--boss` 并传 `boss_depth=MAX_DEPTH`、收尾语 / `_ending_banner` boss 化；`render_pygame.py` 的 `_draw_glyph` 增 `B` 分支 → `_draw_boss`（程序化绿魔面孔，暴怒时脸色转暗红+脉动怒光））：把「无限下潜」收口成一局完整胜负——**最终层（depth == boss_depth）且 boss 开启**时确定性刷绿魔（选离玩家起点曼哈顿最远房间、中心优先行优先扫描找空位、**不消耗 RandomSource** ⇒ 前几层与 `boss=False` 逐字节一致、#1/#2 不破）；绿魔 HP 30 / 攻击 3（压在平衡基线内、不破 #1~#6）、半血暴怒 `effective_attack` 确定性 +1（零随机）；最终层只刷 Boss（清场即终局）；`is_victory()` 仅在「boss 模式且绿魔被击败且玩家未阵亡」时为真、非 boss 模式恒 False（沿用 M1~M24 语义）；opt-in 默认关闭 ⇒ 不加 `--boss` 与 M24 逐字节一致（演示 seed 19 仍第 171 回合清场 HP 18/20）、`--boss` 第 171 回合击败绿魔 HP 10/20。`tests/test_boss.py`（14 例）覆盖 opt-in 零回归 / 最终层刷 Boss / 字形 B / 半血暴怒 / 胜利闭环 / 渲染纯净 / 确定性；gate 四道门全绿：测试 550→564（不变量 #25）；实现 commit `0639cf0`。
- [x] M26 存档 / 读档（`src/rogue/game.py` 的 `Game.to_dict`（确定性排序导出完整快照）/`apply_state`（原地恢复）/`from_dict`（重建）/`save`/`load`/`load_into`，`src/rogue/rng.py` 的 `RandomSource.get_state`/`set_state`；`main.py` 的 `_handle_key` 增大写 `S`（存档）/`L`（读档）键，默认路径 `savegame.json`（已加 `.gitignore`）；`tests/test_save.py` 10 例）：把「关掉即丢」变成「可随时存、关掉再读档接着玩」——存「seed + PRNG 内部状态 + 全部玩法状态」（玩家 HP/背包/纳米加成/地图/怪物/道具/灯开关/灯光场/视野记忆/各开关/boss），读档即原地还原；**关键**：PRNG 内部状态经 `get_state` 完整保存 ⇒ 读档后续随机序列与「从未存读」逐字节衔接（#1/#2）；`to_dict` 集合/字典按可复现顺序排序导出 ⇒ 同状态同字节、往返幂等；同存档+同后续输入⇒同终态（不变量 #26）；opt-in 默认不触发（游戏照常运行与 M25 逐字节一致）。gate 四道门全绿：测试 564→574（不变量 #26）；实现 commit `819521d`。

- [x] M27 序列帧 Sprite（`src/rogue/render_pygame.py` 的地形绘制抽成模块级 `_make_floor_surface`/`_make_wall_surface`/`_make_unseen_surface`，`_make_*` 方法退化为回退委托；新增 `_load_tile_sprites` 从 `tiles/*.png` 加载并按 cell 缩放、`_build_tiles` 优先用 PNG、缺文件回退同款程序化；`scripts/gen_tiles.py` 确定性烘焙 20 张 PNG（floor/wall 各 lit/dim ×4 帧 + unseen ×4 帧，BASE=64，零随机）；`tests/test_gui.py` 增 4 例（资产存在 / PNG 加载 / 逐像素一致防漂移 / 缺文件回退）；评审流水线 `allowed_dirs` 加 `tiles`；`docs/工单/T-027-序列帧Sprite.md` + `docs/adr/ADR-023-序列帧Sprite.md` + 不变量 #27；把「每帧程序化重绘地形」换成「确定性 PNG 序列帧 blit」，视觉与 M24 逐像素一致、零回归、确定性不变（#1/#2/#8 延伸）；4 例测试全绿 574→578；实现 commit `291ebd2`）。
- [x] M28 网页化（Pygbag）：把 M22 起的 Pygame 窗口原样打包成 wasm 在浏览器运行——`web.py` 浏览器入口（`async main` 构造 `Game.procedural` + `PygameRenderer.async_run(main._handle_key)`，复用 `main._handle_key` 与同款旗标语义、默认全开展示）+ `src/rogue/render_pygame.py` 抽出 `_pump_events`/`_check_ending(wait=)` 共用逻辑并新增 `async_run`（每帧 `await asyncio.sleep(0)` 让出浏览器事件循环，避免 wasm 单线程卡死）、字体初始化加 `try/except` 回退内置默认字体；`build_wasm.bat`/`build_wasm.sh` 构建脚本 + `requirements-web.txt`（pygbag>=0.4）；`tests/test_gui.py` 增 2 例 `async_run` 用例（headless 验证不卡死、Game 状态不变）；游戏核心（`Game`/`render()`/`_handle_key`）一字未改、零新增随机（#1/#2/#8 延伸），`run`/`async_run` 同构 ⇒ 同 seed+同输入序列同结果（#28）；`docs/工单/T-028-网页化Pygbag.md` + `docs/adr/ADR-024-网页化Pygbag.md` + 不变量 #28；gate 四道门全绿：测试 578→580（不变量 #28）；实现 commit `65e242d`。
- [x] M29 网页版 localStorage 存档（`src/rogue/web_storage.py` 的 `LocalStorageBackend`（浏览器 `platform.window.localStorage` 固定键）/ `FileSaveBackend`（桌面回退）/ `get_default_backend`（按环境自动选）+ `main.py` 的 `SAVE_BACKEND` 接线（`_handle_key` 的 S/L 改走 `SAVE_BACKEND.save/load_into`、不再写死 `SAVE_PATH`）、`web.py` 显式注入、新增 `play_web.bat`/`play_web.sh` 启动入口、`scripts/review_pipeline.py` 范围白名单加 web/启动脚本；把网页版存档从 pygbag `/data`（IndexedDB）切到浏览器原生 localStorage——跨刷新更稳妥、键空间独立；序列化仍走 M26 `Game.to_dict`/`apply_state` 确定性排序导出 ⇒ localStorage 往返与文件往返 dict 层面逐字节等价（#26）、桌面与 M26 逐字节一致；纯 I/O、零随机、不写 `Game`（#1/#2/#8 延伸）；`tests/test_web_storage.py` 11 例覆盖后端探测 / localStorage 往返 / 确定性 JSON / 无档 FileNotFoundError / 不可用 RuntimeError / `_handle_key` 经 `SAVE_BACKEND` 路由；gate 四道门全绿：测试 580→591（不变量 #29）；实现 commit `1eec636`）。

- [x] M30 交互式射灯 / 碎灯 UI（`src/rogue/aim_state.py` 控制层视图状态模块 + `main.py::_handle_key` 瞄准模式分支 + `src/rogue/render_pygame.py::_draw_aim_cursor` 准星 + `tests/test_aim_mode.py` 27 例）：把 M19 的「射灭 / 射碎墙边开关」决策权从 demo 自动战术（`_player_act::_light_to_destroy`）交还玩家——按 `T` 进入瞄准、方向键 / WASD / HJKL 移动光标（不消耗回合）、`Enter`/空格 射灭射亮（`game.toggle_switch`，可逆）、`X` 射碎（`game.destroy_switch`，一次性不可逆）、`T`/`Q`/`Esc` 退出瞄准；**瞄准状态是控制层视图状态**（`aim_state` 模块级 `_AIM` 字典，不属于 `Game`，与 `PygameRenderer.effects` 同性质）⇒ 不写 `Game` 任何字段、不调 `RandomSource`（#1/#2/#8 延伸 / 不变量 #30）；**瞄准不消耗回合**（进入 / 退出 / 移动光标都不调 `monster_turn`，只有确认射灭 / 射碎成功才消耗回合——潜行玩法的核心：玩家可反复瞄准不惊动敌人）；几何约束复用 M19 的 `can_toggle_switch`/`can_destroy_switch`（够不着 ⇒ `acted=False`、不耗回合、不改 `Game`）；光标可在 `in_bounds` 内自由移动（不限于射程内，让玩家看见「够不着」反馈）；终端 `--play` 在状态行提示光标坐标、GUI `--gui` / 网页版画黄色方框 + 几何约束颜色十字（绿=可射灭 / 红=可射碎 / 灰=够不着）；`opt-in 默认零回归`（不按 `T` 不进入瞄准 ⇒ 与 M29 逐字节一致；`balance_check` 默认 30/30、潜行 28/30 复刻；`python main.py` seed 19 仍第 171 回合清场 HP 18/20）；`aim_state` 在 `descend` / 游戏结束 / `run`·`async_run` finally 复位避免跨局串扰；ADR-026；不变量 #30；gate 四道门全绿：测试 591→618；实现 commit `63356a2`）。

## 下一步指令（给下一个会话 / M28）
0. 已完成的 M15 关键结论（**先读，能省半天**）：
   - **默认追击统一走 close_in=True**：`_step_toward` 现在调用 `_step_toward_point(candidates, (px,py), close_in=True)`，与潜行分支一致。曼哈顿平局时切比雪夫更小的那一步才是真的在逼近；只比曼哈顿会选「横跳」那步 ⇒ 玩家轴向往复时怪锁轴震荡、永不贴上（seed 19 实测锁死 30+ 回合）。
   - **配平各降 1（1~3 → 0~2）**：`MONSTER_TABLE = (0,0,1,1,2,1)`。修复让怪物更可靠地贴上 ⇒ 整体威胁上升；实测三态：旧追击+旧攻击 26/30（HANDOFF 现状）、新追击+旧攻击 **22/30**（只修不配平会掉）、新追击+新攻击 **默认 30/30 / 潜行 28/30**（配平后，≥ 基线）。
   - **0 伤害杂鱼是 harmless fodder**：街头小混混 / 迷途无人机攻击 0，仍占位、可被杀死、清场才能下潜，只是挠一下不破防（主题：街头小混混够不到你）。这是「各降 1」配平的代价，刻意保留。
   - **确定性不变**：修复与配平均纯几何、零随机，同 seed + 同输入 ⇒ 同结果（#2）。不变量 #9（感知对称）未触及、未破。
   - **默认追击行为改变是预期的**：此前 M1~M14 的「逐字节一致」保证只适用于 opt-in 开关（fov/stealth/noise/light）；默认追击是核心玩法，修正它就是本里程碑目的，不要求与旧演示逐字节相同。stealth 模式不受影响（它早已用 close_in=True）。
   - **验证四件套全绿**：`python scripts/gate.py`（389 例，+5）、`python scripts/balance_check.py`（默认 30/30、潜行 28/30）、`python main.py`（seed 19 第 171 回合清场 HP 18/20）、`python main.py --stealth`（第 225 回合 HP 18/20，均 ≤ 240 上限）。
0b. 已完成的 M16 关键结论（**先读，能省半天**）：
   - **破坏是 M14 翻转式的「不可逆」升级**：M14 用 `switched_lights`（可恢复），M16 新增 `destroyed_lights`（一次性永久黑暗）；`_light_sources` 合并跳过两者 ⇒ 行为一致地「只移除光源、不新增」。
   - **`can_destroy_light` 复用 M14 四条几何约束 + 第五条「尚未被破坏」**；`destroy_light` 纯状态操作（翻集合 + `update_fov` + `emit_noise`），零随机、不改玩法状态、换层（`load_level`）重置。
   - **已碎灯不可再 toggle**（`can_toggle_light` 对 `destroyed_lights` 返 False），破坏也可作用于「已关灯（switched）」房间 ⇒ 永久黑暗；`light_is_on` 同时查两个集合。
   - **碎裂响度 `NOISE_SHATTER_BULB=3` 与 M14 拉链持平**（刻意）：保全「已验证的 `--light --stealth` 演示」通关行为不变（噪声相同 ⇒ 惊动集合相同）；声源在灯处（调虎离山）。
   - **`light=False` 时 `destroy_light` 恒 no-op** ⇒ 默认/潜行/听觉三条演示与 M15 逐字节一致（默认 30/30、潜行 28/30 经 balance_check 复刻）；新测试 43 例（1 skip）。
   - **存档读档本质是「存 seed + PRNG 内部状态 + 完整状态快照」**：只存 seed 不够——游戏进行到中途 rng 早已消费过（关卡生成/撒点/怪物游走/伤害浮动），必须把 `random.Random.getstate()` 一并存下，`RandomSource.get_state/set_state` 封装了它；读档后下一次 `rng` 调用与「从未存读」逐字节衔接（#1/#2）。
   - **确定性导出是关键**：`to_dict` 把坐标集合转列表后 `sorted`、把 `dict` 项转 `(list(key), value)` 后 `sorted`、`json.dump(sort_keys=True)` ⇒ 同状态永远导出同一字节，往返零漂移，`from_dict(to_dict())` 幂等。
   - **opt-in 默认关闭**：游戏照常运行不会触发任何存读档；只有玩家按 `S` 或显式 `Game.save()` 才写盘，不加参数时与 M25 逐字节一致；小写 `s`/`l` 仍是移动键，不冲突。
   - **验证四件套全绿**：`python scripts/gate.py`（574 例，+10）、`tests/test_save.py` 覆盖 JSON 可序列化 / dict 往返幂等 / 文件往返 / load_into 原地恢复 / 读档后确定性（同存档+同后续输入⇒同终态）/ rng 序列衔接 / 灯光开关状态保留 / 教学图零回归 / 存档不改玩法结果。
   - **`main.py` 演示改动**：`--light --stealth` 下原 `toggle_light` 改为 `destroy_light`（射碎灯泡，永夜降临）——潜行路线里本就不打算回点亮，行为等价且更彻底；房间变暗仍缩短玩家自身视野（M13 双刃），但已验证三层通关。
0c. 已完成的 M30 关键结论（**先读，能省半天**）：
   - **瞄准状态归属控制层而非 Game**：`aim_state`（`src/rogue/aim_state.py`）是模块级 `_AIM` 字典（`active`/`x`/`y`），与 `PygameRenderer.effects` 同性质——纯视图状态、不回写 `Game`。污染 `Game` 会破坏 `to_dict`/`apply_state`（M26 存档）与 `render()` 纯净性（#8）。`main` 与 `render_pygame` 都 import 它、无循环导入。
   - **瞄准不消耗回合是潜行核心**：进入 / 退出 / 移动光标都不调 `monster_turn`，玩家可反复瞄准不惊动敌人；只有确认射灭 / 射碎成功（`acted=True`）才由调用方跑 `monster_turn`。这把「出手才付代价」的潜行决策权交还玩家。
   - **模态拦截必须在所有动作键之前**：`_handle_key` 瞄准分支放在 S/L 之后、MOVE_KEYS 之前，拦截方向键 / 空格 / Q 的既有语义——瞄准下 `Q` 退瞄准而非退游戏、空格射灭而非等待、方向键移光标而非走位。
   - **Esc 在 GUI 下被 translate_key 吞掉**（M22 `test_escape_ignored` 钉死返回 `None`），GUI 用 `T`/`Q` 退出瞄准；终端 `--play` 下 Esc 是 `\x1b` 可退出。**不改 translate_key**（熔断②禁止改测试凑绿）。
   - **几何约束复用 M19**：确认时调 `can_toggle_switch`/`can_destroy_switch`，不引入新判定；光标可在 `in_bounds` 内自由移动（不限于射程），让玩家看见「够不着」反馈；够不着 ⇒ `acted=False`、不耗回合、不改 `Game`。
   - **opt-in 默认零回归**：不按 `T` 不进入瞄准 ⇒ `balance_check` 默认 30/30、潜行 28/30 复刻；`python main.py` seed 19 仍第 171 回合清场 HP 18/20（与 M29 逐字节一致）。
   - **复位避免跨局串扰**：`descend` 后 / 游戏结束（`_player_interactive` 末尾）/ `run`·`async_run` `finally` 都调 `aim_state.reset()`；测试 `setUp`/`tearDown` 也 reset。
1. 读 `CLAUDE.md` → （T-019 / T-020 已建，见 `docs/工单/T-019-灯开关独立实体.md`、`docs/工单/T-020-光照影响蜘蛛感应半径.md` 与对应 ADR-015 / ADR-016）。下一步候选（M30 完成后剩余方向）：
   - ~~**怪物感知改用环境场**（已完成，见 M18 / `docs/工单/T-018-怪物感知改用环境场.md` / `docs/adr/ADR-014-怪物感知改用环境场.md`）~~：把 M11 怪物感知从 `light_level_at`（完整场，含被动微光）切到「怪物感知光场」`monster_light_level_at`（仅房间灯 + 手电，**不含被动微光**），修正「微光替暗处怪点灯」的隐性副作用；手电双刃（M12）保留。
   - ~~**灯开关作为独立实体**（已完成，见 M19 / `docs/工单/T-019-灯开关独立实体.md` / `docs/adr/ADR-015-灯开关独立实体.md`）~~：墙边开关 `LightSwitch` 实体与天花板灯具 `room.center` 分离；保留 M14 `toggle_light` / M16 `destroy_light` API 不动，平行新增 switch API（翻同一份 `switched_lights`/`destroyed_lights`，按 `room.center` 记录）⇒ 行为零回归；opt-in（默认关闭，与 M18 逐字节一致）、声源在灯具处（调虎离山成立）、`render()` 只加 `=` 字形。
   - ~~**让光照也影响蜘蛛感应半径**（已完成，见 M20 / `docs/工单/T-020-光照影响蜘蛛感应半径.md` / `docs/adr/ADR-016-光照影响蜘蛛感应半径.md`）~~：把 M6 的穿墙预警半径从恒 4 改为随目标格光照衰减（暗 2 / 昏暗 3 / 明 4），与 M11 怪物感知、M13 玩家视野形成「黑暗三重削弱」对称；默认关闭、与 M1~M19 逐字节一致、28 例测试全绿（478→506）。
  - **（M21 已完成：可键盘操作玩法；M22 已完成：Pygame GUI 渲染层；M23 已完成：Spider-Man 主题化 GUI 渲染；M24 已完成：主题美术再升级 · 动画+美术+音效；M25 已完成：Boss 战与胜利条件闭环；M26 已完成：存档 / 读档）**：M6–M25 的「视野 / 潜行 / 听觉 / 光照 / 蜘蛛感应 + 可键盘操作 + 窗口渲染 + 蜘蛛侠主题动画美术 + 音效 + 最终层绿魔 Boss 与胜利闭环」体系已闭环，游戏从「只能看 ASCII 终端 demo」变成「能在真实窗口里手动玩、角色会呼吸/浮动、攻击有蛛网行进与火花、暗夜有氛围光、且听得见脚步与摆荡、击败绿魔才真正通关」。后续新里程碑仍需先登记工单 + ADR + 不变量后再开工。候选方向（按优先级）：
    - ~~**交互式射灯 / 碎灯 / 开关（M14/M16/M19 的玩家可控版）**（已完成，见 M30 / `docs/工单/T-030-交互式射灯碎灯UI.md` / `docs/adr/ADR-026-交互式射灯碎灯UI.md`）**~~：`_handle_key` 加瞄准模式（`T` 进入 / 方向键移光标 / `Enter` 射灭 / `X` 射碎 / `T`·`Q`·`Esc` 退出），瞄准状态是控制层视图状态（`aim_state`，不属于 `Game`）、瞄准不耗回合、确认才耗、复用 M19 几何约束、opt-in 默认零回归（不变量 #30）。
    - ~~**存档 / 读档（save/load，已完成，见 M26 / `docs/工单/T-026-存档读档.md` / `docs/adr/ADR-022-存档读档.md`）**~~：保存「seed + PRNG 内部状态 + 全部玩法状态」，读档后续演化与「从未存读、并行推进」完全一致（不变量 #26）；`--play` / `--gui` 下按 `S` 存、`L` 读。
    - **更多蜘蛛侠招式（AoE 蛛网束缚 / 摆荡位移）**：把 M7 摆荡突袭扩展为可手动指定落点的位移技、或范围蛛网束缚多怪。
    - ~~**主题美术换 tiles/*.png 序列帧 Sprite（已完成，见 M27 / `docs/工单/T-027-序列帧Sprite.md` / `docs/adr/ADR-023-序列帧Sprite.md`）**~~：M24 预渲染已按帧组织，把程序化地形贴图换成 `tiles/*.png` 序列帧（`_load_tile_sprites` 加载、缺文件回退同款程序化、视觉与 M24 逐像素一致）；仅地形贴图（floor/wall/unseen）走 PNG 序列帧，玩家面具/怪物/Boss/道具/特效/HUD 仍为程序化实时绘制（带位置相位动画，不适合静态序列帧）。
    - ~~**网页化（Pygbag 把 Pygame 打包成 wasm，零改核心，已完成，见 M28 / `docs/工单/T-028-网页化Pygbag.md` / `docs/adr/ADR-024-网页化Pygbag.md`）**~~：游戏核心零改动，浏览器直接玩（不变量 #28）。
    - ~~**网页版存档接入 `platform.window.localStorage` 替代 `/data` 直写（更稳妥的跨刷新持久化，已完成，见 M29 / `docs/工单/T-029-网页版localStorage存档.md` / `docs/adr/ADR-025-网页版localStorage存档.md`）**~~：浏览器落 localStorage（固定键 `spiderman_roguelike_save_v1`）、桌面回退文件、序列化仍走 M26 `to_dict`/`apply_state` 确定性等价（不变量 #29）；新增 `play_web.bat`/`play_web.sh` 直接启动入口。
    - **移动端触屏 / 虚拟按键支持**（Pygbag 触屏事件）：把 WASD/方向键操作映射到屏幕虚拟摇杆 / 按钮，让手机浏览器也能玩；可加在 `render_pygame.async_run` 的事件循环里（仍是只读 Game、只调 `_handle_key`，零随机）。
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
  （不在玩家处）⇒ 调虎离山成立（M8 联动）；  可开关房间灯**默认无意义**（`light=False` ⇒
  `toggle_light` 恒返回 False、no-op，与 M1~M13 逐字节一致）；换层（`load_level`）重置 `switched_lights`。
- 假设 S（M18 起）：怪物感知改用「怪物感知光场」是**纯几何、零随机**（`game.py` 的 `monster_light_level_at`：由 `update_light` 与 `light_field`/`ambient_field` 同源重算，光源 = 房间中心固定灯 + 随身手电、**不含玩家被动微光**）；它**只缩短**怪物感知半径（恒 ≤ `MONSTER_SIGHT_RADIUS`(7)，从不放大）⇒ #9 对称硬性质不破；**排除被动微光**修正了「微光替暗处怪点灯」的隐性副作用（暗处怪仍是近视眼、你更难被发现），而**手电作为主动光仍保留在感知场里**（M12 双刃：开灯让你更易被暗处怪察觉）；渲染梯度（`colorize`）仍走完整场 `light_field`（含微光），`render()` 字形一字不差（#8 延伸）；`light=False` 时怪物感知光场清空、`monster_light_level_at` 恒返回「明亮」，M1~M17 三条演示逐字节一致。
- 假设 T（M19 起）：灯开关独立实体是**纯几何、零随机**（`game.py` 的 `LightSwitch` + `_place_switches`/`_switch_position_for`：每房间外沿首个命中墙格摆一个开关、确定性、不消耗 `RandomSource`；`toggle_switch`/`destroy_switch` 翻 `switched_lights`/`destroyed_lights` 集合——按 `room.center` 记录、与 M14/M16 同源——+ 重算光照场/可见集合（`update_fov`）+ 发出轻响（`emit_noise`），不消耗 `RandomSource`、不改写 `grid`/HP/背包/怪物状态，与 `toggle_light`/`toggle_flashlight` 同一零副作用哲学）；它**只是灯具 `room.center` 的解耦控制手柄**——蛛网够得到墙边开关、翻/碎的却是该房间的灯 ⇒ 光照场只变暗或恢复、有效半径恒 ≤ `SIGHT_RADIUS`(8) ⇒ #9/#12/#14 不破；**声源在灯具处**（不在开关格、不在玩家处）⇒ 调虎离山成立（M8 联动）；开关**默认不摆**（`switches=False` ⇒ `_place_switches` 不摆实体、`render()` 不含 `=`、与 M18 逐字节一致）；换层（`load_level`）重摆 `switches` 并清空 `switched_lights`/`destroyed_lights`（`switches_enabled` 跨层保留）；已碎开关不可再 toggle、退回底层墙 `#`。
- 假设 U（M20 起）：光照影响蜘蛛感应半径是**纯几何、零随机**（`fov.py` 的 `spider_sense_radius` + `game.py` 的 `spider_sense`：按怪物所在格光照算有效半径——暗 2 / 昏暗 3 / 明 4，与 M13 玩家视野同一盏灯的定义、读 `light_level_at(目标格)`（完整场：房间灯 + 玩家微光 + 手电），只缩短不放大、恒 ≤ `SPIDER_SENSE_RADIUS`(4) ⇒ #9 对称硬性质不破）；它**只改变「哪些隐藏威胁被列为 `?` 预警」**，不改写任何玩法状态、`render()` 字形一字不差（#8 延伸）；暗处仍保留最小半径 2（避免彻底无预警）；**默认关闭**（`light=False` ⇒ `spider_sense` 恒用常量 4、与 M1~M19 逐字节一致）；`light=True` 且存在黑暗格时，远处暗处威胁的 `?` 预警范围收缩（暗走廊距 3~4 的隐藏威胁不再预警），形成 M11 怪物感知 / M13 玩家视野 / M20 蜘蛛感应「黑暗三重削弱」对称。
- 假设 V（M21 起）：可键盘操作是**纯几何、零随机**的控制层（`main.py` 的 `_handle_key` / `_player_interactive`）：只调用 `Game` 既有确定性方法（move/player_attack/web_strike/pick_up/use_item/descend/toggle_flashlight），不引入任何随机 ⇒ #1/#2 不变；与脚本自动驾驶 demo（`_player_act`）共用同一套 Game 方法、互不影响（`--play` 才进交互、默认仍是 demo，零回归）；撞怪即攻击（bump-to-attack，不改写 `grid` 以外状态，#8 延伸）；move 保持 4 向（与 M1 网格一致，避免斜向穿墙角，#4）；有效动作消耗一个回合（随后 `monster_turn`）、无效/纯信息键（未知/`?`/`q`）不消耗回合（不扰动随机序列，#2）；相同 seed + 相同按键序列 ⇒ 相同结果（#2，机器判定 `tests/test_interactive.py`）。
- 假设 W（M22 起）：GUI 视图层是**纯几何、零随机**的展示层（`src/rogue/render_pygame.py` 的 `PygameRenderer`）：只读 `Game` 公开状态（grid/px/py/monsters/items/stairs/visible/explored/light_field/hp/inventory）、只调 `Game` 既有确定性方法（经 `_handle_key` + `monster_turn`），不引入任何随机、不改写任何玩法状态 ⇒ #1/#2/#8 不破；字符网格直接消费 `game.render()`（与终端同字形，零漂移）、调色板镜像 `color.py` 的 `GLYPH_COLORS`；主循环 `run(_handle_key)` 与 `--play` 终端路径同构（共用 `_handle_key`）⇒ 同 seed+同输入序列⇒同结果（#2，机器判定 `tests/test_gui.py`）；`--gui` 为 opt-in，`main.py` 延迟 import 本模块 ⇒ gate 不传 `--gui` 时不强制 pygame（首个第三方依赖 `pygame` 写 `requirements.txt`）；v1 用纯色块、不做 Sprite/动画/音效（留 M23）。
- 假设 X（M23 起）：Spider-Man 主题化 GUI 渲染是**纯几何、零随机**的美术升级（在假设 W 的 `PygameRenderer` 骨架上）：所有美术用 `pygame` 图元**程序化绘制**、不依赖任何外部图片/字体素材 ⇒ 自包含、可复现、确定性满分；地形底取自 `game.grid`（墙/地板）、实体/特征取自 `game.render()` 字形（迷雾可见性门控 + 渲染优先级全由它管），零漂移；玩家画蜘蛛侠面具、怪物按 `M`/`m`/`~` 画不同图标、道具按 `item.key` 画不同图标、楼梯/开关/蜘蛛感应各有主题图形；攻击生成的**蛛网特效 / 命中白闪**是 `renderer` 自身视图状态（`self.effects`，按帧衰减、不回写 `Game`）、合成音效（`pygame.mixer` 懒初始化、整段 `try/except` 包裹、不可用则静默、**从不读写游戏状态**）⇒ #1/#2/#8 不破；小 cell（<16）自动跳过精细纹理以保 headless 测试轻量；`tile_color`/`pixel_pos`/`translate_key` 行为不变（M22 测试钉死的字面颜色元组仍成立）⇒ 既有 12 例 GUI 规格零破；`--gui` 仍 opt-in，默认（无 `--gui`）仍走脚本 demo / `--play` 终端，与 M22 逐字节一致。
- 假设 Y（M24 起）：主题美术动画与音效升级是**纯几何、零随机**的视图/听觉层（`src/rogue/render_pygame.py` 的 `PygameRenderer`）：所有动画由 renderer 的 `self.frame` 计数器驱动（每帧 +1，纯几何、不消耗 `RandomSource`）、地形多帧预渲染、玩家呼吸/突进/受击红闪、怪物浮动/眨眼、蛛网行进/火花迸发、蜘蛛感应扩散环、暗角/开灯光晕均为 renderer 自身视图状态（按帧衰减、不回写 `Game`）；跨帧对比 `player_hp`/`px,py`/蜘蛛感应集合只用于触发视图特效与音效、不回写 `Game`；音效全程序化合成（`_synth_buffer` 内存 `wave`）、懒初始化、失败静默、绝不读写游戏状态 ⇒ #1/#2/#8 不破；`tile_color`/`pixel_pos`/`translate_key`/`apply_keys` 行为不变（M22/M23 测试钉死字面仍成立）；GUI 主循环与 `--play` 终端路径同构（共用 `_handle_key`）⇒ 同 seed+同输入序列⇒同结果（#2）；`--gui` 仍 opt-in，默认（无 `--gui`）仍走脚本 demo / `--play` 终端，与 M23 逐字节一致。
- 假设 Z（M27 起）：序列帧 Sprite 是**确定性、零随机**的视图资产（`tiles/*.png` 由 `scripts/gen_tiles.py` 用与运行时回退同一套绘制函数离线烘焙，不引入任何随机 ⇒ #1/#2 不变）；运行时 `_build_tiles` 优先 `blit` 已加载 PNG、`tiles/` 缺失或任一文件缺失则回退同款程序化绘制（视觉与 M24 逐像素一致、零回归）；PNG 以 BASE=64 烘焙、运行时 `pygame.transform.scale` 到 `self.cell` 对齐网格（任意 cell 分辨率都清晰、cell==BASE 时即原图）；地形源（PNG 或程序化）只影响「怎么画」地板/墙/未探索格，不改写 `Game` 状态、不扰动随机序列、不改变 `render()` 字形与渲染优先级 `?<><!>M<@` ⇒ #1/#2/#8 延伸不破；评审流水线 `allowed_dirs` 已加 `tiles`（范围审计无新增告警）。
- 假设 AA（M29 起）：网页版存档的**传输层**与序列化分离（`src/rogue/web_storage.py`）：`LocalStorageBackend` 在浏览器 wasm 下把状态写到 `platform.window.localStorage[spiderman_roguelike_save_v1]`、`FileSaveBackend` 在桌面/无浏览器环境回退到 `Game.save/load_into`（文件）；`get_default_backend` 按 `local_storage_available()`（函数内 `import platform`、探测 `.window.localStorage`）自动选对后端 ⇒ 桌面与 M26 逐字节一致、网页版无缝切 localStorage；两个后端共用 M26 的 `Game.to_dict`/`apply_state` 确定性排序导出（同状态同字节）⇒ localStorage 往返与文件往返在 dict 层面逐字节等价（#26）；本模块纯 I/O、零随机、不写 `Game` 玩法状态（#1/#2/#8 延伸）；`_handle_key` 的 S/L 经由可插拔 `SAVE_BACKEND`（不再写死 `SAVE_PATH`），同步/异步主循环与终端 `--play` 共用同一 `_handle_key` ⇒ 同 seed+同输入序列⇒同结果（#2/#29）；存档仍 opt-in（按 S 才触发）、失败被 `_handle_key` 的 try/except 兜住不崩；`play_web.bat`/`play_web.sh` 是双击即起 `pygbag web.py` 本地预览的网页启动入口（`python web.py` 也可作桌面 Pygame 预览，localStorage 不可用则回退文件存档）。
- 假设 AB（M30 起）：交互式瞄准模式是**控制层视图状态**（`src/rogue/aim_state.py` 的模块级 `_AIM` 字典，不属于 `Game` 状态）；纯几何、零随机（光标移动只判 `game.in_bounds`、确认只调 `Game` 既有确定性方法 `toggle_switch`/`destroy_switch`）；**opt-in 默认关闭**（不按 `T` 不进入 ⇒ 与 M29 逐字节一致）；**瞄准不消耗回合**（进入 / 退出 / 移动光标都不调 `monster_turn`，只有确认射灭 / 射碎成功才消耗回合）；几何约束复用 M19 的 `can_toggle_switch`/`can_destroy_switch`（够不着 ⇒ `acted=False`、不消耗回合、不改 `Game`）；renderer / `_colored` 只读 `aim_state` 画光标、不回写 `Game`（#8 延伸）；同 seed + 同按键序列 ⇒ 同 `Game` 终态（#2 不破，因为 `aim_state` 不影响 `Game`）；`aim_state` 在游戏结束 / 换层时由调用方复位（避免跨局串扰）。按键：`T` 进入 / 退出瞄准；瞄准下方向键 / WASD / HJKL 移动光标；`Enter`/空格 = 射灭射亮（`toggle_switch`，可逆）；`X` = 射碎（`destroy_switch`，一次性不可逆）；`Esc`/`Q`/`T` 退出瞄准（瞄准下 `Q` 退瞄准而非退游戏，模态语义；GUI 下 `Esc` 被 `translate_key` 吞掉返回 `None`——M22 `test_escape_ignored` 钉死，用 `T`/`Q` 退出）。光标可在 `in_bounds` 内自由移动（不限于射程内，让玩家看见「够不着」的反馈）。只在 `light=True` 且 `switches=True` 时有意义（否则没有开关可瞄准）；未启用时按 `T` 友好提示、不进入。
