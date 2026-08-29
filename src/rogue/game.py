"""M1：格子地图 + 玩家移动。

注意（不变量 #1）：随机经 RandomSource 注入；本模块不 import random。
注意（GB-1 边界地雷）：不可走出边界、不可走入墙。
"""
from __future__ import annotations
from .rng import RandomSource

WALL = "#"
FLOOR = "."
PLAYER = "@"

# M1 采用固定小房间（程序化生成留待后续里程碑）
_MAP = [
    "#######",
    "#@....#",
    "#.###.#",
    "#.....#",
    "#######",
]


class Game:
    def __init__(self, rng: RandomSource | None = None) -> None:
        self.rng = rng or RandomSource(0)
        self.grid = [list(row) for row in _MAP]
        self.height = len(self.grid)
        self.width = len(self.grid[0])
        self.px, self.py = self._find_player()

    def _find_player(self):
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == PLAYER:
                    return x, y
        raise ValueError("地图缺少玩家起点 @")

    def tile_at(self, x: int, y: int) -> str:
        return self.grid[y][x]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, x: int, y: int) -> bool:
        return self.tile_at(x, y) == WALL

    def move(self, dx: int, dy: int) -> bool:
        """尝试移动；撞墙/越界则失败（位置不变）。返回是否移动成功。"""
        nx, ny = self.px + dx, self.py + dy
        if not self.in_bounds(nx, ny):
            return False
        if self.is_wall(nx, ny):
            return False
        self.grid[self.py][self.px] = FLOOR
        self.px, self.py = nx, ny
        self.grid[self.py][self.px] = PLAYER
        return True

    def render(self) -> str:
        return "\n".join("".join(row) for row in self.grid)
