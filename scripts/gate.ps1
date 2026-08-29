# 本地入口（Windows）：跑 L1 墙四道门
$ROOT = Split-Path $PSScriptRoot -Parent
$py = (Get-Command python3 -ErrorAction SilentlyContinue)?.Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue)?.Source }
if (-not $py) { Write-Error "未找到 python"; exit 1 }
& $py (Join-Path $ROOT scripts/gate.py)
