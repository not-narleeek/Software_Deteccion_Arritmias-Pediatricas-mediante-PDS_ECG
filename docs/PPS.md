# Propuesta de Proyecto (PPS)

## Software de Detección de Arritmias Pediátricas mediante Procesamiento Digital de Señales ECG

| | |
|---|---|
| **Código de proyecto** | TICS-II-2026-ECG-PED |
| **Versión del documento** | 0.1 (borrador para revisión interna) |
| **Fecha** | 6 de septiembre de 2026 |
| **Autores** | Equipo de Proyecto TICS II — Facultad de Ingeniería, UDP |
| **Experto asesor clínico** | Diego Maureira |
| **Clasificación** | Interno / Académico |

**Trazabilidad:** este documento sintetiza los artefactos versionados en el repositorio
(`results/inventario/`, `notebooks/01–04`, `docs/literatura/`, `docs/diseno_pipeline.md`,
`docs/anotaciones_pendientes.txt`). Todo número citado es reproducible desde esos insumos.

---

## 1. Resumen ejecutivo

Se propone construir un software de soporte diagnóstico que clasifique el ritmo cardíaco de
señales ECG pediátricas de 12 derivaciones mediante procesamiento digital de señales
(filtrado, detección de picos R, extracción de características morfológicas y espectrales)
y un clasificador supervisado con salida probabilística calibrada. La Etapa I completó la
exploración exhaustiva del dataset Leipzig Heart Center (PhysioNet), la revisión
bibliográfica y el diseño formal del pipeline. **Hallazgo central:** la distribución real
del dataset no soporta el KPI del acta "F1 ≥ 0.80 por clase" con las 5 clases definidas
(VT pediátrico: 0.9 min; AFL: 0.6 min en 29 registros). Se propone un clasificador
primario de **3 clases** (Sinusal/SVT/Paced) — con 2.477 ventanas de entrenamiento — y
VT/AFL tratados como **estudios de caso**, decisión pendiente de validación del experto
asesor. Con esa salvedad, todos los insumos de la propuesta están completos y el pipeline
está especificado para su implementación en la Etapa II.

## 2. Introducción y contexto

Las arritmias pediátricas (taquicardias supraventriculares, bloqueos de rama, ritmos de
marcapasos) presentan patrones electrocardiográficos distintos de los del adulto y están
subrepresentadas en las bases de datos clínicas, dominadas por patología adulta. El
proyecto se ejecuta entre el 1 de septiembre y el 20 de diciembre de 2026 (16 semanas,
presupuesto $0, software libre exclusivamente), con validación clínica de criterios a
cargo de D. Maureira. El presente documento constituye el entregable E1 del acta:
exploración del dataset, revisión bibliográfica y diseño del pipeline DSP.

## 3. Exploración del dataset

### 3.1 Verificación e inventario

El dataset Leipzig Heart Center ECG-Database v1.0.0 se descargó completo a `data/`.
Verificación SHA256: **126/126 archivos correctos**. Inventario automatizado
(`scripts/inventario.py` → `results/inventario/*.csv`):

| Métrica | Valor medido | Descripción oficial |
|---|---|---|
| Registros | 39 (29 pediátricos `x001–x0029` + 10 adultos `x100–x109`) | igual |
| Frecuencia de muestreo | 977 Hz (única) | igual |
| Duración total | **1107.0 min** (headers ≡ CSVs oficiales, 1107.1) | 1075.85 min |
| Anotaciones de latido | **115.748** | 113.924 |
| Derivaciones superficiales | 12 en el 100 % de los registros | igual |
| Canales intracardíacos | 7 (excluidos del alcance, EX1) | igual |
| Anotaciones de calidad (`~`) | 228 en 10 registros | — |

Las dos discrepancias con la descripción oficial están documentadas (AP-4/AP-5): el acta
citaba las cifras oficiales; los archivos reales difieren (31.2 min y 1.824 latidos). Se
incluirá nota metodológica en el informe final. La edad de x007 viene corrupta en el CSV
oficial (`.14.3`) y se trata como desconocida (AP-10).

### 3.2 Demografía y diagnóstico de la población

La población pediátrica cubre 5,0–18,1 años (mediana 12,5; n=28 con edad válida — x007
queda fuera por AP-10), lo que obliga a tratar la edad como covariable: los límites
normales pediátricos de RR, QRS y amplitudes son continuos en edad y sexo (Rijnbeek
2001). Los adultos corresponden íntegramente a tetralogía de Fallot (postoperatorio,
alto riesgo de VT). Figuras: `01_edad_por_grupo.png`, `01_duracion_por_registro.png`,
`01_diagnosticos_ped.png`.

### 3.3 Distribución de clases y segmentos (hallazgo AP-1)

Minutos por clase objetivo sobre los 29 registros pediátricos:

