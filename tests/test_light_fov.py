"""M13 光照影响玩家自身视野规格。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（视野纯几何、不引入随机模块）
- 不变量 #2 回合确定性（视野只依赖 grid + 玩家位置 + rooms + 光照场 ⇒ 同状态同可见集合）
- 不变量 #8 渲染纯净性（光照影响可见集合，不改 render 字形；fov=False 时一字不差）
- 不变量 #9 延伸：按目标格光照算玩家视野半径，同档位下 player_r ≥ monster_r
  （DARK 2=2 / DIM 4=4 / LIT 8>7）⇒「怪看得见你 ⇒ 你看得见它」硬性质不破
- 不变量 #14：光照影响玩家视野是纯几何、零随机、默认关闭
  （light=False 或 fov=False ⇒ 走 M6 原逻辑，与 M1~M12 逐字节一致）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.fov import (SIGHT_RADIUS, PLAYER_SIGHT_DARK, PLAYER_SIGHT_DIM,
                       player_sight_radius, visible_tiles)
from rogue.light import (LIGHT_LEVEL_DARK, LIGHT_LEVEL_DIM, LIGHT_LEVEL_LIT,
                         PLAYER_GLOW_RADIUS, FLASHLIGHT_RADIUS)
from rogue.game import Game
from rogue.level import Level, Room
from rogue.rng import RandomSource
from rogue.tiles import FLOOR, UNSEEN

# 长走廊（无房间）：只有玩家随身光源，便于验证「暗处视野短」
_LONG = [
    "############",
    "#@..........#",
    "############",
]
# 一字房间：整间都在房间光源半径内 ⇒ 明亮
_ROOM = [
    "############",
    "#@.........#",
    "############",
]
_NO_STAIRS = (-1, -1)


def _make(rows, start=(1, 1), rooms=(), fov=False, stealth=True,
          light=False, flashlight=False, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，只测光照与视野）。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, _NO_STAIRS, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth, light=light, flashlight=flashlight)


def _open_field(width=25, height=9):
    return (["#" * width]
            + ["#" + FLOOR * (width - 2) + "#"] * (height - 2)
            + ["#" * width])


class TestPlayerSightRadius(unittest.TestCase):
    """player_sight_radius 档位（纯函数，只缩短不放大，不变量 #9/#14）。"""

    def test_buckets_match_monster_symmetry(self):
        # 与 monster_sight_radius 对称：DARK 2 / DIM 4 / LIT 8
        self.assertEqual(player_sight_radius(LIGHT_LEVEL_DARK), PLAYER_SIGHT_DARK)
        self.assertEqual(player_sight_radius(LIGHT_LEVEL_DIM), PLAYER_SIGHT_DIM)
        self.assertEqual(player_sight_radius(LIGHT_LEVEL_LIT), SIGHT_RADIUS)

    def test_never_exceeds_base(self):
        # 任何光照等级都不会让玩家看得比「明亮」更远 ⇒ 只缩短不放大
        for lvl in (LIGHT_LEVEL_DARK, LIGHT_LEVEL_DIM, LIGHT_LEVEL_LIT):
            self.assertLessEqual(player_sight_radius(lvl), SIGHT_RADIUS)
        # 自定义更小 base 也钳制
        self.assertLessEqual(player_sight_radius(LIGHT_LEVEL_LIT, base=5), 5)

    def test_player_ge_monster_same_level(self):
        # #9 硬性质的数学前提：同光照等级下 player_r ≥ monster_r
        from rogue.light import monster_sight_radius, MONSTER_SIGHT_DARK, MONSTER_SIGHT_DIM
        from rogue.fov import MONSTER_SIGHT_RADIUS
        self.assertGreaterEqual(player_sight_radius(LIGHT_LEVEL_DARK),
                                monster_sight_radius(LIGHT_LEVEL_DARK))
        self.assertGreaterEqual(player_sight_radius(LIGHT_LEVEL_DIM),
                                monster_sight_radius(LIGHT_LEVEL_DIM))
        self.assertGreaterEqual(player_sight_radius(LIGHT_LEVEL_LIT),
                                monster_sight_radius(LIGHT_LEVEL_LIT))


