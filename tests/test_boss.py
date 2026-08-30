"""M25 Boss 战与胜利条件闭环测试。

只验证 Boss 作为「纯几何、零随机」确定性实体的行为，不引入任何随机：
- opt-in 默认零回归：boss=False ⇒ 最终层照旧刷普通怪、不刷 Boss、不占 rng（#1/#2）
- 最终层且 boss 开启 ⇒ 确定性刷绿魔（字形 B、高 HP、攻击压在平衡基线内）
- 半血暴怒：effective_attack 确定性 +1（零随机）
- 胜利闭环：is_victory() 仅在「最终层绿魔被击败且玩家未阵亡」时为真
- 渲染纯净（#8 延伸）：render() 不改写任何状态
- 确定性：同 seed + 同 boss_depth ⇒ 同位置
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rogue import Game  # noqa: E402
from rogue.game import BOSS_NAME, BOSS_HP, BOSS_ATTACK, BOSS_ENRAGE_BONUS  # noqa: E402
from rogue.rng import RandomSource  # noqa: E402

SEED = 19
BOSS_DEPTH = 3


def _final_floor(boss: bool) -> Game:
    """开一局、直接跳到最终层（boss_depth 命中），返回该层 Game。"""
    g = Game.procedural(RandomSource(SEED), depth=BOSS_DEPTH,
                        boss=boss, boss_depth=BOSS_DEPTH)
    return g


class TestBossSpawn(unittest.TestCase):
    def test_opt_in_default_no_boss(self):
        """boss=False ⇒ 最终层不刷 Boss（零回归，#1/#2 不破）。"""
        g = _final_floor(boss=False)
        self.assertIsNone(g.boss)
        self.assertTrue(any(m.alive for m in g.monsters))  # 仍有普通怪

    def test_boss_only_on_final_floor(self):
        """boss=True 但当前层 < boss_depth ⇒ 不刷 Boss。"""
        for d in (1, 2):
            g = Game.procedural(RandomSource(SEED), depth=d,
                                 boss=True, boss_depth=BOSS_DEPTH)
            self.assertIsNone(g.boss, f"depth={d} 不应刷 Boss")

    def test_boss_spawns_on_final_floor(self):
        """boss=True 且 depth == boss_depth ⇒ 刷绿魔，属性正确。"""
        g = _final_floor(boss=True)
        self.assertIsNotNone(g.boss)
        self.assertTrue(g.boss.boss)
        self.assertEqual(g.boss.name, BOSS_NAME)
        self.assertEqual(g.boss.max_hp, BOSS_HP)
        self.assertEqual(g.boss.attack, BOSS_ATTACK)
        self.assertFalse(g.boss.boss and any(m.alive and not m.boss
                                              for m in g.monsters))  # 最终层只有 Boss

    def test_boss_glyph_is_B(self):
        """render() 中 Boss 恒画 'B'，与 M/m/~ 区分。"""
        g = _final_floor(boss=True)
        self.assertIn("B", g.render())
        # 普通怪字形不受影响：非 boss 怪仍走 M/m/~
        for m in g.monsters:
            if not m.boss:
                self.assertNotEqual(g._monster_glyph(m), "B")


class TestBossDeterminism(unittest.TestCase):
    def test_same_seed_same_boss_position(self):
        """同 seed + 同 boss_depth ⇒ 同位置（确定性，#2）。"""
        a = _final_floor(boss=True)
        b = _final_floor(boss=True)
        self.assertEqual((a.boss.x, a.boss.y), (b.boss.x, b.boss.y))

    def test_non_final_floors_untouched(self):
        """Boss 只出现在最终层、且不消耗 rng ⇒ 前几层布局与 boss=False 逐字节一致（#1/#2）。"""
        ga = Game.procedural(RandomSource(SEED), depth=1, boss=True, boss_depth=BOSS_DEPTH)
        gb = Game.procedural(RandomSource(SEED), depth=1, boss=False, boss_depth=BOSS_DEPTH)
        # 第 1、2 层实体布局必须完全相同（boss 只改最终层，且不扰动随机序列）
        for _ in range(2):  # 跑到第 2 层（depth == boss_depth 之前）
            self.assertEqual(
                [(m.name, m.x, m.y) for m in ga.monsters],
                [(m.name, m.x, m.y) for m in gb.monsters],
                f"depth={ga.depth} 实体布局应一致",
            )
            ga.descend()
            gb.descend()


