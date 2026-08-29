"""M9 主动制造响动（皇后区垃圾桶盖）行为规格（对应工单 T-009 验收 A）。

核心红线覆盖：
- 不变量 #1 随机仅经 RandomSource（投掷几何与响动判定不含任何随机）
- 不变量 #2 回合确定性（落点只依赖 grid + 玩家位置 + 视线；响度是常量表、不掷骰）
- 不变量 #8 throw_decoy 不在 render() 里被调用；render() 只读 alert_cause 不改写它
- 不变量 #10 响动仍只经 emit_noise → Monster.alert(cause=CAUSE_SOUND) 唯一入口生效
- 不变量 #11 投掷几何纯几何、不消耗 RandomSource；诱饵只在听觉开启时出现；
            听觉关闭时既不刷诱饵、也甩不响，M1~M8 的玩法与规格一字节不变
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rogue.game import (Game, CAUSE_SOUND, NOISE_DECOY, DECOY_KEY,
                        DECOY_RANGE)
from rogue.level import Level, generate_level
from rogue.rng import RandomSource
from rogue.tiles import FLOOR, PLAYER, MONSTER, HEARD

# 超宽长廊：玩家 (1,1)，可站到 x=10 —— 用来测射程、视线、声源误导
_WIDE = [
    "############",
    "#@.........#",
    "############",
]
# 一墙之隔：x=4 是墙，挡住玩家对 (5,1)/(6,1) 的视线（测试「看得见落点」这条约束）
_BLOCKED = [
    "#########",
    "#@..#..#",
    "#########",
]
_NO_STAIRS = (-1, -1)


def _make(rows, start=(1, 1), rooms=(), fov=False, stealth=True, noise=True,
          seed=0, stairs=_NO_STAIRS):
    """用固定 rows 搭一局（不撒怪撒道具，只测诱饵）。默认开潜行 + 开听觉。"""
    grid = [list(r.replace("@", FLOOR)) for r in rows]
    lv = Level(grid, list(rooms), start, stairs, 1, "测试层")
    return Game(rng=RandomSource(seed=seed), level=lv, populate=False,
                fov=fov, stealth=stealth, noise=noise)


def _grid_of(rows):
    return [list(r.replace("@", FLOOR)) for r in rows]


class TestDecoySwitch(unittest.TestCase):
    """诱饵挂在 noise 开关下：默认不刷、甩不响；noise=True 时开局脚边给一个。"""

    def test_default_tutorial_grants_no_decoy(self):
        g = Game(rng=RandomSource(seed=0))   # 默认 noise=False
        self.assertFalse(g.noise_enabled)
        self.assertFalse(any(it.key == DECOY_KEY for it in g.items))
        self.assertEqual(g.inventory, [])

    def test_default_procedural_grants_no_decoy(self):
        g = Game.procedural(RandomSource(seed=0), depth=1)  # 默认 noise=False
        self.assertFalse(g.noise_enabled)
        self.assertFalse(any(it.key == DECOY_KEY for it in g.items))

    def test_noise_on_tutorial_grants_a_decoy_at_start(self):
        g = _make(_WIDE, noise=True)
        self.assertTrue(g.noise_enabled)
        decoys = [it for it in g.items if it.key == DECOY_KEY]
        self.assertEqual(len(decoys), 1)
        self.assertEqual((decoys[0].x, decoys[0].y), (g.px, g.py))

    def test_noise_on_procedural_grants_a_decoy_at_start(self):
        g = Game.procedural(RandomSource(seed=19), depth=1, noise=True)
        self.assertTrue(any(it.key == DECOY_KEY for it in g.items))

    def test_throw_is_noop_when_noise_off(self):
        g = _make(_WIDE, noise=False)
        self.assertIsNone(g.throw_decoy(6, 1))

    def test_throw_does_not_consume_item_when_noise_off(self):
        # 听觉关掉也手动塞一个诱饵：必须返回 False 且**不消耗**
        g = _make(_WIDE, noise=False)
        g.spawn_item(DECOY_KEY, g.px, g.py)
        g.pick_up()
        self.assertTrue(any(it.key == DECOY_KEY for it in g.inventory))
        self.assertFalse(g.use_item(0, target=(6, 1)))
        self.assertTrue(any(it.key == DECOY_KEY for it in g.inventory))

    def test_decoy_rejected_by_default_specs(self):
        # 与 test_noise.py 同款哲学：默认/潜行模式下，玩家手里没有任何诱饵
        for g in (Game(rng=RandomSource(seed=0)),
                  Game.procedural(RandomSource(seed=0), depth=1),
                  Game.procedural(RandomSource(seed=0), depth=1, stealth=True)):
            self.assertFalse(any(it.key == DECOY_KEY for it in g.items))
            self.assertFalse(any(it.key == DECOY_KEY for it in g.inventory))


class TestDropTableUnchanged(unittest.TestCase):
    """诱饵不进掉落池：ITEM_KEYS 仍是三项，随机序列不扰动（#1/#2）。"""

    def test_item_keys_still_three(self):
        from rogue.game import ITEM_KEYS
        self.assertEqual(ITEM_KEYS, ("sandwich", "web_cartridge", "nano_boost"))

    def test_decoy_not_in_drop_pool(self):
        from rogue.game import ITEM_KEYS
        self.assertNotIn(DECOY_KEY, ITEM_KEYS)

    def test_procedural_floor_identical_with_or_without_decoy(self):
        # 诱饵是「开局脚边丢一个」，零随机 ⇒ 关听觉与开听觉生成的楼层（地形/怪/非诱饵道具）逐字节相同
        def signature(seed, noise):
            g = Game.procedural(RandomSource(seed=seed), depth=2,
                                stealth=True, noise=noise)
            return (
                [row[:] for row in g.grid],
                [(m.name, m.x, m.y, m.hp) for m in g.monsters],
                sorted((it.key, it.x, it.y) for it in g.items
                       if it.key != DECOY_KEY),
            )
        for seed in (19, 3, 42, 7):
            self.assertEqual(signature(seed, False), signature(seed, True))


