#!/usr/bin/env bash
# Spider-Man roguelike — 网页版「双击即玩」入口（M28/M29 · Pygbag + localStorage 存档）
# 流程：pygbag 构建静态包 -> 修正加载器入口(web.py) -> 本地静态服务器托管 -> 自动开浏览器
# 依赖：pip install -r requirements-web.txt
# PYTHONUTF8=1 让 pygbag 以 UTF-8 读源码，避免任何 locale 下解码报错。
set -e
export PYTHONUTF8=1
cd "$(dirname "$0")"
python3 -m pygbag --build web.py
python3 scripts/patch_web_index.py
python3 -m http.server 8000 --directory build/web &
SRV=$!
sleep 1
(xdg-open http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null || echo "请在浏览器打开 http://localhost:8000")
wait $SRV