class TestVisibleTilesLightField(unittest.TestCase):
    """visible_tiles 的 light_field 参数（纯几何、零随机）。"""

    def test_none_light_field_uses_fixed_radius(self):
        # light_field=None ⇒ M6 原逻辑（固定半径 8）
        grid = [list(r) for r in _open_field(width=21)]
        origin = (10, 4)
        vis = visible_tiles(grid, origin, SIGHT_RADIUS, rooms=[], light_field=None)
        self.assertIn((18, 4), vis)   # 距离 8（半径内）
        self.assertNotIn((19, 4), vis)  # 距离 9（超出）

    def test_lit_target_full_radius(self):
        # 目标格 LIT ⇒ 有效半径 8
        grid = [list(r) for r in _open_field(width=21)]
        origin = (10, 4)
        lf = {(x, 4): LIGHT_LEVEL_LIT for x in range(21)}
        vis = visible_tiles(grid, origin, SIGHT_RADIUS, rooms=[], light_field=lf)
        self.assertIn((18, 4), vis)   # 距离 8、LIT ⇒ 可见
        self.assertNotIn((19, 4), vis)  # 距离 9 > 8 ⇒ 不可见

    def test_dark_target_short_radius(self):
        # 目标格 DARK ⇒ 有效半径 2
        grid = [list(r) for r in _open_field(width=21)]
        origin = (10, 4)
        lf = {(x, 4): LIGHT_LEVEL_DARK for x in range(21)}
        vis = visible_tiles(grid, origin, SIGHT_RADIUS, rooms=[], light_field=lf)
        self.assertIn((12, 4), vis)   # 距离 2、DARK ⇒ 可见
        self.assertNotIn((13, 4), vis)  # 距离 3 > 2 ⇒ 不可见

    def test_dim_target_medium_radius(self):
        # 目标格 DIM ⇒ 有效半径 4
        grid = [list(r) for r in _open_field(width=21)]
        origin = (10, 4)
        lf = {(x, 4): LIGHT_LEVEL_DIM for x in range(21)}
        vis = visible_tiles(grid, origin, SIGHT_RADIUS, rooms=[], light_field=lf)
        self.assertIn((14, 4), vis)   # 距离 4、DIM ⇒ 可见
        self.assertNotIn((15, 4), vis)  # 距离 5 > 4 ⇒ 不可见

    def test_mixed_light_field_sees_lit_far_dark_near(self):
        # 混合场：亮处远可见、暗处近才可见
        grid = [list(r) for r in _open_field(width=21)]
        origin = (10, 4)
        # 左半暗、右半亮
        lf = {(x, 4): LIGHT_LEVEL_DARK if x < 10 else LIGHT_LEVEL_LIT
              for x in range(21)}
        vis = visible_tiles(grid, origin, SIGHT_RADIUS, rooms=[], light_field=lf)
        self.assertIn((18, 4), vis)    # 右侧距离 8、LIT ⇒ 可见
        self.assertNotIn((7, 4), vis)  # 左侧距离 3、DARK > 2 ⇒ 不可见
        self.assertIn((8, 4), vis)     # 左侧距离 2、DARK ⇒ 可见

    def test_origin_always_visible_with_light_field(self):
        grid = [list(r) for r in _open_field(width=9)]
        lf = {(x, y): LIGHT_LEVEL_DARK for x in range(9) for y in range(9)}
        vis = visible_tiles(grid, (4, 4), SIGHT_RADIUS, rooms=[], light_field=lf)
        self.assertIn((4, 4), vis)  # 脚下恒可见

    def test_wall_still_blocks_with_light_field(self):
        # 光照开启后墙仍挡视线（#4 / #8 不破）
        grid = [list(r) for r in [
            "#######",
            "#@#...#",
            "#######",
        ]]
        lf = {(x, y): LIGHT_LEVEL_LIT for x in range(7) for y in range(3)}
        vis = visible_tiles(grid, (1, 1), SIGHT_RADIUS, rooms=[], light_field=lf)
        self.assertTrue(vis.isdisjoint({(3, 1), (4, 1), (5, 1)}))  # 墙后看不见


