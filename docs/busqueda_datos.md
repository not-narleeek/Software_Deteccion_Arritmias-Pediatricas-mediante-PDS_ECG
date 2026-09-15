# Búsqueda de datos — rama `busqueda-datos`

Creado: 2026-09-13, tras reunión con D. Maureira (AP-13).
Última actualización: 2026-09-13 — ingesta ZZU-pECG completa.

## 0. Objetivo y decisiones de alcance

**Meta (feedback D. Maureira):** >5000 estudios pediátricos limpios y bien
clasificados antes de reanudar pre-procesamiento y modelado.

Cadena de decisiones del 2026-09-13 (equipo):
1. Acotar la búsqueda a Chile (domain shift: "la taquicardia en Inglaterra
   no es igual que en Chile").
2. **Revisado horas después: avanzar con la reserva internacional como vía
   activa** — ingesta ZZU-pECG (§3) — y justificar después la limitación de
   usar población no-chilena. Las gestiones chilenas (§4) corren en paralelo
   como vía de población-objetivo a futuro.

Justificación de la limitación (pendiente, se redacta en el informe FPS):
- Declarar explícitamente: ZZU-pECG = niños hospitalizados de Zhengzhou
  (China), 2018–2024, MedEx MECG-300; población ≠ objetivo chileno.
- Mitigación planificada: validación cruzada por población (entrenar ZZU →
  evaluar Leipzig pediátrico y viceversa) para cuantificar el gap de
  transferencia; LORO por institución; a la llegada de datos chilenos,
  fine-tuning/evaluación separada (EX3 análogo).
- El acta/KPI no cambia: el sistema final se declara validado en la
  población de los datos disponibles, con la limitación explicitada.

## 1. Feedback del experto (D. Maureira, sep-2026)

- "Exámenes mal tomados, filtrar" → §3.4 (regla provisional).
- "Buscar más datos" → meta >5000 (cumplida en registros: 14.190; ver §3).
- Contactar a Isatec → §4, prioridad 1 de la vía chilena.
- Domain shift x→y → §0 (limitación a justificar).
- Combinaciones de canales / por canal vs combinar → retomar en F8 (features
  por derivación y combinadas).
- Serie de tiempo → imágenes: resultados similares → opcional, no prioritario.

## 2. Fuentes

**Internacional (activa):** ZZU-pECG — ingesta completa, §3 y
`docs/reserva_datos_internacionales.md` (detalle verificado contra el paper).
Otras internacionales (PTB-XL, CPSC, MIMIC-IV-ECG, CinC-2020): comparativas
bajo EX3, no ingesta.

**Chile (paralela, equipo):**

| Fuente | Qué tiene | Vía | Estado |
|---|---|---|---|
| **Isatec** (Instituto de Salud y Tecnología de Chile Ltda.) | Tele-informes ECG 12 deriv + Holter en decenas de establecimientos; decenas de miles de pacientes/mes; proyecto IA CardIA-ECG (Corfo) | Contacto/convenio | **Prioridad 1 — contactar** |
| Hospitales pediátricos: Luis Calvo Mackenna, Roberto del Río | Ficha electrónica con ECG digital; protocolo formal de registros + CEC (Calvo Mackenna) | Protocolo Unidad de Investigación/CEC | Prioridad 2 |
| Red UC Christus / Hospital Clínico U. de Chile | Registros académicos | CEC + convenio | Prioridad 3 |
| datos.gob.cl / DEIS | SOLO estadísticas agregadas (REM); sin trazos (Ley 19.628) | Pública | Dimensionar oferta, no entrenar |

Verificado 2026-09-13: en Chile NO existe repositorio público de trazos ECG
individuales; la vía es institucional/industrial (convenio + CEC +
anonimización, Ley 19.628).

## 3. Ingesta ZZU-pECG (COMPLETA, 2026-09-13)

Procedencia y checksums: `results/inventario_zzu/fuente.txt` (Figshare
10.6084/m9.figshare.27078763 v1, CC BY 4.0; 6/6 MD5 verificados; extracción
7z → `data/zzu_pecg/Child_ecg/`, 4,3 GB, no versionado).
Metodología completa de procesamiento y comprobación (con URLs de
procedencia): `docs/metodologia_zzu_pecg.md`.

Inventario automatizado: `scripts/inventario_zzu.py` →
`results/inventario_zzu/` (registros.csv, aha.csv, clases.csv, calidad.csv,
verificacion.txt).

### 3.1 Verificación
- 14.190/14.190 registros: diccionario == cabeceras WFDB (fs, n_sig,
  sig_len) — **0 inconsistencias**; fs única 500 Hz.
- Señal en mV (rango fisiológico ±4 mV verificado por muestreo por clase).
- 12.334 de 12 deriv + 1.856 de 9 deriv (menores de 7 años: V1/V3/V5 en
  lugar de V2/V4/V6 → sin V2; el detector F7 fusiona II+V2: fallback
  II+V1 o II-only, medir degradación antes de usar).
- Nomenclatura 'AVR/AVL/AVF' mayúsculas ≠ Leipzig 'aVR/aVL/aVF' →
  normalizar al integrar en `io.py`.
- Duración total 6.387,5 min; mediana 30 s; **7 registros <10 s** (sin
  ventana posible; excluidos del conteo de ventanas).

### 3.2 Clases (mapeo AHA → taxonomía AP-1, propuesta pendiente de experto)

Prioridad Paced > VT > SVT > Sinusal > Otro (registro con varias etiquetas
queda en la más específica; multi-etiqueta preservada en registros.csv):

| Clase | Registros | Pacientes | Minutos | Ventanas est. (margen 0) |
|---|---|---|---|---|
| Sinusal | 7.708 | 6.742 | 3.465 | 33.386 |
| Otro | 6.008 | 5.402 | 2.693 | 25.937 |
| SVT | 348 | 222 | 168 | 1.651 |
| VT | 103 | 53 | 49 | 489 |
| Paced | 23 | 11 | 10 | 107 |

vs Leipzig (Sinusal/SVT/Paced 1.971/320/186 ventanas; VT 0,9 min; AFL
0,6 min): ZZU aporta escala en Sinusal/SVT y hace viable VT pediátrico
(49 min, caso de estudio → clase binaria posible). **Paced sigue escaso
(23 registros, 11 pacientes)** — riesgo documentado; Leipzig aporta la
mayor parte de Paced (117 min). AFL = 43 registros dentro de SVT.

### 3.3 Mapeo aplicado (códigos AHA base)
- Paced: 'Pacing rhythm' N(180+181) · VT: G70 G72 G74 · SVT: E50 E51 E52
  E54 E55 (AFIB/AFL/EAT/juncional/SVT — análogo AP-2) · Sinusal: A1 A2 C21
  C22 C23 C25 C26 · Otro: resto (escapes, bloqueos AV, etc.).
- 'Otro' (6.008) = registros sin enunciado de ritmo sinusal ni clase
  superior (p. ej. solo "T-wave abnormality") — evidencia en aha.csv; el
  experto debería revisar si parte va a Sinusal (ritmo implícito normal).

### 3.4 Calidad ("exámenes mal tomados") — evidencia y regla provisional
- pSQI: mediana global 0,33 — NO usable como umbral (excluiría 99 %).
- basSQI<0,95 excluiría 47 % — demasiado agresivo.
- bSQI<0,95 marca 537 registros (3,8 %) PERO excluye desproporcionadamente
  Paced (7/23) y VT (16/103): bajo bSQI puede ser arritmia, no mala toma
  (confound calidad↔patología).
- **Regla provisional (doctrina AP-6):** excluir solo los 7 registros <10 s
  (estructural) y los rango_mv>5 mV (tomas defectuosas, 0,8 % de la
  muestra — docs/analisis_zzu_pecg.md §2.C/§3.1); MARCAR calidad_dudosa
  bsqi_min<0,95 (537) y reportar aparte, sin excluir del baseline.
- Análisis exploratorio completo (demografía, etiquetas, validación por
  FC, señal): `docs/analisis_zzu_pecg.md`, datos en `results/analisis_zzu/`.

- [x] Manifiesto, descarga, MD5, extracción, verificación WFDB (§3.1).
- [x] Inventario + mapeo AHA (§3.2/§3.3).
- [x] Análisis de calidad + regla provisional (§3.4).
- [x] Etapa I sobre ZZU (E1-bis): exploración + QC 100 % del corpus
      (754 excluidos con causa) + literatura F3-B + diseño actualizado —
      docs/etapa1_zzu_pecg.md (2026-09-13).
- [ ] Validación del mapeo con D. Maureira (junto con AP-1/2/3; incluir
      qué hacer con 'Otro' y Paced escaso).
- [ ] Integrar ZZU en `io.py` (leads mayúsculas, sin `.atr` — etiquetas de
      diccionario por registro completo; ventanas toman la clase del
      registro, no hay segmentación temporal).
- [ ] Medir degradación del detector F7 sin V2 (1.856 registros 9-deriv).
- [ ] Re-ejecutar F6/F7/F8 sobre ZZU + Leipzig; retomar F9.
- [ ] Vía chilena en paralelo (equipo): contactar Isatec; protocolo CEC
      Calvo Mackenna / Roberto del Río; errata x007 (AP-10) a PhysioNet.
- [ ] Redactar justificación de limitación de población (§0) para el FPS.

## 5. Riesgo domain shift (advertencia del experto)

- ZZU-pECG (China, hospitalizados) + Leipzig (Alemania, EP-lab) ≠ población
  chilena: limitación explícita (§0), nunca mezclar poblaciones sin
  estratificar; LORO por institución/fuente; reportar métricas por estrato.
