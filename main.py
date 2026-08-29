"""终端 Roguelike 演示入口（M1 移动 + M2 战斗）。

主题：MCU 荷兰弟（Tom Holland）版蜘蛛侠。运行：python main.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from rogue import Game
from rogue.rng import RandomSource


def _player_act(game: Game) -> None:
    """蜘蛛侠向最近怪物逼近（相邻则蛛网拳）；移动经 Game.move 把关（不变量 #4）。"""
    targets = [m for m in game.monsters if m.alive]
    if not targets:
        return
    target = min(targets, key=lambda m: abs(m.x - game.px) + abs(m.y - game.py))
    if game.is_adjacent(target.x, target.y):
        game.player_attack(target)
        return
    dx = (target.x > game.px) - (target.x < game.px)
    dy = (target.y > game.py) - (target.y < game.py)
    if dx != 0 and game.move(dx, 0):
        return
    if dy != 0 and game.move(0, dy):
        return


def main() -> None:
    game = Game(rng=RandomSource(seed=42))
    print("=== 初始地图（蜘蛛侠 MCU 荷兰弟版）===")
    print(game.render())
    print(f"玩家 HP: {game.player_hp}/{game.player_max_hp}")

    # M3：一只追击的街头小混混 + 一只随机游走的迷途无人机（Mysterio 风格）
    game.spawn_monster("街头小混混", 4, 3, hp=12, attack=3, behavior="chase")
    game.spawn_monster("迷途无人机", 1, 3, hp=8, attack=2, behavior="wander")
    print("\n=== 怪物出现，蜘蛛侠进入战斗 ===")
    print(game.render())

    # 玩家与怪物 AI 交替推进（每回合：蜘蛛侠行动 → 怪物 AI 推进），最多 30 回合防死循环
    for turn in range(1, 31):
        _player_act(game)
        game.monster_turn()
        alive = [m for m in game.monsters if m.alive]
        print(f"\n-- 第{turn}回合 --")
        print(game.render())
        print(f"玩家 HP: {game.player_hp}/{game.player_max_hp}"
              + (f" | 存活怪物: {len(alive)}" if alive else " | 怪物全清！"))
        if game.player_dead:
            print("蜘蛛侠被击倒了……（演示结束）")
            break
        if not alive:
            print("纽约街头恢复平静，蜘蛛侠获胜！")
            break


if __name__ == "__main__":
    main()
