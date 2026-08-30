# T-025 · Boss 战与胜利条件闭环

## 一入一出（In/Out）
- **入**：M1~M24 把游戏从「只能看 ASCII 终端 demo」做成「能在真实窗口手动玩、角色会呼吸浮动、
  攻击有蛛网火花、暗夜有氛围光、听得见脚步与摆荡」的完整蜘蛛侠 Roguelike，但**没有真正的终局**——
  演示在 `MAX_DEPTH` 清场就「演示结束」，没有 Boss、没有胜利画面。用户选 **Boss 战与胜利条件闭环**，
  把「无限下潜」收口成一局完整的胜负。
- **出**：在**不碰玩法内核、不引入随机、确定性不变、默认零回归**的前提下，给最终层加一场绿魔
  （Green Goblin）决战，并明确「击败绿魔才算通关」的胜负闭环：
  1. **Boss 实体（纯几何、零随机）**：新增 `Monster.boss` 标志 + `Game` 的 `boss` / `boss_depth`
     开关（opt-in，默认 `boss=False`）。只在「最终层（depth == boss_depth）且 boss 开启」确定性摆下
     绿魔——选离玩家起点曼哈顿最远的房间、房间内中心优先行优先扫描找空位，**不消耗 RandomSource**
     ⇒ 不扰动任何随机序列（#1/#2），同 seed + 同 boss_depth ⇒ 同位置（#2）。
  2. **Boss 体量**：HP `BOSS_HP=30`（是普通怪 5~14 的数倍，构成一场需要周旋的战斗）、攻击
     `BOSS_ATTACK=3`（压在平衡基线 M3「相邻即每回合挨打」内，不破 #1~#6）；半血**暴怒**：
     `effective_attack` 在 `HP ≤ 半` 时确定性 +1（零随机、只缩短不放大）。
  3. **Boss 字形**：渲染恒画 `B`（与 `M`/`m`/`~` 区分，永远是已知威胁）；终端 `color.py` 亮绿、
     GUI `render_pygame._draw_boss` 程序化画绿魔面孔（南瓜头 + 锯齿邪笑 + 紫帽尖，暴怒时脸色转暗红
     + 脉动怒光）。全程序化、零素材、确定性满分。
  4. **胜利闭环**：`Game.is_victory()` 仅在「boss 模式且最终层绿魔被击败且玩家未阵亡」时为真；
     非 boss 模式恒为 False（沿用 M1~M24「清场即收工」语义）。终端 `_ending_banner` / 演示收尾语 /
     GUI `_check_ending` 横幅在 boss 模式下提示「把绿魔掀翻在楼顶」的胜利语。
  5. `tests/test_boss.py`（14 例）覆盖 opt-in 默认零回归 / 最终层刷 Boss / 字形 B / 半血暴怒 /
     胜利判定 / 渲染纯净 / 确定性；`python scripts/gate.py` 四道门全绿（550 → 564）。

## 委托级别
- 红线（不变量）改造：**否**。全在既有红线内新增 opt-in 能力，不放松任何一条。
- 玩法内核改造：**否**。`Game` 核心（rng/level/fov/sound/light/战斗/AI）一字未改；Boss 走既有
  `spawn_monster` / `monster_turn` / `player_attack`，只是多一个带标志的 Monster。
- 视图层改造：**否**（仅新增 `_draw_boss` 与字面量，M22/M23 测试钉死的契约不变）。

## 设计要点（与全项目一致）
- **opt-in 默认关闭**：`boss=False` ⇒ 一字节不变，与 M1~M24 逐字节一致（演示 seed 19 仍第 171 回合
  清场 HP 18/20）。只有显式 `--boss` 才在最终层刷绿魔。
- **确定性摆位不占 rng**：摆位基于已生成 `rooms`（楼层连通，#7 ⇒ 必经可达），纯几何扫描，
  不调用 `self.rng` ⇒ 前几层实体布局与 `boss=False` 逐字节一致（`test_non_final_floors_untouched`
  机器判定 #1/#2）。
- **平衡可复现**：绿魔是最终层唯一怪物（`_populate_level` 在 boss 最终层跳过普通撒怪），
  构成「清场即终局」的干净 Boss 竞技场；攻击压在基线内、半血暴怒确定性，保证演示 `--boss` 仍能在
  回合上限内通关（seed 19 第 171 回合击败绿魔、HP 10/20）。

## 验证
- 门控：`python scripts/gate.py` 四道门全绿（564 例，+14）。
- 回归：`python main.py`（默认）与 M24 逐字节一致（第 171 回合清场 HP 18/20）；
  `python main.py --boss` 最终层刷绿魔、第 171 回合击败、胜利语正确。
- 机器判定：`tests/test_boss.py` —— opt-in 零回归 / 最终层刷 Boss / 字形 B / 半血暴怒 /
  胜利闭环 / 渲染纯净（#8 延伸）/ 确定性（#2）。
- GUI：`SDL_VIDEODRIVER=dummy` 下 `PygameRenderer.draw()` 含 Boss 不崩（暴怒分支覆盖）。

## 关联
- ADR：`docs/adr/ADR-021-Boss战与胜利条件闭环.md`
- 不变量：`docs/不变量.md` #25
- 接力：`docs/接力/HANDOFF-T001.md`（M25 段）
