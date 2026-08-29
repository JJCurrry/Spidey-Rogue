"""终端 Roguelike 演示入口（M1 移动 + M2 战斗 + M3 怪物 AI + M4 道具背包）。

主题：MCU 荷兰弟（Tom Holland）版蜘蛛侠。运行：python main.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from rogue import Game
from rogue.rng import RandomSource


def _step_toward(game: Game, tx: int, ty: int) -> bool:
    """朝目标格走一步（先横后纵）；移动经 Game.move 把关（不变量 #4）。"""
    dx = (tx > game.px) - (tx < game.px)
    dy = (ty > game.py) - (ty < game.py)
    if dx != 0 and game.move(dx, 0):
        return True
    if dy != 0 and game.move(0, dy):
        return True
    return False


def _nearest_monster(game: Game):
    alive = [m for m in game.monsters if m.alive]
    if not alive:
        return None
    return min(alive, key=lambda m: abs(m.x - game.px) + abs(m.y - game.py))


def _find_in_bag(game: Game, key: str) -> int:
    """返回背包中该道具的下标；没有则返回 -1。"""
    for i, it in enumerate(game.inventory):
        if it.key == key:
            return i
    return -1


def _player_act(game: Game) -> str:
    """蜘蛛侠一回合的决策：强化 → 补血 → 捡道具 → 蛛网拳 → 蛛网弹 → 移动。返回动作说明。"""
    # 1) 纳米强化剂：永久提升蛛网拳伤害，越早用越值
    idx = _find_in_bag(game, "nano_boost")
    if idx >= 0 and game.use_item(idx):
        return "注入斯塔克纳米强化剂，蛛网拳威力提升！"

    # 2) 残血吃三明治（梅姨的手艺不能浪费在满血时）
    if game.player_hp <= game.player_max_hp * 0.4:
        idx = _find_in_bag(game, "sandwich")
        if idx >= 0 and game.use_item(idx):
            return "吃掉梅姨的三明治，补充体力！"

    # 3) 脚下有道具且背包没满 → 拾取（不变量 #5）
    if game.item_at(game.px, game.py) is not None and not game.inventory_full:
        it = game.pick_up()
        if it is not None:
            return f"拾取 {it.name}"

    target = _nearest_monster(game)
    if target is None:
        return "纽约暂时平静，蜘蛛侠原地待命"

    # 4) 相邻 → 蛛网拳（M2）
    if game.is_adjacent(target.x, target.y):
        dmg, dead = game.player_attack(target)
        return f"蛛网拳命中 {target.name}，造成 {dmg} 点伤害" + ("（倒下！）" if dead else "")

    # 5) 有备用芯 → 远程蛛网弹先手消耗（M4：伤害 + 束缚）
    idx = _find_in_bag(game, "web_cartridge")
    if idx >= 0 and game.use_item(idx):
        return f"射出蛛网弹，缠住 {target.name}！"

    # 6) 半血以下优先去捡补给
    if game.player_hp <= game.player_max_hp * 0.7:
        food = [it for it in game.items
                if it.key in ("sandwich", "web_cartridge")] if not game.inventory_full else []
        if food:
            it = min(food, key=lambda i: abs(i.x - game.px) + abs(i.y - game.py))
            if _step_toward(game, it.x, it.y):
                return f"朝 {it.name} 移动"

    # 7) 否则朝最近的道具或怪物移动
    if game.items and not game.inventory_full:
        it = min(game.items, key=lambda i: abs(i.x - game.px) + abs(i.y - game.py))
        if _step_toward(game, it.x, it.y):
            return f"朝 {it.name} 移动"
    if _step_toward(game, target.x, target.y):
        return f"逼近 {target.name}"
    return "被挡住了，原地调整姿态"


def _bag_str(game: Game) -> str:
    if not game.inventory:
        return "空"
    return "、".join(f"{i}:{it.name}" for i, it in enumerate(game.inventory))


def main() -> None:
    game = Game(rng=RandomSource(seed=42))
    print("=== 初始地图（蜘蛛侠 MCU 荷兰弟版）===")
    print(game.render())
    print(f"玩家 HP: {game.player_hp}/{game.player_max_hp}")

    # M3：一只追击的街头小混混 + 一只随机游走的迷途无人机（Mysterio 风格）
    game.spawn_monster("街头小混混", 4, 3, hp=10, attack=2, behavior="chase")
    game.spawn_monster("迷途无人机", 1, 3, hp=6, attack=1, behavior="wander")
    # M4：地面散落的补给（掉落/布置均走 spawn_item）
    game.spawn_item("web_cartridge", 3, 1)
    game.spawn_item("nano_boost", 5, 1)
    game.spawn_item("sandwich", 5, 3)
    print("\n=== 敌人与补给出现（! = 地面道具）===")
    print(game.render())
    print(f"背包: {_bag_str(game)}")

    # 玩家与怪物 AI 交替推进（每回合：蜘蛛侠行动 → 怪物 AI 推进），最多 30 回合防死循环
    for turn in range(1, 31):
        action = _player_act(game)
        game.monster_turn()
        alive = [m for m in game.monsters if m.alive]
        print(f"\n-- 第{turn}回合 -- {action}")
        print(game.render())
        print(f"玩家 HP: {game.player_hp}/{game.player_max_hp}"
              + (f" | 存活敌人: {len(alive)}" if alive else " | 敌人全清！"))
        print(f"背包: {_bag_str(game)}（{len(game.inventory)}/5）")
        if game.player_dead:
            print("蜘蛛侠被击倒了……（演示结束）")
            break
        if not alive:
            print("纽约街头恢复平静，蜘蛛侠获胜！")
            break


if __name__ == "__main__":
    main()
