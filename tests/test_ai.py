"""M3 怪物 AI 行为规格（对应工单 T-003 验收 A）。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（随机游走的方向选择走 self.rng）
- 不变量 #2 回合确定性（相同 seed + 相同布置 ⇒ 相同 AI 结果）
- 不变量 #4 怪物 AI 不可越界 / 穿墙 / 踩玩家 / 踩其它怪物
- 不变量 #3 怪物攻击玩家时 HP 永不为负（_hurt_player 钳制）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.game import Game, Monster
from rogue.rng import RandomSource


def manhattan(g: Game, m: Monster) -> int:
    return abs(m.x - g.px) + abs(m.y - g.py)


class TestMonsterChase(unittest.TestCase):
    def setUp(self):
        self.g = Game(rng=RandomSource(seed=0))
        self.m = self.g.spawn_monster("街头小混混", 4, 3, hp=12, attack=3, behavior="chase")

    def test_chase_reduces_distance(self):
        before = manhattan(self.g, self.m)
        self.g.monster_turn()
        self.assertLess(manhattan(self.g, self.m), before)

    def test_chase_does_not_enter_wall(self):
        for _ in range(10):
            self.g.monster_turn()
            self.assertFalse(self.g.is_wall(self.m.x, self.m.y))
            self.assertTrue(self.g.in_bounds(self.m.x, self.m.y))

    def test_chase_eventually_attacks_player(self):
        hp0 = self.g.player_hp
        for _ in range(8):
            self.g.monster_turn()
        self.assertLess(self.g.player_hp, hp0)  # 追到相邻后开始反击


class TestMonsterAttack(unittest.TestCase):
    def test_adjacent_monster_attacks(self):
        g = Game(rng=RandomSource(seed=0))
        m = g.spawn_monster("街头小混混", 2, 1, hp=12, attack=3, behavior="chase")
        # (2,1) 与玩家 (1,1) 相邻（切比雪夫距离 1）
        self.assertTrue(g.is_adjacent(2, 1))
        before = g.player_hp
        g.monster_turn()
        self.assertEqual(g.player_hp, before - 3)

    def test_monster_never_enters_player_tile(self):
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("街头小混混", 2, 1, hp=12, attack=3, behavior="chase")
        for _ in range(5):
            g.monster_turn()
            self.assertNotEqual((g.monsters[0].x, g.monsters[0].y), (g.px, g.py))

    def test_player_hp_never_negative_from_monster(self):
        # 不变量 #3：怪物超额伤害下玩家 HP 永不为负
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("重击者", 2, 1, hp=100, attack=999, behavior="chase")
        for _ in range(20):
            g.monster_turn()
        self.assertEqual(g.player_hp, 0)
        self.assertTrue(g.player_dead)


class TestOccupancy(unittest.TestCase):
    def test_two_monsters_never_overlap(self):
        # 不变量 #4：AI 移动不可踩其它怪物
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("A", 2, 3, hp=50, attack=1, behavior="chase")
        g.spawn_monster("B", 3, 3, hp=50, attack=1, behavior="chase")
        for _ in range(15):
            g.monster_turn()
            occupied = [(mm.x, mm.y) for mm in g.monsters if mm.alive]
            self.assertEqual(len(occupied), len(set(occupied)))


class TestWanderDeterminism(unittest.TestCase):
    def _run(self, seed):
        g = Game(rng=RandomSource(seed=seed))
        m = g.spawn_monster("迷途无人机", 4, 3, hp=8, attack=2, behavior="wander")
        path = []
        for _ in range(12):
            g.monster_turn()
            path.append((m.x, m.y))
        return path

    def test_same_seed_same_wander(self):
        # 不变量 #2：相同 seed ⇒ 相同随机游走结果（随机只出自 RandomSource）
        self.assertEqual(self._run(7), self._run(7))

    def test_wander_stays_in_bounds(self):
        g = Game(rng=RandomSource(seed=3))
        m = g.spawn_monster("迷途无人机", 4, 3, hp=8, attack=2, behavior="wander")
        for _ in range(20):
            g.monster_turn()
            self.assertTrue(g.in_bounds(m.x, m.y))
            self.assertFalse(g.is_wall(m.x, m.y))


class TestDeadMonster(unittest.TestCase):
    def test_dead_monster_does_not_act(self):
        g = Game(rng=RandomSource(seed=0))
        m = g.spawn_monster("练习靶", 2, 1, hp=1, attack=3, behavior="chase")
        g.player_attack(m)  # 一击击倒
        self.assertFalse(m.alive)
        pos = (m.x, m.y)
        g.monster_turn()
        self.assertEqual((m.x, m.y), pos)  # 死怪不动、不攻击


class TestMonsterTurnAll(unittest.TestCase):
    def test_all_alive_monsters_act(self):
        g = Game(rng=RandomSource(seed=0))
        m1 = g.spawn_monster("A", 4, 3, hp=50, attack=1, behavior="chase")
        m2 = g.spawn_monster("B", 5, 3, hp=50, attack=1, behavior="chase")
        p1, p2 = (m1.x, m1.y), (m2.x, m2.y)
        g.monster_turn()
        self.assertTrue((m1.x, m1.y) != p1 or (m2.x, m2.y) != p2)


if __name__ == "__main__":
    unittest.main()
