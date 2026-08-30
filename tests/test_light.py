"""M11 光照衰减（明暗梯度 + 暗处降低怪物感知半径）规格。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（光照纯几何、不引入随机模块）
- 不变量 #2 回合确定性（光照只依赖 grid + 光源 ⇒ 同状态同场，不消耗 rng）
- 不变量 #8 渲染纯净性（光照只经由 colorize 上色，不改 render 字形）
- 不变量 #9 延伸：暗处只缩短怪物感知半径（恒 ≤ MONSTER_SIGHT_RADIUS），
  所以「怪看得见你 ⇒ 你看得见它」的硬性质不被破坏
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.light import (ROOM_LIGHT_RADIUS, PLAYER_GLOW_RADIUS,
                         LIGHT_LEVEL_DARK, LIGHT_LEVEL_DIM, LIGHT_LEVEL_LIT,
                         light_contribution, light_level, light_field,
                         monster_sight_radius)
from rogue.fov import MONSTER_SIGHT_RADIUS
from rogue.game import Game
from rogue.level import Level, Room
from rogue.rng import RandomSource
from rogue.tiles import WALL, FLOOR, PLAYER

# 测试地图（'@' 仅标注起点，交给 Game 落笔；无房间 ⇒ 无房间光，只有玩家微光）
# 长走廊（无房间）：用于验证「远离玩家微光 = 全黑」与「靠近 = 被照亮」
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
          light=False, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，只测光照与感知）。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, _NO_STAIRS, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth, light=light)


def _open_field(width=25, height=9):
    return (["#" * width]
            + ["#" + FLOOR * (width - 2) + "#"] * (height - 2)
            + ["#" * width])


class TestLightGeometry(unittest.TestCase):
    """light.py 纯几何、零随机（不变量 #1/#2/#8）。"""

    def test_light_contribution_zero_beyond_radius(self):
        grid = [list(r) for r in _open_field(width=9)]
        # 光源半径 3，距离 4 ⇒ 照不到
        self.assertEqual(light_contribution(grid, (1, 1, 3), (1, 5)), 0)

    def test_light_contribution_blocked_by_wall(self):
        # (1,1) 到 (1,4) 之间 (1,2) 是一堵墙 ⇒ 光遇墙即断
        grid = [list(r) for r in [
            "#######",
            "#@#...#",
            "#######",
        ]]
        self.assertEqual(light_contribution(grid, (1, 1, 5), (1, 4)), 0)

    def test_light_contribution_falloff(self):
        grid = [list(r) for r in _open_field(width=9)]
        # 半径 5：脚下贡献 5，距离 2 贡献 3，随距离线性衰减
        self.assertEqual(light_contribution(grid, (1, 1, 5), (1, 1)), 5)
        self.assertEqual(light_contribution(grid, (1, 1, 5), (1, 3)), 3)
        self.assertGreater(light_contribution(grid, (1, 1, 5), (1, 1)),
                           light_contribution(grid, (1, 1, 5), (1, 3)))

    def test_light_level_dark_when_far_from_all_sources(self):
        grid = [list(r) for r in _open_field(width=13)]
        # 没有任何光源覆盖到 (10,4) ⇒ 全黑
        self.assertEqual(light_level(grid, [], (10, 4)), LIGHT_LEVEL_DARK)

    def test_light_level_lit_near_source(self):
        grid = [list(r) for r in _open_field(width=13)]
        # 光源中心处贡献 = 半径 ⇒ 明亮
        self.assertEqual(light_level(grid, [(6, 4, 6)], (6, 4)), LIGHT_LEVEL_LIT)

    def test_light_level_dim_in_between(self):
        grid = [list(r) for r in _open_field(width=13)]
        # 半径 5、距离 3 ⇒ 贡献 2 ⇒ 昏暗（介于全黑与明亮之间）
        self.assertEqual(light_level(grid, [(6, 4, 5)], (9, 4)), LIGHT_LEVEL_DIM)

    def test_light_field_covers_grid(self):
        grid = [list(r) for r in _open_field(width=11, height=7)]
        field = light_field(grid, [(5, 3, 6)])
        self.assertEqual(len(field), 11 * 7)

    def test_light_field_deterministic(self):
        grid = [list(r) for r in _open_field(width=11, height=7)]
        sources = [(5, 3, 6)]
        self.assertEqual(light_field(grid, sources), light_field(grid, sources))


