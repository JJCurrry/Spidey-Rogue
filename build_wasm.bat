@echo off
rem Spider-Man roguelike — 网页化构建（M28 · Pygbag）
rem 第一次用先装构建依赖：pip install -r requirements-web.txt
rem   pygbag web.py           本地预览（自动起静态服务器 + websocket 中继，浏览器开提示地址）
rem   pygbag --build web.py   产出静态包到 build/web/（可托管任意静态服务器）
cd /d "%~dp0"
"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m pygbag %*
pause
