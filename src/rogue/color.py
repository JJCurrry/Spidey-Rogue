"""ANSI 终端着色（M10 · 纯展示层）。

把 `render()` 产出的 ASCII 地图按字形上色，**不修改任何游戏状态，也不改变字形本身**
——只是给每个字形套一层 ANSI 转义码。因此 `render()` 的输出保持原样，既有
`assertIn("@", render())` 类断言零风险（不变量 #8 渲染纯净性的延伸）。

着色只发生在演示入口 `main.py`（presentation layer），不进入 `Game` / `render()`。
理由：`fov` / `stealth` / `noise` 是「改变显示什么」的玩法开关 ⇒ 挂在 `Game`；
颜色只是「改变怎么画」的纯装饰 ⇒ 留在展示层。这样 M10 对既有 245 例规格零侵入。

纯几何、零随机、确定性：同输入 ⇒ 同输出（不变量 #2 的精神）。
"""
from __future__ import annotations

import os
import sys

RESET = "\033[0m"  # 每个着色字形后复位，避免颜色串到后面的字符

# 字形 → ANSI 转义前缀（开色）。
# 调色板在浅色 / 深色背景都尽量可读：
#   @ 玩家    亮红加粗（呼应红蓝战衣的红）
#   M 已察觉敌 亮品红
#   m 未察觉敌 暗品红
#   ~ 听见动静 亮蓝（声音=蓝）
#   ? 蜘蛛感应 亮青
#   ! 补给    亮黄
#   > 楼梯    亮绿
#   # 墙      亮黑（暗灰）
# 其它（`.` 地板 / ` ` 未探索）保持默认色，确保任何主题下都可读、不强制上色。
GLYPH_COLORS: dict[str, str] = {
    "@": "\033[1;31m",   # 玩家：亮红加粗
    "M": "\033[1;35m",   # 已察觉的敌人：亮品红
    "m": "\033[0;35m",   # 未察觉的敌人：暗品红
    "~": "\033[1;34m",   # 听见动静的敌人：亮蓝
    "?": "\033[1;36m",   # 蜘蛛感应：亮青
    "!": "\033[1;33m",   # 补给：亮黄
    ">": "\033[1;32m",   # 楼梯：亮绿
    "#": "\033[90m",     # 墙：暗灰
}


def colorize(text: str, enabled: bool = True) -> str:
    """把多行地图文本按字形上色。

    - enabled=False ⇒ 原样返回（管道 / 重定向 / NO_COLOR 环境下降级为纯文本）。
    - 只包裹「已知字形」；空格、换行、未知字符原样透传 ⇒ **剥离转义码后 == 原文本**。
    - 纯函数、零随机、确定性：同输入 ⇒ 同输出。
    """
    if not enabled:
        return text
    out: list[str] = []
    for ch in text:
        code = GLYPH_COLORS.get(ch)
        if code is None:
            out.append(ch)
        else:
            out.append(code + ch + RESET)
    return "".join(out)


def should_color(stream=None, env=None) -> bool:
    """是否应该上色：默认「是 TTY 且没被 NO_COLOR 关掉」。

    遵循 https://no-color.org ：设了 NO_COLOR（任意值）就强制无色。
    设了 FORCE_COLOR / CLICOLOR=1 则强制上色。否则按「标准输出是终端」自动判断。
    `main.py` 的 `--color` / `--no-color` 会越过这里的自动判断（见 main）。
    """
    if env is None:
        env = os.environ
    if env.get("NO_COLOR"):
        return False
    if env.get("FORCE_COLOR") or env.get("CLICOLOR") == "1":
        return True
    if stream is None:
        stream = sys.stdout
    try:
        return stream.isatty()
    except Exception:
        return False
