# Resultados F20 — rama HF y primera simulación GPU

## Implementación

Se recuperó ZZU pECG v1 desde Figshare: seis archivos con MD5 oficial válido,
extracción multipartita correcta y 14.190/14.190 pares WFDB `.hea/.dat`.

F20 conserva la ResNet morfológica LP 40 Hz y agrega opcionalmente un MLP
8→32→32 alimentado por ocho variables HF desde señal cruda. La fusión ocurre
antes de la cabeza de cinco clases. Sin sidecar, el comportamiento y las claves
de checkpoint F16 permanecen iguales.

El sidecar productivo contiene 52.607 ventanas:

| Partición | Ventanas |
| --- | ---: |
| Train | 46.958 |
| Validación | 5.649 |
| Test | **0** |

La cobertura por `window_id`, paciente, registro y partición es exacta. Todas
las variables son finitas/no negativas; `log1p + z-score` se calculó solo con
train. El preflight quedó VERDE.

## Gate CPU previo a GPU

Para comprobar que la rama puede generalizar hacia el único paciente `Paced`
de validación, se entrenó un RF binario únicamente con features HF de train,
sin usar test ni metadatos clínicos.

| Métrica en validación | Resultado |
| --- | ---: |
| F1 Paced | 0,0000 |
| Sensibilidad | 0,0000 |
| Especificidad | 0,9965 |
| AUC ROC | 0,2869 |
| Matriz TN / FP / FN / TP | 5.621 / 20 / 8 / 0 |

La mediana de RMS HF es 0,0319 mV para `Paced` train, 0,00485 mV para el resto
de desarrollo y 0,00388 mV para P05649. `Paced` train tiene mediana de dos
espículas por ventana; P05649 tiene cero. P05649 se comporta como no-Paced en
la representación que sí generalizó de PTB-XL a Leipzig pediátrico.

## Redefinición operativa: pacing activo

El resultado anterior motivó un split derivado sin modificar el histórico ni
test. P05649 quedó como `holdout_uncertain` y P05281, con 10 ventanas
exclusivamente `Paced` y evidencia HF, pasó de train a val. El nuevo sidecar
tiene 46.948 ventanas train y 5.646 val, cero test y normalización recalculada
solo con train.

El screening CPU del split activo quedó VERDE: sensibilidad 0,60,
especificidad 0,9966, AUC 0,9585 y 6/10 ventanas `Paced` detectadas.

## Simulación GPU — semilla 14

Se ejecutó en una RTX 5070 Ti con PyTorch 2.14.1 + CUDA 13.0. El humo GPU
completó una época en 27,4 s. La corrida real detuvo temprano en época 24 y
seleccionó el checkpoint de época 16.

| Métrica de validación | Resultado | Gate |
| --- | ---: | ---: |
| F1 macro | **0,5927** | ≥0,4664 ✅ |
| F1 Paced | **0,6667** | >0 ✅ |
| F1 VT | **0,3797** | ≥0,4115 ❌ |
| F1 Sinusal | 0,7455 | — |
| F1 SVT | 0,4926 | — |
| F1 Otro | 0,6792 | — |

El gate conjunto queda **ROJO exclusivamente por VT**. Por protocolo se
detienen semillas adicionales y test sigue sin consultarse. F20 demuestra que
la rama HF resuelve `Paced` activo, pero el siguiente cambio debe recuperar VT
sin perder esa ganancia; F16 continúa como candidato hasta superar los tres
criterios.

## Validación

- MD5 oficial 6/6 y conteo WFDB 14.190/14.190.
- Regresión F19 bit-exacta en las ocho features tras optimización.
- Preflight base F18 y sidecar F20: VERDE.
- Split activo: P05649 fuera de desarrollo, P05281 en val y test inmutable.
- Screening HF activo: VERDE.
- Compilación Python y sintaxis Bash: correctas.
- Siete shards verificados por SHA-256 entre local y Vast.ai.
- Humo GPU y semilla 14 completados; checkpoint y resultados rescatados con
  SHA-256 coincidente.
