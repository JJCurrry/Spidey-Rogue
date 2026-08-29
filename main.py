"""终端 Roguelike 演示入口（M1：渲染 + 示例移动）。

运行：python main.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from rogue import Game
from rogue.rng import RandomSource


def main() -> None:
    game = Game(rng=RandomSource(seed=42))
    print("=== 初始地图 ===")
    print(game.render())
    print("\n=== 尝试 右 / 下 / 下(撞墙) ===")
    for label, (dx, dy) in [("右", (1, 0)), ("下", (0, 1)), ("下", (0, 1))]:
        ok = game.move(dx, dy)
        print(f"{label}: {'成功' if ok else '被挡'}")
    print("\n=== 移动后 ===")
    print(game.render())


if __name__ == "__main__":
    main()
