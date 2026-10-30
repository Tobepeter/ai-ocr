#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec "$(uv tool dir)/mineru/bin/python" src/ocr_ui/app.py "$@"
