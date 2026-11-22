#!/usr/bin/env bash

utils=/opt/supervisor-scripts/utils
. "${utils}/logging.sh"
. "${utils}/environment.sh"
set -eo pipefail

source /venv/main/bin/activate
cd /workspace/ecg
pty ./ops/scripts/ejecutar_f18.sh /workspace/ecg/runs/f18_augmented 2>&1
