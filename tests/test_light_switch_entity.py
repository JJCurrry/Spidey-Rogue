"""M19 灯开关独立实体（墙上的开关 tile，与灯泡分离）。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（开关摆位 / toggle / destroy 纯状态操作，不引入随机、不消耗 rng）
- 不变量 #2 回合确定性（同 seed + 同输入 ⇒ 同开关摆位 / 同光照场）
- 不变量 #8 渲染纯净性（render() 只改可见集合与光照场，不改写 world state；开关是「加字形」而非「改字形」）
- 不变量 #9 硬性质在 M19 下仍成立：怪看得见你 ⇒ 你看得见它（开关只是控制手柄，不动光照几何）
- 不变量 #10 延伸：toggle / destroy 的轻响只经 emit_noise → Monster.alert(cause=CAUSE_SOUND) 唯一入口，
  且声源在**灯具坐标 room.center**（不在开关格、不在玩家处）⇒ 调虎离山成立（与 M14/M16 同源）
- 不变量 #19（M19 新增）：开关是「灯具 room.center 的解耦控制手柄」
  —— toggle/destroy 仍翻 switched_lights/destroyed_lights（按 room.center 记录），复用 M14/M16 全部光照逻辑
  ⇒ 默认关闭（switches=False）时演示与 M18 逐字节一致；开启后行为零回归

设计要点（ADR-015）：保留 M14 的 toggle_light(room.center) / M16 的 destroy_light(room.center) API 不动
（既有 445 例规格零回归），新增平行的 switch API：开关实体摆在与灯泡不同的墙上格子，
蛛网够得到「开关」才能翻转/射碎该房间的灯；声源仍在灯具处，保证已验证的「听觉调虎离山」3 关演示可复现。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.tiles import SWITCH, WALL, FLOOR, PLAYER, UNSEEN
from rogue.light import LIGHT_LEVEL_LIT
from rogue.fov import SIGHT_RADIUS
from rogue.game import (Game, LightSwitch, WEB_LIGHT_RANGE, NOISE_TOGGLE_LIGHT,
                        NOISE_SHATTER_BULB, CAUSE_SOUND)
from rogue.level import Level, Room
from rogue.rng import RandomSource

_NO_STAIRS = (-1, -1)


def _make(rows, start=(1, 1), rooms=(), fov=False, stealth=True,
          light=False, flashlight=False, noise=False, switches=False, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，只测开关实体与光照）。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, _NO_STAIRS, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth, light=light,
                flashlight=flashlight, noise=noise, switches=switches)


# 单房间：玩家在房间内（1,1），房间 (1,1)~(10,3)，中心 (6,2)
_ROOM_INNER = [
    "###########",
    "#@........#",
    "#.........#",
    "#.........#",
    "###########",
]
_ROOM_INNER_ROOM = Room(1, 1, 10, 3)  # center = (1+5, 1+1) = (6,2)
# 开关摆在房间北沿第一格 (1,0)（墙），玩家 (1,1) 距其 1、视线清晰 ⇒ 够得着

# 开阔单房间（用于摆位 / 范围几何）
_OPEN = [
    "#######",
    "#@....#",
    "#.....#",
    "#.....#",
    "#######",
]
_OPEN_ROOM = Room(1, 1, 5, 3)  # center = (3,2)；开关摆在 (1,0)

# 带内墙的迷宫（用于验证「墙挡视线 ⇒ 够不着开关」）
_MAZE = [
    "#######",
    "#@#...#",
    "#.#...#",
    "#.#...#",
    "#######",
]
_MAZE_ROOM = Room(1, 1, 5, 3)  # 仅用于 _make 的 rooms 列表；几何测试用人工注入开关


class TestOptInDefaultOff(unittest.TestCase):
    """M19 默认关闭（opt-in）：switches=False ⇒ 不摆开关、不出 '='、不影响 M1~M18 演示。"""

    def test_switches_off_no_entities(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=False)
        self.assertEqual(g.switches, [])
        self.assertFalse(g.switches_enabled)

    def test_switches_off_render_has_no_equals(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], fov=True, switches=False)
        self.assertNotIn(SWITCH, g.render())

    def test_procedural_default_no_switches(self):
        g = Game.procedural(RandomSource(seed=19), depth=1)
        self.assertFalse(g.switches_enabled)
        self.assertEqual(g.switches, [])
        self.assertFalse(g.light_enabled)

    def test_switch_api_noop_when_disabled(self):
        # 开关未启用 ⇒ toggle/destroy 恒 False、no-op（与 M14/M16 的 light 门同理）
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, switches=False)
        self.assertFalse(g.can_toggle_switch(1, 0))
        self.assertFalse(g.can_destroy_switch(1, 0))
        self.assertFalse(g.toggle_switch(1, 0))
        self.assertFalse(g.destroy_switch(1, 0))
        self.assertEqual(g.switched_lights, set())
        self.assertEqual(g.destroyed_lights, set())


class TestPlacementDeterministic(unittest.TestCase):
    """开关确定性摆位（不变量 #1/#2）：每房间一个、摆墙上、零随机、同 seed 同摆位。"""

    def test_one_switch_per_room_on_wall(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True)
        self.assertEqual(len(g.switches), 1)
        sw = g.switches[0]
        self.assertTrue(g.is_wall(sw.x, sw.y), "开关必须摆在墙格上")
        self.assertEqual((sw.x, sw.y), (1, 0))  # 北沿第一格
        self.assertEqual(sw.room.center, (6, 2))
        self.assertFalse(sw.destroyed)

    def test_two_rooms_two_switches(self):
        rows = [
            "#################",
            "#@........#.....#",
            "#.........#.....#",
            "#.........#.....#",
            "#################",
        ]
        room_a = Room(1, 1, 9, 3)    # center (5,2)
        room_b = Room(11, 1, 7, 3)   # center (14,2)
        g = _make(rows, rooms=[room_a, room_b], switches=True, light=True)
        self.assertEqual(len(g.switches), 2)
        for sw in g.switches:
            self.assertTrue(g.is_wall(sw.x, sw.y))

    def test_placement_deterministic_same_seed(self):
        a = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True, seed=7)
        b = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True, seed=7)
        self.assertEqual([(s.x, s.y) for s in a.switches],
                         [(s.x, s.y) for s in b.switches])

    def test_placement_rng_free(self):
        # 摆位不消耗 RandomSource ⇒ 两次建局后随机序列一致
        a = Game.procedural(RandomSource(seed=19), depth=1, switches=True)
        b = Game.procedural(RandomSource(seed=19), depth=1, switches=True)
        self.assertEqual([a.rng.int(0, 999) for _ in range(5)],
                         [b.rng.int(0, 999) for _ in range(5)])


