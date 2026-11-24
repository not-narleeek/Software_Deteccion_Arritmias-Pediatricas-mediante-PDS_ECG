# Etapa II sobre corpus combinado — proceso, metodología, resultados y consultas

**Rama `etapa2-corpus-combinado` · 2026-09-13 · Para revisión de D. Maureira y del equipo.**

Documento integral del trabajo realizado desde el feedback del experto
(buscar >5.000 estudios, AP-13) hasta el cierre de la Etapa II sobre el
corpus combinado ZZU pECG + Leipzig. Toda la evidencia es reproducible y
está versionada; los caminos se citan por hito.

## 1. Proceso realizado (cronología)

| # | Acción | Commit / evidencia |
|---|---|---|
| 1 | Feedback D. Maureira: >5.000 estudios, filtrar exámenes mal tomados, domain shift (AP-13) | `docs/busqueda_datos.md` |
| 2 | Decisión de alcance: Chile-only → revisada el mismo día a "reserva internacional activa + Chile en paralelo; limitación se justifica después" | AP-13, `docs/reserva_datos_internacionales.md` |
| 3 | Ingesta ZZU pECG: 4,06 GB, 6/6 MD5, 14.190 registros WFDB verificados (0 inconsistencias) | `results/inventario_zzu/`, `docs/metodologia_zzu_pecg.md` |
| 4 | Análisis exploratorio: etiquetas AHA validadas fisiológicamente (FC por clase/subgrupo) | `results/analisis_zzu/`, `docs/analisis_zzu_pecg.md` |
| 5 | Etapa I-bis (E1 análogo del acta): exploración + QC 100 % (754 excluidos con causa; 13.436 aceptados) + literatura F3-B + diseño actualizado | `docs/etapa1_zzu_pecg.md` |
| 6 | Etapa II: F11 (integración io + índice) → F12 (detector) → F13 (features) → F14 (clasificador, 3 iteraciones autorizadas por el equipo) | commits `03c3be4..d61ddaf` |
| 7 | Este documento + push a `origin/etapa2-corpus-combinado` | — |

Decisiones de alcance tomadas por el equipo (registradas): uso de ZZU pECG
como corpus principal (CC BY 4.0,WFDB, anotación por consenso de dos
médicos — en línea con S6 del acta); validación por paciente y por fuente
(nunca mezclar poblaciones en un fold); cada re-entrenamiento requiere
autorización explícita del equipo (política de cómputo).

## 2. Metodología

### 2.1 Corpus (tras QC del 100 %, regla por tiers sobre derivaciones críticas)

| Clase | Registros ZZU | Ventanas ZZU (10 s / hop 5 s) | Ventanas Leipzig | Total F13 |
|---|---|---|---|---|
| Sinusal | 7.238 | 31.285 | 6.587* | 37.872 |
| SVT | 317 | 1.501 | 1.210* | 2.711 |
| VT | 92 | 435 | 2 | 437 |
| Paced | 22 | 104 | 776 | 880 |
| (Otro) | 5.767 | 24.853 | — | clase reportada, no objetivo |

\* Leipzig a 10 s/hop 5 s/margen 1 s (spec unificado §4.4 de etapa1);
AFL→SVT (AP-2). Excluidos 754 con causa individual (`results/qc_zzu/excluidos.csv`).

### 2.2 Pipeline (F11–F13)
- Lectura ZZU con normalización de derivaciones (AVR→aVR), reorden a 12
  canales, ausentes (9-deriv < 7 años) rellenadas en 0; detector con
  fusión II+V2 o **II+V1** según disponibilidad (`idx_v` parametrizado).
- Misma cadena de filtros (HP 0,5/notch 50/LP 40, fase cero) parametrizada
  a fs=500; banda de espículas clamp a Nyquist (237,5 Hz a 500 Hz).
- Ventanas: ZZU hereda la clase del registro (etiqueta por registro, sin
  `.atr`); Leipzig conserva segmentación por ritmo.
- Features: 66 (56 previas + 10 morfológicas nuevas: polaridad P en II y
  V1, fracción P negativa, relación |P III|/|P II|, duración P, RP, PR,
  R/S y amplitudes en V1 — válidas también con 9 derivaciones).

### 2.3 Validación (F14)
- **A (dentro de ZZU)**: GroupKFold-5 por PACIENTE anidado; selección de
  hiperparámetros solo en folds internos agrupados (Cawley); SVM-RBF
  primario y RF comparador; calibración Platt; **submuestreo de la clase
  mayoritaria a 3× la segunda solo en entrenamiento** (test intacto).
- **B (transferencia)**: entrenar ZZU→evaluar Leipzig pediátrico y el
  reverso (cuantificación del domain shift).
- Métricas §8.2: Se/Sp/F1 por clase, matrices por ventana y por registro
  (voto), Brier multiclase, IC bootstrap.

## 3. Resultados

### 3.1 Verificaciones intermedias (VERDE)
- F11: regresión F6 exacta (2.428 ventanas), ZZU≡QC, índice 66.759.
- F12: det_ok 100 % (13.436/13.436); FC por clase en orden clínico
  (VT 149 / SVT 146 / Sinusal 95 lpm); degradación fusión V1-vs-V2:
  |ΔFC| mediana 0,2 lpm — el subconjunto de 9 derivaciones queda habilitado.
- F13: separabilidad fuerte (fc_norm_media F 5.017; p_rp_ms nueva en 4º
  lugar, Fisher 0,119).

### 3.2 F14 — trayectoria de las 3 iteraciones (F1 macro)

