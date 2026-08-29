"""M6 视野 / 渲染层行为规格（对应工单 T-006 验收 A）。

核心红线覆盖：
- 不变量 #1 视野是纯几何计算，不消耗 RandomSource（也不引入随机模块）
- 不变量 #2 视野只依赖 grid + 玩家位置 + rooms ⇒ 同状态 ⇒ 同可见集合
- 不变量 #8 render() 不改写地形 / 玩家 / 怪物 / 道具状态（唯一例外：记忆单调增长）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.fov import (SIGHT_RADIUS, SPIDER_SENSE_RADIUS, bresenham_between,
                       has_line_of_sight, visible_tiles, in_spider_sense)
from rogue.game import Game
from rogue.level import Level, Room, TUTORIAL_LEVEL_NAME
from rogue.rng import RandomSource
from rogue.tiles import WALL, FLOOR, PLAYER, MONSTER, ITEM, STAIRS, UNSEEN, SENSE

# 测试用地图（'@' 只是标注起点，交给 Game 自己落笔）
_OPEN = [
    "#######",
    "#@....#",
    "#####.#",
    "#.....#",
    "#######",
]
_BLOCKED = [
    "#########",
    "#@#.....#",
    "#########",
]
_ROOM = [
    "#####",
    "#@..#",
    "#####",
]
_PILLAR = [
    "#########",
    "#@..#...#",
    "#...#...#",
    "#.......#",
    "#########",
]
_NO_STAIRS = (-1, -1)   # 越界坐标当作「本层无楼梯」（渲染与 can_descend 都会忽略它）


def _make(rows, start=(1, 1), stairs=None, rooms=(), fov=True, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，测视野本身）。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, stairs or _NO_STAIRS, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False, fov=fov)


def _open_field(width=21, height=9):
    """一张开阔地：外圈墙、内部全地板。"""
    return (["#" * width]
            + ["#" + FLOOR * (width - 2) + "#"] * (height - 2)
            + ["#" * width])


def _walk(game: Game, steps) -> None:
    for dx, dy in steps:
        game.move(dx, dy)


def _to_corner(game: Game) -> None:
    """从 (1,1) 沿走廊绕到 (1,3)——走完之后 (1,1) 与 (3,1) 都变成「记忆」。"""
    _walk(game, [(1, 0)] * 4 + [(0, 1)] * 2 + [(-1, 0)] * 4)
    game.update_fov()


class TestFovSwitch(unittest.TestCase):
    """视野是可选开关：默认关闭 ⇒ 既有 79 例规格不受影响。"""

    def test_fov_disabled_by_default(self):
        self.assertFalse(Game(rng=RandomSource(seed=0)).fov_enabled)
        self.assertFalse(Game.procedural(RandomSource(seed=0), depth=1).fov_enabled)

    def test_fov_enabled_when_asked(self):
        self.assertTrue(_make(_ROOM).fov_enabled)
        self.assertTrue(Game(rng=RandomSource(seed=0), fov=True).fov_enabled)
        self.assertTrue(Game.procedural(RandomSource(seed=0), depth=1, fov=True).fov_enabled)

    def test_default_render_is_full_map(self):
        # 视野关闭 ⇒ 全图可见（教学图一行不落）
        g = Game(rng=RandomSource(seed=0), fov=False)
        self.assertEqual(g.render(), g._render_full())
        self.assertNotIn(UNSEEN, g.render())

    def test_default_render_still_shows_stairs(self):
        # 与 test_level.py::test_render_shows_stairs 同款断言，确保开关没打破它
        g = Game.procedural(RandomSource(seed=4), depth=1)
        self.assertIn(STAIRS, g.render())
        self.assertNotIn(UNSEEN, g.render())

    def test_fog_hides_unexplored_area(self):
        g = Game.procedural(RandomSource(seed=19), depth=1, fov=True)
        self.assertIn(UNSEEN, g.render())
        self.assertLess(len(g.explored), g.width * g.height)


class TestVisibilityGeometry(unittest.TestCase):
    def test_player_tile_always_visible(self):
        g = _make(_OPEN)
        self.assertTrue(g.is_visible(g.px, g.py))
        self.assertIn(PLAYER, g.render())

    def test_visible_is_subset_of_explored(self):
        g = _make(_OPEN)
        self.assertTrue(g.visible.issubset(g.explored))

    def test_wall_blocks_sight(self):
        g = _make(_BLOCKED)
        self.assertTrue(g.is_visible(2, 1))   # 墙本身能看见
        self.assertFalse(g.is_visible(3, 1))  # 墙后面看不见
        self.assertFalse(g.is_visible(7, 1))

    def test_sight_stops_at_radius(self):
        grid = [list(r) for r in _open_field()]
        origin = (10, 4)
        vis = visible_tiles(grid, origin, SIGHT_RADIUS, rooms=[])
        self.assertIn((18, 4), vis)   # 距离 8（恰好在半径内）
        self.assertNotIn((19, 4), vis)  # 距离 9（超出半径）
        self.assertIn((10, 4), vis)

    def test_visible_tiles_stay_in_bounds(self):
        g = Game.procedural(RandomSource(seed=3), depth=1, fov=True)
        for (x, y) in g.visible:
            self.assertTrue(g.in_bounds(x, y), f"{x},{y} 越界")

    def test_update_fov_is_idempotent(self):
        g = _make(_OPEN)
        first = set(g.visible)
        g.update_fov()
        self.assertEqual(first, g.visible)

    def test_explored_only_grows(self):
        g = _make(_OPEN)
        seen = []
        for dx, dy in [(1, 0), (1, 0), (0, 1), (0, 1), (1, 0)]:
            g.move(dx, dy)
            seen.append(set(g.explored))
        for prev, nxt in zip(seen, seen[1:]):
            self.assertTrue(prev.issubset(nxt), "记忆集合不该缩水")

    def test_move_updates_fov(self):
        g = _make(_OPEN)
        before = set(g.visible)
        g.move(1, 0)
        self.assertNotEqual(before, g.visible)
        self.assertTrue(g.is_visible(g.px, g.py))


class TestRoomLighting(unittest.TestCase):
    """进房间点亮整间（复用 M5 的 Game.rooms）。"""

    def test_open_field_corners_dark_without_rooms(self):
        grid = [list(r) for r in _open_field()]
        vis = visible_tiles(grid, (10, 4), SIGHT_RADIUS, rooms=[])
        self.assertNotIn((1, 1), vis)
        self.assertNotIn((19, 7), vis)

    def test_room_lights_up_beyond_sight_radius(self):
        rows = _open_field()
        room = Room(1, 1, len(rows[0]) - 2, len(rows) - 2)
        g = _make(rows, start=room.center, rooms=[room])
        # 房角距离圆心 ≈ 9.5 > SIGHT_RADIUS(8)，靠「室内照明」才亮
        for (x, y) in room.tiles():
            self.assertTrue(g.is_visible(x, y), f"房内 {x},{y} 该被点亮")

    def test_room_lighting_needs_player_inside(self):
        rows = _open_field(width=25)
        room = Room(13, 1, 11, 7)  # 房间只盖住右半边，玩家站在左半边（房外）
        g = _make(rows, start=(1, 4), rooms=[room])
        self.assertFalse(g.is_visible(23, 7))  # 人不在房里 ⇒ 远端房角仍是黑的


class TestSpiderSense(unittest.TestCase):
    """蜘蛛感应：4 格内穿墙感知，只给 `?` 轮廓。"""

    def test_sense_radius_is_chebyshev(self):
        self.assertTrue(in_spider_sense((5, 5), (9, 8), 4))
        self.assertFalse(in_spider_sense((5, 5), (10, 5), 4))

    def test_sense_is_smaller_than_sight(self):
        self.assertLess(SPIDER_SENSE_RADIUS, SIGHT_RADIUS)

    def test_hidden_nearby_monster_shows_sense_marker(self):
        g = _make(_BLOCKED)
        g.spawn_monster("街头小混混", 3, 1, 8)  # 墙后 2 格：看不见，但感得到
        self.assertFalse(g.is_visible(3, 1))
        self.assertIn((3, 1), [(m.x, m.y) for m in g.spider_sense()])
        self.assertIn(SENSE, g.render())

    def test_far_hidden_monster_is_not_sensed(self):
        g = _make(_BLOCKED)
        g.spawn_monster("街头小混混", 7, 1, 8)  # 墙后 6 格：超出感应半径
        self.assertEqual(g.spider_sense(), [])
        self.assertNotIn(SENSE, g.render())
        self.assertNotIn(MONSTER, g.render())

    def test_sense_skips_dead_monsters(self):
        g = _make(_BLOCKED)
        m = g.spawn_monster("街头小混混", 3, 1, 8)
        m.hp = 0
        self.assertEqual(g.spider_sense(), [])
        self.assertNotIn(SENSE, g.render())

    def test_visible_monster_shows_M_not_sense(self):
        g = _make(_ROOM)
        g.spawn_monster("街头小混混", 2, 1, 8)
        self.assertTrue(g.is_visible(2, 1))
        self.assertIn(MONSTER, g.render())
        self.assertNotIn(SENSE, g.render())


class TestMemory(unittest.TestCase):
    """走过的地方留记忆：地形 / 楼梯 / 道具留下，怪物不留。"""

    def test_unexplored_rendered_as_blank(self):
        g = _make(_OPEN)
        self.assertFalse(g.is_visible(1, 3))  # 隔着一堵墙
        row3 = g.render().splitlines()[3]
        self.assertEqual(row3[1], UNSEEN)

    def test_memory_keeps_terrain_after_leaving(self):
        g = _make(_OPEN)
        _to_corner(g)  # (1,1) 走过但此刻看不见
        self.assertIn((1, 1), g.explored)
        self.assertFalse(g.is_visible(1, 1))
        row1 = g.render().splitlines()[1]
        self.assertEqual(row1[1], FLOOR)

    def test_stairs_remembered_once_seen(self):
        g = _make(_OPEN, stairs=(3, 1))
        self.assertIn(STAIRS, g.render())
        _to_corner(g)  # (3,1) 变成记忆
        self.assertFalse(g.is_visible(3, 1))
        self.assertIn(STAIRS, g.render())

    def test_item_remembered_once_seen(self):
        g = _make(_OPEN, stairs=None)
        g.spawn_item("sandwich", 3, 1)
        self.assertIn(ITEM, g.render())
        _to_corner(g)
        self.assertFalse(g.is_visible(3, 1))
        self.assertIn(ITEM, g.render())

    def test_unseen_monster_is_not_rendered(self):
        # 柱子挡着、又超出蜘蛛感应半径 ⇒ 完全不画（怪物不进记忆）
        g = _make(_PILLAR)
        g.spawn_monster("街头小混混", 6, 1, 8)
        self.assertFalse(g.is_visible(6, 1))
        self.assertEqual(g.spider_sense(), [])
        self.assertNotIn(MONSTER, g.render())
        self.assertNotIn(SENSE, g.render())

    def test_monster_appears_when_walking_into_view(self):
        g = _make(_PILLAR)
        g.spawn_monster("街头小混混", 6, 1, 8)
        _walk(g, [(0, 1), (0, 1)] + [(1, 0)] * 6 + [(0, -1), (0, -1)])
        self.assertTrue(g.is_visible(6, 1))
        self.assertIn(MONSTER, g.render())

    def test_descend_resets_memory(self):
        g = Game.procedural(RandomSource(seed=12), depth=1, fov=True)
        _walk(g, [(1, 0), (0, 1), (-1, 0)])
        self.assertGreater(len(g.explored), len(g.visible))
        g.grid[g.py][g.px] = FLOOR
        g.px, g.py = g.stairs
        g.grid[g.py][g.px] = PLAYER
        g.update_fov()
        self.assertTrue(g.descend())
        self.assertEqual(g.explored, g.visible)  # 新楼层重新探索


class TestRenderPriority(unittest.TestCase):
    """渲染优先级：? < 楼梯 > < 道具 ! < 怪物 M < 玩家 @。"""

    def _char_at(self, g: Game, x: int, y: int) -> str:
        return g.render().splitlines()[y][x]

    def test_item_over_stairs(self):
        g = _make(_ROOM, stairs=(2, 1))
        g.spawn_item("sandwich", 2, 1)
        self.assertEqual(self._char_at(g, 2, 1), ITEM)

    def test_monster_over_item(self):
        g = _make(_ROOM, stairs=(2, 1))
        g.spawn_item("sandwich", 2, 1)
        g.spawn_monster("街头小混混", 2, 1, 8)
        self.assertEqual(self._char_at(g, 2, 1), MONSTER)

    def test_player_over_everything(self):
        g = _make(_ROOM, stairs=(1, 1))
        g.spawn_item("sandwich", 1, 1)
        g.spawn_monster("街头小混混", 1, 1, 8)
        self.assertEqual(self._char_at(g, 1, 1), PLAYER)

    def test_stairs_over_spider_sense(self):
        g = _make(_OPEN, stairs=(3, 1))
        _to_corner(g)  # (3,1) 变成记忆：看得见楼梯、看不见怪
        g.spawn_monster("街头小混混", 3, 1, 8)  # 感应得到（2 格）却被墙挡着
        self.assertFalse(g.is_visible(3, 1))
        self.assertEqual(len(g.spider_sense()), 1)
        self.assertEqual(self._char_at(g, 3, 1), STAIRS)

    def test_item_over_spider_sense(self):
        g = _make(_OPEN)
        g.spawn_item("sandwich", 3, 1)
        _to_corner(g)
        g.spawn_monster("街头小混混", 3, 1, 8)
        self.assertEqual(len(g.spider_sense()), 1)
        self.assertEqual(self._char_at(g, 3, 1), ITEM)


class TestFovDeterminism(unittest.TestCase):
    """不变量 #2：同 seed + 同输入序列 ⇒ 同画面。"""

    def test_same_seed_same_fog_frames(self):
        moves = [(1, 0), (1, 0), (0, 1), (0, 1), (-1, 0), (1, 0), (0, -1)]

        def frames(seed):
            g = Game.procedural(RandomSource(seed=seed), depth=2, fov=True)
            out = [g.render()]
            for dx, dy in moves:
                g.move(dx, dy)
                g.monster_turn()
                out.append(g.render())
            return out

        self.assertEqual(frames(19), frames(19))

    def test_fov_does_not_consume_random(self):
        # 视野是纯几何 ⇒ 开不开视野，战斗随机序列必须完全一致
        a = Game.procedural(RandomSource(seed=19), depth=1, fov=False)
        b = Game.procedural(RandomSource(seed=19), depth=1, fov=True)
        for _ in range(5):
            b.update_fov()
            b.render()
        self.assertEqual([a.rng.int(0, 999) for _ in range(5)],
                         [b.rng.int(0, 999) for _ in range(5)])