class TestCanToggleGeometry(unittest.TestCase):
    """can_toggle_switch / can_destroy_switch 的硬约束（纯几何、零随机，不变量 #19）。"""

    def test_valid_switch_in_range_los_true(self):
        g = _make(_OPEN, rooms=[_OPEN_ROOM], switches=True, light=True, fov=True)
        sw = g.switches[0]  # (1,0)
        self.assertTrue(g.can_toggle_switch(sw.x, sw.y))
        self.assertTrue(g.can_destroy_switch(sw.x, sw.y))

    def test_non_switch_coordinate_false(self):
        # (3,2) 是房间中心、不是开关 ⇒ 够不着（开关是独立实体，灯具坐标本身不可作为开关目标）
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True)
        self.assertFalse(g.can_toggle_switch(3, 2))
        self.assertFalse(g.can_destroy_switch(3, 2))

    def test_out_of_range_false(self):
        g = _make(_OPEN, rooms=[_OPEN_ROOM], switches=True, light=True)
        sw = g.switches[0]  # (1,0)
        # 把玩家挪到房间远角 (5,3)，距 (1,0) 切比雪夫 4？不对——(1,0) 到 (5,3) 距 4 ≤ 6 仍够得着。
        # 改用更大房间以制造超距：
        big = [
            "###############",
            "#@............#",
            "#.............#",
            "#.............#",
            "###############",
        ]
        big_room = Room(1, 1, 13, 3)  # 开关仍摆 (1,0)
        g2 = _make(big, rooms=[big_room], switches=True, light=True)
        s = g2.switches[0]
        # 玩家移到 (12,3) 远角：距 (1,0) 切比雪夫 11 > 6
        g2.grid[g2.py][g2.px] = FLOOR
        g2.px, g2.py = 12, 3
        g2.grid[g2.py][g2.px] = "@"
        g2.update_fov()
        self.assertGreater(max(abs(s.x - g2.px), abs(s.y - g2.py)), WEB_LIGHT_RANGE)
        self.assertFalse(g2.can_toggle_switch(s.x, s.y))
        self.assertFalse(g2.can_destroy_switch(s.x, s.y))
        # 顺带确认小房间里的原始开关够得着（对照）
        self.assertTrue(g.can_toggle_switch(sw.x, sw.y))

    def test_wall_blocks_los_false(self):
        # 人工在 (5,1) 注入一个开关，玩家 (1,1) 到它的直线被 (2,1) 的墙挡住 ⇒ 看不见 ⇒ 够不着
        g = _make(_MAZE, rooms=[_MAZE_ROOM], switches=True, light=True)
        g.switches = [LightSwitch(5, 1, Room(0, 0, 1, 1))]
        self.assertFalse(g.can_toggle_switch(5, 1))
        self.assertFalse(g.can_destroy_switch(5, 1))

    def test_light_off_false(self):
        # 光照关闭 ⇒ 即便开关已摆、玩家够得着，toggle/destroy 也恒 False（与 M14/M16 门一致）
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=False)
        sw = g.switches[0]
        self.assertFalse(g.can_toggle_switch(sw.x, sw.y))
        self.assertFalse(g.can_destroy_switch(sw.x, sw.y))

    def test_switches_off_false(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=False, light=True)
        self.assertEqual(g.switches, [])
        self.assertFalse(g.can_toggle_switch(1, 0))
        self.assertFalse(g.can_destroy_switch(1, 0))


