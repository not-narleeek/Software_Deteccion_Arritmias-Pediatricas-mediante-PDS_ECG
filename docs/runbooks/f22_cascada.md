# Runbook F22 — morfología + gate Paced F20

## Entradas

- siete shards F15;
- `results/dl/splits_f20_active.csv`;
- sidecar y normalización HF F20 para validar el split;
- `runs/f20_hf_fusion/seed_14/predicciones_val.csv` como decisión del gate.

F16 antiguo no se reutiliza por fuga de P05281 respecto del split activo.

## Validación local

```bash
python ops/checks/validar_f22_cascada.py
python -m py_compile scripts/evaluar_cascada_f22.py \
  ops/checks/validar_f22_cascada.py
bash -n ops/scripts/ejecutar_f22.sh ops/supervisor/f22-train.sh
```

## Ejecución Vast.ai

```bash
chmod +x ops/scripts/ejecutar_f22.sh ops/supervisor/f22-train.sh
cp ops/supervisor/f22-train.conf /etc/supervisor/conf.d/
supervisorctl reread
supervisorctl update
supervisorctl status f22_train
tail -f runs/f22_cascada/supervisor.log
```

El flujo ejecuta preflights, prueba sintética, humo GPU, morfología semilla 14
y evaluación de cascada. El gate F20 solo se aplica si morfología no predice
VT. Gate: macro ≥0,4664, Paced >0 y VT ≥0,4115. Un ROJO
detiene semillas adicionales y mantiene test sin consultar.

El job de supervisor define `CONFIRMAR=1`, pero el lanzador solo alcanza las
semillas 42/73 si la semilla 14 queda VERDE; con gate ROJO termina antes.

Solo después de VERDE:

```bash
CONFIRMAR=1 ops/scripts/ejecutar_f22.sh
```

## Rescate

Descargar `runs/f22_cascada/`, verificar SHA-256 de checkpoint, resumen, gate y
predicciones de cascada, y detener la instancia. Vast.ai no tiene volumen
persistente en esta máquina.
