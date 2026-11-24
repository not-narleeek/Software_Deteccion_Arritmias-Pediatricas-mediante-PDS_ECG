# Runbook — F16/F18 Deep Learning en Vast.ai

## Propósito

Ejecutar el baseline ResNet-1D de F16 en una instancia Vast.ai PyTorch usando
los shards DL ya preparados. Este procedimiento no usa Tailscale, Google Colab
ni Google Drive. F18 agrega augmentation online, muestreo moderado de `Paced`
por paciente y tres semillas sin consultar test.

## Requisitos

- Instancia x86_64 con plantilla PyTorch de Vast.ai, GPU CUDA disponible y SSH
  directo.
- Al menos 16 GB de VRAM y 16 GB libres de disco para los 6,6 GB de shards y
  resultados. No cargar el dato crudo ZZU en la misma instancia.
- Clave pública SSH registrada en Vast.ai. No copiar la clave privada ni una
  API key a la instancia.

## Preparar la instancia

```bash
ssh -i ~/.ssh/keys/vast-ai/id_ed25519 -p <PUERTO> root@<IP>
source /venv/main/bin/activate
git clone --branch etapa2-corpus-combinado --single-branch \
  https://codeberg.org/norlek/Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG.git \
  /workspace/ecg
mkdir -p /workspace/ecg/results/dl/shards /workspace/ecg/runs
```

Comprueba CUDA antes de continuar:

```bash
source /venv/main/bin/activate
python -c 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())'
nvidia-smi
df -h /workspace
```

## Transferir datos

Desde el equipo local, copiar solo `results/dl/` al clon remoto:

```bash
rsync -avP -e 'ssh -i ~/.ssh/keys/vast-ai/id_ed25519 -p <PUERTO>' \
  results/dl/ root@<IP>:/workspace/ecg/results/dl/
```

Debe haber siete archivos `shard_*.npy`, más `manifiesto.csv`, `splits.csv`,
`normalizacion.json` y `verificacion_shards.txt`. No copiar `data/zzu_pecg/`.

## Validar y entrenar

Abrir Jupyter de Vast.ai o ejecutar en SSH:

```bash
source /venv/main/bin/activate
cd /workspace/ecg
uv pip install pandas
python scripts/entrenar_baseline_dl.py --humo
python scripts/entrenar_baseline_dl.py \
  --epocas 30 --batch 64 --lr 3e-4 --salida runs/f16_baseline
```

Si hay `CUDA out of memory`, repetir la corrida completa con `--batch 32`.
No ejecutar sobre `test` durante F16; el gate se decide con macro-F1 de `val`.

## Ejecutar F18

No levantar la instancia hasta que el preflight local termine en `OK`:

```bash
uv run python scripts/auditar_paced.py --salida results/dl/auditoria_paced
uv run python ops/checks/preflight_f18.py --dir-shards shards \
  --salida results/dl/preflight_f18_local.json
```

La auditoría excluye test por defecto. Sus banderas no re-etiquetan datos: los
pacientes sin espículas requieren revisión clínica.

Una vez transferidos los shards a `results/dl/shards`, en Vast.ai:

```bash
source /venv/main/bin/activate
cd /workspace/ecg
uv pip install pandas
install -m 755 ops/scripts/supervisor_f18.sh \
  /opt/supervisor-scripts/f18.sh
install -m 644 ops/supervisor/f18.conf \
  /etc/supervisor/conf.d/f18.conf
supervisorctl reread
supervisorctl update
supervisorctl start f18
```

El proceso largo queda administrado por `supervisor`: sobrevive a la desconexión
SSH y se reinicia si termina con error. El lanzador es reanudable: omite el humo
o una semilla si ya existe su archivo de gate. Ejecuta primero un preflight,
luego una época de humo GPU y
finalmente las semillas 14, 42 y 73. La configuración F18 usa:

- augmentation conservadora solo en train;
- fracción esperada `Paced=0,03`, equilibrada entre pacientes;
- pesos de clase con exponente 0,5, menos extremos que F16;
- label smoothing de 0,05 para reducir sobreconfianza;
- derivaciones ausentes en cero después de normalizar;
- scheduler coseno, early stopping con paciencia 8 y LR inicial `1e-4`.

Monitorear sin interrumpir:

```bash
supervisorctl status f18
tail -f /var/log/portal/f18.log
nvidia-smi
```

Cada semilla debe producir `mejor.pt`, `ultimo.pt`, `historial.json`,
`resumen.json`, `predicciones_val.csv`, `matriz_confusion_val.csv` y
`gate_f18.txt`. Si el humo no produce esos artefactos, no iniciar las semillas.
No abrir ni evaluar la partición test.

## Rescatar resultados y apagar

Antes de reciclar o destruir la instancia, descargar los directorios completos
de corrida, no solo los checkpoints:

```bash
scp -i ~/.ssh/keys/vast-ai/id_ed25519 -P <PUERTO> -r \
  root@<IP>:/workspace/ecg/runs/f16_baseline ./resultados_f16

rsync -avP -e 'ssh -i ~/.ssh/keys/vast-ai/id_ed25519 -p <PUERTO>' \
  root@<IP>:/workspace/ecg/runs/f18_augmented/ ./resultados_f18/
```

La instancia actual no monta un volumen persistente: destruirla elimina los
archivos locales. Verifica la descarga antes de destruirla.
