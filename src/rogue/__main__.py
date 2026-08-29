"""终端入口：python -m rogue（需 PYTHONPATH=src）。"""
from __future__ import annotations
from .game import Game
from .rng import RandomSource


def main() -> None:
    game = Game(rng=RandomSource(seed=42))
    print(game.render())
    for dx, dy in [(1, 0), (0, 1), (0, 1)]:
        ok = game.move(dx, dy)
        print("move:", "ok" if ok else "blocked")
    print(game.render())


if __name__ == "__main__":
    main()
