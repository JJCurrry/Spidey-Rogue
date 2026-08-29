"""M5 程序化关卡：房间 + 走廊生成（蜘蛛侠 MCU 荷兰弟版 · 纽约都市楼层）。

不变量 #1：生成用的一切随机（房间位置/尺寸、走廊拐向、起点、楼梯、撒点）
          必须经注入的 RandomSource；本模块不直接引入随机模块。
不变量 #2：生成只依赖 rng 与 depth ⇒ 同 seed + 同 depth ⇒ 同楼层。
不变量 #4：楼层外圈恒为墙，走廊只在界内开挖。
不变量 #7：玩家起点可达全部可通行格——生成期用「房间成链 + L 形走廊」保证，
          生成后再用洪泛兜底，把不可达的死口袋回填成墙（故该不变量恒真）。
"""
from __future__ import annotations
from collections import deque
from .rng import RandomSource
from .tiles import WALL, FLOOR, STAIRS

# ---- 楼层尺寸与形状参数（常量，不做调参入口）----
LEVEL_WIDTH = 33
LEVEL_HEIGHT = 17
ROOM_MIN_W = 4
ROOM_MAX_W = 8
ROOM_MIN_H = 3
ROOM_MAX_H = 5
MAX_ROOMS = 7
ROOM_TRIES = 80          # 房间放置的拒绝采样次数上限
EXTRA_LINK_PROB = 0.35   # 隔一间房再连一条走廊的概率（避免退化成一条链）
STAIRS_RETRY = 8         # 楼梯落到起点时重试次数

# ---- 楼层命名（纽约都市地标，depth 超过表长则循环）----
LEVEL_NAMES = (
    "皇后区地铁隧道",
    "奥斯本大厦底层",
    "布鲁克林仓库区",
    "曼哈顿下水道",
    "斯塔克工业废弃实验室",
    "复仇者大厦检修层",
    "纽约公共图书馆地下书库",
    "帝国大厦通风井",
    "神秘客的摄影棚",
    "蜥蜴人的地下巢穴",
)
TUTORIAL_LEVEL_NAME = "皇后区后巷 · 训练层"

# 四方向（BFS / 走廊拐弯共用，顺序固定 ⇒ 确定性）
DIRECTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def level_name_for_depth(depth: int) -> str:
    """按楼层号取纽约地标名；depth 非法时按第 1 层处理。"""
    idx = (max(1, depth) - 1) % len(LEVEL_NAMES)
    return LEVEL_NAMES[idx]


class Room:
    """矩形房间，覆盖 [x, x+w) × [y, y+h) 的闭开区间。"""

    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h

    def intersects(self, other: "Room", pad: int = 1) -> bool:
        """两房各自外扩 pad 格后是否相交；pad=1 保证房间之间至少隔一堵墙。"""
        return (self.x - pad < other.x + other.w and self.x + self.w + pad > other.x
                and self.y - pad < other.y + other.h and self.y + self.h + pad > other.y)

    def tiles(self) -> list[tuple[int, int]]:
        return [(x, y)
                for y in range(self.y, self.y + self.h)
                for x in range(self.x, self.x + self.w)]

    def random_tile(self, rng: RandomSource) -> tuple[int, int]:
        """房间内随机取一格（经 RandomSource，不变量 #1）。"""
        return (rng.int(self.x, self.x + self.w - 1),
                rng.int(self.y, self.y + self.h - 1))

    def __repr__(self) -> str:
        return f"Room(x={self.x},y={self.y},w={self.w},h={self.h})"


class Level:
    """一层楼：地形 + 房间列表 + 起点/楼梯坐标 + 楼层元信息。

    楼梯只是坐标（`stairs`），不改写 grid（与 M4 道具同属实体层，见假设 C/E）。
    """

    def __init__(self, grid: list[list[str]], rooms: list[Room],
                 start: tuple[int, int], stairs: tuple[int, int],
                 depth: int, name: str) -> None:
        self.grid = grid
        self.rooms = rooms
        self.start = start
        self.stairs = stairs
        self.depth = depth
        self.name = name

    @property
    def width(self) -> int:
        return len(self.grid[0])

    @property
    def height(self) -> int:
        return len(self.grid)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile_at(self, x: int, y: int) -> str:
        return self.grid[y][x]

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.grid[y][x] in (FLOOR, STAIRS)

    def walkable_tiles(self) -> list[tuple[int, int]]:
        return [(x, y)
                for y in range(self.height)
                for x in range(self.width)
                if self.is_walkable(x, y)]

    def reachable_from(self, start: tuple[int, int] | None = None) -> set[tuple[int, int]]:
        """四方向洪泛可达集合（BFS，方向顺序固定 ⇒ 确定性）。"""
        origin = start or self.start
        if not self.is_walkable(*origin):
            return set()
        seen = {origin}
        queue = deque([origin])
        while queue:
            x, y = queue.popleft()
            for dx, dy in DIRECTIONS:
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen or not self.is_walkable(nx, ny):
                    continue
                seen.add((nx, ny))
                queue.append((nx, ny))
        return seen

    def is_connected(self, start: tuple[int, int] | None = None) -> bool:
        """不变量 #7 自检：起点是否可达全部可通行格。"""
        origin = start or self.start
        if not self.is_walkable(*origin):
            return False
        reachable = self.reachable_from(origin)
        return len(reachable) == len(self.walkable_tiles())

    def room_at(self, x: int, y: int) -> Room | None:
        for r in self.rooms:
            if r.contains(x, y):
                return r
        return None


