"""M14 可开关房间灯（蛛网射中灯拉链，翻转该房间的灯）。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（toggle_light 纯状态操作，不引入随机模块、不消耗 rng）
- 不变量 #2 回合确定性（关灯只改光照场 ⇒ 同状态同场；toggle 不改写玩法状态）
- 不变量 #8 渲染纯净性（关灯只改光照场与可见集合，不改 render 字形）
- 不变量 #9 延伸：关灯只移除光源（不新增）⇒ 光照场只变暗或恢复 ⇒ 有效半径恒 ≤ SIGHT_RADIUS(8)
  ⇒「怪看得见你 ⇒ 你看得见它」硬性质不破
- 不变量 #10 延伸：拉链轻响仍只经 emit_noise → Monster.alert(cause=CAUSE_SOUND) 唯一入口生效；
  声源在**灯处**（不在玩家处）⇒ 调虎离山成立
- 不变量 #12 延伸：关灯移除房间灯 ⇒ 房间变暗 ⇒ 怪物感知只缩短不放大（恒 ≤ MONSTER_SIGHT_RADIUS）
- 不变量 #14 延伸：关灯后暗处目标格光照降档 ⇒ 玩家视野半径缩短（恒 ≤ SIGHT_RADIUS）
- 不变量 #15：可开关房间灯纯几何、零随机、默认关闭
  （light=False ⇒ toggle_light 恒返回 False、no-op，与 M1~M13 逐字节一致）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.light import (ROOM_LIGHT_RADIUS, PLAYER_GLOW_RADIUS,
                         LIGHT_LEVEL_DARK, LIGHT_LEVEL_DIM, LIGHT_LEVEL_LIT)
from rogue.fov import SIGHT_RADIUS, MONSTER_SIGHT_RADIUS
from rogue.game import (Game, WEB_LIGHT_RANGE, NOISE_TOGGLE_LIGHT,
                        CAUSE_SOUND)
from rogue.level import Level, Room
from rogue.rng import RandomSource
from rogue.tiles import FLOOR, WALL

# 一间房 + 走廊：玩家在走廊，灯在房间中心
# 房间 (4,1)~(10,3)，中心 (7,2)；玩家在 (1,1) 走廊
_ROOM_CORRIDOR = [
    "############",
    "#@.........#",   # 走廊
    "###.......##",  # 房间上沿（y=2 行 3~9 是房间）
    "###.......##",
    "############",
]
_ROOM_A = Room(3, 2, 7, 2)   # 房间 (3,2)~(9,3)，中心 (6,2)... 用 (3,2,7,2) ⇒ center=(3+3,2+1)=(6,2)
_NO_STAIRS = (-1, -1)


def _make(rows, start=(1, 1), rooms=(), fov=False, stealth=True,
          light=False, flashlight=False, noise=False, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，只测光照与灯开关）。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, _NO_STAIRS, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth, light=light,
                flashlight=flashlight, noise=noise)


def _open_field(width=25, height=9):
    return (["#" * width]
            + ["#" + FLOOR * (width - 2) + "#"] * (height - 2)
            + ["#" * width])


# 房间 (1,1)~(10,3)，中心 (5,2)；玩家在 (1,1) 房间内
_ROOM_INNER = [
    "###########",
    "#@........#",
    "#.........#",
    "#.........#",
    "###########",
]
_ROOM_INNER_ROOM = Room(1, 1, 10, 3)  # center = (1+5, 1+1) = (6,2)


class TestToggleLightDefault(unittest.TestCase):
    """M14 默认关闭：light=False ⇒ toggle_light 恒返回 False、no-op（不变量 #15）。"""

    def test_light_off_toggle_returns_false(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=False)
        cx, cy = _ROOM_INNER_ROOM.center
        self.assertFalse(g.toggle_light(cx, cy))

    def test_light_off_no_state_change(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=False, fov=True)
        cx, cy = _ROOM_INNER_ROOM.center
        vis_before = set(g.visible)
        explored_before = set(g.explored)
        g.toggle_light(cx, cy)
        self.assertEqual(g.switched_lights, set())
        self.assertEqual(g.visible, vis_before)
        self.assertEqual(g.explored, explored_before)

    def test_light_off_can_toggle_returns_false(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=False)
        cx, cy = _ROOM_INNER_ROOM.center
        self.assertFalse(g.can_toggle_light(cx, cy))

    def test_procedural_default_has_no_switched_lights(self):
        g = Game.procedural(RandomSource(seed=19), depth=1)
        self.assertEqual(g.switched_lights, set())
        self.assertFalse(g.light_enabled)


