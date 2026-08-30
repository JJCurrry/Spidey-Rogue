# ADR-024 · 网页化（Pygbag 把 Pygame 窗口打包成 wasm，零改核心）

## 状态
已采纳（M28）

## 背景
M1~M27 把游戏做成「终端 ASCII + Pygame 窗口（M22 起）」双层视图，渲染层（M22 骨架 / M23 主题化 /
M24 动画美术音效 / M27 序列帧 Sprite）始终「只读 `Game`、只调既有动作方法、纯几何零随机」（#1/#2/#8 延伸）。
HANDOFF-T001 把「网页化（Pygbag 把 Pygame 打包成 wasm，零改核心）」列为 M27 之后的下一步候选，并强调
「零改核心」——这正是 Pygbag 的卖点：它把已有的 Pygame 程序原样编译成 wasm 在浏览器跑，不需要重写游戏。

约束与 M1~M27 同款：
- 熔断②禁止改/删测试凑绿 ⇒ 既有 578 例不能破；
- 不变量 #1/#2 ⇒ 任何新增随机都会让同 seed 的既有回放全部作废；
- 不变量 #8 渲染纯净性 ⇒ 视图层不改写游戏状态。

候选：
- **Pygbag 直接打包现有 PygameRenderer（采纳）**：只新增一个浏览器入口 `web.py` + 把主循环从同步 `run`
  抽出一个异步 `async_run`（每帧 `await asyncio.sleep(0)` 让出浏览器事件循环），游戏核心、`render()`、
  `_handle_key` 一字未动。零重写、确定性满分、与桌面/终端同构；构建由 `pygbag` 完成。
- 用 JavaScript 游戏引擎重写（Phaser / PixiJS 等）：美术可控，但要丢弃整套已验证的 Python 玩法内核与
  测试，违背「零改核心」与确定性纪律——否决。
- 用 PyScript 在浏览器跑 CPython（非 wasm Pygame）：能跑 Python 但 Pygame 在 PyScript 下的音频/事件循环
  支持不稳定，且不是「打包成静态 wasm 应用」的干净产物——否决。
- 仅保留终端 ASCII（不网页化）：与 HANDOFF 下一步候选冲突——否决。

## 决策
- **主循环抽成「共用帧处理 + 两种调度外壳」**：`_pump_events`（事件→token→step）与 `_check_ending(wait=)`
  抽出为 `run` / `async_run` 共用；`run`（桌面）保持同步、行为不变，`async_run`（浏览器）每帧
  `await asyncio.sleep(0)` 让出事件循环。两条路径逻辑零漂移 ⇒ 同 seed+同输入序列同终态（#2，#28）。
- **字体初始化加 try/except 回退**：`pygame.font.SysFont([...])` 失败时回退 `pygame.font.Font(None)`，
  保证 wasm/缺字体环境也能构造渲染器（#22/#23 纯净性延伸，不改桌面行为——桌面有这些字体时 SysFont 成功）。
- **浏览器入口 `web.py` 复用既有 API**：`Game.procedural` + `PygameRenderer.async_run(main._handle_key)`，
  旗标语义与 `main.py` 同款（默认全开展示），存档路径指向 pygbag 持久化目录 `/data`；`web.py` 不被 gate 扫描
  （不在 `src/`/`tests/`），且 import 不触发 `main()`（有 `__main__` 守卫）⇒ 门禁零影响。
- **构建脚本与依赖单列**：`build_wasm.bat` / `build_wasm.sh`（pygbag 预览 + `--build`）+ `requirements-web.txt`
  （pygbag>=0.4）；桌面窗口模式仍只依赖 `requirements.txt` 的 pygame，构建 wasm 才需要 pygbag。
- **不变式**：只读 `Game`、只调既有方法、不引入随机 ⇒ #1/#2/#8 延伸不破；
  `run`/`async_run` 共用内部方法 ⇒ 网页版与桌面/终端同构（#28）。

## 后果
- 优点：蜘蛛侠 Roguelike 现在能直接在浏览器里玩（Pygbag 打包成静态 wasm 应用，可托管任意静态服务器），
  游戏核心与 578 例测试全部复用、零回归；美术（程序化主题 + 序列帧 Sprite）/ 动画 / 音效全部保留；
  自包含、确定性满分（不变量 #28）。
- 取舍：
  - 仅新增一个入口文件 + 一个异步主循环方法 + 构建脚本，核心代码零改动；
  - 浏览器存档走 `/data`（pygbag 持久化 IndexedDB），是 opt-in（按 S 才触发），失败被 try/except 兜住；
  - `pygbag --build` 需联网下载 wasm 运行时，构建产物 `build/web/` 不含源码随机（确定性由 `Game` 保证）；
  - 网页版控制与桌面 `--gui` 完全一致（WASD/方向键移动、撞怪攻击、G 拾取、1-5 道具、E 突袭、F 手电、
    > 下潜、空格等待、? 帮助、Q 退出）。
