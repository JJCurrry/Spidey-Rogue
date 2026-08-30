#!/usr/bin/env python3
"""评审流水线 · 5 监理角色（终端 Roguelike 适配）。

产出证据式监理报告。无 HIGH 则退出 0（可合并）；有 HIGH 退出 1。
仅扫描 src/，避免扫描 docs 文本造成的误报。
"""
from __future__ import annotations
import sys
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
FORBIDDEN = [r"\bimport\s+random\b", r"\bfrom\s+random\b", r"\brandom\.\w+",
             r"\bsecrets\.\w+", r"\bos\.urandom\b", r"\brandint\s*\(", r"\bnp\.random\b"]
RX = [re.compile(p) for p in FORBIDDEN]
ALLOWED = "rng.py"


def role_arch() -> list[str]:
    notes = []
    rng = SRC / "rogue" / "rng.py"
    notes.append("架构：rng.py 存在（唯一随机入口）" if rng.exists()
                 else "架构：❌ 缺少 rng.py（随机入口）")
    return notes


def role_invariant() -> list[str]:
    highs = []
    for f in SRC.rglob("*.py"):
        if f.name == ALLOWED:
            continue
        in_doc = False
        for i, raw in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if '"""' in raw or "'''" in raw:
                in_doc = not in_doc
                continue
            if in_doc:
                continue
            for rx in RX:
                if rx.search(raw):
                    highs.append(f"{f.relative_to(ROOT)}:{i} 裸随机 → 违反不变量#1")
    return highs


def role_scope() -> list[str]:
    warns = []
    # .workbuddy 是 AI 工作记忆目录（非源码、不入版本库），纳入白名单避免常驻误报
    allowed_dirs = {".git", "src", "tests", "docs", "scripts", ".github", ".workbuddy", "tiles"}
    allowed_files = {"README.md", "CLAUDE.md", "CODEOWNERS",
                     ".gitignore", ".pre-commit-config.yaml", "main.py"}
    for p in ROOT.iterdir():
        if p.name in allowed_dirs:
            continue
        if p.is_file() and p.name in allowed_files:
            continue
        warns.append(f"范围：发现非常规顶层条目 {p.name}")
    return warns


def role_test_discipline() -> list[str]:
    notes = []
    tdir = ROOT / "tests"
    tfiles = list(tdir.glob("test_*.py")) if tdir.exists() else []
    notes.append(f"测试纪律：发现 {len(tfiles)} 个测试文件")
    if not tfiles:
        notes.append("测试纪律：❌ 无测试文件")
    return notes


def main() -> None:
    print("# 评审流水线 · 监理报告")
    highs = role_invariant()
    print("\n## 不变量哨兵（红线 #1）")
    if highs:
        for h in highs:
            print("  HIGH ❌", h)
    else:
        print("  OK ✅ 无裸随机")

    print("\n## 架构监理")
    for n in role_arch():
        print("  -", n)

    print("\n## 范围审计")
    warns = role_scope()
    if warns:
        for w in warns:
            print("  WARN ⚠", w)
    else:
        print("  OK ✅ 改动在允许目录内")

    print("\n## 测试纪律")
    for n in role_test_discipline():
        print("  -", n)

    print("\n## 总结监理")
    if highs:
        print("  结论：存在 HIGH，禁止合并。先修红线。")
        sys.exit(1)
    print("  结论：无 HIGH，可进入合并门（仍需 CI 绿 + 必需评审 + 人裁决）。")
    sys.exit(0)


if __name__ == "__main__":
    main()