class TestToggleLightGeometry(unittest.TestCase):
    """can_toggle_light 的四条硬约束（纯几何、零随机，不变量 #15）。"""

    def test_valid_room_center_in_range(self):
        # 玩家在 (1,1)，房间中心 (6,2)，切比雪夫距离 5 ≤ WEB_LIGHT_RANGE(6) ⇒ 可关
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, fov=True)
        cx, cy = _ROOM_INNER_ROOM.center
        self.assertTrue(g.can_toggle_light(cx, cy))

    def test_non_room_center_target(self):
        # (3,2) 不是房间中心（中心是 (6,2)）⇒ 够不着
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True)
        self.assertFalse(g.can_toggle_light(3, 2))

    def test_out_of_range(self):
        # 玩家在 (1,1)，造一个远房间（中心距离 > 6）
        rows = [
            "#################",
            "#@..............#",
            "#################",
            "#...............#",
            "#################",
        ]
        far_room = Room(1, 3, 15, 1)  # center = (8,3)，距 (1,1) 切比雪夫 7 > 6
        g = _make(rows, rooms=[far_room], light=True)
        self.assertFalse(g.can_toggle_light(8, 3))

    def test_at_range_boundary(self):
        # 切比雪夫距离恰好 = WEB_LIGHT_RANGE(6) ⇒ 可关（闭区间）
        rows = [
            "#################",
            "#@..............#",
            "#################",
        ]
        # 玩家 (1,1)，房间中心 (7,1)，距离 6 = WEB_LIGHT_RANGE ⇒ 可关
        room = Room(1, 1, 15, 1)  # center = (8,1)... 调整成 center=(7,1): Room(0,1,15,1) center=(7,1)
        room = Room(0, 1, 15, 1)  # center = (0+7, 1+0) = (7,1)，距 (1,1) = 6
        g = _make(rows, rooms=[room], light=True)
        self.assertEqual(room.center, (7, 1))
        self.assertTrue(g.can_toggle_light(7, 1))

    def test_wall_blocks_line_of_sight(self):
        # 玩家与灯之间隔一堵墙 ⇒ 看不见灯 ⇒ 够不着
        rows = [
            "###########",
            "#@##......#",   # (1,1) 玩家，(4..9,1) 房间，中间 (2,1)(3,1) 是墙
            "###########",
        ]
        room = Room(4, 1, 6, 1)  # center = (4+3, 1+0) = (7,1)
        g = _make(rows, rooms=[room], light=True)
        # 距离 6（在射程内），但中间有墙挡视线
        self.assertFalse(g.can_toggle_light(7, 1))

    def test_standing_under_light_can_toggle(self):
        # 玩家站在灯正下方（距离 0）⇒ 伸手就能够到拉链
        g = _make(_ROOM_INNER, start=(6, 2), rooms=[_ROOM_INNER_ROOM], light=True)
        # 把玩家挪到房间中心
        g.grid[g.py][g.px] = FLOOR
        g.px, g.py = _ROOM_INNER_ROOM.center
        g.grid[g.py][g.px] = "@"
        g.update_fov()
        cx, cy = _ROOM_INNER_ROOM.center
        self.assertTrue(g.can_toggle_light(cx, cy))


