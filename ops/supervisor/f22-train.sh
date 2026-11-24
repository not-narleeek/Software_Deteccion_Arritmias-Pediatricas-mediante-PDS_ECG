#!/usr/bin/env bash
set -euo pipefail

source /venv/main/bin/activate
cd /workspace/ecg

export PYTHON_BIN=/venv/main/bin/python
export DIR_SHARDS=/workspace/ecg/shards
exec ops/scripts/ejecutar_f22.sh /workspace/ecg/runs/f22_cascada
