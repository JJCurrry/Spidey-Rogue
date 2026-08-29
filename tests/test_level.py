"""M5 程序化关卡行为规格（对应工单 T-005 验收 A）。

核心红线覆盖：
- 不变量 #1 生成随机仅经 RandomSource（房间/走廊/起点/楼梯/撒点）
- 不变量 #2 同 seed + 同 depth ⇒ 同楼层、同怪、同道具
- 不变量 #4 外圈恒为墙、走廊与实体只在可通行格
- 不变量 #7 玩家起点可达全部可通行格（本单转正并补机器判定）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.game import (Game, MONSTER_TABLE, MONSTER_HP_PER_DEPTH,
                        MONSTERS_PER_ROOM_MAX, ITEM_KEYS)
from rogue.level import (generate_level, level_name_for_depth,
                         TUTORIAL_LEVEL_NAME, MAX_ROOMS, ROOM_MIN_W, ROOM_MIN_H)
from rogue.rng import RandomSource
from rogue.tiles import WALL, FLOOR, PLAYER, STAIRS


def _teleport(game: Game, x: int, y: int) -> None:
    """测试辅助：把玩家挪到指定格（绕过逐格移动，等价于走过去的最终状态）。"""
    game.grid[game.py][game.px] = FLOOR
    game.px, game.py = x, y
    game.grid[game.py][game.px] = PLAYER


class TestLevelStructure(unittest.TestCase):
    def setUp(self):
        self.lv = generate_level(RandomSource(seed=6), depth=1)

    def test_border_is_all_wall(self):
        # 不变量 #4：楼层外圈恒为墙，玩家不可能走出地图
        top = self.lv.grid[0]
        bottom = self.lv.grid[self.lv.height - 1]
        self.assertTrue(all(ch == WALL for ch in top))
        self.assertTrue(all(ch == WALL for ch in bottom))
        for y in range(self.lv.height):
            self.assertEqual(self.lv.grid[y][0], WALL)
            self.assertEqual(self.lv.grid[y][self.lv.width - 1], WALL)

    def test_start_and_stairs_are_walkable(self):
        self.assertTrue(self.lv.is_walkable(*self.lv.start))
        self.assertTrue(self.lv.is_walkable(*self.lv.stairs))
        self.assertNotEqual(self.lv.start, self.lv.stairs)

    def test_room_count_within_limit(self):
        self.assertGreaterEqual(len(self.lv.rooms), 1)
        self.assertLessEqual(len(self.lv.rooms), MAX_ROOMS)

    def test_rooms_do_not_overlap(self):
        for seed in range(10):
            lv = generate_level(RandomSource(seed=seed), depth=1)
            for i, a in enumerate(lv.rooms):
                for b in lv.rooms[i + 1:]:
                    self.assertFalse(a.intersects(b), f"seed={seed} 房间重叠")

    def test_room_tiles_are_carved(self):
        for room in self.lv.rooms:
            self.assertGreaterEqual(room.w, ROOM_MIN_W)
            self.assertGreaterEqual(room.h, ROOM_MIN_H)
            for (x, y) in room.tiles():
                self.assertTrue(self.lv.is_walkable(x, y), f"{x},{y} 未挖通")


class TestConnectivity(unittest.TestCase):
    """不变量 #7：玩家起点可达全部可通行格（本单的机器判定）。"""

    def test_all_walkable_reachable_from_start(self):
        for seed in range(30):
            depth = seed % 5 + 1
            lv = generate_level(RandomSource(seed=seed), depth=depth)
            reachable = lv.reachable_from(lv.start)
            self.assertEqual(len(reachable), len(lv.walkable_tiles()),
                             f"seed={seed} 存在不可达的地板")

    def test_level_selfcheck_connected(self):
        for seed in range(10):
            lv = generate_level(RandomSource(seed=seed), depth=seed % 3 + 1)
            self.assertTrue(lv.is_connected())

    def test_game_grid_has_no_sealed_pocket(self):
        # 生成后经过封填兜底，Game 侧的地板也应全部可达
        g = Game.procedural(RandomSource(seed=13), depth=2)
        seen = set()
        stack = [(g.px, g.py)]
        while stack:
            x, y = stack.pop()
            if (x, y) in seen or g.is_wall(x, y):
                continue
            seen.add((x, y))
            stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
        floors = [(x, y) for y in range(g.height) for x in range(g.width)
                  if not g.is_wall(x, y)]
        self.assertEqual(len(seen), len(floors))


