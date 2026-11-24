# ADR 0001 — Rama auxiliar de alta frecuencia para Paced

- Estado: aceptada como ablación F20
- Fecha: 2026-11-15

## Contexto

F16, F17 y F18 obtuvieron F1 `Paced=0`. Los shards DL almacenan la señal tras
un paso-bajo de 40 Hz, mientras que las espículas de pacing poseen información
relevante por encima de esa banda. F19 mostró que ocho variables de energía,
pendiente y sincronía HF alcanzan F1 0,976 en PTB-XL y F1 0,793 al transferir
sin ajuste a ventanas pediátricas Leipzig.

Reemplazar el pipeline morfológico por señal ancha alteraría una cadena ya
validada y podría degradar Sinusal, SVT y VT. Mezclar directamente adultos
PTB-XL con el clasificador pediátrico introduciría domain shift.

## Decisión

Mantener la ResNet morfológica sobre los shards LP 40 Hz e incorporar una rama
auxiliar pequeña que consume ocho características calculadas desde el ECG
crudo correspondiente a la misma ventana:

1. contador conservador de espículas;
2. RMS HF mediana y máxima;
3. percentil 99,5 HF mediano y máximo;
4. pendiente 99,9 mediana y máxima;
5. sincronía multiderivación HF.

Las variables reciben `log1p`, z-score con estadísticos exclusivamente train y
recorte a ±8. Un MLP 8→32→32 se concatena con el embedding morfológico antes de
la cabeza de cinco clases. La rama es opcional: sin sidecar, el código y los
checkpoints F16 conservan su estructura anterior.

El sidecar F20 cubre solo train/val durante desarrollo. Test no se genera ni se
consulta hasta una evaluación final expresamente autorizada. Los datasets
externos F19 justifican la representación, pero no se mezclan con el target de
entrenamiento ZZU en esta ablación.

Para la ablación de pacing activo, el split histórico permanece inmutable.
`P05649`, sin evidencia HF de estimulación, se conserva como
`holdout_uncertain`; `P05281` pasa de train a val porque sus 10 ventanas son
exclusivamente `Paced` y sí presentan evidencia HF representativa. El split
derivado `splits_f20_active.csv` nunca modifica test.

## Consecuencias

- Se preserva el camino morfológico y se aísla el cambio experimental.
- La alineación `window_id` pasa a ser un contrato validado por preflight.
- El despliegue necesita el sidecar HF además de shards y normalizaciones.
- `Paced` puede mejorar sin obligar al modelo a descubrir espículas desde LP40.
- La etiqueta de registro y el único paciente Paced de validación continúan
  limitando la fuerza de la conclusión.

## Criterio de aceptación y reversión

Una semilla de screening debe lograr simultáneamente macro-F1 ≥0,4664,
F1 `Paced>0` y F1 VT ≥0,4115. Si falla, F20 se detiene y F16 permanece como
candidato. La reversión operacional consiste en omitir `--sidecar-hf` y
`--normalizacion-hf`; no requiere migrar shards ni checkpoints existentes.
