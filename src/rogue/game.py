"""M1~M4：格子地图 + 玩家移动 + 战斗系统 + 怪物 AI + 道具背包（蜘蛛侠 MCU 荷兰弟版主题）。

注意（不变量 #1）：随机经 RandomSource 注入；本模块不直接引入随机模块。
注意（GB-1 边界地雷）：不可走出边界、不可走入墙、不可走入怪物。
注意（不变量 #3）：玩家/怪物 HP 永不为负，由 take_damage 的 max(0, ...) 保证。
注意（不变量 #5）：背包容量有上限，满包时拾取失败且道具留在地面。
注意（不变量 #6）：治疗类效果不得让 HP 超过上限，由 _heal_player 的 min(...) 钳制。
"""
from __future__ import annotations
from .rng import RandomSource

WALL = "#"
FLOOR = "."
PLAYER = "@"
MONSTER = "M"
ITEM = "!"

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

# M3 怪物 AI（蜘蛛侠主题：街头小混混追击、迷途无人机随机游走）
MONSTER_WANDER_PROB = 0.5      # 随机游走怪「偶尔改为追击」的概率（仅 wander 行为消耗 RandomSource，#1）

# M4 道具与背包（蜘蛛侠主题：梅姨的爱心便当、备用蛛网芯、斯塔克的纳米科技）
INVENTORY_CAPACITY = 5         # 不变量 #5：背包容量上限
DROP_PROB = 0.5                # 怪物死亡掉落概率（经 RandomSource，#1）
SANDWICH_HEAL = 6              # 梅姨的三明治：恢复量（不超过上限，#6）
WEB_SHOT_DMG = 5               # 蛛网发射器备用芯：蛛网弹伤害
WEB_SHOT_STUN_TURNS = 1        # 蛛网弹束缚回合数（被束缚怪跳过行动）
NANO_BOOST_DMG = 2             # 斯塔克纳米强化剂：蛛网拳基础伤害增量（本局内累加）

# 道具目录：key -> 名称（掉落种类经 rng.choice(ITEM_KEYS) 决定，#1）
ITEM_NAMES = {
    "sandwich": "梅姨的三明治",
    "web_cartridge": "蛛网发射器备用芯",
    "nano_boost": "斯塔克纳米强化剂",
}
ITEM_KEYS = ("sandwich", "web_cartridge", "nano_boost")


class Item:
    """M4 道具实体（地面上的可拾取物；拾取后进入 Game.inventory）。"""

    def __init__(self, key: str, x: int, y: int) -> None:
        if key not in ITEM_NAMES:
            raise ValueError(f"未知道具: {key}")
        self.key = key
        self.name = ITEM_NAMES[key]
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Item({self.key}@{self.x},{self.y})"


