#!/usr/bin/env bash
set -euo pipefail

python3 -m ruff check server/graph server/agents/tools.py tests
python3 -m mypy --config-file mypy.graph.ini
python3 -m pytest -q tests
