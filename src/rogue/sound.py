"""M8 噪音与听觉（声音传播几何）。

主题：MCU 荷兰弟版蜘蛛侠——他自己落地无声（走路不发声），
      但**动作**会响：蛛网拳、挣扎的猎物、破窗落地，都是会招来麻烦的动静。

与 M6/M7 的「视野 / 感知」同一套哲学：**纯几何、零随机、只读 grid**。
区别只在传播介质——光走直线、遇墙即断；声音沿走廊**绕**着走、穿墙只是变闷。

不变量 #1：本模块是纯几何计算，不含任何随机，也不引入随机模块（seed-guard 拦截）。
不变量 #2：传播只依赖 grid + 声源 + 响度 ⇒ 同状态 ⇒ 同一份噪声场；
          且不消耗 RandomSource ⇒ 不会扰动战斗/掉落/生成的随机序列。
不变量 #8：本模块只读 grid，不改写地形与任何实体状态。
不变量 #10：听觉判定是纯几何、零随机；是否被听到不掷骰。

算法：以声源为起点在 grid 上跑一次 Dijkstra（空地代价 1、墙代价 3），
      代价超过响度的格子直接丢弃 —— 得到一张「谁听得见」的噪声场。
      地图只有 33×17、响度个位数 ⇒ 每次发声几百个节点，开销可忽略。
"""
from __future__ import annotations
import heapq
from .tiles import WALL

# ---- 传播代价（常量，不做调参入口）----
NOISE_COST_FLOOR = 1   # 声音沿空地传播一格
NOISE_COST_WALL = 3    # 声音穿过一堵墙的代价（闷响 ⇒ 只剩三分之一的传播距离）

Tile = tuple[int, int]
_DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def step_cost(grid: list[list[str]], x: int, y: int) -> int:
    """踏入 (x,y) 这一格的传播代价（墙要闷掉一大截，但不隔音）。"""
    return NOISE_COST_WALL if grid[y][x] == WALL else NOISE_COST_FLOOR


def noise_field(grid: list[list[str]], origin: Tile,
                loudness: int) -> dict[Tile, int]:
    """声源 origin 发出响度 loudness 的动静后，各格的「听见代价」。

    返回 `{坐标: 代价}`，只含**代价 ≤ 响度**的格子（听不见的不在字典里）。
    声源自身代价为 0（站在声源上一定听得见）。

    纯几何、零随机（不变量 #1/#2/#10）：Dijkstra 的最短代价与遍历顺序无关，
    同一份 grid + 声源 + 响度 ⇒ 同一份字典。
    """
    height = len(grid)
    width = len(grid[0]) if height else 0
    field: dict[Tile, int] = {}
    ox, oy = origin
    if not (0 <= ox < width and 0 <= oy < height):
        return field          # 声源在界外 ⇒ 没人听得见
    if loudness <= 0:
        return field          # 没响度就是没声音（连声源自己也算没被惊动）

    field[origin] = 0
    heap: list[tuple[int, int, int]] = [(0, ox, oy)]
    while heap:
        cost, x, y = heapq.heappop(heap)
        if cost > field.get((x, y), cost):
            continue          # 过期条目（已有更便宜的路径到达这里）
        for dx, dy in _DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue      # 越界不参与传播（不变量 #4 的同款边界观）
            nxt = cost + step_cost(grid, nx, ny)
            if nxt > loudness:
                continue      # 传不过去 ⇒ 不必再往外扩
            key = (nx, ny)
            if nxt < field.get(key, loudness + 1):
                field[key] = nxt
                heapq.heappush(heap, (nxt, nx, ny))
    return field


def noise_cost(grid: list[list[str]], origin: Tile, target: Tile,
               loudness: int) -> int | None:
    """声音从 origin 传到 target 的代价；听不见则返回 None（纯几何、零随机）。"""
    return noise_field(grid, origin, loudness).get(target)


def noise_reaches(grid: list[list[str]], origin: Tile, target: Tile,
                  loudness: int) -> bool:
    """target 处能否听见 origin 发出的响度 loudness 的动静（纯几何、零随机）。"""
    return noise_cost(grid, origin, target, loudness) is not None
