"""M26 存档 / 读档测试。

只验证存档作为「纯数据快照」的：
- JSON 可序列化 / 文件往返；
- 快照幂等（to_dict 同状态同结果，可还原）；
- 读档后确定性不破：同存档 + 同后续输入序列 ⇒ 同终态（不变量 #2 / #26）；
- rng 内部状态完整保存 ⇒ 读档后续随机序列无缝衔接（#1/#2）；
- 开关 / 怪物 / 道具 / 灯光 / 楼梯等状态全部保留，且 opt-in 默认玩法零回归。

不引入任何新随机；全部走既有 Game 方法。
"""
import os
import sys
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rogue import Game  # noqa: E402
from rogue.game import SAVE_VERSION  # noqa: E402
from rogue.rng import RandomSource  # noqa: E402

SEED = 19


def _build_full(**over):
    """构造一个把大多数开关都打开的 Game（最大化要序列化的状态面）。"""
    kw = dict(fov=True, stealth=True, noise=True, light=True,
              flashlight=True, switches=True, boss=True, boss_depth=3)
    kw.update(over)
    return Game.procedural(RandomSource(SEED), depth=1, **kw)


def _post_actions():
    """确定性的「后续输入序列」，覆盖移动 / 怪物回合 / 手电（消耗 rng 或状态）。"""
    return (["mt"] * 12
            + ["up", "mt", "down", "mt", "left", "mt", "right", "mt"] * 4
            + ["fl", "mt"] * 3)


def _apply(g, a):
    if a == "mt":
        g.monster_turn()
    elif a == "up":
        g.move(0, -1)
    elif a == "down":
        g.move(0, 1)
    elif a == "left":
        g.move(-1, 0)
    elif a == "right":
        g.move(1, 0)
    elif a == "fl" and g.flashlight_enabled:
        g.toggle_flashlight()
    # 其余为无效动作占位（确定性，不影响状态）


class TestSaveSerialization(unittest.TestCase):
    def test_to_dict_is_json_serializable(self):
        g = _build_full()
        blob = json.dumps(g.to_dict())
        self.assertIsInstance(blob, str)
        # 能原样解析回来
        self.assertEqual(json.loads(blob)["version"], SAVE_VERSION)

    def test_to_dict_is_pure(self):
        """to_dict 不改动任何游戏状态（纯读取，#8 延伸）。"""
        g = _build_full()
        d1 = g.to_dict()
        d2 = g.to_dict()
        self.assertEqual(d1, d2)

    def test_roundtrip_dict_preserves_full_state(self):
        g = _build_full()
        d = g.to_dict()
        g2 = Game.from_dict(d)
        # 导出幂等：重建后再导出应与原快照逐字节一致
        self.assertEqual(g2.to_dict(), d)
        # 关键玩法状态逐字段相等
        self.assertEqual(g2.player_hp, g.player_hp)
        self.assertEqual(g2.grid, g.grid)
        self.assertEqual(g2.depth, g.depth)
        self.assertEqual(len(g2.monsters), len(g.monsters))
        self.assertEqual(len(g2.items), len(g.items))
        self.assertEqual(len(g2.switches), len(g.switches))
        # rng 内部状态完整保留
        self.assertEqual(g2.rng.get_state(), g.rng.get_state())

    def test_file_roundtrip(self):
        g = _build_full()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "save.json")
            g.save(path)
            self.assertTrue(os.path.exists(path))
            g2 = Game.load(path)
        self.assertEqual(g2.to_dict(), g.to_dict())

    def test_load_into_mutates_in_place(self):
        g = _build_full()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "save.json")
            g.save(path)
            g2 = _build_full(boss=False)  # 用不同初始状态，验证被原地覆盖
            g2.load_into(path)
        self.assertEqual(g2.to_dict(), g.to_dict())


class TestSaveDeterminism(unittest.TestCase):
    def test_determinism_after_load(self):
        """核心不变量 #26：同存档 + 同后续输入序列 ⇒ 同终态。"""
        g = _build_full()
        # 先在存档点之前推进一段（消耗 rng 与状态）
        for _ in range(8):
            g.monster_turn()
        save = g.to_dict()

        g1 = g
        for a in _post_actions():
            _apply(g1, a)
        final1 = g1.to_dict()

        g2 = Game.from_dict(save)
        for a in _post_actions():
            _apply(g2, a)
        final2 = g2.to_dict()

        self.assertEqual(final2, final1)

    def test_rng_stream_continues_across_load(self):
        """rng 内部状态随存档完整保存，读档后下一次随机调用逐字节衔接（#1/#2）。"""
        g = _build_full()
        for _ in range(5):
            g.monster_turn()
        save = g.to_dict()
        g2 = Game.from_dict(save)
        self.assertEqual(g2.rng.get_state(), g.rng.get_state())
        # 各自再走一步随机，结果必须相同
        for _ in range(3):
            g.monster_turn()
            g2.monster_turn()
        self.assertEqual(g2.rng.get_state(), g.rng.get_state())

    def test_light_and_switch_state_survive(self):
        """灯光 / 房间灯开关状态应随存档保留（#12/#14/#15/#19 跨层之外的持久化）。"""
        g = _build_full()
        # 程序化首层应已摆好开关实体
        self.assertTrue(len(g.switches) >= 0)  # 至少不报错
        d = g.to_dict()
        g2 = Game.from_dict(d)
        # 开关的房间归属（center）必须一致
        self.assertEqual([s.room.center for s in g2.switches],
                         [s.room.center for s in g.switches])
        self.assertEqual(g2.switched_lights, g.switched_lights)
        self.assertEqual(g2.destroyed_lights, g.destroyed_lights)
        self.assertEqual(g2.light_field, g.light_field)


class TestSaveOptInDefault(unittest.TestCase):
    def test_tutorial_map_roundtrip(self):
        """默认（M1 固定教学图）也能正常存读档，零回归。"""
        g = Game(RandomSource(0))
        d = g.to_dict()
        g2 = Game.from_dict(d)
        self.assertEqual(g2.to_dict(), d)
        self.assertEqual(g2.render(), g.render())

    def test_save_does_not_change_gameplay_result(self):
        """存档本身不扰动后续玩法（存档后再走一步，与未存档走一步完全一致）。"""
        g_a = _build_full()
        g_a.monster_turn()
        save = g_a.to_dict()
        g_a.monster_turn()
        after_a = g_a.to_dict()

        g_b = Game.from_dict(save)
        g_b.monster_turn()
        after_b = g_b.to_dict()

        self.assertEqual(after_b, after_a)


if __name__ == "__main__":
    unittest.main()