class TestToggleLightField(unittest.TestCase):
    """关灯后光照场变化（M11 联动：房间变暗；M13 联动：玩家视野缩短）。"""

    def test_off_darkens_room(self):
        # 房间亮着时中心 LIT；关灯后变暗（DARK 或 DIM，取决于微光是否够到）
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, fov=True)
        cx, cy = _ROOM_INNER_ROOM.center
        before = g.light_level_at(cx, cy)
        self.assertEqual(before, LIGHT_LEVEL_LIT)  # 房间灯覆盖 ⇒ 明亮
        self.assertTrue(g.toggle_light(cx, cy))
        after = g.light_level_at(cx, cy)
        # 关灯后房间灯没了，只剩玩家微光：中心 (6,2) 距玩家 (1,1) 切比雪夫 5 > PLAYER_GLOW_RADIUS(4) ⇒ DARK
        self.assertLess(after, before)

    def test_off_removes_source_from_list(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True)
        cx, cy = _ROOM_INNER_ROOM.center
        srcs_before = g._light_sources()
        self.assertIn((cx, cy, ROOM_LIGHT_RADIUS), srcs_before)
        g.toggle_light(cx, cy)
        srcs_after = g._light_sources()
        self.assertNotIn((cx, cy, ROOM_LIGHT_RADIUS), srcs_after)

    def test_on_restores_source(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True)
        cx, cy = _ROOM_INNER_ROOM.center
        g.toggle_light(cx, cy)  # 关
        g.toggle_light(cx, cy)  # 开
        self.assertIn((cx, cy, ROOM_LIGHT_RADIUS), g._light_sources())

    def test_toggle_roundtrip_restores_field(self):
        # 关→开 ⇒ 光照场恢复原状
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, fov=True)
        cx, cy = _ROOM_INNER_ROOM.center
        field_before = dict(g.light_field)
        g.toggle_light(cx, cy)  # 关
        g.toggle_light(cx, cy)  # 开
        self.assertEqual(g.light_field, field_before)

    def test_other_rooms_unaffected(self):
        # 两个房间，关一个不影响另一个
        rows = [
            "###################",
            "#@........#.......#",
            "###########.......#",
            "###################",
        ]
        room_a = Room(1, 1, 8, 1)    # center = (4,1)... Room(1,1,8,1) center=(1+4,1+0)=(5,1)
        room_b = Room(10, 1, 7, 2)  # center = (10+3, 1+1) = (13,2)
        # 重新构造让中心对齐
        room_a = Room(1, 1, 9, 1)    # center = (5,1)
        room_b = Room(11, 1, 7, 2)   # center = (14,2)
        g = _make(rows, rooms=[room_a, room_b], light=True)
        ca = room_a.center
        cb = room_b.center
        b_before = g.light_level_at(*cb)
        g.toggle_light(*ca)  # 关 A
        b_after = g.light_level_at(*cb)
        self.assertEqual(b_before, b_after)

    def test_off_shortens_monster_sight(self):
        # 关灯后房间变暗 ⇒ 怪物感知半径缩短（M11 联动）
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, stealth=True)
        cx, cy = _ROOM_INNER_ROOM.center
        # 在房间中心放一只怪
        m = g.spawn_monster("街头小混混", cx, cy, hp=8, behavior="chase")
        # 灯亮时：怪物所在格 LIT ⇒ 感知半径 7
        from rogue.light import monster_sight_radius
        self.assertEqual(monster_sight_radius(g.light_level_at(cx, cy)), MONSTER_SIGHT_RADIUS)
        g.toggle_light(cx, cy)  # 关灯
        # 灯灭后：怪物所在格变暗 ⇒ 感知半径缩短
        self.assertLess(monster_sight_radius(g.light_level_at(cx, cy)),
                        MONSTER_SIGHT_RADIUS)

    def test_off_shortens_player_sight_into_room(self):
        # 关灯后房间格子变暗（M13 联动：暗处目标格视野半径缩短）
        # 检查光照场直接变化（不依赖可见集合，避开 M6 进房间点亮整间规则）
        g = Game.procedural(RandomSource(seed=19), depth=1, light=True, fov=True)
        for room in g.rooms:
            cx, cy = room.center
            if not g.can_toggle_light(cx, cy):
                continue
            # 灯亮时房间中心 LIT（房间灯覆盖）
            self.assertEqual(g.light_level_at(cx, cy), LIGHT_LEVEL_LIT)
            g.toggle_light(cx, cy)  # 关灯
            # 灯灭后房间中心变暗（只剩玩家微光，距离远 ⇒ DARK/DIM）
            self.assertLess(g.light_level_at(cx, cy), LIGHT_LEVEL_LIT)
            return
        self.fail("没找到可关灯的房间")


