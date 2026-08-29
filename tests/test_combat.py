"""M2 战斗系统行为规格（对应工单 T-002 验收 A）。

核心红线覆盖：
- 不变量 #3 玩家 HP 永不为负（max(0, ...) 钳制）
- 不变量 #2 回合确定性（相同 seed + 相同攻击序列 ⇒ 相同结果）
- 不变量 #1 随机仅经 RandomSource（由 gate 门2 / 评审流水线静态拦截）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.game import Game, Monster
from rogue.rng import RandomSource


class TestPlayerState(unittest.TestCase):
    def setUp(self):
        self.g = Game(rng=RandomSource(seed=0))

    def test_player_hp_initial(self):
        self.assertEqual(self.g.player_hp, 20)
        self.assertEqual(self.g.player_max_hp, 20)

    def test_player_not_dead_initially(self):
        self.assertFalse(self.g.player_dead)


class TestCombatResolution(unittest.TestCase):
    def setUp(self):
        self.g = Game(rng=RandomSource(seed=0))
        self.g.spawn_monster("街头暴徒", 2, 1, hp=10, attack=3)

    def test_attack_reduces_monster_hp(self):
        # 玩家 (1,1)，怪物 (2,1) 相邻
        self.assertTrue(self.g.is_adjacent(2, 1))
        dmg, dead = self.g.player_attack(self.g.monsters[0])
        self.assertGreater(dmg, 0)
        self.assertEqual(self.g.monsters[0].hp, 10 - dmg)

    def test_monster_dies_at_zero(self):
        # 1 HP 怪物：一击必死，HP 钳制为 0（不变量 #3）
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("练习靶", 2, 1, hp=1, attack=3)
        dmg, dead = g.player_attack(g.monsters[0])
        self.assertTrue(dead)
        self.assertEqual(g.monsters[0].hp, 0)

    def test_cannot_attack_non_adjacent(self):
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("远处敌人", 5, 3, hp=10, attack=3)
        dmg, dead = g.player_attack(g.monsters[0])
        self.assertEqual(dmg, 0)
        self.assertFalse(dead)
        self.assertEqual(g.monsters[0].hp, 10)

    def test_attack_counter_hurts_player(self):
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("反击者", 2, 1, hp=50, attack=4)  # 高血确保存活反击
        before = g.player_hp
        g.player_attack(g.monsters[0])
        self.assertEqual(g.player_hp, before - 4)

    def test_player_hp_never_negative(self):
        # 不变量 #3：玩家 HP 永不为负，即使受到超额伤害
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("重击者", 2, 1, hp=100, attack=999)
        for _ in range(10):
            g.player_attack(g.monsters[0])
        self.assertEqual(g.player_hp, 0)
        self.assertTrue(g.player_dead)


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_result(self):
        def run(seed):
            g = Game(rng=RandomSource(seed=seed))
            g.spawn_monster("靶子", 2, 1, hp=30, attack=2)
            out = []
            for _ in range(5):
                dmg, dead = g.player_attack(g.monsters[0])
                out.append((dmg, g.monsters[0].hp, g.player_hp))
            return out
        self.assertEqual(run(7), run(7))

    def test_damage_range_and_random_engaged(self):
        # #1 随机经 RandomSource：伤害落在 [基础, 基础+浮动] 且确有浮动（非退化为常量）
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("沙包", 2, 1, hp=1000, attack=2)
        damages = [g.player_attack(g.monsters[0])[0] for _ in range(30)]
        self.assertTrue(all(4 <= d <= 7 for d in damages))
        self.assertGreater(len(set(damages)), 1)


class TestMoveBlockedByMonster(unittest.TestCase):
    def test_cannot_walk_into_monster(self):
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("挡路者", 2, 1, hp=10, attack=3)
        ok = g.move(1, 0)  # 试图走入怪物格
        self.assertFalse(ok)
        self.assertEqual((g.px, g.py), (1, 1))


if __name__ == "__main__":
    unittest.main()
