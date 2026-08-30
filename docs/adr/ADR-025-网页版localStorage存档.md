# ADR-025 · 网页版存档接入浏览器 localStorage（M29）

## 状态
已采纳（M29）

## 背景
M28 把 M22 起的 Pygame 窗口（`PygameRenderer`）原样打包成 wasm 在浏览器跑，游戏核心一字未改
（不变量 #28）。但当时存档仍落 pygbag 的 `/data`（映射到 IndexedDB）——这是 pygbag 提供的
虚拟持久化目录。HANDOFF-T001 把「网页版存档接入 `platform.window.localStorage` 替代 `/data` 直写
（更稳妥的跨刷新持久化）」列为 M28 之后的下一步候选，并同时需要一个「能直接启动网页游戏的入口」。

约束与 M1~M28 同款：
- 熔断②禁止改/删测试凑绿 ⇒ 既有 580 例不能破（尤其 `tests/test_save.py` 的 10 例文件存读档）；
- 不变量 #1/#2 ⇒ 任何新增随机都会让同 seed 的既有回放全部作废；
- 不变量 #8 渲染纯净性 ⇒ 本模块纯传输层、绝不写 `Game` 状态；
- 序列化必须保持 M26 已验证的「确定性排序导出」（同状态同字节，#26）。

候选：
- **可插拔存档后端：浏览器用 `platform.window.localStorage`、桌面回退文件（采纳）**：
  新增 `src/rogue/web_storage.py` 定义 `LocalStorageBackend` / `FileSaveBackend` 两个传输层，
  共用 M26 的 `Game.to_dict`/`apply_state` 序列化；`main._handle_key` 的 S/L 改走
  模块级 `SAVE_BACKEND`，由 `get_default_backend()` 按环境自动挑选；
  新增 `play_web.bat` / `play_web.sh` 作为双击启动入口。零改 `Game` 核心、确定性满分、
  与桌面/终端同构；文件语义完整保留 ⇒ headless 零回归。
- 继续沿用 pygbag `/data`（IndexedDB）直写：能工作，但键空间与 pygbag 持久化目录绑定，
  不是用户要的「更稳妥的跨刷新持久化、键空间独立」——否决。
- 在 `Game` 核心里加 `save_to_local_storage()` 方法：把传输层塞进玩法核心，违背
  「视图/IO 与核心分离」与 `tests/test_save.py` 既有的文件接口约定——否决。
- 用 JS 侧 fetch 把存档同步到服务器：超出本次范围（纯前端单机存档足矣），且引入网络依赖
  会破坏离线可玩性——否决。

## 决策
- **传输层与序列化分离**：`LocalStorageBackend` / `FileSaveBackend` 只做「dict ↔ 存储介质」，
  序列化完全复用 `Game.to_dict`（确定性 `sort_keys=True, indent=2`）与 `apply_state`；
  因此 localStorage 与文件两条路径在 dict 层面**逐字节等价**（#26），不新增任何序列化分支。
- **后端按环境自动探测**：`local_storage_available()` 在**函数内** `import platform`——
  桌面导入标准库 `platform`（无 `.window` 属性 ⇒ `getattr` 安全回退 None），浏览器 pygbag
  注入的 `platform.window` 带 `.localStorage` ⇒ 自动选对后端；调用方（`main._handle_key` /
  `web.py`）无需感知差异，保证桌面与 M26 逐字节一致、网页版无缝切 localStorage。
- **`_handle_key` 走可插拔 `SAVE_BACKEND`**：移除原本写死的 `game.save(SAVE_PATH)` /
  `game.load_into(SAVE_PATH)`，改走 `SAVE_BACKEND.save/load_into`；桌面模块加载时
  `SAVE_BACKEND = get_default_backend(SAVE_PATH)` 默认仍是文件 ⇒ M26 行为零改变；
  `render_pygame.py` 调用 `handle_key(self.game, token)` 的签名不变 ⇒ 同步/异步主循环无需改动。
- **启动入口 `play_web.bat` / `play_web.sh`**：与 `play_gui.bat` 同构，双击即起
  `pygbag web.py` 本地预览服务器（浏览器开提示地址即玩）；`python web.py` 也可作为桌面
  Pygame 本地预览（localStorage 不可用 ⇒ 回退文件存档）。构建静态包仍用 `build_wasm.*`。
- **不变式**：本模块纯 I/O、零随机、不写 `Game` 玩法状态 ⇒ #1/#2/#8 延伸不破；
  序列化复用 M26 ⇒ 同状态同字节、localStorage 往返等价文件（#26 / #29）。

## 后果
- 优点：网页版存档现在落浏览器原生 `localStorage`（固定键、键空间独立、跨刷新稳健），
  不再依赖 pygbag 的 `/data`；桌面终端/GUI 与既有 M26 文件存档逐字节一致、零回归；
  新增一个双击即玩的网页启动入口（`play_web.bat` / `play_web.sh`）；11 例新测试全绿、
  gate 四道门 ALL GREEN（580 → 591）。
- 取舍：
  - 仅新增一个传输层模块 + 一个可插拔后端接线 + 两个启动脚本，核心代码零改动；
  - localStorage 仅在浏览器 wasm 环境生效，桌面预览自动回退文件（行为明确、不静默丢失）；
  - 存档仍是 opt-in（按 S 才触发），失败被 `main._handle_key` 的 try/except 兜住、不崩；
  - 固定键 `spiderman_roguelike_save_v1`：单存档槽，换 seed/楼层覆盖同一份（与 M26 单文件语义一致）。
