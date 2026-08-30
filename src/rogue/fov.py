"""M6 视野 / 光照（蜘蛛感应版）+ M7 怪物感知几何 + M13 光照影响玩家自身视野 + M20 光照影响蜘蛛感应半径。

主题：MCU 荷兰弟版蜘蛛侠——视野即「蜘蛛感应（Spider-Sense）」：
     视线内看得清（画实体），墙后的近处威胁只有轮廓（画 `?`）。
M7：怪物用同一套视线几何判断「有没有发现蜘蛛侠」（`monster_can_see`）——
    视线本来就是对称的，潜行只是把这套几何反过来用在了敌人身上。
M13：光照开启时玩家自己的视野半径也随光照衰减（暗处看不远、亮处不变），
     与 M11「暗处缩短怪物感知」对称；逐格按**目标格光照**决定视野半径
     （亮处的东西容易被看见、暗处的东西难被看见）⇒ #9 硬性质不破。
M20：光照开启时蜘蛛感应（预警）半径也随**目标格光照**衰减（暗 2 / 昏暗 3 / 明 4），
     与 M11 怪物感知、M13 玩家视野形成「黑暗三重削弱」对称；暗处仍保留最小半径 2
     （避免彻底无预警），只缩短、不放大、恒 ≤ `SPIDER_SENSE_RADIUS`(4) ⇒ #9 对称硬性质不破。
     光照关闭时半径恒为 `SPIDER_SENSE_RADIUS`（与 M1~M19 逐字节一致）。

不变量 #1：视野是**纯几何**计算，不含任何随机，本模块也不引入随机模块
          （seed-guard 拦截）。
不变量 #2：视野只依赖 grid + 双方位置 + rooms（+ 光照场，M13）⇒ 同状态 ⇒ 同可见集合；
          且不消耗 RandomSource ⇒ 不会扰动战斗/掉落/生成的随机序列。
不变量 #8：本模块只读 grid（与光照场），不改写地形与任何实体状态。
不变量 #9：怪物感知同样是纯几何、零随机，「是否被察觉」不掷骰。
不变量 #14：光照影响玩家视野是纯几何、零随机、默认关闭（light_field 为 None ⇒ M6 原逻辑）；
           有效半径恒 ≤ SIGHT_RADIUS(8)（按目标格光照，暗处缩短、亮处不变）⇒ #9 对称硬性质不破。

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
# M20 蜘蛛感应半径随光照衰减的档位（与 light.py 的光照等级整数对应：0=暗 1=昏暗 2=明）。
# 与 M11 怪物感知、M13 玩家视野同一哲学——黑暗削弱「感知」，只缩短不放大，
# 恒 ≤ SPIDER_SENSE_RADIUS(4) ⇒ 对称硬性质「怪看得见你 ⇒ 你看得见它」不破。
# 暗处仍保留最小半径 2，避免彻底无预警（超能力仍有兜底）。
SPIDER_SENSE_DARK = 2      # 全黑处蜘蛛感应只预警 2 格
SPIDER_SENSE_DIM = 3       # 昏暗处预警 3 格
# 明亮处蜘蛛感应 = SPIDER_SENSE_RADIUS(4)，无需另设常量
# M7 怪物感知半径：刻意比玩家视野小 1 ⇒ 玩家总能先发现敌人，潜行才有操作空间
MONSTER_SIGHT_RADIUS = 7

# M13 玩家视野半径随光照衰减的档位（与 light.py 的光照等级整数对应：0=暗 1=昏暗 2=明）。
# 与 monster_sight_radius 对称，但玩家基础视野(8)比怪物(7)大 1 ⇒ 同档位下玩家仍先发现敌人。
# 逐格判定时按**目标格光照**决定视野半径（亮处的东西容易被看见、暗处的东西难被看见），
# 不是按玩家所在格——玩家微光让脚下恒 LIT，按玩家所在格算会退化为「视野永远 8」。
# #9 硬性质成立：怪物感知取决于怪物所在格光照、玩家视野取决于目标格(=怪物所在格)光照，
# 同档位下 player_r ≥ monster_r（2≥2 / 4≥4 / 8≥7）⇒「怪看得见你 ⇒ 你看得见它」。
PLAYER_SIGHT_DARK = 2      # 全黑处玩家只看清 2 格（= MONSTER_SIGHT_DARK，对称）
PLAYER_SIGHT_DIM = 4       # 昏暗处玩家看清 4 格（= MONSTER_SIGHT_DIM，对称）
# 明亮处玩家视野 = SIGHT_RADIUS(8)，无需另设常量

Tile = tuple[int, int]


def player_sight_radius(light_lvl: int, base: int = SIGHT_RADIUS) -> int:
    """M13：玩家视野半径随目标格光照衰减（纯函数，只缩短不放大，不变量 #9/#14）。

    永远 ≤ base（= SIGHT_RADIUS=8）：只缩短、从不放大 ⇒
    与 monster_sight_radius 同一哲学——暗处近视、亮处正常。
    光照等级整数与 light.py 的 LIGHT_LEVEL_* 对应（0=暗 / 1=昏暗 / 2=明）。
    """
    if light_lvl == 0:       # LIGHT_LEVEL_DARK
        return PLAYER_SIGHT_DARK
    if light_lvl == 1:       # LIGHT_LEVEL_DIM
        return PLAYER_SIGHT_DIM
    return base              # LIGHT_LEVEL_LIT


def spider_sense_radius(light_lvl: int, base: int = SPIDER_SENSE_RADIUS) -> int:
    """M20：蜘蛛感应半径随目标格光照衰减（纯函数，只缩短不放大，不变量 #9/#20）。

    永远 ≤ base（= SPIDER_SENSE_RADIUS=4）：暗处近视、亮处正常。
    光照等级整数与 light.py 的 LIGHT_LEVEL_* 对应（0=暗 / 1=昏暗 / 2=明）。
    与 M11 怪物感知（monster_sight_radius）、M13 玩家视野（player_sight_radius）同一哲学——
    黑暗削弱「感知」、只缩短不放大，对称硬性质「怪看得见你 ⇒ 你看得见它」不破
    （感应半径恒 ≤ 视野/感知半径）。
    """
    if light_lvl <= 0:       # LIGHT_LEVEL_DARK
        return SPIDER_SENSE_DARK
    if light_lvl == 1:       # LIGHT_LEVEL_DIM
        return SPIDER_SENSE_DIM
    return base              # LIGHT_LEVEL_LIT


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
                  rooms: list[Room] | None = None,
                  light_field: dict[Tile, int] | None = None) -> set[Tile]:
    """算出玩家当前可见的格子集合（纯几何、无随机）。

    两步：
    1) 射线：半径内 + 无墙遮挡的格子可见（墙本身可见，但挡住它后面的格子）；
    2) 室内照明：玩家所在房间整间点亮（超出半径也亮，复用 M5 的 Game.rooms）。

    M13 光照影响玩家视野（light_field 不为 None 时生效）：
      逐格按**目标格光照**决定视野半径——亮处的东西容易被看见（半径 8）、
      暗处的东西难被看见（半径 2）、昏暗居中（半径 4）。
      这绕开了「玩家微光让脚下恒 LIT」的陷阱：微光是给怪物看的标志（M11），
      不是玩家的望远镜；玩家看得远不远取决于**要看的地方亮不亮**，不是脚下亮不亮。
      #9 硬性质成立：怪物感知半径取决于怪物所在格光照（monster_sight_radius），
      玩家视野半径取决于目标格（=怪物所在格）光照（player_sight_radius），
      同光照等级下 player_r ≥ monster_r（DARK 2=2 / DIM 4=4 / LIT 8>7）⇒
      「怪看得见你 ⇒ 距离 ≤ monster_r ⇒ 距离 ≤ player_r ⇒ 你看得见它」。
    """
    height = len(grid)
    width = len(grid[0]) if height else 0
    ox, oy = origin
    out: set[Tile] = set()
    if not (0 <= ox < width and 0 <= oy < height):
        return out
    out.add(origin)  # 脚下恒可见

    if light_field is None:
        # M6 原逻辑：固定半径（光照关闭 ⇒ 与 M1~M12 逐字节一致）
        r2 = radius * radius
        for y in range(max(0, oy - radius), min(height, oy + radius + 1)):
            for x in range(max(0, ox - radius), min(width, ox + radius + 1)):
                if (x - ox) ** 2 + (y - oy) ** 2 > r2:
                    continue  # 超出视野半径
                if has_line_of_sight(grid, origin, (x, y)):
                    out.add((x, y))
    else:
        # M13：光照影响玩家视野——逐格按目标格光照决定视野半径
        # 外层仍按 radius(=8) 圈定候选范围（最亮情况下有效半径就是 8），
        # 内层对每个候选格查其光照等级、算有效半径。
        for y in range(max(0, oy - radius), min(height, oy + radius + 1)):
            for x in range(max(0, ox - radius), min(width, ox + radius + 1)):
                d2 = (x - ox) ** 2 + (y - oy) ** 2
                if d2 == 0:
                    continue  # 脚下已加入
                target_light = light_field.get((x, y), 0)  # 不在场里 ⇒ 全黑
                eff_r = player_sight_radius(target_light, base=radius)
                if d2 > eff_r * eff_r:
                    continue  # 超出有效视野半径
                if has_line_of_sight(grid, origin, (x, y)):
                    out.add((x, y))

    # 进房间点亮整间：站在房里就该看清全屋（房间最大 8×5，不会因半径被切角）
    # 两条路径都保留：光照开启时房间内格子本就是 LIT（房间灯覆盖），这条规则与之兼容；
    # 光照关闭时它仍是 M6 的核心机制。
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


def monster_can_see(grid: list[list[str]], eye: Tile, target: Tile,
                    radius: int = MONSTER_SIGHT_RADIUS,
                    rooms: list[Room] | None = None) -> bool:
    """M7：怪物（eye）能否看见目标（target）——纯几何、零随机、只读 grid。

    四条判定，依次短路（不变量 #9：全程不掷骰、不消耗 RandomSource）：
      1) 同格：贴身一定被察觉；
      2) 同一房间：房间里没有遮挡，与 M6「进房间点亮整间」对称 ⇒ 无视半径；
      3) 超出感知半径：太远看不见；
      4) **双向**射线判遮挡：不仅 eye 看向 target，还要 target 反向看得见 eye。

    为什么第 4 条要双向：整数 Bresenham 不是对称的——(1,1)→(3,2) 途经 (2,1)，
    而 (3,2)→(1,1) 途经 (2,2)；若只判单向，就会出现「怪物能隔着拐角看见玩家、
    玩家却看不见它」的幽灵猎手。双向判定换来一条硬性质：
    **怪物看得见你 ⇒ 你一定看得见它**（怪物感知半径 7 < 玩家视野 8）。
    """
    if eye == target:
        return True
    for room in rooms or ():
        if room.contains(eye[0], eye[1]) and room.contains(target[0], target[1]):
            return True
    dx = target[0] - eye[0]
    dy = target[1] - eye[1]
    if dx * dx + dy * dy > radius * radius:
        return False
    return (has_line_of_sight(grid, eye, target)
            and has_line_of_sight(grid, target, eye))