# ---------- 生成内部工具 ----------
def _carve_room(grid: list[list[str]], room: Room) -> None:
    for (x, y) in room.tiles():
        grid[y][x] = FLOOR


def _carve_h(grid: list[list[str]], y: int, x0: int, x1: int) -> None:
    for x in range(min(x0, x1), max(x0, x1) + 1):
        if 0 <= x < len(grid[0]) and 0 <= y < len(grid):
            grid[y][x] = FLOOR


def _carve_v(grid: list[list[str]], x: int, y0: int, y1: int) -> None:
    for y in range(min(y0, y1), max(y0, y1) + 1):
        if 0 <= x < len(grid[0]) and 0 <= y < len(grid):
            grid[y][x] = FLOOR


def _carve_corridor(grid: list[list[str]], a: tuple[int, int],
                    b: tuple[int, int], rng: RandomSource) -> None:
    """L 形走廊连接两格；拐向（先横后纵 / 先纵后横）经 RandomSource（#1）。"""
    x0, y0 = a
    x1, y1 = b
    if rng.chance(0.5):
        _carve_h(grid, y0, x0, x1)
        _carve_v(grid, x1, y0, y1)
    else:
        _carve_v(grid, x0, y0, y1)
        _carve_h(grid, y1, x0, x1)


def _fallback_room(width: int, height: int) -> Room:
    """极小地图下一个房间都塞不下时的兜底：中央挖一间。"""
    w = max(1, min(ROOM_MIN_W, width - 2))
    h = max(1, min(ROOM_MIN_H, height - 2))
    return Room(max(1, (width - w) // 2), max(1, (height - h) // 2), w, h)


def _pick_stairs(rng: RandomSource, room: Room, start: tuple[int, int]) -> tuple[int, int]:
    """在指定房间内挑楼梯格；尽量避开玩家起点（房间 ≥ 4×3，必定挑得到）。"""
    for _ in range(STAIRS_RETRY):
        t = room.random_tile(rng)
        if t != start:
            return t
    return room.random_tile(rng)


def _seal_unreachable(level: Level) -> None:
    """不变量 #7 兜底：把起点不可达的可通行格回填成墙（确定性，无随机）。"""
    reachable = level.reachable_from(level.start)
    for (x, y) in level.walkable_tiles():
        if (x, y) not in reachable:
            level.grid[y][x] = WALL


def generate_level(rng: RandomSource, depth: int = 1,
                   width: int = LEVEL_WIDTH,
                   height: int = LEVEL_HEIGHT) -> Level:
    """生成一层「房间 + 走廊」楼层（不变量 #1/#2/#4/#7）。

    流程：拒绝采样摆房间 → 按生成顺序连成链（保证连通）→ 额外环路 →
    定起点与楼梯 → 洪泛兜底封死不可达口袋。
    """
    grid = [[WALL] * width for _ in range(height)]
    rooms: list[Room] = []

    for _ in range(ROOM_TRIES):
        if len(rooms) >= MAX_ROOMS:
            break
        w = rng.int(ROOM_MIN_W, ROOM_MAX_W)
        h = rng.int(ROOM_MIN_H, ROOM_MAX_H)
        x = rng.int(1, max(1, width - w - 2))
        y = rng.int(1, max(1, height - h - 2))
        if x + w >= width or y + h >= height:
            continue  # 不变量 #4：房间必须整体在界内且留出外墙
        cand = Room(x, y, w, h)
        if any(cand.intersects(r) for r in rooms):
            continue
        rooms.append(cand)
        _carve_room(grid, cand)

    if not rooms:
        rooms = [_fallback_room(width, height)]
        _carve_room(grid, rooms[0])

    # 房间成链 ⇒ 生成期即保证连通（#7）
    for a, b in zip(rooms, rooms[1:]):
        _carve_corridor(grid, a.center, b.center, rng)
    # 偶尔再连一条「隔一间」的走廊，避免地图退化成一条链
    for i in range(len(rooms) - 2):
        if rng.chance(EXTRA_LINK_PROB):
            _carve_corridor(grid, rooms[i].center, rooms[i + 2].center, rng)

    start = rooms[0].random_tile(rng)
    stairs = _pick_stairs(rng, rooms[-1], start)

    level = Level(grid, rooms, start, stairs, depth, level_name_for_depth(depth))
    _seal_unreachable(level)
    return level
