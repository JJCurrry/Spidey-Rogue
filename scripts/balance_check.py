"""临时平衡实测：重放演示 main._player_act 循环，统计 30 seed 通关率。
不进仓库门禁，仅用于 M15 配平验证（跑完即删或留作 dev 工具）。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from rogue import Game
from rogue.rng import RandomSource
import main as demo

MAX_DEPTH = 3
TURNS_PER_LEVEL = 80


def run(seed: int, stealth: bool) -> str:
    """返回 'win' / 'dead' / 'timeout'。"""
    rng = RandomSource(seed=seed)
    game = Game.procedural(rng, depth=1, fov=True, stealth=stealth,
                           noise=False, light=False, flashlight=False)
    for _ in range(1, TURNS_PER_LEVEL * MAX_DEPTH + 1):
        demo._player_act(game)
        game.monster_turn()
        alive = [m for m in game.monsters if m.alive]
        if game.player_dead:
            return "dead"
        if game.depth >= MAX_DEPTH and not alive:
            return "win"
    return "timeout"


def sweep(stealth: bool, n: int = 30) -> tuple[int, int, int]:
    wins = dead = timeout = 0
    for s in range(n):
        r = run(s, stealth)
        if r == "win":
            wins += 1
        elif r == "dead":
            dead += 1
        else:
            timeout += 1
    return wins, dead, timeout


if __name__ == "__main__":
    for name, stealth in (("默认（潜行关闭）", False), ("潜行", True)):
        w, d, t = sweep(stealth)
        print(f"{name}: 通关 {w}/30 | 被击倒 {d} | 回合用尽 {t}")
