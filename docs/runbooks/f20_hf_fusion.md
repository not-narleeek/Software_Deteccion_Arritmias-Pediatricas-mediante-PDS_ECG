# Runbook F20 — fusión morfología + alta frecuencia

## Preparación local

Recuperar ZZU crudo y verificar sus seis MD5 oficiales:

```bash
ops/scripts/descargar_zzu.sh
```

Generar únicamente desarrollo train/val:

```bash
uv run python scripts/generar_sidecar_hf_zzu.py --workers 8
uv run python scripts/crear_split_f20_activo.py
uv run python ops/checks/preflight_f20.py \
  --splits results/dl/splits_f20_active.csv \
  --sidecar results/dl/sidecar_hf_f20_active.csv \
  --normalizacion results/dl/sidecar_hf_f20_active_normalizacion.json
uv run python scripts/evaluar_sidecar_f20.py \
  --splits results/dl/splits_f20_active.csv \
  --sidecar results/dl/sidecar_hf_f20_active.csv
```

El sidecar productivo debe informar `incluye_test=false`. No ejecutar
`--incluir-test` durante selección de modelo.

## Archivos para Vast.ai

Además del repositorio y los siete shards F15, transferir:

- `results/dl/splits_f20_active.csv`
- `results/dl/sidecar_hf_f20_active.csv`
- `results/dl/sidecar_hf_f20_active_normalizacion.json`
- `results/dl/f20_active_split.json`

El crudo ZZU no se copia a la GPU. Verificar en remoto:

```bash
python ops/checks/preflight_f18.py --dir-shards results/dl/shards
python ops/checks/preflight_f20.py
```

## Screening

F20 conserva la configuración de F16 para que el cambio principal sea la rama
HF. El lanzador exige primero que el screening HF detecte al menos una ventana
`Paced` en la validación fija; si queda VERDE, ejecuta un humo GPU y la semilla
14:

```bash
ops/scripts/ejecutar_f20.sh
```

En Vast.ai, para que una caída de SSH no interrumpa la corrida, instalar el job
de `supervisor` incluido en el repositorio:

```bash
chmod +x ops/supervisor/f20-train.sh
cp ops/supervisor/f20-train.conf /etc/supervisor/conf.d/
supervisorctl reread
supervisorctl update
supervisorctl status f20_train
```

El log queda en `runs/f20_hf_fusion/supervisor.log`.

Si `seed_14/gate_f20.json` queda VERDE, confirmar dos semillas adicionales:

```bash
CONFIRMAR=1 ops/scripts/ejecutar_f20.sh
```

Un gate ROJO termina con código distinto de cero y no autoriza más GPU ni test.
`FORZAR_GPU=1` existe únicamente como override explícito y debe justificarse en
el informe del experimento.

## Rescate

Descargar antes de detener/destruir la instancia:

- `preflight_base.json`, `preflight_f20.json`;
- `smoke_gpu/`;
- `seed_14/` y, si aplica, `seed_42/`, `seed_73/`;
- checkpoints, historiales, predicciones y matrices completos.

Verificar SHA-256 local/remoto antes de borrar la instancia. El procedimiento
SSH y de respaldo general permanece en `docs/runbooks/vastai_dl.md`.

## Rollback

F16/F18 no se modifican en disco. Para volver al modelo morfológico, ejecutar
el entrenador sin las dos opciones HF. Los checkpoints F20 no son compatibles
con F16 porque contienen `rama_hf` y `cabeza_fusion`; el campo `config` permite
distinguirlos.
