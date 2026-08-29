"""M10 ANSI 颜色高亮行为规格（对应工单 T-010 验收 A）。

核心红线覆盖：
- 不变量 #8 渲染纯净性（延伸）：`render()` 输出零改动；`colorize` 只是 `render()` 之外的
  纯函数包裹，剥离转义码后 == 原文本 ⇒ 既有 `assertIn("@", render())` 类断言全部成立。
- 不变量 #2 回合确定性（精神）：`colorize` 是确定性纯函数，同输入同输出，不消耗随机。
- 不变量 #1：`color.py` 不引入任何随机调用（seed-guard 仍只放行 rng.py）。
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.color import colorize, should_color, RESET, GLYPH_COLORS
from rogue import Game
from rogue.rng import RandomSource

# 所有被上色的字形
_GLYPHS = "@Mm~?!>#"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip(text: str) -> str:
    """剥掉所有 ANSI 转义码，得到纯文本。"""
    return _ANSI_RE.sub("", text)


class _FakeStream:
    """模拟一个文件流，isatty 可指定。"""
    def __init__(self, tty: bool):
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


class TestColorizeDisabled(unittest.TestCase):
    def test_disabled_returns_plain(self):
        text = "abc@# .\nM~m?!>"
        self.assertEqual(colorize(text, enabled=False), text)

    def test_disabled_default_is_on_but_flag_off(self):
        # 明确 enabled=False 必须原样；enabled 缺省为 True（与 main 的 color_on 解耦）
        self.assertEqual(colorize("@@", enabled=False), "@@")


class TestColorizeGlyphs(unittest.TestCase):
    def test_wraps_known_glyphs(self):
        for g in _GLYPHS:
            out = colorize(g, enabled=True)
            self.assertIn(g, out)
            self.assertTrue(out.startswith("\x1b["), f"{g!r} 应被 ANSI 前缀包裹")
            self.assertTrue(out.endswith(RESET), f"{g!r} 应以 RESET 收尾")

    def test_strip_equals_original(self):
        text = "##@....\n#!M~m?#\n> .  "
        self.assertEqual(_strip(colorize(text, enabled=True)), text)

    def test_leaves_unknown_and_spaces(self):
        # 未知字符、空格、换行原样透传，且不被包裹
        text = "x y\nz"
        out = colorize(text, enabled=True)
        self.assertEqual(_strip(out), text)
        # 没有任何转义码（因为没有已知字形）
        self.assertEqual(out, text)

    def test_known_glyph_only_wrapped_once_each(self):
        text = "@@"  # 两个玩家字形
        out = colorize(text, enabled=True)
        self.assertEqual(out.count(RESET), 2)
        self.assertEqual(_strip(out), "@@")


class TestColorizeDeterminism(unittest.TestCase):
    def test_same_input_same_output(self):
        text = "#@.!\nM~m?>"
        a = colorize(text, enabled=True)
        b = colorize(text, enabled=True)
        self.assertEqual(a, b)

    def test_no_random_invariant(self):
        # 多跑几次也稳定（ implicitly 验证无随机）
        text = "@Mm~?!>#."
        first = colorize(text, enabled=True)
        for _ in range(20):
            self.assertEqual(colorize(text, enabled=True), first)


class TestShouldColor(unittest.TestCase):
    def test_no_color_env_forces_off(self):
        self.assertFalse(should_color(env={"NO_COLOR": "1"}))
        self.assertFalse(should_color(env={"NO_COLOR": "anything"}))

    def test_force_color_env_forces_on(self):
        self.assertTrue(should_color(env={"FORCE_COLOR": "1"}, stream=_FakeStream(False)))
        self.assertTrue(should_color(env={"CLICOLOR": "1"}, stream=_FakeStream(False)))

    def test_tty_auto(self):
        self.assertTrue(should_color(stream=_FakeStream(True)))
        self.assertFalse(should_color(stream=_FakeStream(False)))

    def test_no_color_wins_over_tty(self):
        # NO_COLOR 优先级高于 TTY 自动
        self.assertFalse(should_color(stream=_FakeStream(True), env={"NO_COLOR": "1"}))


class TestColorizeRealRender(unittest.TestCase):
    def _render(self) -> str:
        # M1 固定教学图（7×5）：渲染输出应含玩家 @
        game = Game(RandomSource(seed=1))
        return game.render()

    def test_render_contains_player_glyph(self):
        plain = self._render()
        self.assertIn("@", plain)

    def test_colorize_preserves_render_assertions(self):
        plain = self._render()
        colored = colorize(plain, enabled=True)
        # 既有规格类断言仍成立
        self.assertIn("@", colored)
        # 剥离转义码后 == 原 render（不变量 #8 渲染纯净性延伸）
        self.assertEqual(_strip(colored), plain)

    def test_colorize_disabled_keeps_render_identical(self):
        plain = self._render()
        self.assertEqual(colorize(plain, enabled=False), plain)


if __name__ == "__main__":
    unittest.main()
