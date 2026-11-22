# Auditoría de la clase Paced

Particiones inspeccionadas: train, val.
El conjunto test permanece excluido por defecto.

## Soporte

- train: 86 ventanas, 8 pacientes, 18 registros.
- val: 8 ventanas, 1 pacientes, 2 registros.

## Revisión prioritaria

- P02746 (train): 100% sin espículas; RMS >100 Hz mediano 1.79 µV.
- P04447 (train): 0% sin espículas; RMS >100 Hz mediano 3.84 µV.
- P05649 (val): 100% sin espículas; RMS >100 Hz mediano 1.39 µV.

Estas banderas requieren revisión clínica; no deben usarse para re-etiquetar automáticamente.
