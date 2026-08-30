# ADR-018 · Pygame GUI 渲染层（M22）

## 状态
已采纳（M22）

## 背景
M1~M21 把游戏做成了**终端 ASCII Roguelike**——黄金层（`Game` + `rng/level/fov/sound/light`，
21 里程碑、红线 #1~#21）全在，视图层只是 `Game.render()`（ASCII）+ `color.py`（终端上色）+ `--play` 循环。
用户明确「不要 ASCII 终端游戏，要真正能玩的游戏」，于是需要把视图层换成真实窗口渲染。

约束与 M1~M21 同款：
- 熔断②禁止改/删测试凑绿 ⇒ 既有 521 例不能破；
- 不变量 #1/#2 ⇒ 任何新增随机都会让同 seed 的既有回放全部作废；
- 不变量 #8 渲染纯净性 ⇒ 视图层不改写游戏状态。

候选（AskUserQuestion）：
- **Pygame 桌面窗口（采纳）**：纯 Python，核心零改动；真实窗口 + 后续可加 Sprite/动画/音效；
  后续 Pygbag 可一键打包成网页；代价是引入第一个第三方依赖。
- Tkinter 桌面：零新依赖，但做游戏手感/动画差。
- Web（HTML5 Canvas）：浏览器可玩、易分享，但要把 `Game` 重写成 JS（对 #1/#2 红线有风险）
  或 Pyodide 在浏览器跑 Python（重、易卡）。

## 决策
- **保留黄金层，只换视图层（微型绞杀者 / strangler）**：`Game` 一行不改；新增 `PygameRenderer`
  只读 `Game` 公开状态、只调既有动作方法。这是「模式放大器」原则的直接应用——
  既有的 521 例规格与红线全部原样继承，新视图层是「外挂」而非「重写」。
- **字符网格直接消费 `game.render()`**：终端与 GUI 用的是**同一份 `render()` 输出**，字形零漂移；
  `PygameRenderer` 只负责「把每个字形按调色板画成色块」。因此 `render()` 既有的 `assertIn("@", render())`
  类断言全部成立，`--play` 终端模式与 `--gui` 窗口模式对同输入产生同结果。
- **主循环与 `--play` 终端路径同构**：GUI `run(handle_key)` 每帧只做
  「事件→按键 token→`_handle_key(game,token)`→(acted? `monster_turn()`)→draw」，
  而 `_handle_key` 就是终端 `--play` 用的同一个函数。两条路径共用同一套 Game 方法
  ⇒ 同 seed + 同输入序列 ⇒ 同结果（#2），可由 `tests/test_gui.py::test_apply_keys_parity_with_terminal` 机器判定。
- **`--gui` 为 opt-in，默认仍是脚本 demo / `--play` 终端**：`main.py` 延迟 import `PygameRenderer`
  （只在 `--gui` 分支），故 gate 不传 `--gui` 时不强制 pygame；`--play` 终端模式完整保留作 headless 回归基线。
- **调色板镜像 `color.py` 的 `GLYPH_COLORS`**：`@` 红 / `M` 品红 / `m` 暗品红 / `~` 蓝 / `?` 青 /
  `!` 黄 / `>` 绿 / `#` 暗灰 / `=` 黄，语义与终端一致；不可见记忆格压暗。
- **headless 测试友好**：pygame 模块顶部 import，但 `pygame.init()` 只在 `PygameRenderer.__init__` 调；
  测试设 `SDL_VIDEODRIVER=dummy` + `SDL_AUDIODRIVER=dummy`，pygame 缺失则整组 skip——不拖垮 gate。
- **v1 用纯色块**：墙=灰块、地板=深块、`@`=红块…，不做 Sprite 美术/动画/音效（留 M23）。

## 后果
- 优点：游戏第一次有「真正的窗口」——蜘蛛侠在窗口里可移动/攻击/拾取/下潜，HUD 显示 HP/背包/层/模式；
  且对 M1~M21 的 521 例规格与红线零侵入（门禁四道门全绿，测试 521 → 533）。
- 取舍：
  - v1 是色块不是 Sprite——美术质感留 M23（可换 `tiles/*.png` 贴图、加动画/音效），架构已为此留好接口
    （`tile_color` 是字形→RGB 的唯一映射点，未来改为字形→surface 即可）；
  - 光照的 GPU 明暗只在 `color.py` 的 ASCII 梯度里，GUI 暂未做光照色阶（M23 可在 `draw()` 按 `light_field` 压暗地形）；
  - 引入首个第三方依赖 `pygame`（写在 `requirements.txt`，CI/他人环境需 `pip install -r requirements.txt`）；
  - 未来若做网页版，走 Pygbag 打包（零改核心），不重写 `Game`。
