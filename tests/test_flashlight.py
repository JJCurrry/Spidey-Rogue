"""M12 随身手电（动态光源：玩家可开关的随身光）。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（toggle_flashlight 纯状态操作，不引入随机模块、不消耗 rng）
- 不变量 #2 回合确定性（手电只改光照场 ⇒ 同状态同场；toggle 不改写玩法状态）
- 不变量 #8 渲染纯净性（手电只经由 colorize 上色，不改 render 字形）
- 不变量 #9 延伸：手电只缩短怪物感知半径（恒 ≤ MONSTER_SIGHT_RADIUS），
  所以「怪看得见你 ⇒ 你看得见它」的硬性质不被破坏
- 不变量 #13：手电默认关闭（flashlight=False）⇒ 即使 light=True 也与 M11 逐字节一致；
  toggle 不改写任何玩法状态（只翻标志 + 重算光照场）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.light import (ROOM_LIGHT_RADIUS, PLAYER_GLOW_RADIUS, FLASHLIGHT_RADIUS,
                         LIGHT_LEVEL_DARK, LIGHT_LEVEL_DIM, LIGHT_LEVEL_LIT,
                         light_contribution)
from rogue.fov import MONSTER_SIGHT_RADIUS
from rogue.game import Game
from rogue.level import Level, Room
from rogue.rng import RandomSource
from rogue.tiles import WALL, FLOOR, PLAYER

# 长走廊（无房间）：只有玩家随身光源，便于验证「手电开/关」对玩家周围明暗的影响
_LONG = [
    "############",
    "#@..........#",
    "############",
]
_ROOM = [
    "############",
    "#@.........#",
    "############",
]
_NO_STAIRS = (-1, -1)


def _make(rows, start=(1, 1), rooms=(), fov=False, stealth=True,
          light=False, flashlight=False, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，只测光照与感知）。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, _NO_STAIRS, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth, light=light, flashlight=flashlight)


def _open_field(width=25, height=9):
    return (["#" * width]
            + ["#" + FLOOR * (width - 2) + "#"] * (height - 2)
            + ["#" * width])


class TestFlashlightSwitch(unittest.TestCase):
    """手电是可选开关：默认不装备 ⇒ 即使 light=True 也与 M11 完全一致（不变量 #13）。"""

    def test_flashlight_disabled_by_default(self):
        # 连 light 都没开时，手电开关默认 False
        self.assertFalse(Game(rng=RandomSource(seed=0)).flashlight_enabled)
        self.assertFalse(Game(rng=RandomSource(seed=0)).flashlight_on)
        # 只开 light 不开手电 ⇒ 手电仍不装备（与 M11 同）
        g = _make(_LONG, light=True)
        self.assertFalse(g.flashlight_enabled)
        self.assertFalse(g.flashlight_on)

    def test_flashlight_enabled_when_asked(self):
        g = _make(_LONG, light=True, flashlight=True)
        self.assertTrue(g.flashlight_enabled)
        self.assertTrue(g.flashlight_on)         # 装备即点亮
        # 不装备手电（默认）与 M11 同：light=True 时照样能跑
        self.assertTrue(_make(_LONG, light=True).light_enabled)


class TestFlashlightSources(unittest.TestCase):
    """光源构成：手电只在「光照开 + 手电装备且点亮」时追加玩家处动态光源。"""

    def test_flashlight_source_present_when_on(self):
        g = _make(_LONG, light=True, flashlight=True)
        srcs = g._light_sources()
        self.assertIn((g.px, g.py, FLASHLIGHT_RADIUS), srcs)

    def test_flashlight_source_absent_when_not_equipped(self):
        g = _make(_LONG, light=True, flashlight=False)
        srcs = g._light_sources()
        self.assertNotIn((g.px, g.py, FLASHLIGHT_RADIUS), srcs)

    def test_flashlight_source_absent_when_toggled_off(self):
        g = _make(_LONG, light=True, flashlight=True)
        g.toggle_flashlight()                    # 关灯
        srcs = g._light_sources()
        self.assertNotIn((g.px, g.py, FLASHLIGHT_RADIUS), srcs)

    def test_flashlight_source_absent_when_light_off(self):
        # 光照都没开，手电标志位翻了也不产生光源（_light_sources 受 light_enabled 门控）
        g = _make(_LONG, light=False, flashlight=True)
        g.flashlight_on = True
        self.assertNotIn((g.px, g.py, FLASHLIGHT_RADIUS), g._light_sources())


