#!/usr/bin/env python3
"""M27 · 把程序化地形贴图烘焙成 tiles/*.png 序列帧 Sprite（确定性、零随机）。

与 render_pygame.py 共用同一套模块级绘制函数（_make_floor_surface 等），
保证产物与运行时「程序化回退」逐像素一致——素材不漂移、视觉零差异。

用法：
    python scripts/gen_tiles.py            # 烘焙到 <仓库根>/tiles/
    python scripts/gen_tiles.py --clean    # 先清空 tiles/ 再烘焙

不变量：本脚本只调用确定性绘图 API，绝不引入随机 ⇒ 不变量 #1/#2/#27。
"""
from __future__ import annotations
import argparse
import os
import shutil
import sys

# headless 烘焙：必须在 import pygame 之前设好 dummy driver
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from rogue.render_pygame import (  # noqa: E402
    TILES_DIR,
    _make_floor_surface,
    _make_wall_surface,
    _make_unseen_surface,
)

# 烘焙基准分辨率：高于默认 cell（26），运行时按 cell 缩放，保证任何分辨率都清晰。
BASE = 64
FRAMES = 4

# (文件名前缀, 绘制函数, visible 参数) —— 与 _load_tile_sprites 的命名约定严格对应。
SPECS = [
    ("floor_lit", _make_floor_surface, True),
    ("floor_dim", _make_floor_surface, False),
    ("wall_lit", _make_wall_surface, True),
    ("wall_dim", _make_wall_surface, False),
    ("unseen", _make_unseen_surface, True),  # 未探索无可见性维度；visible 形参被忽略
]


def bake(clean: bool = False) -> None:
    if clean and TILES_DIR.is_dir():
        shutil.rmtree(TILES_DIR)
    TILES_DIR.mkdir(parents=True, exist_ok=True)

    pygame.init()
    written = []
    for name, fn, visible in SPECS:
        for f in range(FRAMES):
            surf = fn(BASE, visible, f, True)
            path = TILES_DIR / f"{name}_{f}.png"
            pygame.image.save(surf, str(path))
            written.append(path.name)
    pygame.quit()
    print(f"已烘焙 {len(written)} 张序列帧 Sprite → {TILES_DIR}")
    for n in written:
        print("  -", n)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true", help="先清空 tiles/ 再烘焙")
    args = ap.parse_args()
    bake(clean=args.clean)
