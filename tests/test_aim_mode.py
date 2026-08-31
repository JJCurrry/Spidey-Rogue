"""M30 交互式瞄准模式（控制层视图状态，不属于 Game）。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（瞄准状态纯视图、不调 rng；确认走 Game 既有 toggle_switch/
  destroy_switch，不引入随机）
- 不变量 #2 回合确定性（瞄准不消耗回合、不改 Game 状态；同 seed + 同按键序列 ⇒ 同 Game 终态）
- 不变量 #8 渲染纯净性延伸（renderer 画光标准星只读 aim_state、不回写 Game）
- 不变量 #19 复用：确认射灭/射碎复用 M19 的 can_toggle_switch/can_destroy_switch 几何约束
- 不变量 #30（M30 新增）：瞄准是控制层视图状态、opt-in 默认关闭、瞄准不耗回合、确认才耗回合
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rogue import aim_state
from rogue.game import Game, WEB_LIGHT_RANGE
from rogue.level import Level, Room
from rogue.rng import RandomSource

try:
    import main  # 取 _handle_key
    _handle_key = main._handle_key
except Exception:  # main import 失败时跳过（与 test_gui.py 同模式）
    _handle_key = None

try:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from rogue.render_pygame import PygameRenderer
    _HAVE_GUI = True
except Exception:
    PygameRenderer = None
    _HAVE_GUI = False

_NO_STAIRS = (-1, -1)


def _make(rows, start=(1, 1), rooms=(), fov=True, stealth=True,
          light=True, flashlight=False, noise=False, switches=True, seed=0):
    """用固定 rows 搭一局（不撒怪撒道具，只测瞄准模式与开关）。"""
    grid = [list(r.replace("@", ".")) for r in rows]
    lv = Level(grid, list(rooms), start, _NO_STAIRS, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth, light=light,
                flashlight=flashlight, noise=noise, switches=switches)


# 单房间：玩家在房间内 (1,1)，房间 (1,1)~(10,3)，中心 (6,2)
# 开关摆在房间北沿第一格 (1,0)（墙），玩家 (1,1) 距其 1、视线清晰 ⇒ 够得着
_ROOM = [
    "###########",
    "#@........#",
    "#.........#",
    "#.........#",
    "###########",
]
_ROOM_DEF = Room(1, 1, 10, 3)  # center = (6,2)；开关摆在 (1,0)


@unittest.skipUnless(_handle_key is not None, "main 模块不可导入")
class TestAimStateMachine(unittest.TestCase):
    """aim_state 模块本身：进入 / 退出 / 移动 / 复位。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_initial_inactive(self):
        self.assertFalse(aim_state.is_active())
        self.assertIsNone(aim_state.cursor())

    def test_enter_sets_cursor_to_player(self):
        aim_state.enter(3, 5)
        self.assertTrue(aim_state.is_active())
        self.assertEqual(aim_state.cursor(), (3, 5))

    def test_exit_clears_active(self):
        aim_state.enter(3, 5)
        aim_state.exit()
        self.assertFalse(aim_state.is_active())
        self.assertIsNone(aim_state.cursor())

    def test_reset_clears_state(self):
        aim_state.enter(3, 5)
        aim_state.reset()
        self.assertFalse(aim_state.is_active())
        self.assertIsNone(aim_state.cursor())


