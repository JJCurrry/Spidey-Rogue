"""随机源注入（可测性红线参考实现）。

不变量 #1：游戏内一切随机必须经由注入的 RandomSource，
禁止在其它模块裸调 random / secrets / os.urandom。
本文件是唯一的 random 入口。
"""
from __future__ import annotations
import random
from typing import Sequence


class RandomSource:
    """封装可重现的随机序列；相同 seed => 相同序列（对应『回合确定性』）。"""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self.seed = seed

    def int(self, low: int, high: int) -> int:
        return self._rng.randint(low, high)

    def choice(self, seq: Sequence):
        return self._rng.choice(list(seq))

    def shuffle(self, seq: list) -> None:
        self._rng.shuffle(seq)

    def chance(self, p: float) -> bool:
        return self._rng.random() < p

    def get_state(self) -> dict:
        """导出内部 PRNG 的完整状态（用于存档 / 读档）。

        返回 JSON 可序列化 dict；读档时经 `set_state` 原样恢复，
        保证「存档处」与「读档后」的随机序列逐字节衔接（对应不变量 #2 / #26）。
        """
        version, internal, gauss = self._rng.getstate()
        return {"version": version, "internal": list(internal), "gauss": gauss}

    def set_state(self, state: dict) -> None:
        """从存档快照恢复内部 PRNG 状态（不引入任何新随机；不变量 #1/#26）。"""
        self._rng.setstate((state["version"], tuple(state["internal"]), state["gauss"]))
