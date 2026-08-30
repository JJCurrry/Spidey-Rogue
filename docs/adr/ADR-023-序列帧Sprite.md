# ADR-023 · tiles/*.png 序列帧 Sprite（M27）

## 状态
已采纳（M27）

## 背景
M1~M26 把游戏做成「终端 ASCII + Pygame 窗口」双层视图：M22 用纯色块、M23 升级为程序化蜘蛛侠主题、
M24 在程序化美术上加帧动画（蛛网轻闪/砖缝呼吸，N=4 相位帧）。M24 的 `floor_frames`/`wall_frames`/
`unseen_frames` 已「按帧组织」，HANDOFF-T001 把「把程序化贴图换成 tiles/*.png 序列帧」列为 M24 续作候选，
并强调「接口已留好、仍须保持只读 Game、零随机、确定性不变」。

约束与 M1~M26 同款：
- 熔断②禁止改/删测试凑绿 ⇒ 既有 574 例不能破；
- 不变量 #1/#2 ⇒ 任何新增随机都会让同 seed 的既有回放全部作废；
- 不变量 #8 渲染纯净性 ⇒ 视图层不改写游戏状态。

候选：
- **离线烘焙 PNG + 运行时 blit（采纳）**：`gen_tiles.py` 用与运行时回退同一套绘制函数确定性烘焙 20 张 PNG，
  `_build_tiles` 优先加载、缺文件回退程序化。零素材依赖（自包含）、确定性满分、视觉与 M24 零差异、
  assets 可日后替换为手绘/真素材而不动代码。
- 运行时每帧程序化重绘（维持 M24 现状）：自包含但每帧重算、且美术上限受图元绘制约束。
- 引入外部美术管线（手绘 PNG/精灵图）：美术更精致，但本环境无素材、且需改命名约定与加载逻辑，
  与「自包含/确定性」基调冲突——留作未来（替换 `tiles/` 即可，接口不变）。

## 决策
- **PNG 与程序化回退共用同一套绘制函数**：`_make_floor_surface`/`_make_wall_surface`/
  `_make_unseen_surface(cell, visible, phase, detail)` 既是 `gen_tiles.py` 的烘焙源，也是
  `_make_floor/_make_wall/_make_unseen` 回退委托的实现 ⇒ 资产与回退逐像素一致，素材永不漂移。
- **`tiles/` 为默认渲染源、缺失即回退**：`_build_tiles` 先 `_load_tile_sprites`，成功则 `blit` 已加载 PNG，
  失败（目录/文件缺失）则走与 M24 完全一致的程序化路径。`tiles/` 不存在的环境（如未跑生成脚本）
  行为与 M24 零差异——这是零回归的双保险。
- **BASE 基准分辨率 + 按 cell 缩放**：PNG 以 BASE=64 烘焙（高于默认 cell=26），运行时
  `pygame.transform.scale(surf, (cell, cell))` 对齐网格；任意 cell 分辨率都清晰，且 `cell==BASE`
  时加载即原图（逐像素一致测试据此成立，钳制素材漂移）。
- **评审流水线加 `tiles` 白名单**：`scripts/review_pipeline.py::role_scope` 的 `allowed_dirs`
  增加 `tiles`，避免顶层目录触发范围告警（WARN 不影响退出码，但保持审计干净）。
- **不变式**：只读 `Game`、只调既有方法、不引入随机 ⇒ #1/#2/#8 延伸不破；
  地形源（PNG 或程序化）只影响「怎么画」、不改变 `render()` 字形/优先级/玩法 ⇒ 与 M24 同构。

## 后果
- 优点：地形贴图从「每帧程序化重绘」变成「确定性 PNG 序列帧 blit」，运行时更轻、且美术可后续替换
  （仅换 `tiles/*.png`，不改 `render_pygame.py`）；与 M24 视觉逐像素一致、零回归；
  自包含、确定性满分（不变量 #27）。
- 取舍：
  - 仅地形贴图（floor/wall/unseen）走 PNG 序列帧；玩家面具/怪物/Boss/道具/特效/HUD 仍为程序化实时绘制
    （带位置相位动画，不适合静态序列帧），架构已为后续「把角色也烘焙成序列帧」留好 `_load_tile_sprites` 范式；
  - 新增 20 个二进制 PNG 资产（已写 `.gitignore` 之外、纳入版本库），`gen_tiles.py` 可随时 `--clean` 重烘焙；
  - 渲染层改动完全不影响玩法日志，`python main.py` 与 M26 逐字节一致。