| Clase | Minutos | Registros | Ventanas 30 s (hop 15 s) |
|---|---|---|---|
| Sinusal | 617.5 | 29 | 1.971 |
| SVT | 132.0 | 28 | 320 |
| Paced | 117.2 | 23 | 186 |
| VT | **0.9** | 5 | **0** (mediana de episodio: 2.1 s) |
| AFL | **0.6** | 1 | 1 |

El desbalance estructural de VT/AFL en pediatría es insalvable por sobremuestreo: la VT
sustantiva vive en los 10 adultos (34.3 min, 10 segmentos ≥ 30 s). La ECDF de duración de
segmentos (`02_ecdf_segmentos.png`) fundamentó el umbral de ventana: 30 s retiene el
84 % del tiempo con 291 segmentos. Varios registros mezclan ritmos → la validación debe
ser por registro (leave-one-record-out). Figuras: `02_minutos_por_clase_ped.png`,
`02_heatmap_registro_clase.png`.

### 3.4 Calidad de señal

Muestreo determinista (3 ventanas de 10 s por registro, 12 derivaciones, métricas en
`results/inventario/calidad_senal.csv`):

- **Interferencia de red:** pico a 50 Hz en 3 de 4 registros representativos; en x001
  sobresale ~6 órdenes de magnitud sobre el piso espectral; x100 está limpio
  (`03_psd_representativos.png`). El notch del acta queda justificado, con contaminación
  heterogénea entre registros.
- **Contenido espectral:** la energía útil se concentra < 40 Hz.
- Deriva basal, ruido de alta frecuencia y saturación (`flat_frac`) tabulados por
  registro (`03_heatmap_calidad.png`); las anotaciones `~` se contrastan contra estas
  métricas (AP-6).
- La banda de registro fue 0.05–100 Hz sin filtrado posterior (página oficial): todo el
  preprocesamiento es responsabilidad del pipeline.

### 3.5 Muestras por clase

Segmentos representativos por clase con frecuencia verificada contra las anotaciones
(`04_muestra_*.png`): Sinusal x001 94.5 bpm; SVT (AVRT) x0011 219.6 bpm, complejo
estrecho sin P visibles; Paced `(/A` x009 219.6 bpm (sobremarcha auricular en EEF) con
espículas previas a cada QRS; VT x002 122.9 bpm monomórfica no sostenida (15.6 s); AFL
x006 ~300 bpm auricular con conducción ~2:1 y diente de sierra inferior.

## 4. Revisión bibliográfica

17 referencias verificadas contra fuente primaria (`docs/literatura/referencias.bib`);
revisión anotada completa en `docs/literatura/revision_bibliografica.md`. Ejes y aportes:

1. **ECG pediátrico normal:** Davignon 1979 (clásico) y Rijnbeek 2001 (límites continuos
   por edad/sexo, digital) → la edad es covariable del clasificador; el QRS pediátrico es
   más corto y de mayor contenido en altas frecuencias → banda de detección desplazada.
2. **Detección de picos R:** Pan-Tompkins 1985 como referencia; **Kathirvel 2011 es el
   detector usado por los anotadores del propio dataset** → candidata base del pipeline.
3. **Preprocesamiento:** deriva 0.05–0.6 Hz; notch fijo con Q moderado vs adaptativo
   (riesgo de "ringing" sobre QRS); obligación de medir la distorsión introducida.
4. **Clasificación con pocos datos:** modelos clásicos sobre características diseñadas
   (SVM/RF); **CV anidado** para evitar el sesgo de selección (Cawley & Talbot 2010);
   calibración Platt/isónica con evaluación Brier (Niculescu-Mizil & Caruana 2005);
   SMOTE con cautela (ventanas correlacionadas por registro).
5. **Vacío identificado:** la DCT exigida por RF4 carece de soporte bibliográfico sólido
   en ECG → el diseño incluye cláusula justificar-o-sustituir por wavelet.
6. Antecedente directo del mismo grupo Leipzig: análisis IA de iECG pediátrico
   (Teich 2023).

## 5. Diseño del pipeline DSP

Especificación completa y justificada en `docs/diseno_pipeline.md`; esqueleto de código
con contratos tipados en `src/ecg_pipeline/`. Resumen:

