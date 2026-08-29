#!/usr/bin/env python3
"""L1 墙 · 四道门（终端 Roguelike 适配）。

门1 编译：py_compile src/ + tests/
门2 seed-guard：src/ 除 rng.py 外禁止裸 random/secrets/os.urandom
门3 测试：unittest 全绿，统计用例数
门4 覆盖率棘轮：用例数只增不减（基线存 scripts/.ratchet）
"""
from __future__ import annotations
import os
import re
import sys
import subprocess
import py_compile
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"
RATCHET = ROOT / "scripts" / ".ratchet"

FORBIDDEN = [
    (re.compile(r"\bimport\s+random\b"), "import random"),
    (re.compile(r"\bfrom\s+random\b"), "from random"),
    (re.compile(r"\brandom\.\w+"), "random.<op>"),
    (re.compile(r"\bsecrets\.\w+"), "secrets.<op>"),
    (re.compile(r"\bos\.urandom\b"), "os.urandom"),
    (re.compile(r"\brandint\s*\("), "randint("),
    (re.compile(r"\bnp\.random\b"), "np.random"),
]
ALLOWED_RANDOM_FILE = "rng.py"


def gate1_compile() -> bool:
    print("== 门1 编译（语法）==")
    files = list(SRC.rglob("*.py")) + list(TESTS.rglob("*.py"))
    try:
        for f in files:
            py_compile.compile(str(f), doraise=True)
        print("  编译通过")
        return True
    except py_compile.PyCompileError as e:
        print("  编译失败:", e)
        return False


def gate2_seed_guard() -> bool:
    print("== 门2 seed-guard（不变量 #1）==")
    ok = True
    for f in SRC.rglob("*.py"):
        if f.name == ALLOWED_RANDOM_FILE:
            continue
        in_doc = False
        for ln, raw in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            # 跳过三引号文档串内的文字，避免 prose 误报
            if '"""' in raw or "'''" in raw:
                in_doc = not in_doc
                continue
            if in_doc:
                continue
            for rx, label in FORBIDDEN:
                if rx.search(raw):
                    print(f"  BLOCKED ❌ {f.relative_to(ROOT)}:{ln} 裸随机: {label}")
                    ok = False
    if ok:
        print("  seed-guard 通过（随机仅出自 rng.py）")
    return ok


def gate3_tests():
    print("== 门3 测试（unittest）==")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    has_tests = any(TESTS.rglob("test_*.py"))
    if not has_tests:
        print("  无测试文件 → 视为未过")
        return False, 0
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "discover",
         "-s", "tests", "-p", "test_*.py", "-v"],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
    )
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
    if r.returncode != 0:
        print("  测试失败")
        return False, 0
    combined = r.stdout + "\n" + r.stderr
    m = re.search(r"Ran (\d+) tests?", combined)
    n = int(m.group(1)) if m else 0
    print(f"  测试 {n} 个，全绿")
    return True, n


def gate4_ratchet(n: int) -> bool:
    print("== 门4 覆盖率棘轮（测试数只增不减）==")
    base = int(RATCHET.read_text().strip()) if RATCHET.exists() else 0
    if n < base:
        print(f"  BLOCKED ❌ 测试数 {n} < 基线 {base}（禁止删测试凑绿）")
        return False
    if n > base:
        RATCHET.write_text(str(n))
        print(f"  棘轮提升 {base} → {n}，基线已更新")
    else:
        print(f"  测试数 {n} >= 基线 {base}，棘轮通过")
    return True


def main() -> None:
    ok1 = gate1_compile()
    ok2 = gate2_seed_guard()
    ok3, n = gate3_tests()
    ok4 = gate4_ratchet(n) if ok3 else False
    print("\n==== 四道门结果 ====")
    if ok1 and ok2 and ok3 and ok4:
        print("ALL GREEN ✅ 可进入评审流水线 / 合并")
        sys.exit(0)
    print("BLOCKED ❌ 未通过，禁止提交")
    sys.exit(1)


if __name__ == "__main__":
    main()
