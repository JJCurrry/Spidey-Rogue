@echo off
rem Spider-Man roguelike - web launcher (M28 web build + M29 localStorage save)
rem Double-click to play in browser via pygbag local preview server.
rem First install web deps: pip install -r requirements-web.txt
rem For a deployable static build use build_wasm.bat (pygbag --build web.py).
rem PYTHONUTF8=1 forces UTF-8 so pygbag can read the UTF-8 source on a
rem non-UTF-8 system (e.g. Chinese Windows GBK) without a UnicodeDecodeError.
set PYTHONUTF8=1
chcp 65001 >nul 2>&1
cd /d "%~dp0"
"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m pygbag web.py
pause
