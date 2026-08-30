"""M17 环境光照场与完整光照场分离规格。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（光照纯几何、不引入随机模块）
- 不变量 #2 回合确定性（ambient_field / light_field 只依赖 grid + 光源 ⇒ 同状态同场，不消耗 rng）
- 不变量 #8 渲染纯净性（分离只新增只读查询，不改 render 字形；默认消费点仍走完整场 ⇒ 行为零回归）
- 不变量 #9 延伸：分离不改变「暗处缩短怪物感知」的硬性质（完整场仍含玩家微光/手电，
  怪物感知半径计算路径未变）

设计要点（ADR-013）：把「静态环境照明」从「玩家随身光源」中拆出——
  ambient_field = 仅房间中心固定灯（不含玩家微光 / 随身手电），代表楼层的环境光；
  light_field   = 房间灯 + 玩家微光 + 随身手电，即原有完整场。
两份场都由 update_light 同源、幂等重算。默认所有玩法 / 渲染判定继续走 light_field（完整场），
ambient_field 仅作为「只看环境光」的查询入口对外暴露（ambient_level_at），行为零回归。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.light import (ROOM_LIGHT_RADIUS, PLAYER_GLOW_RADIUS, FLASHLIGHT_RADIUS,
                         LIGHT_LEVEL_DARK, LIGHT_LEVEL_DIM, LIGHT_LEVEL_LIT,
                         light_field, monster_sight_radius)
from rogue.fov import SIGHT_RADIUS, visible_tiles
from rogue.game import Game
from rogue.level import Level, Room
from rogue.rng import RandomSource
from rogue.tiles import FLOOR

_NO_STAIRS = (-1, -1)

# 地图 A：左侧小房间（cols1-3）+ 隔墙(col4) + 右侧暗走廊(cols5-12)；玩家站在暗走廊。
#   - 环境光（房间灯，中心(2,1)）遇隔墙即断 ⇒ 走廊在 ambient_field 里全黑；
#   - 玩家微光（半径4，源(5,1)）沿走廊无遮挡 ⇒ 走廊近处在 light_field 里被照亮。
#   ⇒ 走廊近处格是「完整场亮、环境场黑」的天然判别点。
_MAP_A = [
    "##############",
    "#...#@.......#",
    "##############",
]
_ROOM_A = Room(1, 1, 3, 1)        # 覆盖 cols1-3，中心 (2,1)

# 地图 B：整层一个宽房间（cols1-11，中心(6,1)），玩家在左角(1,1)。
#   房间灯半径9 ⇒ 中心被照亮；玩家微光半径4 ⇒ 中心(距5)够不到 ⇒ 微光不参与中心照明。
#   用于验证「射碎/关掉房间灯 ⇒ 该光源从 ambient 与 light 两份场同时消失」。
_MAP_B = [
    "#############",
    "#@..........#",
    "#############",
]
_ROOM_B = Room(1, 1, 11, 1)       # 覆盖 cols1-11，中心 (6,1)


def _make(rows, rooms=(), start=(1, 1), fov=False, stealth=True,
          light=False, flashlight=False, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，只测光照场分离）。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, _NO_STAIRS, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth, light=light, flashlight=flashlight)


class TestAmbientExcludesPlayerLight(unittest.TestCase):
    """环境场不含玩家微光 / 手电（只含房间灯）。"""

    def test_ambient_excludes_player_glow(self):
        # 玩家在暗走廊(5,1)，微光照亮走廊近处(6,1)，但环境场因隔墙无房间光 ⇒ 走廊(6,1)仍黑
        g = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=True)
        self.assertEqual(g.ambient_level_at(6, 1), LIGHT_LEVEL_DARK)
        self.assertNotEqual(g.light_level_at(6, 1), LIGHT_LEVEL_DARK)  # 完整场被微光照亮

    def test_ambient_lights_only_rooms(self):
        # 房间内(2,1)有房间灯 ⇒ 环境场明亮；隔墙外的走廊(10,1)环境场全黑
        g = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=True)
        self.assertEqual(g.ambient_level_at(2, 1), LIGHT_LEVEL_LIT)
        self.assertEqual(g.ambient_level_at(10, 1), LIGHT_LEVEL_DARK)

    def test_ambient_unchanged_by_flashlight(self):
        # 手电只改完整场（追加玩家处光源），环境场（仅房间灯）应纹丝不动
        g = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=True, flashlight=True)
        ambient_before = dict(g.ambient_field)
        far = (10, 1)                               # 隔墙外走廊远端：手电半径6可达，微光半径4不可达
        lit_with_flashlight_on = g.light_level_at(*far)
        g.toggle_flashlight()                       # 关手电
        # 环境场不随手电变化
        self.assertEqual(g.ambient_field, ambient_before)
        self.assertEqual(g.ambient_level_at(*far), LIGHT_LEVEL_DARK)
        # 完整场确实随手电改变（关灯后远端走廊变暗）
        self.assertNotEqual(g.light_level_at(*far), lit_with_flashlight_on)
        g.toggle_flashlight()                       # 开手电
        self.assertEqual(g.ambient_field, ambient_before)


class TestAmbientMatchesRoomOnlyField(unittest.TestCase):
    """ambient_field 严格等于「仅房间灯」算出的场（定义即契约）。"""

    def test_ambient_equals_room_only_light_field(self):
        g = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=True)
        expected = light_field(
            g.grid,
            [(r.center[0], r.center[1], ROOM_LIGHT_RADIUS)
             for r in g.rooms
             if r.center not in g.switched_lights
             and r.center not in g.destroyed_lights],
        )
        self.assertEqual(g.ambient_field, expected)

    def test_full_field_includes_glow_beyond_ambient(self):
        # 完整场比环境场多了玩家微光 ⇒ 至少在「走廊近处」存在差异
        g = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=True)
        diff = [(k, v, g.light_field[k])
                for k, v in g.ambient_field.items() if g.light_field.get(k) != v]
        self.assertTrue(any(lvl != LIGHT_LEVEL_DARK for _, _, lvl in diff)
                        or any(g.light_field.get(k, LIGHT_LEVEL_DARK) != LIGHT_LEVEL_DARK
                               for k in [(6, 1), (7, 1)]),
                        "完整场应比环境场多照出玩家微光覆盖的走廊近处")


class TestSourceRemovalFromBothFields(unittest.TestCase):
    """关灯 / 碎灯同时移除 ambient 与 light 两份场里的房间光源（只移除不新增）。"""

    def test_destroy_light_removes_from_both(self):
        g = _make(_MAP_B, rooms=(_ROOM_B,), start=(1, 1), light=True)
        cx, cy = _ROOM_B.center
        self.assertEqual(g.ambient_level_at(cx, cy), LIGHT_LEVEL_LIT)
        self.assertEqual(g.light_level_at(cx, cy), LIGHT_LEVEL_LIT)
        self.assertTrue(g.can_destroy_light(cx, cy))
        g.destroy_light(cx, cy)
        # 房间灯被射碎 ⇒ 环境场（仅此一源）整层变暗；完整场中心也因超出微光半径而变暗
        self.assertEqual(g.ambient_level_at(cx, cy), LIGHT_LEVEL_DARK)
        self.assertEqual(g.light_level_at(cx, cy), LIGHT_LEVEL_DARK)

    def test_toggle_light_off_removes_from_both(self):
        g = _make(_MAP_B, rooms=(_ROOM_B,), start=(1, 1), light=True)
        cx, cy = _ROOM_B.center
        self.assertEqual(g.ambient_level_at(cx, cy), LIGHT_LEVEL_LIT)
        self.assertTrue(g.can_toggle_light(cx, cy))
        g.toggle_light(cx, cy)                      # 关灯
        self.assertEqual(g.ambient_level_at(cx, cy), LIGHT_LEVEL_DARK)
        self.assertEqual(g.light_level_at(cx, cy), LIGHT_LEVEL_DARK)


class TestAmbientOffAndDeterminism(unittest.TestCase):
    """光照关闭 ⇒ 两份场清空且查询恒明亮；分离是纯几何、幂等、确定。"""

    def test_light_off_empties_both_and_queries_lit(self):
        g = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=False)
        self.assertEqual(g.light_field, {})
        self.assertEqual(g.ambient_field, {})
        # 任何查询恒明亮（不改变任何行为，#8/#9）
        self.assertEqual(g.ambient_level_at(2, 1), LIGHT_LEVEL_LIT)
        self.assertEqual(g.light_level_at(2, 1), LIGHT_LEVEL_LIT)

    def test_update_light_idempotent_and_deterministic(self):
        g = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=True)
        first = dict(g.ambient_field)
        g.update_light()                            # 再算一次
        self.assertEqual(g.ambient_field, first)
        # 同 grid + 同房间 + 同玩家 ⇒ 同环境场（#2）
        g2 = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=True)
        self.assertEqual(g2.ambient_field, first)


class TestUpdateFovUsesFullField(unittest.TestCase):
    """M13 玩家视野必须继续用完整场（含微光），而非环境场——保证行为零回归。"""

    def test_visible_set_matches_full_field_not_ambient(self):
        g = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=True, fov=True)
        # 构造一份「若误用环境场」的可见集合，应与原可见集合不同 ⇒ 证明 update_fov 用的是完整场
        visible_full = visible_tiles(g.grid, (g.px, g.py), SIGHT_RADIUS,
                                     g.rooms, light_field=g.light_field)
        visible_ambient = visible_tiles(g.grid, (g.px, g.py), SIGHT_RADIUS,
                                        g.rooms, light_field=g.ambient_field)
        self.assertEqual(g.visible, visible_full)
        self.assertNotEqual(g.visible, visible_ambient)   # 完整场比环境场多照亮近处


class TestMonsterPerceptionUnchanged(unittest.TestCase):
    """M11 怪物感知仍走完整场（light_level_at）→ 不变量 #9 硬性质不破、行为零回归。"""

    def test_monster_sight_uses_full_field_radius(self):
        g = _make(_MAP_A, rooms=(_ROOM_A,), start=(5, 1), light=True)
        # 走廊近处(6,1)在完整场被微光照亮 ⇒ 该格的怪物感知半径应取「明亮」档（最大）
        lvl = g.light_level_at(6, 1)
        self.assertEqual(monster_sight_radius(lvl), 7)    # MONSTER_SIGHT_RADIUS
        # 同一格若只用环境场则是全黑 ⇒ 半径会缩短；确认我们没把怪物感知切到环境场
        self.assertNotEqual(monster_sight_radius(g.ambient_level_at(6, 1)),
                            monster_sight_radius(lvl))


if __name__ == "__main__":
    unittest.main()
