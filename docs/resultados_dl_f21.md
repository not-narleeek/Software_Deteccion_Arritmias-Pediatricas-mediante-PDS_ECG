# Resultados F21 — residual Paced y augmentation VT

## Formulación

F21 restringió la rama HF a un residual exclusivo sobre el logit `Paced`. Los
otros cuatro logits dependen solo de morfología. La última capa residual inició
en cero. Se aplicó augmentation solo a VT, LR 2e-4, scheduler coseno, pesos
inversos completos y paciencia 10 sobre el split activo de F20.

La validación dinámica confirmó formas 2×5, neutralidad inicial, gradiente HF
cero hacia logits no-Paced y compatibilidad exacta de claves con F20 `concat`.
Preflights y screening HF quedaron verdes; test no fue consultado.

## Semilla 14

La RTX 5070 Ti ejecutó un humo y 21 épocas reales; la parada temprana seleccionó
la época 11.

| Métrica | F20 | F21 | Gate F21 |
| --- | ---: | ---: | ---: |
| F1 macro | **0,5927** | 0,5881 | ≥0,4664 ✅ |
| F1 Paced | **0,6667** | 0,6364 | >0 ✅ |
| F1 VT | **0,3797** | 0,3462 | ≥0,4115 ❌ |
| F1 SVT | 0,4926 | **0,5811** | — |
| F1 Sinusal | **0,7455** | 0,7290 | — |
| F1 Otro | **0,6792** | 0,6480 | — |

El gate conjunto quedó ROJO exclusivamente por VT. No se ejecutaron semillas
42/73 ni test.

## Diagnóstico

VT aumentó verdaderos positivos de 15 a 18 y redujo confusión VT→SVT de 10 a
1. Sin embargo, los falsos positivos VT subieron de 16 a 38: 20 Sinusal y 18
Otro se predijeron como VT. Por ello el problema de F21 es precisión VT, no
sensibilidad. La combinación augmentation VT + pesos inversos completos
sobrecompensó la clase minoritaria.

La siguiente ablación debe conservar el residual `paced_logit`, pero retirar
augmentation VT y volver a la optimización F20 (LR 3e-4, sin scheduler) para
medir la arquitectura aisladamente. No corresponde ajustar umbrales sobre la
misma validación ni consultar test.

## Evidencia y cierre

Los artefactos están en `runs/f21_paced_logit_vt/`. Los SHA-256 de mejor
checkpoint, resumen y gate coincidieron entre Vast.ai y local. La instancia se
detuvo después del rescate.
