"""Pygame GUI 渲染层（M22 · 微型绞杀者：换视图层，不动 Game 核心）。

把 ASCII 视图层（Game.render() + color.py）替换为真实窗口渲染。
铁律（与 color.py 同源，红线不被触碰）：
- 只读 Game 公开状态，只调既有动作方法（move/player_attack/web_strike/pick_up/
  use_item/descend/toggle_flashlight/monster_turn）；不写任何游戏状态、不引入随机
  ⇒ 不变量 #8 渲染纯净性延伸 / #1 Seed 注入不破。
- 字符网格直接消费 `game.render()`（终端与 GUI 同一份字形，零漂移）；
  调色板镜像 colorize 的字形→颜色映射。
- 主循环只做「事件→按键 token→handle_key(game,token)→(acted? monster_turn)→draw」，
  与 main.py 的 --play 终端路径逐字节同构 ⇒ 同 seed+同输入序列 ⇒ 同结果（#2）。

纯几何、零随机、确定性（不变量 #2 精神）。
"""
from __future__ import annotations

import os
import sys

# pygame 在模块顶部 import：headless 测试用 SDL_VIDEODRIVER=dummy 加载；
# main.py 只在 --gui 分支 import 本模块，故 gate 不传 --gui 时不强制 pygame。
import pygame

# ---- 调色板（镜像 src/rogue/color.py 的 GLYPH_COLORS 语义）----
# 字形 → RGB：@红 / M品红 / m暗品红 / ~蓝 / ?青 / !黄 / >绿 / #暗灰 / =黄
GLYPH_RGB: dict[str, tuple[int, int, int]] = {
    "@": (225, 40, 50),     # 玩家：亮红（红蓝战衣）
    "M": (220, 50, 200),    # 已察觉敌人：品红
    "m": (150, 50, 140),    # 未察觉敌人：暗品红
    "~": (70, 130, 240),    # 听见动静：蓝
    "?": (50, 200, 225),    # 蜘蛛感应：青
    "!": (230, 200, 50),    # 补给：黄
    ">": (50, 200, 90),     # 楼梯：绿
    "#": (95, 95, 110),     # 墙：暗灰
    "=": (230, 200, 50),    # 墙边灯开关：黄
}
FLOOR_RGB = (48, 48, 58)       # 地板（可见）
FLOOR_DIM = (26, 26, 33)       # 地板（记忆 / 迷雾）
WALL_RGB = (95, 95, 110)       # 墙（可见）
WALL_DIM = (55, 55, 65)        # 墙（记忆）
UNSEEN_RGB = (12, 12, 16)      # 未探索：近黑
HUD_BG = (18, 18, 24)
TEXT_RGB = (210, 210, 220)

HUD_HEIGHT = 140
DEFAULT_HELP = (
    "WASD/方向键 移动（撞怪=攻击） · G 拾取 · 1-5 用道具\n"
    "E 蛛网摆荡突袭 · F 手电 · > 下潜 · 空格/回车 等待\n"
    "? 帮助开关 · Q 退出"
)


def _dim(rgb: tuple[int, int, int], factor: float = 0.45) -> tuple[int, int, int]:
    """把一个 RGB 压暗（迷雾里的记忆格）。纯函数。"""
    r, g, b = rgb
    return (int(r * factor), int(g * factor), int(b * factor))


def tile_color(ch: str, visible: bool) -> tuple[int, int, int]:
    """给定地图字形与可见性，返回该格颜色。纯函数（不变量 #2 精神）。

    - 实体/特征字形（@ M m ~ ? ! > = #）按调色板；不可见时压暗。
    - '.' 地板：可见亮、记忆暗。'#' 墙：可见/记忆同色系。
    - ' ' 未探索：近黑。
    """
    if ch == " ":
        return UNSEEN_RGB
    if ch == ".":
        return FLOOR_RGB if visible else FLOOR_DIM
    if ch == "#":
        return WALL_RGB if visible else WALL_DIM
    base = GLYPH_RGB.get(ch)
    if base is None:
        return TEXT_RGB
    return base if visible else _dim(base)


def pixel_pos(gx: int, gy: int, cell: int) -> tuple[int, int]:
    """网格坐标 → 像素左上角。纯函数（便于单测，不依赖任何状态）。"""
    return (gx * cell, gy * cell)


def _bag_str(game) -> str:
    if not game.inventory:
        return "空"
    return "、".join(f"{i}:{it.name}" for i, it in enumerate(game.inventory))