class TestRenderPurity(unittest.TestCase):
    """不变量 #8：render() 不改写地形与实体状态。"""

    def test_render_does_not_touch_world_state(self):
        g = Game.procedural(RandomSource(seed=19), depth=1, fov=True)
        g.spawn_item("sandwich", g.px, g.py)
        before = (["".join(r) for r in g.grid],
                  [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                  [(i.key, i.x, i.y) for i in g.items],
                  g.player_hp, g.player_dmg_bonus, g.depth, g.stairs,
                  (g.px, g.py))
        g.render()
        g.render()
        after = (["".join(r) for r in g.grid],
                 [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                 [(i.key, i.x, i.y) for i in g.items],
                 g.player_hp, g.player_dmg_bonus, g.depth, g.stairs,
                 (g.px, g.py))
        self.assertEqual(before, after)

    def test_render_twice_is_stable(self):
        g = Game.procedural(RandomSource(seed=7), depth=1, fov=True)
        self.assertEqual(g.render(), g.render())

    def test_render_keeps_grid_charset(self):
        # 渲染层不把 '@' / 'M' / '!' / '>' 写回 grid（grid 只存地形与 '@'）
        g = Game.procedural(RandomSource(seed=7), depth=1, fov=True)
        g.render()
        chars = {ch for row in g.grid for ch in row}
        self.assertTrue(chars.issubset({WALL, FLOOR, PLAYER}))


class TestFovHelpers(unittest.TestCase):
    """fov.py 的纯函数（几何工具）。"""

    def test_bresenham_excludes_endpoints(self):
        self.assertEqual(bresenham_between(1, 1, 1, 1), [])
        self.assertEqual(bresenham_between(1, 1, 2, 1), [])
        self.assertEqual(bresenham_between(1, 1, 4, 1), [(2, 1), (3, 1)])

    def test_line_of_sight_blocked_by_wall(self):
        grid = [list(r.replace("@", FLOOR)) for r in _BLOCKED]
        self.assertTrue(has_line_of_sight(grid, (1, 1), (3, 1)) is False)
        self.assertTrue(has_line_of_sight(grid, (1, 1), (2, 1)))  # 紧贴的墙看得见

    def test_tutorial_map_has_no_rooms(self):
        g = Game(rng=RandomSource(seed=0), fov=True)
        self.assertEqual(g.level_name, TUTORIAL_LEVEL_NAME)
        self.assertEqual(g.rooms, [])
        self.assertGreater(len(g.explored), 0)


if __name__ == "__main__":
    unittest.main()
