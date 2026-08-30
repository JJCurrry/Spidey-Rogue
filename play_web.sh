#!/usr/bin/env bash
# Spider-Man roguelike - 网页版启动器（M28 网页化 + M29 localStorage 存档）
# 运行即起 pygbag 本地预览服务器，浏览器打开提示地址即可玩网页版。
# 首次使用先装网页构建依赖：pip install -r requirements-web.txt
# 若要产出可托管的静态包，改用 build_wasm.sh（pygbag --build web.py）。
set -e
cd "$(dirname "$0")"
python3 -m pygbag web.py
