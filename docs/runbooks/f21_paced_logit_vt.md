# Runbook F21 — residual Paced y regularización VT

## Objetivo y entradas

F21 reutiliza sin modificar:

- `shards/` o `results/dl/shards/`;
- `results/dl/splits_f20_active.csv`;
- `results/dl/sidecar_hf_f20_active.csv`;
- `results/dl/sidecar_hf_f20_active_normalizacion.json`.

Test no se consulta durante selección de modelo.

## Validación previa

```bash
python -m py_compile scripts/entrenar_baseline_dl.py \
  ops/checks/validar_f21_modelo.py
bash -n ops/scripts/ejecutar_f21.sh ops/supervisor/f21-train.sh
python ops/checks/validar_f21_modelo.py \
  --checkpoint-f20 runs/f20_hf_fusion/seed_14/mejor.pt
```

La última comprobación requiere PyTorch y se ejecuta en Vast.ai si el entorno
local no lo incluye. Debe confirmar que HF no altera ni entrega gradiente a los
cuatro logits no-Paced y que las claves `concat` siguen cargando F20.

## Ejecución robusta en Vast.ai

```bash
chmod +x ops/scripts/ejecutar_f21.sh ops/supervisor/f21-train.sh
cp ops/supervisor/f21-train.conf /etc/supervisor/conf.d/
supervisorctl reread
supervisorctl update
supervisorctl status f21_train
tail -f runs/f21_paced_logit_vt/supervisor.log
```

El flujo ejecuta preflights, screening HF, humo GPU y semilla 14. El gate exige
simultáneamente macro-F1 ≥0,4664, F1 `Paced` >0 y F1 VT ≥0,4115. Si queda ROJO,
termina sin semillas adicionales ni test.

Solo con gate VERDE:

```bash
CONFIRMAR=1 ops/scripts/ejecutar_f21.sh
```

## Rescate y cierre

Descargar `runs/f21_paced_logit_vt/`, comparar SHA-256 del mejor checkpoint,
resumen y gate, y detener la instancia antes de destruirla. El disco de Vast.ai
no es un volumen persistente.
