# T-027 · tiles/*.png 序列帧 Sprite（M27）

## 一入一出（In/Out）
- **入**：HANDOFF-T001「下一步候选」最后一条明确——「主题美术换 tiles/*.png 序列帧 Sprite
  （M24 续，可选）：M24 预渲染已按帧组织，若要更精致可把程序化贴图换成 tiles/*.png 序列帧
  （接口已留好），仍须保持『只读 Game、零随机、确定性不变』」。M24 的 `floor_frames`/`wall_frames`/
  `unseen_frames` 已按 N=4 相位帧组织，本里程碑把这层地形贴图从「每帧程序化重绘」换成
  「磁盘 PNG 序列帧 + 运行时 blit」，接口/视觉/契约与 M24 一致。
- **出**：地形贴图来源变为 `tiles/*.png`（确定性烘焙、零随机），运行时优先加载、缺文件回退程序化：
  1. `render_pygame.py`：地形绘制函数抽成模块级 `_make_floor_surface`/`_make_wall_surface`/
     `_make_unseen_surface(cell, visible, phase, detail)`，`_make_floor/_make_wall/_make_unseen`
     方法退化为回退委托；新增 `_load_tile_sprites(cell, n)` 从 `tiles/*.png` 加载并按 cell 缩放、
     `_build_tiles` 优先用 PNG、缺文件回退同款程序化（视觉零差异）。
  2. 新增 `scripts/gen_tiles.py`：离线确定性烘焙 20 张 PNG（floor/wall 各 lit/dim ×4 帧 +
     unseen ×4 帧，BASE=64 基准分辨率、零随机）到 `tiles/`。
  3. `tests/test_gui.py` 增 M27 用例：PNG 加载成功 / PNG 与程序化在 `cell==BASE` 逐像素一致
     （防素材漂移）/ 资产存在性。

## 委托级别
- **S（自主完成）**：范围清晰（只换地形贴图的来源，不动 `Game`/`render()` 字形/优先级/玩法）、
  红线明确（#1 零随机 / #2 确定性 / #8 渲染纯净）、复用 M24 既有的「按帧组织」接口、
  是 HANDOFF 已登记的下一步候选，无歧义。

## 验收分级
- **A（必过，门禁）**：`tests/test_gui.py` M27 新增用例全绿——
  - **只读不写**：renderer 仍只读 `Game`、只调既有方法、不引入随机（#1/#2/#8 延伸）；
  - **PNG 与程序化同像**：`cell==BASE` 时加载的序列帧与 `_make_*_surface` 逐像素一致
    （素材不漂移，视觉与 M24 零差异）；
  - **回退健全**：`tiles/` 缺失时 `_build_tiles` 回退程序化、属性齐全、`draw()` 不报错；
  - `python scripts/gate.py` 四道门 ALL GREEN，棘轮 574 → +N；评审流水线范围审计加 `tiles` 白名单、无 HIGH。
- **B（建议）**：`python main.py --gui` 窗口中地形由 PNG 序列帧绘制、动画（蛛网轻闪/砖缝呼吸）正常；
  `python main.py`（无 `--gui`）演示与 M26 逐字节一致（零回归，渲染层改动不影响玩法日志）。

## 范围边界
- **只换地形贴图来源，不动玩法/字形/优先级**：`tiles/*.png` 与「程序化回退」是同一套绘制函数的两种产物；
  只影响「怎么画地板/墙/未探索格」，不改 `game.render()` 字形、渲染优先级 `?<><!>M<@`、任何玩法判定。
- **确定性烘焙 + 确定性加载**：`gen_tiles.py` 只调确定性绘图 API、零随机；运行时 `blit` 已加载 PNG，
  不重绘也不掷骰 ⇒ 不变量 #2 精神不变。
- **BASE 基准分辨率 + 按 cell 缩放**：PNG 以 BASE=64 烘焙，运行时 `pygame.transform.scale` 到 `self.cell`
  对齐网格；任意 cell 分辨率都清晰，且 `cell==BASE` 时为原图（逐像素一致测试据此成立）。
- **缺文件回退**：`tiles/` 不存在或任一 PNG 缺失 ⇒ `_load_tile_sprites` 返回 None，走与 M24 完全一致的程序化
  路径 ⇒ headless/资产缺失环境下行为与 M24 零差异（零回归保险）。
- **opt-in 无关**：本里程碑不新增开关；PNG 是默认渲染源（存在即用），与 `--gui` 是否开启无关。

## 不变量增量
- **#27 序列帧 Sprite 确定性**：地形贴图可由 `tiles/*.png` 序列帧提供，加载为确定性文件读取、零随机，
  与「程序化回退」共用同一套绘制函数 ⇒ 视觉与 M24 逐像素一致、素材不漂移；贴图来源（PNG 或程序化）
  只影响「怎么画」、不改写 `Game` 状态、不扰动随机序列、不改变 `render()` 字形与渲染优先级
  ⇒ #1/#2/#8 延伸不破；`tiles/` 缺失时自动回退程序化、行为零差异。
