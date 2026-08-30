@echo off
rem Spider-Man roguelike — 网页版「双击即玩」入口（M28/M29 · Pygbag + localStorage 存档）
rem 流程：pygbag 构建静态包 -> 修正加载器入口(web.py) -> 本地静态服务器托管 -> 自动开浏览器
rem 依赖：pip install -r requirements-web.txt
rem PYTHONUTF8=1 让 pygbag 以 UTF-8 读源码，避免非 UTF-8 系统（如中文 Windows GBK）解码报错。
set PYTHONUTF8=1
chcp 65001 >nul 2>&1
cd /d "%~dp0"
set "PY=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
"%PY%" -m pygbag --build web.py
"%PY%" scripts/patch_web_index.py
start "" http://localhost:8000
"%PY%" -m http.server 8000 --directory build/web
pause
