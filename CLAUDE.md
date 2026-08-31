# CLAUDE.md · 终端 Roguelike（AI Coding 标准方法示范）

> 本仓库用 `ai-coding-method` 的七件套 + 流水线从 0 搭建。
> **新会话第一步：读本文档 → 按 `docs/工单/` + `docs/接力/` 接手下一个里程碑。**
> 不要靠聊天记录；记忆都在 `docs/` 里。

## 项目一句话
终端（ASCII）Roguelike 地牢探险；以「最新蜘蛛侠（Spider-Man，MCU 荷兰弟 / Tom Holland 风格）」为主角与美术基调（红蓝战衣、蛛网摆荡、纽约都市地牢）。一个人用标准 AI Coding 方式持续迭代。

## 技术栈（决策见 ADR-001）
- 语言：Python 3.11+；测试：unittest（零依赖）；渲染：核心 ASCII 模型 + Pygame GUI 视图层（M22 起，`--gui` 进窗口，首个第三方依赖 pygame）；终端 ASCII 仍保留作 `--play` 回归基线
- 随机：**必须经 Seed 注入**（见 `docs/不变量.md` #1）
- 视野（M6）：纯几何、零随机；**默认关闭**，`Game(..., fov=True)` 显式开启（见 `docs/不变量.md` #8）
- 潜行（M7）：怪物感知是纯几何、零随机、双向视线；**默认关闭**，`Game(..., stealth=True)` 显式开启（见 `docs/不变量.md` #9）
- 听觉（M8）：声音传播是纯几何、零随机的 Dijkstra 噪声场（空地 1 / 墙 3、会绕路）；**默认关闭**，`Game(..., noise=True)` 显式开启（见 `docs/不变量.md` #10）

