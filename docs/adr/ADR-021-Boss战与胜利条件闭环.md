# ADR-021 · Boss 战与胜利条件闭环（M25）

## 状态
已采纳（M25）

## 背景
M1~M24 完成了视野/潜行/听觉/光照/蜘蛛感应体系 + 可键盘操作 + Pygame 窗口渲染 + 蜘蛛侠主题动画美术
与音效，游戏「能玩且像活的蜘蛛侠」。但终局仍是「`MAX_DEPTH` 清场即演示结束」——没有 Boss、没有胜利
画面，无限下潜没有被收口成一局完整的胜负。用户从 HANDOFF 下一步候选里选了「Boss 战与胜利条件闭环」。

约束与 M1~M24 同款：
- 不变量 #1/#2 ⇒ 任何新增随机都会让同 seed 的既有回放作废；
- 不变量 #8 渲染纯净性 ⇒ 视图层不改写游戏状态；
- 熔断②禁止改/删测试凑绿 ⇒ 既有 550 例不能破；
- 项目一贯哲学：新能力默认 opt-in，不加参数时与上一里程碑逐字节一致。

## 决策
- **Boss 是「带标志的普通 Monster」，不是新子系统**：`Monster.boss` 标志 + `Game.boss`（引用）/
  `Game.boss_depth`（出现层，由 `main.py` 传 `MAX_DEPTH`）。只新增 `_spawn_boss` / `_free_boss_tile`
  / `is_victory` / `_monster_glyph` 的 `B` 分支 / `monster_attack` 走 `effective_attack`。战斗、AI、
  掉落、渲染全部复用既有路径 ⇒ 内核零改动。
- **opt-in 默认关闭**：`Game(..., boss=False)` ⇒ 不刷 Boss、不占 rng、不画 `B`，与 M24 逐字节一致。
  只有 `main.py --boss`（→`Game.procedural(..., boss=True, boss_depth=MAX_DEPTH)`）才在最终层刷绿魔。
- **确定性摆位、零随机（#1/#2）**：`_spawn_boss` 选「离玩家起点曼哈顿最远的房间」（遍历顺序固定、
  严格大于取最远），房间内中心优先、否则行优先扫描找第一个可站空位——全程不调用 `self.rng`。
  楼层连通（#7）⇒ 该房间必可达。同 seed + 同 boss_depth ⇒ 同位置（机器判定 `test_same_seed_same_boss_position`）。
  由于 boss 只出现在最终层，且摆位不消耗 rng，前几层实体布局与 `boss=False` 逐字节一致
  （机器判定 `test_non_final_floors_untouched`）。
- **最终层只刷 Boss（干净竞技场）**：`_populate_level` 在「boss 且当前层 == boss_depth」时跳过普通撒怪
  （普通怪的 rng 调用一并省去），最终层只摆绿魔——清场即终局，胜负收口清晰。
- **Boss 体量压在平衡基线内（#1~#6）**：`BOSS_HP=30`（普通怪 5~14 的数倍，构成周旋空间）、
  `BOSS_ATTACK=3`（M3「相邻即每回合挨打」下攻高会换血崩盘，故压在基线内）；半血**暴怒**：
  `Monster.effective_attack` 在 `HP*2 <= max_hp` 时确定性 +1（零随机、只缩短不放大），是 Boss 区别于
  杂鱼的独有机制，由 `monster_attack` 统一读取。
- **渲染纯净（#8 延伸）**：终端 `_monster_glyph` 对 `m.boss` 恒返回 `BOSS='B'`（与 M/m/~ 区分，
  永远是已知威胁）；`color.py::GLYPH_COLORS` 加 `"B": 亮绿`；GUI `render_pygame._draw_glyph` 加 `B`
  分支 → `_draw_boss`（程序化绿魔面孔：南瓜头 + 锯齿邪笑 + 紫帽尖，暴怒时脸色转暗红 + 脉动怒光），
  全程序化、零素材、确定性。视图状态不回写 `Game`。
- **胜利闭环**：`Game.is_victory()` = `boss_enabled and boss is not None and not boss.alive
  and not player_dead`；非 boss 模式恒 False（沿用 M1~M24 语义）。终端 `_ending_banner` / 演示收尾语 /
  GUI `_check_ending` 横幅在 boss 模式下提示「把绿魔掀翻在楼顶」的胜利语。

## 取舍
- **为什么是「最终层刷一只 Boss」而非「每层的 Boss」**：契合「收口成一局胜负」的诉求，且只改最终层
  让前几层零回归、随机序列不受扰，最稳。
- **为什么 Boss 攻击压在 3 而非更高**：M3 规则是「相邻即每回合挨打」，攻击值高会让换血在 20HP 下
  无法承受（M15 配平已验证）；Boss 的「战」体量靠 HP(30) 而非攻击堆出来，半血暴怒给确定性张力。
- **为什么不改 `_player_act` 核心逻辑**：清场语义天然涵盖「击败唯一 Boss」，现有 `_target_monster` /
  攻击 / 下潜流程直接复用，零改动即达成 Boss 战。

## 后果
- 正面：游戏第一次有真正的终局与胜利画面；`--boss` 一条开关即可体验，默认行为完全不变。
- 负面：无（opt-in，且未放松任何红线）。
- 后续可选：Boss 专属招式（南瓜炸弹 AoE）、多阶段、或把 Boss 战做成可选「挑战层」。

## 验证
- `python scripts/gate.py` 四道门全绿（564 例，+14，棘轮 550 → 564）。
- `python main.py`（默认）与 M24 逐字节一致；`python main.py --boss` 第 171 回合击败绿魔、HP 10/20、
  胜利语正确。
- `tests/test_boss.py` 14 例覆盖 opt-in 零回归 / 最终层刷 Boss / 字形 B / 半血暴怒 / 胜利闭环 /
  渲染纯净 / 确定性。
