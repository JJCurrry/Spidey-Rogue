"""M4 道具与背包行为规格（对应工单 T-004 验收 A）。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（掉落判定/种类走 rng.chance / rng.choice）
- 不变量 #2 回合确定性（同 seed + 同击杀序列 ⇒ 同掉落）
- 不变量 #4 道具只生成在界内且非墙的格子
- 不变量 #5 背包容量上限（满包拾取失败且道具留在地面）
- 不变量 #6 玩家 HP 不得超过上限（治疗钳制）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.game import (Game, Item, ITEM_KEYS, INVENTORY_CAPACITY,
                        SANDWICH_HEAL, WEB_SHOT_DMG, NANO_BOOST_DMG)
from rogue.rng import RandomSource


class TestGroundSpawn(unittest.TestCase):
    def setUp(self):
        self.g = Game(rng=RandomSource(seed=0))

    def test_spawn_item_on_floor(self):
        it = self.g.spawn_item("sandwich", 3, 1)
        self.assertIsNotNone(it)
        self.assertEqual((it.x, it.y), (3, 1))
        self.assertIs(self.g.item_at(3, 1), it)
        self.assertEqual(it.name, "梅姨的三明治")

    def test_spawn_rejects_wall(self):
        # 不变量 #4：墙格不可放道具
        self.assertIsNone(self.g.spawn_item("sandwich", 0, 0))
        self.assertEqual(self.g.items, [])

    def test_spawn_rejects_out_of_bounds(self):
        # 不变量 #4：越界不可放道具
        self.assertIsNone(self.g.spawn_item("sandwich", 99, 99))
        self.assertIsNone(self.g.spawn_item("sandwich", -1, -1))

    def test_spawn_rejects_unknown_key(self):
        self.assertIsNone(self.g.spawn_item("振金盾牌", 3, 1))
        with self.assertRaises(ValueError):
            Item("振金盾牌", 1, 1)

    def test_one_item_per_tile(self):
        self.assertIsNotNone(self.g.spawn_item("sandwich", 3, 1))
        self.assertIsNone(self.g.spawn_item("nano_boost", 3, 1))
        self.assertEqual(len(self.g.items), 1)

    def test_item_does_not_alter_grid(self):
        # 道具是实体层，不改写地图格子
        self.g.spawn_item("sandwich", 3, 1)
        self.assertEqual(self.g.tile_at(3, 1), ".")


class TestPickUp(unittest.TestCase):
    def setUp(self):
        self.g = Game(rng=RandomSource(seed=0))

    def test_pick_up_moves_item_to_inventory(self):
        self.g.spawn_item("sandwich", 2, 1)
        self.g.move(1, 0)  # 玩家走到 (2,1)
        it = self.g.pick_up()
        self.assertIsNotNone(it)
        self.assertIsNone(self.g.item_at(2, 1))
        self.assertEqual(self.g.inventory, [it])
        self.assertEqual(self.g.items, [])

    def test_pick_up_nothing_returns_none(self):
        self.assertIsNone(self.g.pick_up())
        self.assertEqual(self.g.inventory, [])

    def test_render_shows_item(self):
        self.g.spawn_item("web_cartridge", 3, 1)
        self.assertIn("!", self.g.render())


class TestInventoryCapacity(unittest.TestCase):
    def test_capacity_enforced(self):
        # 不变量 #5：背包容量上限；满包时拾取失败且道具留在地面
        g = Game(rng=RandomSource(seed=0))
        g.move(1, 0)  # 玩家走到 (2,1)
        for _ in range(INVENTORY_CAPACITY + 1):
            g.spawn_item("sandwich", 2, 1)
            g.pick_up()
        self.assertEqual(len(g.inventory), INVENTORY_CAPACITY)
        self.assertTrue(g.inventory_full)
        self.assertEqual(len(g.items), 1)  # 第 6 个留在地面，没被吞掉
        self.assertIsNone(g.pick_up())


class TestSandwich(unittest.TestCase):
    def setUp(self):
        self.g = Game(rng=RandomSource(seed=0))
        self.g.player_hp = 10
        self.g.spawn_item("sandwich", 1, 1)
        self.g.pick_up()

    def test_sandwich_heals(self):
        self.assertTrue(self.g.use_item(0))
        self.assertEqual(self.g.player_hp, 10 + SANDWICH_HEAL)
        self.assertEqual(self.g.inventory, [])

    def test_heal_capped_at_max_hp(self):
        # 不变量 #6：治疗不得超过上限
        self.g.player_hp = self.g.player_max_hp - 2
        self.g.use_item(0)
        self.assertEqual(self.g.player_hp, self.g.player_max_hp)

    def test_full_hp_does_not_consume(self):
        self.g.player_hp = self.g.player_max_hp
        self.assertFalse(self.g.use_item(0))
        self.assertEqual(len(self.g.inventory), 1)  # 不浪费


class TestNanoBoost(unittest.TestCase):
    def test_nano_boost_raises_damage(self):
        g = Game(rng=RandomSource(seed=0))
        g.spawn_monster("沙包", 2, 1, hp=10000, attack=0)
        g.spawn_item("nano_boost", 1, 1)
        g.pick_up()
        self.assertTrue(g.use_item(0))
        self.assertEqual(g.player_dmg_bonus, NANO_BOOST_DMG)
        damages = [g.player_attack(g.monsters[0])[0] for _ in range(30)]
        # 基础 4 + 加成 2 + 浮动 [0,3] ⇒ [6,9]
        self.assertTrue(all(6 <= d <= 9 for d in damages))
        self.assertGreater(len(set(damages)), 1)  # 随机浮动仍生效（#1）


class TestWebCartridge(unittest.TestCase):
    def setUp(self):
        self.g = Game(rng=RandomSource(seed=0))
        self.g.spawn_item("web_cartridge", 1, 1)
        self.g.pick_up()

    def test_shot_hits_nearest_monster(self):
        near = self.g.spawn_monster("近处恶徒", 2, 1, hp=20, attack=3)
        far = self.g.spawn_monster("远处恶徒", 5, 3, hp=20, attack=3)
        self.assertTrue(self.g.use_item(0))
        self.assertEqual(near.hp, 20 - WEB_SHOT_DMG)
        self.assertEqual(far.hp, 20)  # 只打最近的一个

    def test_shot_applies_stun(self):
        m = self.g.spawn_monster("街头小混混", 5, 3, hp=20, attack=3, behavior="chase")
        self.g.use_item(0)
        self.assertEqual(m.stunned, 1)
        pos = (m.x, m.y)
        self.g.monster_turn()
        self.assertEqual((m.x, m.y), pos)  # 被蛛网束缚，本回合不动
        self.assertEqual(m.stunned, 0)
        self.g.monster_turn()
        self.assertNotEqual((m.x, m.y), pos)  # 挣脱后恢复行动

    def test_stunned_monster_does_not_attack(self):
        self.g.spawn_monster("街头小混混", 2, 1, hp=20, attack=3, behavior="chase")
        hp0 = self.g.player_hp
        self.g.use_item(0)  # 命中并束缚
        self.g.monster_turn()
        self.assertEqual(self.g.player_hp, hp0)  # 束缚中，不吃反击
        self.g.monster_turn()
        self.assertEqual(self.g.player_hp, hp0 - 3)  # 解束缚后反击

    def test_no_target_does_not_consume(self):
        self.assertFalse(self.g.use_item(0))
        self.assertEqual(len(self.g.inventory), 1)

    def test_kill_by_shot_can_drop(self):
        m = self.g.spawn_monster("脆皮无人机", 3, 1, hp=1, attack=0)
        self.assertTrue(self.g.use_item(0))
        self.assertFalse(m.alive)


class TestUseItemGuards(unittest.TestCase):
    def setUp(self):
        self.g = Game(rng=RandomSource(seed=0))

    def test_invalid_index_returns_false(self):
        self.assertFalse(self.g.use_item(0))   # 空背包
        self.assertFalse(self.g.use_item(-1))
        self.assertFalse(self.g.use_item(99))
        self.g.spawn_item("sandwich", 1, 1)
        self.g.pick_up()
        self.assertFalse(self.g.use_item(1))   # 越界序号


class TestDropDeterminism(unittest.TestCase):
    def _run(self, seed):
        g = Game(rng=RandomSource(seed=seed))
        drops = []
        for _ in range(30):
            # 每次在相邻格放一只 1 HP 靶子，一击必杀后记录掉落再清场
            m = g.spawn_monster("靶子", 2, 1, hp=1, attack=0)
            g.player_attack(m)
            if g.items:
                it = g.items.pop(0)
                drops.append((it.key, it.x, it.y))
            else:
                drops.append(None)
        return drops

    def test_same_seed_same_drops(self):
        # 不变量 #2 + #1：掉落序列可重现
        self.assertEqual(self._run(7), self._run(7))

    def test_drop_actually_happens(self):
        # 掉落概率 0.5 × 30 次 ⇒ 至少掉一个（否则说明掉落根本没接线）
        drops = [d for d in self._run(11) if d is not None]
        self.assertGreater(len(drops), 0)

    def test_drop_key_is_known(self):
        for key, _, _ in [d for d in self._run(11) if d is not None]:
            self.assertIn(key, ITEM_KEYS)


if __name__ == "__main__":
    unittest.main()
