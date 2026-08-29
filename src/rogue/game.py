"""M1~M9：格子地图 + 玩家移动 + 战斗系统 + 怪物 AI + 道具背包 + 程序化关卡 + 视野渲染 + 怪物感知潜行 + 噪音听觉 + 主动制造响动（蜘蛛侠 MCU 荷兰弟版主题）。

注意（不变量 #1）：随机经 RandomSource 注入；本模块不直接引入随机模块。
注意（GB-1 边界地雷）：不可走出边界、不可走入墙、不可走入怪物。
注意（不变量 #3）：玩家/怪物 HP 永不为负，由 take_damage 的 max(0, ...) 保证。
注意（不变量 #5）：背包容量有上限，满包时拾取失败且道具留在地面。
注意（不变量 #6）：治疗类效果不得让 HP 超过上限，由 _heal_player 的 min(...) 钳制。
注意（不变量 #7）：程序化楼层中玩家起点可达全部可通行格（生成期保证 + 洪泛兜底）。
注意（不变量 #8）：render() 只依赖地形 + 实体 + 玩家位置，不改写任何游戏状态
                  （唯一例外：开启视野时「已探索记忆」集合单调增长）。
注意（不变量 #9）：怪物感知是纯几何、不消耗 RandomSource；潜行默认关闭
                  （stealth=False ⇒ 怪物恒为「已察觉」，M1~M6 的行为一字节不变）。
注意（不变量 #10）：声音传播是纯几何、不消耗 RandomSource；听觉默认关闭
                  （noise=False ⇒ 只有视觉，M1~M7 的行为一字节不变）。
注意（不变量 #11）：投掷几何是纯几何、不消耗 RandomSource；诱饵只在听觉开启时出现
                  （noise=False ⇒ 既不刷「皇后区垃圾桶盖」、也甩不响，M1~M8 一字节不变）。
注意（不变量 #12）：光照衰减是纯几何、不消耗 RandomSource；光照默认关闭
                  （light=False ⇒ 怪物感知半径恒满、render() 字形一字不差，M1~M10 一字节不变）；
                  暗处只缩短怪物感知半径（恒 ≤ MONSTER_SIGHT_RADIUS），
                  所以「怪看得见你 ⇒ 你看得见它」的硬性质不破。
"""
from __future__ import annotations
from typing import NamedTuple
from .rng import RandomSource
from .tiles import (WALL, FLOOR, PLAYER, MONSTER, ITEM, STAIRS, UNSEEN, SENSE,
                    UNAWARE, HEARD)
from .level import Level, Room, generate_level, TUTORIAL_LEVEL_NAME
from .fov import (SIGHT_RADIUS, SPIDER_SENSE_RADIUS, MONSTER_SIGHT_RADIUS,
                  visible_tiles, in_spider_sense, monster_can_see,
                  has_line_of_sight)
from .sound import (NOISE_COST_FLOOR, NOISE_COST_WALL, noise_field,
                    noise_reaches)
from .light import (ROOM_LIGHT_RADIUS, PLAYER_GLOW_RADIUS, LIGHT_LEVEL_LIT,
                    LIGHT_LEVEL_DIM, LIGHT_LEVEL_DARK, light_field,
                    monster_sight_radius)

# M1 采用固定小房间（程序化生成见 M5 的 level.py；默认仍是这张教学图）
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

# M7 怪物感知与潜行（三条常量都是确定性常数，不掷骰 ⇒ 不扰动随机序列，#2/#9）
ALERT_MEMORY = 3               # 失去视线后还会扑向「最后目击点」搜捕几个回合
SNEAK_ATTACK_MULT = 2          # 倒挂突袭的伤害倍率（趁敌人还没反应过来）
WEB_STRIKE_RANGE = 2           # 蛛网摆荡突袭的射程：最多荡几步（沿可通行格，不穿墙）

# M8 噪音与听觉（四条响度都是确定性常数，不掷骰 ⇒ 不扰动随机序列，#2/#10）
# 走路 / 拾取 / 吃三明治 / 注射纳米强化剂全部**无声**：蜘蛛侠落地无响，
# 「发声」始终是玩家自己的选择——不做动作就不会暴露。
NOISE_PUNCH = 6                # 蛛网拳（正面交手，动静传半条走廊）
NOISE_SNEAK = 2                # 倒挂突袭（闷哼，几乎无声 ⇒ 摸掉哨兵未必惊动全层）
NOISE_STRUGGLE = 7             # 被蛛网弹缠住的怪挣扎的动静（声源在**怪物**处 ⇒ 调虎离山）
NOISE_LANDING = 8              # 进入新楼层的落地声（刚落地就惊动一圈人）
CAUSE_SIGHT = "sight"          # 被惊动的原因：看见你了
CAUSE_SOUND = "sound"          # 被惊动的原因：听见动静了（渲染为 `~`）

# M9 主动制造响动（两条常量都是确定性常数，不掷骰 ⇒ 不扰动随机序列，#2/#11）
# 主题：friendly neighborhood Spider-Man —— 脚边有什么抄什么，皇后区最不缺的就是垃圾盖。
NOISE_DECOY = 9                # 垃圾桶盖落地的响动（全场最响：它的全部意义就是响）
DECOY_RANGE = 6                # 甩出距离上限（切比雪夫）⇒ 隔着房间甩不过去，得走到看得见的地方
DECOY_KEY = "decoy"            # 诱饵道具的 key（**不在** ITEM_KEYS 掉落池里，理由见下）

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
    DECOY_KEY: "皇后区垃圾桶盖",  # M9 诱饵（**不进掉落池** ⇒ 不扰动随机序列）
}
# 掉落表刻意**不含** decoy：rng.choice 的取值域从 3 变 4 会改变 _randbelow 的拒绝采样，
# 进而改变随机数消耗 ⇒ 既有三条演示的回放全部作废（不变量 #2）。
# 诱饵改由「听觉开启 ⇒ 开局脚边躺着一个」供给，零随机扰动（见 Game._grant_decoy）。
ITEM_KEYS = ("sandwich", "web_cartridge", "nano_boost")

