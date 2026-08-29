#!/bin/sh
# 本地 / CI 共用入口：跑 L1 墙四道门
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$(command -v python3 || command -v python)"
exec "$PY" "$ROOT/scripts/gate.py"
