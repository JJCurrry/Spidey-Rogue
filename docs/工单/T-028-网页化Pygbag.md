# T-028 · 网页化（Pygbag 把 Pygame 窗口打包成 wasm，零改核心）

## 一入一出（In/Out）
- **入**：HANDOFF-T001「下一步候选」明确——「网页化（Pygbag 把 Pygame 打包成 wasm，零改核心）」。
  M22 已把 ASCII 视图换成 Pygame 窗口（`PygameRenderer`），渲染层只读 `Game` 公开状态、只调既有动作方法、
  纯几何零随机（#1/#2/#8 延伸）。Pygbag 正是把「已有 Pygame 程序」原样跑在浏览器 wasm 里的官方工具，
  本里程碑只做「窗口调度适配 + 浏览器入口 + 构建脚本」，不碰任何游戏核心。
- **出**：
  1. `src/rogue/render_pygame.py`：抽出 `_pump_events`（事件→token→step 的共用帧处理）与 `_check_ending(wait=)`；
     新增 `async_run`（异步主循环，每帧 `await asyncio.sleep(0)` 让出浏览器事件循环，避免 wasm 单线程卡死）；
     字体初始化加 `try/except` 回退 `pygame.font.Font(None)`，提升 wasm/缺字体环境的健壮性。
     `run`（桌面同步）行为完全不变（共用同一套内部方法）。
  2. 新增 `web.py`（仓库根）：浏览器入口。`async main` 构造 `Game.procedural` + `PygameRenderer.async_run(_handle_key)`，
     复用 `main._handle_key` 与同款旗标语义（默认全开展示）；存档路径落到 pygbag 持久化目录 `/data`。
  3. 新增 `build_wasm.bat` / `build_wasm.sh`（pygbag 预览 + `--build` 静态包）与 `requirements-web.txt`（pygbag>=0.4）。
  4. `tests/test_gui.py` 增 M28 用例：`async_run` 在 headless dummy 下处理 QUIT 返回 "quit"、? 被正确消费、
     Game 状态不被破坏（hp/depth 不变）——为网页化不变式提供机器判定。

## 委托级别
- **S（自主完成）**：范围清晰（只换主循环调度方式，不动 `Game`/`render()` 字形/优先级/玩法）、
  红线明确（#1 零随机 / #2 确定性 / #8 渲染纯净）、复用 M22 既有的「只读 Game」接口、
  是 HANDOFF 已登记的下一步候选，无歧义。

## 验收分级
- **A（必过，门禁）**：`tests/test_gui.py` M28 新增用例全绿——
  - **只读不写**：`async_run` 与 `run` 共用 `_pump_events` / `step` / `draw` / `_check_ending`，
    renderer 仍只读 `Game`、只调既有方法、不引入随机（#1/#2/#8 延伸）；
  - **同构不变式**：`web.py` 复用 `main._handle_key` 与 `Game.procedural`，零新增随机；
    同 seed + 同按键序列 ⇒ 同结果（#2 精神，#28）；
  - `python scripts/gate.py` 四道门 ALL GREEN，棘轮 578 → 580；
  - `web.py` 在 headless dummy 下可 import、可构造 Game、可解析旗标（冒烟验证，不依赖浏览器）。
- **B（建议）**：`pygbag web.py` 能起本地预览、`pygbag --build web.py` 产出 `build/web/` 静态包
  （需联网下载 wasm 运行时；本环境若网络受限则仅文档化，不影响核心验收 A）。

## 范围边界
- **只换主循环调度，不改玩法/字形/优先级**：`async_run` 与 `run` 是同一套渲染/动作逻辑的不同「调度外壳」；
  事件处理（`_pump_events`）、单步（`step`）、绘制（`draw`）、结局判定（`_check_ending`）三者完全共用，
  杜绝逻辑漂移 ⇒ 网页版与桌面版、与终端 `--play` 对同 seed+同输入序列产生同终态（#2）。
- **异步让出是 wasm 必需**：浏览器 wasm 是单线程，主循环不 `await asyncio.sleep(0)` 就会独占线程、页面卡死；
  `await` 只在帧末与「等任意键」处发生，不插入任何游戏逻辑 ⇒ 确定性不受影响（#28）。
- **字体健壮性**：wasm 环境未必有「Microsoft YaHei / Consolas」等字体，`SysFont` 失败时回退内置默认字体
  （`pygame.font.Font(None)`），保证任何环境都能构造渲染器、不依赖特定字体存在（#22/#23 纯净性延伸）。
- **存档落 /data**：浏览器只读文件系统下，`web.py` 把 `_handle_key` 的存档路径指向 pygbag 持久化目录 `/data`
  （映射到 IndexedDB），跨刷新可保留；非 pygbag 环境回退到仓库目录 `savegame.json`；
  写入失败已被 `main._handle_key` 的 try/except 兜住，不会崩（存档是 opt-in，按 S 才触发）。
- **零改核心**：`Game` / `game.render()` / `main._handle_key` 一字未动；新增的 `web.py` 与 `async_run`
  只调用既有公开 API，不引入随机 ⇒ #1/#2/#8 不破（不变量 #28）。

## 不变量增量
- **#28 网页化不变式**：Pygbag 把 M22 起的 Pygame 窗口（`PygameRenderer`）原样打包成 wasm 在浏览器运行，
  只换主循环的调度方式（异步 `async_run` 每帧 `await asyncio.sleep(0)` 让出浏览器事件循环），
  不改任何游戏核心（`Game`/`render()`/`_handle_key` 一字未动）⇒ #1/#2/#8 不破；
  `run`（桌面同步）与 `async_run`（浏览器异步）共用 `_pump_events` / `step` / `draw` / `_check_ending`
  ⇒ 同 seed + 同按键序列 ⇒ 同结果（#2 精神）；网页入口 `web.py` 复用 `main._handle_key` 与 `Game.procedural`、
  零新增随机；浏览器只读文件系统下存档落到 pygbag 持久化目录 `/data` 并已被 `_handle_key` 的 try/except 兜住、不崩。
