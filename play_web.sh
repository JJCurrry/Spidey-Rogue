#!/usr/bin/env bash
# Spider-Man roguelike - web launcher (M28 web build + M29 localStorage save)
# Runs pygbag local preview server; open the printed URL in a browser to play.
# First install web deps: pip install -r requirements-web.txt
# For a deployable static build use build_wasm.sh (pygbag --build web.py).
# PYTHONUTF8=1 keeps pygbag's internal text reads UTF-8 on any locale.
set -e
export PYTHONUTF8=1
cd "$(dirname "$0")"
python3 -m pygbag web.py
