"""M15 规格：修正 M3 老追击路径（轴向往复锁死）+ 怪物攻击配平（1~3 → 0~2）。

核心修复：默认 chase（潜行关闭）的 `_step_toward` 改用切比雪夫二次关键字
（close_in=True），与潜行分支统一。此前只比曼哈顿距离、平局按方向顺序裁决，
会挑中「切比雪夫距离没缩小」的那一步，玩家沿轴向往复时怪锁在同一条轴上震荡、
永不贴上（演示 seed 19 实测锁死 30+ 回合）。修法纯几何、零随机（不变量 #2 不变）。

平衡：追击修正让怪物更可靠地贴上，整体威胁上升，故怪物攻击各降 1
（1~3 → 0~2）；实测只修不配平会从 26/30 掉到 22/30，配平后回到 ~28/30。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.game import Game, MonsterKind
from rogue.rng import RandomSource


def _open_arena() -> Game:
    """搭一张 17x17 的全开放房间（仅边界墙），把玩家放在中心、清空怪物。"""
    g = Game(rng=RandomSource(seed=0))
    W = H = 17
    g.grid = [['#' if (x in (0, W - 1) or y in (0, H - 1)) else '.'
               for x in range(W)] for y in range(H)]
    g.width, g.height = W, H
    g.px, g.py = (8, 8)
    g.grid[g.py][g.px] = '@'
    g.monsters = []
    g.update_fov()
    return g


class TestStepTowardCloseIn(unittest.TestCase):
    def test_step_toward_point_tiebreak_differs(self):
        # 曼哈顿平局、切比雪夫不同的两个候选：close_in 必须改变选择
        cands = [(16, 4), (15, 5)]  # 到 (13,4) 的曼哈顿都是 3
        g = _open_arena()
        old = g._step_toward_point(cands, (13, 4), close_in=False)   # 取列表靠前的 (16,4)
        new = g._step_toward_point(cands, (13, 4), close_in=True)    # 取切比雪夫更小的 (15,5)
        self.assertEqual(old, (16, 4))
        self.assertEqual(new, (15, 5))
        self.assertNotEqual(old, new)

    def test_step_toward_uses_close_in(self):
        # M15 修复点：默认 chase 的 _step_toward 现在走 close_in=True
        g = _open_arena()
        g.px, g.py = (13, 4)
        g.grid[g.py][g.px] = '@'
        # 在曼哈顿平局时，必须挑切比雪夫更小的那一步（真的在逼近），而不是方向顺序靠前的
        self.assertEqual(g._step_toward([(16, 4), (15, 5)]), (15, 5))

    def test_close_in_reduces_chebyshev_when_manhattan_ties(self):
        # 纯几何断言：close_in 下选出的那一步，其到目标的切比雪夫距离严格更小
        g = _open_arena()
        goal = (13, 4)
        cands = [(16, 4), (15, 5)]
        chosen = g._step_toward_point(cands, goal, close_in=True)
        cx, cy = chosen
        self.assertEqual(max(abs(cx - goal[0]), abs(cy - goal[1])), 2)  # 切比雪夫 2，优于 (16,4) 的 3


class TestChaseClosesIn(unittest.TestCase):
    def test_chase_reaches_player_in_open_arena(self):
        # 回归：修复后怪物在开放场地能稳定贴上玩家（不退化成原地打转）
        g = _open_arena()
        m = g.spawn_monster("街头小混混", 12, 8, hp=12, attack=0, behavior="chase")
        turns = 0
        while not g.is_adjacent(m.x, m.y) and turns < 12:
            g.monster_turn()
            turns += 1
        self.assertTrue(g.is_adjacent(m.x, m.y),
                        f"修复后怪物应在 12 回合内贴上玩家，实际用了 {turns} 回合仍未相邻")


class TestMonsterTableRebalance(unittest.TestCase):
    def test_attack_values_rebalanced_to_band(self):
        # M15 配平：攻击值各降 1（1~3 → 0~2），仍以切比雪夫/距离规则与 M3 相邻反击叠加
        from rogue import game as _g
        self.assertEqual(
            tuple(k.attack for k in _g.MONSTER_TABLE),
            (0, 0, 1, 1, 2, 1),
        )
        # 不变量 #2 不受配平影响：表是确定性常量，不掷骰
        self.assertTrue(all(0 <= a <= 2 for a in
                            tuple(k.attack for k in _g.MONSTER_TABLE)))


if __name__ == "__main__":
    unittest.main()
