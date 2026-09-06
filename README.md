# Software de Detección de Arritmias Pediátricas mediante Procesamiento Digital de Señales ECG

Software de soporte diagnóstico que, dada una señal ECG de entrada de **12 derivaciones**, aplica un pipeline de procesamiento digital de señales (filtrado digital, extracción de características morfológicas y espectrales, y clasificación supervisada) para clasificar el ritmo cardíaco y reportar un diagnóstico con **porcentaje de certeza**.

Proyecto académico de la asignatura **Proyectos en TICS II** (Facultad de Ingeniería, Universidad Diego Portales) — Segundo Semestre 2026.

| | |
|---|---|
| Código de proyecto | `TICS-II-2026-ECG-PED` |
| Duración | 16 semanas (1 septiembre – 20 diciembre 2026) |
| Experto asesor clínico | Diego Maureira |
| Estado | Etapa I — Propuesta (PPS) |

## Motivación

Las arritmias pediátricas (taquicardias supraventriculares, bloqueos de rama, ritmos de marcapasos) presentan patrones electrocardiográficos distintos a los del adulto y están subrepresentadas en bases de datos clínicas. Este sistema se entrena y valida exclusivamente sobre datos de población pediátrica y con cardiopatías congénitas.

## Pipeline

```
ECG 12 derivaciones (WFDB)
        │
        ▼
[1] Preprocesamiento ──── Filtros FIR paso-alto / paso-bajo + IIR notch 50 Hz
        │
        ▼
[2] Detección de picos R ─ Intervalos RR (precisión ≥ 95 %)
        │
        ▼
[3] Extracción de features  Morfológicas (duración QRS, onda P) +
        │                   Espectrales (DCT, energía por bandas)
        ▼
[4] Clasificador ────────── Random Forest / SVM con salida probabilística calibrada
        │
        ▼
Diagnóstico de ritmo + porcentaje de certeza
```

**Clases objetivo:** Sinusal, SVT (taquicardia supraventricular), VT (taquicardia ventricular), AFL (aleteo auricular), Paced (ritmo de marcapasos).

## Dataset

[Leipzig Heart Center ECG Database](https://physionet.org/content/leipzig-heart-center-ecg-database-arrhythmias-in-children-and-patients-with-congenital-heart-disease/) (PhysioNet, 2025):

- 1075 minutos de grabaciones de pacientes pediátricos y con cardiopatías congénitas
- 113.924 latidos anotados por expertos
- 29 registros pediátricos (`x001`–`x029`) para entrenamiento y validación; 10 adultos (`x100`–`x109`) solo para análisis comparativo opcional
- Formato estándar WFDB (`.hea`, `.dat`, `.atr`)

> El dataset **no se encuentra en este repositorio** (peso excesivo). Está excluido vía `.gitignore` bajo `data/`; descargarlo manualmente desde PhysioNet y colocarlo en esa ruta.

## Objetivos y métricas de éxito (KPI)

| Objetivo | KPI |
|---|---|
| Preprocesamiento que limpie la señal sin distorsionar morfologías clínicas (QRS, onda P, espículas de marcapasos) | Distorsión < 5 % en complejos QRS de referencia |
| Características que discriminen ritmos normales de arrítmicos en población pediátrica | Separabilidad inter-clase (ANOVA / índice de Fisher) |
| Clasificador con salida probabilística calibrada | Brier score < 0.2 |
| Validación sobre segmentos no vistos del dataset | Sensibilidad y especificidad ≥ 85 %; F1-score por clase ≥ 0.80 |

## Stack

Software libre exclusivamente (presupuesto $0): **Python 3**, `wfdb`, **NumPy**, **SciPy**, **scikit-learn**, **Matplotlib**. Dependencias fijadas en `requirements.txt` y entorno virtual (`venv`/`conda`) para reproducibilidad.

## Etapas del proyecto

| Etapa | Contenido |
|---|---|
| I — Propuesta (PPS) | Exploración del dataset, revisión de literatura, diseño del pipeline DSP |
| II — Avance + Prototipo (APS) | Preprocesamiento y extracción de características en Python; clasificación preliminar |
| III — Informe Final + Defensa (FPS/DPS) | Sistema completo, métricas de evaluación, casos clínicos y demo funcional |

## Alcance y limitaciones

- Opera solo con las 12 derivaciones ECG superficiales; excluye electrogramas intracardíacos (IEGM).
- Clasifica segmentos de ritmo sostenido, no latido a latido.
- No es un dispositivo médico certificado: uso limitado a investigación, educación y soporte diagnóstico no certificado.
- Diagnóstica ritmos eléctricos, no patologías estructurales del corazón.
- Validación retrospectiva sobre el dataset; sin captura de ECG en pacientes reales.
