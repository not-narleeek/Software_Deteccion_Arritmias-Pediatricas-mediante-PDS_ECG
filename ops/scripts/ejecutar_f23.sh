#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="${PYTHON_BIN:-python}"
salida_raiz="${1:-${repo_dir}/runs/f23_especialista_vt}"
dir_shards="${DIR_SHARDS:-${repo_dir}/results/dl/shards}"
splits="${SPLITS_F23:-${repo_dir}/results/dl/splits_f20_active.csv}"
f22_raiz="${F22_RAIZ:-${repo_dir}/runs/f22_cascada}"

cd "${repo_dir}"
mkdir -p "${salida_raiz}"
for semilla in 14 42 73; do
  pred="${f22_raiz}/seed_${semilla}/predicciones_cascada_val.csv"
  [[ -f "${pred}" ]] || { echo "Falta F22 seed ${semilla}: ${pred}" >&2; exit 2; }
done

"${python_bin}" ops/checks/preflight_f18.py \
  --dir-shards "${dir_shards}" --fraccion-paced 0.03 \
  --salida "${salida_raiz}/preflight_base.json"
"${python_bin}" ops/checks/preflight_f23.py \
  --splits "${splits}" --semilla 23 \
  --salida "${salida_raiz}/preflight_split_vt.json"
"${python_bin}" ops/checks/validar_f23_cascada.py \
  > "${salida_raiz}/validacion_cascada.json"

smoke="${salida_raiz}/smoke_gpu"
if [[ ! -f "${smoke}/resumen.json" ]]; then
  "${python_bin}" scripts/entrenar_especialista_vt.py \
    --humo --epocas 1 --semilla 23 --batch 64 \
    --splits "${splits}" --dir-shards "${dir_shards}" --salida "${smoke}"
fi

especialista="${salida_raiz}/especialista_seed_23"
if [[ ! -f "${especialista}/resumen.json" ]]; then
  "${python_bin}" scripts/entrenar_especialista_vt.py \
    --epocas 30 --semilla 23 --batch 64 --lr 3e-4 \
    --fraccion-vt 0.10 --precision-minima 0.50 --paciencia 8 \
    --splits "${splits}" --dir-shards "${dir_shards}" \
    --salida "${especialista}"
fi

gates=()
for semilla in 14 42 73; do
  corrida="${salida_raiz}/seed_${semilla}"
  "${python_bin}" scripts/evaluar_cascada_f23.py \
    --predicciones-f22 "${f22_raiz}/seed_${semilla}/predicciones_cascada_val.csv" \
    --predicciones-vt "${especialista}/predicciones_val.csv" \
    --salida "${corrida}/predicciones_cascada_val.csv" \
    --matriz "${corrida}/matriz_cascada_val.csv" \
    --gate "${corrida}/gate_f23.json"
  gates+=("${corrida}/gate_f23.json")
done
"${python_bin}" scripts/resumir_f23.py "${gates[@]}" \
  --salida "${salida_raiz}/resumen_multisemilla.json"

echo "F23 terminado. Descargar antes de destruir: ${salida_raiz}"