class TestToggleSwitchBehavior(unittest.TestCase):
    """toggle_switch 翻转该房间灯（翻 switched_lights[room.center]），声源在灯具处。"""

    def test_toggle_flips_switched_lights_at_fixture(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True, fov=True)
        sw = g.switches[0]  # 控制房间 center=(6,2)
        self.assertTrue(g.can_toggle_switch(sw.x, sw.y))
        before = g.light_level_at(*sw.room.center)
        self.assertEqual(before, LIGHT_LEVEL_LIT)  # 灯亮 ⇒ 明亮
        self.assertTrue(g.toggle_switch(sw.x, sw.y))
        # 翻的是「灯具坐标 room.center」，不是开关格
        self.assertIn(sw.room.center, g.switched_lights)
        after = g.light_level_at(*sw.room.center)
        self.assertLess(after, before)  # 关灯 ⇒ 房间变暗

    def test_toggle_then_back_restores(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True, fov=True)
        sw = g.switches[0]
        g.toggle_switch(sw.x, sw.y)        # 关
        self.assertIn(sw.room.center, g.switched_lights)
        g.toggle_switch(sw.x, sw.y)        # 开
        self.assertNotIn(sw.room.center, g.switched_lights)
        self.assertEqual(g.light_level_at(*sw.room.center), LIGHT_LEVEL_LIT)

    def test_toggle_does_not_consume_random(self):
        a = Game.procedural(RandomSource(seed=19), depth=1, light=True, switches=True)
        b = Game.procedural(RandomSource(seed=19), depth=1, light=True, switches=True)
        target = next((s for s in a.switches if a.can_toggle_switch(s.x, s.y)), None)
        if target is None:
            self.skipTest("seed=19 起始房开关不可达，无法走通 toggle 路径")
        a.toggle_switch(target.x, target.y)
        self.assertEqual([a.rng.int(0, 999) for _ in range(5)],
                         [b.rng.int(0, 999) for _ in range(5)])

    def test_toggle_noise_source_at_fixture(self):
        # 声源在灯具 room.center（6,2），不在开关格 (1,0)、不在玩家 (1,1) ⇒ 调虎离山成立
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True,
                  noise=True, stealth=True)
        sw = g.switches[0]
        m = g.spawn_monster("街头小混混", 6, 2, hp=8, behavior="chase")  # 站在灯具处附近
        self.assertFalse(m.alerted)
        self.assertTrue(g.can_toggle_switch(sw.x, sw.y))
        g.toggle_switch(sw.x, sw.y)
        self.assertEqual(g.last_noise_loudness, NOISE_TOGGLE_LIGHT)
        self.assertTrue(m.alerted)
        self.assertEqual(m.alert_cause, CAUSE_SOUND)
        self.assertEqual(m.last_seen, sw.room.center)  # 声源 = 灯具 (6,2)
        self.assertNotEqual(m.last_seen, (sw.x, sw.y))  # 不是开关格
        self.assertNotEqual(m.last_seen, (g.px, g.py))  # 不是玩家

    def test_failed_toggle_no_noise(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True, noise=True)
        before = g.last_noise_loudness
        g.toggle_switch(3, 2)  # 不是开关 ⇒ False、不发声
        self.assertEqual(g.last_noise_loudness, before)


