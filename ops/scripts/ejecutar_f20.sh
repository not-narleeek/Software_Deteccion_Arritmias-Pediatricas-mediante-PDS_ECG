#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${PYTHON_BIN:-python}"
salida_raiz="${1:-${repo_dir}/runs/f20_hf_fusion}"
dir_shards="${DIR_SHARDS:-${repo_dir}/results/dl/shards}"
splits_f20="${SPLITS_F20:-${repo_dir}/results/dl/splits_f20_active.csv}"
sidecar="${SIDECAR_HF:-${repo_dir}/results/dl/sidecar_hf_f20_active.csv}"
norm_hf="${NORMALIZACION_HF:-${repo_dir}/results/dl/sidecar_hf_f20_active_normalizacion.json}"

cd "${repo_dir}"
mkdir -p "${salida_raiz}"

"${python_bin}" ops/checks/preflight_f18.py \
  --dir-shards "${dir_shards}" \
  --fraccion-paced 0.03 \
  --salida "${salida_raiz}/preflight_base.json"
"${python_bin}" ops/checks/preflight_f20.py \
  --splits "${splits_f20}" --sidecar "${sidecar}" --normalizacion "${norm_hf}" \
  --salida "${salida_raiz}/preflight_f20.json"
"${python_bin}" scripts/evaluar_sidecar_f20.py \
  --splits "${splits_f20}" --sidecar "${sidecar}" \
  --salida "${salida_raiz}/screening_hf.json" \
  --predicciones "${salida_raiz}/screening_hf_predicciones_val.csv" \
  --distribuciones "${salida_raiz}/screening_hf_distribuciones.csv"
if [[ "$("${python_bin}" -c 'import json,sys; print(json.load(open(sys.argv[1]))["estado"])' "${salida_raiz}/screening_hf.json")" != VERDE ]] \
   && [[ "${FORZAR_GPU:-0}" != 1 ]]; then
  echo "F20 detenido: screening HF activo ROJO; para override explícito use FORZAR_GPU=1." >&2
  exit 2
fi

smoke_dir="${salida_raiz}/smoke_gpu"
if [[ ! -f "${smoke_dir}/resumen.json" ]]; then
  "${python_bin}" scripts/entrenar_baseline_dl.py \
    --epocas 1 --batch 64 --lr 3e-4 --paciencia 0 \
    --enmascarar-derivaciones-ausentes \
    --splits "${splits_f20}" \
    --sidecar-hf "${sidecar}" --normalizacion-hf "${norm_hf}" \
    --nombre-gate gate_smoke.txt --dir-shards "${dir_shards}" \
    --salida "${smoke_dir}"
fi

screening="${salida_raiz}/seed_14"
if [[ ! -f "${screening}/resumen.json" ]]; then
  "${python_bin}" scripts/entrenar_baseline_dl.py \
    --epocas 30 --batch 64 --lr 3e-4 --semilla 14 \
    --paciencia 8 --min-delta 0.001 \
    --enmascarar-derivaciones-ausentes \
    --splits "${splits_f20}" \
    --sidecar-hf "${sidecar}" --normalizacion-hf "${norm_hf}" \
    --nombre-gate gate_modelo.txt --dir-shards "${dir_shards}" \
    --salida "${screening}"
fi
"${python_bin}" ops/checks/gate_f20.py "${screening}/resumen.json" \
  --salida "${screening}/gate_f20.json"

if [[ "${CONFIRMAR:-0}" == 1 ]]; then
  for semilla in 42 73; do
    corrida="${salida_raiz}/seed_${semilla}"
    if [[ -f "${corrida}/resumen.json" ]]; then
      echo "F20 seed ${semilla}: ya terminada, se omite"
      continue
    fi
    "${python_bin}" scripts/entrenar_baseline_dl.py \
      --epocas 30 --batch 64 --lr 3e-4 --semilla "${semilla}" \
      --paciencia 8 --min-delta 0.001 \
      --enmascarar-derivaciones-ausentes \
      --splits "${splits_f20}" \
      --sidecar-hf "${sidecar}" --normalizacion-hf "${norm_hf}" \
      --nombre-gate gate_modelo.txt --dir-shards "${dir_shards}" \
      --salida "${corrida}"
  done
fi

echo "F20 terminado. Descargar antes de destruir la instancia: ${salida_raiz}"
