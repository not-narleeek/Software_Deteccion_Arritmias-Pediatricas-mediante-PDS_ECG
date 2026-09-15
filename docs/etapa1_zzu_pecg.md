# Etapa I (PPS) — Ampliación al corpus ZZU pECG

**Entregable E1-bis · Rama `busqueda-datos` · 2026-09-13 (AP-13).**
Análogo del entregable E1 del acta (§7.3: "exploración del dataset, revisión
bibliográfica y diseño del pipeline DSP") aplicado al dataset de ampliación
ZZU pECG, habilitado por R3/S6/RS6 del acta (ampliación restringida a
fuentes públicas con formato WFDB y anotaciones expertas — ZZU: Figshare,
CC BY 4.0, etiquetas ECG por consenso de dos médicos).

El PPS original (docs/PPS.md, F5, v0.1 sobre Leipzig) permanece vigente;
este documento lo extiende al corpus combinado. Trazabilidad completa:
ingesta y verificación en `docs/metodologia_zzu_pecg.md`, análisis
exploratorio en `docs/analisis_zzu_pecg.md`, evidencia en `results/`.

## 1. Exploración del dataset (resumen ejecutivo)

Fuente: ZZU pECG v1 [tan2025zzupecg] — 14.190 ECG (500 Hz, WFDB, 24 bit,
MedEx MECG-300) de 11.643 niños 0–14 años hospitalizados (Zhengzhou,
2018–2024). Verificación de ingesta (2026-09-13): 6/6 MD5 contra la API de
Figshare, 14.190/14.190 registros con diccionario ≡ cabecera WFDB (fs,
n_sig, sig_len), 0 inconsistencias; señal en mV con rango fisiológico.

| Clase (mapeo AHA→AP-1, §4.4) | Registros | Pacientes | Minutos |
|---|---|---|---|
| Sinusal (A1/A2/C21/C22/C23/C25/C26) | 7.708 | 6.742 | 3.465 |
| Otro (sin enunciado de ritmo de los grupos previos) | 6.008 | 5.402 | 2.693 |
| SVT (E50/E51/E52/E54/E55) | 348 | 222 | 168 |
| VT (G70/G72/G74) | 103 | 53 | 49 |
| Paced ('Pacing rhythm' N(180+181)) | 23 | 11 | 10 |

Hallazgos del análisis exploratorio (detalle en `docs/analisis_zzu_pecg.md`):
- **Etiquetas fisiológicamente válidas**: FC mediana VT 156 / SVT 151 /
  Sinusal 95 lpm; dentro de Sinusal, C21 133 vs C22 57 lpm sin solapamiento
  de cuartiles; SVT neonatal real hasta 273 lpm.
- Epidemiología coherente (SVT concentra lactantes: mediana 5,3 años).
- Señal limpia: 50 Hz ausente (equipo filtra en origen), sin flatline, sin
  saturación — contraste con Leipzig (AP-8).
- Estructura: 49,8 % multi-enunciado (coincide con el paper), 0,6 % con
  enunciados de >1 grupo de clase, contradicciones A1+anormal 0,2 %.

## 2. Control de calidad — exámenes con defectos de adquisición

Protocolo completo (acta §7.2 Etapa I: "identificación temprana de
exámenes con defectos de adquisición"): `scripts/qc_zzu.py` evalúa el
**100 % del corpus** (no muestra) — resultados en `results/qc_zzu/`
(qc_registros.csv 14.190 filas; excluidos.csv 754 con causa).

**Regla por tiers** (derivaciones críticas del pipeline: II para
detector/features; V2 — o V1 en 9-deriv — para la fusión):

| Criterio | Umbral | Acción | Registros |
|---|---|---|---|
| Duración < 10 s | — | excluir (sin ventana) | 7 |
| Artefacto en II (rango p1–p99) | > 5 mV | excluir | ~450 |
| Electrodo suelto en deriv. de fusión (V2/V1) | > 10 mV | excluir | ~50 |
| Canal muerto (ventanas 1 s std==0 en II) | > 20 % | excluir | ~0 |
| Interferencia de red (pico 49–51 Hz / piso 20–40 Hz) | > 20× | excluir | ~80 |
| Artefacto solo en OTRAS derivaciones | > 10 mV | **marcar** | 1.823 |
| bSQI mínimo < 0,95 | — | **marcar** calidad_dudosa | 537 |

(los conteos por criterio se solapan; total excluidos **754 = 5,3 %**)

Fundamento de los umbrales: análisis de muestra (§2.C/§3.1 de
analisis_zzu_pecg.md) — amplitudes >5 mV en II son infisiológicas y rompen
la detección; bSQI bajo NO se usa como exclusión porque se confunde con
arritmia (excluiría 30 % de Paced); el tier "otras derivaciones" no excluye
porque el pipeline no depende de ellas (decisión revisable si RF7
multi-canal se activa).

**Supervivientes (13.436 registros, 94,7 %):**

| Clase | Registros | Pacientes | Minutos | Ventanas est. (10 s/hop 5 s) |
|---|---|---|---|---|
| Sinusal | 7.238 | 6.385 | 3.248 | 31.285 |
| Otro | 5.767 | 5.203 | 2.582 | 24.853 |
| SVT | 317 | 212 | 153 | 1.501 |
| VT | 92 | 51 | 44 | 435 |
| Paced | 22 | 10 | 11 | 104 |

1.641 supervivientes son de 9 derivaciones (menores de 7 años, sin V2).

Meta cuantitativa del experto cumplida: **>>5.000 estudios limpios y
clasificados** (13.436).

## 3. Revisión bibliográfica (addendum F3-B)

Seis entradas nuevas verificadas en `docs/literatura/referencias.bib`
(detalle anotado en `revision_bibliografica.md` §F3-B): dataset ZZU
[tan2025zzupecg]; estándar de terminología que define las etiquetas
[kligfield2007aha]; precedente metodológico de estandarización
[liu2022sph]; datasets pediátricos previos [saarel2018phn]; DL pediátrico
con conceptos clínicos [chen2024chd]; bandas etarias con Z-scores
[bratincsak2020z]. Vacío F3-2 (corpus pediátrico a escala) resuelto, con
limitaciones declaradas (§5).

## 4. Diseño formal del pipeline DSP — deltas sobre diseno_pipeline.md

El diseño F4 (docs/diseno_pipeline.md) se mantiene; estos son los cambios
que el corpus ZZU introduce, sección por sección:

**4.1 Corpus y estratificación (§5 F4 → §5-bis).** Corpus combinado:
ZZU (entrenamiento/validación principal, 13.436 registros) + Leipzig
(desarrollo del método F6–F8 ya verificado; enriquecimiento de Paced —117
min vs 11 en ZZU— y validación externa por población). Validación LORO
**por paciente** dentro de ZZU y **por fuente** (ZZU vs Leipzig): nunca
entrenar en una población y reportar KPI en otra sin declararlo. Estrato
adicional por banda etaria (SVT concentra lactantes —
[bratincsak2020z]). Justificación formal de la limitación de población:
FPS (docs/busqueda_datos.md §0).

**4.2 Preprocesamiento (§3 F4, sin cambios de diseño).** Misma cadena
HP 0,5 Hz → notch 50 Hz Q=35 → LP 40 Hz (SOS, fase cero), ahora
parametrizada `FilterSpec(fs=500)` para ZZU (Leipzig 977 Hz). El notch es
salvaguarda en ZZU (50 Hz ausente, verificado) y necesario en Leipzig.

**4.3 Detector R (§4 F4).** Fusión II+V2 en 12-deriv; **II+V1 en
9-deriv** (menores de 7 años, sin V2); II-only validado como fallback
(98,6 % det_ok en muestra ZZU). Cota de plausibilidad de FC extendida a
300 lpm para <1 año (SVT neonatal medida hasta 273 lpm). Re-validación
F7 sobre ZZU pendiente (sin `.atr` de referencia: validar por estabilidad
de RR y consistencia de FC por etiqueta, como en el análisis).

**4.4 Ventanas y etiquetas (§5.1 F4).** Ventanas de 10 s / hop 5 s. En
Leipzig la clase viene de la segmentación por ritmo (`.atr`); en ZZU **la
ventana hereda la clase del registro** (etiqueta por registro completo,
sin anotación temporal — limitación declarada; solo 0,6 % de registros
tiene enunciados de >1 grupo).

**4.5 Clases (§5.3 F4 / AP-1).** Propuesta actualizada: clasificador de
**4 clases primarias (Sinusal / SVT / VT / Paced)** + 'Otro' como clase
reportada (no objetivo). Cambios vs F4: **VT asciende de caso-estudio a
clase** (435 ventanas ZZU vs 0,9 min en Leipzig); AFL permanece
subsumido en SVT (AP-2); Paced se sostiene con el soporte combinado
ZZU+Leipzig. Pendiente de validación escrita del experto junto con
AP-1/2/3 y la decisión sobre 'Otro' (6.008 registros sin enunciado de
ritmo sinusal).

**4.6 Calidad (§5.1 F4).** Reglas de exclusión/marca del §2 (reemplazan
la regla provisional bsqi-only). Índice de ventanas de producción excluye
los 754 y marca 1.823+537 para reporte aparte (doctrina AP-6).

**4.7 KPIs.** Sin cambios (acta §5): distorsión <5 %, Se/+P ≥95 %,
separabilidad ANOVA/Fisher, Se/Sp ≥85 %, F1 ≥0,80 por clase primaria,
Brier <0,2. La enmienda "por clase primaria" (AP-1) sigue pendiente.

## 5. Limitaciones declaradas (a justificar formalmente en el FPS)

1. **Población**: ZZU = niños hospitalizados de Zhengzhou (China); Leipzig
   = EEF pediátricos (Alemania). Ninguna es población chilena ambulatoria
   (advertencia del experto). Mitigación: validación cruzada por población
   + FPS con limitación explícita + fine-tuning si llegan datos chilenos
   (vía Isatec/hospitales, en gestión).
2. **Etiqueta por registro** (no por segmento): contaminación potencial
   intra-registro (0,6 % multi-grupo declarado).
3. **Paced escaso** (104 ventanas ZZU): soporte combinado con Leipzig;
   reportar por separado si el KPI no es alcanzable.
4. **'Otro' masivo** (24.853 ventanas): clase reportada, no objetivo;
   decisión del experto pendiente sobre ritmo sinusal implícito.

## 6. Criterios de aceptación de esta etapa y estado

| Criterio (análogo E1) | Estado |
|---|---|
| Exploración del dataset documentada y verificable | ✓ (metodologia + analisis + results/) |
| Control de calidad con lista explícita de excluidos | ✓ (754 con causa, qc_zzu/excluidos.csv) |
| Revisión bibliográfica ampliada | ✓ (F3-B + referencias.bib) |
| Diseño formal del pipeline actualizado al corpus | ✓ (§4, deltas sobre F4) |
| Validación del experto del mapeo de clases | **pendiente** (AP-1/2/3 + 'Otro' + VT como clase) |

Próximo hito (Etapa II sobre corpus ampliado): integrar ZZU en `io.py`
(lectura, nomenclatura AVR→aVR, índice de ventanas con reglas §2),
re-validar F7 (fusion II+V1 en 9-deriv), re-ejecutar F8 y retomar F9
(pausado en `desarrollo`, WIP 4d52c10).
