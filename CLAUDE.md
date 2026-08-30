# CLAUDE.md · 终端 Roguelike（AI Coding 标准方法示范）

> 本仓库用 `ai-coding-method` 的七件套 + 流水线从 0 搭建。
> **新会话第一步：读本文档 → 按 `docs/工单/` + `docs/接力/` 接手下一个里程碑。**
> 不要靠聊天记录；记忆都在 `docs/` 里。

## 项目一句话
终端（ASCII）Roguelike 地牢探险；以「最新蜘蛛侠（Spider-Man，MCU 荷兰弟 / Tom Holland 风格）」为主角与美术基调（红蓝战衣、蛛网摆荡、纽约都市地牢）。一个人用标准 AI Coding 方式持续迭代。

## 技术栈（决策见 ADR-001）
- 语言：Python 3.11+；测试：unittest（零依赖）；渲染：终端 ASCII
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
- 下一步候选（M20 已完成「光照影响蜘蛛感应半径」，核心光照/感知/视野体系 M6–M20 收尾）：**无更多接力登记项**。如需新里程碑，按流程在 `docs/工单/` + `docs/adr/` + `docs/不变量.md`（#1–#20）登记后再开工。

## 七件套索引（只放指针）
- ① 本文档（根索引）
- ② 工单：`docs/工单/T-001-格子与移动.md` … `docs/工单/T-019-灯开关独立实体.md`
- ③ 接力：`docs/接力/HANDOFF-T001.md`（含 commit + 下一步；**全程只有这一根棒**，勿按里程碑新建）
- ④ ADR：`docs/adr/ADR-001-技术选型.md`、`docs/adr/ADR-002-视野与渲染层.md`、
  `docs/adr/ADR-003-怪物感知与潜行.md`、`docs/adr/ADR-004-噪音与听觉.md`、
  `docs/adr/ADR-005-主动制造响动.md`、`docs/adr/ADR-006-ANSI颜色高亮.md`、
  `docs/adr/ADR-007-光照衰减.md`、`docs/adr/ADR-008-随身手电.md`、
  `docs/adr/ADR-009-光照影响玩家视野.md`、`docs/adr/ADR-010-可开关的房间灯.md`、
  `docs/adr/ADR-011-怪物追击修正与配平.md`、`docs/adr/ADR-012-可破坏的房间灯.md`、
  `docs/adr/ADR-013-环境光照场分离.md`、`docs/adr/ADR-014-怪物感知改用环境场.md`、
  `docs/adr/ADR-015-灯开关独立实体.md`、`docs/adr/ADR-016-光照影响蜘蛛感应半径.md`
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
