#!/usr/bin/env bash
# Spider-Man roguelike — 网页化构建（M28 · Pygbag）
# 第一次用先装构建依赖：pip install -r requirements-web.txt
#   pygbag web.py          本地预览（浏览器开提示地址）
#   pygbag --build web.py  产出静态包到 build/web/（可托管任意静态服务器）
set -e
cd "$(dirname "$0")"
python3 -m pygbag "$@"