## 当前里程碑
- M1 格子地图 + 玩家移动（已提交，见 `docs/接力/HANDOFF-T001.md`）
- M2 战斗系统（已完成，见 `docs/工单/T-002-战斗系统.md`）
- M3 怪物 AI（已完成，见 `docs/工单/T-003-怪物AI.md`）：追击 / 随机游走，确定性（#1/#2/#4）
- M4 道具与背包（已完成，见 `docs/工单/T-004-道具与背包.md`）：拾取 / 使用 / 击杀掉落，背包容量上限 #5、HP 不超上限 #6
- M5 程序化关卡（已完成，见 `docs/工单/T-005-程序化关卡.md`）：房间+走廊生成、自动撒怪撒道具、楼梯下潜（#1/#2/#4/#7）
- M6 视野 / 渲染层（已完成，见 `docs/工单/T-006-视野与渲染层.md`）：迷雾 + 房间照明 + 蜘蛛感应（#1/#2/#8）
- M7 怪物视野与潜行（已完成，见 `docs/工单/T-007-怪物视野与潜行.md`）：怪物感知 + 警觉状态机 + 倒挂突袭（#1/#2/#9）
- M8 噪音与听觉（已完成，见 `docs/工单/T-008-噪音与听觉.md`）：声音传播 + 四个声源 + 声源误导（#1/#2/#10）
- M9 主动制造响动（已完成，见 `docs/工单/T-009-主动制造响动.md`）：皇后区垃圾桶盖 + 投掷几何 + 主动调虎离山（#1/#2/#11）
- M10 ANSI 颜色高亮（已完成，见 `docs/工单/T-010-ANSI颜色高亮.md` / `docs/adr/ADR-006-ANSI颜色高亮.md`）：纯展示层上色（`src/rogue/color.py` + `main.py`），不进 `Game`/`render()`，默认 TTY 自动、`--color`/`--no-color` 可强制（#8 渲染纯净性延伸）
- M11 光照衰减（已完成，见 `docs/工单/T-011-光照衰减.md` / `docs/adr/ADR-007-光照衰减.md`）：纯几何光照场（`src/rogue/light.py`）+ 明暗梯度（展示层上色）+ 暗处缩短怪物感知半径，默认关闭、`--light` 显式开启（#1/#2/#8/#12）
- M12 随身手电（已完成，见 `docs/工单/T-012-随身手电.md` / `docs/adr/ADR-008-随身手电.md`）：玩家可开关的随身动态光源（`Game.toggle_flashlight`，默认关闭、opt-in）；开灯照亮四周（同时让自己更易被暗处的怪察觉），关灯退回微光摸黑潜行；纯几何零随机、只缩短怪物感知、不破坏 #9 对称；`render()` 字形一字不差（#13）
- M13 光照影响玩家自身视野（已完成，见 `docs/工单/T-013-光照影响玩家视野.md` / `docs/adr/ADR-009-光照影响玩家视野.md`）：光照开启且视野开启时，玩家视野半径按**目标格光照**衰减（暗 2 / 昏暗 4 / 明 8）——暗处看不远、亮处看得清；与 M11「暗处缩短怪物感知」对称；按目标格光照算（绕开「玩家微光让脚下恒 LIT」陷阱）；纯几何零随机、默认关闭、#9 对称硬性质不破（#14）
- M14 可开关房间灯（已完成，见 `docs/工单/T-014-可开关的房间灯.md` / `docs/adr/ADR-010-可开关的房间灯.md`）：蛛网射中房间中心灯的拉链翻转该房间的灯（关灯变暗 / 开灯恢复）；关灯只移除光源（不新增）⇒ #9/#12/#14 不破；拉链轻响从灯处传出（M8 调虎离山）；纯几何零随机、默认关闭（light=False ⇒ no-op，与 M1~M13 逐字节一致）（#15）
- M15 怪物追击修正与攻击配平（已完成，见 `docs/工单/T-015-怪物追击修正.md` / `docs/adr/ADR-011-怪物追击修正与配平.md`）：M3 老追击路径 `_step_toward` 改用切比雪夫二次关键字（close_in=True），修掉玩家轴向往复时怪锁轴震荡、永不贴上的 bug，与潜行分支统一；威胁上升故怪物攻击各降 1（1~3 → 0~2）配平——只修不配平 26/30→22/30，配平后默认 30/30 / 潜行 28/30；纯几何零随机（#2 不变）、默认追击行为预期改变（核心玩法修正）
- M16 可破坏的房间灯（已完成，见 `docs/工单/T-016-可破坏的房间灯.md` / `docs/adr/ADR-012-可破坏的房间灯.md`）：在 M14 翻转式灯开关之上加「蛛网射碎灯泡，一次性不可逆」——新增 `destroyed_lights` 集合 + `can_destroy_light`/`destroy_light`（纯几何、零随机、默认关闭、换层重置）；`_light_sources` 同时跳过 `switched_lights` 与 `destroyed_lights`（只移除光源、不新增 ⇒ #9/#12/#14 不破）；已碎灯不可再 toggle、可作用于已关灯房间 ⇒ 永久黑暗；碎裂轻响 `NOISE_SHATTER_BULB=3` 从灯处传出（调虎离山）；测试 432 例全绿（不变量 #16）
- M17 环境光照场与完整光照场分离（已完成，见 `docs/工单/T-017-环境光照场分离.md` / `docs/adr/ADR-013-环境光照场分离.md`）：`update_light()` 同源、幂等重算两份场——`ambient_field`（仅房间灯，不含玩家微光/手电，静态环境照明）与 `light_field`（房间灯 + 微光 + 手电，完整场）；新增 `_ambient_sources` 与只读查询 `ambient_level_at`（与 `light_level_at` 对称，光照关闭恒「明亮」）；**默认所有玩法/渲染判定仍走完整场** ⇒ 行为零回归（gate 432 → 443，演示逐字节一致，不变量 #17）
- M18 怪物感知改用环境场（已完成，见 `docs/工单/T-018-怪物感知改用环境场.md` / `docs/adr/ADR-014-怪物感知改用环境场.md`）：M11 怪物感知半径判定从完整场 `light_level_at` 改走「怪物感知光场」`monster_light_level_at`（**仅房间灯 + 随身手电，不含玩家被动微光**），修正「被动微光把附近暗处怪照成近视眼反面」的隐性副作用；新增 `_monster_light_sources` / `monster_light_field` / `monster_light_level_at`，由 `update_light()` 同源、幂等重算；有效半径恒 ≤ `MONSTER_SIGHT_RADIUS` ⇒ #9 对称硬性质不破、手电双刃（M12）保留；`light=False` 三条演示与 M17 逐字节一致、`--light`/`--flashlight` 演示仍通关（gate 443 → 445，不变量 #18）
- M19 灯开关独立实体（已完成，见 `docs/工单/T-019-灯开关独立实体.md` / `docs/adr/ADR-015-灯开关独立实体.md`）：墙边开关 `LightSwitch` 实体与天花板灯具 `room.center` 分离的独立控制手柄；**保留 M14 `toggle_light` / M16 `destroy_light` API 不动**，平行新增 switch API（`switch_at` / `can_toggle_switch` / `toggle_switch` / `can_destroy_switch` / `destroy_switch` / `switch_light_is_on`，纯几何零随机、默认关闭）翻同一份 `switched_lights`/`destroyed_lights`（按 `room.center` 记录）⇒ 完全复用 M14/M16 光照场逻辑、行为零回归；几何约束瞄准「开关格」的 `has_line_of_sight` + 切比雪夫 ≤ `WEB_LIGHT_RANGE`；声源仍在灯具处（`NOISE_TOGGLE_LIGHT=3` / `NOISE_SHATTER_BULB=3` 从 `room.center` 传出，M8 调虎离山成立）；`main.py` 设 `switches=light`，`--light --stealth` 下 `step 0b` 改为蛛网射碎未察觉敌人所在房间**墙边开关**的灯泡（永夜摸黑接近，行为等价于 M18 射碎灯具）；`render()` 全图/迷雾画 `=`、已碎退回 `#`、不改写 world state（#8 延伸）；opt-in（`switches=False` ⇒ 默认/潜行/听觉三条演示与 M18 逐字节一致）；测试 445 例 → 478 例全绿（不变量 #19）
- M20 光照影响蜘蛛感应半径（已完成，见 `docs/工单/T-020-光照影响蜘蛛感应半径.md` / `docs/adr/ADR-016-光照影响蜘蛛感应半径.md`）：M6 的蜘蛛感应（穿墙预警 `?`）半径原本恒为 `SPIDER_SENSE_RADIUS=4`、不受光照约束；M20 起 `light=True` 时按怪物所在格光照衰减（暗 2 / 昏暗 3 / 明 4），与 M11 怪物感知、M13 玩家视野形成「黑暗三重削弱」对称；纯几何、零随机、`fov.spider_sense_radius` 只缩短不放大、恒 ≤ 4；默认关闭（`light=False` ⇒ 半径恒 4，与 M1~M19 逐字节一致）；暗处保留最小半径 2 避免彻底无预警；`render()` 字形一字不差（#8 延伸）；测试 478 例 → 506 例全绿（不变量 #20）
- M21 可键盘操作玩法（已完成，见 `docs/工单/T-021-可键盘操作玩法.md` / `docs/adr/ADR-017-可键盘操作玩法.md`）：把「只能看脚本自动驾驶 demo」变成「能自己上手玩、开发中可实测」——`main.py` 新增 `_handle_key`（按键→动作，撞怪即攻击 bump-to-attack、`g` 拾取、`1~5` 用道具、`e` 蛛网摆荡突袭、`f` 手电、`>` 下潜、空格/`.`/回车等待、`?` 帮助、`q` 退出）+ `_player_interactive`（渲染→读键→执行→怪物回合，判定 win/dead/quit）+ `main()` 的 `--play` 开关（默认仍走 `_player_act` 自动驾驶 demo，零回归）；纯几何、零随机（只调 Game 既有方法）、move 保持 4 向（#4）、有效动作耗回合/无效键不耗（#2）、操作说明内置；测试 506 例 → 521 例全绿（不变量 #21）
- M22 Pygame GUI 渲染层（已完成，见 `docs/工单/T-022-GUI渲染层.md` / `docs/adr/ADR-018-GUI渲染层.md`）：把「ASCII 终端视图」换成「真实 Pygame 窗口」——新增 `src/rogue/render_pygame.py` 的 `PygameRenderer`（只读 `Game` 公开状态、逐帧画窗口、主循环 `run(_handle_key)` 与 `--play` 终端路径同构），`main.py` 新增 `--gui` 开关（延迟 import，opt-in），`--play` 终端模式保留作 headless 回归基线；引入首个第三方依赖 `pygame`（`requirements.txt`）；纯几何零随机、不改 `Game` 一字（#1/#2/#8 延伸），GUI 与终端对同 seed+同输入序列产生同结果（#2，机器判定 `tests/test_gui.py`）；测试 521 例 → 533 例全绿（不变量 #22）
- M23 Spider-Man 主题化 GUI 渲染（已完成，见 `docs/工单/T-023-主题化GUI渲染.md` / `docs/adr/ADR-019-主题化GUI渲染.md`）：把 M22 的纯色块升级为**程序化蜘蛛侠主题**——玩家画面具（红底+黑蛛网+白眼）、蛛网地板/纽约砖墙贴图、怪物 `M/m/~` 与道具按 key 主题图标、蜘蛛感应红色脉冲、攻击蛛网特效+命中白闪、合成音效（thwip/闷响，懒初始化静默）、主题 HUD；美术**全程序化、零素材依赖**；红线不变（只读 Game、零随机、不改 `Game` 一字）；`tile_color`/`pixel_pos`/`translate_key` 行为不变；`tests/test_gui.py` 12 例 → 20 例、gate 533 例 → 541 例全绿（不变量 #23）
- M24 Spider-Man 主题美术再升级 · 动画 + 美术 + 音效（已完成，见 `docs/工单/T-024-美术动画升级.md` / `docs/adr/ADR-020-美术动画升级.md`）：在 M23 程序化美术上叠加**帧动画**（地形多帧微动、玩家呼吸/突进/受击红闪、怪物浮动/眨眼、蛛网行进+火花迸发、蜘蛛感应扩散环、暗角+开灯光晕）与**音效升级**（脚步/摆荡 whoosh/感应刺痛/胜负 stings），全部 `self.frame` 计数器驱动、零随机、纯视图状态；`tile_color`/`pixel_pos`/`translate_key`/`apply_keys` 契约不变；红线不变（#1/#2/#8 延伸）；`--gui` 仍 opt-in（不变量 #24）
- M25 Boss 战与胜利条件闭环（已完成，见 `docs/工单/T-025-Boss战与胜利条件闭环.md` / `docs/adr/ADR-021-Boss战与胜利条件闭环.md`）：把「无限下潜」收口成一局完整的胜负——最终层（由 `main.py --boss` 触发）确定性刷出绿魔（Green Goblin）Boss（HP 30 / 攻击 3 / 半血暴怒 +1，纯几何、零随机、不占 rng），击败绿魔才算真正通关；`Monster.boss` 标志 + `Game.boss`/`boss_depth` 开关（opt-in，默认关闭 ⇒ 与 M24 逐字节一致）、渲染恒画 `B`、`Game.is_victory()` 胜利闭环；红线不变（#1/#2/#8 延伸）；gate 541→564 全绿、演示 `--boss` 第 171 回合击败绿魔 HP 10/20（不变量 #25）
- M26 存档 / 读档（已完成，见 `docs/工单/T-026-存档读档.md` / `docs/adr/ADR-022-存档读档.md`）：把「关掉即丢」变成「可随时存、关掉再读档接着玩」——保存「seed + PRNG 内部状态 + 全部玩法状态」（`Game.to_dict`/`apply_state`/`from_dict`/`save`/`load`/`load_into` + `RandomSource.get_state/set_state`），读档后续演化与「从未存读、并行推进」完全一致（不变量 #26，同存档+同后续输入⇒同终态）；`--play`/`--gui` 下按 S 存、L 读；gate 564→574 全绿（不变量 #26）
- M27 序列帧 Sprite（已完成，见 `docs/工单/T-027-序列帧Sprite.md` / `docs/adr/ADR-023-序列帧Sprite.md`）：把 M24 程序化地形贴图换成 `tiles/*.png` 序列帧——`render_pygame.py` 地形绘制抽成模块级 `_make_floor_surface`/`_make_wall_surface`/`_make_unseen_surface`，`_load_tile_sprites` 从 `tiles/*.png` 加载并按 cell 缩放、`_build_tiles` 优先用 PNG、缺文件回退同款程序化（视觉与 M24 逐像素一致）；`scripts/gen_tiles.py` 确定性烘焙 20 张 PNG（floor/wall 各 lit/dim ×4 帧 + unseen ×4 帧，BASE=64，零随机）；`tests/test_gui.py` 增 4 例（资产存在/PNG 加载/逐像素一致防漂移/缺文件回退）；评审 `allowed_dirs` 加 `tiles`；不变量 #27（确定性产物、加载零随机、缺文件回退、视觉零差异）；gate 574→578 全绿（实现 commit `291ebd2`）
- M28 网页化（Pygbag）（已完成，见 `docs/工单/T-028-网页化Pygbag.md` / `docs/adr/ADR-024-网页化Pygbag.md`）：把 M22 起的 Pygame 窗口原样打包成 wasm——新增 `web.py` 浏览器入口 + `PygameRenderer.async_run` 异步主循环（每帧 `await asyncio.sleep(0)` 让出浏览器事件循环）+ `build_wasm.bat`/`build_wasm.sh` 构建脚本 + `requirements-web.txt`；游戏核心（`Game`/`render()`/`_handle_key`）一字未改、零新增随机（#1/#2/#8 延伸）；`run`/`async_run` 共用 `_pump_events` ⇒ 同 seed+同输入序列同结果（#28）；gate 578→580 全绿（不变量 #28）
- M29 网页版 localStorage 存档（已完成，见 `docs/工单/T-029-网页版localStorage存档.md` / `docs/adr/ADR-025-网页版localStorage存档.md`）：把网页版存档的**传输层**从 pygbag `/data`（IndexedDB）切换到浏览器原生 `platform.window.localStorage`（固定键 `spiderman_roguelike_save_v1`）——新增 `src/rogue/web_storage.py` 可插拔后端（`LocalStorageBackend` 浏览器 / `FileSaveBackend` 桌面回退 / `get_default_backend` 按环境自动选）；`main.SAVE_BACKEND` 接线（`_handle_key` 的 S/L 改走 `SAVE_BACKEND.save/load_into`、不再写死 `SAVE_PATH`）、`web.py` 显式注入、新增 `play_web.bat`/`play_web.sh` 双击启动网页入口；序列化仍走 M26 `Game.to_dict`/`apply_state` 确定性排序导出 ⇒ localStorage 往返与文件往返 dict 层面逐字节等价（#26）、桌面与 M26 逐字节一致；纯 I/O、零随机、不写 `Game`（#1/#2/#8 延伸）；`tests/test_web_storage.py` 11 例全绿、gate 580→591 全绿（不变量 #29）
- M30 交互式射灯 / 碎灯 UI（已完成，见 `docs/工单/T-030-交互式射灯碎灯UI.md` / `docs/adr/ADR-026-交互式射灯碎灯UI.md`）：把 M19「射灭 / 射碎墙边开关」的决策权从 demo 自动战术交还玩家——新增 `src/rogue/aim_state.py` 控制层视图状态（模块级 `_AIM` 字典，不属于 `Game`，与 `PygameRenderer.effects` 同性质）+ `main._handle_key` 瞄准模式分支（`T` 进入 / 方向键移光标 / `Enter` 射灭 / `X` 射碎 / `T`·`Q`·`Esc` 退出）+ `render_pygame._draw_aim_cursor` 准星（黄色方框 + 几何约束颜色十字）；**瞄准不消耗回合**（进入 / 退出 / 移动光标都不调 `monster_turn`，只有确认射灭 / 射碎成功才消耗回合——潜行核心：玩家可反复瞄准不惊动敌人）；几何约束复用 M19 的 `can_toggle_switch`/`can_destroy_switch`（够不着 ⇒ `acted=False`、不耗回合、不改 `Game`）；纯几何零随机、不写 `Game`（#1/#2/#8 延伸）、opt-in 默认零回归（不按 `T` 与 M29 逐字节一致）；`tests/test_aim_mode.py` 27 例全绿、gate 591→618 全绿（不变量 #30）
- 下一步候选（M30 交互式射灯已落地）：① ~~交互式射灯/碎灯/墙边开关的目标选择 UI（已完成，见 M30）~~；② 更多蜘蛛侠招式（AoE 蛛网束缚 / 可指定落点摆荡位移，可复用 M30 的 `aim_state` 瞄准 UI）；③ 移动端触屏 / 虚拟按键支持（Pygbag 触屏事件，让手机浏览器也能玩）；④ 把 README/CLAUDE.md 七件套索引对齐到 M30 现状（README 里程碑表目前只到 M8，可补 M9~M30 摘要）。

