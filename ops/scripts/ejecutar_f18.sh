#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${PYTHON_BIN:-python}"
salida_raiz="${1:-${repo_dir}/runs/f18_augmented}"
dir_shards="${DIR_SHARDS:-${repo_dir}/results/dl/shards}"

cd "${repo_dir}"
mkdir -p "${salida_raiz}"

"${python_bin}" ops/checks/preflight_f18.py \
  --dir-shards "${dir_shards}" \
  --fraccion-paced 0.03 \
  --salida "${salida_raiz}/preflight.json"

"${python_bin}" scripts/auditar_paced.py \
  --salida "${salida_raiz}/auditoria_paced"

smoke_dir="${salida_raiz}/smoke_gpu"
if [[ ! -f "${smoke_dir}/gate_smoke.txt" ]]; then
  "${python_bin}" scripts/entrenar_baseline_dl.py \
    --epocas 1 --batch 64 --lr 1e-4 \
    --augmentacion --fraccion-paced 0.03 --exponente-pesos 0.5 \
    --label-smoothing 0.05 \
    --enmascarar-derivaciones-ausentes --scheduler-coseno \
    --paciencia 0 --nombre-gate gate_smoke.txt \
    --dir-shards "${dir_shards}" --salida "${smoke_dir}"
fi

for semilla in 14 42 73; do
  corrida="${salida_raiz}/seed_${semilla}"
  if [[ -f "${corrida}/gate_f18.txt" ]]; then
    echo "F18 seed ${semilla}: ya terminada, se omite"
    continue
  fi
  "${python_bin}" scripts/entrenar_baseline_dl.py \
    --epocas 40 --batch 64 --lr 1e-4 --semilla "${semilla}" \
    --augmentacion --fraccion-paced 0.03 --exponente-pesos 0.5 \
    --label-smoothing 0.05 \
    --enmascarar-derivaciones-ausentes --scheduler-coseno \
    --paciencia 8 --min-delta 0.001 --nombre-gate gate_f18.txt \
    --dir-shards "${dir_shards}" --salida "${corrida}"
done

echo "F18 completo. Descargar antes de destruir la instancia: ${salida_raiz}"
