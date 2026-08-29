"""终端 Roguelike 演示入口（M1 移动 + M2 战斗 + M3 怪物 AI + M4 道具背包 + M5 程序化关卡）。

主题：MCU 荷兰弟（Tom Holland）版蜘蛛侠。运行：python main.py

演示流程：按 seed 程序化生成楼层 → 蜘蛛侠逐层清怪 → 走楼梯下潜（共 MAX_DEPTH 层）。
随机只从 src/rogue/rng.py 流出（不变量 #1）；本文件不含任何随机调用。
"""
from __future__ import annotations
import os
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from rogue import Game
from rogue.rng import RandomSource

SEED = 19                # 演示种子（挑过：三层都有怪，且能在回合上限内清场）
MAX_DEPTH = 3            # 演示下潜到第几层收工
TURNS_PER_LEVEL = 80     # 单层回合上限（防死循环）
MAP_EVERY = 15           # 每几回合补印一次地图，避免刷屏
MOVE_LOG_EVERY = 4       # 纯走位每几步报一次，避免刷屏

DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def _bfs(game: Game, targets, avoid_monsters: bool = True):
    """对目标集合做一次 BFS，返回 (最短距离, 首步方向)；不可达返回 (None, None)。

    纯确定性（方向顺序固定），不引入任何随机。
    """
    targets = set(targets)
    start = (game.px, game.py)
    if not targets or start in targets:
        return (0 if targets else None), None
    prev = {start: None}
    queue = deque([start])
    found = None
    while queue and found is None:
        x, y = queue.popleft()
        for dx, dy in DIRS:
            nxt = (x + dx, y + dy)
            if nxt in prev or not game.in_bounds(*nxt) or game.is_wall(*nxt):
                continue
            if nxt in targets:
                prev[nxt] = (x, y)
                found = nxt
                break
            if avoid_monsters and game.monster_at(*nxt):
                continue
            prev[nxt] = (x, y)
            queue.append(nxt)
    if found is None:
        return None, None
    dist = 0
    node = found
    while prev[node] is not None:
        node = prev[node]
        dist += 1
    node = found
    while prev[node] != start:
        node = prev[node]
    return dist, (node[0] - start[0], node[1] - start[1])


def _move_towards(game: Game, targets) -> bool:
    """朝目标集合走一步；先绕开怪物，绕不开就允许贴着怪走（下一步会变成攻击）。"""
    _, step = _bfs(game, targets, avoid_monsters=True)
    if step is None:
        _, step = _bfs(game, targets, avoid_monsters=False)
    return bool(step) and game.move(*step)


def _approach_tiles(game: Game, m) -> list[tuple[int, int]]:
    """怪物四周可站的格子（走到这些格子下一步就能蛛网拳）。"""
    out = []
    for dx, dy in DIRS:
        x, y = m.x + dx, m.y + dy
        if game.in_bounds(x, y) and not game.is_wall(x, y) and not game.monster_at(x, y):
            out.append((x, y))
    return out


def _adjacent_monsters(game: Game) -> list:
    """与玩家相邻（切比雪夫距离 1）的存活怪物。"""
    return [m for m in game.monsters if m.alive and game.is_adjacent(m.x, m.y)]


def _threat_at(game: Game, x: int, y: int) -> int:
    """站在 (x,y) 会被几只怪相邻攻击到。"""
    return sum(1 for m in game.monsters
               if m.alive and max(abs(m.x - x), abs(m.y - y)) == 1)


def _retreat_step(game: Game) -> tuple[int, int] | None:
    """被围殴时后退一步：挑「相邻怪更少」的格子（方向顺序固定 ⇒ 确定性）。"""
    cur = _threat_at(game, game.px, game.py)
    best = None
    best_score = cur
    for dx, dy in DIRS:
        x, y = game.px + dx, game.py + dy
        if not game.in_bounds(x, y) or game.is_wall(x, y) or game.monster_at(x, y):
            continue
        score = _threat_at(game, x, y)
        if score < best_score:
            best_score = score
            best = (dx, dy)
    return best


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


WEB_SHOT_RANGE = 6       # 蛛网弹的有效射程（曼哈顿距离）
HEAL_THRESHOLD = 0.45    # HP 低于该比例就吃三明治
LOOT_RANGE = 6           # 清场后只「顺路」捡这个距离内的补给，太远的直接奔楼梯