class TestDestroySwitchBehavior(unittest.TestCase):
    """destroy_switch 永久熄灭该房间灯（destroyed_lights + 开关 destroyed），声源在灯具处。"""

    def test_destroy_flips_destroyed_and_mark(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True, fov=True)
        sw = g.switches[0]
        self.assertTrue(g.destroy_switch(sw.x, sw.y))
        self.assertIn(sw.room.center, g.destroyed_lights)
        self.assertNotIn(sw.room.center, g.switched_lights)
        self.assertTrue(sw.destroyed)
        # 灯具永久熄灭：房间中心不再受任何房间灯光源覆盖，玩家微光也够不到（距玩家 5 > 微光半径）
        # ⇒ 光照等级降到 LIT 以下（此处为全黑 DARK=0）
        self.assertLess(g.light_level_at(*sw.room.center), LIGHT_LEVEL_LIT)

    def test_destroyed_not_toggleable(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True)
        sw = g.switches[0]
        g.destroy_switch(sw.x, sw.y)
        self.assertFalse(g.can_toggle_switch(sw.x, sw.y))
        self.assertFalse(g.toggle_switch(sw.x, sw.y))
        # 二次破坏也不行
        self.assertFalse(g.can_destroy_switch(sw.x, sw.y))
        self.assertFalse(g.destroy_switch(sw.x, sw.y))

    def test_destroy_noise_source_at_fixture(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True,
                  noise=True, stealth=True)
        sw = g.switches[0]
        m = g.spawn_monster("街头小混混", 6, 2, hp=8, behavior="chase")
        self.assertFalse(m.alerted)
        self.assertTrue(g.can_destroy_switch(sw.x, sw.y))
        g.destroy_switch(sw.x, sw.y)
        self.assertEqual(g.last_noise_loudness, NOISE_SHATTER_BULB)
        self.assertTrue(m.alerted)
        self.assertEqual(m.alert_cause, CAUSE_SOUND)
        self.assertEqual(m.last_seen, sw.room.center)  # 声源 = 灯具 (6,2)

    def test_switch_light_is_on_query(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True)
        sw = g.switches[0]
        self.assertTrue(g.switch_light_is_on(sw.x, sw.y))      # 初始灯亮
        g.toggle_switch(sw.x, sw.y)
        self.assertFalse(g.switch_light_is_on(sw.x, sw.y))     # 关灯
        g.destroy_switch(sw.x, sw.y)
        self.assertFalse(g.switch_light_is_on(sw.x, sw.y))     # 碎了也无灯可亮


