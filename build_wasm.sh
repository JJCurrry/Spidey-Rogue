#!/usr/bin/env bash
# Spider-Man roguelike — 网页化构建（M28 · Pygbag）
# 第一次用先装构建依赖：pip install -r requirements-web.txt
#   pygbag web.py          本地预览（浏览器开提示地址）
#   pygbag --build web.py  产出静态包到 build/web/（可托管任意静态服务器）
#
# 重要：pygbag 加载器默认跑 assets/main.py（本仓库是「终端 demo」），网页可玩入口是 web.py，
# 故构建后需用 scripts/patch_web_index.py 把加载器入口改回 web.py。
# PYTHONUTF8=1 让 pygbag 以 UTF-8 读源码，避免任何 locale 下解码报错。
set -e
export PYTHONUTF8=1
cd "$(dirname "$0")"
python3 -m pygbag "$@"
python3 scripts/patch_web_index.py
echo "构建完成：用任意静态服务器托管 build/web/ 即可在浏览器游玩（例如 python3 -m http.server 8000 --directory build/web）。"