def _player_act(game: Game) -> str:
    """蜘蛛侠一回合的决策：强化 → 补血 → 拾取 → 被围则后撤 → 蛛网拳 → 蛛网弹/逼近 → 搜刮 → 下楼。"""
    # 1) 纳米强化剂：永久提升蛛网拳伤害，越早用越值
    idx = _find_in_bag(game, "nano_boost")
    if idx >= 0 and game.use_item(idx):
        return "注入斯塔克纳米强化剂，蛛网拳威力提升！"

    # 2) 残血吃三明治（梅姨的手艺不能浪费在满血时）
    if game.player_hp <= game.player_max_hp * HEAL_THRESHOLD:
        idx = _find_in_bag(game, "sandwich")
        if idx >= 0 and game.use_item(idx):
            return "吃掉梅姨的三明治，补充体力！"

    # 3) 脚下有道具且背包没满 → 拾取（不变量 #5）
    if game.item_at(game.px, game.py) is not None and not game.inventory_full:
        it = game.pick_up()
        if it is not None:
            return f"拾取 {it.name}"

    target = _nearest_monster(game)

    # 4) 被多只怪相邻围住 → 先后撤（M2 规则是「攻击必吃反击」，硬拼会被围殴致死）
    if len(_adjacent_monsters(game)) >= 2:
        step = _retreat_step(game)
        if step and game.move(*step):
            return "被围住了，后撤拉开距离"

    # 5) 有敌人：相邻就打（M2）——优先补刀血量最低的那只，少挨一次反击；
    #    不相邻就远程消耗或逼近（M4）
    if target is not None:
        adj = _adjacent_monsters(game)
        if adj:
            victim = min(adj, key=lambda m: (m.hp, m.x, m.y))
            dmg, dead = game.player_attack(victim)
            return (f"蛛网拳命中 {victim.name}，造成 {dmg} 点伤害"
                    + ("（倒下！）" if dead else ""))
        dist = abs(target.x - game.px) + abs(target.y - game.py)
        if dist <= WEB_SHOT_RANGE:
            idx = _find_in_bag(game, "web_cartridge")
            if idx >= 0 and game.use_item(idx):
                return f"射出蛛网弹，缠住 {target.name}！"
        if _move_towards(game, _approach_tiles(game, target)):
            return f"逼近 {target.name}"

    # 6) 本层清场：补给比楼梯近就顺手捡（LOOT_RANGE 内），否则直接下潜（M5）
    #    判定用 BFS 距离、且「开始捡之后距离只会变近」，不会在补给与楼梯之间来回摇摆。
    if game.items and not game.inventory_full:
        spots = [(it.x, it.y) for it in game.items]
        d_item, _ = _bfs(game, spots)
        d_stairs, _ = _bfs(game, [game.stairs]) if game.stairs else (None, None)
        if d_item is not None and d_item <= LOOT_RANGE and (d_stairs is None
                                                            or d_item <= d_stairs):
            if _move_towards(game, spots):
                return "顺路捡起补给"

    if game.stairs is not None:
        if game.depth < MAX_DEPTH:
            if game.can_descend():
                game.descend()
                return f"走下楼梯 → 第 {game.depth} 层「{game.level_name}」"
            if _move_towards(game, [game.stairs]):
                return "沿走廊奔向下行楼梯"
        return "本层已清场，蜘蛛侠原地待命"

    return "被挡住了，原地调整姿态"


def _bag_str(game: Game) -> str:
    if not game.inventory:
        return "空"
    return "、".join(f"{i}:{it.name}" for i, it in enumerate(game.inventory))


def _is_move(action: str) -> bool:
    """是否只是走位（纯移动不逐回合刷屏，每 MOVE_LOG_EVERY 步才报一次）。"""
    return action.startswith(("逼近", "顺路捡起补给", "沿走廊奔向下行楼梯", "被围住了",
                              "被挡住了"))


def main() -> None:
    rng = RandomSource(seed=SEED)
    game = Game.procedural(rng, depth=1)
    print(f"=== 第 {game.depth} 层「{game.level_name}」（seed={SEED}）===")
    print(game.render())
    print(f"玩家 HP: {game.player_hp}/{game.player_max_hp} | 背包: {_bag_str(game)}")

    shown_depth = game.depth
    level_turn = 0
    move_streak = 0
    for turn in range(1, TURNS_PER_LEVEL * MAX_DEPTH + 1):
        level_turn += 1
        action = _player_act(game)
        game.monster_turn()
        alive = [m for m in game.monsters if m.alive]

        if _is_move(action):
            move_streak += 1
            if move_streak % MOVE_LOG_EVERY == 1:
                print(f"\n-- 第 {turn} 回合（第 {game.depth} 层）-- {action}"
                      f"（连续走位中……）")
        else:
            move_streak = 0
            print(f"\n-- 第 {turn} 回合（第 {game.depth} 层）-- {action}")
            print(f"   HP: {game.player_hp}/{game.player_max_hp}"
                  + (f" | 存活敌人: {len(alive)}" if alive else " | 本层已清场")
                  + f" | 背包: {_bag_str(game)}（{len(game.inventory)}/5）")

        if game.depth != shown_depth:
            shown_depth = game.depth
            level_turn = 0
            print(f"\n=== 下潜到第 {game.depth} 层「{game.level_name}」===")
            print(game.render())
        elif level_turn % MAP_EVERY == 0:
            print(game.render())

        if game.player_dead:
            print("\n蜘蛛侠被击倒了……（演示结束）")
            break
        if game.depth >= MAX_DEPTH and not alive:
            print(f"\n第 {game.depth} 层清场，蜘蛛侠摆荡着回家吃梅姨的三明治。（演示结束）")
            break
    else:
        print("\n回合用尽，演示到此为止。")


if __name__ == "__main__":
    main()