class TestMonsterSightDecay(unittest.TestCase):
    """暗处怪物感知半径衰减（不变量 #9 延伸：只缩短、不放大）。"""

    def test_monster_sight_radius_buckets(self):
        self.assertEqual(monster_sight_radius(LIGHT_LEVEL_DARK), 2)
        self.assertEqual(monster_sight_radius(LIGHT_LEVEL_DIM), 4)
        self.assertEqual(monster_sight_radius(LIGHT_LEVEL_LIT), MONSTER_SIGHT_RADIUS)

    def test_monster_sight_radius_never_exceeds_base(self):
        # 任何光照等级都不会让怪物看得比「明亮」更远 ⇒ 对称硬性质不破
        for lvl in (LIGHT_LEVEL_DARK, LIGHT_LEVEL_DIM, LIGHT_LEVEL_LIT):
            self.assertLessEqual(monster_sight_radius(lvl), MONSTER_SIGHT_RADIUS)
        # 自定义的更大 base 也不会被放大
        self.assertLessEqual(monster_sight_radius(LIGHT_LEVEL_LIT, base=7), 7)


class TestLightSwitch(unittest.TestCase):
    """光照是可选开关：默认关闭 ⇒ M1~M10 一字节不变。"""

    def test_light_disabled_by_default(self):
        self.assertFalse(Game(rng=RandomSource(seed=0)).light_enabled)
        self.assertFalse(Game.procedural(RandomSource(seed=0), depth=1).light_enabled)

    def test_light_enabled_when_asked(self):
        self.assertTrue(_make(_LONG, light=True).light_enabled)
        self.assertTrue(Game(rng=RandomSource(seed=0), light=True).light_enabled)
        self.assertTrue(Game.procedural(RandomSource(seed=0), depth=1,
                                        light=True).light_enabled)


class TestLightAwareness(unittest.TestCase):
    """暗处怪物感知半径被缩短（纯几何、零随机）。"""

    def test_monster_in_dark_has_reduced_radius(self):
        # 长走廊、无房间：玩家微光半径 4，怪在距离 6 处 ⇒ 全黑，只看 2 格看不见
        g = _make(_LONG, light=True)
        g.px, g.py = 1, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 7, 1, hp=8, behavior="chase")
        self.assertFalse(g.monster_can_see_player(m))
        # 玩家贴近到距离 1 ⇒ 怪脚下被照亮（明亮）⇒ 半径恢复 7，看得见
        g.px, g.py = 6, 1
        g.update_fov()
        self.assertTrue(g.monster_can_see_player(m))

    def test_passive_glow_does_not_light_monster(self):
        # M18：玩家被动微光**不再**照亮暗处怪——无房间、无手电、怪在微光半径内（距离 3）
        # ⇒ 怪所在格在怪物感知光场里仍是全黑（被动微光被排除）⇒ 半径缩短为 2 < 3 ⇒ 看不见
        g = _make(_LONG, light=True)
        g.px, g.py = 1, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 4, 1, hp=8, behavior="chase")
        self.assertEqual(g.monster_light_level_at(4, 1), LIGHT_LEVEL_DARK)
        self.assertFalse(g.monster_can_see_player(m))
        # 但主动打出手电（半径 6）会照亮距离 3 处 ⇒ 该怪看得见你（手电是主动光，保留 M12 双刃）
        g.flashlight_on = True
        g.update_fov()
        self.assertEqual(g.monster_light_level_at(4, 1), LIGHT_LEVEL_LIT)
        self.assertTrue(g.monster_can_see_player(m))

    def test_monster_in_lit_room_full_radius(self):
        # 房间中心有固定灯 ⇒ 房间里始终明亮 ⇒ 满半径
        room = Room(1, 1, 10, 1)
        g = _make(_ROOM, start=(1, 1), rooms=[room], light=True)
        m = g.spawn_monster("街头小混混", 10, 1, hp=8, behavior="chase")
        self.assertTrue(room.contains(g.px, g.py) and room.contains(m.x, m.y))
        self.assertTrue(g.monster_can_see_player(m))

    def test_same_room_always_seen_with_light(self):
        # 同房间（无视半径）⇒ 即使把房间灯调暗也看得见（房间照明独立于光源衰减）
        room = Room(1, 1, 10, 1)
        g = _make(_ROOM, start=(1, 1), rooms=[room], light=True)
        m = g.spawn_monster("街头小混混", 10, 1, hp=8, behavior="chase")
        # 直接验证同房间覆盖：即便把怪挪到距离 7 处仍被同房间规则判定为可见
        self.assertTrue(g.monster_can_see_player(m))

    def test_light_off_keeps_full_radius(self):
        # 光照关闭 ⇒ 感知半径恒满，距离 5 仍可见（控制组）
        g = _make(_LONG, light=False)
        g.px, g.py = 1, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 6, 1, hp=8, behavior="chase")
        self.assertTrue(g.monster_can_see_player(m))

    def test_adjacent_always_seen_in_dark(self):
        # 相邻格（距离 1）即便在全黑处（半径 2）也看得见（M3 相邻即被发现不破）
        g = _make(_LONG, light=True)
        g.px, g.py = 1, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 7, 1, hp=8, behavior="chase")
        self.assertFalse(g.monster_can_see_player(m))   # 远处全黑看不见
        g.px, g.py = 6, 1
        g.update_fov()
        self.assertTrue(g.monster_can_see_player(m))    # 贴近后看得见

    def test_dark_monster_not_alerted_until_close(self):
        # 潜行 + 光照：暗处的怪在远处不惊动，贴近才被发现
        g = _make(_LONG, light=True)
        g.px, g.py = 1, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 7, 1, hp=8, behavior="chase")
        g.update_awareness()
        self.assertFalse(m.alerted)          # 远处全黑：没发现你
        g.px, g.py = 6, 1
        g.update_fov()
        g.update_awareness()
        self.assertTrue(m.alerted)           # 贴近被照亮：发现了

    def test_update_awareness_idempotent_with_light(self):
        g = _make(_LONG, light=True)
        g.px, g.py = 6, 1
        g.update_fov()
        m = g.spawn_monster("街头小混混", 7, 1, hp=8, behavior="chase")
        g.update_awareness()
        first = m.alerted
        g.update_awareness()
        self.assertEqual(m.alerted, first)   # 幂等


