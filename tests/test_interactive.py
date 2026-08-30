"""M21 可键盘操作模式测试。

只验证交互输入的「动作→状态」映射与确定性，不引入任何随机：
- 撞怪即攻击（bump-to-attack）
- 无效键/纯信息键不消耗回合（不扰动随机序列，#2）
- 拾取 / 用道具 / 等待 / 手电开关 / 蛛网突袭 / 下潜 等核心动作
- 交互循环能正确判定 胜利 / 失败 / 退出
- 相同按键序列 ⇒ 相同结果（不变量 #2：同 seed + 同输入序列 ⇒ 同结果）
默认（无 --play）的脚本自动驾驶 demo 路径完全不受影响（_player_act 未改）。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # 让 import main 可用

from rogue import Game  # noqa: E402
from rogue.game import Item, NANO_BOOST_DMG  # noqa: E402
from rogue.rng import RandomSource  # noqa: E402
import main as demo  # noqa: E402

DIR_KEY = {(1, 0): "d", (-1, 0): "a", (0, 1): "s", (0, -1): "w"}


def _adjacent_floor(game):
    """找一个与玩家相邻的可站地板格（不确定则强制改成地板）。返回 (dx, dy)。"""
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if game.in_bounds(game.px + dx, game.py + dy):
            return dx, dy
    raise AssertionError("玩家被四壁包围，测试无法布置相邻格")


class HandleKeyTest(unittest.TestCase):
    def test_move_bumps_attacks(self):
        g = Game(RandomSource(0))
        g.monsters = []  # 固定教学图默认无怪，清场确保干净
        dx, dy = _adjacent_floor(g)
        g.grid[g.py + dy][g.px + dx] = "."  # 确保可站
        tx, ty = g.px + dx, g.py + dy
        m = g.spawn_monster("测试靶", tx, ty, hp=10, attack=0)
        acted, msg = demo._handle_key(g, DIR_KEY[(dx, dy)])
        self.assertTrue(acted)
        self.assertLess(m.hp, 10)
        self.assertIn("蛛网拳", msg)

    def test_move_into_wall_no_turn(self):
        g = Game(RandomSource(0))
        g.monsters = []
        dx, dy = _adjacent_floor(g)
        g.grid[g.py + dy][g.px + dx] = "#"  # 强制成墙
        acted, msg = demo._handle_key(g, DIR_KEY[(dx, dy)])
        self.assertFalse(acted)
        self.assertIn("墙", msg)

    def test_pickup(self):
        g = Game(RandomSource(0))
        g.monsters = []
        it = g.spawn_item("sandwich", g.px, g.py)
        self.assertIsNotNone(g.item_at(g.px, g.py))
        acted, msg = demo._handle_key(g, "g")
        self.assertTrue(acted)
        self.assertIn(it, g.inventory)

    def test_use_nano_boost(self):
        g = Game(RandomSource(0))
        g.monsters = []
        g.inventory.append(Item("nano_boost", g.px, g.py))
        bonus0 = g.player_dmg_bonus
        acted, msg = demo._handle_key(g, "1")
        self.assertTrue(acted)
        self.assertEqual(g.player_dmg_bonus, bonus0 + NANO_BOOST_DMG)

    def test_wait_consumes_turn(self):
        g = Game(RandomSource(0))
        g.monsters = []
        acted, msg = demo._handle_key(g, " ")
        self.assertTrue(acted)
        self.assertIn("待命", msg)

    def test_flashlight_toggle(self):
        g = Game(RandomSource(0), flashlight=True)
        g.monsters = []
        on0 = g.flashlight_on
        acted, msg = demo._handle_key(g, "f")
        self.assertTrue(acted)
        self.assertNotEqual(g.flashlight_on, on0)

    def test_flashlight_toggle_without_equip(self):
        g = Game(RandomSource(0))  # 未装备手电
        g.monsters = []
        acted, msg = demo._handle_key(g, "f")
        self.assertFalse(acted)
        self.assertIn("未装备", msg)

    def test_web_strike_unaware(self):
        g = Game(RandomSource(0), stealth=True)
        g.monsters = []
        dx, dy = _adjacent_floor(g)
        g.grid[g.py + dy][g.px + dx] = "."
        tx, ty = g.px + dx, g.py + dy
        m = g.spawn_monster("哨兵", tx, ty, hp=5, attack=0)
        self.assertFalse(m.alerted)  # 潜行下新怪未察觉
        acted, msg = demo._handle_key(g, "e")
        self.assertTrue(acted)
        self.assertIn("突袭", msg)
        self.assertTrue(m.hp < 5 or not m.alive)

    def test_web_strike_no_unaware_target(self):
        g = Game(RandomSource(0), stealth=True)
        g.monsters = []  # 没有任何未察觉目标
        acted, msg = demo._handle_key(g, "e")
        self.assertFalse(acted)
        self.assertIn("没有可突袭", msg)

    def test_quit(self):
        g = Game(RandomSource(0))
        acted, msg = demo._handle_key(g, "q")
        self.assertFalse(acted)
        self.assertEqual(msg, "quit")

    def test_unknown_key(self):
        g = Game(RandomSource(0))
        acted, msg = demo._handle_key(g, "z")
        self.assertFalse(acted)
        self.assertIn("未知", msg)


class InteractiveLoopTest(unittest.TestCase):
    def _session(self, game, keys):
        fake = iter(list(keys) + ["q"])  # 末尾补 q，保证循环必然终止
        return demo._player_interactive(game, color_on=False,
                                         get_key=lambda _prompt=None: next(fake))

    def test_loop_win_on_final_floor(self):
        g = Game(RandomSource(0))
        g.monsters = []
        g.depth = demo.MAX_DEPTH
        dx, dy = _adjacent_floor(g)
        g.grid[g.py + dy][g.px + dx] = "."
        g.spawn_monster("靶", g.px + dx, g.py + dy, hp=1, attack=0)
        ending = self._session(g, ["d"])
        self.assertEqual(ending, "win")

    def test_loop_dead(self):
        g = Game(RandomSource(0))
        g.monsters = []
        dx, dy = _adjacent_floor(g)
        g.grid[g.py + dy][g.px + dx] = "."
        g.spawn_monster("杀手", g.px + dx, g.py + dy, hp=100, attack=5)
        g.player_hp = 1
        ending = self._session(g, ["d"])
        self.assertEqual(ending, "dead")

    def test_loop_quit(self):
        g = Game(RandomSource(0))
        g.monsters = []
        ending = self._session(g, ["q"])
        self.assertEqual(ending, "quit")

    def test_determinism_same_keys_same_result(self):
        def run():
            g = Game.procedural(RandomSource(demo.SEED), depth=1, fov=True,
                                stealth=False, noise=False, light=False,
                                flashlight=False)
            ending = self._session(g, ["s", "a", "d", "w", "."])
            return g, ending
        g1, e1 = run()
        g2, e2 = run()
        self.assertEqual(e1, e2)
        self.assertEqual((g1.player_hp, g1.depth, g1.px, g1.py),
                         (g2.player_hp, g2.depth, g2.px, g2.py))


if __name__ == "__main__":
    unittest.main()