class TestThrowGeometry(unittest.TestCase):
    """投掷几何四条硬约束，各自一条用例（不变量 #11）。

    1) 界内且非墙；2) 切比雪夫距离在 1..DECOY_RANGE；
    3) 玩家看得见落点（fov.has_line_of_sight）；任一不满足 ⇒ can_throw 为 False。
    """

    def test_can_throw_rejects_wall(self):
        g = _make(_BLOCKED)   # (4,1) 是墙
        self.assertFalse(g.can_throw(4, 1))

    def test_can_throw_rejects_self_tile(self):
        g = _make(_WIDE)      # 甩在脚下 = 把敌人引到自己身上 ⇒ bug，必须禁
        self.assertFalse(g.can_throw(g.px, g.py))

    def test_can_throw_rejects_out_of_range(self):
        g = _make(_WIDE)      # (8,1) 可见、可通行，但切比雪夫距离 7 > DECOY_RANGE(6)
        self.assertFalse(g.can_throw(8, 1))

    def test_can_throw_rejects_no_line_of_sight(self):
        g = _make(_BLOCKED)   # (6,1) 可通行、距离 5 ≤ 6，但被 (4,1) 的墙挡住视线
        self.assertTrue(g.in_bounds(6, 1) and not g.is_wall(6, 1))
        self.assertFalse(g.can_throw(6, 1))

    def test_can_throw_accepts_valid_landing(self):
        g = _make(_WIDE)      # (6,1) 可见、可通行、距离 5 ≤ 6
        self.assertTrue(g.can_throw(6, 1))

    def test_can_throw_respects_range_upper_bound(self):
        # 距离恰好 = DECOY_RANGE 应放行，再多一格就拒（#4 同款边界观）
        g = _make(_WIDE)
        self.assertTrue(g.can_throw(1 + DECOY_RANGE, 1))
        self.assertFalse(g.can_throw(1 + DECOY_RANGE + 1, 1))


class TestDecoyNoise(unittest.TestCase):
    """成功投掷：在落点发出 NOISE_DECOY，被惊动者扑向落点（调虎离山），画面画 ~。"""

    def _listening_game(self):
        g = _make(_WIDE)              # 玩家 (1,1)，(6,1) 可甩，监听器 (10,1)
        g.spawn_monster("迷途无人机", 10, 1, hp=99, attack=0, behavior="chase")
        return g

    def test_successful_throw_emits_at_landing(self):
        g = self._listening_game()
        heard = g.throw_decoy(6, 1)
        m = g.monsters[0]
        self.assertIn(m, heard)
        self.assertTrue(m.alerted)
        self.assertEqual(m.alert_cause, CAUSE_SOUND)
        self.assertEqual(m.last_seen, (6, 1))          # 声源 = 落点，不是玩家 (1,1)
        self.assertNotEqual(m.last_seen, (g.px, g.py))

    def test_decoy_is_loudest_source(self):
        # 全场最响（比落地声 8 还响一档）——它的全部意义就是响
        self.assertGreater(NOISE_DECOY, 8)

    def test_throw_failure_does_not_emit(self):
        g = _make(_WIDE)
        m = g.spawn_monster("迷途无人机", 9, 1, hp=99, attack=0, behavior="chase")
        # (8,1) 超出射程 ⇒ throw_decoy 返回 None，且不应惊动任何人
        self.assertIsNone(g.throw_decoy(8, 1))
        self.assertFalse(m.alerted)
        self.assertEqual(g.last_noise_loudness, 0)

    def test_listener_rendered_as_tilde(self):
        g = self._listening_game()
        g.throw_decoy(6, 1)
        self.assertEqual(g.render().splitlines()[1][10], HEARD)

    def test_use_item_consumes_decoy_on_success(self):
        g = _make(_WIDE, noise=True)
        g.pick_up()                                   # 诱饵入包
        self.assertTrue(any(it.key == DECOY_KEY for it in g.inventory))
        self.assertTrue(g.use_item(0, target=(6, 1)))
        self.assertFalse(any(it.key == DECOY_KEY for it in g.inventory))

    def test_use_item_does_not_consume_decoy_on_bad_target(self):
        g = _make(_WIDE, noise=True)
        g.pick_up()
        before = len(g.inventory)
        # 落点非法（脚下）→ 甩不出去 → 不消耗
        self.assertFalse(g.use_item(0, target=(g.px, g.py)))
        self.assertEqual(len(g.inventory), before)

    def test_decoy_without_target_is_a_noop_and_not_consumed(self):
        # use_item 对诱饵若不给 target，规整成非法坐标 ⇒ 不消耗（向后兼容签名）
        g = _make(_WIDE, noise=True)
        g.pick_up()
        before = len(g.inventory)
        self.assertFalse(g.use_item(0))
        self.assertEqual(len(g.inventory), before)