class TestDarkCorridorShortSight(unittest.TestCase):
    """关键场景：暗走廊里玩家视野短（M13 核心收益）。"""

    def test_corridor_sees_only_glow_area(self):
        # 长走廊、无房间、light=True：玩家微光照亮脚下 4 格，
        # 按目标格光照算：LIT 区(距离≤2) 半径 8、DIM 区(距离 3~4) 半径 4、
        # DARK 区(距离≥5) 半径 2 ⇒ 只能看清距离 4 以内
        g = _make(_LONG, light=True, fov=True)
        vis = g.visible
        self.assertIn((1, 1), vis)   # 脚下
        self.assertIn((2, 1), vis)   # 距离 1、LIT
        self.assertIn((3, 1), vis)   # 距离 2、LIT
        self.assertIn((4, 1), vis)   # 距离 3、DIM（半径 4）
        self.assertNotIn((5, 1), vis)  # 距离 4、DARK（半径 2 < 4）⇒ 看不见
        self.assertNotIn((8, 1), vis)  # 远处全黑

    def test_corridor_far_shorter_than_m6(self):
        # M13 开启后走廊视野 < M6 原逻辑（半径 8）
        on = _make(_LONG, light=True, fov=True)
        off = _make(_LONG, light=False, fov=True)
        self.assertLess(len(on.visible), len(off.visible))

    def test_corridor_dark_target_invisible_beyond_two(self):
        # DARK 格（距离 ≥ 5）在 M13 下看不见，在 M6 下看得见
        g_on = _make(_LONG, light=True, fov=True)
        g_off = _make(_LONG, light=False, fov=True)
        for x in (6, 7, 8):
            self.assertNotIn((x, 1), g_on.visible)
            self.assertIn((x, 1), g_off.visible)


class TestLitRoomLongSight(unittest.TestCase):
    """关键场景：亮房间里玩家视野长（房间灯覆盖 ⇒ LIT ⇒ 半径 8）。"""

    def test_room_lights_up_full(self):
        # 房间内格子 LIT（房间灯半径 9 覆盖）⇒ 半径 8 ⇒ 8 格内可见
        room = Room(1, 1, 10, 1)
        g = _make(_ROOM, start=(1, 1), rooms=[room], light=True, fov=True)
        for x in range(1, 10):  # 距离 0~8
            self.assertIn((x, 1), g.visible, f"房间内 {x},1 该可见")

    def test_room_corner_visible_by_room_lighting(self):
        # 房角 (10,1) 距离 9 > 8，但「进房间点亮整间」规则覆盖 ⇒ 可见
        room = Room(1, 1, 10, 1)
        g = _make(_ROOM, start=(1, 1), rooms=[room], light=True, fov=True)
        self.assertIn((10, 1), g.visible)

    def test_room_same_as_m6_when_lit(self):
        # 亮房间里 M13 与 M6 的可见集合一致（房间灯让所有格子 LIT ⇒ 半径 8 = M6）
        room = Room(1, 1, 10, 1)
        on = _make(_ROOM, start=(1, 1), rooms=[room], light=True, fov=True)
        off = _make(_ROOM, start=(1, 1), rooms=[room], light=False, fov=True)
        self.assertEqual(on.visible, off.visible)


class TestFlashlightExtendsSight(unittest.TestCase):
    """手电照亮暗处后玩家视野恢复（M12 手电 + M13 视野联动）。"""

    def test_flashlight_extends_corridor_sight(self):
        # 走廊里手电开 ⇒ 手电半径 6 照亮更远 ⇒ 比手电关多看见格子
        on = _make(_LONG, light=True, fov=True, flashlight=True)
        off = _make(_LONG, light=True, fov=True, flashlight=False)
        self.assertGreater(len(on.visible), len(off.visible))

    def test_flashlight_reaches_distance_5(self):
        # 手电半径 6：距离 5 处贡献 1 ⇒ DIM ⇒ 半径 4，但距离 5 > 4 ⇒ 不可见
        # 距离 4 处贡献 2 ⇒ DIM ⇒ 半径 4，距离 4 ≤ 4 ⇒ 可见
        g = _make(_LONG, light=True, fov=True, flashlight=True)
        self.assertIn((5, 1), g.visible)   # 距离 4、DIM ⇒ 可见
        self.assertNotIn((6, 1), g.visible)  # 距离 5、DIM 但 5 > 4 ⇒ 不可见


