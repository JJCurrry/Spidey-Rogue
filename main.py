"""终端 Roguelike 演示入口（M1 移动 + M2 战斗 + M3 怪物 AI + M4 道具背包 + M5 程序化关卡
+ M6 视野 + M7 怪物感知与潜行 + M8 噪音与听觉 + M9 主动制造响动 + M10 ANSI 颜色高亮）。

主题：MCU 荷兰弟（Tom Holland）版蜘蛛侠。
运行：python main.py（--no-fog 切回全图；--stealth 开启怪物视野与潜行；--noise 再开启听觉，
      --noise 隐含 --stealth——听觉只在「怪物需要被发现才追你」时才有意义；
      --color / --no-color 控制终端上色，默认在终端（TTY）自动上色、管道/重定向下自动降级为纯文本）

演示流程：按 seed 程序化生成楼层 → 蜘蛛侠逐层清怪 → 走楼梯下潜（共 MAX_DEPTH 层）。
随机只从 src/rogue/rng.py 流出（不变量 #1）；本文件不含任何随机调用。

M6：默认开启视野/迷雾——蜘蛛侠只看得见视线内的区域，走进房间点亮整间，
走过的地方留下记忆，墙后的近处威胁靠「蜘蛛感应」以 `?` 提示。
注意：演示用的寻路 AI 仍然知道全图（它是演示脚本不是玩家），
视野只影响**渲染**，不影响任何游戏状态（不变量 #8）。

M7：`--stealth` 开启怪物感知与潜行——敌人只在看得见你时才会被惊动，
还没发现你的敌人画成小写 `m`；从它看不见的地方荡过去即可**倒挂突袭**
（伤害翻倍、敌人来不及反击）。默认关闭 ⇒ 不加参数时演示与 M6 完全一致。

M8：`--noise` 开启噪音与听觉——动静沿走廊传播、穿墙会闷掉一大截，
听得见的敌人会扑向**声源**（不是你的实时位置）。走路无声，只有动作会响：
蛛网拳（响 6）、倒挂突袭（响 2，几乎无声）、被蛛网弹缠住的怪挣扎（响 7，声源在它自己那儿
⇒ 同伴被引向它）、下潜落地（响 8）。听见动静但还没看见你的敌人画成 `~`。
默认关闭 ⇒ 不加参数时演示与 M7 完全一致。

M9：`--noise` 下蜘蛛侠脚边会多一个**皇后区垃圾桶盖**——抄起来甩到远处，落地「哐」的一声
（响 9，全场最响），把听得见的敌人全引到**落点**去。这是 M8「调虎离山」的主动版：
被动版只能靠「蛛网弹缠住一只怪、它挣扎着把同伴引过去」，而那已经先动手了。
默认（不加 --noise）既不会刷出垃圾盖、也甩不响 ⇒ 与 M8 逐字节一致。
"""
from __future__ import annotations
import os
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from rogue import Game
from rogue.game import DECOY_KEY, NOISE_DECOY
from rogue.rng import RandomSource
from rogue.color import colorize, should_color  # M10：纯展示层上色

SEED = 19                # 演示种子（挑过：三层都有怪，且能在回合上限内清场）
MAX_DEPTH = 3            # 演示下潜到第几层收工
TURNS_PER_LEVEL = 80     # 单层回合上限（防死循环）
MAP_EVERY = 15           # 每几回合补印一次地图，避免刷屏
MOVE_LOG_EVERY = 4       # 纯走位每几步报一次，避免刷屏

LEGEND = ("图例：@ 蜘蛛侠 | M 已察觉你的敌人 | m 未察觉的敌人（可倒挂突袭） | "
          "~ 听见动静、还没看见你的敌人 | "
          "? 蜘蛛感应（看不见的威胁） | ! 补给 | > 下行楼梯 | # 墙 | . 地板 | 空白 未探索")

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


def _target_monster(game: Game):
    """本回合要招呼谁：潜行开启时优先「还没发现你」的那只（摸哨优先于硬拼）。"""
    target = _nearest_monster(game)
    if not game.stealth_enabled or target is None:
        return target
    unaware = game.unaware_monsters()
    if not unaware:
        return target
    return min(unaware, key=lambda m: (abs(m.x - game.px) + abs(m.y - game.py),
                                       m.x, m.y))


def _stealth_str(game: Game) -> str:
    """状态栏的潜行提示（潜行关闭时不显示）。"""
    if not game.stealth_enabled:
        return ""
    unaware = len(game.unaware_monsters())
    if game.hidden:
        return " | 潜行中：还没有人发现你"
    return f" | 已被 {len(game.alerted_monsters())} 只敌人发现（{unaware} 只尚未察觉）"


def _noise_str(game: Game) -> str:
    """状态栏的听觉提示（听觉关闭时不显示；没发出过动静也不显示）。"""
    if not game.noise_enabled or game.last_noise_loudness <= 0:
        return ""
    heard = game.last_noise_heard
    tail = "（没人听见）" if heard == 0 else f"（{heard} 只敌人正朝声源摸过来）"
    return f" | 动静：响度 {game.last_noise_loudness}{tail}"


def _find_in_bag(game: Game, key: str) -> int:
    """返回背包中该道具的下标；没有则返回 -1。"""
    for i, it in enumerate(game.inventory):
        if it.key == key:
            return i
    return -1


