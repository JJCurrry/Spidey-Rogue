"""Pygame GUI 渲染层（M22 骨架 · M23 Spider-Man 主题化 · M24 动画+美术+音效）。

把 ASCII 视图层（Game.render() + color.py）替换为真实窗口渲染。
铁律（与 color.py 同源，红线不被触碰）：
- 只读 Game 公开状态，只调既有动作方法（move/player_attack/web_strike/pick_up/
  use_item/descend/toggle_flashlight/monster_turn）；不写任何游戏状态、不引入随机
  ⇒ 不变量 #8 渲染纯净性延伸 / #1 Seed 注入不破。
- 地形底取自 `game.grid`（墙/地板），实体/特征取自 `game.render()` 字形
  （迷雾可见性门控 + 渲染优先级 `?`<`>`<`!`<`M`<`@` 全由它管），零漂移；
- 主循环只做「事件→按键 token→handle_key(game,token)→(acted? monster_turn)→draw」，
  与 main.py 的 --play 终端路径逐字节同构 ⇒ 同 seed+同输入序列⇒同结果（#2）。

M23 主题化（HANDOFF 预留的「Sprite/动画/音效」）：
- 预渲染主题贴图（蛛网地板 / 纽约砖墙 / 近黑未探索），按可见性双版；
- 玩家画成蜘蛛侠面具（红底+黑蛛网放射线+白眼）；
- 怪物 M/m/~、道具 !（按 key）、楼梯 >、开关 =、蜘蛛感应 ? 均有主题图标；
- 攻击生成淡出蛛网特效 + 命中白闪（renderer 自身视图状态，不回写 Game）；
- 合成音效（蛛网 thwip / 命中闷响），懒初始化、失败静默、不碰游戏状态；
- 主题化 HUD（红蓝标题条 + 蛛网分隔 + 红色血条 + 背包格）。

M24 动画 + 美术 + 音效升级（T-024 / ADR-020 / 不变量 #24）：
- 动画全部由 renderer 的 `self.frame` 计数器驱动（每帧 +1，纯几何、零随机）；
- 地形多帧预渲染（蛛网轻闪 / 砖缝呼吸）；
- 玩家待机呼吸 / 攻击突进 / 受击红闪；怪物待机浮动 + 眨眼；
- 攻击蛛网行进 + 命中火花迸发；蜘蛛感应扩散同心环；
- 氛围层：暗角 vignette + 开灯房间光晕；
- 音效升级：脚步 / 摆荡 whoosh / 感应刺痛 / 胜负 stings（全程序化合成、懒初始化、失败静默）。
纯几何、零随机、确定性（不变量 #2 精神）。

M27 序列帧 Sprite（T-027 / ADR-023 / 不变量 #27）：
- M24 预渲染已「按帧组织」（floor_frames / wall_frames / unseen_frames，N=4 相位），
  本里程碑把这层地形贴图换成磁盘上的 `tiles/*.png` 序列帧 Sprite——运行时 `blit`
  取代每帧程序化重绘，接口/视觉与 M24 一致。
- 烘焙与回退共用同一套模块级绘制函数（`_make_floor_surface` 等）：`scripts/gen_tiles.py`
  离线确定性烘焙 14 张 PNG（floor/wall 各 lit/dim ×4 帧 + unseen ×4 帧，零随机）；
  `_build_tiles` 优先加载 PNG，缺文件则回退到同款程序化绘制（视觉零差异）。
- 不变式：只读 Game、零随机、确定性不变（#1/#2/#8 延伸）；PNG 是确定性产物、加载不引入随机；
  地形源（PNG 还是程序化）只影响「怎么画」，不改变 `render()` 字形/优先级/玩法。
- 红线不变：仍只调 Game 既有方法、不写任何游戏状态、不引入随机 ⇒ 门禁四道门与 M24 同构。
"""
from __future__ import annotations

import array
import io
import math
import os
import pathlib
import sys
# wave 模块懒导入（pygbag/WASM 环境默认不包含，运行时 pip 安装；
# 懒导入保证模块加载不崩、缺 wave 时音效静默降级）。
_wave_module = None


def _get_wave():
    """返回 wave 模块；不可用时返回 None（调用方自行降级）。"""
    global _wave_module
    if _wave_module is None:
        try:
            import wave as _w
            _wave_module = _w
        except Exception:
            pass
    return _wave_module

# M27：序列帧 Sprite 目录（仓库根 tiles/）。渲染层优先从这里的 *.png 加载，
# 缺文件时回退到同款程序化绘制（与 M24 视觉零差异、确定性不变）。
TILES_DIR = pathlib.Path(__file__).resolve().parents[2] / "tiles"

# pygame 在模块顶部 import：headless 测试用 SDL_VIDEODRIVER=dummy 加载；
# main.py 只在 --gui 分支 import 本模块，故 gate 不传 --gui 时不强制 pygame。
import pygame

# M30 交互式瞄准模式：控制层视图状态（不属于 Game）。renderer 只读它画光标准星，
# 不写它（与 self.effects 同性质，#8 延伸）。aim_state 在 src/rogue/ 下、无循环导入。
from . import aim_state


class _NullFont:
    """字体完全不可用时的最小兜底：render 返回 1×1 透明面、get_height 给最小高度。

    保证渲染器在「无 SysFont 也无内置默认字体」的极端环境（如某些 wasm 构建）下
    任何 `self.font.render(...)` 调用都不抛 AttributeError/异常，避免灰屏。
    """

    def __init__(self, size: int):
        self._size = max(1, int(size))

    def render(self, text, antialias, color, *args, **kwargs):
        return pygame.Surface((self._size, self._size), pygame.SRCALPHA)

    def get_height(self) -> int:
        return self._size


def _make_font(names, size: int):
    """返回可用字体：优先 SysFont，其次内置默认 Font(None)，再不行返回 _NullFont 桩。

    永不抛异常——这是 WASM/缺字体环境下防止渲染器构造失败、进而灰屏的关键兜底。
    """
    try:
        return pygame.font.SysFont(names, size)
    except Exception:
        pass
    try:
        return pygame.font.Font(None, size)
    except Exception:
        pass
    return _NullFont(size)


# ---- 调色板（镜像 src/rogue/color.py 的 GLYPH_COLORS 语义）----
# 字形 → RGB：@红 / M品红 / m暗品红 / ~蓝 / ?青 / !黄 / >绿 / #暗灰 / =黄
# 注意：下面三行实体字形颜色是 M22 测试钉死的字面值，必须保持（不变量 #22/#23 契约）。
GLYPH_RGB: dict[str, tuple[int, int, int]] = {
    "@": (225, 40, 50),     # 玩家：亮红（M22 测试钉死）
    "M": (220, 50, 200),    # 已察觉敌人：品红（M22 测试钉死）
    "m": (150, 50, 140),    # 未察觉敌人：暗品红
    "~": (70, 130, 240),    # 听见动静：蓝
    "?": (50, 200, 225),    # 蜘蛛感应：青
    "!": (230, 200, 50),    # 补给：黄
    ">": (50, 200, 90),     # 楼梯：绿（M22 测试钉死）
    "#": (95, 95, 110),     # 墙：暗灰
    "=": (230, 200, 50),    # 墙边灯开关：黄
}

