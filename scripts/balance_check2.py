"""验证 M15 修正的三态平衡叙事（临时）：
  (A) 旧追击(close_in=False) + 旧攻击(1,1,2,2,3,2)  → 预期 ~26/30（HANDOFF 现状）
  (B) 新追击(close_in=True)  + 旧攻击(1,1,2,2,3,2)  → 预期 ~22/30（只修不配平）
  (C) 新追击(close_in=True)  + 新攻击(0,0,1,1,2,1)  → 已测 30/30（配平后）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from rogue import Game
from rogue import game as game_mod
from rogue.rng import RandomSource
from rogue.game import MonsterKind
import main as demo

MAX_DEPTH = 3
TURNS_PER_LEVEL = 80

OLD_TABLE = (
    MonsterKind("街头小混混", 8, 1, "chase", 1),
    MonsterKind("迷途无人机", 5, 1, "wander", 1),
    MonsterKind("神秘客幻象", 7, 2, "wander", 3),
    MonsterKind("奥斯本实验体", 12, 2, "chase", 3),
    MonsterKind("电光人残党", 9, 3, "wander", 5),
    MonsterKind("沙人分身", 14, 2, "chase", 5),
)


def run(seed: int, stealth: bool) -> str:
    rng = RandomSource(seed=seed)
    g = Game.procedural(rng, depth=1, fov=True, stealth=stealth)
    for _ in range(1, TURNS_PER_LEVEL * MAX_DEPTH + 1):
        demo._player_act(g)
        g.monster_turn()
        alive = [m for m in g.monsters if m.alive]
        if g.player_dead:
            return "dead"
        if g.depth >= MAX_DEPTH and not alive:
            return "win"
    return "timeout"


def sweep(stealth: bool, n: int = 30) -> int:
    return sum(1 for s in range(n) if run(s, stealth) == "win")


def old_chase(self, candidates):
    return self._step_toward_point(candidates, (self.px, self.py), close_in=False)


# (A) 旧追击 + 旧攻击
Game._step_toward = old_chase
game_mod.MONSTER_TABLE = OLD_TABLE
print(f"(A) 旧追击+旧攻击 默认: {sweep(False)}/30  潜行: {sweep(True)}/30")

# (B) 新追击 + 旧攻击
Game._step_toward = lambda self, c: self._step_toward_point(c, (self.px, self.py), close_in=True)
game_mod.MONSTER_TABLE = OLD_TABLE
print(f"(B) 新追击+旧攻击 默认: {sweep(False)}/30  潜行: {sweep(True)}/30")