class TestToggleLightDeterminism(unittest.TestCase):
    """不变量 #2：同 seed + 同输入 ⇒ 同光照场；关灯不消耗 RandomSource（#15）。"""

    def test_toggle_does_not_consume_random(self):
        # 关灯是纯状态操作 ⇒ 不消耗 rng
        a = Game.procedural(RandomSource(seed=19), depth=1, light=True)
        b = Game.procedural(RandomSource(seed=19), depth=1, light=True)
        # 找第一个房间的中心
        cx, cy = a.rooms[0].center
        a.toggle_light(cx, cy)  # 关灯
        # 两者后续的随机序列必须一致（关灯没消耗 rng）
        self.assertEqual([a.rng.int(0, 999) for _ in range(5)],
                         [b.rng.int(0, 999) for _ in range(5)])

    def test_same_seed_same_field_after_toggle(self):
        def field_after_toggle(seed):
            g = Game.procedural(RandomSource(seed=seed), depth=1, light=True, fov=True)
            cx, cy = g.rooms[0].center
            g.toggle_light(cx, cy)
            return dict(g.light_field)

        self.assertEqual(field_after_toggle(19), field_after_toggle(19))

    def test_toggle_idempotent_field(self):
        # 关灯后光照场稳定：再算几次结果一样
        g = Game.procedural(RandomSource(seed=7), depth=1, light=True)
        cx, cy = g.rooms[0].center
        g.toggle_light(cx, cy)
        f1 = dict(g.light_field)
        g.update_fov()
        g.update_fov()
        self.assertEqual(g.light_field, f1)

    def test_toggle_back_and_forth_deterministic(self):
        # 翻转奇数次 = 关、偶数次 = 开，状态确定
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True)
        cx, cy = _ROOM_INNER_ROOM.center
        for _ in range(3):  # 奇数次 ⇒ 关
            g.toggle_light(cx, cy)
        self.assertIn((cx, cy), g.switched_lights)
        for _ in range(3):  # 总共 6 次（偶数）⇒ 开
            g.toggle_light(cx, cy)
        self.assertNotIn((cx, cy), g.switched_lights)


class TestToggleLightNoise(unittest.TestCase):
    """M8 联动：关灯发出 NOISE_TOGGLE_LIGHT 响动，声源在灯处（不在玩家处）。"""

    def test_noise_emitted_when_noise_on(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, noise=True)
        cx, cy = _ROOM_INNER_ROOM.center
        before_loudness = g.last_noise_loudness
        g.toggle_light(cx, cy)
        self.assertEqual(g.last_noise_loudness, NOISE_TOGGLE_LIGHT)

    def test_no_noise_when_noise_off(self):
        # 听觉关闭 ⇒ emit_noise 是空操作 ⇒ last_noise_loudness 不变
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, noise=False)
        cx, cy = _ROOM_INNER_ROOM.center
        before = g.last_noise_loudness
        g.toggle_light(cx, cy)
        self.assertEqual(g.last_noise_loudness, before)

    def test_source_at_light_not_player(self):
        # 声源在灯处 ⇒ 被惊动的怪扑向灯、不是扑向玩家
        # 用 _ROOM_INNER（玩家在房间内，LOS 到中心清晰）
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, noise=True, stealth=True)
        cx, cy = _ROOM_INNER_ROOM.center  # (6, 2)
        # 在房间远端放一只怪（距灯近、距玩家远）
        m = g.spawn_monster("街头小混混", 8, 2, hp=8, behavior="chase")
        self.assertFalse(m.alerted)  # 潜行模式、还没被发现
        # 玩家在 (1,1)，距灯 (6,2) 切比雪夫 5 ≤ WEB_LIGHT_RANGE(6)，LOS 清晰
        self.assertTrue(g.can_toggle_light(cx, cy))
        g.toggle_light(cx, cy)  # 关灯 + 发声
        # 怪被声惊动 ⇒ 扑向声源（灯处 6,2），不是玩家 (1,1)
        self.assertTrue(m.alerted)
        self.assertEqual(m.alert_cause, CAUSE_SOUND)
        self.assertEqual(m.last_seen, (cx, cy))  # 声源 = 灯位置 (6,2)，不是玩家 (1,1)

    def test_failed_toggle_no_noise(self):
        # 够不着（非房间中心）⇒ toggle 返回 False、不发声
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, noise=True)
        before = g.last_noise_loudness
        g.toggle_light(3, 2)  # 不是房间中心
        self.assertEqual(g.last_noise_loudness, before)


