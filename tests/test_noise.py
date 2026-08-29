"""M8 噪音与听觉行为规格（对应工单 T-008 验收 A）。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（传播与听觉判定不含任何随机）
- 不变量 #2 回合确定性（传播只依赖几何；响度是常量表、不掷骰）
- 不变量 #8 emit_noise 不在 render() 里被调用，且不改写 grid / 实体 / HP
- 不变量 #10 声音传播纯几何、不消耗 RandomSource；听觉默认关闭 ⇒ 既有规格零改动
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.game import (Game, CAUSE_SIGHT, CAUSE_SOUND,
                        NOISE_PUNCH, NOISE_SNEAK, NOISE_STRUGGLE, NOISE_LANDING,
                        WEB_SHOT_DMG)
from rogue.level import Level
from rogue.rng import RandomSource
from rogue.sound import (NOISE_COST_FLOOR, NOISE_COST_WALL,
                         noise_field, noise_cost, noise_reaches, step_cost)
from rogue.tiles import FLOOR, PLAYER, MONSTER, UNAWARE, HEARD

# 一字长廊：玩家 (1,1)，声音沿空地一格一格传过去（代价 = 距离）
_LONG = [
    "##########",
    "#@.......#",
    "##########",
]
# 一墙之隔：x=6 整列是墙，声音只能穿墙过去（穿墙代价 3 ⇒ 白丢两格传播距离）
_NEXT_ROOM = [
    "###########",
    "#@....#...#",
    "#.....#...#",
    "###########",
]
# 绕路图：x=3..5 是三格厚的墙，硬穿要 14，绕下面的走廊只要 12 ⇒ 声音会**绕**着走
_DETOUR = [
    "###########",
    "#@.###....#",
    "#..###....#",
    "#.........#",
    "###########",
]
# 超宽长廊：玩家 (1,1)，可站到 x=10 —— 用来区分「声源在玩家处」与「声源在怪物处」
_WIDE = [
    "############",
    "#@.........#",
    "############",
]
_NO_STAIRS = (-1, -1)


def _make(rows, start=(1, 1), rooms=(), fov=False, stealth=True, noise=True,
          seed=0, stairs=_NO_STAIRS):
    """用固定 rows 搭一局（不撒怪撒道具，只测听觉）。默认开潜行 + 开听觉。

    传 `stairs` 是为了测「下潜落地声」：把楼梯放在起点旁边，走一步就能踩上去。
    """
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, stairs, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth, noise=noise)


def _grid_of(rows):
    return [list(r.replace("@", FLOOR)) for r in rows]


class TestNoiseSwitch(unittest.TestCase):
    """听觉是可选开关：默认关闭 ⇒ 既有 168 例规格不受影响。"""

    def test_noise_disabled_by_default(self):
        self.assertFalse(Game(rng=RandomSource(seed=0)).noise_enabled)
        self.assertFalse(Game.procedural(RandomSource(seed=0), depth=1).noise_enabled)

    def test_noise_enabled_when_asked(self):
        self.assertTrue(_make(_LONG).noise_enabled)
        self.assertTrue(Game(rng=RandomSource(seed=0), noise=True).noise_enabled)
        self.assertTrue(Game.procedural(RandomSource(seed=0), depth=1,
                                        noise=True).noise_enabled)

    def test_emit_noise_is_noop_when_disabled(self):
        # 听觉关闭 ⇒ 发声什么都不做（不惊动、不留记录）⇒ M1~M7 的行为一字节不变
        g = _make(_LONG, noise=False)
        m = g.spawn_monster("街头小混混", 2, 1, hp=99, attack=0, behavior="chase")
        self.assertEqual(g.emit_noise(1, 1, 99), [])
        self.assertFalse(m.alerted)
        self.assertEqual(g.last_noise_loudness, 0)
        self.assertEqual(g.last_noise_heard, 0)
        self.assertEqual(g.heard_monsters(), [])

    def test_noise_off_never_produces_heard_glyph(self):
        # 没人会是 CAUSE_SOUND ⇒ 画面上不会出现 `~`（既有 M/m 断言仍成立）
        g = _make(_LONG, noise=False)
        g.spawn_monster("街头小混混", 3, 1, hp=8, behavior="chase")
        self.assertNotIn(HEARD, g.render())

    def test_noise_does_not_change_chase_when_off(self):
        # 与 test_ai.py 同款：听觉关闭时怪物照旧贪心追击
        g = _make(_LONG, stealth=False, noise=False)
        m = g.spawn_monster("街头小混混", 5, 1, hp=12, attack=3, behavior="chase")
        before = abs(m.x - g.px) + abs(m.y - g.py)
        g.monster_turn()
        self.assertLess(abs(m.x - g.px) + abs(m.y - g.py), before)


class TestNoiseGeometry(unittest.TestCase):
    """传播几何（纯函数 noise_field）：空地 1 / 墙 3 / 绕路 / 越界 / 响度截断。"""

    def test_source_costs_zero(self):
        field = noise_field(_grid_of(_LONG), (1, 1), 5)
        self.assertEqual(field[(1, 1)], 0)

    def test_floor_step_costs_one(self):
        grid = _grid_of(_LONG)
        self.assertEqual(step_cost(grid, 2, 1), NOISE_COST_FLOOR)
        self.assertEqual(noise_cost(grid, (1, 1), (5, 1), 9), 4)

    def test_wall_step_costs_three(self):
        grid = _grid_of(_NEXT_ROOM)
        self.assertEqual(step_cost(grid, 6, 1), NOISE_COST_WALL)
        # 曼哈顿距离 6 + 穿墙多付的 2 格 = 8
        self.assertEqual(NOISE_COST_WALL - NOISE_COST_FLOOR, 2)
        self.assertEqual(noise_cost(grid, (1, 1), (7, 1), 20), 8)

    def test_wall_eats_two_tiles_of_range(self):
        grid = _grid_of(_NEXT_ROOM)
        self.assertFalse(noise_reaches(grid, (1, 1), (7, 1), 7))
        self.assertTrue(noise_reaches(grid, (1, 1), (7, 1), 8))
        # 同样的距离在空地上（_LONG 的 (7,1) 距离 6）只要响度 6
        self.assertTrue(noise_reaches(_grid_of(_LONG), (1, 1), (7, 1), 6))

    def test_sound_detours_around_thick_walls(self):
        grid = _grid_of(_DETOUR)
        cost = noise_cost(grid, (1, 1), (9, 1), 30)
        self.assertEqual(cost, 12)                     # 绕下面的走廊 12 步
        self.assertLess(cost, 1 + 3 * NOISE_COST_WALL + 4)  # 比硬穿三格墙（14）便宜
        self.assertFalse(noise_reaches(grid, (1, 1), (9, 1), 11))
        self.assertTrue(noise_reaches(grid, (1, 1), (9, 1), 12))

    def test_loudness_zero_reaches_nobody(self):
        # 没响度就是没声音——连声源自己也不算被惊动
        self.assertEqual(noise_field(_grid_of(_LONG), (1, 1), 0), {})

    def test_source_out_of_bounds_reaches_nobody(self):
        self.assertEqual(noise_field(_grid_of(_LONG), (-1, -1), 9), {})

    def test_field_never_exceeds_loudness(self):
        grid = _grid_of(_LONG)
        for loud in range(1, 9):
            for (cost) in noise_field(grid, (1, 1), loud).values():
                self.assertLessEqual(cost, loud)

    def test_field_stays_in_bounds(self):
        grid = _grid_of(_DETOUR)
        height, width = len(grid), len(grid[0])
        for (x, y) in noise_field(grid, (1, 1), 40):
            self.assertTrue(0 <= x < width and 0 <= y < height)

    def test_field_is_pure(self):
        # 同输入 ⇒ 同输出；且算一次与算两次完全一样（不变量 #2）
        grid = _grid_of(_DETOUR)
        self.assertEqual(noise_field(grid, (1, 1), 12), noise_field(grid, (1, 1), 12))


class TestHearing(unittest.TestCase):
    """谁听得见：只惊动存活的敌人；听觉查询照实回答、与开关无关。"""

    def test_monster_hears_when_in_range(self):
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 5, 1, hp=99, attack=0, behavior="chase")
        self.assertTrue(g.can_hear(m, 1, 1, 6))
        self.assertIn(m, g.monsters_hearing(1, 1, 6))

    def test_monster_out_of_range_hears_nothing(self):
        g = _make(_WIDE)
        m = g.spawn_monster("街头小混混", 10, 1, hp=99, attack=0, behavior="chase")
        self.assertFalse(g.can_hear(m, 1, 1, 6))
        self.assertNotIn(m, g.monsters_hearing(1, 1, 6))

    def test_dead_monsters_hear_nothing(self):
        g = _make(_LONG)
        alive = g.spawn_monster("街头小混混", 3, 1, hp=99, attack=0, behavior="chase")
        dead = g.spawn_monster("迷途无人机", 4, 1, hp=1, attack=0, behavior="chase")
        dead.take_damage(1)
        self.assertFalse(dead.alive)
        self.assertFalse(g.can_hear(dead, 1, 1, 99))
        self.assertEqual(g.monsters_hearing(1, 1, 99), [alive])

    def test_emit_skips_dead_monsters(self):
        g = _make(_LONG)
        dead = g.spawn_monster("迷途无人机", 2, 1, hp=1, attack=0, behavior="chase")
        dead.take_damage(1)
        self.assertEqual(g.emit_noise(1, 1, 99), [])
        self.assertFalse(dead.alerted)

    def test_query_answers_regardless_of_switch(self):
        # 与 monster_can_see_player 同一哲学：查询照实回答，开关只决定「要不要作用于 AI」
        off = _make(_LONG, noise=False)
        on = _make(_LONG, noise=True)
        m_off = off.spawn_monster("街头小混混", 4, 1, hp=99, attack=0, behavior="chase")
        m_on = on.spawn_monster("街头小混混", 4, 1, hp=99, attack=0, behavior="chase")
        self.assertEqual(off.can_hear(m_off, 1, 1, 5), on.can_hear(m_on, 1, 1, 5))
        self.assertTrue(off.can_hear(m_off, 1, 1, 5))

    def test_hearing_is_independent_of_sight(self):
        # 隔着墙看不见（MONSTER_SIGHT_RADIUS 内但被挡），却听得见
        g = _make(_NEXT_ROOM)
        m = g.spawn_monster("街头小混混", 7, 1, hp=99, attack=0, behavior="chase")
        self.assertFalse(g.monster_can_see_player(m))
        self.assertTrue(g.can_hear(m, 1, 1, NOISE_LANDING))


class TestNoiseSources(unittest.TestCase):
    """四个声源接入点：蛛网拳 / 倒挂突袭 / 挣扎 / 落地；其余动作无声。"""

    def _victim_and_listener(self, sneak, listener_x=6):
        g = _make(_LONG)
        victim = g.spawn_monster("街头小混混", 2, 1, hp=999, attack=0,
                                 behavior="chase")
        listener = g.spawn_monster("迷途无人机", listener_x, 1, hp=99, attack=0,
                                   behavior="chase")
        if not sneak:
            victim.alert((g.px, g.py))   # 已察觉 ⇒ 普通攻击（不是突袭）
        g.player_attack(victim)
        return g, victim, listener

    def test_punch_is_loud(self):
        _, _, listener = self._victim_and_listener(sneak=False, listener_x=6)
        self.assertTrue(listener.alerted)          # 距离 5 ≤ NOISE_PUNCH(6)
        self.assertEqual(listener.alert_cause, CAUSE_SOUND)

    def test_sneak_attack_is_almost_silent(self):
        g, victim, listener = self._victim_and_listener(sneak=True, listener_x=6)
        self.assertTrue(g.last_attack_sneak)
        self.assertFalse(listener.alerted)         # 距离 5 > NOISE_SNEAK(2)

    def test_sneak_still_wakes_the_neighbour_next_door(self):
        # 突袭不是完全无声：贴得很近（距离 2）的同伴还是听得见闷哼
        _, _, listener = self._victim_and_listener(sneak=True, listener_x=3)
        self.assertTrue(listener.alerted)

    def test_sneak_is_much_quieter_than_punch(self):
        self.assertLess(NOISE_SNEAK, NOISE_PUNCH)

    def test_struggle_noise_comes_from_the_tangled_monster(self):
        g = _make(_WIDE)
        victim = g.spawn_monster("街头小混混", 4, 1, hp=99, attack=0,
                                 behavior="chase")
        listener = g.spawn_monster("迷途无人机", 9, 1, hp=99, attack=0,
                                   behavior="chase")
        g.spawn_item("web_cartridge", g.px, g.py)
        g.pick_up()
        self.assertTrue(g.use_item(0))
        self.assertEqual(victim.hp, 99 - WEB_SHOT_DMG)
        self.assertTrue(listener.alerted)
        # 声源是被缠住的那只（距离 5 ≤ 7），不是玩家（距离 8 > 7 ⇒ 若声源在玩家处就听不见）
        self.assertEqual(listener.last_seen, (victim.x, victim.y))
        self.assertFalse(g.can_hear(listener, g.px, g.py, NOISE_STRUGGLE))

    def test_punch_does_not_carry_as_far_as_a_struggle(self):
        # 同一只听众：蛛网拳（声源在玩家、响度 6）够不着，挣扎声（声源在怪、响度 7）够得着
        g = _make(_WIDE)
        victim = g.spawn_monster("街头小混混", 2, 1, hp=999, attack=0,
                                 behavior="chase")
        listener = g.spawn_monster("迷途无人机", 9, 1, hp=99, attack=0,
                                   behavior="chase")
        victim.alert((g.px, g.py))
        g.player_attack(victim)
        self.assertFalse(listener.alerted)

    def test_dead_monster_makes_no_struggle(self):
        g = _make(_WIDE)
        victim = g.spawn_monster("街头小混混", 4, 1, hp=1, attack=0,
                                 behavior="chase")
        g.spawn_item("web_cartridge", g.px, g.py)
        g.pick_up()
        g.use_item(0)
        self.assertFalse(victim.alive)
        self.assertEqual(g.last_noise_loudness, 0)   # 倒下无声

    def test_descending_lands_with_noise(self):
        g = _make(_LONG, stairs=(2, 1), stealth=True, noise=True, seed=4)
        self.assertTrue(g.move(1, 0))
        self.assertTrue(g.can_descend())
        self.assertTrue(g.descend())
        self.assertEqual(g.last_noise_loudness, NOISE_LANDING)
        self.assertEqual(g.last_noise_heard, len(g.heard_monsters()))

    def test_no_landing_noise_when_disabled(self):
        g = _make(_LONG, stairs=(2, 1), stealth=True, noise=False, seed=4)
        g.move(1, 0)
        self.assertTrue(g.descend())
        self.assertEqual(g.last_noise_loudness, 0)
        self.assertEqual(g.heard_monsters(), [])

    def test_landing_alerts_exactly_those_who_can_hear(self):
        for seed in (19, 3):
            g = _make(_LONG, stairs=(2, 1), stealth=True, noise=True, seed=seed)
            g.move(1, 0)
            self.assertTrue(g.descend())
            self.assertTrue(g.monsters, "程序化楼层至少保底一只怪")
            for m in [m for m in g.monsters if m.alive]:
                self.assertEqual(m.alerted,
                                 g.can_hear(m, g.px, g.py, NOISE_LANDING))
                if m.alerted:
                    self.assertEqual(m.last_seen, (g.px, g.py))

    def test_quiet_actions_make_no_noise(self):
        # 走路 / 拾取 / 吃三明治 / 注射纳米强化剂 全部无声（蜘蛛侠落地无响）
        g = _make(_WIDE)
        listener = g.spawn_monster("迷途无人机", 3, 1, hp=99, attack=0,
                                   behavior="chase")
        g.spawn_item("sandwich", g.px, g.py)
        g.spawn_item("nano_boost", g.px + 1, g.py)
        g.pick_up()
        g.move(1, 0)
        g.pick_up()
        g.player_hp = 5
        g.use_item(0)      # 三明治
        g.use_item(0)      # 纳米强化剂
        self.assertEqual(g.last_noise_loudness, 0)
        self.assertFalse(listener.alerted)


class TestNoiseMisdirection(unittest.TestCase):
    """声源未必是玩家：被误导的怪会扑向声源，而不是你。"""

    def test_alerted_monster_targets_the_source(self):
        g = _make(_WIDE)
        m = g.spawn_monster("街头小混混", 5, 1, hp=99, attack=0, behavior="chase")
        heard = g.emit_noise(9, 1, 6)
        self.assertEqual(heard, [m])
        self.assertTrue(m.alerted)
        self.assertEqual(m.alert_cause, CAUSE_SOUND)
        self.assertEqual(m.last_seen, (9, 1))       # 声源，不是玩家位置 (1,1)
        self.assertNotEqual(m.last_seen, (g.px, g.py))

    def test_monster_walks_toward_the_sound_not_the_player(self):
        # 隔着墙看不见玩家 ⇒ 只能凭听觉，朝声源（而不是你）摸过去
        g = _make(_NEXT_ROOM)
        m = g.spawn_monster("街头小混混", 7, 1, hp=99, attack=0, behavior="chase")
        self.assertFalse(g.monster_can_see_player(m))
        g.emit_noise(9, 1, 6)
        to_source = abs(m.x - 9) + abs(m.y - 1)
        to_player = abs(m.x - g.px) + abs(m.y - g.py)
        g.monster_turn()
        self.assertLess(abs(m.x - 9) + abs(m.y - 1), to_source)         # 朝声源走
        self.assertGreater(abs(m.x - g.px) + abs(m.y - g.py), to_player)  # 离你更远了

    def test_sight_overrides_sound_when_both_happen(self):
        # 视听同时发生时以视觉为准：视觉给的是实时位置，听觉只给声源
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 5, 1, hp=99, attack=0, behavior="chase")
        g.emit_noise(8, 1, 6)
        self.assertEqual(m.last_seen, (8, 1))
        self.assertEqual(m.alert_cause, CAUSE_SOUND)
        g.monster_turn()                       # 回合开始：它其实一眼就看见你了
        self.assertEqual(m.last_seen, (g.px, g.py))
        self.assertEqual(m.alert_cause, CAUSE_SIGHT)

    def test_hearing_overrides_an_older_sighting(self):
        # 先看见你在 (1,1)，再听见 (9,1) 的动静 ⇒ 搜捕目标改到声源处
        g = _make(_WIDE)
        m = g.spawn_monster("街头小混混", 5, 1, hp=99, attack=0, behavior="chase")
        m.alert((1, 1))
        self.assertEqual(m.last_seen, (1, 1))
        self.assertEqual(m.alert_cause, CAUSE_SIGHT)
        g.emit_noise(9, 1, 6)
        self.assertEqual(m.last_seen, (9, 1))
        self.assertEqual(m.alert_cause, CAUSE_SOUND)

    def test_being_hit_counts_as_sight_not_sound(self):
        # 挨打的那只知道人在哪 ⇒ 记成「看见」，不画 `~`
        g = _make(_LONG)
        victim = g.spawn_monster("街头小混混", 2, 1, hp=999, attack=0,
                                 behavior="chase")
        g.player_attack(victim)
        self.assertEqual(victim.alert_cause, CAUSE_SIGHT)
        self.assertNotIn(CAUSE_SOUND, [victim.alert_cause])


class TestNoiseRender(unittest.TestCase):
    """画面区分「看见你了 M」与「听见动静 ~」。"""

    def _char_at(self, g: Game, x: int, y: int) -> str:
        return g.render().splitlines()[y][x]

    def test_unaware_still_rendered_lowercase(self):
        g = _make(_LONG)
        g.spawn_monster("街头小混混", 3, 1, hp=8, behavior="chase")
        self.assertEqual(self._char_at(g, 3, 1), UNAWARE)

    def test_heard_monster_rendered_as_tilde(self):
        # 隔着墙：看不见你，但听得见动静 ⇒ 画 `~`
        g = _make(_NEXT_ROOM)
        m = g.spawn_monster("街头小混混", 7, 1, hp=8, behavior="chase")
        self.assertFalse(g.monster_can_see_player(m))
        g.emit_noise(1, 1, 8)
        self.assertTrue(m.alerted)
        self.assertEqual(self._char_at(g, 7, 1), HEARD)

    def test_sighted_monster_rendered_big_m(self):
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 5, 1, hp=8, behavior="chase")
        m.alert((g.px, g.py))
        self.assertEqual(self._char_at(g, 5, 1), MONSTER)

    def test_fog_render_also_marks_heard(self):
        g = _make(_LONG, fov=True)
        m = g.spawn_monster("街头小混混", 4, 1, hp=8, behavior="chase")
        g.emit_noise(1, 1, 6)
        self.assertTrue(g.is_visible(m.x, m.y))
        self.assertEqual(self._char_at(g, 4, 1), HEARD)

    def test_player_still_overrides_monsters(self):
        g = _make(_LONG)
        g.spawn_monster("街头小混混", 2, 1, hp=8, behavior="chase")
        self.assertEqual(self._char_at(g, 1, 1), PLAYER)

    def test_render_does_not_change_alert_state(self):
        # 不变量 #8：render() 只读警觉状态，不改写它
        g = _make(_LONG)
        m = g.spawn_monster("街头小混混", 5, 1, hp=8, behavior="chase")
        g.emit_noise(1, 1, 6)
        before = (m.alerted, m.alert_cause, m.last_seen, m.x, m.y, m.hp)
        g.render()
        g.render()
        self.assertEqual((m.alerted, m.alert_cause, m.last_seen, m.x, m.y, m.hp),
                         before)
        self.assertEqual(g.render(), g.render())


class TestNoiseDeterminism(unittest.TestCase):
    """不变量 #10：传播与听觉不消耗随机；同 seed + 同输入 ⇒ 同结果。"""

    def test_noise_does_not_consume_random(self):
        a = _make(_LONG, noise=False)
        b = _make(_LONG, noise=True)
        b.spawn_monster("街头小混混", 4, 1, hp=99, attack=0, behavior="chase")
        for loud in (1, 3, 6, 8):
            b.emit_noise(1, 1, loud)
            b.render()
        self.assertEqual([a.rng.int(0, 999) for _ in range(5)],
                         [b.rng.int(0, 999) for _ in range(5)])

    def test_emit_noise_does_not_touch_the_world(self):
        # 只改 alerted / last_seen / alert_cause，不动地形、道具、HP、怪物位置
        g = Game.procedural(RandomSource(seed=11), depth=2, stealth=True,
                            noise=True)
        g.spawn_item("sandwich", g.px, g.py)
        snapshot = ([row[:] for row in g.grid], g.player_hp,
                    [(it.key, it.x, it.y) for it in g.items],
                    [(m.name, m.x, m.y, m.hp) for m in g.monsters])
        g.emit_noise(g.px, g.py, NOISE_LANDING)
        self.assertEqual(([row[:] for row in g.grid], g.player_hp,
                          [(it.key, it.x, it.y) for it in g.items],
                          [(m.name, m.x, m.y, m.hp) for m in g.monsters]),
                         snapshot)

    def test_same_seed_same_noisy_run(self):
        moves = [(1, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 0)]

        def run(seed):
            g = Game.procedural(RandomSource(seed=seed), depth=2,
                                stealth=True, noise=True)
            out = [g.render()]
            for dx, dy in moves:
                g.move(dx, dy)
                g.monster_turn()
                out.append((g.render(), g.player_hp,
                            [(m.name, m.x, m.y, m.hp, m.alerted, m.alert_cause)
                             for m in g.monsters]))
            return out

        self.assertEqual(run(19), run(19))

    def test_noise_keeps_hp_and_bag_invariants(self):
        # #3 / #5 / #6 不受听觉影响
        g = Game.procedural(RandomSource(seed=7), depth=3, stealth=True,
                            noise=True)
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


if __name__ == "__main__":
    unittest.main()
