# Reserva — fuentes internacionales de datos ECG

Creado: 2026-09-13. Preserva los hallazgos de la búsqueda inicial.
**Actualizado 2026-09-13 (mismo día): ZZU-pECG REACTIVADO como vía activa**
(decisión del equipo: avanzar con la reserva internacional y justificar
después la limitación — AP-13); las gestiones chilenas siguen en paralelo.

## 1. Cuándo usar cada fuente no-chilena

1. **ZZU-pECG: ingesta activa** (ver docs/busqueda_datos.md §3).
2. Otras (PTB-XL, CPSC, MIMIC-IV-ECG, CinC-2020): comparativas o
   pre-entrenamiento declarado, con evaluación separada en la población de
   interés.
3. Estudios de transferencia (entrenar en X → evaluar en Y): permiten
   cuantificar empíricamente el domain shift advertido por el experto
   ("la taquicardia en Inglaterra no es igual que en Chile").

## 2. ZZU-pECG — datos verificados contra el paper (Sci Data 12:867, 2025)

Pediatric ECG database del First Affiliated Hospital of Zhengzhou University
(China), 2018–2024. DOI paper: 10.1038/s41597-025-05225-z; DOI dataset
(Figshare, v1, 2025-05-27): 10.6084/m9.figshare.27078763; licencia CC BY 4.0.

- **Volumen:** 14.190 registros ECG de 11.643 niños 0–14 años (6.740 M /
  4.903 F), hospitalizados. Único corpus pediátrico abierto de gran escala.
- **Señal:** equipo MedEx MECG-300, 24-bit, mV, 500 Hz, 5–120 s (92,9 %
  entre 20–40 s). 12.334 registros de 12 derivaciones; 1.856 de 9
  derivaciones — niños < 7 años: set V1/V3/V5 en lugar de V2/V4/V6
  (decisión de cardiólogos pediatras del propio dataset).
- **Formato: WFDB** (`.hea`/`.dat`), generado con la librería wfdb de
  Python. Nomenclatura `P######_E##` (paciente + orden de adquisición).
  → NO requiere lector nuevo; `io.py`/wfdb sirven directo.
- **Etiquetas por registro** (AttributesDictionary.csv):
  - Diagnóstico ECG convertidos a estándares **AHA/ACC/HRS 2007** (78
    enunciados primarios + 13 secundarios) y **CHN** (consenso chino 2019,
    complemento población oriental); 2.641 normales / 11.549 anormales;
    49,8 % de los registros tiene >1 enunciado ECG.
  - Diagnóstico de alta hospitalaria en **ICD-10** (19 categorías
    cardiovasculares pediátricas: miocarditis, cardiomiopatías,
    cardiopatía congénita, Kawasaki, etc.). Inconsistencia menor del
    paper: abstract dice 3.516 registros con ECV, Data Records dice 3.716
    (ambos suman 14.190 con su complemento) — el inventario lo dirá.
  - Multi-etiqueta: `;` separa valores múltiples dentro de un campo.
- **Calidad:** pSQI, basSQI, bSQI por registro en el diccionario; el
  dataset ya excluyó registros con desprendimiento de electrodos y el
  equipo adquirente filtra en origen (no requieren filtrado extra según
  los autores).
- **Metadatos:** edad en días (nac. vs fecha de adquisición), sexo, fecha
  de adquisición desensibilizada (offset aleatorio), ID de paciente
  regenerado.
- **Ética:** aprobado por el comité de ética del hospital (2024-KY-0221-003,
  2025-KY-0369-001), consentimiento eximido, datos desensibilizados.
- **Archivos (v1):** `Child_ecg.zip` (1,91 GB) + `Child_ecg.z01` (2,15 GB)
  + `AttributesDictionary.csv` (7,7 MB) + `ECGCode.csv` (3,6 KB) +
  `DiseaseCode.csv` (3 KB) + `ExampleReadingCode.ipynb` (159 KB).
  Total 4,06 GB. MD5 oficiales en la API de Figshare (registrados en
  `data/zzu_pecg/downloads/lista.txt`).

Advertencias para la ingesta:
- Mapeo de ritmos debe usar los **códigos AHA/CHN** (diagnóstico ECG por
  registro), no el ICD-10 de alta (nivel enfermedad). Verificar qué
  enunciados AHA existen (¿SVT? ¿marcapasos?) en `ECGCode.csv` y con qué
  frecuencias antes de fijar el mapeo a la taxonomía AP-1.
- 1.856 registros < 7 años sin V2: el detector F7 fusiona II+V2 → fallback
  II+V1 o II-only; medir degradación con `validar_detector_r.py`.
- Registros < 10 s no generan ventana de 10 s; contabilizar.
- Población oriental hospitalizada ≠ población chilena ambulatoria: la
  limitación se declara y justifica formalmente después (informe).

## 3. Otras fuentes internacionales (rol comparativo, EX3)

| Fuente | Registros | Edad | Señal | Etiquetas | Licencia |
|---|---|---|---|---|---|
| Leipzig Heart Center (PhysioNet) — **en uso en `data/`** | 39 (29 pediátricos) | ped + adultos | 12 deriv + IEGM, WFDB | ritmo por segmento (`.atr` experto) | abierta |
| PTB-XL (PhysioNet) | 21.837 (18.885 pacientes) | predominantemente adulto | 12 deriv, 10 s | diagnóstico SNOMED | CC BY 4.0 |
| CPSC 2018 (ICBEB) | 6.877 (11 hospitales, China) | adulto | 12 deriv, 6–60 s, 500 Hz | 9 clases (Normal, AF, I-AVB, LBBB, RBBB, PAC, PVC, STD, STE) | abierta |
| MIMIC-IV-ECG (PhysioNet) | ~800.000 (~160.000 pacientes, EE.UU.) | **18+** (5 casos 0–14 según el paper de ZZU) | 12 deriv, 10 s, 500 Hz | diagnóstico | credencial DUA |
| CinC Challenge 2020 (PhysioNet) | agregado multi-fuente (incluye CPSC/PTB-XL) | predominantemente adulto | 12 deriv | multi-etiqueta SNOMED | abierta |

Nota: Leipzig (Alemania) queda como insumo de **desarrollo del método**
(protocolo F1–F8, scripts de verificación) y comparación.

## 4. Referencias

- Paper ZZU-pECG: https://doi.org/10.1038/s41597-025-05225-z
- Dataset ZZU-pECG: https://doi.org/10.6084/m9.figshare.27078763
- Leipzig: https://physionet.org/content/leipzig-heart-center-ecg/
- PTB-XL: https://physionet.org/content/ptb-xl/
- CPSC 2018: http://2018.icbeb.org/Challenge.html
- MIMIC-IV-ECG: https://physionet.org/content/mimic-iv-ecg/
