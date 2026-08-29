"""M1+M2：格子地图 + 玩家移动 + 战斗系统（蜘蛛侠 MCU 荷兰弟版主题）。

注意（不变量 #1）：随机经 RandomSource 注入；本模块不 import random。
注意（GB-1 边界地雷）：不可走出边界、不可走入墙、不可走入怪物。
注意（不变量 #3）：玩家/怪物 HP 永不为负，由 take_damage 的 max(0, ...) 保证。
"""
from __future__ import annotations
from .rng import RandomSource

WALL = "#"
FLOOR = "."
PLAYER = "@"
MONSTER = "M"

# M1 采用固定小房间（程序化生成留待后续里程碑）
_MAP = [
    "#######",
    "#@....#",
    "#.###.#",
    "#.....#",
    "#######",
]

# M2 战斗数值（蜘蛛侠主题基调：年轻、敏捷、近身格斗 + 蛛网）
PLAYER_MAX_HP = 20
PLAYER_BASE_DMG = 4            # 蛛网拳基础伤害
PLAYER_DMG_VARIANCE = 3        # 伤害浮动区间 [0, 3]，经 Seed 注入（不变量 #1/#2）


class Monster:
    """M2 怪物实体（M3 才赋予 AI 行为）。

    不变量 #3：HP 永不为负，由 take_damage 经 max(0, ...) 保证，业务不得直接写负。
    """

    def __init__(self, name: str, x: int, y: int, hp: int, attack: int = 3) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.attack = attack

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, dmg: int) -> int:
        # 不变量 #3：HP 永不为负（引擎保证，业务不得直接写负）
        self.hp = max(0, self.hp - dmg)
        return self.hp


class Game:
    def __init__(self, rng: RandomSource | None = None) -> None:
        self.rng = rng or RandomSource(0)
        self.grid = [list(row) for row in _MAP]
        self.height = len(self.grid)
        self.width = len(self.grid[0])
        self.px, self.py = self._find_player()
        # M2 玩家状态（蜘蛛侠：年轻但能扛，HP 由引擎钳制 ≥0）
        self.player_max_hp = PLAYER_MAX_HP
        self.player_hp = PLAYER_MAX_HP
        self.monsters: list[Monster] = []

    def _find_player(self):
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == PLAYER:
                    return x, y
        raise ValueError("地图缺少玩家起点 @")

    # ---------- 地图查询 ----------
    def tile_at(self, x: int, y: int) -> str:
        return self.grid[y][x]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_wall(self, x: int, y: int) -> bool:
        return self.tile_at(x, y) == WALL

    # ---------- 移动（GB-1 边界 + M2 不可穿怪）----------
    def move(self, dx: int, dy: int) -> bool:
        """尝试移动；撞墙/越界/踩中怪物则失败（位置不变）。返回是否移动成功。"""
        nx, ny = self.px + dx, self.py + dy
        if not self.in_bounds(nx, ny):
            return False
        if self.is_wall(nx, ny):
            return False
        if self.monster_at(nx, ny):
            return False  # M2：不可穿过怪物，必须先战斗
        self.grid[self.py][self.px] = FLOOR
        self.px, self.py = nx, ny
        self.grid[self.py][self.px] = PLAYER
        return True

    # ---------- M2 怪物 / 战斗 ----------
    def spawn_monster(self, name: str, x: int, y: int, hp: int, attack: int = 3) -> Monster:
        """在 (x,y) 生成一只怪物（M3 之前由外部手动布置，演示/测试用）。"""
        m = Monster(name, x, y, hp, attack)
        self.monsters.append(m)
        return m

    def monster_at(self, x: int, y: int) -> Monster | None:
        for m in self.monsters:
            if m.alive and m.x == x and m.y == y:
                return m
        return None

    def is_adjacent(self, x: int, y: int) -> bool:
        """切比雪夫距离为 1 即相邻（上下左右，不含斜向穿墙）。"""
        return max(abs(self.px - x), abs(self.py - y)) == 1

    def player_attack(self, monster: Monster) -> tuple[int, bool]:
        """玩家攻击相邻怪物（蛛网拳 / Web-Strike）。

        伤害 = 基础 + Seed 注入的随机浮动（不变量 #1/#2：相同 seed + 相同攻击序列 ⇒ 相同伤害）。
        怪物存活则反击玩家（固定值，保持简单；确定性仍由同一 rng 序列保障）。
        返回 (造成的伤害, 怪物是否阵亡)。
        """
        if not monster.alive:
            return 0, False
        if not self.is_adjacent(monster.x, monster.y):
            return 0, False
        dmg = PLAYER_BASE_DMG + self.rng.int(0, PLAYER_DMG_VARIANCE)
        monster.take_damage(dmg)
        if monster.alive:
            self._hurt_player(monster.attack)
        return dmg, not monster.alive

    def _hurt_player(self, dmg: int) -> None:
        # 不变量 #3：玩家 HP 永不为负（引擎保证）
        self.player_hp = max(0, self.player_hp - dmg)

    @property
    def player_dead(self) -> bool:
        return self.player_hp <= 0

    # ---------- 渲染 ----------
    def render(self) -> str:
        view = [list(row) for row in self.grid]
        for m in self.monsters:
            if m.alive and self.in_bounds(m.x, m.y):
                view[m.y][m.x] = MONSTER
        return "\n".join("".join(row) for row in view)