## 七件套索引（只放指针）
- ① 本文档（根索引）
- ② 工单：`docs/工单/T-001-格子与移动.md` … `docs/工单/T-030-交互式射灯碎灯UI.md`
- ③ 接力：`docs/接力/HANDOFF-T001.md`（含 commit + 下一步；**全程只有这一根棒**，勿按里程碑新建）
- ④ ADR：`docs/adr/ADR-001-技术选型.md` … `docs/adr/ADR-026-交互式射灯碎灯UI.md`（共 26 份：技术选型 / 视野 / 潜行 / 噪音 / 响动 / 颜色 / 光照 / 手电 / 光照影响视野 / 可开关灯 / 追击修正 / 可破坏灯 / 环境场 / 怪物感知环境场 / 灯开关实体 / 蜘蛛感应光照 / 可键盘操作 / GUI / 主题化GUI / 美术动画 / Boss战 / 存档 / 序列帧Sprite / 网页化 / localStorage存档 / 交互式射灯碎灯UI）
- ⑤ 不变量（红线）：`docs/不变量.md`
- ⑥ 术语表：`docs/术语表.md`
- ⑦ 地图：`docs/地图.md`

## 流水线（墙）
- L1 墙四道门：`scripts/gate.py`（编译 → seed-guard → 测试 → 覆盖率棘轮）
- 提交瞬间拦截：`scripts/hooks/pre-commit`
- 评审流水线 5 监理：`scripts/review_pipeline.py`
- CI：`.github/workflows/ci.yml`（见 `scripts/gate.py`）
- 合并门：`CODEOWNERS` + `.github/branch-protection.md` + `.github/PULL_REQUEST_TEMPLATE.md`

## 铁律（每次改动前）
1. 跑 `python scripts/gate.py`，全绿才提交。
2. **禁止裸调 `random`/`secrets`/`os.urandom`**——随机必须走 `src/rogue/rng.py` 的 `RandomSource`（Seed 注入）。
3. 一个里程碑 = 一次提交；提交前更新接力文件（含本次 commit）。
4. 绝不改/删测试凑绿（熔断②）。
