# T-029 · 网页版存档接入浏览器 localStorage（M29）

## 一入一出（In/Out）
- **入**：HANDOFF-T001「下一步候选」明确——「网页版存档接入 `platform.window.localStorage`
  替代 `/data` 直写（更稳妥的跨刷新持久化）」。M28 把游戏核心原样打包成 wasm 在浏览器跑，
  但存档仍走 pygbag 的 `/data`（映射到 IndexedDB）；用户需要更稳妥、键空间独立的跨刷新持久化。
  同时需要一个「能直接启动网页游戏的入口」（类比 `play_gui.bat` 的 `play_web.bat` / `play_web.sh`）。
- **出**：
  1. 新增 `src/rogue/web_storage.py`：存档**传输层**后端。
     - `LocalStorageBackend`：浏览器/`platform.window.localStorage[SAVE_KEY]` 读写；
     - `FileSaveBackend`：桌面/无浏览器回退，走既有 `Game.save`/`load_into`；
     - `get_default_backend(path)`：按 `local_storage_available()` 自动选对后端；
     - `local_storage_available()` / `_local_storage()`：在**函数内** `import platform`
       （桌面导入标准库、无 `.window` ⇒ 安全回退 None），零随机、零状态。
  2. `main.py`：`SAVE_BACKEND = get_default_backend(SAVE_PATH)`；
     `_handle_key` 的 S/L 分支改走 `SAVE_BACKEND.save/load_into`（不再写死 `SAVE_PATH`）。
     桌面终端/GUI 行为与 M26 完全一致（回退文件），网页版自动切 localStorage。
  3. `web.py`：显式 `_main.SAVE_BACKEND = get_default_backend(_save_path())`
     （浏览器走 localStorage、桌面 `python web.py` 预览回退文件）；移除旧的 `/data` 写路径 hack；
     模块文档补 M29 存档说明。
  4. 新增启动入口 `play_web.bat`（Windows）/ `play_web.sh`（Linux·macOS）：双击即起
     `pygbag web.py` 本地预览服务器，浏览器打开提示地址即可玩网页版。
  5. `scripts/review_pipeline.py`：把 `web.py` / `build_wasm.*` / `play_gui.bat` /
     `play_web.*` 加入 `allowed_files`，消除范围审计误报（WARN 不影响退出码，但应当干净）。
  6. `tests/test_web_storage.py`：11 例——localStorage 往返等价文件 / 确定性 JSON /
     无存档抛 FileNotFoundError / 不可用抛 RuntimeError / 后端自动探测 / 文件回退 /
     `_handle_key` 经 `SAVE_BACKEND` 路由（S 写档、L 恢复、无档友好提示、不可用兜底）。

## 委托级别
- **S（自主完成）**：范围清晰（只换存档**传输层**，不碰 `Game` 核心与 `to_dict`/`apply_state` 序列化）、
  红线明确（#1 零随机 / #2 确定性 / #8 渲染纯净——本模块纯 I/O、不引入随机、不写 `Game`）、
  复用 M26 既有的确定性排序导出、是 HANDOFF 已登记的下一步候选，无歧义。

## 验收分级
- **A（必过，门禁）**：`tests/test_web_storage.py` 11 例全绿；`python scripts/gate.py`
  四道门 ALL GREEN，棘轮 580 → 591；`web.py` 在 headless 下可 import、可构造 Game、
  存档后端按环境自动选（桌面 FileSaveBackend / 浏览器 LocalStorageBackend，冒烟验证）。
- **B（建议）**：`pygbag web.py`（经 `play_web.bat`/`play_web.sh`）能起本地预览、`pygbag --build web.py`
  产出 `build/web/` 静态包（需联网下载 wasm 运行时；本环境若网络受限仅文档化，不影响核心验收 A）。

## 范围边界
- **只换传输层，不改序列化与核心**：`LocalStorageBackend` 仍是 `json.dumps(game.to_dict(),
  sort_keys=True, indent=2)` → 存储 → `json.loads` → `game.apply_state`，
  与 `Game.save`（文件）使用**同一套**确定性导出 ⇒ localStorage 往返与文件往返在 dict 层面逐字节等价（#26）。
- **零随机、零状态改写**：本模块仅在函数内 `import platform`、纯 JSON I/O，
  不调用 `RandomSource`、不碰 `Game` 玩法状态 ⇒ #1/#2/#8 延伸不破（不变量 #29）。
- **按环境自动选后端**：`local_storage_available()` 探测 `platform.window.localStorage`；
  桌面标准库 `platform` 无 `.window` ⇒ 回退文件；浏览器 pygbag 注入 `window` ⇒ 用 localStorage。
  调用方（`main._handle_key` / `web.py`）无需感知环境差异。
- **opt-in 默认零回归**：存档仍只在按 S 时触发；`SAVE_BACKEND` 在 `main` 模块加载即定，
  桌面路径与 M26 逐字节一致——`tests/test_save.py` 10 例全绿、未改动（文件语义原样保留）。
- **失败兜底**：`localStorage` 不可用 / 存档损坏时，异常被 `main._handle_key` 的 try/except 兜住，
  返回友好中文提示、不崩（与 M26 同源）。

## 不变量增量
- **#29 网页版 localStorage 存档不变式**：网页化存档的**传输层**从 pygbag `.data`（IndexedDB）
  切换到浏览器原生 `platform.window.localStorage`（固定键 `spiderman_roguelike_save_v1`），
  跨刷新更稳妥、键空间独立；后端按环境自动探测（浏览器 localStorage / 桌面回退文件），
  但序列化仍走 M26 已验证的 `Game.to_dict`/`apply_state`（确定性排序导出）⇒ 同状态同字节、
  localStorage 往返与文件往返逐字节等价（#26）；本模块纯 I/O、零随机、不写 `Game` 玩法状态
  （#1/#2/#8 延伸不破）；`_handle_key` 的 S/L 经由可插拔 `SAVE_BACKEND`，桌面与 M26 逐字节一致、
  网页版无缝切 localStorage；opt-in（按 S 才触发）、失败被 try/except 兜住不崩。