WEB_SHOT_RANGE = 6       # 蛛网弹的有效射程（曼哈顿距离）
HEAL_THRESHOLD = 0.45    # HP 低于该比例就吃三明治
LOOT_RANGE = 6           # 清场后只「顺路」捡这个距离内的补给，太远的直接奔楼梯
DECOY_MIN_THREAT = 2     # 至少被几只敌人盯上，才值得花一回合甩垃圾桶盖（换取各个击破）


def _decoy_spot(game: Game):
    """挑一个甩垃圾桶盖的落点：**听得见的人最多**、其次**离你最远**。

    前者保证这一盖不白甩，后者保证敌人是朝「离开你」的方向走——调虎离山要的是
    把它们从你身边支开，而不是换个地方团团围住你。
    遍历顺序固定、用严格大于取最优 ⇒ 确定性（不引入任何随机）。
    没有人听得见时返回 None（甩了也是白甩）。
    """
    best = None
    best_score = (0, -1)      # (听得见的敌人数, 与玩家的切比雪夫距离)
    for y in range(game.height):
        for x in range(game.width):
            if not game.can_throw(x, y):
                continue
            heard = len(game.monsters_hearing(x, y, NOISE_DECOY))
            score = (heard, max(abs(x - game.px), abs(y - game.py)))
            if score > best_score:
                best_score = score
                best = (x, y)
    return best if best_score[0] >= 1 else None


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

    target = _target_monster(game)

    # 4) 被多只怪相邻围住 → 先后撤（M2 规则是「攻击必吃反击」，硬拼会被围殴致死）
    if len(_adjacent_monsters(game)) >= 2:
        step = _retreat_step(game)
        if step and game.move(*step):
            return "被围住了，后撤拉开距离"

    # 5) 被多只敌人盯上、且还没人贴脸 ⇒ 甩出垃圾桶盖（M9：主动制造响动）。
    #    把动静甩到「听得见的人最多、离你最远」的地方，换来各个击破的机会。
    #    （有人贴脸就该打而不是甩——那一回合更值钱。）
    if game.noise_enabled and not _adjacent_monsters(game):
        if len(game.alerted_monsters()) >= DECOY_MIN_THREAT:
            idx = _find_in_bag(game, DECOY_KEY)
            if idx >= 0:
                spot = _decoy_spot(game)
                if spot is not None and game.use_item(idx, target=spot):
                    return f"抄起垃圾桶盖甩向 ({spot[0]},{spot[1]})，把动静引开！"

    # 6) 有敌人：相邻就打（M2）——优先补刀血量最低的那只，少挨一次反击；
    #    不相邻就远程消耗或逼近（M4）；潜行开启时还能直接荡过去倒挂突袭（M7）
    if target is not None:
        adj = _adjacent_monsters(game)
        if adj:
            victim = min(adj, key=lambda m: (m.hp, m.x, m.y))
            dmg, dead = game.player_attack(victim)
            verb = "倒挂突袭" if game.last_attack_sneak else "蛛网拳命中"
            return (f"{verb} {victim.name}，造成 {dmg} 点伤害"
                    + ("（倒下！）" if dead else ""))
        if game.stealth_enabled and not target.alerted:
            # 它还没发现你 ⇒ 射出蛛丝荡过去，落地就是一记背身突袭
            strike = game.web_strike(target)
            if strike is not None:
                dmg, dead = strike
                return (f"蛛丝摆荡，倒挂突袭 {target.name}，造成 {dmg} 点伤害"
                        + ("（一击放倒！）" if dead else ""))
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
    args = sys.argv[1:]
    fog = "--no-fog" not in args           # M6：默认开视野迷雾
    noise = "--noise" in args              # M8：听觉默认关闭
    # 听觉只在「怪物要被发现才追你」时才有意义 ⇒ --noise 隐含 --stealth
    stealth = "--stealth" in args or noise
    # M10：终端上色（纯展示层，不改字形/状态）。默认 TTY 自动开，可用 --no-color / --color 强制。
    if "--no-color" in args:
        color_on = False
    elif "--color" in args:
        color_on = True
    else:
        color_on = should_color()
    rng = RandomSource(seed=SEED)
    game = Game.procedural(rng, depth=1, fov=fog, stealth=stealth, noise=noise)
    print(f"=== 第 {game.depth} 层「{game.level_name}」（seed={SEED}）===")
    if fog:
        print(LEGEND)
    if stealth:
        print("潜行模式：还没发现你的敌人是小写 m —— 从它看不见的地方荡过去，一击放倒。")
    if noise:
        print("听觉模式：走路无声，但动作会响——蛛网拳（6）、被蛛网弹缠住的怪挣扎（7，"
              "声源在它自己那儿）、下潜落地（8）；倒挂突袭只有 2，几乎无声。听见动静的敌人画 ~。")
    print(colorize(game.render(), color_on))
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
                  + f" | 背包: {_bag_str(game)}（{len(game.inventory)}/5）"
                  + _stealth_str(game) + _noise_str(game))

        if game.depth != shown_depth:
            shown_depth = game.depth
            level_turn = 0
            print(f"\n=== 下潜到第 {game.depth} 层「{game.level_name}」===")
            print(colorize(game.render(), color_on))
        elif level_turn % MAP_EVERY == 0:
            print(colorize(game.render(), color_on))

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
