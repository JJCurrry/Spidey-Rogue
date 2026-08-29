# roguelike-ai-coding · 用 AI Coding 标准方法从 0 做的「MCU 荷兰弟版蜘蛛侠主题」终端 Roguelike

> 这是一个**示范仓库**：把培训 `ai-coding-method` 的「七件套制品 + 流水线」
> 落到一个能跑、能提交、能被门禁拦下的真实游戏项目上。
> 你在**新工作空间**打开它，新会话读 `CLAUDE.md` 就能接手，不靠聊天记录。

---

## 0. 一句话对应表（培训概念 ↔ git 落点）

| 培训材料说的 | 在 git 上的形态 | 本仓库位置 |
|---|---|---|
| **七件套制品** | 版本化 `.md` 文件，随代码提交 | `docs/`（工单/接力/不变量/术语/地图/adr）+ `CLAUDE.md` |
| **① CLAUDE.md 根索引** | 每会话自动读取的入口，≤100 行只放指针 | 根目录 `CLAUDE.md` |
| **③ 接力文件（交接棒）** | 普通文件，**内含 commit hash + 下一步指令** | `docs/接力/HANDOFF-T001.md` |
| **② 任务工单** | 一入一出 + 委托级别 + 验收分级 A-B-C + 变更记录 | `docs/工单/T-001*.md` |
| **⑤ 不变量（红线）** | 文档 + **可机器判定**检查（L1 墙 seed-guard） | `docs/不变量.md` #1 Seed 注入 + `scripts/gate.py` |
| **流水线 L1 墙** | 四道门，提交瞬间拦截 | `scripts/gate.py` + `scripts/hooks/pre-commit` |
| **评审流水线 5 监理** | 多角色证据式审查 | `scripts/review_pipeline.py` |
| **合并门** | 必需评审 / 禁直推 | `CODEOWNERS` + `.github/branch-protection.md` + PR 模板 |

> 本仓库与 `ai-coding-git-demo` 同构，把"Clock 注入"红线换成了游戏里更直观的
> **"Seed 随机必须注入"** 红线——这是 AI Coding「可测性」最经典的纪律。

---

## 1. 怎么跑起来

```bash
# 0) 装好 Python 3.11+（游戏运行需要；门禁也需要）
python --version

# 1) 玩一下（ASCII 渲染 + 程序化三层下潜 + 视野迷雾演示）
python main.py
python main.py --no-fog   # 切回「全图可见」，方便看整层结构
python main.py --stealth  # 开启怪物视野与潜行（小写 m = 还没发现你的敌人）
python main.py --noise    # 再开启听觉（--noise 隐含 --stealth；~ = 听见动静还没看见你）

# 2) 跑 L1 墙四道门（每次改动前必跑）
python scripts/gate.py

# 3) 跑评审流水线 5 监理
python scripts/review_pipeline.py
```

预期：`main.py` 打印按 Seed 生成的三层纽约楼层（房间+走廊、自动撒怪撒道具），
蜘蛛侠逐层清怪、走到楼梯下潜，HP 与背包跨层保留；开启视野时只看得见视线内区域，
走进房间点亮整间，墙后的近处威胁以 `?`（蜘蛛感应）预警；加 `--stealth` 后敌人只在
看得见你时才会被惊动，从它看不见的地方荡过去就是「倒挂突袭」（伤害翻倍、不挨反击）；
再加 `--noise` 则动静也会暴露你——蛛网拳（响 6）、被蛛网弹缠住的怪挣扎（响 7，声源在它自己那儿）、
下潜落地（响 8），而倒挂突袭只有 2、走路完全无声；
`gate.py` 四道门 ALL GREEN（215 测试全绿）；`review_pipeline.py` 无 HIGH。

---

## 2. 在新工作空间开新会话时，贴这段话

> 这是一个用 AI Coding 方法开发、以**MCU 荷兰弟（Tom Holland）版蜘蛛侠（Spider-Man）**为主角的终端 Roguelike（仓库 `roguelike-ai-coding`）。
> 请先读根目录 `CLAUDE.md`，再按 `docs/工单/` 和 `docs/接力/` 接手下一个里程碑。
> 改动前先跑 `python scripts/gate.py`，全绿才能提交；
> **禁止裸调 `random`/`secrets`/`os.urandom`**——随机必须走 `src/rogue/rng.py` 的 `RandomSource`（Seed 注入）。
> 一个里程碑 = 一次提交；提交前更新接力文件（含本次 commit）。

新会话读完 `CLAUDE.md + 最新工单 + 接力 HANDOFF-T001`，就知道：
M1~M8 已经做完（M8 = 噪音与听觉），下一步候选是 **光照衰减 / ANSI 颜色高亮 / 主动制造响动**。

---

## 3. 后续里程碑（一个人持续迭代的路线）