# ---- Spider-Man 主题配色（M23）----
SPIDEY_RED = (214, 38, 47)      # 战衣红
SPIDEY_BLUE = (26, 54, 120)     # 战衣蓝（纽约夜色）
WEB_COLOR = (150, 165, 195)     # 蛛网丝（冷白蓝）
EYE_WHITE = (245, 245, 250)

# 地形贴图基色（M23 主题化；tile_color 仍返回这些常量以兼容 M22 测试）
FLOOR_RGB = (26, 30, 46)        # 地板（可见）：暗蓝
FLOOR_DIM = (15, 17, 27)        # 地板（记忆 / 迷雾）
WALL_RGB = (44, 48, 66)         # 墙（可见）：砖蓝灰
WALL_DIM = (26, 28, 40)         # 墙（记忆）
UNSEEN_RGB = (9, 9, 13)         # 未探索：近黑
HUD_BG = (14, 14, 22)
TEXT_RGB = (220, 222, 235)
TITLE_RGB = (255, 255, 255)

# 道具按 key 的色相（HUD 背包格 + 图标）
ITEM_TINT: dict[str, tuple[int, int, int]] = {
    "web_cartridge": (90, 200, 230),   # 蛛网弹：青
    "sandwich": (210, 180, 120),       # 梅姨三明治：琥珀
    "nano_boost": (70, 120, 230),      # 纳米强化剂：蓝
    "decoy": (150, 150, 160),          # 垃圾桶盖：灰
}

HUD_HEIGHT = 150
LIGHT_LIT = 2                       # src/rogue/light.py: LIGHT_LEVEL_LIT
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
    M22 测试钉死：tile_color("@"/"M"/">", True) 与 ("."/"#"/" ",*) 的特定返回值不变。
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