class PygameRenderer:
    """读取 Game 公开状态、逐帧画窗口的视图层。

    不持有也不改写任何游戏状态；所有交互经由注入的 handle_key（main.py 的
    _handle_key，与终端 --play 同函数）走既有 Game 方法。
    """

    def __init__(self, game, cell_size: int = 24, max_depth: int = 999,
                 caption: str = "Spider-Man Roguelike", help_text: str = DEFAULT_HELP):
        self.game = game
        self.cell = cell_size
        self.max_depth = max_depth
        self.caption = caption
        self.help_text = help_text
        self.help_shown = False
        self.messages: list[str] = []
        w = game.width * cell_size
        h = game.height * cell_size + HUD_HEIGHT
        pygame.init()
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption(caption)
        self.font = pygame.font.SysFont("consolas, monospace", max(13, cell_size - 9))
        self.big_font = pygame.font.SysFont("consolas, monospace", 30)

    # ---- 输入：pygame 事件 → _handle_key 能懂的 token ----
    def translate_key(self, event) -> str | None:
        """把一次 KEYDOWN 翻译成 _handle_key 接受的 token（与终端同构）。

        方向键映射到 w/a/s/d；其余靠 event.unicode 取得真实字符
        （含 '>' '?' '.' '1'~'5' 等；_handle_key 会 lower 处理字母）。
        返回 None 表示忽略（如 ESC）。
        """
        k = event.key
        if k == pygame.K_UP:
            return "w"
        if k == pygame.K_DOWN:
            return "s"
        if k == pygame.K_LEFT:
            return "a"
        if k == pygame.K_RIGHT:
            return "d"
        if k == pygame.K_SPACE or k == pygame.K_RETURN:
            return " "
        if k == pygame.K_ESCAPE:
            return None
        u = event.unicode
        if u:
            return u
        return None

    # ---- 渲染 ----
    def draw(self) -> None:
        game = self.game
        cell = self.cell
        self.screen.fill(HUD_BG)
        grid_text = game.render()            # 与终端同字形，零漂移
        rows = grid_text.split("\n")
        visible = game.visible if game.fov_enabled else None
        for gy, row in enumerate(rows):
            for gx, ch in enumerate(row):
                if ch == "":
                    continue
                vis = True if visible is None else ((gx, gy) in visible)
                color = tile_color(ch, vis)
                x, y = pixel_pos(gx, gy, cell)
                pygame.draw.rect(self.screen, color, (x, y, cell, cell))
        self._draw_hud()
        self._draw_messages()
        if self.help_shown:
            self._draw_help()
        pygame.display.flip()

    def _draw_hud(self) -> None:
        game = self.game
        cell = self.cell
        y0 = game.height * cell + 6
        lines = [
            f"HP {game.player_hp}/{game.player_max_hp}  |  层 {game.depth}：{game.level_name}",
            f"背包：{_bag_str(game)}",
        ]
        flags = []
        if game.stealth_enabled:
            flags.append("潜行")
        if game.noise_enabled:
            flags.append("听觉")
        if game.light_enabled:
            flags.append("光照")
        if game.flashlight_enabled:
            flags.append("手电" + ("开" if game.flashlight_on else "关"))
        if flags:
            lines.append("模式：" + " / ".join(flags))
        lines.append("WASD/方向键移动 · 撞怪攻击 · G拾取 · 1-5道具 · E突袭 · F手电 · >下潜 · 空格等待 · ?帮助 · Q退出")
        for i, txt in enumerate(lines):
            surf = self.font.render(txt, True, TEXT_RGB)
            self.screen.blit(surf, (8, y0 + i * (self.font.get_height() + 2)))

    def _draw_messages(self) -> None:
        if not self.messages:
            return
        last = self.messages[-1]
        surf = self.font.render(last[:90], True, (240, 220, 120))
        self.screen.blit(surf, (8, self.game.height * self.cell + HUD_HEIGHT - self.font.get_height() - 4))

    def _draw_help(self) -> None:
        surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 200))
        self.screen.blit(surf, (0, 0))
        for i, line in enumerate(self.help_text.split("\n")):
            t = self.font.render(line, True, (240, 240, 200))
            self.screen.blit(t, (20, 30 + i * (self.font.get_height() + 4)))

    # ---- 动作应用（run 与单测共用，保证同构）----
    def apply_keys(self, handle_key, seq: list[str]) -> None:
        """按 token 序列执行动作（与 --play 终端路径同构）。无绘制。"""
        for token in seq:
            acted, msg = handle_key(self.game, token)
            if msg == "quit":
                break
            if acted:
                self.game.monster_turn()
            if self.game.player_dead:
                break

    # ---- 主循环 ----
    def run(self, handle_key, fps: int = 15) -> str:
        """窗口主循环。handle_key 即 main.py 的 _handle_key（与终端同函数）。

        每帧：读事件 → token → handle_key(game,token) → (acted? monster_turn) → draw。
        返回 'win' / 'dead' / 'quit'。
        """
        clock = pygame.time.Clock()
        self.draw()
        try:
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return "quit"
                    if event.type == pygame.KEYDOWN:
                        token = self.translate_key(event)
                        if token is None:
                            continue
                        if token == "?":
                            self.help_shown = not self.help_shown
                            self.draw()
                            continue
                        acted, msg = handle_key(self.game, token)
                        if msg and msg != "quit":
                            self.messages.append(msg)
                            if len(self.messages) > 6:
                                self.messages.pop(0)
                        if msg == "quit":
                            return "quit"
                        if acted:
                            self.game.monster_turn()
                        self.draw()
                        end = self._check_ending()
                        if end is not None:
                            return end
                clock.tick(fps)
        finally:
            pygame.quit()

    def _check_ending(self) -> str | None:
        if self.game.player_dead:
            self._draw_banner("蜘蛛侠被击倒了……（游戏结束）")
            self._wait_key()
            return "dead"
        alive = [m for m in self.game.monsters if m.alive]
        if self.game.depth >= self.max_depth and not alive:
            self._draw_banner("三层清场，蜘蛛侠摆荡着回家吃三明治。（你赢了！）")
            self._wait_key()
            return "win"
        return None

    def _draw_banner(self, text: str) -> None:
        surf = self.big_font.render(text, True, (240, 90, 90))
        rect = surf.get_rect(center=(self.screen.get_width() // 2,
                                     self.game.height * self.cell // 2))
        self.screen.blit(surf, rect)
        pygame.display.flip()

    def _wait_key(self) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    return