class TestBossEnrage(unittest.TestCase):
    def test_effective_attack_below_half_enraged(self):
        """HP ≤ 半 ⇒ effective_attack = 攻击 + 暴怒加成（确定性，零随机）。"""
        g = _final_floor(boss=True)
        b = g.boss
        b.hp = b.max_hp // 2  # 恰好半血
        self.assertEqual(b.effective_attack, b.attack + BOSS_ENRAGE_BONUS)
        b.hp = 1
        self.assertEqual(b.effective_attack, b.attack + BOSS_ENRAGE_BONUS)

    def test_effective_attack_above_half_normal(self):
        """HP > 半 ⇒ effective_attack == 基础攻击（不暴怒）。"""
        g = _final_floor(boss=True)
        b = g.boss
        b.hp = b.max_hp // 2 + 1
        self.assertEqual(b.effective_attack, b.attack)

    def test_enrage_applied_in_monster_attack(self):
        """半血时 monster_attack 实际造成暴怒伤害（#3 由 _hurt_player 钳制）。"""
        g = _final_floor(boss=True)
        b = g.boss
        # 把 Boss 摆到玩家相邻（纯几何，不扰动 rng）
        dx, dy = 1, 0
        bx, by = g.px + dx, g.py + dy
        self.assertTrue(g.in_bounds(bx, by) and not g.is_wall(bx, by))
        b.x, b.y = bx, by
        b.hp = b.max_hp // 2  # 暴怒状态
        hp0 = g.player_hp
        dmg = g.monster_attack(b)
        self.assertEqual(dmg, b.attack + BOSS_ENRAGE_BONUS)
        self.assertEqual(g.player_hp, max(0, hp0 - dmg))


class TestVictoryLoop(unittest.TestCase):
    def test_is_victory_false_when_boss_alive(self):
        g = _final_floor(boss=True)
        self.assertFalse(g.is_victory())

    def test_is_victory_true_when_boss_dead(self):
        g = _final_floor(boss=True)
        g.boss.take_damage(9999)
        self.assertFalse(g.boss.alive)
        self.assertTrue(g.is_victory())

    def test_is_victory_false_when_player_dead(self):
        g = _final_floor(boss=True)
        g.boss.take_damage(9999)
        g.player_hp = 0
        self.assertFalse(g.is_victory())

    def test_is_victory_always_false_without_boss(self):
        g = _final_floor(boss=False)
        for m in g.monsters:
            m.take_damage(9999)
        self.assertFalse(g.is_victory())  # 非 boss 模式沿用 M1~M24 语义


class TestRenderingPurity(unittest.TestCase):
    def test_render_does_not_mutate_game(self):
        """#8 延伸：render() 只读状态，不改写任何玩法状态（含 Boss 引用）。"""
        g = _final_floor(boss=True)
        snap = {
            "px": g.px, "py": g.py, "hp": g.player_hp,
            "monsters": [(m.x, m.y, m.hp, m.alive) for m in g.monsters],
            "boss": (g.boss.x, g.boss.y, g.boss.hp) if g.boss else None,
            "items": [(it.x, it.y) for it in g.items],
        }
        _ = g.render()
        after = {
            "px": g.px, "py": g.py, "hp": g.player_hp,
            "monsters": [(m.x, m.y, m.hp, m.alive) for m in g.monsters],
            "boss": (g.boss.x, g.boss.y, g.boss.hp) if g.boss else None,
            "items": [(it.x, it.y) for it in g.items],
        }
        self.assertEqual(snap, after)


if __name__ == "__main__":
    unittest.main()
