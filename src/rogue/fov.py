"""M6 视野 / 光照（蜘蛛感应版）。

主题：MCU 荷兰弟版蜘蛛侠——视野即「蜘蛛感应（Spider-Sense）」：
     视线内看得清（画实体），墙后的近处威胁只有轮廓（画 `?`）。

不变量 #1：视野是**纯几何**计算，不含任何随机，本模块也不引入随机模块
          （seed-guard 拦截）。
不变量 #2：视野只依赖 grid + 玩家位置 + rooms ⇒ 同状态 ⇒ 同可见集合；
          且不消耗 RandomSource ⇒ 不会扰动战斗/掉落/生成的随机序列。
不变量 #8：本模块只读 grid，不改写地形与任何实体状态。

算法：对每个「半径内」的候选格，从玩家处拉一条 Bresenham 直线，
      途中遇到墙则该格不可见（墙本身可见、挡住它后面的东西）。
      地图只有 33×17、半径 8 ⇒ 每帧约 200 条线，开销可忽略。
"""
from __future__ import annotations
from .tiles import WALL
from .level import Room

# ---- 视野参数（常量，不做调参入口）----
SIGHT_RADIUS = 8           # 视野半径（欧氏距离，超出即不可见）
SPIDER_SENSE_RADIUS = 4    # 蜘蛛感应半径（切比雪夫距离，穿墙、只给轮廓）

Tile = tuple[int, int]


def bresenham_between(x0: int, y0: int, x1: int, y1: int) -> list[Tile]:
    """Bresenham 直线上「两端点之间」的格子（不含起点与终点）。

    用于视线判定：途中的格子若有一格是墙，就挡住了终点。
    纯整数运算、方向由符号决定 ⇒ 确定性（不变量 #2）。
    """
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    line: list[Tile] = []
    while True:
        line.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return line[1:-1]  # 去掉起点（玩家）与终点（待判定格）


def is_transparent(grid: list[list[str]], x: int, y: int) -> bool:
    """该格是否透光（只有墙挡视线）；越界一律视为不透光。"""
    if y < 0 or y >= len(grid):
        return False
    row = grid[y]
    if x < 0 or x >= len(row):
        return False
    return row[x] != WALL


def has_line_of_sight(grid: list[list[str]], origin: Tile, target: Tile) -> bool:
    """origin 到 target 之间是否无墙遮挡（两端点自身不算遮挡）。"""
    for (x, y) in bresenham_between(origin[0], origin[1], target[0], target[1]):
        if not is_transparent(grid, x, y):
            return False
    return True


def visible_tiles(grid: list[list[str]], origin: Tile,
                  radius: int = SIGHT_RADIUS,
                  rooms: list[Room] | None = None) -> set[Tile]:
    """算出玩家当前可见的格子集合（纯几何、无随机）。

    两步：
    1) 射线：半径内 + 无墙遮挡的格子可见（墙本身可见，但挡住它后面的格子）；
    2) 室内照明：玩家所在房间整间点亮（超出半径也亮，复用 M5 的 Game.rooms）。
    """
    height = len(grid)
    width = len(grid[0]) if height else 0
    ox, oy = origin
    out: set[Tile] = set()
    if not (0 <= ox < width and 0 <= oy < height):
        return out
    out.add(origin)  # 脚下恒可见

    r2 = radius * radius
    for y in range(max(0, oy - radius), min(height, oy + radius + 1)):
        for x in range(max(0, ox - radius), min(width, ox + radius + 1)):
            if (x - ox) ** 2 + (y - oy) ** 2 > r2:
                continue  # 超出视野半径
            if has_line_of_sight(grid, origin, (x, y)):
                out.add((x, y))

    # 进房间点亮整间：站在房里就该看清全屋（房间最大 8×5，不会因半径被切角）
    for room in rooms or ():
        if room.contains(ox, oy):
            out.update(room.tiles())
    return out


def in_spider_sense(origin: Tile, target: Tile,
                    radius: int = SPIDER_SENSE_RADIUS) -> bool:
    """蜘蛛感应：切比雪夫距离 ≤ radius 即能感到「那里有东西」。

    与视野不同，它**穿墙**、不看遮挡——MCU 荷兰弟版的 Peter Tingle 就是这种预警；
    半径（4）刻意小于视野半径（8），是预警而不是透视。
    """
    return max(abs(target[0] - origin[0]), abs(target[1] - origin[1])) <= radius