class TestLightFovSwitch(unittest.TestCase):
    """M13 只在「光照且视野都开启」时生效。"""

    def test_light_off_fov_on_uses_m6_logic(self):
        # light=False、fov=True ⇒ 走 M6 原逻辑（固定半径 8）
        g = _make(_LONG, light=False, fov=True)
        self.assertIn((8, 1), g.visible)  # 距离 7 ≤ 8 ⇒ 可见（M6 原逻辑）

    def test_light_on_fov_off_uses_m6_logic(self):
        # light=True、fov=False ⇒ visible 仍走 M6 原逻辑（全图渲染不用 visible）
        g = _make(_LONG, light=True, fov=False)
        # fov=False 时 visible 仍按固定半径算（M13 条件是 light and fov）
        self.assertIn((8, 1), g.visible)

    def test_default_uses_m6_logic(self):
        # 默认（light=False、fov=False）⇒ M6 原逻辑
        g = _make(_LONG)
        self.assertIn((8, 1), g.visible)

    def test_procedural_default_unaffected(self):
        # 程序化楼层默认（无参数）⇒ 与 M12 逐字节一致
        g = Game.procedural(RandomSource(seed=19), depth=1)
        self.assertFalse(g.light_enabled)
        self.assertFalse(g.fov_enabled)


class TestLightFovSymmetry(unittest.TestCase):
    """不变量 #9 硬性质在 M13 下仍成立：怪看得见你 ⇒ 你看得见它。"""

    def test_monster_sees_you_you_can_see(self):
        # 程序化楼层 + 光照 + 视野 + 潜行：跑若干回合，
        # 任何「看得见玩家的怪」都必须在玩家的可见集合内
        g = Game.procedural(RandomSource(seed=11), depth=1,
                            fov=True, stealth=True, light=True)
        for _ in range(40):
            g.monster_turn()
            g.update_fov()  # 确保视野与感知同步
            for m in g.monsters:
                if m.alive and g.monster_can_see_player(m):
                    self.assertTrue(g.is_visible(m.x, m.y),
                                    f"{m.name}@{m.x},{m.y} 看得见你、你却看不见它")

    def test_symmetry_across_seeds(self):
        # 多 seed 回归：#9 硬性质在任意楼层布局下都成立
        for seed in (3, 7, 11, 19, 23):
            g = Game.procedural(RandomSource(seed=seed), depth=1,
                                fov=True, stealth=True, light=True)
            for _ in range(30):
                g.monster_turn()
                g.update_fov()
                for m in g.monsters:
                    if m.alive and g.monster_can_see_player(m):
                        self.assertTrue(g.is_visible(m.x, m.y),
                                        f"seed={seed} {m.name}@{m.x},{m.y} 幽灵猎手")

    def test_dark_monster_symmetric(self):
        # 两者都在昏暗处：怪感知 4 = 玩家视野 4（按目标格 DIM）⇒ 对称
        # (3,1) 距离玩家 2，微光贡献 4-2=2 ⇒ DIM
        g = _make(_LONG, light=True, fov=True, stealth=True)
        g.px, g.py = 1, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 3, 1, hp=8, behavior="chase")
        self.assertEqual(g.light_level_at(3, 1), LIGHT_LEVEL_DIM)
        # DIM 档位：怪感知 4、玩家视野 4，距离 2 ≤ 4 ⇒ 双向都看得见
        self.assertTrue(g.monster_can_see_player(m))
        self.assertTrue(g.is_visible(3, 1))

    def test_both_dark_invisible_symmetric(self):
        # 两者都在全黑处（距离 ≥ 5、微光贡献 0 ⇒ DARK）：
        # 怪感知 2、玩家视野 2，距离 5 > 2 ⇒ 双向都看不见
        g = _make(_LONG, light=True, fov=True, stealth=True)
        g.px, g.py = 1, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 6, 1, hp=8, behavior="chase")
        self.assertEqual(g.light_level_at(6, 1), LIGHT_LEVEL_DARK)
        self.assertFalse(g.monster_can_see_player(m))
        self.assertFalse(g.is_visible(6, 1))


class TestLightFovDeterminism(unittest.TestCase):
    """不变量 #2：同 seed + 同输入序列 ⇒ 同可见集合；光照不消耗 RandomSource。"""

    def test_same_seed_same_visible_frames(self):
        moves = [(1, 0), (1, 0), (0, 0), (1, 0), (0, 0)]

        def vis_frames(seed):
            g = Game.procedural(RandomSource(seed=seed), depth=2,
                                fov=True, light=True)
            out = [frozenset(g.visible)]
            for dx, dy in moves:
                g.move(dx, dy)
                out.append(frozenset(g.visible))
            return out

        self.assertEqual(vis_frames(19), vis_frames(19))

    def test_light_fov_does_not_consume_random(self):
        # 光照 + 视野是纯几何 ⇒ 开不开，战斗随机序列必须完全一致
        a = Game.procedural(RandomSource(seed=19), depth=1, fov=False, light=False)
        b = Game.procedural(RandomSource(seed=19), depth=1, fov=True, light=True)
        for _ in range(5):
            b.update_fov()
            b.render()
        self.assertEqual([a.rng.int(0, 999) for _ in range(5)],
                         [b.rng.int(0, 999) for _ in range(5)])