# M5 程序化关卡的「撒点」数值（地形生成参数见 level.py）
MONSTER_ROOM_PROB = 0.55       # 房间里有怪的概率（起始房间除外）
MONSTERS_PER_ROOM_MAX = 2      # 有怪的房间里刷几只（1~该值，经 rng 决定）
ITEM_ROOM_PROB = 0.6           # 每间房放一件补给的概率（经 rng.chance，#1）
MONSTER_HP_PER_DEPTH = 1       # 怪物 HP 随楼层号的成长量
MONSTER_PLACE_TRIES = 8        # 单个实体在房间里找空位的尝试次数


class MonsterKind(NamedTuple):
    """怪物条目（M5 起按楼层解锁，不再手摆）。"""

    name: str
    hp: int
    attack: int
    behavior: str   # "chase" 贪心追击 / "wander" 随机游走（见 M3）
    min_depth: int  # 从第几层开始出现


# 怪物登记表（蜘蛛侠 MCU 荷兰弟版：街头恶徒 + 经典反派）
# 攻击值刻意压低：M3 规则是「相邻即每回合挨打」，攻高会让换血变得无法承受
MONSTER_TABLE = (
    MonsterKind("街头小混混", 8, 1, "chase", 1),
    MonsterKind("迷途无人机", 5, 1, "wander", 1),
    MonsterKind("神秘客幻象", 7, 2, "wander", 3),
    MonsterKind("奥斯本实验体", 12, 2, "chase", 3),
    MonsterKind("电光人残党", 9, 3, "wander", 5),
    MonsterKind("沙人分身", 14, 2, "chase", 5),
)


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
        # M7 警觉状态机（潜行默认关闭 ⇒ alerted 恒为 True，行为与 M3 完全一致）
        self.alerted = True        # 是否已发现玩家
        self.alert_turns = 0       # 失去视线后还会搜捕几个回合（递减到 0 即放弃）
        self.last_seen = None      # 最后看见玩家的位置（搜捕目标，不是全知追踪）
        self.home = (x, y)         # 巢位：未察觉时回这里待命
        # M8 被惊动的原因：看见（`CAUSE_SIGHT`）/ 听见（`CAUSE_SOUND`）/ 尚未惊动（None）
        # 只用于让画面区分「它看见你了」与「它只是听见动静」——不参与任何伤害或命中判定。
        self.alert_cause: str | None = CAUSE_SIGHT

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def alert(self, pos: tuple[int, int] | None = None,
              cause: str = CAUSE_SIGHT) -> None:
        """被惊动：记下最后目击点并重置搜捕计时（不变量 #9/#10：不掷骰）。

        cause 记下是「看见」还是「听见」——它扑向的 `last_seen` 在听觉情形下是**声源**，
        未必是玩家的真实位置（这就是「调虎离山」成立的地方）。
        """
        self.alerted = True
        self.alert_turns = ALERT_MEMORY
        self.alert_cause = cause
        if pos is not None:
            self.last_seen = tuple(pos)

    def calm(self) -> None:
        """放弃搜捕：回到「未察觉」，回巢待命（不变量 #9：不掷骰）。"""
        self.alerted = False
        self.alert_turns = 0
        self.last_seen = None
        self.alert_cause = None

    def take_damage(self, dmg: int) -> int:
        # 不变量 #3：HP 永不为负（引擎保证，业务不得直接写负）
        self.hp = max(0, self.hp - dmg)
        return self.hp


