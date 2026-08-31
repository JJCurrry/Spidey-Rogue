# ADR-026 · 交互式射灯 / 碎灯 UI（M30）

## 状态
已采纳（2026-08-30，M30 落地）。

## 上下文
M19 起墙边开关 `LightSwitch` 实体已就位、`toggle_switch` / `destroy_switch` API 已对外暴露，
但**只有 demo 自动战术（`main._player_act` 的 `_light_to_destroy`）在用**——它在 `--light --stealth`
下自动射碎未察觉敌人所在房间的开关。玩家在 `--play` / `--gui` / 网页版下**无法手动选择**
射灭 / 射碎哪个开关，潜行玩法的核心决策权没交到玩家手里。

HANDOFF-T001「下一步候选」优先级 ① 明确：「`_handle_key` 当前未覆盖「选定某个房间灯 /
墙边开关」的目标选择，仍由 demo 自动战术承担；可加「瞄准模式」（如先按某键进入瞄准、
再用方向选目标格）让玩家手动射灭 / 射碎灯」。

## 决策
**加「瞄准模式」作为控制层视图状态，把射灭 / 射碎开关的决策权交给玩家。**

### 1. 状态归属：控制层视图状态，不属于 `Game`
瞄准光标（`active` / `x` / `y`）是「玩家在选目标」的 UI 状态，与 `Game` 玩法状态无关——
它不决定 HP / 背包 / 地图 / 怪物，只决定「`_handle_key` 怎么解析按键」和「画面上画什么」。
与 `PygameRenderer.effects`（蛛网特效 / 命中闪光）同性质：纯视图状态、不回写 `Game`。

**实现**：新建 `src/rogue/aim_state.py`，模块级 `_AIM` 字典 + helper 函数
（`enter` / `exit` / `move` / `is_active` / `cursor` / `reset`）。
`main._handle_key` 读写它、`render_pygame.draw` 只读它画光标、`main._colored` 只读它高亮光标格。
`src/rogue/` 下的 `aim_state` 不依赖 `main`（避免循环导入），`main` 和 `render_pygame` 都 import 它。

### 2. 按键设计：模态、不与既有键冲突
- **`T`（target）**：进入 / 退出瞄准模式（切换）。进入时光标初始位置 = 玩家位置。
- **瞄准模式下方向键 / WASD / HJKL**：移动光标（不消耗回合）。
- **`Enter` / 空格**：确认射灭 / 射亮（`game.toggle_switch`，可逆：亮→暗 / 暗→亮）。
- **`X`**：射碎（`game.destroy_switch`，一次性不可逆）。
  - 用 `X` 而非 `D`（destroy）——`D` 是移动键（右）；`X` 联想「叉掉」，无冲突。
- **`Esc` / `Q` / `T`**：退出瞄准（不消耗回合）。
  - 瞄准模式下 `Q` 退出瞄准而非退出游戏（模态语义；要退出游戏需先 `T`/`Esc` 退出瞄准再按 `Q`）。
- **其它键在瞄准模式下被忽略**（`acted=False` + 提示操作说明）。

### 3. 回合消耗：瞄准不耗、确认才耗
- 进入 / 退出 / 移动光标：**不调 `monster_turn`**（`acted=False`）。
  - 这是潜行玩法的核心：玩家可以反复瞄准、比对目标、看清够不够得着，**不惊动敌人**。
  - 只有真正出手（确认射灭 / 射碎成功）才付出回合代价（`acted=True`，调用方跑 `monster_turn`）。
- 确认时调 `game.toggle_switch` / `destroy_switch`（M19 既有方法，内部已 `emit_noise` +
  `update_fov`），成功 ⇒ 消耗回合；够不着（`can_toggle_switch` / `can_destroy_switch` 返 `False`）
  ⇒ `acted=False` + 友好提示、不消耗回合、不改 `Game` 状态。

### 4. 几何约束：复用 M19，不引入新判定
- 确认射灭 / 射碎时调 `game.can_toggle_switch(x, y)` / `can_destroy_switch(x, y)`
  （M19 已包含「开关未启用 / 看不见 / 射程外 / 已碎」全部判定）。
- 光标可在 `game.in_bounds` 内自由移动（不限于射程内）——让玩家看见「够不着」的反馈，
  比限制光标在射程内更友好（玩家能学到射程边界 `WEB_LIGHT_RANGE=6`）。