class Monster:
    """M2 怪物实体（M3 才赋予 AI 行为）。

    不变量 #3：HP 永不为负，由 take_damage 经 max(0, ...) 保证，业务不得直接写负。
    """

    def __init__(self, name: str, x: int, y: int, hp: int, attack: int = 3,
                 behavior: str = "chase") -> None:
        self.name = name
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        # M3 行为模式："chase"（贪心追击，确定性、不消耗 rng）/ "wander"（随机游走，走 RandomSource）
        self.behavior = behavior
        # M4 束缚状态：>0 时跳过接下来若干次行动（蛛网弹命中后置位）
        self.stunned = 0

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
        self.player_dmg_bonus = 0       # M4：纳米强化剂提供的永久伤害加成
        self.monsters: list[Monster] = []
        self.items: list[Item] = []     # M4：地面道具
        self.inventory: list[Item] = []  # M4：背包（容量上限见 INVENTORY_CAPACITY，#5）

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
    def spawn_monster(self, name: str, x: int, y: int, hp: int, attack: int = 3,
                       behavior: str = "chase") -> Monster:
        """在 (x,y) 生成一只怪物（M3 之前由外部手动布置，演示/测试用）。

        behavior: "chase" 贪心追击 / "wander" 随机游走（随机仅经 RandomSource，#1）。
        """
        m = Monster(name, x, y, hp, attack, behavior)
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

        伤害 = 基础(+纳米加成) + Seed 注入的随机浮动（不变量 #1/#2：相同 seed + 相同攻击序列 ⇒ 相同伤害）。
        怪物存活则反击玩家（固定值，保持简单；确定性仍由同一 rng 序列保障）。
        怪物阵亡则按 Seed 掷一次掉落（M4，#1/#2）。
        返回 (造成的伤害, 怪物是否阵亡)。
        """
        if not monster.alive:
            return 0, False
        if not self.is_adjacent(monster.x, monster.y):
            return 0, False
        dmg = PLAYER_BASE_DMG + self.player_dmg_bonus + self.rng.int(0, PLAYER_DMG_VARIANCE)
        dead = self._damage_monster(monster, dmg)
        if not dead:
            self._hurt_player(monster.attack)
        return dmg, dead

    def _damage_monster(self, monster: Monster, dmg: int) -> bool:
        """对怪物造成伤害；阵亡则掷掉落。返回是否阵亡（不变量 #3 由 take_damage 保证）。"""
        monster.take_damage(dmg)
        if monster.alive:
            return False
        self._roll_drop(monster.x, monster.y)
        return True

    def _hurt_player(self, dmg: int) -> None:
        # 不变量 #3：玩家 HP 永不为负（引擎保证）
        self.player_hp = max(0, self.player_hp - dmg)

    def _heal_player(self, amount: int) -> int:
        # 不变量 #6：玩家 HP 不得超过上限（引擎保证）
        self.player_hp = min(self.player_max_hp, self.player_hp + amount)
        return self.player_hp

    # ---------- M3 怪物 AI（追击 / 随机游走）----------
    # 不变量 #1：随机游走的方向选择必须走 self.rng（RandomSource）；本模块不直接引入随机模块。
    # 不变量 #2：同 seed + 同玩家输入序列 ⇒ 同结果；AI 不引入隐藏随机源（chase 不消耗 rng，保持纯确定性）。
    # 不变量 #4：AI 移动不可越界 / 穿墙 / 踩玩家 / 踩其它怪物（由 _monster_can_enter 把关）。
    def monster_turn(self) -> None:
        """推进所有存活怪物的 AI（一个世界回合）。顺序固定 ⇒ 确定性（#2）。"""
        for m in self.monsters:
            self.monster_act(m)

    def monster_act(self, m: Monster) -> None:
        """单只怪物的 AI 决策：被束缚则跳过；相邻则攻击玩家，否则按行为模式移动一步。"""
        if not m.alive:
            return
        if m.stunned > 0:
            m.stunned -= 1  # M4：蛛网弹束缚，吞噬本次行动（不消耗 rng，确定性 #2）
            return
        # 相邻（切比雪夫距离 1，含斜向）→ 攻击玩家，不移动
        if self.is_adjacent(m.x, m.y):
            self.monster_attack(m)
            return
        candidates = self._valid_monster_moves(m)
        if not candidates:
            return  # 无路可走，原地待命
        if m.behavior == "wander":
            # 随机游走：偶尔改为追击；方向选择走 RandomSource（#1）
            if self.rng.chance(MONSTER_WANDER_PROB):
                step = self._step_toward(candidates)
            else:
                step = self.rng.choice(candidates)
        else:  # chase：贪心逼近，确定性、不消耗 rng
            step = self._step_toward(candidates)
        if step:
            m.x, m.y = step

    def monster_attack(self, m: Monster) -> int:
        """怪物攻击相邻玩家（固定伤害，确定性；不变量 #3 由 _hurt_player 钳制）。"""
        if not m.alive or not self.is_adjacent(m.x, m.y):
            return 0
        self._hurt_player(m.attack)
        return m.attack

    def _valid_monster_moves(self, m: Monster) -> list[tuple[int, int]]:
        """四方向正交相邻且可进入的格子（不含斜向，与玩家移动一致）。"""
        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        out = []
        for dx, dy in dirs:
            nx, ny = m.x + dx, m.y + dy
            if self._monster_can_enter(nx, ny):
                out.append((nx, ny))
        return out

    def _monster_can_enter(self, x: int, y: int) -> bool:
        """不变量 #4：越界/墙/玩家/其它怪物 均不可进入。"""
        if not self.in_bounds(x, y):
            return False
        if self.is_wall(x, y):
            return False
        if (x, y) == (self.px, self.py):
            return False  # 不可踩玩家
        if self.monster_at(x, y):
            return False  # 不可踩其它怪物
        return True

    def _step_toward(self, candidates: list[tuple[int, int]]) -> tuple[int, int] | None:
        """在候选格中选曼哈顿距离玩家最近者（贪心追击）；平局取候选列表靠前者（确定性）。"""
        best = None
        best_d = None
        for (x, y) in candidates:
            d = abs(x - self.px) + abs(y - self.py)
            if best_d is None or d < best_d:
                best_d = d
                best = (x, y)
        return best

    # ---------- M4 道具与背包 ----------
    # 不变量 #1：掉落判定与掉落种类必须走 self.rng（RandomSource）；本模块不直接引入随机模块。
    # 不变量 #2：掉落只在「怪物阵亡」这一确定性事件上掷骰 ⇒ 同 seed + 同输入序列 ⇒ 同掉落。
    # 不变量 #4：道具只生成在界内且非墙的格子。
    # 不变量 #5：背包容量上限 INVENTORY_CAPACITY，满包拾取失败且道具留在地面。
    # 不变量 #6：治疗经 _heal_player 钳制，HP 不得超过上限。
    def spawn_item(self, key: str, x: int, y: int) -> Item | None:
        """在 (x,y) 放置一个地面道具；非法格或该格已有道具则返回 None（不叠放）。"""
        if key not in ITEM_NAMES:
            return None
        if not self.in_bounds(x, y) or self.is_wall(x, y):
            return None  # 不变量 #4
        if self.item_at(x, y) is not None:
            return None  # 一格只放一个道具，保持规则简单
        item = Item(key, x, y)
        self.items.append(item)
        return item

    def item_at(self, x: int, y: int) -> Item | None:
        for it in self.items:
            if it.x == x and it.y == y:
                return it
        return None

    @property
    def inventory_full(self) -> bool:
        return len(self.inventory) >= INVENTORY_CAPACITY

    def pick_up(self) -> Item | None:
        """拾取玩家脚下道具入包；无道具或背包已满则返回 None（不变量 #5）。"""
        if self.inventory_full:
            return None
        item = self.item_at(self.px, self.py)
        if item is None:
            return None
        self.items.remove(item)
        self.inventory.append(item)
        return item

    def use_item(self, index: int) -> bool:
        """使用背包中第 index 个道具（0 起）；失败则不消耗。返回是否生效。"""
        if not isinstance(index, int) or index < 0 or index >= len(self.inventory):
            return False
        item = self.inventory[index]
        if item.key == "sandwich":
            if self.player_hp >= self.player_max_hp:
                return False  # 满血不浪费（不消耗）
            self._heal_player(SANDWICH_HEAL)
        elif item.key == "web_cartridge":
            target = self._nearest_alive_monster()
            if target is None:
                return False  # 场上无怪，留着下次用（不消耗）
            self._damage_monster(target, WEB_SHOT_DMG)
            if target.alive:
                target.stunned = WEB_SHOT_STUN_TURNS
        elif item.key == "nano_boost":
            self.player_dmg_bonus += NANO_BOOST_DMG
        else:
            return False
        self.inventory.pop(index)
        return True

    def _nearest_alive_monster(self) -> Monster | None:
        """曼哈顿距离最近的存活怪物；平局取生成顺序靠前者（确定性 #2）。"""
        best = None
        best_d = None
        for m in self.monsters:
            if not m.alive:
                continue
            d = abs(m.x - self.px) + abs(m.y - self.py)
            if best_d is None or d < best_d:
                best_d = d
                best = m
        return best

    def _roll_drop(self, x: int, y: int) -> Item | None:
        """怪物阵亡掉落：先 rng.chance 判定，再 rng.choice 选种类（不变量 #1/#2）。"""
        if not self.rng.chance(DROP_PROB):
            return None
        key = self.rng.choice(ITEM_KEYS)
        return self.spawn_item(key, x, y)

    @property
    def player_dead(self) -> bool:
        return self.player_hp <= 0

    # ---------- 渲染 ----------
    def render(self) -> str:
        view = [list(row) for row in self.grid]
        # M4：地面道具画在空地板上；玩家/怪物优先显示
        for it in self.items:
            if self.in_bounds(it.x, it.y) and view[it.y][it.x] == FLOOR:
                view[it.y][it.x] = ITEM
        for m in self.monsters:
            if m.alive and self.in_bounds(m.x, m.y):
                view[m.y][m.x] = MONSTER
        return "\n".join("".join(row) for row in view)