class TestFlashlightField(unittest.TestCase):
    """手电点亮玩家周围：开灯让微光照不到的格子变亮，关灯还原（纯几何、零随机）。"""

    def test_flashlight_lights_ring_beyond_glow(self):
        # 玩家微光半径 4、手电半径 6：
        #   距离 4 处——微光贡献 0（全黑），手电贡献 6-4=2（昏暗）
        #   距离 2 处——微光贡献 2（昏暗），手电贡献 4（明亮）
        g = _make(_LONG, light=True, flashlight=False)
        g.px, g.py = 1, 1
        g.update_fov()
        self.assertEqual(g.light_level_at(5, 1), LIGHT_LEVEL_DARK)
        self.assertEqual(g.light_level_at(3, 1), LIGHT_LEVEL_DIM)

        g.toggle_flashlight()                    # 开灯
        self.assertEqual(g.light_level_at(5, 1), LIGHT_LEVEL_DIM)
        self.assertEqual(g.light_level_at(3, 1), LIGHT_LEVEL_LIT)

    def test_flashlight_off_reverts_field(self):
        g = _make(_LONG, light=True, flashlight=True)
        g.px, g.py = 1, 1
        g.update_fov()
        lit_with = g.light_level_at(5, 1)        # 开灯：昏暗
        self.assertEqual(lit_with, LIGHT_LEVEL_DIM)
        g.toggle_flashlight()                    # 关灯
        lit_without = g.light_level_at(5, 1)     # 关灯：全黑
        self.assertEqual(lit_without, LIGHT_LEVEL_DARK)
        # 再开灯应精确还原
        g.toggle_flashlight()
        self.assertEqual(g.light_level_at(5, 1), lit_with)

    def test_flashlight_radius_greater_than_glow(self):
        self.assertGreater(FLASHLIGHT_RADIUS, PLAYER_GLOW_RADIUS)
        self.assertLess(FLASHLIGHT_RADIUS, ROOM_LIGHT_RADIUS)


class TestFlashlightPerception(unittest.TestCase):
    """手电的玩法效果：开灯让「微光照不到的远处怪」更易察觉你（仍只缩短、不放大，#9）。"""

    def test_flashlight_makes_distant_monster_see_you(self):
        # 长走廊、无房间：玩家微光半径 4 ⇒ 距离 4 处全黑（感知半径 2）；
        # 手电半径 6 ⇒ 同处贡献 6-4=2 → 昏暗（感知半径 4）⇒ 怪看得见你
        g = _make(_LONG, light=True, flashlight=False)
        g.px, g.py = 1, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 5, 1, hp=8, behavior="chase")  # 距离 4，视线通透
        sees_without = g.monster_can_see_player(m)   # 全黑：半径 2 < 4 ⇒ 看不见
        self.assertFalse(sees_without)
        g.flashlight_on = True
        g.update_fov()
        sees_with = g.monster_can_see_player(m)      # 昏暗：半径 4 ≥ 4 ⇒ 看得见
        self.assertTrue(sees_with)

    def test_flashlight_radius_never_exceeds_monster_base(self):
        # 手电只是把玩家周围照得更亮 ⇒ 怪所在格最多「明亮」⇒ 感知半径最多 base(7)
        g = _make(_LONG, light=True, flashlight=True)
        g.px, g.py = 1, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 6, 1, hp=8, behavior="chase")
        # 直接验证：被手电照亮 ⇒ 半径 = 满值，但仍 ≤ MONSTER_SIGHT_RADIUS
        radius = MONSTER_SIGHT_RADIUS
        if g.light_enabled:
            from rogue.light import monster_sight_radius
            radius = monster_sight_radius(g.light_level_at(m.x, m.y))
        self.assertLessEqual(radius, MONSTER_SIGHT_RADIUS)


