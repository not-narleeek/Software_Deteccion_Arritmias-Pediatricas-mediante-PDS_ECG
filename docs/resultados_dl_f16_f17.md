# Resultados DL: baseline F16 y seguimiento F17

## Alcance y protocolo

Los experimentos usan los siete shards int16 validados (58.178 ventanas de
12 derivaciones y 5.000 muestras), normalización calculada solo en train y el
split por paciente existente. El test permanece sin consultar durante este
ajuste.

## F16 — baseline ResNet-1D ponderado

Ejecución: Vast.ai, GPU NVIDIA RTX PRO 4000 Blackwell, PyTorch 2.14.0+cu130.
Configuración: ResNet-1D, `AdamW`, LR `3e-4`, batch `64`, 30 épocas, pérdida
con pesos inversos a la frecuencia de clase.

| Métrica | Resultado |
| --- | ---: |
| Mejor época | 16 |
| Mejor F1 macro de validación | 0,4764 |
| Gate de referencia RF | 0,5180 |
| Estado | ROJO |
| F1 Sinusal / SVT / VT / Paced / Otro | 0,7307 / 0,5094 / 0,4615 / 0,0000 / 0,6802 |

La pérdida de entrenamiento bajó de 1,1211 (época 1) a 0,2134 (época 30),
mientras la pérdida de validación alcanzó su mínimo alrededor de la época 6 y
subió hasta 0,9272 al final. Esto indica sobreajuste posterior; el checkpoint
usable es `mejor.pt` de la época 16, no el último.

La distribución por ventanas confirma el principal factor de riesgo:

| Partición | Sinusal | SVT | VT | Paced | Otro |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 25.255 | 1.245 | 312 | 86 | 20.060 |
| Validación | 3.013 | 128 | 48 | 8 | 2.452 |
| Test (sin usar) | 3.017 | 128 | 75 | 10 | 2.341 |

## F17 — experimento de balanceo

Hipótesis: los pesos de la pérdida no garantizan suficientes ejemplos `Paced`
por lote. F17 activa muestreo balanceado de train con reemplazo y, para no
aplicar la corrección dos veces, usa entropía cruzada sin pesos. Además aplica
parada temprana por F1 macro de validación. Conserva los shards, normalización,
split y conjunto test de F16.

Configuración prevista: `--muestreo-balanceado --lr 1e-4 --epocas 40
--paciencia 8 --min-delta 0.001 --nombre-gate gate_f17.txt`.

Resultado: terminó por parada temprana en la época 14 (mejor checkpoint:
época 9). No alcanzó el gate.

| Métrica | F16 | F17 |
| --- | ---: | ---: |
| Mejor época | 16 | 9 |
| Mejor F1 macro de validación | 0,4764 | 0,4587 |
| F1 Sinusal | 0,7307 | 0,7390 |
| F1 SVT | 0,5094 | 0,5379 |
| F1 VT | 0,4615 | 0,3448 |
| F1 Paced | 0,0000 | 0,0000 |
| F1 Otro | 0,6802 | 0,6717 |
| Gate 0,518 | ROJO | ROJO |

F17 mejora marginalmente Sinusal y SVT, pero empeora VT y no logra detectar
`Paced`; por ello su F1 macro queda 0,0177 por debajo de F16. La hipótesis de
que bastaba balancear lotes queda descartada para este corpus. No corresponde
evaluar test ni sustituir el mejor checkpoint F16.

## Conclusión y siguiente decisión

El artefacto candidato vigente es F16 `mejor.pt` (época 16, F1 macro 0,4764).
La limitación no es solo la frecuencia por lote: `Paced` tiene únicamente 86
ventanas de train y 8 de validación, por lo que su métrica es inestable y no
respondió al sobre-muestreo. Antes de otro entrenamiento conviene auditar esas
94 ventanas y sus etiquetas/pacientes, y decidir si se consigue más dato o si
se define una tarea sin `Paced` respaldada metodológicamente. El test continúa
sin usar.
