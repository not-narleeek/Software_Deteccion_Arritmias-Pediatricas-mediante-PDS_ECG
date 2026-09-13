# Metodología de procesamiento y comprobación — dataset ZZU pECG

Creado: 2026-09-13 (rama `busqueda-datos`, AP-13). Documenta cómo se
obtuvo, procesó y verificó el dataset ZZU pECG, con las URLs de procedencia
de toda la información utilizada y los comandos para reproducir cada paso.
Resultados citados: `results/inventario_zzu/`.

## 1. Fuentes de información (URLs, acceso 2026-09-13)

**Paper y dataset**
- Paper descriptor (Scientific Data 12:867, 2025):
  https://www.nature.com/articles/s41597-025-05225-z
  (DOI: https://doi.org/10.1038/s41597-025-05225-z) — de aquí salen:
  composición (14.190 registros / 11.643 niños 0–14 a), equipo adquirente
  MedEx MECG-300 (24 bit, 500 Hz), formato WFDB, nomenclatura P######_E##,
  estándares de codificación, ética (aprobación 2024-KY-0221-003 y
  2025-KY-0369-001, consentimiento eximido, datos desensibilizados).
- Dataset (Figshare, v1, 2025-05-27, CC BY 4.0):
  https://doi.org/10.6084/m9.figshare.27078763 — página:
  https://springernature.figshare.com/articles/dataset/A_pediatric_ECG_database_with_disease_diagnosis_covering_11643_children/27078763
- Manifiesto JSON (archivos, tamaños, MD5 oficiales; base de la
  verificación de integridad): https://api.figshare.com/v2/articles/27078763

**Descargas directas utilizadas** (ndownloader, verificación en §3):

| Archivo | URL | MD5 |
|---|---|---|
| ECGCode.csv | https://ndownloader.figshare.com/files/53512538 | 7612c5af0e01e052eb85792c5e362f12 |
| DiseaseCode.csv | https://ndownloader.figshare.com/files/53512544 | 0bff597c23397c0d05a937fe09807ad4 |
| AttributesDictionary.csv | https://ndownloader.figshare.com/files/53580632 | ffbbb7ebd8ad4425b3a859739eb65eb1 |
| ExampleReadingCode.ipynb | https://ndownloader.figshare.com/files/53581268 | 66694258f55ea75bf3454546d486a0e5 |
| Child_ecg.z01 | https://ndownloader.figshare.com/files/53524583 | 4782e8c17b478745853db85210ce46aa |
| Child_ecg.zip | https://ndownloader.figshare.com/files/53523902 | d7bb207d0f559c5f697bd7e442975718 |

**Estándares de las etiquetas** (citados en el paper, no descargados)
- AHA/ACC/HRS 2007 (Kligfield et al., Circulation 115:1306–1324):
  https://doi.org/10.1161/CIRCULATIONAHA.106.180200
- Consenso chino de terminología ECG 2019 (Guo & Wang):
  https://doi.org/10.13308/j.issn.2095-9354.2019.03.002
- ICD-10 versión 2019 (WHO): https://icd.who.int/browse10/2019/en

Otras URLs del trabajo de búsqueda (contexto, no de este dataset):
`docs/busqueda_datos.md` §2 y `docs/reserva_datos_internacionales.md` §4.

## 2. Cadena de procesamiento

1. **Manifiesto**: GET a la API de Figshare (URL arriba) → lista de 6
   archivos con tamaño y MD5 (`supplied_md5` == `computed_md5` en la API).
2. **Descarga**: HTTPS por archivo; reanudable (`curl -L -C -`); después de
   cada archivo se recalcula `md5sum` y se aborta si difiere del manifiesto.
3. **Extracción**: 7-Zip 26.02 sobre el zip multipartito (`Child_ecg.zip` +
   `Child_ecg.z01`) → `data/zzu_pecg/Child_ecg/P##/P######/P######_E##`
   (`.hea` + `.dat`). Conteo de archivos contra el diccionario.
4. **Inventario automatizado** (`scripts/inventario_zzu.py`, ejecutar con
   `uv run python scripts/inventario_zzu.py`):
   - Parseo de `AttributesDictionary.csv`: campos multi-valor separados por
     `;`, valores entre comillas simples; edad `'<N>d'` (días) → años
     (÷365,25); duración = `Sampling_point` / 500.
   - Verificación por registro contra la cabecera WFDB (`wfdb.rdheader`):
     `fs == 500`, `n_sig == Lead`, `sig_len == Sampling_point`.
   - Etiquetas: tokens AHA por registro; código base separando sufijos
     `+ModifierNNN`; multi-etiqueta preservada en `registros.csv`
     (`aha_crudo`).
   - SQI: parseo por derivación de `'Lead':valor` (`Null` = derivación
     ausente en 9-deriv); se reporta el **mínimo** por registro.
   - Mapeo a taxonomía AP-1 con prioridad **Paced > VT > SVT > Sinusal >
     Otro** (un registro con varias etiquetas queda en la clase más
     específica): Paced = 'Pacing rhythm' N(180+181); VT = G70/G72/G74;
     SVT = E50/E51/E52/E54/E55; Sinusal = A1/A2/C21/C22/C23/C25/C26.
     Propuesta del equipo, pendiente de validación del experto (AP-1/2/3).
   - Ventanas estimadas (margen 0, comparable a F2):
     `max(0, floor((dur_s − 10)/5) + 1)` para dur ≥ 10 s.
5. **Salidas** (`results/inventario_zzu/`): `registros.csv` (metadatos +
   clase + SQI mínimos), `aha.csv` (distribución cruda de enunciados),
   `clases.csv` (registros/pacientes/minutos/ventanas por clase),
   `calidad.csv` (SQI por clase), `verificacion.txt` (consistencia
   diccionario↔WFDB), `fuente.txt` (procedencia + checksums).

## 3. Comprobaciones realizadas y resultado (2026-09-13)

| # | Comprobación | Criterio de pase | Resultado |
|---|---|---|---|
| 1 | Integridad de descarga | MD5 de los 6 archivos == manifiesto API | 6/6 OK |
| 2 | Extracción completa | .hea y .dat == 14.190 c/u (== filas del diccionario) | OK |
| 3 | Diccionario ↔ WFDB | fs, n_sig, sig_len por registro | 14.190/14.190, **0 inconsistencias** |
| 4 | Frecuencia de muestreo | fs única 500 Hz | OK |
| 5 | Unidades y rango de señal | mV; rango fisiológico (muestreo por clase: Paced/VT/SVT/Sinusal) | OK (±4 mV) |
| 6 | Cierre de clases | Σ registros por clase == 14.190 | OK (7.708+6.008+348+103+23) |
| 7 | Cruce con el paper | 12-deriv = 12.334; 9-deriv = 1.856; normales (A1+A2) = 2.641; duración 92,9 % en 20–40 s | OK en los cuatro |
| 8 | Registros sin ventana | duración < 10 s | 7 (excluidos del conteo de ventanas, listados) |

Nota (7): el paper es internamente inconsistente en "registros con ECV"
(abstract 3.516 vs Data Records 3.716); una medida laxa por ICD-10
cardiovascular da 3.866 — no se usa como criterio de pase hasta definir el
conjunto exacto de códigos.

## 4. Reproducibilidad

- Re-descarga y verificación: repetir el bucle de §2.2 con la tabla de §1
  (los MD5 de la API son el oráculo; si Figshare publica una v2, el DOI
  resuelve a otra versión — repetir manifiesto antes de descargar).
- Re-procesamiento: `uv run python scripts/inventario_zzu.py` (requiere
  `data/zzu_pecg/` extraído; ~100 s para 14.190 cabeceras).
- Re-verificación de un resultado: `results/inventario_zzu/verificacion.txt`
  se regenera en cada ejecución; comparar contra el versionado en git.
- El dataset NO se versiona (`data/` en .gitignore): la trazabilidad es
  DOI+MD5 (`fuente.txt`) + código del inventario.

## 5. Decisiones y limitaciones registradas (para el integrador de `io.py`)

- Derivaciones en mayúsculas (`AVR`, `AVL`, `AVF`) ≠ Leipzig (`aVR`...):
  normalizar al unificar.
- **Sin anotación temporal** (no hay `.atr`): la clase es del registro
  completo; toda ventana de un registro hereda su clase (limitación frente
  a la segmentación por ritmo de Leipzig).
- 1.856 registros de 9 derivaciones (menores de 7 años) sin V2: el detector
  F7 (fusión II+V2) requiere fallback II+V1 o II-only; medir degradación
  con `validar_detector_r.py` antes de usarlos en entrenamiento.
- 'Otro' (6.008 registros) = sin enunciado de ritmo sinusal ni clase
  superior: pendiente de decisión del experto (ritmo sinusal implícito).
- Calidad (regla provisional, doctrina AP-6): excluir solo duración <10 s;
  **marcar** `calidad_dudosa` si `bsqi_min < 0.95` (537 registros) y
  reportar aparte — excluir por bSQI sesga contra Paced/VT (confound
  calidad↔arritmia; evidencia en `docs/busqueda_datos.md` §3.4). pSQI no
  usable como umbral (mediana 0,33 global).