class TestLightFovRenderPurity(unittest.TestCase):
    """不变量 #8：光照影响可见集合，不改 render 字形。"""

    def test_fov_off_render_identical_with_light(self):
        # fov=False ⇒ 全图渲染，光照不影响字形（只影响颜色，经 colorize）
        a = _make(_LONG, light=True, fov=False)
        b = _make(_LONG, light=False, fov=False)
        self.assertEqual(a.render(), b.render())

    def test_fov_on_uses_original_glyphs(self):
        # fov=True + light=True ⇒ 迷雾渲染，可见格子仍用原字形（不引入新字形）
        g = _make(_LONG, light=True, fov=True)
        from rogue.tiles import WALL, PLAYER, UNSEEN
        rendered = g.render()
        chars = set(rendered.replace("\n", ""))
        # 只有 墙/地板/玩家/未探索 四种字形（长走廊无怪无道具无楼梯）
        self.assertTrue(chars.issubset({WALL, FLOOR, PLAYER, UNSEEN}))

    def test_render_does_not_touch_world_state(self):
        # render() 不改写任何状态（#8：world state 前后快照比对）
        g = Game.procedural(RandomSource(seed=19), depth=1, fov=True, light=True)
        g.spawn_item("sandwich", g.px, g.py)
        before = (["".join(r) for r in g.grid],
                  [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                  [(i.key, i.x, i.y) for i in g.items],
                  g.player_hp, g.player_dmg_bonus, g.depth, g.stairs,
                  (g.px, g.py), set(g.visible))
        g.render()
        g.render()
        after = (["".join(r) for r in g.grid],
                 [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                 [(i.key, i.x, i.y) for i in g.items],
                 g.player_hp, g.player_dmg_bonus, g.depth, g.stairs,
                 (g.px, g.py), set(g.visible))
        self.assertEqual(before, after)

    def test_render_twice_stable(self):
        g = Game.procedural(RandomSource(seed=7), depth=1, fov=True, light=True)
        self.assertEqual(g.render(), g.render())


class TestLightFovIdempotent(unittest.TestCase):
    """update_fov 幂等：同状态算几次结果一样。"""

    def test_update_fov_idempotent_with_light(self):
        g = _make(_LONG, light=True, fov=True)
        first = set(g.visible)
        g.update_fov()
        g.update_fov()
        self.assertEqual(first, g.visible)

    def test_update_fov_idempotent_procedural(self):
        g = Game.procedural(RandomSource(seed=19), depth=1, fov=True, light=True)
        first = set(g.visible)
        g.update_fov()
        self.assertEqual(first, g.visible)


class TestLightFovExploredMemory(unittest.TestCase):
    """换层清空记忆（M6 规则不破）+ 暗处探索后留下记忆。"""

    def test_explored_only_grows_with_light(self):
        # 光照下走过的地方仍留记忆（explored 单调增长）
        g = _make(_LONG, light=True, fov=True)
        seen = []
        for dx in (1, 0), (1, 0), (1, 0):
            g.move(*dx)
            seen.append(set(g.explored))
        for prev, nxt in zip(seen, seen[1:]):
            self.assertTrue(prev.issubset(nxt), "记忆集合不该缩水")

    def test_descend_resets_memory_with_light(self):
        # 换层清空 explored（M6 规则）
        g = Game.procedural(RandomSource(seed=12), depth=1, fov=True, light=True)
        g.move(1, 0)
        g.move(0, 1)
        self.assertGreater(len(g.explored), len(g.visible))
        # 把玩家挪到楼梯上下潜
        g.grid[g.py][g.px] = FLOOR
        g.px, g.py = g.stairs
        g.grid[g.py][g.px] = " @"
        g.grid[g.py][g.px] = "@"
        g.update_fov()
        self.assertTrue(g.descend())
        self.assertEqual(g.explored, g.visible)  # 新楼层重新探索


if __name__ == "__main__":
    unittest.main()
