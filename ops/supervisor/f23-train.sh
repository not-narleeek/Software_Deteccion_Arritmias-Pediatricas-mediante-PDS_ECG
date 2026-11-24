#!/usr/bin/env bash
set -euo pipefail

source /venv/main/bin/activate
cd /workspace/ecg

export PYTHON_BIN=/venv/main/bin/python
export DIR_SHARDS=/workspace/ecg/shards
exec ops/scripts/ejecutar_f23.sh /workspace/ecg/runs/f23_especialista_vt