| Iteración | Cambio | SVM | RF |
|---|---|---|---|
| 1 | Base (sin balancear) | 0,354 | 0,403 |
| 2 | + submuestreo 3× en train | 0,412 | 0,506 |
| 3 | + features morfológicas P/RP/PR/V1 | 0,487 | **0,518** |

Mejor modelo (RF, it.3), por clase a nivel ventana: Sinusal F1 0,95 ·
VT 0,43 · SVT 0,35 · Paced 0,34. A nivel registro (voto mayoritario):
Sinusal 94 % · SVT 109/212 · VT 27/51 · Paced 3/10. Brier multiclase
0,037 (**KPI de calibración del acta cumplido con holgura**).

Matriz de confusión dominante: **SVT↔Sinusal** (EAT del grupo SVT vs
sinuso-taquicardia C21 del grupo Sinusal — clínicamente limítrofes a
10 s; 87 SVT→Sinusal y 363 Sinusal→SVT por registro).

### 3.3 Transferencia entre poblaciones (evidencia del domain shift)

| Dirección | F1 macro | Brier |
|---|---|---|
| ZZU → Leipzig | 0,362 | 0,086 |
| Leipzig → ZZU | 0,097 | 0,139 |

El gap es asimétrico y grande: cuantifica la advertencia del experto
("la taquicardia en Inglaterra no es igual que en Chile") y fundamenta
la limitación de población del FPS + la prioridad de datos chilenos.

### 3.4 KPI del acta — estado

| KPI | Meta | Resultado | Estado |
|---|---|---|---|
| 1 Distorsión filtros | < 5 % | 2,59 % (F6) | ✅ |
| 3 Brier | < 0,2 | 0,037 | ✅ |
| Se/Sp global | ≥ 85 % | Se 0,57 / Sp 0,90 (RF) | ⚠️ Se no cumple |
| F1 por clase | ≥ 0,80 | Sinusal 0,95; resto 0,34–0,43 | ❌ requiere enmienda |

## 4. Limitaciones declaradas
1. Población de entrenamiento no-chilena (hospitalizada, Zhengzhou;
   EEF pediátrico, Leipzig) — gap de transferencia medido en §3.3.
2. Etiqueta por registro completo en ZZU (sin segmentación temporal).
3. Paced con 10 pacientes en ZZU (soporte combinado con Leipzig).
4. 'Otro' (24.853 ventanas) excluido del clasificador primario y
   reportado aparte — decisión de diseño pendiente de validación.
5. Ventanas de 10 s: límite físico para discriminar EAT vs
   sinuso-taquicardia sin análisis morfológico fino de P (se exploró con
   las 10 features nuevas; la mejora fue +0,01 F1 macro).

## 5. Consultas para D. Maureira

**Sobre clases y etiquetas (AP-1/2/3 ampliadas):**
1. ¿Valida el mapeo AHA→clases usado? (SVT = E50 AFIB + E51 AFL + E52
   EAT + E54 junctional + E55; VT = G70/G72/G74; Paced = 'Pacing rhythm';
   Sinusal = A1/A2/C21–C26; prioridad Paced>VT>SVT>Sinusal>Otro).
2. Los 6.008 registros ZZU 'Otro' (sin enunciado de ritmo sinusal, p. ej.
   solo "T-wave abnormality"): ¿los trata como Sinusal (ritmo normal
   implícito), como clase aparte, o se excluyen del sistema?
3. ¿EAT (E52, 189 registros) agrupado con SVT o separado? Es la principal
   fuente de confusión con sinuso-taquicardia (C21).
4. ¿Mantiene VT como 4ª clase primaria (435 ventanas) o prefiere
   detector binario "taquicardia ancha" como segundo nivel?

**Sobre el KPI (enmienda propuesta):**
5. ¿Respalda enmendar "F1 ≥ 0,80 por clase" a alguna de: (a) por clase
   primaria a nivel REGISTRO (voto por ventanas), (b) ≥ 0,80 solo
   Sinusal+SVT con VT/Paced como casos de estudio, o (c) reposicionar el
   sistema como soporte de screening (priorizar Se de arritmia con
   reporte de certeza calibrada — Brier 0,037 ya cumple)?
6. Con los datos disponibles, ¿qué Se mínima considera clínicamente
   útil para SVT en un contexto de screening pediátrico?

**Sobre población y alcance:**
7. El gap de transferencia ZZU↔Leipzig (F1 0,10–0,36) confirma su
   advertencia de domain shift: ¿respalda la estrategia "entrenar en
   corpus público + validar/declarar limitación + fine-tuning cuando
   lleguen datos chilenos (Isatec/hospitales)"? ¿Firma una carta de
   apoyo para las gestiones con Isatec y los CEC de Calvo Mackenna /
   Roberto del Río?

**Menores:**
8. Leipzig: registros pediátricos con segmentos de estimulación no
   fisiológica (sobremarcha) siguen etiquetados Paced — ¿correcto?
9. Erratas: edad x007 ('.14.3', AP-10) y cifras del paper ZZU (3.516 vs
   3.716 registros con ECV) — ¿consultamos a las fuentes?

## 6. Dónde está la evidencia

- `results/experimento_corpus/` — métricas F14 completas (svm/rf,
  transferencia, KPI, matrices, confiabilidad).
- `results/corpus/` — índice y features (66.759 / 41.900 ventanas).
- `results/validacion_detector_zzu/`, `results/qc_zzu/`,
  `results/analisis_zzu/`, `results/inventario_zzu/` — cadena completa.
- Scripts reproducibles: `scripts/{validar_corpus,validar_detector_zzu,
  extraer_features_corpus,ejecutar_experimento_corpus}.py` (`uv run`).
