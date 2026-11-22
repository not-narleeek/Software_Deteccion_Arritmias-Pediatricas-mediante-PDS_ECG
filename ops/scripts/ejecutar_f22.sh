#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${PYTHON_BIN:-python}"
salida_raiz="${1:-${repo_dir}/runs/f22_cascada}"
dir_shards="${DIR_SHARDS:-${repo_dir}/results/dl/shards}"
splits_f22="${SPLITS_F22:-${repo_dir}/results/dl/splits_f20_active.csv}"
sidecar="${SIDECAR_HF:-${repo_dir}/results/dl/sidecar_hf_f20_active.csv}"
norm_hf="${NORMALIZACION_HF:-${repo_dir}/results/dl/sidecar_hf_f20_active_normalizacion.json}"
pred_paced="${PREDICCIONES_PACED:-${repo_dir}/runs/f20_hf_fusion/seed_14/predicciones_val.csv}"

cd "${repo_dir}"
mkdir -p "${salida_raiz}"

[[ -f "${pred_paced}" ]] || { echo "Falta especialista F20: ${pred_paced}" >&2; exit 2; }
"${python_bin}" ops/checks/preflight_f18.py \
  --dir-shards "${dir_shards}" --fraccion-paced 0.03 \
  --salida "${salida_raiz}/preflight_base.json"
"${python_bin}" ops/checks/preflight_f20.py \
  --splits "${splits_f22}" --sidecar "${sidecar}" \
  --normalizacion "${norm_hf}" \
  --salida "${salida_raiz}/preflight_split_activo.json"
"${python_bin}" ops/checks/validar_f22_cascada.py \
  > "${salida_raiz}/validacion_cascada.json"

config=(
  --batch 64 --lr 3e-4 --exponente-pesos 1.0 --label-smoothing 0.0
  --enmascarar-derivaciones-ausentes
  --splits "${splits_f22}" --dir-shards "${dir_shards}"
)

smoke_dir="${salida_raiz}/smoke_gpu"
if [[ ! -f "${smoke_dir}/resumen.json" ]]; then
  "${python_bin}" scripts/entrenar_baseline_dl.py \
    --epocas 1 --paciencia 0 --nombre-gate gate_smoke.txt \
    "${config[@]}" --salida "${smoke_dir}"
fi

evaluar_semilla() {
  local semilla="$1"
  local corrida="${salida_raiz}/seed_${semilla}"
  if [[ ! -f "${corrida}/resumen.json" ]]; then
    "${python_bin}" scripts/entrenar_baseline_dl.py \
      --epocas 30 --semilla "${semilla}" --paciencia 8 --min-delta 0.001 \
      --nombre-gate gate_morfologia.txt "${config[@]}" --salida "${corrida}"
  fi
  "${python_bin}" scripts/evaluar_cascada_f22.py \
    --predicciones-morfologia "${corrida}/predicciones_val.csv" \
    --predicciones-paced "${pred_paced}" \
    --salida "${corrida}/predicciones_cascada_val.csv" \
    --matriz "${corrida}/matriz_cascada_val.csv" \
    --gate "${corrida}/gate_f22.json"
}

evaluar_semilla 14
if [[ "$("${python_bin}" -c 'import json,sys; print(json.load(open(sys.argv[1]))["estado"])' "${salida_raiz}/seed_14/gate_f22.json")" != VERDE ]]; then
  echo "F22 detenido: gate semilla 14 ROJO; no se consulta test." >&2
  exit 2
fi

if [[ "${CONFIRMAR:-0}" == 1 ]]; then
  evaluar_semilla 42
  evaluar_semilla 73
fi

echo "F22 terminado. Descargar antes de destruir: ${salida_raiz}"