- 确认时几何约束拦下、返无效信息——**不消耗回合、不改 `Game`**（与 M19 的「够不着返 False」同源）。

### 5. opt-in 默认零回归
- 不按 `T` 不进入瞄准，`aim_state.is_active()` 恒 `False` ⇒ `_handle_key` 走原有分支、
  `_colored` 不高亮、`draw` 不画光标 ⇒ 与 M29 逐字节一致。
- 瞄准模式只在 `light=True` 且 `switches=True` 时有意义（否则没有开关可瞄准）；
  未启用时按 `T` 友好提示「未启用开关模式（用 --light 启动）」、不进入。
- 默认 / 潜行 / 听觉 / 光照 / 手电 / Boss 演示不受影响（`balance_check` 不变）。

### 6. 渲染：终端 ANSI 高亮 + GUI 准星
- **终端 `--play`**：`_colored` 在瞄准模式下高亮光标格——用 ANSI 反相（`\x1b[7m...\x1b[27m`）
  或方括号包住该格字符。不改 `game.render()` 字形（#8 延伸）。
- **GUI `--gui` / 网页版**：`draw` 在画完地图 / 特效后，若 `aim_state.is_active()` 则画光标——
  目标格画十字准星 + 高亮边框（黄色方框 + 中心十字），并按 `game.can_toggle_switch` /
  `can_destroy_switch` 给颜色提示（绿=可射灭 / 红=可射碎 / 灰=够不着）。
  renderer 只读 `aim_state`、不写它（与 `self.effects` 同性质，#8 延伸）。

## 备选方案与取舍
- **方案 B：`_handle_key` 加可选 `aim_state` 参数**——破坏 M21 钉死的 `_handle_key(game, key)`
  签名，需改 `tests/test_interactive.py` 15 例 + `tests/test_gui.py` 29 例，回归风险大。**否决**。
- **方案 C：renderer 持有瞄准状态**——`renderer.run(_handle_key)` 把 `_handle_key` 注入 renderer，
  renderer 拦截方向键、不让 `_handle_key` 看到——但这破坏「`_handle_key` 与终端 `--play` 同构」
  （#2 不变式的关键），且终端 `--play` 没有 renderer、无法瞄准。**否决**。
- **方案 D：把瞄准状态塞进 `Game`**——`Game.aim_cursor` 字段——但这污染 `Game` 核心状态、
  破坏 `to_dict` / `apply_state`（M26 存档要序列化它）、破坏 `render()` 纯净性（#8）。
  瞄准是控制层概念、不属于玩法状态。**否决**。
- **选定方案 A**：模块级 `aim_state` 控制层视图状态，`main` 和 `render_pygame` 都 import 它。
  不破坏任何既有签名、不污染 `Game`、不引入循环导入、`reset()` 可复位测试隔离。

## 后果
- **正向**：玩家在 `--play` / `--gui` / 网页版下都能手动瞄准射灭 / 射碎开关，潜行玩法核心决策权
  交到玩家手里；终端与 GUI / 网页版控制完全一致（共用 `_handle_key`，#2 不破）。
- **负向**：新增模块级可变状态 `aim_state`（与 `main.SAVE_BACKEND` 同性质），测试需 `reset()`
  复位保证用例隔离——`tests/test_aim_mode.py` 的 `setUp` 已 `aim_state.reset()`。
- **风险**：瞄准模式下 `Q` 退出瞄准而非退出游戏，是「模态」语义——玩家需学习。
  缓解：进入瞄准时打印操作说明、`?` 帮助里写清。

## 关联
- 工单：`docs/工单/T-030-交互式射灯碎灯UI.md`
- 不变量：`docs/不变量.md` #30
- 上游：M19（`LightSwitch` 实体 + `toggle_switch` / `destroy_switch` API）、M14/M16（光照场逻辑）、
  M21（`_handle_key` 控制层）、M22（`PygameRenderer` 视图层）、M28（网页化 `async_run`）、M29（localStorage 存档）
- 下游：未来可扩展瞄准模式到「指定蛛网弹目标」「指定摆荡突袭落点」（候选 ②「更多蜘蛛侠招式」的瞄准 UI 复用本里程碑的 `aim_state`）。
