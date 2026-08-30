@echo off
rem Spider-Man roguelike — 网页化构建（M28 · Pygbag）
rem 第一次用先装构建依赖：pip install -r requirements-web.txt
rem   pygbag web.py           本地预览（自动起静态服务器，浏览器开提示地址）
rem   pygbag --build web.py   产出静态包到 build/web/（可托管任意静态服务器）
rem
rem 重要：pygbag 生成的加载器默认跑 assets/main.py（本仓库那是「终端自动驾驶 demo」），
rem 网页可玩入口其实是 web.py。所以构建后必须用 scripts/patch_web_index.py
rem 把加载器入口从 main.py 改回 web.py，否则网页版打开后跑的是文本 demo、不弹游戏窗口。
rem PYTHONUTF8=1 让 pygbag 以 UTF-8 读源码，避免非 UTF-8 系统（如中文 Windows GBK）解码报错。
set PYTHONUTF8=1
chcp 65001 >nul 2>&1
cd /d "%~dp0"
set "PY=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
"%PY%" -m pygbag %*
"%PY%" scripts/patch_web_index.py
echo 构建完成：用任意静态服务器托管 build/web/ 即可在浏览器游玩（例如 python -m http.server 8000 --directory build/web）。
pause
