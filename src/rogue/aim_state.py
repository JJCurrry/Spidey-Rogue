"""M30 交互式瞄准模式 · 控制层视图状态（不属于 ``Game`` 状态）。

本模块是 ``main._handle_key`` 与 ``render_pygame.PygameRenderer.draw`` 共享的「玩家在选目标」
UI 状态，与 ``PygameRenderer.effects``（蛛网特效 / 命中闪光）同性质——只决定「``_handle_key``
怎么解析按键」和「画面上画什么」，**不写 ``Game`` 任何字段、不调 ``RandomSource``**
⇒ 不变量 #1/#2/#8 延伸不破（不变量 #30）。

设计要点（ADR-026）：
- 瞄准状态归属**控制层**而非 ``Game``：污染 ``Game`` 会破坏 ``to_dict``/``apply_state``（M26 存档）
  与 ``render()`` 纯净性（#8）；模块级 ``_AIM`` 字典与 ``main.SAVE_BACKEND`` 同性质、
  可被 ``reset()`` 复位（测试隔离）。
- 瞄准**不消耗回合**：进入 / 退出 / 移动光标都不调 ``monster_turn``，只有确认射灭 / 射碎成功
  才由调用方跑 ``monster_turn``——这是潜行玩法的核心：玩家可以反复瞄准不惊动敌人。
- 几何约束复用 M19：确认时调 ``game.can_toggle_switch``/``can_destroy_switch``，够不着 ⇒
  ``acted=False``、不消耗回合、不改 ``Game``。
- ``move`` 只判 ``game.in_bounds``（不限于射程内，让玩家看见「够不着」的反馈）；
  不引入随机、不写 ``Game``。
"""
from __future__ import annotations

# 模块级控制层视图状态。reset() 可复位（测试隔离 / 跨局清零）。
# 与 main.SAVE_BACKEND 同性质：模块加载即定、可被测试 / 调用方覆盖。
_AIM: dict = {"active": False, "x": 0, "y": 0}


def reset() -> None:
    """复位瞄准状态（测试 setUp / 游戏结束 / 换层时调用，避免跨局串扰）。

    纯状态操作、不调 ``Game``、不引入随机 ⇒ #1/#2/#8 不破。
    """
    _AIM["active"] = False
    _AIM["x"] = 0
    _AIM["y"] = 0


def enter(px: int, py: int) -> None:
    """进入瞄准模式，光标初始位置 = 玩家位置。

    纯状态操作、不调 ``Game``、不引入随机 ⇒ #1/#2/#8 不破。
    """
    _AIM["active"] = True
    _AIM["x"] = px
    _AIM["y"] = py


def exit() -> None:
    """退出瞄准模式（不消耗回合、不改 ``Game``）。"""
    _AIM["active"] = False


def is_active() -> bool:
    """是否处于瞄准模式（``_handle_key`` / ``draw`` / ``_colored`` 共用）。"""
    return bool(_AIM["active"])


def cursor() -> tuple[int, int] | None:
    """当前光标坐标；未瞄准时返回 ``None``。"""
    if not _AIM["active"]:
        return None
    return (_AIM["x"], _AIM["y"])


def move(dx: int, dy: int, game) -> bool:
    """按方向增量移动光标，受 ``game.in_bounds`` 约束（不引入随机、不写 ``Game``）。

    返回是否实际移动（越界 ⇒ 不动、返回 ``False``）。
    光标可在 ``in_bounds`` 内自由移动（不限于射程内，让玩家看见「够不着」的反馈）；
    确认时几何约束（M19 ``can_toggle_switch``/``can_destroy_switch``）拦下、返无效信息。
    """
    if not _AIM["active"]:
        return False
    nx, ny = _AIM["x"] + dx, _AIM["y"] + dy
    if not game.in_bounds(nx, ny):
        return False
    _AIM["x"] = nx
    _AIM["y"] = ny
    return True
