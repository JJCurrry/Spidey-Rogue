"""M11 光照衰减（明暗梯度 + 暗处降低怪物感知半径）。

主题：MCU 荷兰弟版蜘蛛侠——纽约的夜：
     房间里有灯（路灯 / 霓虹），走廊与死角昏暗甚至全黑；
     蜘蛛侠随身一缕蛛丝微光（PLAYER_GLOW_RADIUS），照亮脚下。

不变量 #1：纯几何，零随机，本模块不引入随机模块（seed-guard 拦截）。
不变量 #2：光照只依赖 grid + 光源（房间中心 + 玩家位置）⇒ 同状态 ⇒ 同光照场；
          不消耗 RandomSource ⇒ 不扰动战斗 / 掉落 / 生成的随机序列。
不变量 #8：本模块只读 grid，不改写地形与任何实体状态。
不变量 #9 延伸：光照只「缩短」怪物感知半径（从不放大），不引入随机、不消耗 rng。

与 M6 视线（遇墙即断）同一哲学：光线也是直线、遇墙即断——
所以光照场用「视线 + 距离衰减」算，而不是声音那种绕墙 Dijkstra。
（与 `sound.py` 的本质差别：光不绕弯、墙是绝对遮挡；声音绕弯、墙只是变闷。）
"""
from __future__ import annotations
from .tiles import WALL
from .fov import has_line_of_sight

# ---- 光源半径（常量，不做调参入口）----
ROOM_LIGHT_RADIUS = 9     # 房间中心固定光源（路灯 / 霓虹）半径：大到能照亮整间房
PLAYER_GLOW_RADIUS = 4    # 蜘蛛侠随身蛛丝微光半径：只够看清脚下几步

# ---- 光照等级（整数档位，便于渲染梯度 + 简化判定）----
LIGHT_LEVEL_DARK = 0      # 全黑：怪物几乎瞎（感知半径降到最低）
LIGHT_LEVEL_DIM = 1       # 昏暗：怪物视野缩短
LIGHT_LEVEL_LIT = 2       # 明亮：怪物正常视野

# ---- 贡献值阈值：光源到格子的衰减贡献 ≥ 该值 ⇒ 落到对应档位 ----
# 贡献 = 半径 - 切比雪夫距离（遇墙即断、随距离线性衰减）。
LIT_CUTOFF = 3            # 贡献 ≥ 3 → 明亮
DIM_CUTOFF = 1            # 贡献 ≥ 1 → 昏暗；否则全黑

# M7 怪物感知半径在暗处的衰减档位（均 < MONSTER_SIGHT_RADIUS=7，
# 保证不变量 #9 的硬性质「怪看得见你 ⇒ 你一定看得见它」不被破坏）。
MONSTER_SIGHT_DARK = 2    # 全黑处怪物只能看清 2 格
MONSTER_SIGHT_DIM = 4     # 昏暗处怪物看清 4 格

Tile = tuple[int, int]
Source = tuple[int, int, int]   # (x, y, radius)


def light_contribution(grid: list[list[str]], source: Source, tile: Tile) -> int:
    """source 对 tile 的光照贡献（整数，遇墙即断、随距离衰减）。

    纯几何、零随机（不变量 #1/#2）：同一份 grid + 同一光源 ⇒ 同一贡献值。
    """
    sx, sy, radius = source
    dx = tile[0] - sx
    dy = tile[1] - sy
    cheb = max(abs(dx), abs(dy))
    if cheb > radius:
        return 0                      # 超出光源半径，照不到
    if not has_line_of_sight(grid, (sx, sy), tile):
        return 0                      # 中间有墙挡着，光遇墙即断
    return radius - cheb              # 距离越近贡献越大（线性衰减）


def light_level(grid: list[list[str]], sources: list[Source],
                tile: Tile) -> int:
    """tile 的光照等级：取所有光源中最大贡献，再映射到档位。

    多光源取最大（不是叠加）——两盏近灯不会合成「超亮」，
    只保证「至少有一处亮源照到」就算亮（不变量 #8：只读 grid）。
    """
    best = 0
    for s in sources:
        c = light_contribution(grid, s, tile)
        if c > best:
            best = c
    if best >= LIT_CUTOFF:
        return LIGHT_LEVEL_LIT
    if best >= DIM_CUTOFF:
        return LIGHT_LEVEL_DIM
    return LIGHT_LEVEL_DARK


def light_field(grid: list[list[str]], sources: list[Source]) -> dict[Tile, int]:
    """逐格光照场（含墙，便于渲染统一取色）。纯几何、零随机（不变量 #1/#2）。"""
    height = len(grid)
    width = len(grid[0]) if height else 0
    field: dict[Tile, int] = {}
    for y in range(height):
        for x in range(width):
            field[(x, y)] = light_level(grid, sources, (x, y))
    return field


def monster_sight_radius(light_lvl: int, base: int = 7) -> int:
    """暗处怪物感知半径衰减（纯函数，不引入随机，不变量 #9）。

    永远 ≤ base（= MONSTER_SIGHT_RADIUS=7）：只缩短、从不放大 ⇒
    「怪物看得见你」必然落在玩家视野半径（8）之内，硬性质不破。
    """
    if light_lvl == LIGHT_LEVEL_DARK:
        return MONSTER_SIGHT_DARK
    if light_lvl == LIGHT_LEVEL_DIM:
        return MONSTER_SIGHT_DIM
    return base
