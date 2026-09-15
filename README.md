# Software de Detección de Arritmias Pediátricas mediante Procesamiento Digital de Señales ECG

Software de soporte diagnóstico que, dada una señal ECG de entrada de **12 derivaciones**, aplica un pipeline de procesamiento digital de señales (filtrado digital, extracción de características morfológicas y espectrales, y clasificación supervisada) para clasificar el ritmo cardíaco y reportar un diagnóstico con **porcentaje de certeza**.

Proyecto académico de la asignatura **Proyectos en TICS II** (Facultad de Ingeniería, Universidad Diego Portales) — Segundo Semestre 2026.

| | |
|---|---|
| Código de proyecto | `TICS-II-2026-ECG-PED` |
| Duración | 16 semanas (1 septiembre – 20 diciembre 2026) |
| Experto asesor clínico | Diego Maureira |
| Estado | Etapa I completa sobre corpus ampliado: PPS v0.1 (Leipzig) + E1-bis ZZU pECG ([docs/etapa1_zzu_pecg.md](docs/etapa1_zzu_pecg.md)); Etapa II en curso — F6–F8 verificados en Leipzig, F9 en pausa; pendiente validación del experto (AP-1/2/3) |

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

**Clases objetivo (propuesta, pendiente de validación del experto):** Sinusal, SVT (taquicardia supraventricular), VT (taquicardia ventricular), Paced (ritmo de marcapasos) — VT asciende de caso-estudio a clase primaria con el corpus ampliado; AFL se reporta dentro de SVT. Ver [docs/etapa1_zzu_pecg.md](docs/etapa1_zzu_pecg.md) §4.5.

## Dataset

[ZZU pECG](https://doi.org/10.6084/m9.figshare.27078763) (Scientific Data 12:867, 2025; CC BY 4.0) — **corpus principal desde Etapa I-bis (AP-13)**:

- 14.190 ECG de 12/9 derivaciones (500 Hz, WFDB) de 11.643 niños 0–14 años hospitalizados
- Etiquetas por registro: enunciados ECG AHA/ACC/HRS 2007 + ICD-10 + índices de calidad (pSQI/basSQI/bSQI)
- Tras QC del 100 % del corpus: **13.436 estudios aceptados** (754 excluidos con causa) — Sinusal 7.238 / Otro 5.767 / SVT 317 / VT 92 / Paced 22

[Leipzig Heart Center ECG Database](https://physionet.org/content/leipzig-heart-center-ecg-database-arrhythmias-in-children-and-patients-with-congenital-heart-disease/) (PhysioNet, 2025) — desarrollo del método (F6–F8 verificados sobre ella), anotación de ritmo por segmento (`.atr`), aporte principal de clase Paced y validación externa por población:

- 29 registros pediátricos (`x001`–`x029`, 977 Hz) + 10 adultos (`x100`–`x109`) solo comparativos

> Ningún dataset se encuentra en este repositorio (peso excesivo, excluidos vía `.gitignore` bajo `data/`). Descarga y verificación de ZZU pECG: checksums y URLs en [results/inventario_zzu/fuente.txt](results/inventario_zzu/fuente.txt) y metodología completa en [docs/metodologia_zzu_pecg.md](docs/metodologia_zzu_pecg.md); Leipzig desde PhysioNet.

Scripts del corpus ZZU (rama `busqueda-datos`): `scripts/inventario_zzu.py` (inventario + mapeo AHA→clases), `scripts/analisis_zzu.py` (análisis exploratorio), `scripts/qc_zzu.py` (control de calidad 100 %). Evidencia en `results/inventario_zzu/`, `results/analisis_zzu/`, `results/qc_zzu/`.

## Objetivos y métricas de éxito (KPI)

| Objetivo | KPI |
|---|---|
| Preprocesamiento que limpie la señal sin distorsionar morfologías clínicas (QRS, onda P, espículas de marcapasos) | Distorsión < 5 % en complejos QRS de referencia |
| Características que discriminen ritmos normales de arrítmicos en población pediátrica | Separabilidad inter-clase (ANOVA / índice de Fisher) |
| Clasificador con salida probabilística calibrada | Brier score < 0.2 |
| Validación sobre segmentos no vistos del dataset | Sensibilidad y especificidad ≥ 85 %; F1-score por clase ≥ 0.80 |

## Stack

Software libre exclusivamente (presupuesto $0): **Python 3.11**, `wfdb`, **NumPy**, **SciPy**, **pandas**, **scikit-learn**, **Matplotlib**. El entorno se gestiona con [uv](https://docs.astral.sh/uv/):

```bash
uv sync                      # crea .venv e instala dependencias desde uv.lock
uv run python script.py      # ejecuta cualquier comando dentro del entorno
uv run jupyter lab           # notebooks de exploración
```

Las versiones exactas quedan fijadas en `uv.lock` (comprometido al repo). Para generar un `requirements.txt` si la cátedra lo exige: `uv export --format requirements-txt`.

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
