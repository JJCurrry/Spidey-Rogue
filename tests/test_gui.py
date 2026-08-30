"""M22 Pygame GUI 渲染层行为规格（对应工单 T-022 验收 A/B）。

核心红线覆盖：
- 不变量 #8 渲染纯净性（延伸）：renderer 只读 Game 公开状态、只调既有动作方法，
  `game.render()` 字形零改动（消费同一份输出）；纯函数 tile_color/pixel_pos 确定性。
- 不变量 #2 回合确定性：GUI 主循环与 --play 终端路径同构（共用 _handle_key），
  同 seed+同输入序列 ⇒ 同结果——test_apply_keys_parity_with_terminal 机器判定。
- 不变量 #1：render_pygame 不引入任何随机（seed-guard 仍只放行 rng.py）。
- 可移植性：headless 环境（SDL_VIDEODRIVER=dummy）下可构造/绘制/单测；
  pygame 缺失时整套用例 skip，不拖垮 gate。
"""
import os
import sys
import unittest

ROOT = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(ROOT, "..", "src"))   # rogue 包
sys.path.insert(0, os.path.join(ROOT, ".."))          # main 模块（取 _handle_key）

# headless 测试：必须在 import pygame 之前设好 dummy driver
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from rogue import Game                                          # noqa: E402
from rogue.rng import RandomSource                              # noqa: E402
from rogue.render_pygame import (                               # noqa: E402
    tile_color, pixel_pos,
    UNSEEN_RGB, FLOOR_RGB, FLOOR_DIM, WALL_RGB, WALL_DIM,
)

try:
    from rogue.render_pygame import PygameRenderer
    _HAVE_GUI = True
except Exception:                                # pygame 未装 → 整组 skip
    PygameRenderer = None
    _HAVE_GUI = False

try:
    from main import _handle_key
except Exception:
    _handle_key = None


def _new_game(**kw):
    rng = RandomSource(seed=19)
    return Game.procedural(rng, depth=1, fov=True, stealth=False,
                           noise=False, light=False, flashlight=False, **kw)


def _run_seq_terminal(game, seq):
    """复刻 --play 终端路径的动作应用（与 renderer.apply_keys 同构）。"""
    for token in seq:
        acted, msg = _handle_key(game, token)
        if msg == "quit":
            break
        if acted:
            game.monster_turn()
        if game.player_dead:
            break


@unittest.skipUnless(_HAVE_GUI, "pygame 未安装（headless 跳过）")
class TestTileColorPure(unittest.TestCase):
    def test_unseen_is_black(self):
        self.assertEqual(tile_color(" ", True), UNSEEN_RGB)
        self.assertEqual(tile_color(" ", False), UNSEEN_RGB)

    def test_floor_visible_vs_dim(self):
        self.assertEqual(tile_color(".", True), FLOOR_RGB)
        self.assertEqual(tile_color(".", False), FLOOR_DIM)

    def test_wall_visible_vs_dim(self):
        self.assertEqual(tile_color("#", True), WALL_RGB)
        self.assertEqual(tile_color("#", False), WALL_DIM)

    def test_entity_glyph_color(self):
        # @ 红 / M 品红 / > 绿，且不可见时压暗但仍可区分
        self.assertEqual(tile_color("@", True), (225, 40, 50))
        self.assertEqual(tile_color("M", True), (220, 50, 200))
        self.assertEqual(tile_color(">", True), (50, 200, 90))
        dim_m = tile_color("M", False)
        self.assertTrue(all(c < 220 for c in dim_m))   # 压暗


@unittest.skipUnless(_HAVE_GUI, "pygame 未安装（headless 跳过）")
class TestPixelPosPure(unittest.TestCase):
    def test_origin(self):
        self.assertEqual(pixel_pos(0, 0, 24), (0, 0))

    def test_scaling(self):
        self.assertEqual(pixel_pos(3, 5, 24), (72, 120))


@unittest.skipUnless(_HAVE_GUI, "pygame 未安装（headless 跳过）")
class TestTranslateKey(unittest.TestCase):
    class _Ev:
        def __init__(self, key=0, unicode=""):
            self.key = key
            self.unicode = unicode

    def setUp(self):
        import pygame
        self.renderer = PygameRenderer(_new_game(), cell_size=8)
        self.pygame = pygame

    def test_arrows_map_to_wasd(self):
        p = self.pygame
        self.assertEqual(self.renderer.translate_key(self._Ev(p.K_UP)), "w")
        self.assertEqual(self.renderer.translate_key(self._Ev(p.K_DOWN)), "s")
        self.assertEqual(self.renderer.translate_key(self._Ev(p.K_LEFT)), "a")
        self.assertEqual(self.renderer.translate_key(self._Ev(p.K_RIGHT)), "d")

    def test_unicode_keys(self):
        self.assertEqual(self.renderer.translate_key(self._Ev(unicode="g")), "g")
        self.assertEqual(self.renderer.translate_key(self._Ev(unicode=">")), ">")
        self.assertEqual(self.renderer.translate_key(self._Ev(unicode="?")), "?")
        self.assertEqual(self.renderer.translate_key(self._Ev(unicode="1")), "1")

    def test_space_and_enter_wait(self):
        p = self.pygame
        self.assertEqual(self.renderer.translate_key(self._Ev(p.K_SPACE)), " ")
        self.assertEqual(self.renderer.translate_key(self._Ev(p.K_RETURN)), " ")

    def test_escape_ignored(self):
        p = self.pygame
        self.assertIsNone(self.renderer.translate_key(self._Ev(p.K_ESCAPE)))