class TestToggleLightRenderPurity(unittest.TestCase):
    """不变量 #8：关灯只改光照场与可见集合，不改 render 字形。"""

    def test_fov_off_render_identical(self):
        # fov=False ⇒ 全图渲染，关灯不改字形（只改 colorize 上色层的明暗）
        a = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, fov=False)
        b = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, fov=False)
        cx, cy = _ROOM_INNER_ROOM.center
        a.toggle_light(cx, cy)  # a 关灯、b 不关
        self.assertEqual(a.render(), b.render())

    def test_fov_on_uses_original_glyphs(self):
        # fov=True + light=True ⇒ 迷雾渲染，可见格子仍用原字形（不引入新字形）
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True, fov=True)
        cx, cy = _ROOM_INNER_ROOM.center
        g.toggle_light(cx, cy)
        rendered = g.render()
        chars = set(rendered.replace("\n", ""))
        from rogue.tiles import PLAYER, UNSEEN
        self.assertTrue(chars.issubset({WALL, FLOOR, PLAYER, UNSEEN}))

    def test_render_does_not_touch_world_state(self):
        # toggle_light 后 render() 不改写任何状态（#8：world state 前后快照比对）
        g = Game.procedural(RandomSource(seed=19), depth=1, fov=True, light=True)
        cx, cy = g.rooms[0].center
        g.toggle_light(cx, cy)  # 关灯
        before = (["".join(r) for r in g.grid],
                  [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                  [(i.key, i.x, i.y) for i in g.items],
                  g.player_hp, g.player_dmg_bonus, g.depth, g.stairs,
                  (g.px, g.py), set(g.visible), dict(g.light_field),
                  set(g.switched_lights))
        g.render()
        g.render()
        after = (["".join(r) for r in g.grid],
                 [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                 [(i.key, i.x, i.y) for i in g.items],
                 g.player_hp, g.player_dmg_bonus, g.depth, g.stairs,
                 (g.px, g.py), set(g.visible), dict(g.light_field),
                 set(g.switched_lights))
        self.assertEqual(before, after)

    def test_render_twice_stable(self):
        g = Game.procedural(RandomSource(seed=7), depth=1, fov=True, light=True)
        cx, cy = g.rooms[0].center
        g.toggle_light(cx, cy)
        self.assertEqual(g.render(), g.render())


class TestToggleLightReset(unittest.TestCase):
    """换层重置：descend → load_level 清空 switched_lights（新楼层 = 新灯）。"""

    def test_load_level_clears_switched_lights(self):
        g = Game.procedural(RandomSource(seed=12), depth=1, light=True)
        cx, cy = g.rooms[0].center
        g.toggle_light(cx, cy)
        self.assertEqual(len(g.switched_lights), 1)
        # 把玩家挪到楼梯上下潜
        g.grid[g.py][g.px] = FLOOR
        g.px, g.py = g.stairs
        g.grid[g.py][g.px] = "@"
        g.update_fov()
        self.assertTrue(g.descend())
        self.assertEqual(g.switched_lights, set())  # 新楼层清空

    def test_procedural_starts_empty(self):
        for seed in (1, 7, 19, 23):
            g = Game.procedural(RandomSource(seed=seed), depth=1, light=True)
            self.assertEqual(g.switched_lights, set())


class TestToggleLightSymmetry(unittest.TestCase):
    """不变量 #9 硬性质在 M14 下仍成立：怪看得见你 ⇒ 你看得见它。"""

    def test_monster_sees_you_you_can_see_after_toggle(self):
        # 程序化楼层 + 光照 + 视野 + 潜行：关灯后跑若干回合，
        # 任何「看得见玩家的怪」都必须在玩家的可见集合内
        g = Game.procedural(RandomSource(seed=11), depth=1,
                            fov=True, stealth=True, light=True)
        # 先关掉第一个房间的灯
        if g.rooms:
            cx, cy = g.rooms[0].center
            if g.can_toggle_light(cx, cy):
                g.toggle_light(cx, cy)
        for _ in range(40):
            g.monster_turn()
            g.update_fov()
            for m in g.monsters:
                if m.alive and g.monster_can_see_player(m):
                    self.assertTrue(g.is_visible(m.x, m.y),
                                    f"{m.name}@{m.x},{m.y} 看得见你、你却看不见它（关灯后）")

    def test_symmetry_across_seeds_with_toggle(self):
        for seed in (3, 7, 11, 19, 23):
            g = Game.procedural(RandomSource(seed=seed), depth=1,
                                fov=True, stealth=True, light=True)
            # 关掉前两个房间的灯（够得着的）
            for room in g.rooms[:2]:
                cx, cy = room.center
                if g.can_toggle_light(cx, cy):
                    g.toggle_light(cx, cy)
            for _ in range(30):
                g.monster_turn()
                g.update_fov()
                for m in g.monsters:
                    if m.alive and g.monster_can_see_player(m):
                        self.assertTrue(g.is_visible(m.x, m.y),
                                        f"seed={seed} {m.name}@{m.x},{m.y} 幽灵猎手（关灯后）")

    def test_toggle_only_shortens_never_amplifies(self):
        # 关灯只移除光源 ⇒ 光照场只变暗（等级只降不升）⇒ 有效半径只缩不放
        g = Game.procedural(RandomSource(seed=19), depth=1, light=True, fov=True)
        for room in g.rooms:
            cx, cy = room.center
            if g.can_toggle_light(cx, cy):
                lit_before = sum(1 for v in g.light_field.values() if v == LIGHT_LEVEL_LIT)
                g.toggle_light(cx, cy)  # 关灯
                lit_after = sum(1 for v in g.light_field.values() if v == LIGHT_LEVEL_LIT)
                self.assertLessEqual(lit_after, lit_before,
                                    "关灯后明亮格数不应增加")


class TestToggleLightIdempotent(unittest.TestCase):
    """update_fov 幂等：关灯后同状态算几次结果一样。"""

    def test_update_fov_idempotent_after_toggle(self):
        g = Game.procedural(RandomSource(seed=19), depth=1, light=True, fov=True)
        cx, cy = g.rooms[0].center
        if g.can_toggle_light(cx, cy):
            g.toggle_light(cx, cy)
        first = set(g.visible)
        g.update_fov()
        g.update_fov()
        self.assertEqual(first, g.visible)

    def test_light_field_stable_after_toggle(self):
        g = Game.procedural(RandomSource(seed=19), depth=1, light=True)
        cx, cy = g.rooms[0].center
        if g.can_toggle_light(cx, cy):
            g.toggle_light(cx, cy)
        f1 = dict(g.light_field)
        g.update_light()
        self.assertEqual(g.light_field, f1)


class TestToggleLightQuery(unittest.TestCase):
    """light_is_on 查询接口（纯查询、不改状态）。"""

    def test_light_on_by_default(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True)
        cx, cy = _ROOM_INNER_ROOM.center
        self.assertTrue(g.light_is_on(cx, cy))

    def test_light_off_after_toggle(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True)
        cx, cy = _ROOM_INNER_ROOM.center
        g.toggle_light(cx, cy)
        self.assertFalse(g.light_is_on(cx, cy))

    def test_light_on_after_toggle_back(self):
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True)
        cx, cy = _ROOM_INNER_ROOM.center
        g.toggle_light(cx, cy)  # 关
        g.toggle_light(cx, cy)  # 开
        self.assertTrue(g.light_is_on(cx, cy))

    def test_non_room_center_always_on(self):
        # 非房间中心恒返回 True（无灯可关）
        g = _make(_ROOM_INNER, rooms=[_ROOM_INNER_ROOM], light=True)
        self.assertTrue(g.light_is_on(3, 2))


class TestToggleLightMultipleRooms(unittest.TestCase):
    """多房间场景：逐个关灯、各不影响。"""

    def test_toggle_two_rooms_independently(self):
        # 程序化楼层里关两个房间的灯，各不影响
        g = Game.procedural(RandomSource(seed=19), depth=1, light=True)
        toggleable = [r.center for r in g.rooms if g.can_toggle_light(*r.center)]
        if len(toggleable) < 2:
            self.skipTest("本 seed 没有两个可关灯的房间")
        ca, cb = toggleable[0], toggleable[1]
        # 关 A
        g.toggle_light(*ca)
        self.assertIn(ca, g.switched_lights)
        self.assertNotIn(cb, g.switched_lights)
        self.assertTrue(g.light_is_on(*cb))  # B 的灯仍亮
        # 关 B
        g.toggle_light(*cb)
        self.assertIn(cb, g.switched_lights)
        # 两个都在 switched_lights 里
        self.assertEqual(len(g.switched_lights), 2)

    def test_all_rooms_toggleable_in_procedural(self):
        # 程序化楼层里至少有一个房间能关灯（玩家在起始房，距离够近）
        g = Game.procedural(RandomSource(seed=19), depth=1, light=True)
        toggleable = [r for r in g.rooms if g.can_toggle_light(*r.center)]
        self.assertGreater(len(toggleable), 0,
                           "程序化楼层里至少该有一个房间的灯能关")


if __name__ == "__main__":
    unittest.main()
