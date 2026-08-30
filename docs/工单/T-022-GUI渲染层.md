# T-022 · Pygame GUI 渲染层（M22）

## 一入一出（In/Out）
- **入**：用户明确「不应该是 ASCII 终端游戏，要做一个真正能玩的游戏」。Brownfield 考古确认
  黄金层 = `Game` + `rng/level/fov/sound/light`（M1~M21、红线 #1~#21 全在），**可替换层** =
  `Game.render()` + `color.py` + `main.py` 的 `--play` 循环（仅视图）。选型（AskUserQuestion）定为
  **Pygame 桌面窗口**——保留 Python 核心零改动、风险最低，后续可用 Pygbag 打包成网页。Tkinter / Web 被否。
- **出**：把 ASCII 视图层换成真实窗口渲染，核心 `Game` 一行不改——
  1. 新增 `src/rogue/render_pygame.py`：`PygameRenderer` 类——只读 `Game` 公开状态、逐帧画窗口、
     主循环 `run(handle_key)`；调色板镜像 `color.py`；坐标↔像素等纯函数便于单测。
  2. `main.py` 新增 `--gui` 开关：延迟 import `PygameRenderer` 并 `run(_handle_key)`，替换 `--play` 分支；
     `--play` 终端模式保留作 headless 回归基线（行为零回归）。
  3. `tests/test_gui.py` 12 例（headless `SDL_VIDEODRIVER=dummy` 守卫、pygame 缺失则 skip）：
     纯函数 / 键位映射 / **确定性回归**（GUI 路径与 `--play` 终端路径对同 seed+同输入序列产生同结果）。
  4. 首个第三方依赖 `pygame`（新增 `requirements.txt`）。

## 委托级别
- **S（自主完成）**：范围清晰（新增一个视图模块 + main 一个分支 + 一组测试，不碰 `src/rogue` 既有逻辑）、
  红线明确（#1 零随机 / #2 确定性 / #8 渲染纯净）、复用 M21 的 `_handle_key`、
  是「让游戏真正能看能玩」这一用户诉求的落地。

## 验收分级
- **A（必过，门禁）**：`tests/test_gui.py` 12 例全绿——
  - **只读不写**：renderer 只调 `Game` 既有方法、不引入随机（#1/#8 延伸）；`tile_color`/`pixel_pos` 纯函数确定性；
  - **键位映射**：方向键→w/a/s/d、WASD/hjkl/数字/特殊键→`_handle_key` 同构 token；ESC 忽略；
  - **确定性回归（不变量 #2）**：`test_apply_keys_parity_with_terminal` 证明 GUI `apply_keys` 与
    `--play` 终端 `_handle_key+monster_turn` 对同 seed+同输入序列产生完全相同的 HP/位置/层数/存活怪数/背包；
  - `python scripts/gate.py` 四道门 ALL GREEN，棘轮 521 → 533。
- **B（建议）**：`python main.py --gui` 打开窗口，WASD/方向键可移动/攻击/拾取/下潜，
  HUD 显示 HP/背包/层/模式；`python main.py`（无 `--gui`）演示与 M21 逐字节一致（零回归）。

## 范围边界
- **只换视图层，不动玩法内核**：`PygameRenderer` 只读 `Game` 公开属性、只调 `_handle_key`（与终端同函数）
  + `monster_turn`，不新增任何随机、不修改 `src/rogue/*`（熔断②友好，既有 521 例零回归）。
- **字符网格消费 `game.render()`**：终端与 GUI 同一份字形，零漂移；调色板镜像 `color.py` 的 `GLYPH_COLORS`。
- **headless 友好**：pygame 在模块顶部 import，但 `pygame.init()` 只在 `PygameRenderer.__init__` 调；
  `main.py` 延迟 import 本模块 ⇒ gate 不传 `--gui` 时不强制 pygame；测试用 dummy driver + skip 守卫。
- **v1 用纯色块**（墙=灰块、地板=深块、`@`=红块…），不做 Sprite 美术/动画/音效（留 M23）。
- **迷雾**：`game.render()` 已按 `visible/explored` 出字形；GUI 只按可见性压暗记忆格，零额外逻辑。
- **opt-in（默认关闭）**：`--gui` 才进窗口；默认仍是脚本自动驾驶 demo（`--play` 终端模式保留），零回归。

## 不变量增量
- **#22 GUI 视图层纯净**：`PygameRenderer` 只读 `Game` 公开状态、只调 `Game` 既有确定性方法（经 `_handle_key`），
  不引入任何随机 ⇒ #1/#2 不变；消费 `game.render()` 同一份字形、不改写状态 ⇒ #8 延伸；
  GUI 主循环与 `--play` 终端路径同构（共用 `_handle_key`）⇒ 同 seed+同输入序列⇒同结果（#2，机器判定 `tests/test_gui.py`）；
  `--gui` 为 opt-in，默认（无 `--gui`）仍走脚本 demo / `--play` 终端，行为零回归。
