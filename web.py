"""网页化入口（M28 · Pygbag 把 Pygame 窗口打包成 wasm；M29 · localStorage 存档）。

零改游戏核心（#1/#2/#8 不变）：直接复用 M22 起的 PygameRenderer，
只把主循环换成浏览器友好的异步循环（render_pygame.PygameRenderer.async_run）。

本地预览（开发用，需要安装 pygbag）：
    pygbag web.py
构建静态包（产物在 build/web/，可托管到任意静态服务器）：
    pygbag --build web.py
等价地用仓库提供的脚本：build_wasm.bat（Windows）/ build_wasm.sh（Linux·macOS）；
双击启动入口：play_web.bat（Windows）/ play_web.sh（Linux·macOS）。

控制：WASD/方向键 移动（撞怪=攻击）· G 拾取 · 1-5 用道具 · E 蛛网摆荡突袭
      · F 手电 · > 下潜 · 空格/回车 等待 · ? 帮助 · Q 退出 · S 存档 · L 读档

存档（M29）：浏览器环境下按 S 把进度写入 `platform.window.localStorage`
（键固定为 spiderman_roguelike_save_v1），跨刷新稳健保留、键空间独立于 pygbag 的 /data；
非 pygbag 环境（普通桌面 / python web.py 本地预览）回退到仓库目录 savegame.json。
写入失败被 main._handle_key 的 try/except 兜住，不会崩（存档是 opt-in，按 S 才触发）。
"""
from __future__ import annotations
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from rogue import Game
from rogue.rng import RandomSource
from rogue.render_pygame import PygameRenderer
from rogue.web_storage import get_default_backend
import main as _main
from main import _handle_key, CONTROLS_HELP

SEED = 19
MAX_DEPTH = 3


def _save_path() -> str:
    """非 pygbag 环境（普通桌面 / python web.py 本地预览）的存档回退路径。

    浏览器 wasm 下 get_default_backend 会直接选 LocalStorageBackend，
    本回退路径只在桌面预览时生效。
    """
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "savegame.json")


def _parse_flags(argv: list[str]) -> dict:
    """复用 main.py 同款语义；未显式给旗标时给一个「全开」的展示默认。"""
    flags = dict(fov=True, stealth=True, noise=True, light=True,
                 flashlight=True, switches=True, boss=True)
    simple = {
        "--no-fog": ("fov", False), "--stealth": ("stealth", True),
        "--no-stealth": ("stealth", False), "--noise": ("noise", True),
        "--no-noise": ("noise", False), "--light": ("light", True),
        "--no-light": ("light", False), "--flashlight": ("flashlight", True),
        "--no-flashlight": ("flashlight", False), "--boss": ("boss", True),
        "--no-boss": ("boss", False),
    }
    for a in argv:
        if a in simple:
            key, val = simple[a]
            flags[key] = val
    return flags


async def main() -> None:
    flags = _parse_flags(sys.argv[1:])
    rng = RandomSource(seed=SEED)
    game = Game.procedural(rng, depth=1, fov=flags["fov"], stealth=flags["stealth"],
                           noise=flags["noise"], light=flags["light"],
                           flashlight=flags["flashlight"], switches=flags["light"],
                           boss=flags["boss"], boss_depth=MAX_DEPTH)
    # 让 --play 路径的 S/L 存档走 M29 后端：浏览器用 localStorage、桌面回退文件
    _main.SAVE_BACKEND = get_default_backend(_save_path())
    renderer = PygameRenderer(game, cell_size=26, max_depth=MAX_DEPTH,
                              help_text=CONTROLS_HELP)
    ending = await renderer.async_run(_handle_key)
    print("游戏结束：", ending)


if __name__ == "__main__":
    asyncio.run(main())