class TestGenerationDeterminism(unittest.TestCase):
    def test_same_seed_same_level(self):
        a = generate_level(RandomSource(seed=99), depth=3)
        b = generate_level(RandomSource(seed=99), depth=3)
        self.assertEqual(["".join(r) for r in a.grid], ["".join(r) for r in b.grid])
        self.assertEqual(a.start, b.start)
        self.assertEqual(a.stairs, b.stairs)
        self.assertEqual([repr(r) for r in a.rooms], [repr(r) for r in b.rooms])

    def test_different_seed_different_level(self):
        a = generate_level(RandomSource(seed=1), depth=1)
        b = generate_level(RandomSource(seed=2), depth=1)
        self.assertNotEqual(["".join(r) for r in a.grid], ["".join(r) for r in b.grid])

    def test_populate_determinism(self):
        # 不变量 #2：同 seed ⇒ 同楼层 + 同怪 + 同道具
        def snapshot(seed):
            g = Game.procedural(RandomSource(seed=seed), depth=4)
            return (["".join(r) for r in g.grid],
                    [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                    [(i.key, i.x, i.y) for i in g.items])
        self.assertEqual(snapshot(21), snapshot(21))


class TestPopulate(unittest.TestCase):
    def setUp(self):
        self.g = Game.procedural(RandomSource(seed=11), depth=1)

    def test_entities_only_on_walkable_tiles(self):
        # 不变量 #4：撒怪撒道具不落在墙里、也不越界
        self.assertTrue(self.g.monsters)
        for m in self.g.monsters:
            self.assertTrue(self.g.in_bounds(m.x, m.y))
            self.assertFalse(self.g.is_wall(m.x, m.y))
        for it in self.g.items:
            self.assertTrue(self.g.in_bounds(it.x, it.y))
            self.assertFalse(self.g.is_wall(it.x, it.y))

    def test_nothing_stacked_on_player_or_stairs(self):
        taken = {(self.g.px, self.g.py), self.g.stairs}
        for m in self.g.monsters:
            self.assertNotIn((m.x, m.y), taken)
        for it in self.g.items:
            self.assertNotIn((it.x, it.y), taken)

    def test_no_monster_in_start_room(self):
        start_room = next(r for r in self.g.rooms if r.contains(self.g.px, self.g.py))
        for m in self.g.monsters:
            self.assertFalse(start_room.contains(m.x, m.y), "起始房间不该刷怪")

    def test_monster_count_within_rooms(self):
        rooms = len(self.g.rooms)
        self.assertGreater(len(self.g.monsters), 0)
        self.assertLessEqual(len(self.g.monsters), rooms * MONSTERS_PER_ROOM_MAX)

    def test_items_are_known_kinds(self):
        for it in self.g.items:
            self.assertIn(it.key, ITEM_KEYS)

    def test_populate_false_leaves_level_empty(self):
        lv = generate_level(RandomSource(seed=1), depth=1)
        g = Game(rng=RandomSource(seed=1), level=lv, populate=False)
        self.assertEqual(g.monsters, [])
        self.assertEqual(g.items, [])

    def test_depth_one_only_unlocks_basic_monsters(self):
        g = Game.procedural(RandomSource(seed=3), depth=1)
        names = {m.name for m in g.monsters}
        self.assertTrue(names.issubset({"街头小混混", "迷途无人机"}))

    def test_monster_hp_grows_with_depth(self):
        base = {k.name: k.hp for k in MONSTER_TABLE}
        g1 = Game.procedural(RandomSource(seed=5), depth=1)
        for m in g1.monsters:
            self.assertEqual(m.hp, base[m.name])
        g5 = Game.procedural(RandomSource(seed=5), depth=5)
        for m in g5.monsters:
            self.assertEqual(m.hp, base[m.name] + 4 * MONSTER_HP_PER_DEPTH)


class TestStairsAndDescend(unittest.TestCase):
    def test_tutorial_map_has_no_stairs(self):
        g = Game(rng=RandomSource(seed=0))
        self.assertIsNone(g.stairs)
        self.assertFalse(g.can_descend())
        self.assertFalse(g.descend())
        self.assertEqual(g.depth, 1)

    def test_can_descend_only_on_stairs(self):
        g = Game.procedural(RandomSource(seed=2), depth=1)
        self.assertFalse(g.can_descend())
        _teleport(g, *g.stairs)
        self.assertTrue(g.can_descend())

    def test_render_shows_stairs(self):
        g = Game.procedural(RandomSource(seed=4), depth=1)
        self.assertIn(STAIRS, g.render())

    def test_descend_goes_one_level_deeper(self):
        g = Game.procedural(RandomSource(seed=7), depth=1)
        name1 = g.level_name
        _teleport(g, *g.stairs)
        self.assertTrue(g.descend())
        self.assertEqual(g.depth, 2)
        self.assertNotEqual(g.level_name, name1)
        self.assertEqual(g.level_name, level_name_for_depth(2))

    def test_descend_keeps_player_state(self):
        g = Game.procedural(RandomSource(seed=8), depth=1)
        g.player_hp = 7
        g.player_dmg_bonus = 2
        g.spawn_item("sandwich", g.px, g.py)
        g.pick_up()
        _teleport(g, *g.stairs)
        self.assertTrue(g.descend())
        # HP / 背包 / 纳米加成跨层保留
        self.assertEqual(g.player_hp, 7)
        self.assertEqual(g.player_dmg_bonus, 2)
        self.assertEqual([it.key for it in g.inventory], ["sandwich"])

    def test_descend_resets_map_and_entities(self):
        g = Game.procedural(RandomSource(seed=9), depth=1)
        old_monsters = list(g.monsters)
        old_items = list(g.items)
        _teleport(g, *g.stairs)
        self.assertTrue(g.descend())
        self.assertTrue(g.monsters)
        self.assertFalse(any(m in g.monsters for m in old_monsters))
        self.assertFalse(any(i in g.items for i in old_items))
        self.assertTrue(g.stairs is not None)
        self.assertFalse(g.can_descend())  # 新楼层起点不在楼梯上


class TestLevelNaming(unittest.TestCase):
    def test_depth_name_mapping(self):
        self.assertEqual(level_name_for_depth(1), "皇后区地铁隧道")
        self.assertEqual(level_name_for_depth(2), "奥斯本大厦底层")
        self.assertEqual(level_name_for_depth(10), "蜥蜴人的地下巢穴")

    def test_name_cycles_after_ten(self):
        self.assertEqual(level_name_for_depth(11), level_name_for_depth(1))

    def test_game_carries_level_name(self):
        g = Game.procedural(RandomSource(seed=1), depth=3)
        self.assertEqual(g.depth, 3)
        self.assertEqual(g.level_name, level_name_for_depth(3))
        tutorial = Game(rng=RandomSource(seed=1))
        self.assertEqual(tutorial.level_name, TUTORIAL_LEVEL_NAME)


if __name__ == "__main__":
    unittest.main()