class TestMultiRoomIndependence(unittest.TestCase):
    """多房间：关/碎一个房间的开关，只影响它自己（不变量 #19 的解耦）。"""

    def test_toggle_one_affects_only_its_room(self):
        rows = [
            "#################",
            "#@........#.....#",
            "#.........#.....#",
            "#.........#.....#",
            "#################",
        ]
        room_a = Room(1, 1, 9, 3)    # center (5,2)
        room_b = Room(11, 1, 7, 3)   # center (14,2)
        g = _make(rows, rooms=[room_a, room_b], switches=True, light=True)
        # 找房间 A 的开关（北沿 (1,0)），玩家在 (1,1) 够得着
        sw_a = next(s for s in g.switches if s.room is room_a)
        self.assertTrue(g.can_toggle_switch(sw_a.x, sw_a.y))
        g.toggle_switch(sw_a.x, sw_a.y)
        self.assertIn(room_a.center, g.switched_lights)
        self.assertNotIn(room_b.center, g.switched_lights)
        self.assertTrue(g.light_is_on(*room_b.center))  # B 灯仍亮

    def test_destroy_one_affects_only_its_room(self):
        rows = [
            "#################",
            "#@........#.....#",
            "#.........#.....#",
            "#.........#.....#",
            "#################",
        ]
        room_a = Room(1, 1, 9, 3)
        room_b = Room(11, 1, 7, 3)
        g = _make(rows, rooms=[room_a, room_b], switches=True, light=True)
        sw_a = next(s for s in g.switches if s.room is room_a)
        g.destroy_switch(sw_a.x, sw_a.y)
        self.assertIn(room_a.center, g.destroyed_lights)
        self.assertNotIn(room_b.center, g.destroyed_lights)
        self.assertFalse(sw_a.destroyed is False)  # sw_a 已碎
        # B 的开关完好、灯仍亮
        sw_b = next(s for s in g.switches if s.room is room_b)
        self.assertFalse(sw_b.destroyed)
        self.assertTrue(g.light_is_on(*room_b.center))


class TestLevelReset(unittest.TestCase):
    """换层重置：descend → load_level 清空 switched_lights / destroyed_lights 并重摆开关。"""

    def test_load_level_clears_and_replaces(self):
        g = Game.procedural(RandomSource(seed=12), depth=1, light=True, switches=True)
        # 破坏一个够得着的开关
        target = next((s for s in g.switches if g.can_destroy_switch(s.x, s.y)), None)
        if target is not None:
            g.destroy_switch(target.x, target.y)
        else:
            # 退而求其次：直接标记状态再下潜
            g.switched_lights.add(g.rooms[0].center)
        self.assertTrue(len(g.switches) > 0 or len(g.destroyed_lights) > 0
                        or len(g.switched_lights) > 0)
        # 把玩家挪到楼梯上下潜
        g.grid[g.py][g.px] = FLOOR
        g.px, g.py = g.stairs
        g.grid[g.py][g.px] = "@"
        g.update_fov()
        self.assertTrue(g.descend())
        self.assertEqual(g.switched_lights, set())       # 新楼层清空关灯状态
        self.assertEqual(g.destroyed_lights, set())      # 新楼层清空碎灯状态
        self.assertTrue(len(g.switches) > 0)             # 新楼层重摆开关
        self.assertTrue(g.switches_enabled)              # 开关启用态保留


