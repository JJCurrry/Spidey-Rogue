@echo off
rem Spider-Man roguelike - GUI 启动器（M22）。
rem 双击此文件进入 Pygame 窗口模式（真正能玩的窗口游戏）。
rem 编辑 flags 后的 --gui 可加：--stealth / --noise / --light / --flashlight
cd /d "%~dp0"
"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" main.py --gui %*
pause
