# Resultados DL F18 — augmentation y muestreo Paced por paciente

## Protocolo

F18 conservó los shards, normalización y split por paciente de F16/F17. El
conjunto test no se evaluó. El cambio se limitó a train:

- augmentation online (desplazamiento, ganancia, deriva, ruido y dropout de lead);
- fracción esperada `Paced=0,03`, con igual masa por paciente;
- pesos de clase con exponente 0,5 y label smoothing 0,05;
- derivaciones ausentes en cero después de normalizar;
- AdamW, LR inicial `1e-4`, scheduler coseno y paciencia 8;
- tres semillas: 14, 42 y 73.

La ejecución se realizó en Vast.ai sobre una RTX 5070 Ti de 16 GB, PyTorch
2.14.1+cu130. Un humo de una época verificó carga, augmentation, CUDA,
checkpoint y artefactos antes de iniciar las semillas.

## Resultados de validación

| Semilla | Mejor época | F1 macro | Sinusal | SVT | VT | Paced | Otro |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 | 13 | 0,4594 | 0,7057 | 0,5946 | 0,3226 | 0,0000 | 0,6740 |
| 42 | 10 | 0,4496 | 0,7074 | 0,5574 | 0,3235 | 0,0000 | 0,6598 |
| 73 | 7 | **0,4658** | 0,7240 | 0,5432 | 0,3889 | 0,0000 | 0,6727 |
| Media ± DE | — | 0,4583 ± 0,0081 | 0,7124 ± 0,0101 | 0,5651 ± 0,0265 | 0,3450 ± 0,0380 | 0,0000 ± 0,0000 | 0,6688 ± 0,0079 |

El mejor F18 no supera F16 (0,4764) ni el gate RF (0,518). Mejora SVT frente
a F16 (0,5094), pero degrada VT y no detecta `Paced`. En la semilla 14 el
modelo no predijo `Paced` para ninguna ventana; las ocho ventanas reales de
validación se repartieron entre Sinusal (3), SVT (3) y Otro (2).

## Interpretación y decisión

F17 ya había descartado que el balanceo completo resolviera `Paced`; F18
descarta también que baste con variantes sintéticas conservadoras y muestreo
moderado por paciente. El paciente `Paced` de validación, P05649, tiene 100 %
de ventanas sin espículas detectadas, RMS >100 Hz mediano de 1,39 µV y 100 %
de ventanas con calidad dudosa. Esto es compatible con una diferencia de
etiqueta o morfología, no solo con falta de frecuencia en train.

El checkpoint candidato continúa siendo F16 `mejor.pt` (F1 macro 0,4764).
No corresponde evaluar test ni ejecutar más sobremuestreo. El siguiente paso
requiere revisión clínica de P02746/P04447/P05649 y, si se conserva la clase,
recuperar el ECG crudo para incluir una rama o sidecar de alta frecuencia.

## Evidencia

Los artefactos rescatados se encuentran en
`artifacts/vastai_2026-11-13/runs/f18_augmented/`: checkpoints mejor/último,
historias, resúmenes, predicciones y matrices por semilla, auditoría y
preflight. Los SHA-256 de los ocho checkpoints descargados coincidieron con
los archivos remotos antes de detener la instancia.
