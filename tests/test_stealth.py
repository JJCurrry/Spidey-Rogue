"""M7 怪物视野与潜行行为规格（对应工单 T-007 验收 A）。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（感知与突袭判定不含任何随机）
- 不变量 #2 回合确定性（感知只依赖几何；突袭倍率是常数、不额外掷骰）
- 不变量 #4 摆荡突袭同样不越界 / 不穿墙 / 不踩玩家 / 不踩怪
- 不变量 #9 感知纯几何、不消耗 RandomSource；潜行默认关闭 ⇒ 既有规格零改动
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.fov import (MONSTER_SIGHT_RADIUS, SIGHT_RADIUS, monster_can_see)
from rogue.game import (Game, Monster, ALERT_MEMORY, SNEAK_ATTACK_MULT,
                        WEB_STRIKE_RANGE, PLAYER_BASE_DMG, PLAYER_DMG_VARIANCE)
from rogue.level import Level, Room
from rogue.rng import RandomSource
from rogue.tiles import WALL, FLOOR, PLAYER, MONSTER, UNAWARE

# 测试用地图（'@' 只是标注起点，交给 Game 自己落笔）
# 拐角埋伏图：玩家 (1,1) 与怪物 (3,2) 之间隔着 (2,1) 这堵墙 —— 看不见，但两步能荡过去
_AMBUSH = [
    "######",
    "#@#..#",
    "#....#",
    "######",
]
# 一字走廊：玩家 (1,1) 与怪物 (4,1) 之间毫无遮挡 ⇒ 一眼就被发现
_OPEN = [
    "######",
    "#@...#",
    "######",
]
# 长走廊：用于验证感知半径之外看不见
_LONG = [
    "##########",
    "#@.......#",
    "##########",
]
# 搜捕图：左右两间被 x=4 的墙隔开，玩家可以从怪物眼皮底下躲到另一间
_SEARCH = [
    "########",
    "#@..#..#",
    "#...#..#",
    "########",
]
_NO_STAIRS = (-1, -1)


def _make(rows, start=(1, 1), rooms=(), fov=False, stealth=True, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，只测感知与潜行）。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, _NO_STAIRS, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth)


def _open_field(width=25, height=9):
    return (["#" * width]
            + ["#" + FLOOR * (width - 2) + "#"] * (height - 2)
            + ["#" * width])


class TestStealthSwitch(unittest.TestCase):
    """潜行是可选开关：默认关闭 ⇒ 既有 121 例规格不受影响。"""

    def test_stealth_disabled_by_default(self):
        self.assertFalse(Game(rng=RandomSource(seed=0)).stealth_enabled)
        self.assertFalse(Game.procedural(RandomSource(seed=0), depth=1).stealth_enabled)

    def test_stealth_enabled_when_asked(self):
        self.assertTrue(_make(_AMBUSH).stealth_enabled)
        self.assertTrue(Game(rng=RandomSource(seed=0), stealth=True).stealth_enabled)
        self.assertTrue(Game.procedural(RandomSource(seed=0), depth=1,
                                        stealth=True).stealth_enabled)

    def test_monsters_alerted_when_stealth_off(self):
        # 潜行关闭 ⇒ 怪物恒为「已察觉」⇒ M3 的全知追击一字节不变
        g = Game(rng=RandomSource(seed=0))
        m = g.spawn_monster("街头小混混", 4, 3, hp=8, behavior="chase")
        self.assertTrue(m.alerted)
        g.monster_turn()
        self.assertTrue(m.alerted)
        self.assertEqual(len(g.alerted_monsters()), 1)
        self.assertEqual(g.unaware_monsters(), [])
        self.assertFalse(g.hidden)

    def test_monsters_unaware_when_stealth_on(self):
        # 潜行开启 ⇒ 刚刷出来的怪还没发现玩家
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        self.assertFalse(m.alerted)
        self.assertEqual(g.unaware_monsters(), [m])
        self.assertEqual(g.alerted_monsters(), [])
        self.assertTrue(g.hidden)

    def test_stealth_off_chase_behaviour_unchanged(self):
        # 与 test_ai.py::TestMonsterChase 同款断言：关闭潜行时怪物照旧追击
        g = Game(rng=RandomSource(seed=0))
        m = g.spawn_monster("街头小混混", 4, 3, hp=12, attack=3, behavior="chase")
        before = abs(m.x - g.px) + abs(m.y - g.py)
        g.monster_turn()
        self.assertLess(abs(m.x - g.px) + abs(m.y - g.py), before)


class TestMonsterSight(unittest.TestCase):
    """感知几何（纯函数 monster_can_see）：同格 / 同房间 / 半径 / 遮挡。"""

    def test_adjacent_always_seen(self):
        # 相邻格之间没有中间格 ⇒ 必被看见（这也是「只走一步摸不到背身」的根因）
        grid = [list(r.replace("@", FLOOR)) for r in _AMBUSH]
        self.assertTrue(monster_can_see(grid, (1, 1), (1, 2)))
        self.assertTrue(monster_can_see(grid, (1, 1), (2, 2)))

    def test_wall_blocks_monster_sight(self):
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        g.px, g.py = 1, 1
        self.assertFalse(g.monster_can_see_player(m))

    def test_open_corridor_is_seen(self):
        g = _make(_OPEN)
        m = g.spawn_monster("街头小混混", 4, 1, hp=8, behavior="chase")
        self.assertTrue(g.monster_can_see_player(m))

    def test_sight_stops_at_radius(self):
        rows = _open_field()
        grid = [list(r) for r in rows]
        self.assertTrue(monster_can_see(grid, (12, 4), (19, 4)))    # 距离 7
        self.assertFalse(monster_can_see(grid, (12, 4), (20, 4)))   # 距离 8
        self.assertLess(MONSTER_SIGHT_RADIUS, SIGHT_RADIUS)         # 玩家总能先看见

    def test_same_room_is_always_seen(self):
        # 房间里没有遮挡（与 M6「进房间点亮整间」对称）⇒ 无视半径
        rows = _open_field(width=25)
        room = Room(1, 1, 23, 7)
        g = _make(rows, start=(2, 2), rooms=[room])
        m = g.spawn_monster("街头小混混", 22, 6, hp=8, behavior="chase")
        self.assertTrue(room.contains(g.px, g.py) and room.contains(m.x, m.y))
        self.assertTrue(g.monster_can_see_player(m))

    def test_dead_monster_sees_nothing(self):
        g = _make(_OPEN)
        m = g.spawn_monster("街头小混混", 4, 1, hp=8, behavior="chase")
        m.hp = 0
        self.assertFalse(g.monster_can_see_player(m))

    def test_monster_sight_is_two_way(self):
        # 双向判定：怪看玩家 与 玩家看怪 结果一致（Bresenham 单向不对称，见 fov.py）
        grid = [list(r.replace("@", FLOOR)) for r in _AMBUSH]
        self.assertEqual(monster_can_see(grid, (1, 1), (3, 2)),
                         monster_can_see(grid, (3, 2), (1, 1)))
        self.assertFalse(monster_can_see(grid, (1, 1), (3, 2)))  # 拐角挡住了

    def test_anything_that_sees_you_you_can_see(self):
        # 双向判定的硬性质：不存在「看不见的敌人在追你」（怪物视野 7 < 玩家视野 8）
        g = Game.procedural(RandomSource(seed=11), depth=1, fov=True, stealth=True)
        for _ in range(40):
            g.monster_turn()
            for m in g.monsters:
                if m.alive and g.monster_can_see_player(m):
                    self.assertTrue(g.is_visible(m.x, m.y),
                                    f"{m.name}@{m.x},{m.y} 看得见你、你却看不见它")


class TestAwareness(unittest.TestCase):
    """警觉状态机：看见即惊动 → 扑向最后目击点 → 搜捕超时放弃。"""

    def test_seeing_player_alerts_monster(self):
        g = _make(_OPEN)
        m = g.spawn_monster("街头小混混", 4, 1, hp=8, behavior="chase")
        g.monster_turn()
        self.assertTrue(m.alerted)
        self.assertEqual(m.last_seen, (g.px, g.py))
        self.assertEqual(m.alert_turns, ALERT_MEMORY)

    def test_hidden_monster_stays_unaware(self):
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        g.monster_turn()
        self.assertFalse(m.alerted)
        self.assertIsNone(m.last_seen)

    def test_alert_expires_after_losing_sight(self):
        # 看见 → 玩家躲到墙后的另一间 → 搜捕 ALERT_MEMORY 个回合后放弃
        g = _make(_SEARCH)
        m = g.spawn_monster("街头小混混", 3, 1, hp=8, behavior="chase")
        g.monster_turn()                       # 同一直线走廊 ⇒ 被看见
        self.assertTrue(m.alerted)
        g.px, g.py = 6, 1                      # 躲进另一间（x=4 的墙挡住了视线）
        self.assertFalse(g.monster_can_see_player(m))
        for _ in range(ALERT_MEMORY + 6):
            g.monster_turn()
        self.assertFalse(m.alerted)
        self.assertIsNone(m.last_seen)

    def test_searching_monster_heads_to_last_seen(self):
        # 被惊动后扑向「最后目击点」，而不是全知追踪玩家的新位置
        g = _make(_SEARCH)
        m = g.spawn_monster("街头小混混", 3, 1, hp=8, behavior="chase")
        g.monster_turn()
        self.assertEqual(m.last_seen, (1, 1))
        g.px, g.py = 6, 1                      # 玩家躲进另一间：怪物只知道旧目击点
        g.monster_turn()
        self.assertEqual(m.last_seen, (1, 1))
        self.assertNotEqual((m.x, m.y), (6, 1))
        self.assertLess(abs(m.x - 1) + abs(m.y - 1), 3)  # 朝 (1,1) 靠拢

    def test_dead_monster_is_never_alerted(self):
        g = _make(_OPEN)
        m = g.spawn_monster("街头小混混", 4, 1, hp=8, behavior="chase")
        m.hp = 0
        g.monster_turn()
        self.assertFalse(m.alerted)

    def test_awareness_update_is_idempotent(self):
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        g.update_awareness()
        first = (m.alerted, m.alert_turns, m.last_seen)
        g.update_awareness()
        self.assertEqual(first, (m.alerted, m.alert_turns, m.last_seen))


class TestStealthAI(unittest.TestCase):
    """潜行下的行为分支：未察觉回巢 / 察觉后搜捕 / wander 照旧游荡。"""

    def test_unaware_chase_monster_returns_home(self):
        # 未察觉的 chase 怪守着自己的地盘，不会「全知」地朝玩家跑
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        m.x, m.y = 4, 2                        # 挪出巢位（home 仍是 (3,2)）
        self.assertEqual(m.home, (3, 2))
        g.monster_turn()
        self.assertFalse(m.alerted)
        self.assertEqual((m.x, m.y), (3, 2))   # 回巢

    def test_unaware_chase_monster_does_not_approach_player(self):
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        before = abs(m.x - g.px) + abs(m.y - g.py)
        for _ in range(5):
            g.monster_turn()
        self.assertGreaterEqual(abs(m.x - g.px) + abs(m.y - g.py), before)

    def test_alerted_monster_approaches_player(self):
        g = _make(_OPEN)
        m = g.spawn_monster("街头小混混", 4, 1, hp=8, behavior="chase")
        before = abs(m.x - g.px) + abs(m.y - g.py)
        g.monster_turn()
        self.assertLess(abs(m.x - g.px) + abs(m.y - g.py), before)

    def test_unaware_wander_monster_still_uses_rng(self):
        # 未察觉的 wander 怪照旧随机游走（#1：方向选择走 RandomSource）
        g = _make(_AMBUSH)
        m = g.spawn_monster("迷途无人机", 3, 2, hp=8, behavior="wander")
        for _ in range(6):
            g.monster_turn()
            self.assertTrue(g.in_bounds(m.x, m.y))
            self.assertFalse(g.is_wall(m.x, m.y))

    def test_alerted_monster_gives_up_after_search(self):
        # 惊动后玩家躲起来 ⇒ 搜捕若干回合后回到「未察觉」
        g = _make(_SEARCH)
        m = g.spawn_monster("街头小混混", 3, 1, hp=8, behavior="chase")
        g.monster_turn()
        self.assertTrue(m.alerted)
        g.px, g.py = 6, 1
        for _ in range(ALERT_MEMORY + 6):
            g.monster_turn()
        self.assertFalse(m.alerted)


class TestSneakAttack(unittest.TestCase):
    """倒挂突袭：未察觉 ⇒ 双倍伤害 + 不挨反击；命中后立刻转为已察觉。"""

    def test_sneak_attack_doubles_damage(self):
        # 同 seed：两次攻击掷出同一个浮动值 ⇒ 突袭伤害恰好翻倍（倍率是常数，不额外掷骰）
        def hit(stealth):
            g = _make(_LONG, stealth=stealth)
            m = g.spawn_monster("街头小混混", 2, 1, hp=99, attack=3, behavior="chase")
            if stealth:
                m.calm()
            return g.player_attack(m)[0]

        self.assertEqual(hit(stealth=True), SNEAK_ATTACK_MULT * hit(stealth=False))

    def test_sneak_attack_takes_no_counterattack(self):
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 2, 1, hp=99, attack=3, behavior="chase")
        m.calm()
        hp0 = g.player_hp
        g.player_attack(m)
        self.assertEqual(g.player_hp, hp0)
        self.assertTrue(g.last_attack_sneak)

    def test_normal_attack_still_takes_counterattack(self):
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 2, 1, hp=99, attack=3, behavior="chase")
        m.alert((g.px, g.py))
        hp0 = g.player_hp
        g.player_attack(m)
        self.assertEqual(g.player_hp, hp0 - 3)
        self.assertFalse(g.last_attack_sneak)

    def test_sneak_attack_alerts_the_victim(self):
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 2, 1, hp=99, attack=3, behavior="chase")
        m.calm()
        g.player_attack(m)
        self.assertTrue(m.alerted)
        self.assertEqual(m.last_seen, (g.px, g.py))

    def test_no_sneak_when_stealth_disabled(self):
        g = _make(_LONG, stealth=False)
        m = g.spawn_monster("街头小混混", 2, 1, hp=99, attack=3, behavior="chase")
        m.calm()                               # 即便手动置为未察觉，潜行关闭也不算突袭
        hp0 = g.player_hp
        self.assertFalse(g.can_sneak_attack(m))
        g.player_attack(m)
        self.assertFalse(g.last_attack_sneak)
        self.assertEqual(g.player_hp, hp0 - 3)

    def test_can_sneak_attack_ignores_dead(self):
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 2, 1, hp=8, behavior="chase")
        m.calm()
        m.hp = 0
        self.assertFalse(g.can_sneak_attack(m))

    def test_kill_by_sneak_attack_rolls_drop_once(self):
        # 突袭致死也照常掷一次掉落（#1/#2 不受影响）
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 2, 1, hp=1, attack=3, behavior="chase")
        m.calm()
        dmg, dead = g.player_attack(m)
        self.assertTrue(dead)
        self.assertGreaterEqual(dmg, SNEAK_ATTACK_MULT * PLAYER_BASE_DMG)
        self.assertLessEqual(len(g.items), 1)


class TestWebStrike(unittest.TestCase):
    """蛛网摆荡突袭：从敌人看不见的地方荡过去，移动 + 攻击同一回合。"""

    def test_web_strike_reaches_unseen_monster(self):
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=99, attack=3, behavior="chase")
        g.monster_turn()                       # 隔着一堵墙 ⇒ 没被发现
        self.assertFalse(m.alerted)
        self.assertFalse(g.is_adjacent(m.x, m.y))
        res = g.web_strike(m)
        self.assertIsNotNone(res)
        self.assertTrue(g.is_adjacent(m.x, m.y))
        self.assertTrue(g.last_attack_sneak)   # 荡过去时它还不知道你要来

    def test_web_strike_moves_at_most_range(self):
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=99, attack=3, behavior="chase")
        start = (g.px, g.py)
        g.web_strike(m)
        steps = abs(g.px - start[0]) + abs(g.py - start[1])
        self.assertLessEqual(steps, WEB_STRIKE_RANGE)
        self.assertGreater(steps, 0)

    def test_web_strike_adjacent_target_does_not_move(self):
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 2, 1, hp=99, attack=3, behavior="chase")
        start = (g.px, g.py)
        self.assertIsNotNone(g.web_strike(m))
        self.assertEqual((g.px, g.py), start)

    def test_web_strike_out_of_range_returns_none(self):
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 6, 1, hp=99, attack=3, behavior="chase")
        start = (g.px, g.py)
        self.assertIsNone(g.web_strike(m))
        self.assertEqual((g.px, g.py), start)   # 够不着 ⇒ 原地不动

    def test_web_strike_on_dead_target_returns_none(self):
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 3, 1, hp=8, behavior="chase")
        m.hp = 0
        start = (g.px, g.py)
        self.assertIsNone(g.web_strike(m))
        self.assertEqual((g.px, g.py), start)

    def test_web_strike_never_enters_wall(self):
        # 不变量 #4：摆荡路径只在可通行格里走
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=99, attack=3, behavior="chase")
        g.web_strike(m)
        self.assertFalse(g.is_wall(g.px, g.py))
        self.assertTrue(g.in_bounds(g.px, g.py))

    def test_web_strike_on_alerted_target_is_normal_attack(self):
        g = _make(_OPEN)
        m = g.spawn_monster("街头小混混", 3, 1, hp=99, attack=3, behavior="chase")
        m.alert((g.px, g.py))
        hp0 = g.player_hp
        self.assertIsNotNone(g.web_strike(m))
        self.assertFalse(g.last_attack_sneak)
        self.assertEqual(g.player_hp, hp0 - 3)


class TestStealthRender(unittest.TestCase):
    """画面上区分「谁还没发现我」：未察觉 m / 已察觉 M。"""

    def _char_at(self, g: Game, x: int, y: int) -> str:
        return g.render().splitlines()[y][x]

    def test_unaware_monster_rendered_lowercase(self):
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        self.assertEqual(self._char_at(g, 3, 2), UNAWARE)

    def test_alerted_monster_rendered_uppercase(self):
        g = _make(_AMBUSH)
        m = g.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        m.alert((g.px, g.py))
        self.assertEqual(self._char_at(g, 3, 2), MONSTER)

    def test_stealth_off_renders_big_M(self):
        # 与 test_level / test_fov 里 assertIn("M", render()) 同款：潜行关闭时全是大写
        g = _make(_AMBUSH, stealth=False)
        g.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        self.assertIn(MONSTER, g.render())
        self.assertNotIn(UNAWARE, g.render())

    def test_fog_render_also_marks_unaware(self):
        g = _make(_AMBUSH, fov=True)
        m = g.spawn_monster("街头小混混", 2, 2, hp=8, behavior="chase")  # 视野内、未察觉
        self.assertTrue(g.is_visible(m.x, m.y))
        self.assertEqual(self._char_at(g, 2, 2), UNAWARE)

    def test_player_still_overrides_monster(self):
        g = _make(_AMBUSH)
        g.spawn_monster("街头小混混", 2, 2, hp=8, behavior="chase")
        self.assertEqual(self._char_at(g, 1, 1), PLAYER)


class TestStealthDeterminism(unittest.TestCase):
    """不变量 #9：感知不消耗随机；同 seed + 同输入 ⇒ 同结果。"""

    def test_awareness_does_not_consume_random(self):
        a = _make(_AMBUSH, stealth=False)
        b = _make(_AMBUSH, stealth=True)
        b.spawn_monster("街头小混混", 3, 2, hp=8, behavior="chase")
        for _ in range(5):
            b.update_awareness()
            b.render()
        self.assertEqual([a.rng.int(0, 999) for _ in range(5)],
                         [b.rng.int(0, 999) for _ in range(5)])

    def test_sneak_attack_does_not_consume_extra_random(self):
        # 突袭只多乘一个常数 ⇒ 随机序列与普通攻击一模一样
        def rolls(sneak):
            g = _make(_LONG)
            m = g.spawn_monster("街头小混混", 2, 1, hp=999, attack=3, behavior="chase")
            m.calm() if sneak else m.alert((g.px, g.py))
            g.player_attack(m)
            return [g.rng.int(0, 999) for _ in range(3)]

        self.assertEqual(rolls(True), rolls(False))

    def test_same_seed_same_stealth_run(self):
        moves = [(1, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 0)]

        def run(seed):
            g = Game.procedural(RandomSource(seed=seed), depth=2, stealth=True)
            out = [g.render()]
            for dx, dy in moves:
                g.move(dx, dy)
                g.monster_turn()
                out.append((g.render(), g.player_hp,
                            [(m.name, m.x, m.y, m.hp, m.alerted) for m in g.monsters]))
            return out

        self.assertEqual(run(19), run(19))

    def test_stealth_keeps_hp_and_bag_invariants(self):
        # #3 / #5 / #6 不受潜行影响
        g = Game.procedural(RandomSource(seed=7), depth=3, stealth=True)
        g.spawn_item("sandwich", g.px, g.py)
        g.pick_up()
        g.player_hp = 5
        g.use_item(0)
        self.assertLessEqual(g.player_hp, g.player_max_hp)
        for m in g.monsters:
            m.alert((g.px, g.py))
        for _ in range(30):
            g.monster_turn()
        self.assertGreaterEqual(g.player_hp, 0)
        self.assertLessEqual(len(g.inventory), 5)


if __name__ == "__main__":
    unittest.main()
