"""M29 网页版存档后端（浏览器 localStorage 替代 /data 直写）。

在 M28 的基础上把「网页版的存档传输层」从 pygbag 的 `/data`（IndexedDB）切换到浏览器原生的
`platform.window.localStorage`——键空间独立、跨刷新更稳妥，且不依赖 pygbag 持久化目录。

设计原则（遵循不变量 #1/#2/#8 延伸与 M28 零改核心精神）：
- 本模块**只负责「dict ↔ 存储介质」的传输**，绝不引入随机、绝不改写 `Game` 状态；
- 序列化仍走 `Game.to_dict` / `apply_state`（M26 已证明确定性排序导出 ⇒ 同状态同字节，#26）；
- 两种后端共用同一套 dict 序列化，因此 localStorage 往返与文件往返在「dict 层面」逐字节等价；
- 桌面 / 无浏览器环境自动回退到文件后端（`FileSaveBackend`），与 M26 既有语义一致 ⇒ headless 测试零回归。

后端接口（鸭子类型，不依赖基类）：
    backend.save(game)       -> None   把 game 当前状态写入存储
    backend.load_into(game)  -> None   从存储读出并原地恢复到 game
        （无存档时抛 FileNotFoundError；存储不可用 / 损坏时抛 RuntimeError / 普通异常）
"""
from __future__ import annotations

import json
import os
import sys

# 固定键名：跨刷新用同一 key 读写，避免多存档键空间混乱。
SAVE_KEY = "spiderman_roguelike_save_v1"


def _local_storage():
    """返回浏览器 localStorage 对象；非浏览器/不可用返回 None。

    仅在 pygbag / wasm 环境，`platform` 模块才被注入 `window` 属性（即 JS 的 window 全局），
    其上的 `localStorage` 才是浏览器原生持久化。`import platform` 放在函数内，
    桌面环境导入的是标准库 `platform`（无 `window` 属性），安全回退 None。
    """
    try:
        import platform  # pygbag 注入 platform.window；桌面导入标准库 platform
    except Exception:
        return None
    win = getattr(platform, "window", None)
    if win is None:
        return None
    return getattr(win, "localStorage", None)


def local_storage_available() -> bool:
    """当前环境能否用 localStorage（浏览器 wasm 为 True，桌面为 False）。"""
    return _local_storage() is not None


class LocalStorageBackend:
    """pygbag / 浏览器：存档落到 `platform.window.localStorage[SAVE_KEY]`。

    纯传输层：序列化走 `game.to_dict`（确定性排序 JSON，#26），与桌面文件后端逐字节一致 ⇒ 确定性不破。
    """

    def __init__(self, key: str = SAVE_KEY):
        self.key = key

    def save(self, game) -> None:
        storage = _local_storage()
        if storage is None:
            raise RuntimeError("localStorage 不可用（非浏览器环境）")
        blob = json.dumps(game.to_dict(), ensure_ascii=False,
                          indent=2, sort_keys=True)
        storage.setItem(self.key, blob)

    def load_into(self, game) -> None:
        storage = _local_storage()
        if storage is None:
            raise RuntimeError("localStorage 不可用（非浏览器环境）")
        blob = storage.getItem(self.key)
        if blob is None or blob == "":
            raise FileNotFoundError("没有找到存档")
        game.apply_state(json.loads(blob))


class FileSaveBackend:
    """桌面 / 无浏览器回退：直接走 `Game` 的文件存读档（与 M26 既有语义一致）。"""

    def __init__(self, path: str):
        self.path = path

    def save(self, game) -> None:
        game.save(self.path)

    def load_into(self, game) -> None:
        game.load_into(self.path)


def get_default_backend(path: str):
    """按运行环境挑选后端：浏览器用 localStorage，否则回退文件。

    让 `main.py`（桌面终端 / GUI）与 `web.py`（浏览器 wasm）各自 import 时自动选对后端，
    调用方无需关心环境差异（#29）。
    """
    if local_storage_available():
        return LocalStorageBackend()
    return FileSaveBackend(path)


if __name__ == "__main__":
    # 冒烟：桌面环境下应回退到文件后端
    print("localStorage 可用:", local_storage_available())
    print("默认后端类型:", type(get_default_backend(
        os.path.join(os.path.dirname(__file__), "..", "..", "savegame.json"))).__name__)
