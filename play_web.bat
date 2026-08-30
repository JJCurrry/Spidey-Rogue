@echo off
rem Spider-Man roguelike - 网页版启动器（M28 网页化 + M29 localStorage 存档）
rem 双击此文件即用浏览器玩网页版（pygbag 本地预览服务器，自动开提示地址）。
rem 首次使用先装网页构建依赖：pip install -r requirements-web.txt
rem 若要产出可托管的静态包，改用 build_wasm.bat（pygbag --build web.py）。
cd /d "%~dp0"
"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m pygbag web.py
pause
