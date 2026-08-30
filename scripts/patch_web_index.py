"""网页版 Loader 修正（M28/M29）。

问题：pygbag 生成的加载器（index.html 的 custom_site()）硬编码运行
`assets/main.py`，但本项目的网页入口是 `web.py`（Pygame GUI + async_run）。
pygbag 把整个工程目录打进包，于是 `assets/main.py` 是「终端自动驾驶 demo」，
`assets/web.py` 才是真正可玩的游戏——结果网页版打开后跑的是文本 demo，
根本不弹游戏窗口（即「进网页版却打不开游戏」）。

修正：把加载器指向 `assets/web.py`。web.py 内部 `import main` 仍能解析到
`assets/main.py`（终端 demo 模块，提供 _handle_key / CONTROLS_HELP），不会循环导入。

本脚本在 `pygbag --build web.py` 之后运行，补丁两处：
  1. build/web/index.html        —— 已产出的静态包（部署/双击打开的直接入口）
  2. build/web-cache/*.tmpl      —— pygbag 缓存的模板；改它能让 `pygbag web.py`
                                   预览服务器与后续 --build 都自动生成正确的 index.html

用法（在仓库根目录执行）：
    python scripts/patch_web_index.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OLD = 'appdir / "assets" / "main.py"'
NEW = 'appdir / "assets" / "web.py"  # M28/M29 网页版入口：运行 web.py（Pygame GUI + async_run），而非终端 demo main.py'


def _patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if OLD not in text:
        if NEW in text:
            return False  # 已打过补丁
        return False  # 找不到目标行，跳过（避免误改）
    text = text.replace(OLD, NEW, 1)
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    patched = []

    idx = ROOT / "build" / "web" / "index.html"
    if idx.is_file() and _patch_file(idx):
        patched.append(str(idx))

    cache = ROOT / "build" / "web-cache"
    if cache.is_dir():
        for tmpl in cache.glob("*.tmpl"):
            if _patch_file(tmpl):
                patched.append(str(tmpl))

    if patched:
        print("[patch_web_index] 已修正加载器入口 -> assets/web.py:")
        for p in patched:
            print("  -", p)
    else:
        print("[patch_web_index] 无需修正（index.html 已是 web.py，或模板未命中）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
