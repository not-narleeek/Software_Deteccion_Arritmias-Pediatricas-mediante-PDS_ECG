# Reserva — fuentes internacionales de datos ECG

Creado: 2026-09-13. Preserva el hallazgo clave de la búsqueda inicial para
uso posterior. **No es parte de la búsqueda activa**: desde 2026-09-13 el
alcance del proyecto está acotado a Chile (AP-13 — domain shift: un modelo
entrenado en otra población no suele diagnosticar bien en la población
objetivo; "la taquicardia en Inglaterra no es igual que en Chile").

## 1. Cuándo reactivar estas fuentes

1. Si el experto o la cátedra enmiendan el alcance (admisión de datos no
   chilenos para entrenamiento del sistema final).
2. Pre-entrenamiento comparativo documentado (población de origen ≠
   población objetivo), con evaluación separada en datos chilenos.
3. Estudios de transferencia (entrenar en X → evaluar en Chile): permiten
   cuantificar empíricamente el domain shift advertido por el experto, con
   o sin ajuste fino (fine-tuning) sobre datos chilenos.

## 2. Hallazgo clave — ZZU-pECG (candidato primario si el alcance se amplía)

Pediatric ECG database de Zhengzhou University (China). Es el único corpus
pediátrico abierto de gran escala encontrado (búsqueda 2026-09-13).

- **Volumen:** 14.190 registros de 11.643 niños hospitalizados, 0–14 años
  (mediana ~8,6 años; 6.740 M / 4.903 F).
- **Señal:** 12.334 registros de 12 derivaciones + 1.856 de 9 derivaciones
  (carecen de V2/V4/V6); 500 Hz; 5–120 s por registro.
- **Etiquetas:** diagnóstico ICD-10 de alta; 3.716 registros con
  enfermedad cardiovascular en 19 categorías pediátricas (miocarditis,
  cardiomiopatías, cardiopatía congénita, Kawasaki, arritmias, etc.);
  incluye índices de calidad pSQI/basSQI/bSQI por registro.
- **Licencia/acceso:** CC BY 4.0; hosteado en Figshare ("ZZU pECG
  Zhengzhou University Pediatric ECG Database"); paper descriptor: DOI
  10.1038/s41597-025-05225-z (Scientific Data).

Advertencias a verificar en una eventual ingesta (no asumir):
- Etiqueta = diagnóstico de alta, **no** ritmo por segmento (≠ Leipzig) →
  mapear las 19 categorías a la taxonomía AP-1; spot-check de los ~10.474
  registros "sin CVD" antes de asumirlos sinusales.
- 1.856 registros sin V2 → el detector F7 fusiona II+V2; medir degradación
  del fallback II-only con `validar_detector_r.py` antes de incluirlos.
- Registros < 10 s no generan ventana de 10 s; contabilizar.
- Formato Figshare ≠ WFDB → lector propio en `io.py`.

## 3. Otras fuentes internacionales (rol comparativo, EX3)

| Fuente | Registros | Edad | Señal | Etiquetas | Licencia |
|---|---|---|---|---|---|
| Leipzig Heart Center (PhysioNet) — **en uso en `data/`** | 39 (29 pediátricos) | ped + adultos | 12 deriv + IEGM, WFDB | ritmo por segmento (`.atr` experto) | abierta |
| PTB-XL (PhysioNet) | 21.837 (18.885 pacientes) | predominantemente adulto | 12 deriv, 10 s | diagnóstico SNOMED | CC BY 4.0 |
| CPSC 2018 (ICBEB) | 6.877 (11 hospitales, China) | adulto | 12 deriv, 6–60 s, 500 Hz | 9 clases (Normal, AF, I-AVB, LBBB, RBBB, PAC, PVC, STD, STE) | abierta |
| MIMIC-IV-ECG (PhysioNet) | ~800.000 (~160.000 pacientes, EE.UU.) | **18+** | 12 deriv, 10 s, 500 Hz | diagnóstico | credencial DUA |
| CinC Challenge 2020 (PhysioNet) | agregado multi-fuente (incluye CPSC/PTB-XL) | predominantemente adulto | 12 deriv | multi-etiqueta SNOMED | abierta |

Nota de alcance: Leipzig (Alemania) queda, bajo la doctrina Chile-first,
como insumo de **desarrollo del método** (protocolo F1–F8, scripts de
verificación) y comparación — no como población de entrenamiento del
sistema final.

## 4. Referencias

- ZZU-pECG — Scientific Data: https://doi.org/10.1038/s41597-025-05225-z
- Leipzig Heart Center: https://physionet.org/content/leipzig-heart-center-ecg/
- PTB-XL: https://physionet.org/content/ptb-xl/
- CPSC 2018: http://2018.icbeb.org/Challenge.html
- MIMIC-IV-ECG: https://physionet.org/content/mimic-iv-ecg/
