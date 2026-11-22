#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${PYTHON_BIN:-python}"
salida_raiz="${1:-${repo_dir}/runs/f21_paced_logit_vt}"
dir_shards="${DIR_SHARDS:-${repo_dir}/results/dl/shards}"
splits_f21="${SPLITS_F21:-${repo_dir}/results/dl/splits_f20_active.csv}"
sidecar="${SIDECAR_HF:-${repo_dir}/results/dl/sidecar_hf_f20_active.csv}"
norm_hf="${NORMALIZACION_HF:-${repo_dir}/results/dl/sidecar_hf_f20_active_normalizacion.json}"

cd "${repo_dir}"
mkdir -p "${salida_raiz}"

"${python_bin}" ops/checks/preflight_f18.py \
  --dir-shards "${dir_shards}" --fraccion-paced 0.03 \
  --salida "${salida_raiz}/preflight_base.json"
"${python_bin}" ops/checks/preflight_f20.py \
  --splits "${splits_f21}" --sidecar "${sidecar}" \
  --normalizacion "${norm_hf}" \
  --salida "${salida_raiz}/preflight_sidecar.json"
"${python_bin}" ops/checks/validar_f21_modelo.py \
  --salida "${salida_raiz}/validacion_modelo.json"
"${python_bin}" scripts/evaluar_sidecar_f20.py \
  --splits "${splits_f21}" --sidecar "${sidecar}" \
  --salida "${salida_raiz}/screening_hf.json" \
  --predicciones "${salida_raiz}/screening_hf_predicciones_val.csv" \
  --distribuciones "${salida_raiz}/screening_hf_distribuciones.csv"

if [[ "$("${python_bin}" -c 'import json,sys; print(json.load(open(sys.argv[1]))["estado"])' "${salida_raiz}/screening_hf.json")" != VERDE ]]; then
  echo "F21 detenido: screening HF activo ROJO." >&2
  exit 2
fi

config=(
  --batch 64 --lr 2e-4 --scheduler-coseno
  --augmentacion --augmentacion-clases VT
  --exponente-pesos 1.0 --label-smoothing 0.0
  --enmascarar-derivaciones-ausentes
  --fusion-hf paced_logit
  --splits "${splits_f21}"
  --sidecar-hf "${sidecar}" --normalizacion-hf "${norm_hf}"
  --dir-shards "${dir_shards}"
)

smoke_dir="${salida_raiz}/smoke_gpu"
if [[ ! -f "${smoke_dir}/resumen.json" ]]; then
  "${python_bin}" scripts/entrenar_baseline_dl.py \
    --epocas 1 --paciencia 0 --nombre-gate gate_smoke.txt \
    "${config[@]}" --salida "${smoke_dir}"
fi

screening="${salida_raiz}/seed_14"
if [[ ! -f "${screening}/resumen.json" ]]; then
  "${python_bin}" scripts/entrenar_baseline_dl.py \
    --epocas 40 --semilla 14 --paciencia 10 --min-delta 0.001 \
    --nombre-gate gate_modelo.txt "${config[@]}" --salida "${screening}"
fi
"${python_bin}" ops/checks/gate_f20.py "${screening}/resumen.json" \
  --salida "${screening}/gate_f21.json"

if [[ "${CONFIRMAR:-0}" == 1 ]]; then
  for semilla in 42 73; do
    corrida="${salida_raiz}/seed_${semilla}"
    if [[ -f "${corrida}/resumen.json" ]]; then
      echo "F21 seed ${semilla}: ya terminada, se omite"
      continue
    fi
    "${python_bin}" scripts/entrenar_baseline_dl.py \
      --epocas 40 --semilla "${semilla}" --paciencia 10 --min-delta 0.001 \
      --nombre-gate gate_modelo.txt "${config[@]}" --salida "${corrida}"
  done
fi

echo "F21 terminado. Descargar antes de destruir: ${salida_raiz}"