| 里程碑 | 内容 | 触碰的红线 / 纪律 |
|---|---|---|
| M1 ✅ | 格子地图 + 玩家移动 | Seed 注入（暂不触发，地图固定） |
| M2 ✅ | 战斗系统（玩家/怪物 HP、攻击结算） | #3 HP≥0、#2 回合确定性（用 Seed） |
| M3 ✅ | 怪物 AI（简单追击/随机游走） | #1 随机走 `RandomSource` |
| M4 ✅ | 道具 / 背包 | #5 背包容量上限、#6 HP 不超上限 |
| M5 ✅ | 程序化关卡生成（房间+走廊、撒怪撒道具、下潜） | #1 生成随机走 Seed、#2 确定性、**#7 地图连通性** |
| M6 ✅ | 视野 / 渲染层（迷雾 + 房间照明 + 蜘蛛感应） | #1 视野零随机、#2 确定性、**#8 渲染纯净性** |
| M7 ✅ | 怪物视野与潜行（感知 + 警觉状态机 + 倒挂突袭） | #1 感知零随机、#2 确定性、**#9 感知/潜行确定性** |
| M8 ✅ | 噪音与听觉（声音传播 + 四个声源 + 声源误导） | #1 传播零随机、#2 确定性、**#10 噪音/听觉确定性** |
| M9 | 光照衰减（暗处降低怪物感知半径）/ ANSI 颜色高亮 / 主动制造响动 | 待定 |

每完成一个里程碑：跑 `gate` 全绿 → 更新 `docs/接力/*.md`（含本次 commit）→ 提交。

---

## 4. 推到远程（真正"上 git"）

```bash
# 在 GitHub/Gitee/GitLab 建【空】仓库（别勾 README 初始化）
git remote add origin https://github.com/<你>/roguelike-ai-coding.git
git push -u origin main
```

推送后去平台 `Settings → Branches` 给 `main` 开分支保护（规则见 `.github/branch-protection.md`），
把"合并门"在真实平台上立起来。认证用 **Personal Access Token**，不是密码。

---

## 5. 目录速览

```
roguelike-ai-coding/
├── CLAUDE.md                     ① 根索引（≤100 行，只放指针）
├── CODEOWNERS                    合并门 · 必需评审
├── main.py                       运行入口：python main.py
├── scripts/
│   ├── gate.py                   L1 墙四道门（编译/seed-guard/测试/棘轮）
│   ├── review_pipeline.py        评审流水线 5 监理
│   ├── hooks/pre-commit          提交瞬间调用 gate.py
│   ├── gate.{sh,ps1}             本地/CI 共用入口
│   └── .ratchet                  覆盖率棘轮基线（=215）
├── src/rogue/
│   ├── __init__.py               暴露 Game / Monster / Item / Level / RandomSource
│   ├── rng.py                    ★ 唯一 random 入口（RandomSource，Seed 注入）
│   ├── tiles.py                  M5：格子字符常量（#/./@/M/!/> + M6 的空白/? + M7 的 m + M8 的 ~）
│   ├── level.py                  M5：Room / Level / generate_level（房间+走廊 + 连通性兜底）
│   ├── fov.py                    M6 视野几何（射线/半径/房间照明/蜘蛛感应）+ M7 怪物感知几何
│   ├── sound.py                  M8 声音传播几何（Dijkstra 噪声场：空地 1 / 墙 3，会绕路）
│   ├── game.py                   M1~M8：移动/战斗/AI/道具/装载楼层/下潜/视野渲染/潜行/听觉（不含随机）
│   └── __main__.py               python -m rogue
├── tests/                        unittest 零依赖（共 215 例行为规格）
│   ├── test_game.py              M1（7 例，跑在固定教学图上）
│   ├── test_combat.py            M2（10 例）
│   ├── test_ai.py                M3（11 例）
│   ├── test_items.py             M4（23 例）
│   ├── test_level.py             M5（28 例，含不变量 #7 的 30 seed 连通性判定）
│   ├── test_fov.py               M6（42 例，含不变量 #8 的渲染纯净性判定）
│   ├── test_stealth.py           M7（47 例，含不变量 #9 的感知/潜行确定性判定）
│   └── test_noise.py             M8（47 例，含不变量 #10 的噪音/听觉确定性判定）
└── docs/                         七件套
    ├── 不变量.md                ⑤ 红线（#1 Seed 注入 … #10 噪音/听觉确定性）
    ├── 术语表.md                ⑥ 只收望文生义会错的词
    ├── 地图.md                  ⑦ 架构地图
    ├── adr/ADR-001-技术选型.md  ④ 决策记录（技术选型）
    ├── adr/ADR-002-视野与渲染层.md  ④ 决策记录（M6 视野）
    ├── adr/ADR-003-怪物感知与潜行.md  ④ 决策记录（M7 潜行）
├── adr/ADR-004-噪音与听觉.md      ④ 决策记录（M8 听觉）
    ├── 工单/T-001*.md           ② 一入一出 + 委托级别 + 验收分级（至 T-007）
    └── 接力/HANDOFF-T001.md     ③ 交接棒（含 commit + 下一步）
```
