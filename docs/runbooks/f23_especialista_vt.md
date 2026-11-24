# Runbook F23 — especialista binario VT

## Entradas

- shards F15;
- `results/dl/splits_f20_active.csv`;
- predicciones de cascada F22 para seeds 14/42/73.

No se consulta test. El threshold se obtiene únicamente del 20% de pacientes
train reservado para calibración interna.

## Validación local

```bash
python ops/checks/validar_f23_cascada.py
python -m py_compile scripts/entrenar_especialista_vt.py \
  scripts/evaluar_cascada_f23.py scripts/resumir_f23.py
bash -n ops/scripts/ejecutar_f23.sh ops/supervisor/f23-train.sh
```

## Vast.ai

```bash
chmod +x ops/scripts/ejecutar_f23.sh ops/supervisor/f23-train.sh
cp ops/supervisor/f23-train.conf /etc/supervisor/conf.d/
supervisorctl reread
supervisorctl update
supervisorctl status f23_train
tail -f runs/f23_especialista_vt/supervisor.log
```

El job ejecuta preflight, humo, especialista seed 23 y las tres evaluaciones
F23. `resumen_multisemilla.json` queda VERDE solo si las tres combinaciones
superan macro ≥0,4664, Paced >0 y VT ≥0,4115.

## Rescate

Descargar `runs/f23_especialista_vt/`, verificar hashes de checkpoint, resumen
y gates; después detener la instancia. No evaluar test sin autorización nueva.