@unittest.skipUnless(_HAVE_GUI and _handle_key is not None,
                     "pygame 或 main._handle_key 不可用（headless 跳过）")
class TestRendererAndParity(unittest.TestCase):
    def test_construct_and_draw_one_frame(self):
        r = PygameRenderer(_new_game(), cell_size=8)
        r.draw()                       # 不应抛错
        r.help_shown = True
        r.draw()                       # 帮助面板也不应抛错

    def test_apply_keys_parity_with_terminal(self):
        """GUI 路径（apply_keys）与 --play 终端路径（_handle_key+monster_turn）
        对同 seed+同输入序列产生完全相同的游戏状态 ⇒ #2 不变。"""
        seq = ["w", "s", "a", "d", " ", "w", "w", "g", "s", "d", " "]
        g_term = _new_game()
        g_gui = _new_game()
        _run_seq_terminal(g_term, seq)
        r = PygameRenderer(g_gui, cell_size=8)
        r.apply_keys(_handle_key, seq)
        self.assertEqual(g_term.player_hp, g_gui.player_hp)
        self.assertEqual((g_term.px, g_term.py), (g_gui.px, g_gui.py))
        self.assertEqual(g_term.depth, g_gui.depth)
        alive_t = [m for m in g_term.monsters if m.alive]
        alive_g = [m for m in g_gui.monsters if m.alive]
        self.assertEqual(len(alive_t), len(alive_g))
        self.assertEqual(len(g_term.inventory), len(g_gui.inventory))


@unittest.skipUnless(_HAVE_GUI, "pygame 未安装（headless 跳过）")
class TestM23Effects(unittest.TestCase):
    def setUp(self):
        self.r = PygameRenderer(_new_game(), cell_size=28)

    def test_spawn_web_effect(self):
        self.r._spawn_web(1, 1, 5, 3)
        self.assertEqual(len(self.r.effects), 1)
        e = self.r.effects[0]
        self.assertEqual(e["kind"], "web")
        self.assertEqual((e["gx0"], e["gy0"], e["gx1"], e["gy1"]), (1, 1, 5, 3))
        self.assertEqual(e["ttl"], e["max"])

    def test_flash_effect(self):
        self.r._spawn_flash(2, 2)
        self.assertEqual(self.r.effects[0]["kind"], "flash")

    def test_effect_decay_removes(self):
        self.r._spawn_web(0, 0, 1, 1)
        ttl0 = self.r.effects[0]["ttl"]
        for _ in range(ttl0 + 5):
            self.r._update_effects()
        self.assertEqual(len(self.r.effects), 0)

    def test_detect_attack_finds_damaged(self):
        g = self.r.game
        alive = [m for m in g.monsters if m.alive]
        if not alive:
            self.skipTest("本 seed 开局无存活怪物")
        m = alive[0]
        prev = {id(m): (m.x, m.y, m.hp)}
        m.hp -= 1
        found = self.r._detect_attack(prev)
        self.assertIsNotNone(found)
        self.assertEqual(found, (m.x, m.y))

    def test_detect_attack_none_when_untouched(self):
        g = self.r.game
        prev = {id(m): (m.x, m.y, m.hp) for m in g.monsters if m.alive}
        self.assertIsNone(self.r._detect_attack(prev))


@unittest.skipUnless(_HAVE_GUI, "pygame 未安装（headless 跳过）")
class TestM23ThemedDraw(unittest.TestCase):
    def test_draw_full_scene_no_error(self):
        r = PygameRenderer(_new_game(), cell_size=28)
        from rogue.game import Item
        g = r.game
        placed = False
        for y in range(g.height):
            for x in range(g.width):
                if g.grid[y][x] == "." and (x, y) != (g.px, g.py):
                    g.items.append(Item("web_cartridge", x, y))
                    placed = True
                    break
            if placed:
                break
        r.draw()                       # 不应抛错
        r.help_shown = True
        r.draw()

    def test_glyph_helpers_no_error(self):
        r = PygameRenderer(_new_game(), cell_size=28)
        r._draw_spider_sense(0, 0)
        r._draw_spidey(1, 1, True)
        r._draw_enemy(2, 2, "M", True, None)
        r._draw_enemy(2, 3, "m", True, None)
        r._draw_enemy(2, 4, "~", True, None)
        r._draw_item(3, 3, "sandwich", True)
        r._draw_item(3, 4, "nano_boost", True)
        r._draw_item(3, 5, "decoy", True)
        r._draw_stairs(4, 4, True)
        r._draw_switch(5, 5, True)
        r._draw_hud()

    def test_themed_tiles_built(self):
        r = PygameRenderer(_new_game(), cell_size=28)
        self.assertTrue(r.detail)
        for name in ("tile_floor", "tile_floor_dim", "tile_wall",
                     "tile_wall_dim", "tile_unseen"):
            self.assertIsNotNone(getattr(r, name))


if __name__ == "__main__":
    unittest.main()
