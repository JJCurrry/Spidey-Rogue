"""M20 光照影响蜘蛛感应半径（对应工单 T-020 验收 A）。

核心红线覆盖：
- 不变量 #1 蜘蛛感应半径衰减是纯几何计算，不消耗 RandomSource（也不引入随机模块）
- 不变量 #2 同状态 ⇒ 同感应集合（确定性）
- 不变量 #8 render() 不改写地形 / 玩家 / 怪物 / 道具状态（含光照开启时）
- 不变量 #9 对称硬性质：蜘蛛感应半径只缩短不放大（恒 ≤ SPIDER_SENSE_RADIUS），
  与 M11 怪物感知、M13 玩家视野形成「黑暗三重削弱」对称
- 不变量 #20（新增）：光照开启时蜘蛛感应半径随目标格光照衰减（暗 2 / 昏暗 3 / 明 4）；
  光照关闭时半径恒为 SPIDER_SENSE_RADIUS（与 M1~M19 逐字节一致，零回归）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.fov import (SPIDER_SENSE_RADIUS, in_spider_sense, spider_sense_radius)
from rogue.game import Game
from rogue.level import Level, Room
from rogue.rng import RandomSource
from rogue.tiles import WALL, FLOOR, PLAYER, SENSE
from rogue.light import (LIGHT_LEVEL_DARK, LIGHT_LEVEL_DIM, LIGHT_LEVEL_LIT)

# 测试用图（'@' 只是标注起点，交给 Game 自己落笔）
_CORRIDOR = [
    "###########",   # 宽 11、无房间 ⇒ 只有玩家微光照亮附近，远处走廊全黑
    "#@........#",
    "###########",
]
_ROOM = [
    "#######",       # 宽 7、高 5，内部 5×3；房间中心固定灯把整间照成 LIT
    "#.....#",
    "#.....#",
    "#.....#",
    "#######",
]
_BLOCKED = [
    "#########",     # 玩家(1,1)、墙(2,1)挡视线；墙后 (5,1) 距 4 且不可见 ⇒ 只能靠蜘蛛感应 `?`
    "#@#.....#",
    "#########",
]


def _make(rows, start=(1, 1), rooms=(), fov=True, light=True, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，测蜘蛛感应本身）。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, (-1, -1), 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, light=light)


class TestSpiderSenseRadiusFn(unittest.TestCase):
    """fov.spider_sense_radius 纯函数：档位映射 + 只缩短不放大。"""

    def test_dark_returns_2(self):
        self.assertEqual(spider_sense_radius(LIGHT_LEVEL_DARK), 2)

    def test_dim_returns_3(self):
        self.assertEqual(spider_sense_radius(LIGHT_LEVEL_DIM), 3)

    def test_lit_returns_4(self):
        self.assertEqual(spider_sense_radius(LIGHT_LEVEL_LIT), SPIDER_SENSE_RADIUS)

    def test_negative_clamped_to_dark(self):
        self.assertEqual(spider_sense_radius(-5), 2)

    def test_never_exceeds_base(self):
        for lvl in range(-3, 6):
            self.assertLessEqual(spider_sense_radius(lvl), SPIDER_SENSE_RADIUS)

    def test_only_shortens_not_amplifies(self):
        # 暗 / 昏暗档位必须严格小于恒亮档位（只缩短、不放大）
        self.assertLess(spider_sense_radius(LIGHT_LEVEL_DARK), SPIDER_SENSE_RADIUS)
        self.assertLess(spider_sense_radius(LIGHT_LEVEL_DIM), SPIDER_SENSE_RADIUS)
        self.assertEqual(spider_sense_radius(LIGHT_LEVEL_LIT), SPIDER_SENSE_RADIUS)

    def test_tiers_ordered(self):
        # 越亮感应半径越大（暗 < 昏暗 < 明）
        self.assertLess(spider_sense_radius(LIGHT_LEVEL_DARK),
                        spider_sense_radius(LIGHT_LEVEL_DIM))
        self.assertLess(spider_sense_radius(LIGHT_LEVEL_DIM),
                        spider_sense_radius(LIGHT_LEVEL_LIT))


class TestSpiderSenseLightOff(unittest.TestCase):
    """光照关闭 ⇒ 半径恒为 SPIDER_SENSE_RADIUS，与 M1~M19 逐字节一致（零回归）。"""

    def test_light_defaults_off(self):
        self.assertFalse(Game(rng=RandomSource(0)).light_enabled)
        self.assertFalse(Game.procedural(RandomSource(0), depth=1).light_enabled)

    def test_light_off_senses_at_radius_4(self):
        g = _make(_CORRIDOR, light=False)
        g.spawn_monster("街头小混混", 5, 1, 8)   # 切比雪夫距离 4
        self.assertEqual(len(g.spider_sense()), 1)

    def test_light_off_does_not_sense_beyond(self):
        g = _make(_CORRIDOR, light=False)
        g.spawn_monster("街头小混混", 8, 1, 8)   # 切比雪夫距离 7
        self.assertEqual(g.spider_sense(), [])

    def test_light_off_uses_constant_regardless_of_cell(self):
        g = _make(_CORRIDOR, light=False)
        g.spawn_monster("街头小混混", 1, 1, 8)   # 同格
        g.spawn_monster("迷途无人机", 4, 1, 8)   # 距离 3
        g.spawn_monster("街头小混混", 9, 1, 8)   # 距离 8（超出）
        coords = {(m.x, m.y) for m in g.spider_sense()}
        self.assertIn((1, 1), coords)
        self.assertIn((4, 1), coords)
        self.assertNotIn((9, 1), coords)

    def test_light_off_skips_dead(self):
        g = _make(_CORRIDOR, light=False)
        m = g.spawn_monster("街头小混混", 3, 1, 8)
        m.hp = 0
        self.assertEqual(g.spider_sense(), [])

    def test_light_off_matches_in_spider_sense_constant(self):
        g = _make(_CORRIDOR, light=False)
        g.spawn_monster("街头小混混", 4, 1, 8)
        manual = [m for m in g.monsters
                  if m.alive and in_spider_sense((g.px, g.py), (m.x, m.y), SPIDER_SENSE_RADIUS)]
        self.assertEqual({(m.x, m.y) for m in g.spider_sense()},
                         {(m.x, m.y) for m in manual})


class TestSpiderSenseLightOn(unittest.TestCase):
    """光照开启 ⇒ 感应半径随目标格光照衰减（暗 2 / 昏暗 3 / 明 4）。"""

    def test_light_on_lit_room_full_radius(self):
        room = Room(1, 1, 5, 3)
        g = _make(_ROOM, start=(1, 1), rooms=[room], light=True)
        g.update_light()
        g.spawn_monster("街头小混混", 5, 3, 8)   # 房内、距玩家 4，整间 LIT ⇒ 半径 4 ⇒ 感得到
        self.assertEqual(len(g.spider_sense()), 1)

    def test_light_on_dark_corridor_edge_not_sensed(self):
        g = _make(_CORRIDOR, light=True)
        g.update_light()
        g.spawn_monster("街头小混混", 5, 1, 8)   # 距 4、无房间灯、超出微光 ⇒ 全黑 ⇒ 半径 2 ⇒ 感不到
        self.assertEqual(g.spider_sense(), [])

    def test_light_off_same_monster_sensed(self):
        # 与上一例同一只怪：关灯则恒半径 4 ⇒ 感得到（零回归对照）
        g = _make(_CORRIDOR, light=False)
        g.spawn_monster("街头小混混", 5, 1, 8)
        self.assertEqual(len(g.spider_sense()), 1)

    def test_light_on_dark_corridor_near_sensed(self):
        g = _make(_CORRIDOR, light=True)
        g.update_light()
        g.spawn_monster("街头小混混", 3, 1, 8)   # 距 2，微光 DIM ⇒ 半径 3 ⇒ 感得到
        self.assertEqual(len(g.spider_sense()), 1)

    def test_light_on_attenuates_vs_off_at_edge(self):
        # 同一只距 4 的怪：开灯(全黑)不感、关灯(恒 4)感
        g_on = _make(_CORRIDOR, light=True)
        g_on.update_light()
        g_on.spawn_monster("街头小混混", 5, 1, 8)
        g_off = _make(_CORRIDOR, light=False)
        g_off.spawn_monster("街头小混混", 5, 1, 8)
        self.assertEqual(g_on.spider_sense(), [])
        self.assertEqual(len(g_off.spider_sense()), 1)

    def test_per_monster_radius_in_same_game(self):
        # 同一局里：近处怪(微光 DIM 半径3)感得到、远处怪(全黑 半径2)感不到
        g = _make(_CORRIDOR, light=True)
        g.update_light()
        g.spawn_monster("街头小混混", 3, 1, 8)   # 距 2，DIM 半径 3 ⇒ 感得到
        g.spawn_monster("迷途无人机", 5, 1, 8)   # 距 4，DARK 半径 2 ⇒ 感不到
        coords = {(m.x, m.y) for m in g.spider_sense()}
        self.assertIn((3, 1), coords)
        self.assertNotIn((5, 1), coords)

    def test_dim_tier_reduces_sensing(self):
        # 白盒：手动把目标格标成 DIM，验证整合路径真的用了档位映射
        g = _make(_CORRIDOR, light=True)
        g.light_enabled = True
        g.light_field = {(5, 1): LIGHT_LEVEL_DIM}
        g.spawn_monster("街头小混混", 5, 1, 8)   # 距 4，DIM ⇒ 半径 3 ⇒ 4>3 感不到
        self.assertEqual(g.spider_sense(), [])
        g2 = _make(_CORRIDOR, light=True)
        g2.light_enabled = True
        g2.light_field = {(3, 1): LIGHT_LEVEL_DIM}
        g2.spawn_monster("迷途无人机", 3, 1, 8)  # 距 2，DIM ⇒ 半径 3 ⇒ 2≤3 感得到
        self.assertEqual(len(g2.spider_sense()), 1)

    def test_total_darkness_keeps_min_radius_2(self):
        # 全黑时仍保留最小半径 2，避免彻底无预警
        g = _make(_CORRIDOR, light=True)
        g.light_enabled = True
        g.light_field = {(2, 1): LIGHT_LEVEL_DARK}
        g.spawn_monster("街头小混混", 2, 1, 8)   # 距 1 ≤ 2 ⇒ 感得到
        g.spawn_monster("迷途无人机", 3, 1, 8)   # 距 2 ≤ 2 ⇒ 感得到
        g.spawn_monster("街头小混混", 4, 1, 8)   # 距 3 > 2 ⇒ 感不到
        coords = {(m.x, m.y) for m in g.spider_sense()}
        self.assertIn((2, 1), coords)
        self.assertIn((3, 1), coords)
        self.assertNotIn((4, 1), coords)

    def test_light_must_be_enabled_for_attenuation(self):
        # 即便场里写着暗，只要 light_enabled=False，仍走恒常量（M1~M19 行为）
        g = _make(_CORRIDOR, light=False)
        g.light_field = {(5, 1): LIGHT_LEVEL_DARK}  # 不生效
        g.spawn_monster("街头小混混", 5, 1, 8)   # 距 4，应被恒半径 4 感得到
        self.assertEqual(len(g.spider_sense()), 1)


class TestSpiderSenseLightRender(unittest.TestCase):
    """渲染层：开灯后暗处威胁不再画 `?`；关灯仍画 `?`（零回归）。"""

    def test_light_on_dark_monster_no_sense_glyph(self):
        # 墙后距 4 的怪：开灯(全黑)感应半径缩到 2 ⇒ 不感 ⇒ 不画 `?`
        g = _make(_BLOCKED, light=True, fov=True)
        g.update_light()
        g.spawn_monster("街头小混混", 5, 1, 8)
        self.assertNotIn(SENSE, g.render())

    def test_light_off_same_monster_shows_sense_glyph(self):
        # 同一只墙后距 4 的怪：关灯恒半径 4 ⇒ 感得到 ⇒ 画 `?`（零回归对照）
        g = _make(_BLOCKED, light=False, fov=True)
        g.spawn_monster("街头小混混", 5, 1, 8)
        self.assertIn(SENSE, g.render())

    def test_render_purity_with_light(self):
        # 不变量 #8：光照开启时 render() 仍不改写 world state
        g = Game.procedural(RandomSource(seed=19), depth=1, fov=True, light=True)
        g.spawn_item("sandwich", g.px, g.py)
        before = (["".join(r) for r in g.grid],
                  [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                  g.player_hp, g.depth, (g.px, g.py))
        g.render()
        g.render()
        after = (["".join(r) for r in g.grid],
                 [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                 g.player_hp, g.depth, (g.px, g.py))
        self.assertEqual(before, after)


class TestSpiderSenseDeterminism(unittest.TestCase):
    """不变量 #2：同 seed + 同输入 ⇒ 同感应集合；且不消耗 RandomSource。"""

    def test_same_seed_same_result(self):
        def sensed():
            g = Game.procedural(RandomSource(seed=19), depth=1, fov=True, light=True)
            g.update_light()
            return {(m.x, m.y) for m in g.spider_sense()}
        self.assertEqual(sensed(), sensed())

    def test_spider_sense_does_not_consume_rng(self):
        g = Game.procedural(RandomSource(seed=19), depth=1, fov=True, light=True)
        g.update_light()
        before = g.rng._rng.getstate()
        g.spider_sense()
        g.spider_sense()
        after = g.rng._rng.getstate()
        self.assertEqual(before, after)

    def test_sense_radius_smaller_than_sight_preserved(self):
        # 即便明亮档（=SPIDER_SENSE_RADIUS=4），仍小于视野半径 8——预警不是透视
        from rogue.fov import SIGHT_RADIUS
        self.assertLess(SPIDER_SENSE_RADIUS, SIGHT_RADIUS)
        self.assertLess(spider_sense_radius(LIGHT_LEVEL_LIT), SIGHT_RADIUS)


if __name__ == "__main__":
    unittest.main()
