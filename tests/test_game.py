"""M1 行为规格（对应工单 T-001 验收 A）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.game import Game
from rogue.rng import RandomSource


class TestSeedDeterminism(unittest.TestCase):
    def test_same_seed_same_sequence(self):
        a = RandomSource(seed=7)
        b = RandomSource(seed=7)
        self.assertEqual([a.int(0, 100) for _ in range(5)],
                         [b.int(0, 100) for _ in range(5)])

    def test_different_seed_differs(self):
        a = RandomSource(seed=1)
        b = RandomSource(seed=2)
        self.assertNotEqual(a.int(0, 1000), b.int(0, 1000))


class TestGridAndMovement(unittest.TestCase):
    def setUp(self):
        self.g = Game(rng=RandomSource(seed=0))

    def test_player_initial_position(self):
        # 地图第 1 行 "#@....#" → 玩家在 (1,1)
        self.assertEqual((self.g.px, self.g.py), (1, 1))
        self.assertEqual(self.g.tile_at(1, 1), "@")

    def test_move_into_floor(self):
        ok = self.g.move(1, 0)  # 向右进入地板
        self.assertTrue(ok)
        self.assertEqual((self.g.px, self.g.py), (2, 1))

    def test_move_blocked_by_wall(self):
        g = Game(rng=RandomSource(seed=0))
        g.move(1, 0)  # (2,1)
        g.move(1, 0)  # (3,1)
        g.move(1, 0)  # (4,1)
        g.move(1, 0)  # (5,1)
        ok = g.move(1, 0)  # (6,1) 是墙 '#'
        self.assertFalse(ok)
        self.assertEqual((g.px, g.py), (5, 1))

    def test_move_blocked_out_of_bounds(self):
        g = Game(rng=RandomSource(seed=0))
        ok = g.move(-1, 0)  # 向左越界
        self.assertFalse(ok)
        self.assertEqual((g.px, g.py), (1, 1))

    def test_render_shows_player(self):
        self.assertIn("@", self.g.render())


if __name__ == "__main__":
    unittest.main()