class TestLightSymmetry(unittest.TestCase):
    """不变量 #9 硬性质在光照下仍成立：怪看得见你 ⇒ 你看得见它。"""

    def test_light_monster_sees_you_you_can_see(self):
        g = Game.procedural(RandomSource(seed=11), depth=1,
                             fov=True, stealth=True, light=True)
        for _ in range(40):
            g.monster_turn()
            for m in g.monsters:
                if m.alive and g.monster_can_see_player(m):
                    self.assertTrue(g.is_visible(m.x, m.y),
                                    f"{m.name}@{m.x},{m.y} 看得见你、你却看不见它")


class TestLightSources(unittest.TestCase):
    """光源构成：房间中心固定灯 + 玩家随身微光（仅光照开启时）。"""

    def test_light_sources_include_room_centers(self):
        room = Room(1, 1, 8, 3)
        g = _make(_ROOM, start=(1, 1), rooms=[room], light=True)
        sources = g._light_sources()
        self.assertIn((room.center[0], room.center[1], ROOM_LIGHT_RADIUS), sources)

    def test_player_glow_only_when_enabled(self):
        room = Room(1, 1, 8, 3)
        on = _make(_ROOM, start=(1, 1), rooms=[room], light=True)
        off = _make(_ROOM, start=(1, 1), rooms=[room], light=False)
        self.assertIn((on.px, on.py, PLAYER_GLOW_RADIUS), on._light_sources())
        self.assertNotIn((off.px, off.py, PLAYER_GLOW_RADIUS), off._light_sources())


class TestRenderPurity(unittest.TestCase):
    """不变量 #8：光照只改变颜色，不改 render 字形（M1~M10 规格零侵入）。"""

    def test_render_glyphs_identical_with_light(self):
        a = _make(_LONG, light=True).render()
        b = _make(_LONG, light=False).render()
        self.assertEqual(a, b)

    def test_light_level_at_lit_when_disabled(self):
        # 光照关闭 ⇒ 任何格都按「明亮」处理，不改变行为
        g = _make(_LONG, light=False)
        self.assertEqual(g.light_level_at(5, 1), LIGHT_LEVEL_LIT)


class TestColorGradient(unittest.TestCase):
    """M11 明暗梯度：colorize 按光照压暗地形，实体字形不变。"""

    def test_colorize_dim_dark_floor(self):
        from rogue.color import colorize, DARK
        text = ".."
        res = colorize(text, True,
                       light={(0, 0): LIGHT_LEVEL_DARK, (1, 0): LIGHT_LEVEL_LIT},
                       width=2)
        # 全黑格被压暗（带 DARK 转义 + 复位），明亮格保持原样（无转义、出现在结尾）
        self.assertIn(DARK, res)
        self.assertEqual(res.count(DARK), 1)        # 只有一处被压暗
        self.assertEqual(res.count("\033[0m"), 1)   # 仅一次复位
        self.assertTrue(res.endswith("."))           # 明亮格是裸 '.'（未上色）

    def test_colorize_entities_not_dimmed(self):
        from rogue.color import colorize
        res = colorize("@M", True,
                       light={(0, 0): LIGHT_LEVEL_DARK, (1, 0): LIGHT_LEVEL_DARK},
                       width=2)
        # 实体字形保持各自颜色，不被压暗
        self.assertIn("\033[1;31m", res)   # @ 红
        self.assertIn("\033[1;35m", res)   # M 品红
        self.assertNotIn("\033[90m", res)  # 没有暗灰压暗

    def test_colorize_light_none_legacy(self):
        from rogue.color import colorize
        # 不带光照场 ⇒ 地板原样返回，不带任何转义
        self.assertEqual(colorize(".", True), ".")


if __name__ == "__main__":
    unittest.main()
