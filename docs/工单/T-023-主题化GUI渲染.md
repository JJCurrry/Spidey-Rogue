# T-023 · Spider-Man 主题化 GUI 渲染（M23）

## 一入一出（In/Out）
- **入**：M22 把 ASCII 视图层换成了 Pygame 窗口，但 v1 是**纯色块**（每格一个
  `pygame.draw.rect`，角色也是字形套颜色）。用户明确指出「画面非常简陋，和蜘蛛侠
  感觉完全无关」。本里程碑就是把 v1 的色块升级为**程序化蜘蛛侠主题渲染**——
  这正是 M22 预留的「Sprite/动画/音效（留 M23）」。
- **出**：在不碰 `Game` 核心、不引入随机、确定性不变的前提下，让窗口真正有
  Spider-Man 味：
  1. 预渲染主题贴图：地板（暗蓝 + 蛛网纹理）、墙（纽约建筑砖缝 + 红蓝描边）、
     未探索（近黑 + 极淡蛛网）；按可见性给明/暗两版。
  2. 玩家 `@` 画成 **蜘蛛侠面具**（红底 + 黑蛛网放射线 + 两只白眼）。
  3. 怪物按字形主题化：`M` 已察觉（亮红眼）/ `m` 未察觉（暗红眼）/ `~` 听见
     （蓝眼 + 声波弧）；按位置读 `game.monster_at` 取实体。
  4. 道具 `!` 按 `item.key` 画不同小图标（蛛网弹=青色蛛球 / 三明治=琥珀方 /
     纳米强化剂=蓝滴 / 垃圾桶盖=灰罐）。
  5. 楼梯 `>` 画成绿色下行箭头门、墙边开关 `=` 画成黄色开关块。
  6. 蜘蛛感应 `?` 画成**红色脉冲光晕**（彼得「蜘蛛感应 tingling」的视觉化）。
  7. 攻击时生成**蛛网特效**（玩家→目标的一缕白蛛丝，数帧内淡出）+ 命中白闪；
     纯视图状态，存于 renderer，不影响 `Game`。
  8. 合成音效（蛛网发射 thwip / 命中闷响），`pygame.mixer` 懒初始化、失败静默、
     默认开但绝不触碰游戏状态。
  9. HUD 主题化：红蓝标题条「SPIDER-MAN」+ 蛛网分隔、红色血条、楼层名、
     背包格（按道具上色）、模式旗标、操作提示。
  10. `tests/test_gui.py` 扩充 M23 纯函数/特效单测；`python scripts/gate.py` 四道门全绿。

## 委托级别
- **S（自主完成）**：范围清晰（只重写视图模块 `render_pygame.py` + 扩测试，不碰
  `src/rogue` 玩法内核）、红线明确（#1 零随机 / #2 确定性 / #8 渲染纯净）、复用
  M22 的 `PygameRenderer` 骨架与 `tile_color`/`pixel_pos`/`translate_key`，是
  「让游戏真正像蜘蛛侠」这一用户诉求的落地。

## 验收分级
- **A（必过，门禁）**：`scripts/gate.py` 四道门 ALL GREEN，且
  `tests/test_gui.py` 的既有 12 例（含 `test_apply_keys_parity_with_terminal`
  确定性回归）零破——证明 GUI 仍只调 `Game` 既有方法、确定性不变；
  `tile_color`/`pixel_pos`/`translate_key` 行为不变；新增 M23 特效/绘制单测全绿。
- **B（建议）**：`python main.py --gui` 打开窗口，能看到蜘蛛侠面具、蛛网地板、
  攻击蛛网特效与主题 HUD；`python main.py`（无 `--gui`）演示与 M22 逐字节一致
  （零回归，GUI 改动不进 `Game`）。

## 范围边界
- **只换视图层，不动玩法内核**：所有美术用 `pygame` 图元**程序化绘制**（不依赖任何
  外部图片/字体素材，保持自包含、可复现、确定性）；只读 `Game` 公开状态
  （grid/render()/monsters/items/stairs/switches/visible/light_field…），只调
  `_handle_key` + `monster_turn`，不新增随机、不修改 `src/rogue/*`。
- **地形贴图消费 `game.grid` + 实体消费 `game.render()` 字形**：两者结合——
  `grid` 给真实地形底（墙/地板），`render()` 字形负责迷雾下的可见性门控与
  实体/特征选择，零漂移。
- **特效是 renderer 的视图状态**：蛛网/闪光存在 `self.effects`，按帧衰减；
  不写 `Game`、不影响确定性（确定性回归测试走 `apply_keys`，不经特效路径）。
- **音效纯装饰**：`pygame.mixer` 懒初始化、整段 `try/except` 包裹；不可用则
  `sound_on=False` 静默降级；音效从不读写游戏状态 ⇒ #2 不变。
- **headless 友好**：沿用 M22 的 `SDL_VIDEODRIVER=dummy` 守卫 + pygame 缺失 skip；
  小 cell（≤16）自动跳过精细纹理，保证测试轻量且不崩。
- **opt-in（默认关闭）**：`--gui` 才进窗口；默认仍是脚本 demo / `--play` 终端，
  行为零回归。

## 不变量增量
- **#23 GUI 主题化渲染纯净**：`PygameRenderer` 的主题化绘制只读 `Game` 公开状态、
  只调 `Game` 既有确定性方法（经 `_handle_key`），不引入任何随机 ⇒ #1/#2 不变；
  消费 `game.grid` + `game.render()` 同一份数据、不改写状态 ⇒ #8 延伸；
  新增的攻击蛛网特效 / 命中闪光 / 脉冲光晕均为 renderer 自身视图状态（按帧衰减、
  不回写 `Game`）；合成音效懒初始化、失败静默、不读写游戏状态；
  GUI 主循环与 `--play` 终端路径同构（共用 `_handle_key`）⇒ 同 seed+同输入序列
  ⇒ 同结果（#2，机器判定 `tests/test_gui.py`）；
  `--gui` 为 opt-in，默认（无 `--gui`）仍走脚本 demo / `--play` 终端，行为零回归。