| Bloque | Decisión |
|---|---|
| Filtrado | HP 0.5 Hz + notch 50 Hz (Q=35) + LP 40 Hz, Butterworth SOS con `sosfiltfilt` (fase cero) |
| Espículas (RS1) | Detección sobre copia sin filtrar (80–250 Hz) y marcado como eventos especiales |
| Distorsión (KPI 1) | D = 100·‖y−x‖₂/‖x‖₂ en R±60 ms; aceptación mediana < 5 %, p90 < 10 % |
| Detector R (RF3) | Kathirvel 2011 (base) / Pan-Tompkins adaptado (comparador); Se/+P ≥ 95 % vs `.atr` (±100 ms) |
| Ventaneo | 30 s, hop 15 s, segmentos ≥ 30 s, margen 1 s en transiciones |
| Características | 46: RR(10) + QRS(9) + P(3) + espículas(2) + espectrales(10) + DCT(8, cláusula) + calidad(2) + edad/sexo(2); reducción por ANOVA/Fisher (KPI 2) |
| Clasificador (RF5) | SVM-RBF primario, RF comparador, `class_weight` balanceado |
| Validación | LORO anidado (29 folds) con GroupKFold interior; Se/Sp ≥ 85 %, F1 ≥ 0.80 (clases primarias), Brier < 0.2 (KPI 3) |
| Reporte (RF6) | Clase + probabilidad calibrada por clase (Platt) + advertencias |

**VT y AFL (estudios de caso):** ventanas de 10 s sobre segmentos ≥ 10 s; detector
binario de VT entrenado solo con adultos (permitido por EX3 como análisis comparativo);
AFL con análisis morfológico descriptivo. Sin mezcla con el conjunto pediátrico primario.

## 6. Desviaciones respecto al acta y decisiones pendientes

| Ítem | Desviación/decisión | Estado |
|---|---|---|
| AP-1 | KPI "F1 ≥ 0.80 por clase" no soportado por datos para VT/AFL → 3 clases primarias + estudios de caso | **Pendiente validación de D. Maureira** |
| AP-2 | AFIB agrupada bajo SVT | Pendiente validación |
| AP-3 | `(B` (bigeminismo) excluido | Pendiente validación |
| AP-4/5 | Cifras oficiales del dataset ≠ archivos (113.924 vs 115.748 latidos; 1075.85 vs 1107.0 min) | Nota metodológica en informe final |
| AP-6 | Ventanas con `~` se marcan, no se excluyen | Propuesta |
| AP-7 | Ventaneo 30 s / hop 15 s | Propuesto con evidencia |
| AP-10 | Edad x007 corrupta → desconocida | Pendiente errata PhysioNet |

Si el experto valida la propuesta de 3 clases, el acta requiere una enmienda menor al KPI
de F1 ("por clase" → "por clase primaria"); las alternativas (5 clases con adultos para
VT; fusión VT+IVR) están documentadas con sus costos en `docs/diseno_pipeline.md` §1.

## 7. Cronograma Etapa II (APS)

| Semanas | Trabajo | Verificación |
|---|---|---|
| 1–2 | Implementar `preprocess.py` + `io.py`; respuestas en frecuencia | `validar_filtros.py`: distorsión < 5 % |
| 2–3 | Detector R + validación contra `.atr` | `validar_detector_r.py`: Se/+P ≥ 95 % |
| 3–5 | Features + separabilidad + experimento DCT-vs-wavelet | Tabla ANOVA/Fisher (KPI 2) |
| 5–7 | SVM/RF + calibración + LORO anidado | Métricas §8.2 + Brier < 0.2 (KPI 3/4) |
| 7–8 | Reporte de diagnóstico + estudio de caso VT (adultos) | Demo funcional (E5) |

Riesgos activos: RS1 (calidad → mitigado con features de calidad y notch cuantificado),
RS2 (sobreajuste → LORO anidado y modelo de margen), RS4 (disponibilidad del experto →
las validaciones AP-1/2/3 se solicitarán por escrito esta semana).

## 8. Conclusiones

La exploración confirmó la viabilidad del proyecto con una corrección de alcance
fundamentada en datos: 3 clases primarias con 2.477 ventanas etiquetadas, VT/AFL como
estudios de caso. La infraestructura de trabajo está operativa y reproducible (uv +
uv.lock, dataset verificado, inventario automatizado, notebooks ejecutados). El diseño
del pipeline está especificado al nivel de contrato de código y cada KPI del acta tiene
un protocolo de medición explícito. Queda pendiente la validación del experto sobre las
decisiones AP-1/2/3 para proceder sin ambigüedad a la implementación.

## Referencias

Davignon et al. 1979, *Pediatric Cardiology* · Rijnbeek et al. 2001, *Eur Heart J* ·
Pan & Tompkins 1985, *IEEE TBME* · Kathirvel et al. 2011, *Cardiovasc Eng Technol* ·
Klehs et al. 2025, *PhysioNet* (dataset) · Goldberger et al. 2000, *Circulation* ·
Pollard et al. 2026, *Nature Health* · Moody & Mark 2001 · Zheng et al. 2020 ·
Wagner et al. 2020 · Teich et al. 2023 · Platt 1999 · Zadrozny & Elkan 2002 ·
Niculescu-Mizil & Caruana 2005 · Brier 1950 · Chawla et al. 2002 · Cawley & Talbot 2010.

Citaciones completas en `docs/literatura/referencias.bib`.