class TestUseItemBackwardCompat(unittest.TestCase):
    """use_item 的 target 只对诱饵有意义；其余三件道具传不传都一样。"""

    def test_sandwich_ignores_target(self):
        g = _make(_WIDE)
        g.spawn_item("sandwich", g.px, g.py)
        g.pick_up()
        g.player_hp = 5
        self.assertTrue(g.use_item(0, target=(9, 9)))   # target 应被忽略
        self.assertGreater(g.player_hp, 5)

    def test_web_cartridge_ignores_target(self):
        g = _make(_WIDE)
        victim = g.spawn_monster("街头小混混", 2, 1, hp=99, attack=0,
                                 behavior="chase")
        g.spawn_item("web_cartridge", g.px, g.py)
        g.pick_up()
        self.assertTrue(g.use_item(0, target=(9, 9)))   # target 应被忽略
        self.assertEqual(victim.hp, 99 - 5)


class TestDecoyDeterminism(unittest.TestCase):
    """不变量 #11：投掷几何纯几何、不消耗 RandomSource；响动只经 emit_noise 生效。"""

    def test_decoy_does_not_consume_random(self):
        a = _make(_WIDE, noise=False)
        b = _make(_WIDE, noise=True)
        b.pick_up()                       # 诱饵入包（零随机）
        b.throw_decoy(6, 1)               # 纯几何投掷
        b.render()
        # 两边 rng 序列必须完全一致：投掷/渲染都没碰 RandomSource
        self.assertEqual([a.rng.int(0, 999) for _ in range(5)],
                         [b.rng.int(0, 999) for _ in range(5)])

    def test_emit_noise_through_decoy_does_not_touch_world(self):
        # 只改 alerted / last_seen / alert_cause，不动地形、道具、HP、怪物位置
        g = Game.procedural(RandomSource(seed=11), depth=2, stealth=True,
                            noise=True)
        g.spawn_item(DECOY_KEY, g.px, g.py)
        g.pick_up()
        snapshot = ([row[:] for row in g.grid], g.player_hp,
                    [(it.key, it.x, it.y) for it in g.items],
                    [(m.name, m.x, m.y, m.hp) for m in g.monsters])
        g.use_item(0, target=(g.px + 2, g.py))
        self.assertEqual(([row[:] for row in g.grid], g.player_hp,
                          [(it.key, it.x, it.y) for it in g.items],
                          [(m.name, m.x, m.y, m.hp) for m in g.monsters]),
                         snapshot)

    def test_same_seed_same_run_with_decoy(self):
        moves = [(1, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 0)]

        def run(seed):
            g = Game.procedural(RandomSource(seed=seed), depth=2,
                                stealth=True, noise=True)
            g.pick_up()                    # 把开局诱饵收进包
            out = [g.render()]
            for dx, dy in moves:
                g.move(dx, dy)
                g.monster_turn()
                if any(it.key == DECOY_KEY for it in g.inventory):
                    g.use_item(0, target=(g.px + 2, g.py))
                out.append((g.render(), g.player_hp,
                            [(m.name, m.x, m.y, m.hp, m.alerted, m.alert_cause)
                             for m in g.monsters]))
            return out

        self.assertEqual(run(19), run(19))

    def test_decoy_granted_on_every_floor(self):
        # 「每层都给一个」：换层后新楼层脚边仍有一个诱饵（零随机）
        g = Game(rng=RandomSource(seed=0),
                 level=generate_level(RandomSource(seed=0), depth=1),
                 populate=False, noise=True)
        g.load_level(generate_level(RandomSource(seed=5), depth=3))
        self.assertTrue(any(it.key == DECOY_KEY for it in g.items))

    def test_render_does_not_change_alert_state(self):
        # 不变量 #8：render() 只读 alert_cause，不改写它
        g = _make(_WIDE)
        m = g.spawn_monster("迷途无人机", 10, 1, hp=99, attack=0,
                            behavior="chase")
        g.throw_decoy(6, 1)
        before = (m.alerted, m.alert_cause, m.last_seen, m.x, m.y, m.hp)
        g.render()
        g.render()
        self.assertEqual((m.alerted, m.alert_cause, m.last_seen, m.x, m.y, m.hp),
                         before)
        self.assertEqual(g.render(), g.render())


if __name__ == "__main__":
    unittest.main()
