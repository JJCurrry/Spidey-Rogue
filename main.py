"""终端 Roguelike 演示入口（M1 移动 + M2 战斗）。

主题：MCU 荷兰弟（Tom Holland）版蜘蛛侠。运行：python main.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from rogue import Game
from rogue.rng import RandomSource


def main() -> None:
    game = Game(rng=RandomSource(seed=42))
    print("=== 初始地图（蜘蛛侠 MCU 荷兰弟版）===")
    print(game.render())
    print(f"玩家 HP: {game.player_hp}/{game.player_max_hp}")

    # M2：在玩家右侧生成一只街头恶徒，演示「蛛网拳」战斗
    game.spawn_monster("街头暴徒", 2, 1, hp=12, attack=3)
    print("\n=== 出现怪物，演示蛛网拳战斗 ===")
    print(game.render())
    target = game.monsters[0]
    round_n = 1
    while target.alive and not game.player_dead:
        dmg, dead = game.player_attack(target)
        tail = "（已击倒！）" if dead else f"，被反击 玩家 HP={game.player_hp}"
        print(f"第{round_n}回合: 蛛网拳造成 {dmg} 伤害，怪物 HP={target.hp}{tail}")
        round_n += 1

    print("\n=== 战后地图 ===")
    print(game.render())
    print(f"玩家 HP: {game.player_hp}/{game.player_max_hp}")


if __name__ == "__main__":
    main()