class TestFlashlightSymmetry(unittest.TestCase):
    """不变量 #9 硬性质在手电下仍成立：怪看得见你 ⇒ 你看得见它。"""

    def test_flashlight_monster_sees_you_you_can_see(self):
        g = Game.procedural(RandomSource(seed=11), depth=1,
                            fov=True, stealth=True, light=True, flashlight=True)
        for _ in range(40):
            g.monster_turn()
            for m in g.monsters:
                if m.alive and g.monster_can_see_player(m):
                    self.assertTrue(g.is_visible(m.x, m.y),
                                    f"{m.name}@{m.x},{m.y} 看得见你、你却看不见它（手电下）")

    def test_flashlight_toggle_keeps_symmetry(self):
        g = Game.procedural(RandomSource(seed=7), depth=1,
                            fov=True, stealth=True, light=True, flashlight=True)
        for _ in range(30):
            g.monster_turn()
            g.toggle_flashlight()
            g.toggle_flashlight()        # 开关一对，状态回到原样
            for m in g.monsters:
                if m.alive and g.monster_can_see_player(m):
                    self.assertTrue(g.is_visible(m.x, m.y),
                                    "手电 toggle 后仍不得出现看不见的幽灵猎手")


class TestFlashlightDeterminism(unittest.TestCase):
    """手电零随机、确定性：toggle 不消耗 RandomSource、不改写玩法状态（#1/#2/#13）。"""

    def test_toggle_does_not_move_monsters(self):
        g = Game.procedural(RandomSource(seed=3), depth=1,
                            fov=True, stealth=True, light=True, flashlight=True)
        before = [(m.x, m.y) for m in g.monsters]
        g.toggle_flashlight()
        g.toggle_flashlight()
        after = [(m.x, m.y) for m in g.monsters]
        self.assertEqual(before, after)        # toggle 不推进任何怪物

    def test_toggle_reproducible_field(self):
        # 用无房间光源的长走廊，手电开/关才会真正改变光照场（程序化楼层多被房间灯照亮）
        g = _make(_LONG, light=True, flashlight=True)
        g.px, g.py = 1, 1
        g.update_fov()
        field_on = dict(g.light_field)
        g.toggle_flashlight()                    # 关灯
        field_off = dict(g.light_field)
        g.toggle_flashlight()                    # 开灯还原
        field_on_again = dict(g.light_field)
        self.assertNotEqual(field_on, field_off)       # 开/关确实不同
        self.assertEqual(field_on, field_on_again)      # 同状态 ⇒ 同场（确定性）

    def test_flashlight_off_matches_m11_field(self):
        # 装备手电但关灯 ⇒ 光照场应与「不装备手电（M11）」完全一致
        on_off = _make(_LONG, light=True, flashlight=True)
        on_off.px, on_off.py = 1, 1
        on_off.flashlight_on = False
        on_off.update_fov()
        m11 = _make(_LONG, light=True, flashlight=False)
        m11.px, m11.py = 1, 1
        m11.update_fov()
        self.assertEqual(on_off.light_field, m11.light_field)


class TestFlashlightRenderPurity(unittest.TestCase):
    """不变量 #8：手电只改变颜色，不改 render 字形（M1~M11 规格零侵入）。"""

    def test_render_glyphs_identical_flashlight_on_off(self):
        a = _make(_LONG, light=True, flashlight=True).render()
        b = _make(_LONG, light=True, flashlight=False).render()
        self.assertEqual(a, b)

    def test_render_glyphs_identical_with_light_off(self):
        # 手电默认关闭 ⇒ 即使传了 flashlight=True 也不影响字形
        a = _make(_LONG, flashlight=True).render()
        b = _make(_LONG, flashlight=False).render()
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