class TestRenderGlyph(unittest.TestCase):
    """开关字形 '=' 渲染（已碎退回墙 '#'）；渲染不改 world state（不变量 #8）。"""

    def test_full_render_has_equals(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True, fov=False)
        sw = g.switches[0]
        rendered = g.render()
        self.assertIn(SWITCH, rendered)
        # 精确校验开关格字形（全图渲染不被玩家/怪覆盖时的位置）
        rows = rendered.split("\n")
        self.assertEqual(rows[sw.y][sw.x], SWITCH)

    def test_fog_render_explored_equals(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True, fov=True)
        sw = g.switches[0]
        self.assertIn(SWITCH, g.render())  # 开关在已探索记忆里画 =

    def test_destroyed_switch_renders_as_wall(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], switches=True, light=True, fov=False)
        sw = g.switches[0]
        before = g.render().split("\n")[sw.y][sw.x]
        self.assertEqual(before, SWITCH)
        g.destroy_switch(sw.x, sw.y)
        after = g.render().split("\n")[sw.y][sw.x]
        self.assertEqual(after, WALL)  # 碎了退回墙，开关不再是控制点


class TestRenderPurity(unittest.TestCase):
    """不变量 #8：render() 不改写任何 world state（开关只是加字形）。"""

    def test_render_does_not_touch_world_state(self):
        g = Game.procedural(RandomSource(seed=19), depth=1, fov=True, light=True, switches=True)
        target = next((s for s in g.switches if g.can_toggle_switch(s.x, s.y)), None)
        if target is not None:
            g.toggle_switch(target.x, target.y)
        before = (["".join(r) for r in g.grid],
                  [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                  [(i.key, i.x, i.y) for i in g.items],
                  g.player_hp, g.player_dmg_bonus, g.depth, g.stairs,
                  (g.px, g.py), set(g.visible), dict(g.light_field),
                  set(g.switched_lights), set(g.destroyed_lights),
                  [(s.x, s.y, s.destroyed) for s in g.switches])
        g.render()
        g.render()
        after = (["".join(r) for r in g.grid],
                 [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                 [(i.key, i.x, i.y) for i in g.items],
                 g.player_hp, g.player_dmg_bonus, g.depth, g.stairs,
                 (g.px, g.py), set(g.visible), dict(g.light_field),
                 set(g.switched_lights), set(g.destroyed_lights),
                 [(s.x, s.y, s.destroyed) for s in g.switches])
        self.assertEqual(before, after)

    def test_render_twice_stable(self):
        g = Game.procedural(RandomSource(seed=7), depth=1, fov=True, light=True, switches=True)
        self.assertEqual(g.render(), g.render())


class TestSymmetryWithSwitches(unittest.TestCase):
    """不变量 #9 硬性质在 M19 下仍成立：怪看得见你 ⇒ 你看得见它（开关不动光照几何）。"""

    def test_monster_sees_you_you_can_see(self):
        g = Game.procedural(RandomSource(seed=11), depth=1,
                            fov=True, stealth=True, light=True, switches=True)
        # 关掉 / 碎掉前两个够得着的房间的灯（验证暗处对称仍成立）
        for room in g.rooms[:2]:
            sw = next((s for s in g.switches if s.room is room), None)
            if sw is not None and g.can_toggle_switch(sw.x, sw.y):
                g.toggle_switch(sw.x, sw.y)
        for _ in range(40):
            g.monster_turn()
            g.update_fov()
            for m in g.monsters:
                if m.alive and g.monster_can_see_player(m):
                    self.assertTrue(g.is_visible(m.x, m.y),
                                    f"{m.name}@{m.x},{m.y} 看得见你、你却看不见它（M19 开关下）")

    def test_symmetry_across_seeds_with_switches(self):
        for seed in (3, 7, 11, 19, 23):
            g = Game.procedural(RandomSource(seed=seed), depth=1,
                                fov=True, stealth=True, light=True, switches=True)
            for room in g.rooms[:2]:
                sw = next((s for s in g.switches if s.room is room), None)
                if sw is not None and g.can_toggle_switch(sw.x, sw.y):
                    g.toggle_switch(sw.x, sw.y)
            for _ in range(30):
                g.monster_turn()
                g.update_fov()
                for m in g.monsters:
                    if m.alive and g.monster_can_see_player(m):
                        self.assertTrue(g.is_visible(m.x, m.y),
                                        f"seed={seed} {m.name}@{m.x},{m.y} 幽灵猎手（M19 开关下）")


if __name__ == "__main__":
    unittest.main()