class Game:
    def __init__(self, rng: RandomSource | None = None, level: Level | None = None,
                 populate: bool = True, fov: bool = False,
                 stealth: bool = False, noise: bool = False,
                 light: bool = False) -> None:
        """rng 为注入的随机源；level 为 None 时用 M1 的固定教学图，否则装载程序化楼层。

        populate 控制装载时是否自动撒怪与补给（测试生成期结构时可关掉）。
        fov 控制是否开启视野/迷雾（M6，默认关闭 ⇒ render() 仍是全图，
        保证 M1~M5 的既有规格不被打破；显式传入 True 才走迷雾渲染）。
        stealth 控制是否开启怪物感知与潜行（M7，默认关闭 ⇒ 怪物恒为「已察觉」，
        M1~M6 的追击行为一字节不变；显式传入 True 才需要「不被发现」地接近）。
        noise 控制是否开启噪音与听觉（M8，默认关闭 ⇒ 只有视觉一条感知通道，
        M1~M7 的行为一字节不变；显式传入 True 后「动静」也会惊动敌人）。
        light 控制是否开启光照衰减（M11，默认关闭 ⇒ 怪物感知半径恒为满值、
        render() 字形一字不差，M1~M10 的行为一字节不变；显式传入 True 后
        暗处怪物视野缩短、地图按光照给出明暗梯度）。
        """
        self.rng = rng or RandomSource(0)
        # M6 视野状态：fov_enabled 是渲染开关，visible/explored 是它的产物
        self.fov_enabled = fov
        self.visible: set[tuple[int, int]] = set()
        self.explored: set[tuple[int, int]] = set()
        # M7 潜行状态：stealth_enabled 是感知开关，Monster.alerted 是它的产物
        self.stealth_enabled = stealth
        self.last_attack_sneak = False  # 上一次成功出手是否为倒挂突袭（供渲染/演示读取）
        # M8 听觉状态：noise_enabled 是听觉开关，Monster.alert_cause 是它的产物
        self.noise_enabled = noise
        self.last_noise_loudness = 0    # 上一次发声的响度（0 = 还没发出过动静）
        self.last_noise_heard = 0       # 上一次动静惊动了几只敌人（供演示读取）
        # M11 光照状态：light_enabled 是光照开关，light_field 是它的产物（渲染梯度 + 感知衰减）
        self.light_enabled = light
        self.light_field: dict[tuple[int, int], int] = {}
        # M2 玩家状态（跨层保留：HP / 背包 / 纳米加成）
        self.player_max_hp = PLAYER_MAX_HP
        self.player_hp = PLAYER_MAX_HP
        self.player_dmg_bonus = 0       # M4：纳米强化剂提供的永久伤害加成
        self.monsters: list[Monster] = []
        self.items: list[Item] = []     # M4：地面道具
        self.inventory: list[Item] = []  # M4：背包（容量上限见 INVENTORY_CAPACITY，#5）
        # M5 楼层元信息（教学图先给默认值，程序化楼层由 load_level 覆盖）
        self.depth = 1
        self.level_name = TUTORIAL_LEVEL_NAME
        self.rooms: list[Room] = []
        self.stairs: tuple[int, int] | None = None
        if level is None:
            self.grid = [list(row) for row in _MAP]
            self.height = len(self.grid)
            self.width = len(self.grid[0])
            self.px, self.py = self._find_player()
            self.update_fov()
            self._grant_decoy()   # M9：听觉开启时脚边躺着一个垃圾桶盖
        else:
            self.load_level(level, populate=populate)

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
        self.update_fov()  # M6：可见区域随移动更新（不变量 #8：只写视野状态）
        return True

    # ---------- M2 怪物 / 战斗 ----------
    def spawn_monster(self, name: str, x: int, y: int, hp: int, attack: int = 3,
                       behavior: str = "chase") -> Monster:
        """在 (x,y) 生成一只怪物（M5 起由 _populate_level 代为撒点，手摆仅用于演示/测试）。

        behavior: "chase" 贪心追击 / "wander" 随机游走（随机仅经 RandomSource，#1）。
        M7：潜行开启时新怪是「未察觉」的（刚刷出来还没发现玩家），
        第一次 `monster_turn` 的感知更新会决定它是否被立刻惊动。
        """
        m = Monster(name, x, y, hp, attack, behavior)
        if self.stealth_enabled:
            m.calm()
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
        M7 潜行：目标尚未察觉 ⇒ **倒挂突袭**——伤害 × SNEAK_ATTACK_MULT（确定性常数，
        不额外掷骰，#9），且敌人来不及反击；命中后它立刻转为已察觉（下回合照样还手）。
        普通攻击仍是 M2 的规则：怪物存活则反击玩家。
        怪物阵亡则按 Seed 掷一次掉落（M4，#1/#2）。
        返回 (造成的伤害, 怪物是否阵亡)；是否突袭读 `self.last_attack_sneak`。
        """
        if not monster.alive or not self.is_adjacent(monster.x, monster.y):
            self.last_attack_sneak = False
            return 0, False
        sneak = self.can_sneak_attack(monster)
        dmg = PLAYER_BASE_DMG + self.player_dmg_bonus + self.rng.int(0, PLAYER_DMG_VARIANCE)
        if sneak:
            dmg *= SNEAK_ATTACK_MULT
        dead = self._damage_monster(monster, dmg)
        # M8：出手就有动静——先让声音扩散（除被打的那只，它下面另行记成「看得见」）
        self.emit_noise(self.px, self.py,
                        NOISE_SNEAK if sneak else NOISE_PUNCH)
        if not dead:
            # 挨了一下，不可能还不知道人在哪 ⇒ 记成「看见」，而不是「听见」
            monster.alert((self.px, self.py))
            if not sneak:
                self._hurt_player(monster.attack)
        self.last_attack_sneak = sneak
        return dmg, dead

    def web_strike(self, target: Monster) -> tuple[int, bool] | None:
        """M7 蛛网摆荡突袭：荡到目标身旁并立刻出手（移动 + 攻击同一回合）。

        这是**主动**潜行唯一的时间窗口——怪物的感知只在世界回合**开始时**更新一次
        （`monster_turn` → `update_awareness`），所以从它看不见的地方荡过去时，
        它还停留在「未察觉」状态，打的就是背身。
        （只走一步是摸不到「看不见你的怪」的：相邻格之间必有视线，见 ADR-003；
          摆荡射程 `WEB_STRIKE_RANGE=2` 让「隔着一堵墙拐角」成为可能。）

        落地格：目标四方向相邻、且玩家沿可通行格 `WEB_STRIKE_RANGE` 步内可达
        （蛛丝只在可通行的空间里荡，不穿墙 ⇒ 不变量 #4 仍成立）。
        已经与目标相邻 ⇒ 直接出手、不移动；够不着或目标已阵亡 ⇒ 原地不动、返回 None。
        返回 `player_attack` 的 (伤害, 是否阵亡)。
        """
        if not target.alive:
            return None
        if self.is_adjacent(target.x, target.y):
            return self.player_attack(target)
        path = self._strike_path(target)
        if path is None:
            return None
        for dx, dy in path:
            if not self.move(dx, dy):
                return None
        return self.player_attack(target)

    def _strike_path(self, target: Monster) -> list[tuple[int, int]] | None:
        """摆荡路径：玩家 →「目标旁能站人的格子」的最短四方向路径（≤ WEB_STRIKE_RANGE 步）。

        逐层 BFS、方向顺序固定 ⇒ 最短路且确定性（#2）。够不着则返回 None（不移动）。
        """
        goals = {(target.x + dx, target.y + dy)
                 for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))}
        goals = {p for p in goals if self._monster_can_enter(*p)}
        if not goals:
            return None
        prev = {(self.px, self.py): None}
        frontier = [(self.px, self.py)]
        found = None
        for _ in range(WEB_STRIKE_RANGE):
            nxt: list[tuple[int, int]] = []
            for (x, y) in frontier:
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    n = (x + dx, y + dy)
                    if n in prev or not self._monster_can_enter(*n):
                        continue  # 不变量 #4：不越界/穿墙/踩玩家/踩怪
                    prev[n] = (x, y)
                    if n in goals:
                        found = n
                        break
                    nxt.append(n)
                if found is not None:
                    break
            if found is not None:
                break
            frontier = nxt
        if found is None:
            return None
        path: list[tuple[int, int]] = []
        node = found
        while prev[node] is not None:
            p = prev[node]
            path.append((node[0] - p[0], node[1] - p[1]))
            node = p
        path.reverse()
        return path

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
        """推进所有存活怪物的 AI（一个世界回合）。顺序固定 ⇒ 确定性（#2）。

        M7：潜行开启时，回合**开始**先统一更新一次感知——「谁看见了蜘蛛侠」。
        这个时机是潜行成立的关键：玩家在自己回合里从敌人视野外扑到面前时，
        敌人还停留在上一回合的「未察觉」状态 ⇒ 突袭窗口天然存在（见 ADR-003）。
        """
        if self.stealth_enabled:
            self.update_awareness()
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
        step = self._pick_monster_step(m, candidates)
        if step:
            m.x, m.y = step

    def _pick_monster_step(self, m: Monster,
                           candidates: list[tuple[int, int]]) -> tuple[int, int] | None:
        """「往哪走一步」的决策（抽出来只为让 monster_act 保持可读）。

        潜行关闭：完全沿用 M3——chase 贪心逼近玩家；wander 随机游走、偶尔改为追击。
        潜行开启：
          - 已察觉：扑向「最后目击点」`last_seen`（不是全知追踪）；
            踏到那儿还没看见人 ⇒ 搜捕计时 -1，耗尽就放弃、回巢待命。
          - 未察觉：chase 怪回巢（确定性、不消耗 rng）；wander 怪照旧随机游走，
            只是「偶尔改为追击」变成「偶尔改为回巢」。
        """
        if not self.stealth_enabled:
            if m.behavior == "wander":
                # 随机游走：偶尔改为追击；方向选择走 RandomSource（#1）
                if self.rng.chance(MONSTER_WANDER_PROB):
                    return self._step_toward(candidates)
                return self.rng.choice(candidates)
            return self._step_toward(candidates)  # chase：贪心逼近，确定性、不消耗 rng

        if m.alerted:
            goal = m.last_seen or (self.px, self.py)
            if (m.x, m.y) == goal:
                self._lose_interest(m)  # 站在最后目击点上没看见人 ⇒ 放弃一层
                return None
            step = self._step_toward_point(candidates, goal, close_in=True)
            if step == goal:
                self._lose_interest(m)  # 这一步踏上了最后目击点
            return step
        # 未察觉：chase 怪回巢待命（已在家则原地不动），wander 怪照旧游荡、偶尔想起回巢
        if m.behavior == "wander":
            go_home = self.rng.chance(MONSTER_WANDER_PROB)
            if go_home and (m.x, m.y) != m.home:
                return self._step_toward_point(candidates, m.home, close_in=True)
            return self.rng.choice(candidates)
        if (m.x, m.y) == m.home:
            return None  # 守着自己的地盘，不瞎晃
        return self._step_toward_point(candidates, m.home, close_in=True)

    def _lose_interest(self, m: Monster) -> None:
        """搜捕计时 -1，归零则放弃（纯状态推进，不掷骰 ⇒ 确定性，#2/#9）。"""
        m.alert_turns -= 1
        if m.alert_turns <= 0:
            m.calm()

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
        return self._step_toward_point(candidates, (self.px, self.py))

    def _step_toward_point(self, candidates: list[tuple[int, int]],
                           goal: tuple[int, int],
                           close_in: bool = False) -> tuple[int, int] | None:
        """在候选格中选离 goal 最近的一步：先比曼哈顿距离，平局取候选靠前者（确定性，#2）。

        close_in=True 时再加一道平局关键字「切比雪夫距离」——
        只比曼哈顿会出现「原地打转」：怪在 (15,3)、玩家在 (13,4)，
        向左与向下的曼哈顿距离都是 2，贪心会随方向顺序挑到向下那一步，
        于是在两格之间来回横跳、永远贴不上来；切比雪夫更小的那一步才是真的在逼近。

        只有 M7 的潜行分支需要 close_in（搜捕/回巢都要真的走拢）。
        M3 的老追击路径保持原样：改它会改写 M1~M6 既有演示的行为，
        而「不改写既有行为」优先于顺手修旧疾——该疾已登记为后续项。
        """
        best = None
        best_key = None
        for (x, y) in candidates:
            manhattan = abs(x - goal[0]) + abs(y - goal[1])
            if close_in:
                key = (manhattan, max(abs(x - goal[0]), abs(y - goal[1])))
            else:
                key = (manhattan, 0)
            if best_key is None or key < best_key:
                best_key = key
                best = (x, y)
        return best

    # ---------- M7 怪物感知与潜行（倒挂突袭）----------
    # 不变量 #9：感知是纯几何（`fov.monster_can_see`），不消耗 RandomSource ⇒ 不扰动随机序列；
    #           「是否倒挂突袭」只由 Monster.alerted 决定，倍率是确定性常数、不额外掷骰。
    # 设计要点（ADR-003）：感知只在世界回合**开始**时更新一次，
    #          于是「玩家回合内从敌人视野外一步扑到面前」天然构成突袭窗口。
    def update_awareness(self) -> None:
        """世界回合开始时统一更新「谁发现了蜘蛛侠」（纯几何、零随机）。

        只在潜行开启时有效；关闭时怪物恒为已察觉（M3 的全知追击，既有规格依赖它）。
        """
        if not self.stealth_enabled:
            return
        for m in self.monsters:
            if m.alive and self.monster_can_see_player(m):
                m.alert((self.px, self.py))

    def monster_can_see_player(self, m: Monster) -> bool:
        """怪物此刻能否看见玩家（#9：纯几何判定，不消耗 RandomSource）。

        潜行关闭时这个几何结果不会去 gate AI——怪物 `alerted` 恒为 True，
        行为仍是 M3 的全知追击；但查询本身照实回答「看不看得见」。
        M11：光照开启时，怪物所在格越暗、感知半径越短（只缩短、不放大，
        半径恒 ≤ MONSTER_SIGHT_RADIUS ⇒ 不变量 #9 的「怪看得见你 ⇒ 你看得见它」不破）。
        """
        if not m.alive:
            return False
        radius = MONSTER_SIGHT_RADIUS
        if self.light_enabled:
            radius = monster_sight_radius(self.light_level_at(m.x, m.y))
        return monster_can_see(self.grid, (m.x, m.y), (self.px, self.py),
                               radius, self.rooms)

    def can_sneak_attack(self, monster: Monster) -> bool:
        """能否对它发动倒挂突袭：潜行开启 + 它还没发现你（#9：不掷骰）。"""
        return self.stealth_enabled and monster.alive and not monster.alerted

    @property
    def hidden(self) -> bool:
        """潜行中：没有任何存活怪物发现你（潜行关闭时恒为 False）。"""
        if not self.stealth_enabled:
            return False
        return not any(m.alive and m.alerted for m in self.monsters)

    def alerted_monsters(self) -> list[Monster]:
        """已发现玩家的存活怪物（潜行关闭时等于全部存活怪）。"""
        return [m for m in self.monsters if m.alive and m.alerted]

    def unaware_monsters(self) -> list[Monster]:
        """还没发现玩家的存活怪物（潜行关闭时恒为空）。"""
        return [m for m in self.monsters if m.alive and not m.alerted]

    def heard_monsters(self) -> list[Monster]:
        """听见动静（而非看见你）才被惊动的存活怪物（听觉关闭时恒为空）。"""
        return [m for m in self.monsters
                if m.alive and m.alerted and m.alert_cause == CAUSE_SOUND]

    # ---------- M8 噪音与听觉（声音传播）----------
    # 不变量 #10：传播是纯几何（`sound.noise_field`：Dijkstra 最短代价，空地 1 / 墙 3），
    #            不消耗 RandomSource ⇒ 不扰动战斗/掉落/生成的随机序列；
    #            「是否被听到」只经 `Monster.alert(cause=CAUSE_SOUND)` 这一入口生效，不额外掷骰。
    # 设计要点（ADR-004）：声源**未必**是玩家——被蛛网弹缠住的怪自己会挣扎出声，
    #            于是同伴被引向它而不是你 ⇒ 听觉不只添压力，还添了一条「调虎离山」的解法。
    def emit_noise(self, x: int, y: int, loudness: int) -> list[Monster]:
        """在 (x,y) 处发出响度 loudness 的动静，惊动听得见的敌人。

        被惊动者扑向**声源**（`last_seen = (x,y)`），不是玩家的实时位置——
        所以声源不在你脚下时，它们会被误导到别处去（这是「调虎离山」的成立条件）。
        听觉关闭时本函数是空操作（返回空表），M1~M7 的行为一字节不变（不变量 #10）。
        返回本次被惊动的敌人（按生成顺序 ⇒ 确定性）。
        """
        if not self.noise_enabled:
            return []
        heard = self.monsters_hearing(x, y, loudness)
        for m in heard:
            m.alert((x, y), cause=CAUSE_SOUND)
        self.last_noise_loudness = loudness
        self.last_noise_heard = len(heard)
        return heard

    def monsters_hearing(self, x: int, y: int,
                         loudness: int) -> list[Monster]:
        """哪些存活怪物听得见 (x,y) 处响度 loudness 的动静（纯查询，不改状态）。

        与 `monster_can_see_player` 同一哲学：查询照实回答「听不听得见」，
        至于这个结果要不要作用于 AI，由 `noise_enabled` 开关决定。
        """
        field = noise_field(self.grid, (x, y), loudness)
        return [m for m in self.monsters if m.alive and (m.x, m.y) in field]

    def can_hear(self, monster: Monster, x: int, y: int, loudness: int) -> bool:
        """这只怪物能否听见 (x,y) 处的动静（纯几何、零随机；死怪一律听不见）。"""
        if not monster.alive:
            return False
        return noise_reaches(self.grid, (x, y), (monster.x, monster.y), loudness)

    # ---------- M9 主动制造响动（皇后区垃圾桶盖）----------
    # 不变量 #11：投掷是纯几何（`fov.has_line_of_sight` + 射程 + 落点可通行），
    #             不消耗 RandomSource ⇒ 不扰动战斗/掉落/生成的随机序列；
    #             响动仍只经 `emit_noise` → `Monster.alert(cause=CAUSE_SOUND)` 唯一入口生效。
    # 设计要点（ADR-005）：M8 的「调虎离山」是**被动**的——唯一的非玩家声源是「被蛛网弹
    #             缠住的怪在挣扎」，想引开巡逻就先得动手，而动手（响 6）已经先招来半个视野。
    #             垃圾盖让动静第一次成为玩家的**主动选择**：声源由你指定，不是由战斗位置决定。
    def can_throw(self, x: int, y: int) -> bool:
        """垃圾盖能否甩到 (x,y)（纯几何、零随机，不变量 #11）。

        三条硬约束，任一不满足即甩不出去：
          1) 在界内且**不是墙**——盖子得落地才响（与 `spawn_item` 对墙格返回 None 同款边界观，#4）；
          2) 切比雪夫距离在 `1..DECOY_RANGE`——「甩出去」本身就意味着离开自己，
             甩在脚下等于把敌人引到自己身上，那是 bug 不是战术；
          3) 玩家**看得见落点**（复用 M6 的 `has_line_of_sight`）——甩没看见的地方不算瞄准。
        """
        if not self.in_bounds(x, y) or self.is_wall(x, y):
            return False
        if not 1 <= max(abs(x - self.px), abs(y - self.py)) <= DECOY_RANGE:
            return False
        return has_line_of_sight(self.grid, (self.px, self.py), (x, y))

    def throw_decoy(self, x: int, y: int) -> list[Monster] | None:
        """把垃圾桶盖甩到 (x,y)：落地发出 `NOISE_DECOY` 的响动，惊动听得见的敌人。

        被惊动者扑向**落点**（`last_seen = (x,y)`），不是玩家的位置 ⇒ 调虎离山成立。
        返回本次被惊动的敌人；落点非法 / 听觉关闭 ⇒ **None（不消耗道具）**——
        与「满血不吃三明治」「场上无怪不射蛛网弹」同一条不浪费规则（#11）。
        """
        if not self.noise_enabled:
            return None          # 听觉关掉的世界里没人听得见，甩出去也是白甩
        if not self.can_throw(x, y):
            return None
        return self.emit_noise(x, y, NOISE_DECOY)

    def _grant_decoy(self) -> Item | None:
        """听觉开启时，开局脚边躺着一个「皇后区垃圾桶盖」（零随机、不扰动生成序列）。

        为什么**不**靠掉落或在房间里撒点：
          - 进 `ITEM_KEYS` 掉落池会把 `rng.choice` 的取值域从 3 改成 4，
            `_randbelow` 的拒绝采样随之改变随机数消耗 ⇒ 既有三条演示的回放全部作废（#2）；
          - 用 rng 在起始房撒点同样会消耗随机数（哪怕只在听觉模式）⇒ 听觉模式的
            地形与撒点就不再与 M8 逐字节相同，回归证据链断掉。
        直接放在起点则一个随机数都不碰：**听觉模式的楼层生成仍与 M8 完全一致**。

        每层都给一个：主题自洽（纽约的楼里到处是垃圾），也保证这条机制用得上。
        """
        if not self.noise_enabled:
            return None
        return self.spawn_item(DECOY_KEY, self.px, self.py)

    # ---------- M4 道具与背包 ----------
    # 不变量 #1：掉落判定与掉落种类必须走 self.rng（RandomSource）；本模块不直接引入随机模块。
    # 不变量 #2：掉落只在「怪物阵亡」这一确定性事件上掷骰 ⇒ 同 seed + 同输入序列 ⇒ 同掉落。
    # 不变量 #4：道具只生成在界内且非墙的格子。
    # 不变量 #5：背包容量上限 INVENTORY_CAPACITY，满包拾取失败且道具留在地面。
    # 不变量 #6：治疗经 _heal_player 钳制，HP 不得超过上限。
    def spawn_item(self, key: str, x: int, y: int) -> Item | None:
        """在 (x,y) 放置一个地面道具；非法格或该格已有道具则返回 None（不叠放）。

        唯一例外：目标是**玩家脚下那一格**且已有道具时，直接「换掉脚下物」——
        M9 的诱饵常驻脚下，测试/玩法需要在脚下临时放别的东西时不应被挡住；
        替换仍保持「一格一物」（不变量 #5），且实战中该分支不会被触发
        （程序化撒点本来就避开起点，落地声也只发生在下潜时）。
        """
        if key not in ITEM_NAMES:
            return None
        if not self.in_bounds(x, y) or self.is_wall(x, y):
            return None  # 不变量 #4
        existing = self.item_at(x, y)
        if existing is not None:
            if (x, y) == (self.px, self.py):
                self.items.remove(existing)   # 换掉脚下物，不叠放
            else:
                return None                    # 其它格：一格只放一个道具
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

    def use_item(self, index: int,
                 target: tuple[int, int] | None = None) -> bool:
        """使用背包中第 index 个道具（0 起）；失败则不消耗。返回是否生效。

        target 只给 M9 的诱饵用：垃圾桶盖要甩到**指定落点**才响，
        其余三件道具传不传都一样（向后兼容既有 215 例规格）。
        """
        if not isinstance(index, int) or index < 0 or index >= len(self.inventory):
            return False
        item = self.inventory[index]
        if item.key == "sandwich":
            if self.player_hp >= self.player_max_hp:
                return False  # 满血不浪费（不消耗）
            self._heal_player(SANDWICH_HEAL)
        elif item.key == "web_cartridge":
            victim = self._nearest_alive_monster()
            if victim is None:
                return False  # 场上无怪，留着下次用（不消耗）
            self._damage_monster(victim, WEB_SHOT_DMG)
            if victim.alive:
                victim.stunned = WEB_SHOT_STUN_TURNS
                # M8：被缠住的怪会挣扎，动静从**它自己**那儿传出去 ⇒
                # 同伴被引向它而不是玩家 —— 这就是「调虎离山」的成立条件。
                self.emit_noise(victim.x, victim.y, NOISE_STRUGGLE)
        elif item.key == "nano_boost":
            self.player_dmg_bonus += NANO_BOOST_DMG
        elif item.key == DECOY_KEY:
            if self.throw_decoy(*self._as_tile(target)) is None:
                return False  # 甩不出去（落点非法 / 听觉关闭）就不消耗
        else:
            return False
        self.inventory.pop(index)
        return True

    @staticmethod
    def _as_tile(target: tuple[int, int] | None) -> tuple[int, int]:
        """把投掷落点参数规整成 (x, y)；传歪了就给一个必然非法的坐标（不抛异常）。"""
        try:
            x, y = target  # type: ignore[misc]
            return (x, y)
        except (TypeError, ValueError):
            return (-1, -1)

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

    # ---------- M5 程序化关卡 ----------
    # 不变量 #1：撒点用的随机全部经 self.rng（RandomSource），本模块不直接引入随机模块。
    # 不变量 #2：先生成地形、再按固定房间顺序撒点 ⇒ 同 seed + 同 depth ⇒ 同楼层。
    # 不变量 #7：楼层由 level.generate_level 保证连通，玩家起点可达全部可通行格。
    @classmethod
    def procedural(cls, rng: RandomSource, depth: int = 1,
                   fov: bool = False, stealth: bool = False,
                   noise: bool = False, light: bool = False) -> "Game":
        """开一局程序化楼层：生成与撒点共用同一个 rng，先后固定（#1/#2）。

        fov=True 时开启视野/迷雾（M6，默认关闭）；
        stealth=True 时开启怪物感知与潜行（M7，默认关闭）；
        noise=True 时开启噪音与听觉（M8，默认关闭）；
        light=True 时开启光照衰减（M11，默认关闭）。
        """
        return cls(rng=rng, level=generate_level(rng, depth=depth),
                   fov=fov, stealth=stealth, noise=noise, light=light)

    def load_level(self, level: Level, populate: bool = True) -> None:
        """装载一层程序化楼层：重置地形与实体，**保留**玩家 HP / 背包 / 伤害加成。

        M6：新楼层 = 新地图 ⇒ 清空上一层的「已探索记忆」（记忆跟着地图走，不跨层）。
        """
        self.explored = set()  # 换层即失忆：上一层的地形记忆对新楼层无意义
        self.grid = [list(row) for row in level.grid]
        self.height = level.height
        self.width = level.width
        self.depth = level.depth
        self.level_name = level.name
        self.rooms = list(level.rooms)
        self.stairs = level.stairs
        self.px, self.py = level.start
        self.grid[self.py][self.px] = PLAYER
        self.monsters = []
        self.items = []
        self.update_fov()  # M6：装载后立刻算一次可见区域
        if populate:
            self._populate_level()
        self._grant_decoy()  # M9：新一层，又随手抄到一个垃圾桶盖（在撒点之后，不抢补给的位置）

    def _populate_level(self) -> None:
        """按房间撒怪与补给：起始房间不刷怪，留一间房喘息。

        有怪的房间（概率 MONSTER_ROOM_PROB）再刷 1~MONSTERS_PER_ROOM_MAX 只，
        于是有的房间空着、有的埋伏两只——楼层整体密度约每两间房一只。
        """
        spawnable = [r for r in self.rooms if not r.contains(self.px, self.py)]
        for room in spawnable:
            if self.rng.chance(MONSTER_ROOM_PROB):
                for _ in range(self.rng.int(1, MONSTERS_PER_ROOM_MAX)):
                    spot = self._free_tile_in(room)
                    if spot is None:
                        break
                    self._spawn_random_monster(self.depth, *spot)
        if not self.monsters and spawnable:
            # 保底：整层至少一只怪，免得生成出「一只怪都没有」的空楼层
            spot = self._free_tile_in(spawnable[-1])
            if spot is not None:
                self._spawn_random_monster(self.depth, *spot)
        for room in self.rooms:
            if self.rng.chance(ITEM_ROOM_PROB):
                spot = self._free_tile_in(room)
                if spot is not None:
                    self.spawn_item(self.rng.choice(ITEM_KEYS), *spot)

    def _free_tile_in(self, room: Room,
                      tries: int = MONSTER_PLACE_TRIES) -> tuple[int, int] | None:
        """房间内找一格「可通行且空着」的位置；找不到返回 None（不变量 #4）。"""
        for _ in range(tries):
            x, y = room.random_tile(self.rng)
            if not self.in_bounds(x, y) or self.is_wall(x, y):
                continue
            if (x, y) == (self.px, self.py) or (x, y) == self.stairs:
                continue
            if self.monster_at(x, y) or self.item_at(x, y):
                continue
            return (x, y)
        return None

    def _spawn_random_monster(self, depth: int, x: int, y: int) -> Monster:
        """从已解锁的怪物条目中随机挑一种（#1），HP 随楼层号成长。"""
        unlocked = [k for k in MONSTER_TABLE if k.min_depth <= depth] or list(MONSTER_TABLE)
        kind = self.rng.choice(unlocked)
        hp = kind.hp + (depth - 1) * MONSTER_HP_PER_DEPTH
        return self.spawn_monster(kind.name, x, y, hp, kind.attack, kind.behavior)

    def can_descend(self) -> bool:
        """是否站在下行楼梯上（固定教学图没有楼梯 ⇒ 恒为 False）。"""
        return self.stairs is not None and (self.px, self.py) == self.stairs

    def descend(self) -> bool:
        """下潜到下一层：重生成楼层、重置实体，保留 HP / 背包 / 伤害加成。

        M8：落地有声——刚落到新一层时的动静会惊动附近的人（`NOISE_LANDING`）。
        只有**下潜**才落地（开局你已经在楼里了），所以发声点在这里而不在 `load_level`。
        """
        if not self.can_descend():
            return False
        self.load_level(generate_level(self.rng, depth=self.depth + 1))
        self.emit_noise(self.px, self.py, NOISE_LANDING)
        return True

    # ---------- M6 视野 / 渲染层（蜘蛛感应）----------
    # 不变量 #1：视野是纯几何计算，不消耗 RandomSource ⇒ 不扰动战斗/掉落/生成序列。
    # 不变量 #2：视野只依赖 grid + 玩家位置 + rooms ⇒ 同状态 ⇒ 同可见集合。
    # 不变量 #8：这里的函数只写 self.visible / self.explored，不碰 grid 与任何实体。
    def update_fov(self) -> set[tuple[int, int]]:
        """重算可见格，并把它们并入「已探索记忆」（记忆只增不减）。

        幂等：同样的状态算几次结果都一样（#2/#8）。
        M11：光照开启时顺手重算光照场（同一份 grid + 光源 ⇒ 同一份场，#1/#2）。
        """
        self.visible = visible_tiles(self.grid, (self.px, self.py),
                                     SIGHT_RADIUS, self.rooms)
        self.explored |= self.visible
        if self.light_enabled:
            self.update_light()
        return self.visible

    # ---------- M11 光照衰减（明暗梯度 + 暗处缩短怪物感知半径）----------
    # 不变量 #1/#2：光照是纯几何（`light.light_field`），不消耗 RandomSource；
    #          不变量 #8：只读 grid 与坐标，不改写任何状态（update_light 只写 self.light_field）。
    # 不变量 #9 延伸：光照只缩短怪物感知半径（monster_sight_radius 恒 ≤ MONSTER_SIGHT_RADIUS），
    #          所以「怪看得见你 ⇒ 你看得见它」的硬性质不被破坏。
    # 设计要点（ADR-007）：光源 = 房间中心固定灯 + 玩家随身微光；
    #          光遇墙即断（与 M6 视线同哲学，与 M8 声音绕墙不同），
    #          于是「房间亮、走廊与死角暗」天然形成明暗梯度，暗处的哨兵成了近视眼。
    def _light_sources(self) -> list[tuple[int, int, int]]:
        """当前楼层的光源列表（房间中心固定灯 + 玩家随身微光）。"""
        sources = [(r.center[0], r.center[1], ROOM_LIGHT_RADIUS)
                   for r in self.rooms]
        if self.light_enabled:
            sources.append((self.px, self.py, PLAYER_GLOW_RADIUS))
        return sources

    def update_light(self) -> None:
        """重算逐格光照场（纯几何、零随机，不变量 #1/#2/#8）。

        光照关闭时清空场（任何查询都按「全亮」处理，不改变任何行为）。
        """
        if not self.light_enabled:
            self.light_field = {}
            return
        self.light_field = light_field(self.grid, self._light_sources())

    def light_level_at(self, x: int, y: int) -> int:
        """(x,y) 的光照等级；光照关闭时恒为「明亮」（不影响任何行为，#8/#9）。
        """
        if not self.light_enabled:
            return LIGHT_LEVEL_LIT
        return self.light_field.get((x, y), LIGHT_LEVEL_DARK)

    def is_visible(self, x: int, y: int) -> bool:
        return (x, y) in self.visible

    def is_explored(self, x: int, y: int) -> bool:
        return (x, y) in self.explored

    def visible_monsters(self) -> list[Monster]:
        """当前看得见的存活怪物（视野内的敌人才画成 M）。"""
        return [m for m in self.monsters
                if m.alive and self.is_visible(m.x, m.y)]

    def spider_sense(self) -> list[Monster]:
        """蜘蛛感应：半径内（穿墙）能感到轮廓的存活怪物，含已经看得见的。

        半径 SPIDER_SENSE_RADIUS 刻意小于视野半径 SIGHT_RADIUS——是预警不是透视。
        """
        return [m for m in self.monsters
                if m.alive and in_spider_sense((self.px, self.py), (m.x, m.y))]

    # ---------- 渲染 ----------
    def render(self) -> str:
        if self.fov_enabled:
            return self._render_fog()
        return self._render_full()

    def _monster_glyph(self, m: Monster) -> str:
        """怪物的渲染字形（只读状态，不变量 #8/#10）。

        未察觉 `m` ｜ 听见动静但还没看见你 `~` ｜ 已看见你 `M`。
        听觉关闭时不会出现 `~`（没人会是 `CAUSE_SOUND`）⇒ 既有断言仍成立。
        """
        if not m.alerted:
            return UNAWARE
        if self.noise_enabled and m.alert_cause == CAUSE_SOUND:
            return HEARD
        return MONSTER

    def _render_full(self) -> str:
        """M1~M5 的全图渲染（视野关闭时的路径，既有规格都跑在这条上）。"""
        view = [list(row) for row in self.grid]
        # M5：楼梯画在空地板上（优先级最低，道具/怪物/玩家依次覆盖）
        if self.stairs is not None and self.in_bounds(*self.stairs):
            sx, sy = self.stairs
            if view[sy][sx] == FLOOR:
                view[sy][sx] = STAIRS
        # M4：地面道具画在空地板上；玩家/怪物优先显示
        for it in self.items:
            if self.in_bounds(it.x, it.y) and view[it.y][it.x] == FLOOR:
                view[it.y][it.x] = ITEM
        for m in self.monsters:
            if m.alive and self.in_bounds(m.x, m.y):
                # M7/M8：未察觉画小写 m（可从背后倒挂突袭）、听见动静画 ~、已看见画 M
                view[m.y][m.x] = self._monster_glyph(m)
        return "\n".join("".join(row) for row in view)

    def _render_fog(self) -> str:
        """M6 迷雾渲染：未探索=空白，走过的地方留记忆，看不见的近处威胁画 `?`。

        渲染优先级（后者覆盖前者）：
          蜘蛛感应 `?` < 楼梯 `>` < 道具 `!` < 怪物 `M` < 玩家 `@`
        （沿用 M5 的 楼梯 < 道具 < 怪物 < 玩家）
        """
        self.update_fov()  # 幂等；怪物移动后进视野也能立刻显示（#8：只写视野状态）

        view = [[UNSEEN] * self.width for _ in range(self.height)]
        # 1) 地形记忆：探索过的格子照实画（玩家脚下的 '@' 归位到玩家层再画）
        for (x, y) in self.explored:
            if not self.in_bounds(x, y):
                continue
            ch = self.grid[y][x]
            view[y][x] = FLOOR if ch == PLAYER else ch
        # 2) 蜘蛛感应：看不见、但感得到的威胁轮廓（穿墙，半径 4）
        for m in self.spider_sense():
            if self.in_bounds(m.x, m.y) and not self.is_visible(m.x, m.y):
                view[m.y][m.x] = SENSE
        # 3) 楼梯 / 4) 道具：不动的东西，看见过就留在记忆里
        if self.stairs is not None and self.in_bounds(*self.stairs):
            sx, sy = self.stairs
            if self.is_explored(sx, sy):
                view[sy][sx] = STAIRS
        for it in self.items:
            if self.in_bounds(it.x, it.y) and self.is_explored(it.x, it.y):
                view[it.y][it.x] = ITEM
        # 5) 怪物：只在**当前可见**时画（怪物会跑，记忆里的位置会骗人）；
        #    M7/M8：未察觉画小写 m、听见动静画 ~、已看见画 M
        for m in self.visible_monsters():
            view[m.y][m.x] = self._monster_glyph(m)
        # 6) 玩家恒可见
        view[self.py][self.px] = PLAYER
        return "\n".join("".join(row) for row in view)
