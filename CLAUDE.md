# CLAUDE.md · 终端 Roguelike（AI Coding 标准方法示范）

> 本仓库用 `ai-coding-method` 的七件套 + 流水线从 0 搭建。
> **新会话第一步：读本文档 → 按 `docs/工单/` + `docs/接力/` 接手下一个里程碑。**
> 不要靠聊天记录；记忆都在 `docs/` 里。

## 项目一句话
终端（ASCII）Roguelike 地牢探险；以「最新蜘蛛侠（Spider-Man，MCU 荷兰弟 / Tom Holland 风格）」为主角与美术基调（红蓝战衣、蛛网摆荡、纽约都市地牢）。一个人用标准 AI Coding 方式持续迭代。

## 技术栈（决策见 ADR-001）
- 语言：Python 3.11+；测试：unittest（零依赖）；渲染：终端 ASCII
- 随机：**必须经 Seed 注入**（见 `docs/不变量.md` #1）
- 视野（M6）：纯几何、零随机；**默认关闭**，`Game(..., fov=True)` 显式开启（见 `docs/不变量.md` #8）

## 当前里程碑
- M1 格子地图 + 玩家移动（已提交，见 `docs/接力/HANDOFF-T001.md`）
- M2 战斗系统（已完成，见 `docs/工单/T-002-战斗系统.md`）
- M3 怪物 AI（已完成，见 `docs/工单/T-003-怪物AI.md`）：追击 / 随机游走，确定性（#1/#2/#4）
- M4 道具与背包（已完成，见 `docs/工单/T-004-道具与背包.md`）：拾取 / 使用 / 击杀掉落，背包容量上限 #5、HP 不超上限 #6
- M5 程序化关卡（已完成，见 `docs/工单/T-005-程序化关卡.md`）：房间+走廊生成、自动撒怪撒道具、楼梯下潜（#1/#2/#4/#7）
- M6 视野 / 渲染层（已完成，见 `docs/工单/T-006-视野与渲染层.md`）：迷雾 + 房间照明 + 蜘蛛感应（#1/#2/#8）
- 下一步候选：M7 怪物视野与潜行 / 光照衰减 / 颜色高亮

## 七件套索引（只放指针）
- ① 本文档（根索引）
- ② 工单：`docs/工单/T-001-格子与移动.md` … `docs/工单/T-006-视野与渲染层.md`
- ③ 接力：`docs/接力/HANDOFF-T001.md`（含 commit + 下一步；**全程只有这一根棒**，勿按里程碑新建）
- ④ ADR：`docs/adr/ADR-001-技术选型.md`、`docs/adr/ADR-002-视野与渲染层.md`
- ⑤ 不变量（红线）：`docs/不变量.md`
- ⑥ 术语表：`docs/术语表.md`
- ⑦ 地图：`docs/地图.md`

## 流水线（墙）
- L1 墙四道门：`scripts/gate.py`（编译 → seed-guard → 测试 → 覆盖率棘轮）
- 提交瞬间拦截：`scripts/hooks/pre-commit`
- 评审流水线 5 监理：`scripts/review_pipeline.py`
- CI：`.github/workflows/ci.yml`（见 `scripts/gate.py`）
- 合并门：`CODEOWNERS` + `.github/branch-protection.md` + `.github/PULL_REQUEST_TEMPLATE.md`

## 铁律（每次改动前）
1. 跑 `python scripts/gate.py`，全绿才提交。
2. **禁止裸调 `random`/`secrets`/`os.urandom`**——随机必须走 `src/rogue/rng.py` 的 `RandomSource`（Seed 注入）。
3. 一个里程碑 = 一次提交；提交前更新接力文件（含本次 commit）。
4. 绝不改/删测试凑绿（熔断②）。