# ---- 音频合成（纯内存 wave，无外部素材；懒初始化、失败静默）----
def _synth_buffer(segments: list[tuple]) -> bytes:
    """把若干 (f0, f1, dur, vol, up) 扫频段拼接成 16-bit PCM 字节流。纯函数。"""
    wave_mod = _get_wave()
    if wave_mod is None:
        return b""  # 无 wave 模块时返回静音（调用方 _init_audio 会将 sound_on 置 False）
    rate = 22050
    buf = array.array("h")
    for (f0, f1, dur, vol, up) in segments:
        n = max(1, int(rate * dur))
        for i in range(n):
            t = i / rate
            p = i / n
            f = (f0 + (f1 - f0) * p) if up else (f1 + (f0 - f1) * p)
            s = math.sin(2 * math.pi * f * t)
            env = 1.0 - p
            v = 1.0 if s >= 0 else -1.0
            buf.append(int(32767 * vol * env * v))
    out = io.BytesIO()
    w = wave_mod.open(out, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(buf.tobytes())
    w.close()
    return out.getvalue()


# ---- 预渲染贴图（M23，M24 增加相位帧）----
def _blend(base: tuple[int, int, int], d: int) -> tuple[int, int, int]:
    return (max(0, min(255, base[0] + d)),
            max(0, min(255, base[1] + d)),
            max(0, min(255, base[2] + d)))


# ---- 地形贴图绘制（模块级，M27 抽出来供「运行时程序化回退」与「gen_tiles 烘焙」共用）----
# 同一套代码 ⇒ PNG 资产与程序化回退逐像素一致（不变量 #27：素材不漂移、确定性不变）。
def _make_floor_surface(cell: int, visible: bool, phase: int = 0,
                        detail: bool = True) -> "pygame.Surface":
    s = pygame.Surface((cell, cell))
    base = FLOOR_RGB if visible else FLOOR_DIM
    s.fill(base)
    if detail and visible:
        line = _blend(base, 22)        # 蛛网纹理：淡冷色细线
        off = (phase % 4) - 1          # -1..2 的轻微相位
        for (x0, y0, x1, y1) in (
            (cell // 2, 0, cell // 2, cell),
            (0, cell // 2, cell, cell // 2),
            (0 + off, 0, cell + off, cell),
            (cell - off, 0, -off, cell),
        ):
            pygame.draw.line(s, line, (x0, y0), (x1, y1), 1)
    return s


def _make_wall_surface(cell: int, visible: bool, phase: int = 0,
                      detail: bool = True) -> "pygame.Surface":
    s = pygame.Surface((cell, cell))
    base = WALL_RGB if visible else WALL_DIM
    s.fill(base)
    if detail:
        breath = 10 * math.sin(phase * math.pi / 2)   # 砖缝呼吸
        seam = _blend(base, -14 + int(breath))
        edge = _blend(base, 16)
        # 砖缝：横向 + 纵向
        pygame.draw.line(s, seam, (0, cell // 2), (cell, cell // 2), 1)
        pygame.draw.line(s, seam, (cell // 2, 0), (cell // 2, cell // 2), 1)
        pygame.draw.line(s, seam, (cell // 4, cell // 2),
                         (cell // 4, cell), 1)
        pygame.draw.line(s, seam, (3 * cell // 4, cell // 2),
                         (3 * cell // 4, cell), 1)
        # 红蓝描边：呼应战衣（上沿红、下沿蓝）
        pygame.draw.line(s, SPIDEY_RED, (0, 0), (cell, 0), 1)
        pygame.draw.line(s, SPIDEY_BLUE, (0, cell - 1), (cell, cell - 1), 1)
        if visible:
            pygame.draw.line(s, edge, (0, 0), (0, cell), 1)
    return s


def _make_unseen_surface(cell: int, visible: bool = True, phase: int = 0,
                        detail: bool = True) -> "pygame.Surface":
    s = pygame.Surface((cell, cell))
    s.fill(UNSEEN_RGB)
    if detail:
        line = _blend(UNSEEN_RGB, 4)
        off = (phase % 4) - 1
        pygame.draw.line(s, line, (0 + off, 0), (cell + off, cell), 1)
        pygame.draw.line(s, line, (cell - off, 0), (-off, cell), 1)
    return s


class PygameRenderer:
    """读取 Game 公开状态、逐帧画窗口的视图层。

    不持有也不改写任何游戏状态；所有交互经由注入的 handle_key（main.py 的
    _handle_key，与终端 --play 同函数）走既有 Game 方法。
    """

    def __init__(self, game, cell_size: int = 26, max_depth: int = 999,
                 caption: str = "Spider-Man Roguelike", help_text: str = DEFAULT_HELP,
                 sound_on: bool = True):
        self.game = game
        self.cell = cell_size
        self.max_depth = max_depth
        self.caption = caption
        self.help_text = help_text
        self.help_shown = False
        self.messages: list[str] = []
        self.effects: list[dict] = []     # 视图特效（蛛网/闪光/火花），renderer 自身状态
        self.frame = 0
        self.sound_on = sound_on
        self._snd_web = None
        self._snd_hit = None
        self._snd_step = None
        self._snd_swing = None
        self._snd_sense = None
        self._snd_win = None
        self._snd_lose = None
        self._hk = None
        # 跨帧视图快照（只用于触发视图特效/音效，绝不回写 Game）
        self._prev_px, self._prev_py = game.px, game.py
        self._prev_hp = getattr(game, "player_hp", 0)
        self._prev_sense: set = set()
        self._glow = None
        self._vignette = None
        self.tiles_dir = TILES_DIR        # M27：序列帧目录（可被测试覆盖以验证回退）
        self._using_png_sprites = False   # M27：是否成功加载了 tiles/*.png
        w = game.width * cell_size
        h = game.height * cell_size + HUD_HEIGHT
        # pygbag/wasm：pygame 的 init 由运行时（pygame.base C 扩展就绪后）才可用。
        # 若模块导入期（web.py 被 runpy 加载时）pygame 已被缓存成「无 init 的桩」，
        # 这里在运行时重新加载、必要时回退到 pygame_ce 真身，把 init/display 等属性挂回（#M28）。
        global pygame
        if not hasattr(pygame, "init"):
            import importlib
            try:
                importlib.reload(pygame)
            except Exception:
                pass
        if not hasattr(pygame, "init"):
            try:
                import pygame_ce
                pygame = pygame_ce
            except Exception:
                pass
        if not hasattr(pygame, "init"):
            # 诊断：若走到这里说明 pygame 真身仍未就绪，打印它到底是什么，便于排障。
            try:
                print("[web][DIAG] pygame 仍无 init：",
                      "type=", type(pygame).__name__,
                      "file=", getattr(pygame, "__file__", "?"),
                      "has_base=", hasattr(pygame, "base"))
            except Exception:
                pass
        pygame.init()
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption(caption)
        # 优先中文字体（Windows 常见微软雅黑）；wasm/浏览器或缺字体时回退到内置默认字体，
        # 再不行用 _NullFont 桩（render 返回透明小面），保证构造渲染器与任何 .render 调用都不崩，
        # 不依赖特定字体存在（#22/#23 纯净性延伸；WASM 字体缺失也不致灰屏）。
        _font_names = ["Microsoft YaHei", "Microsoft YaHei UI", "Consolas",
                       "DejaVu Sans", "SimHei", "monospace"]
        self.font = _make_font(_font_names, max(13, cell_size - 9))
        self.big_font = _make_font(_font_names, 30)
        self.detail = cell_size >= 16     # 小 cell（headless 测试）跳过精细纹理
        self._build_tiles()
        self._init_audio()

    # ---- 预渲染地形贴图（M27：优先加载 tiles/*.png 序列帧，缺失回退程序化）----
    def _build_tiles(self) -> None:
        cell = self.cell
        N = 4
        sprites = self._load_tile_sprites(cell, N)
        if sprites is not None:
            # 已从 PNG 资产加载（确定性、零随机）：直接用于绘制 + 帧动画
            self.tile_floor = sprites["floor"][True][0]
            self.tile_floor_dim = sprites["floor"][False][0]
            self.tile_wall = sprites["wall"][True][0]
            self.tile_wall_dim = sprites["wall"][False][0]
            self.tile_unseen = sprites["unseen"][0]
            self.floor_frames = sprites["floor"]
            self.wall_frames = sprites["wall"]
            self.unseen_frames = sprites["unseen"]
            self._using_png_sprites = True
            return
        # 回退：与 M24 完全一致的程序化贴图（tiles/ 缺失时也能跑，零回归）
        self._using_png_sprites = False
        self.tile_floor = self._make_floor(True, 0)
        self.tile_floor_dim = self._make_floor(False, 0)
        self.tile_wall = self._make_wall(True, 0)
        self.tile_wall_dim = self._make_wall(False, 0)
        self.tile_unseen = self._make_unseen(0)
        # 多帧（仅 detail 下生成；小 cell 退化为单帧，保证 headless 轻量）
        if self.detail:
            self.floor_frames = {
                True: [self._make_floor(True, p) for p in range(N)],
                False: [self._make_floor(False, p) for p in range(N)],
            }
            self.wall_frames = {
                True: [self._make_wall(True, p) for p in range(N)],
                False: [self._make_wall(False, p) for p in range(N)],
            }
            self.unseen_frames = [self._make_unseen(p) for p in range(N)]
        else:
            self.floor_frames = {True: [self.tile_floor], False: [self.tile_floor_dim]}
            self.wall_frames = {True: [self.tile_wall], False: [self.tile_wall_dim]}
            self.unseen_frames = [self.tile_unseen]

    def _load_tile_sprites(self, cell: int, n: int) -> dict | None:
        """尝试从 tiles/*.png 加载序列帧 Sprite。

        文件命名约定（scripts/gen_tiles.py 烘焙）：
          floor_lit_<f>.png / floor_dim_<f>.png / wall_lit_<f>.png /
          wall_dim_<f>.png / unseen_<f>.png   （f = 0..n-1）
        任一缺失或损坏 ⇒ 返回 None（调用方回退程序化绘制）。
        加载后按 cell 缩放（最近邻）到与网格对齐；cell==BASE 时即原图。
        纯文件读取、零随机 ⇒ 不变量 #2/#27。
        """
        base = self.tiles_dir
        if not base.is_dir():
            return None

        def load(name: str) -> list | None:
            out: list = []
            for f in range(n):
                p = base / f"{name}_{f}.png"
                if not p.is_file():
                    return None
                try:
                    surf = pygame.image.load(str(p))
                    surf = pygame.transform.scale(surf, (cell, cell))
                except Exception:
                    return None
                out.append(surf)
            return out

        try:
            floor_lit = load("floor_lit")
            floor_dim = load("floor_dim")
            wall_lit = load("wall_lit")
            wall_dim = load("wall_dim")
            unseen = load("unseen")
        except Exception:
            return None
        if None in (floor_lit, floor_dim, wall_lit, wall_dim, unseen):
            return None
        if not self.detail:
            # 小 cell：退化为单帧（与 M24 行为一致，headless 轻量）
            return {
                "floor": {True: [floor_lit[0]], False: [floor_dim[0]]},
                "wall": {True: [wall_lit[0]], False: [wall_dim[0]]},
                "unseen": [unseen[0]],
            }
        return {
            "floor": {True: floor_lit, False: floor_dim},
            "wall": {True: wall_lit, False: wall_dim},
            "unseen": unseen,
        }

    def _make_floor(self, visible: bool, phase: int = 0) -> pygame.Surface:
        # M27 回退：与 _make_floor_surface 同款；tiles/*.png 缺失时用它（视觉零差异）
        return _make_floor_surface(self.cell, visible, phase, self.detail)

    def _make_wall(self, visible: bool, phase: int = 0) -> pygame.Surface:
        return _make_wall_surface(self.cell, visible, phase, self.detail)

    def _make_unseen(self, phase: int = 0) -> pygame.Surface:
        return _make_unseen_surface(self.cell, True, phase, self.detail)

    # ---- 音效（懒初始化 + 静默降级）----
    def _init_audio(self) -> None:
        if not self.sound_on:
            return
        # pygbag/WASM 默认无 wave 模块：缺则直接静音降级，不触发运行时 pip 下载、不崩。
        if _get_wave() is None:
            self.sound_on = False
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._snd_web = self._make_sound(880, 1500, 0.12, 0.22, True)
            self._snd_hit = self._make_sound(200, 80, 0.10, 0.28, False)
            self._snd_step = self._make_sound(140, 120, 0.05, 0.10, False)
            self._snd_swing = self._make_sound(1500, 400, 0.18, 0.18, False)
            self._snd_sense = self._make_sound(1600, 2200, 0.08, 0.16, True)
            self._snd_win = self._make_seq([
                (440, 440, 0.12, 0.20, True),
                (660, 660, 0.12, 0.20, True),
                (880, 880, 0.20, 0.22, True),
            ])
            self._snd_lose = self._make_seq([
                (330, 330, 0.15, 0.20, False),
                (220, 220, 0.15, 0.20, False),
                (140, 140, 0.30, 0.22, False),
            ])
            self.sound_on = True
        except Exception:
            self.sound_on = False
            for attr in ("_snd_web", "_snd_hit", "_snd_step", "_snd_swing",
                         "_snd_sense", "_snd_win", "_snd_lose"):
                setattr(self, attr, None)

    def _make_sound(self, f0: int, f1: int, dur: float, vol: float, up: bool):
        return pygame.mixer.Sound(_synth_buffer([(f0, f1, dur, vol, up)]))

    def _make_seq(self, segments: list[tuple]):
        return pygame.mixer.Sound(_synth_buffer(segments))

    def play_web(self) -> None:
        if self.sound_on and self._snd_web is not None:
            try:
                self._snd_web.play()
            except Exception:
                pass

    def play_hit(self) -> None:
        if self.sound_on and self._snd_hit is not None:
            try:
                self._snd_hit.play()
            except Exception:
                pass

    def play_step(self) -> None:
        if self.sound_on and self._snd_step is not None:
            try:
                self._snd_step.play()
            except Exception:
                pass

    def play_swing(self) -> None:
        if self.sound_on and self._snd_swing is not None:
            try:
                self._snd_swing.play()
            except Exception:
                pass

    def play_sense(self) -> None:
        if self.sound_on and self._snd_sense is not None:
            try:
                self._snd_sense.play()
            except Exception:
                pass

    def play_win(self) -> None:
        if self.sound_on and self._snd_win is not None:
            try:
                self._snd_win.play()
            except Exception:
                pass

    def play_lose(self) -> None:
        if self.sound_on and self._snd_lose is not None:
            try:
                self._snd_lose.play()
            except Exception:
                pass

    # ---- 输入：pygame 事件 → _handle_key 能懂的 token ----
    def translate_key(self, event) -> str | None:
        """把一次 KEYDOWN 翻译成 _handle_key 接受的 token（与终端同构）。"""
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
        # wasm/pygbag 下 SDL 投递的 KEYDOWN 往往不带 unicode 字段（或为空），
        # 用 getattr 兜底避免 AttributeError 炸掉主循环；若仍取不到字符，
        # 再回退到 event.key 的名称（'w'/'g'/'1'…），保证 WASD/道具键在网页版一定可用（#M28 健壮性）。
        u = getattr(event, "unicode", "")
        if not u:
            try:
                name = pygame.key.name(event.key)
                if len(name) == 1:
                    u = name
            except Exception:
                u = ""
        if u:
            return u
        return None

    # ---- 特效（renderer 自身视图状态，不回写 Game）----
    def _spawn_web(self, gx0: int, gy0: int, gx1: int, gy1: int) -> None:
        self.effects.append({
            "kind": "web", "gx0": gx0, "gy0": gy0, "gx1": gx1, "gy1": gy1,
            "ttl": 10, "max": 10,
        })

    def _spawn_flash(self, gx: int, gy: int) -> None:
        self.effects.append({"kind": "flash", "gx": gx, "gy": gy, "ttl": 6, "max": 6})

    def _spawn_burst(self, gx: int, gy: int) -> None:
        self.effects.append({"kind": "burst", "gx": gx, "gy": gy, "ttl": 12, "max": 12})

    def _update_effects(self) -> None:
        alive: list[dict] = []
        for e in self.effects:
            e["ttl"] -= 1
            if e["ttl"] > 0:
                alive.append(e)
        self.effects = alive

    def _detect_attack(self, prev: dict) -> tuple[int, int] | None:
        """对比动作前的怪物 HP 快照，找出被击中的那只的『动作前坐标』。"""
        for m in self.game.monsters:
            p = prev.get(id(m))
            if p is None:
                continue
            if (not m.alive) or m.hp < p[2]:
                return (p[0], p[1])
        return None

    # ---- 单步（run 与单测共用；run 走特效+音效，apply_keys 不走）----
    def step(self, token: str, handle_key) -> str:
        """执行一个按键动作并生成攻击特效/音效。返回 msg（"quit" 表示退出）。"""
        game = self.game
        prev_px, prev_py = game.px, game.py
        prev = {id(m): (m.x, m.y, m.hp) for m in game.monsters if m.alive}
        acted, msg = handle_key(game, token)
        if msg == "quit":
            return "quit"
        if acted:
            target = self._detect_attack(prev)
            moved = (game.px != prev_px or game.py != prev_py)
            if target is not None:
                self._spawn_web(prev_px, prev_py, target[0], target[1])
                self.play_web()
                self.play_swing()
                self.play_hit()
                self._spawn_flash(target[0], target[1])
                self._spawn_burst(target[0], target[1])
            elif moved:
                self.play_step()
            game.monster_turn()
        return msg

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
                if ch == " ":
                    self.screen.blit(self._frame_tile(self.unseen_frames, gx, gy),
                                     (gx * cell, gy * cell))
                    continue
                vis = True if visible is None else ((gx, gy) in visible)
                base = "#"
                if gy < len(game.grid) and gx < len(game.grid[gy]):
                    base = game.grid[gy][gx]
                if base == "#":
                    tile = self._frame_tile(self.wall_frames[vis], gx, gy)
                else:
                    tile = self._frame_tile(self.floor_frames[vis], gx, gy)
                self.screen.blit(tile, (gx * cell, gy * cell))
                self._draw_glyph(ch, gx, gy, vis)
        self._draw_light_glow()
        self._draw_effects()
        self._draw_spider_sense_stings()
        self._draw_vignette()
        self._draw_aim_cursor()  # M30：瞄准模式光标准星（只读 aim_state，不写 Game）
        self._draw_hud()
        self._draw_messages()
        if self.help_shown:
            self._draw_help()
        self._prev_px, self._prev_py = game.px, game.py

    def _draw_aim_cursor(self) -> None:
        """M30：瞄准模式下画光标准星（黄色方框 + 中心十字），按几何约束给颜色提示。

        只读 ``aim_state`` 与 ``game.can_toggle_switch``/``can_destroy_switch``（纯查询），
        不写 ``Game`` 状态、不引入随机（#8 延伸 / #1 不破）。未瞄准时直接返回（零副作用）。
        颜色：绿=可射灭射亮（can_toggle_switch）/ 红=可射碎（can_destroy_switch）/ 灰=够不着。
        """
        if not aim_state.is_active():
            return
        cur = aim_state.cursor()
        if cur is None:
            return
        gx, gy = cur
        game = self.game
        cell = self.cell
        px, py = gx * cell, gy * cell
        can_toggle = game.can_toggle_switch(gx, gy)
        can_destroy = game.can_destroy_switch(gx, gy)
        if can_toggle:
            border = (90, 220, 120)     # 绿：可射灭射亮
        elif can_destroy:
            border = (220, 80, 80)      # 红：可射碎（理论上未碎开关两个都能，这里兜底）
        else:
            border = (160, 160, 160)    # 灰：够不着
        # 黄色方框边框（与绿/红区分，提示「这是光标」）+ 几何约束颜色十字
        pygame.draw.rect(self.screen, (255, 215, 0), (px, py, cell, cell), 2)
        # 中心十字（按几何约束上色）
        cx, cy = px + cell // 2, py + cell // 2
        arm = cell // 3
        pygame.draw.line(self.screen, border, (cx - arm, cy), (cx + arm, cy), 2)
        pygame.draw.line(self.screen, border, (cx, cy - arm), (cx, cy + arm), 2)
        self._prev_hp = getattr(game, "player_hp", 0)
        self.frame += 1
        pygame.display.flip()

    def splash(self, text: str) -> None:
        """首帧启动画面：强制填充不透明底色 + 标题文字并 flip，用于确认 canvas 可见。

        在 WASM/pygbag 下若连 splash 都画不出来，说明 canvas 根本没呈现（环境问题），
        而不是游戏逻辑崩了——此时仍能从异常路径拿到报错。
        """
        self.screen.fill((18, 18, 30))
        try:
            title = self.big_font.render("SPIDER-MAN", True, (255, 255, 255))
            self.screen.blit(title, (24, 24))
            sub = self.font.render(text, True, (220, 220, 235))
            self.screen.blit(sub, (24, 70))
        except Exception:
            pass
        pygame.display.flip()

    def _frame_tile(self, frames: list, gx: int, gy: int) -> pygame.Surface:
        """按 self.frame 在预渲染帧间切换（相位动画）。纯视图，零随机。"""
        n = len(frames)
        if n <= 1:
            return frames[0]
        return frames[(self.frame // 6 + (gx + gy)) % n]

    def _draw_glyph(self, ch: str, gx: int, gy: int, vis: bool) -> None:
        if ch == "@":
            self._draw_spidey(gx, gy, vis)
        elif ch in ("M", "m", "~"):
            m = self.game.monster_at(gx, gy)
            self._draw_enemy(gx, gy, ch, vis, m)
        elif ch == "B":
            m = self.game.monster_at(gx, gy)
            self._draw_boss(gx, gy, vis, m)
        elif ch == "!":
            it = self._item_at(gx, gy)
            self._draw_item(gx, gy, it.key if it is not None else None, vis)
        elif ch == ">":
            self._draw_stairs(gx, gy, vis)
        elif ch == "=":
            self._draw_switch(gx, gy, vis)
        elif ch == "?":
            self._draw_spider_sense(gx, gy)

    def _item_at(self, gx: int, gy: int):
        for it in self.game.items:
            if it.x == gx and it.y == gy:
                return it
        return None

    def _center(self, gx: int, gy: int) -> tuple[float, float]:
        cell = self.cell
        return (gx * cell + cell / 2, gy * cell + cell / 2)

    def _draw_spidey(self, gx: int, gy: int, vis: bool) -> None:
        cell = self.cell
        cxp, cyp = self._center(gx, gy)
        # 待机呼吸（垂直浮动）
        bob = math.sin(self.frame * 0.12) * cell * 0.04
        cyp += bob
        # 攻击突进：读取活动 web 特效方向
        dx = dy = 0.0
        for e in self.effects:
            if e["kind"] == "web" and e["gx0"] == gx and e["gy0"] == gy:
                prog = 1 - e["ttl"] / e["max"]
                lx, ly = e["gx1"] - e["gx0"], e["gy1"] - e["gy0"]
                d = math.hypot(lx, ly) or 1
                push = cell * 0.22 * (1 - abs(prog - 0.5) * 2)  # 中段最大冲量
                dx, dy = lx / d * push, ly / d * push
                break
        cxp += dx
        cyp += dy
        # 受击红闪（跨帧 HP 下降）
        hurt = getattr(self.game, "player_hp", 0) < self._prev_hp
        body = SPIDEY_RED if not hurt else (255, 120, 120)
        r = cell * 0.40
        pygame.draw.circle(self.screen, body, (cxp, cyp), r)
        lw = max(1, cell // 18)
        for k in range(8):
            a = math.radians(k * 45)
            pygame.draw.line(self.screen, (12, 12, 18),
                             (cxp, cyp), (cxp + math.cos(a) * r, cyp + math.sin(a) * r), lw)
        er = r * 0.30
        exo = r * 0.42
        eyo = -r * 0.16
        for sx in (-1, 1):
            ex = cxp + sx * exo
            ey = cyp + eyo
            rect = (ex - er * 0.8, ey - er * 0.6, er * 1.6, er * 1.2)
            pygame.draw.ellipse(self.screen, EYE_WHITE, rect)
            pygame.draw.ellipse(self.screen, (12, 12, 18), rect, max(1, lw))

    def _draw_enemy(self, gx: int, gy: int, ch: str, vis: bool, m) -> None:
        cell = self.cell
        cxp, cyp = self._center(gx, gy)
        # 待机浮动
        bob = math.sin(self.frame * 0.10 + (gx + gy) * 0.7) * cell * 0.04
        cyp += bob
        r = cell * 0.36
        body = (60, 62, 78) if vis else (40, 41, 52)
        pygame.draw.circle(self.screen, body, (cxp, cyp), r)
        if ch == "M":
            eye = (225, 60, 60)
        elif ch == "m":
            eye = (130, 50, 50)
        else:
            eye = (70, 130, 240)   # ~ 听见
        # 眨眼（眼形/亮度随相位振荡）
        blink = math.sin(self.frame * 0.07 + (gx - gy) * 0.9)
        eye_scale = 0.2 if blink > 0.92 else 1.0
        er = r * 0.26 * eye_scale
        for sx in (-1, 1):
            pygame.draw.circle(self.screen, eye, (cxp + sx * r * 0.34, cyp - r * 0.1), er)
        if ch == "~":
            # 声波弧
            for rr in (r * 1.25, r * 1.55):
                pygame.draw.arc(self.screen, (70, 130, 240),
                                (cxp - rr, cyp - rr, rr * 2, rr * 2),
                                math.radians(200), math.radians(340), 1)
        pygame.draw.circle(self.screen, _blend(body, -18), (cxp, cyp), r, max(1, cell // 22))

    def _draw_boss(self, gx: int, gy: int, vis: bool, m) -> None:
        """M25 最终层 Boss「绿魔」：程序化面孔（南瓜头 + 锯齿笑 + 紫帽尖），纯图元、零随机。

        沿用玩家的呼吸浮动；半血暴怒（monster.effective_attack > base）时脸色转暗红、加一圈怒光，
        纯视图状态、不回写 Game（#1/#2/#8 延伸）。字形 `B` 只在此绘制，与终端同态。
        """
        cell = self.cell
        cxp, cyp = self._center(gx, gy)
        bob = math.sin(self.frame * 0.12 + (gx + gy) * 0.7) * cell * 0.05
        cyp += bob
        enraged = bool(m is not None and getattr(m, "boss", False)
                       and m.effective_attack > m.attack)
        r = cell * 0.46                       # Boss 比杂鱼大一圈，视觉上就是威胁
        body = (58, 150, 70) if vis else (38, 95, 46)
        if enraged:
            body = (150, 70, 55)              # 暴怒：脸色转暗红
        # 怒光（暴怒时一圈脉动红环，确定性、按 frame 振荡）
        if enraged:
            pulse = (cell * 0.58) * (1 + 0.06 * math.sin(self.frame * 0.3))
            pygame.draw.circle(self.screen, (200, 60, 50), (cxp, cyp), pulse, max(1, cell // 16))
        # 南瓜头主体
        pygame.draw.circle(self.screen, body, (cxp, cyp), r)
        # 帽尖（绿魔招牌尖顶，朝上）
        pygame.draw.polygon(self.screen, _blend(body, 40),
                            [(cxp, cyp - r * 1.35), (cxp - r * 0.28, cyp - r * 0.7),
                             (cxp + r * 0.28, cyp - r * 0.7)])
        # 锯齿邪笑（黄）
        mouth = (240, 210, 70)
        for k in range(5):
            a0 = math.radians(200 + k * 32)
            a1 = math.radians(200 + (k + 1) * 32)
            pygame.draw.line(self.screen, mouth,
                             (cxp + math.cos(a0) * r * 0.9, cyp + math.sin(a0) * r * 0.55),
                             (cxp + math.cos(a1) * r * 0.9, cyp + math.sin(a1) * r * 0.55),
                             max(1, cell // 18))
        # 眼睛（白底黑瞳，邪笑时眯）
        blink = math.sin(self.frame * 0.07 + (gx - gy) * 0.9)
        es = 0.25 if blink > 0.92 else 1.0
        er = r * 0.24 * es
        for sx in (-1, 1):
            ex = cxp + sx * r * 0.4
            ey = cyp - r * 0.18
            pygame.draw.ellipse(self.screen, (245, 245, 235),
                                (ex - er, ey - er * 0.7, er * 2, er * 1.4))
            pygame.draw.ellipse(self.screen, (12, 12, 18),
                                (ex - er * 0.5, ey - er * 0.4, er, er * 0.9))
        pygame.draw.circle(self.screen, _blend(body, -18), (cxp, cyp), r, max(1, cell // 20))

    def _draw_item(self, gx: int, gy: int, key: str | None, vis: bool) -> None:
        cell = self.cell
        cxp, cyp = self._center(gx, gy)
        tint = ITEM_TINT.get(key, (230, 200, 50))
        if key == "web_cartridge":
            r = cell * 0.26
            pygame.draw.circle(self.screen, tint, (cxp, cyp), r)
            for k in range(4):
                a = math.radians(k * 90 + 45)
                pygame.draw.line(self.screen, (235, 245, 255),
                                 (cxp, cyp), (cxp + math.cos(a) * r, cyp + math.sin(a) * r), 1)
        elif key == "sandwich":
            w = cell * 0.5
            h = cell * 0.34
            pygame.draw.rect(self.screen, tint, (cxp - w / 2, cyp - h / 2, w, h), 0)
            pygame.draw.rect(self.screen, (120, 80, 40),
                             (cxp - w / 2, cyp - h / 6, w, h / 3), 0)
        elif key == "nano_boost":
            r = cell * 0.28
            pygame.draw.circle(self.screen, tint, (cxp, cyp + r * 0.2), r * 0.8)
            pygame.draw.polygon(self.screen, tint,
                                [(cxp, cyp - r), (cxp - r * 0.7, cyp + r * 0.4),
                                 (cxp + r * 0.7, cyp + r * 0.4)])
        elif key == "decoy":
            w = cell * 0.42
            h = cell * 0.5
            pygame.draw.rect(self.screen, tint, (cxp - w / 2, cyp - h / 2, w, h), 0)
            pygame.draw.line(self.screen, (90, 90, 100),
                             (cxp - w / 2, cyp), (cxp + w / 2, cyp), 2)
        else:
            r = cell * 0.28
            pygame.draw.circle(self.screen, tint, (cxp, cyp), r)

    def _draw_stairs(self, gx: int, gy: int, vis: bool) -> None:
        cell = self.cell
        cxp, cyp = self._center(gx, gy)
        col = (60, 210, 110) if vis else (40, 130, 70)
        for i in range(3):
            off = (i - 1) * cell * 0.18
            y = cyp + off
            pygame.draw.line(self.screen, col,
                             (cxp - cell * 0.32, y - cell * 0.12),
                             (cxp, y + cell * 0.05), 2)
            pygame.draw.line(self.screen, col,
                             (cxp, y + cell * 0.05),
                             (cxp + cell * 0.32, y - cell * 0.12), 2)

    def _draw_switch(self, gx: int, gy: int, vis: bool) -> None:
        cell = self.cell
        cxp, cyp = self._center(gx, gy)
        col = (235, 205, 60) if vis else (150, 130, 40)
        w = cell * 0.5
        h = cell * 0.34
        pygame.draw.rect(self.screen, col, (cxp - w / 2, cyp - h / 2, w, h), 0)
        pygame.draw.rect(self.screen, (60, 50, 20), (cxp - w / 2, cyp - 2, w, 4), 0)

    def _draw_spider_sense(self, gx: int, gy: int) -> None:
        cell = self.cell
        cxp, cyp = self._center(gx, gy)
        # 扩散同心环（M24 升级：取代单团脉冲），随帧外扩淡出
        rings = 3
        for i in range(rings):
            phase = (self.frame * 0.05 + i / rings) % 1.0
            rr = cell * (0.30 + 0.55 * phase)
            alpha = int(120 * (1 - phase))
            if alpha <= 0:
                continue
            surf = pygame.Surface((cell, cell), pygame.SRCALPHA)
            pygame.draw.circle(surf, (225, 40, 50, alpha), (cell / 2, cell / 2), rr, 2)
            self.screen.blit(surf, (gx * cell, gy * cell))

    def _draw_effects(self) -> None:
        cell = self.cell
        for e in self.effects:
            a = int(255 * (e["ttl"] / e["max"]))
            if e["kind"] == "web":
                # 蛛网从玩家向目标「行进」（随 ttl 减小而伸长）
                frac = 1 - e["ttl"] / e["max"]
                x0, y0 = self._center(e["gx0"], e["gy0"])
                tx, ty = self._center(e["gx1"], e["gy1"])
                x1 = x0 + (tx - x0) * frac
                y1 = y0 + (ty - y0) * frac
                pygame.draw.line(self.screen, (235, 245, 255, a), (x0, y0), (x1, y1), 2)
            elif e["kind"] == "flash":
                cxp, cyp = self._center(e["gx"], e["gy"])
                surf = pygame.Surface((cell, cell), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 255, 255, a), (cell / 2, cell / 2), cell * 0.4)
                self.screen.blit(surf, (e["gx"] * cell, e["gy"] * cell))
            elif e["kind"] == "burst":
                # 命中火花：扩散同心环
                cxp, cyp = self._center(e["gx"], e["gy"])
                frac = 1 - e["ttl"] / e["max"]
                surf = pygame.Surface((cell, cell), pygame.SRCALPHA)
                for k in range(2):
                    rr = cell * (0.15 + 0.35 * frac) + k * cell * 0.12
                    aa = int(a * (1 - k * 0.5))
                    pygame.draw.circle(surf, (255, 240, 200, aa),
                                       (cell / 2, cell / 2), rr, 2)
                self.screen.blit(surf, (e["gx"] * cell, e["gy"] * cell))

    # ---- 氛围层（M24）----
    def _draw_light_glow(self) -> None:
        game = self.game
        if not getattr(game, "light_enabled", False):
            return
        if self._glow is None:
            self._glow = self._make_glow(self.cell)
        cell = self.cell
        gw, gh = self._glow.get_size()
        visible = game.visible if game.fov_enabled else None
        for gy in range(game.height):
            for gx in range(game.width):
                if visible is not None and (gx, gy) not in visible:
                    continue
                try:
                    lvl = game.light_level_at(gx, gy)
                except Exception:
                    continue
                if lvl < LIGHT_LIT:
                    continue
                self.screen.blit(self._glow,
                                 (gx * cell - (gw - cell) / 2,
                                  gy * cell - (gh - cell) / 2),
                                 special_flags=pygame.BLEND_ADD)

    def _make_glow(self, cell: int) -> pygame.Surface:
        g = pygame.Surface((cell * 2, cell * 2), pygame.SRCALPHA)
        c = cell
        for r in range(c, 0, -1):
            alpha = int(70 * (1 - r / c))
            if alpha <= 0:
                continue
            pygame.draw.circle(g, (255, 235, 170, alpha), (c, c), r)
        return g

    def _draw_vignette(self) -> None:
        if not self.detail:
            return
        w = self.game.width * self.cell
        h = self.game.height * self.cell
        if self._vignette is None:
            self._vignette = self._make_vignette(w, h)
        self.screen.blit(self._vignette, (0, 0))

    def _make_vignette(self, w: int, h: int) -> pygame.Surface:
        sw, sh = max(2, w // 6), max(2, h // 6)
        small = pygame.Surface((sw, sh), pygame.SRCALPHA)
        cx, cy = sw / 2.0, sh / 2.0
        maxd = math.hypot(cx, cy) or 1.0
        for yy in range(sh):
            for xx in range(sw):
                d = math.hypot(xx - cx, yy - cy) / maxd
                a = int(150 * max(0.0, d - 0.55) ** 1.5)
                small.set_at((xx, yy), (0, 0, 0, a))
        return pygame.transform.smoothscale(small, (w, h))

    def _draw_spider_sense_stings(self) -> None:
        """对比当前蜘蛛感应集合与上一帧，对新出现的威胁播放刺痛音（纯视图）。"""
        game = self.game
        if not getattr(game, "fov_enabled", False):
            return
        sense = set()
        try:
            for m in game.spider_sense():
                sense.add((m.x, m.y))
        except Exception:
            return
        if sense - self._prev_sense:
            self.play_sense()
        self._prev_sense = sense

    # ---- HUD（主题化）----
    def _draw_hud(self) -> None:
        game = self.game
        cell = self.cell
        y0 = game.height * cell
        W = self.screen.get_width()
        # 红蓝标题条
        pygame.draw.rect(self.screen, SPIDEY_RED, (0, y0, W, 26))
        pygame.draw.rect(self.screen, SPIDEY_BLUE, (0, y0 + 26, W, 4))
        t = self.font.render("SPIDER-MAN", True, TITLE_RGB)
        self.screen.blit(t, (8, y0 + 3))
        sub = self.font.render("纽约暗夜 · 蛛网行动", True, (220, 220, 235))
        self.screen.blit(sub, (W - sub.get_width() - 8, y0 + 4))

        # 血条
        hpw = 170
        ratio = game.player_hp / max(1, game.player_max_hp)
        bx, by, bh = 8, y0 + 40, 14
        pygame.draw.rect(self.screen, (40, 20, 24), (bx, by, hpw, bh))
        pygame.draw.rect(self.screen, SPIDEY_RED, (bx, by, int(hpw * max(0.0, ratio)), bh))
        lbl = self.font.render(f"HP {game.player_hp}/{game.player_max_hp}",
                               True, TEXT_RGB)
        self.screen.blit(lbl, (bx + hpw + 8, by - 1))

        # 楼层名
        ln = self.font.render(f"第 {game.depth} 层：{game.level_name}", True, TEXT_RGB)
        self.screen.blit(ln, (bx, by + 20))

        # 模式旗标
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
            fl = self.font.render("模式：" + " / ".join(flags), True, (180, 200, 240))
            self.screen.blit(fl, (bx, by + 40))

        # 背包格
        slot = 24
        sx = bx
        sy = y0 + HUD_HEIGHT - 34
        self.screen.blit(self.font.render("背包", True, TEXT_RGB), (sx, sy - 16))
        for i in range(5):
            x = sx + i * (slot + 4)
            pygame.draw.rect(self.screen, (34, 36, 50), (x, sy, slot, slot), 0)
            pygame.draw.rect(self.screen, (70, 74, 96), (x, sy, slot, slot), 1)
            if i < len(game.inventory):
                it = game.inventory[i]
                tint = ITEM_TINT.get(it.key, (230, 200, 50))
                pygame.draw.circle(self.screen, tint,
                                   (x + slot / 2, sy + slot / 2), slot * 0.32)
                num = self.font.render(str(i + 1), True, (10, 10, 14))
                self.screen.blit(num, (x + 2, sy + 1))

        # 操作提示
        hint = self.font.render(
            "WASD移动 撞怪攻击 · G拾取 · 1-5道具 · E突袭 · F手电 · >下潜 · 空格等待 · ?帮助 · Q退出",
            True, (170, 172, 190))
        self.screen.blit(hint, (8, y0 + HUD_HEIGHT - 14))

    def _draw_messages(self) -> None:
        if not self.messages:
            return
        last = self.messages[-1]
        surf = self.font.render(last[:90], True, (240, 220, 120))
        self.screen.blit(surf, (8, self.game.height * self.cell - 2))

    def _draw_help(self) -> None:
        surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        surf.fill((120, 20, 26, 210))    # 红幕
        self.screen.blit(surf, (0, 0))
        bar = pygame.Surface((self.screen.get_width(), 30), pygame.SRCALPHA)
        bar.fill((26, 54, 120, 230))     # 蓝条
        self.screen.blit(bar, (0, 0))
        self.screen.blit(self.font.render("操作说明", True, (255, 255, 255)), (12, 6))
        for i, line in enumerate(self.help_text.split("\n")):
            t = self.font.render(line, True, (245, 240, 235))
            self.screen.blit(t, (20, 40 + i * (self.font.get_height() + 4)))

    # ---- 动作应用（apply_keys 与 --play 终端路径同构，不含特效/音效）----
    def apply_keys(self, handle_key, seq: list[str]) -> None:
        """按 token 序列执行动作（与 --play 终端路径同构）。无绘制、无特效。"""
        for token in seq:
            acted, msg = handle_key(self.game, token)
            if msg == "quit":
                break
            if acted:
                self.game.monster_turn()
            if self.game.player_dead:
                break

    # ---- 主循环 ----
    def _pump_events(self, handle_key) -> str | None:
        """处理一帧累积的 pygame 事件；返回 'quit' 或 None（继续）。

        同步 run 与异步 async_run 共用 ⇒ 两条主循环逻辑零漂移（#2 精神，#28 网页化不变式）。
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                token = self.translate_key(event)
                if token is None:
                    continue
                if token == "?":
                    self.help_shown = not self.help_shown
                    continue          # 帧末统一 draw
                msg = self.step(token, handle_key)
                if msg == "quit":
                    return "quit"
        return None

    def run(self, handle_key, fps: int = 30) -> str:
        """窗口主循环（桌面 / 同步）。handle_key 即 main.py 的 _handle_key（与终端同函数）。

        每帧：读事件 → step（含特效/音效）→ 结局判定 → draw。
        返回 'win' / 'dead' / 'quit'。
        """
        self._hk = handle_key
        clock = pygame.time.Clock()
        self.draw()
        try:
            while True:
                res = self._pump_events(handle_key)
                if res is not None:
                    return res
                end = self._check_ending(wait=True)
                if end is not None:
                    return end
                self._update_effects()
                self.draw()
                clock.tick(fps)
        finally:
            aim_state.reset()  # M30：游戏结束复位瞄准状态，避免跨局串扰
            pygame.quit()

    async def async_run(self, handle_key, fps: int = 30) -> str:
        """Pygbag 浏览器异步主循环（M28 · 网页化）。

        与 run() 逻辑完全一致（共用 _pump_events / step / draw / _check_ending），
        但每帧 `await asyncio.sleep(0)` 把控制权交还浏览器事件循环——wasm 单线程下
        不 yield 就会卡死页面。同 seed + 同按键序列 ⇒ 同结果（不变量 #2，#28 网页化不变式）。
        """
        import asyncio
        self._hk = handle_key
        clock = pygame.time.Clock()
        self.draw()
        err = None
        try:
            while True:
                res = self._pump_events(handle_key)
                if res is not None:
                    return res
                end = self._check_ending(wait=False)
                if end is not None:
                    await self._wait_key_async()
                    return end
                self._update_effects()
                self.draw()
                clock.tick(fps)
                await asyncio.sleep(0)
        except Exception as _e:
            # 异常向上抛给 web.py 顶层 try（显示到浏览器 infobox），
            # 不在此 pygame.quit()，保留最后一帧画面，避免把错误清成灰屏。
            err = _e
            raise
        finally:
            # 仅在正常结束（return）时退出 pygame；异常路径保留画面以便排查。
            if err is None:
                aim_state.reset()  # M30：游戏结束复位瞄准状态，避免跨局串扰
                pygame.quit()

    async def _wait_key_async(self) -> None:
        """异步版「等任意键」：结局横幅已画出后，等玩家按键再返回（不阻塞 wasm 线程）。"""
        import asyncio
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    return
            await asyncio.sleep(0)

    def _check_ending(self, wait: bool = True) -> str | None:
        if self.game.player_dead:
            self.play_lose()
            self._draw_banner("蜘蛛侠被击倒了……（游戏结束）", (200, 60, 60))
            if wait:
                self._wait_key()
            return "dead"
        alive = [m for m in self.game.monsters if m.alive]
        if self.game.depth >= self.max_depth and not alive:
            self.play_win()
            if getattr(self.game, "boss_enabled", False) and self.game.boss is not None \
                    and not self.game.boss.alive:
                self._draw_banner("蜘蛛侠把绿魔掀翻在楼顶！（你赢了！）",
                                  (90, 200, 120))
            else:
                self._draw_banner("三层清场，蜘蛛侠摆荡着回家吃三明治。（你赢了！）",
                                  (90, 200, 120))
            if wait:
                self._wait_key()
            return "win"
        return None

    def _draw_banner(self, text: str, color: tuple[int, int, int]) -> None:
        surf = self.big_font.render(text, True, color)
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