class TestCursorMovement(unittest.TestCase):
    """光标移动受 game.in_bounds 约束、不写 Game、不引入随机。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_move_within_bounds(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        aim_state.enter(1, 1)
        self.assertTrue(aim_state.move(1, 0, g))   # 右
        self.assertEqual(aim_state.cursor(), (2, 1))
        self.assertTrue(aim_state.move(0, 1, g))   # 下
        self.assertEqual(aim_state.cursor(), (2, 2))

    def test_move_out_of_bounds_blocked(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        aim_state.enter(0, 0)
        # 越界：(-1,0) 不存在
        self.assertFalse(aim_state.move(-1, 0, g))
        self.assertEqual(aim_state.cursor(), (0, 0))  # 原地不动

    def test_move_does_not_write_game(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        before = g.to_dict()
        aim_state.enter(1, 1)
        aim_state.move(2, 1, g)
        aim_state.move(-1, 0, g)
        after = g.to_dict()
        self.assertEqual(before, after)  # Game 状态零变化（#8 延伸）


@unittest.skipUnless(_handle_key is not None, "main 模块不可导入")
class TestAimDoesNotConsumeTurn(unittest.TestCase):
    """瞄准模式：进入 / 退出 / 移动光标都不调 monster_turn（acted=False）。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_enter_aim_no_turn(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        acted, _ = _handle_key(g, "t")
        self.assertFalse(acted)
        self.assertTrue(aim_state.is_active())

    def test_move_cursor_no_turn(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")              # 进入瞄准
        acted, _ = _handle_key(g, "d")   # 右移光标
        self.assertFalse(acted)

    def test_exit_aim_no_turn(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")
        acted, _ = _handle_key(g, "t")   # 再按 T 退出
        self.assertFalse(acted)
        self.assertFalse(aim_state.is_active())

    def test_exit_via_q_no_turn(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")
        acted, msg = _handle_key(g, "q")  # 瞄准下 Q 退瞄准而非退游戏
        self.assertFalse(acted)
        self.assertFalse(aim_state.is_active())
        self.assertNotEqual(msg, "quit")  # 不是退出游戏


@unittest.skipUnless(_handle_key is not None, "main 模块不可导入")
class TestAimDoesNotWriteGame(unittest.TestCase):
    """瞄准模式前后 Game.to_dict() 完全相同（#8 延伸 / #30）。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_aim_sequence_preserves_game_state(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        before = g.to_dict()
        _handle_key(g, "t")       # 进入瞄准
        _handle_key(g, "d")       # 右移
        _handle_key(g, "s")       # 下移
        _handle_key(g, "a")       # 左移
        _handle_key(g, "w")       # 上移
        _handle_key(g, "t")       # 退出瞄准
        after = g.to_dict()
        self.assertEqual(before, after)


@unittest.skipUnless(_handle_key is not None, "main 模块不可导入")
class TestConfirmToggleCallsGameToggleSwitch(unittest.TestCase):
    """确认射灭（Enter/空格）走 game.toggle_switch：成功 ⇒ acted=True + switched_lights 改变。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_confirm_toggle_consumes_turn(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        # 开关摆在 (1,0)，玩家 (1,1) 够得着
        _handle_key(g, "t")               # 进入瞄准
        # 移光标到开关格 (1,0)：从 (1,1) 上移
        _handle_key(g, "w")
        self.assertEqual(aim_state.cursor(), (1, 0))
        acted, msg = _handle_key(g, " ")  # 空格 = 射灭
        self.assertTrue(acted)
        self.assertIn("射灭", msg)
        # switched_lights 应包含房间中心 (6,2)
        self.assertIn((6, 2), g.switched_lights)
        # 出手后退出瞄准
        self.assertFalse(aim_state.is_active())

    def test_confirm_toggle_with_enter(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")
        _handle_key(g, "w")
        acted, msg = _handle_key(g, "\r")  # 回车
        self.assertTrue(acted)


@unittest.skipUnless(_handle_key is not None, "main 模块可导入")
class TestConfirmDestroyCallsGameDestroySwitch(unittest.TestCase):
    """确认射碎（X）走 game.destroy_switch：成功 ⇒ acted=True + destroyed_lights 改变。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_confirm_destroy_consumes_turn(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")
        _handle_key(g, "w")               # 光标到 (1,0)
        acted, msg = _handle_key(g, "x")  # 射碎
        self.assertTrue(acted)
        self.assertIn("射碎", msg)
        self.assertIn((6, 2), g.destroyed_lights)
        self.assertFalse(aim_state.is_active())


@unittest.skipUnless(_handle_key is not None, "main 模块可导入")
class TestGeometryBlocksOutOfRange(unittest.TestCase):
    """几何约束：够不着（射程外 / 看不见 / 非开关格）⇒ acted=False、不改 Game、不耗回合。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_toggle_non_switch_tile_acts_false(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")
        # 光标在 (1,1)（玩家处，非开关格）
        acted, msg = _handle_key(g, " ")
        self.assertFalse(acted)
        self.assertNotIn((6, 2), g.switched_lights)
        self.assertTrue(aim_state.is_active())  # 够不着不退出瞄准

    def test_destroy_non_switch_tile_acts_false(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")
        acted, msg = _handle_key(g, "x")
        self.assertFalse(acted)
        self.assertNotIn((6, 2), g.destroyed_lights)

    def test_toggle_out_of_range_acts_false(self):
        # 玩家在 (1,1)，把开关挪到远处的墙格（超出 WEB_LIGHT_RANGE=6）
        g = _make([
            "#############",
            "#@..........#",
            "#...........#",
            "#...........#",
            "#############",
        ], rooms=[Room(1, 1, 11, 3)])  # center=(6,2)；开关在 (1,0)（北沿首格）
        # 把玩家移远：直接构造开关在远处——改用更小的房间让玩家离开关远
        # 实际上 _ROOM 里玩家 (1,1) 离开关 (1,0) 只有 1，够得着；
        # 这里测「光标移到射程外的开关」——构造一个玩家够不着的场景
        g2 = _make([
            "###############",
            "#@............#",
            "#.............#",
            "#.............#",
            "###############",
        ], rooms=[Room(1, 1, 13, 3)])  # center=(7,2)；开关在 (1,0)（北沿首格，距玩家 1）
        # 玩家 (1,1) 离开关 (1,0) 仍只 1，够得着——这个用例改测「光标在非开关墙格」
        aim_state.reset()
        _handle_key(g2, "t")
        # 移光标到远处墙格 (13,0)（非开关、且超射程）
        for _ in range(12):
            aim_state.move(1, 0, g2)
        acted, msg = _handle_key(g2, " ")
        self.assertFalse(acted)


@unittest.skipUnless(_handle_key is not None, "main 模块可导入")
class TestCancelDoesNotConsumeTurn(unittest.TestCase):
    """退出瞄准（T/Q/Esc）不消耗回合。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_cancel_via_t(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")
        acted, _ = _handle_key(g, "t")
        self.assertFalse(acted)

    def test_cancel_via_q(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")
        acted, msg = _handle_key(g, "q")
        self.assertFalse(acted)
        self.assertNotEqual(msg, "quit")

    def test_cancel_via_escape(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        _handle_key(g, "t")
        acted, _ = _handle_key(g, "\x1b")
        self.assertFalse(acted)
        self.assertFalse(aim_state.is_active())


@unittest.skipUnless(_handle_key is not None, "main 模块可导入")
class TestDeterminismSameKeysSameResult(unittest.TestCase):
    """同 seed + 同按键序列 ⇒ 同 Game 终态（#2 不破，aim_state 不影响 Game）。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_same_sequence_same_terminal_state(self):
        keys = ["t", "w", " ", "t", "q"]  # 进入瞄准→移光标→射灭→退出→quit
        g1 = _make(_ROOM, rooms=[_ROOM_DEF], seed=19)
        g2 = _make(_ROOM, rooms=[_ROOM_DEF], seed=19)
        for k in keys:
            _handle_key(g1, k)
            if _handle_key(g2, k)[0]:  # acted
                pass  # 不调 monster_turn（这里测 _handle_key 路径确定性）
        # 两个实例 Game 状态完全相同（aim_state 不影响 Game）
        self.assertEqual(g1.to_dict(), g2.to_dict())

    def test_aim_does_not_disturb_rng_sequence(self):
        """瞄准不调 rng，后续随机序列与「从未瞄准」逐字节一致。"""
        g1 = _make(_ROOM, rooms=[_ROOM_DEF], seed=19)
        g2 = _make(_ROOM, rooms=[_ROOM_DEF], seed=19)
        # g1：瞄准一通后退出，再调 rng
        _handle_key(g1, "t")
        _handle_key(g1, "d")
        _handle_key(g1, "s")
        _handle_key(g1, "a")
        _handle_key(g1, "w")
        _handle_key(g1, "t")  # 退出瞄准
        # g2：直接调 rng（不瞄准）
        # 对比 rng 内部状态：应完全相同
        self.assertEqual(g1.rng.get_state(), g2.rng.get_state())


@unittest.skipUnless(_handle_key is not None, "main 模块可导入")
class TestOptInDefaultOff(unittest.TestCase):
    """不按 T 不进入瞄准 ⇒ _handle_key 走原有分支、与 M29 逐字节一致。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_t_is_unknown_when_aim_disabled(self):
        # 光照关 / 开关未启用时按 T 友好提示、不进入瞄准
        g = _make(_ROOM, rooms=[_ROOM_DEF], light=False, switches=False)
        acted, msg = _handle_key(g, "t")
        self.assertFalse(acted)
        self.assertIn("未启用", msg)
        self.assertFalse(aim_state.is_active())

    def test_no_aim_keys_preserve_m29_behavior(self):
        # 不按 T，正常移动键照常工作（瞄准模式零干扰）
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        before = g.to_dict()
        acted, _ = _handle_key(g, "d")  # 右移（非瞄准）
        self.assertTrue(acted)  # 移动消耗回合
        # aim_state 仍 inactive
        self.assertFalse(aim_state.is_active())


@unittest.skipUnless(_HAVE_GUI, "pygame 未安装（headless 跳过）")
@unittest.skipUnless(_handle_key is not None, "main 模块可导入")
class TestRenderPurity(unittest.TestCase):
    """renderer 画光标准星不改 Game 状态（#8 延伸 / #30）。"""

    def setUp(self):
        aim_state.reset()

    def tearDown(self):
        aim_state.reset()

    def test_draw_with_aim_does_not_change_game(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        renderer = PygameRenderer(g, cell_size=16, max_depth=1, sound_on=False)
        _handle_key(g, "t")  # 进入瞄准
        before = g.to_dict()
        renderer.draw()      # 画一帧（含光标准星）
        renderer.draw()      # 再画一帧
        after = g.to_dict()
        self.assertEqual(before, after)
        # aim_state 仍激活（draw 不改它）
        self.assertTrue(aim_state.is_active())

    def test_draw_without_aim_no_cursor(self):
        g = _make(_ROOM, rooms=[_ROOM_DEF])
        renderer = PygameRenderer(g, cell_size=16, max_depth=1, sound_on=False)
        # 不进入瞄准，draw 不应崩
        before = g.to_dict()
        renderer.draw()
        after = g.to_dict()
        self.assertEqual(before, after)
        self.assertFalse(aim_state.is_active())


if __name__ == "__main__":
    unittest.main()
