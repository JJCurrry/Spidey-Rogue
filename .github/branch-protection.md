# 分支保护规则（在平台后台开启）

目标分支：`main`

- Require a pull request before merging
- Require status checks to pass：勾 `L1-wall` 的 `gate` 与 `review` job
- Require review from Code Owners
- 禁止直接 push 到 main（对应演示的合并门）
- 建议：每次 PR 附 `python scripts/review_pipeline.py` 输出的监理报告
