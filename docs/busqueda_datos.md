# Búsqueda y ampliación de datos — rama `busqueda-datos`

Creado: 2026-09-13, tras reunión con D. Maureira (AP-13).
Objetivo: pasar de 29 registros pediátricos a **>5000 estudios limpios y
correctamente clasificados** antes de reanudar pre-procesamiento y modelado.
F6–F8 ya verificados se re-ejecutan sobre el dataset ampliado; F9 (en pausa,
commit WIP 4d52c10 en `desarrollo`) se retoma con los datos nuevos.

## 1. Feedback del experto (D. Maureira, sep-2026)

Relevante para **datos** (esta rama):
- "Exámenes mal tomados, filtrar" → criterio de calidad obligatorio en la
  ingesta; los excluidos se listan y contabilizan, no se descartan en silencio.
- "Buscar más datos" → meta >5000 estudios (este documento).
- Contactar a Isatec → acción externa del equipo (posible fuente chilena).
- "Un modelo entrenado con población 'x' no suele funcionar con población
  'y'" → estratificar por población; corpus adultos solo con rol comparativo
  o de pre-entrenamiento (misma lógica que EX3 del acta).

Relevante para **modelado** (se retoma al volver a F8/F9, registrado aquí
para no perderlo):
- Combinaciones de canales pueden identificar patologías → explorar features
  por derivación y combinadas (p. ej. II+V1/V2) en el hito de features.
- Serie de tiempo → imágenes y vuelta: "suelen dar resultados similares" →
  línea opcional de comparación, no prioritaria.
- Ver por canales individuales o combinar → ídem, decisión con evidencia.

No aplicable al desarrollo: dimensionamiento de precio/valor para la empresa.

## 2. Criterios de aceptación (un estudio entra solo si)

1. **Población pediátrica identificable** (edad por registro) — o rol
   explícito comparativo/pre-entrenamiento (adultos, EX3), nunca mezclados
   sin control (§5).
2. **Derivaciones suficientes**: 12 derivaciones ideal; mínimo I/II y al
   menos una precordial (el detector F7 fusiona II+V2; sin V2 hay fallback a
   II-only — verificar impacto con `validar_detector_r.py`).
3. **Etiqueta mapeable** a la taxonomía del proyecto (Sinusal/SVT/Paced u
   "Otro", AP-1): etiqueta de ritmo por segmento (ideal, tipo Leipzig) o
   diagnóstico por registro si el mapeo es defendible y queda documentado.
4. **Calidad**: SQI del propio dataset si existe + nuestro vector de calidad
   (AP-6); exámenes mal tomados excluidos con lista explícita (feedback §1).
5. **Duración** ≥ 10 s para generar al menos una ventana de 10 s.
6. **Licencia** abierta verificada (CC BY 4.0, ODbL, etc.) o convenio formal
   (Isatec/hospital); se registra con el inventario.

## 3. Fuentes candidatas (verificadas 2026-09-13 vía web)

| Fuente | Registros | Edad | Señal | Etiquetas | Licencia | Rol |
|---|---|---|---|---|---|---|
| **ZZU-pECG** (Zhengzhou Univ.; Figshare; DOI 10.1038/s41597-025-05225-z) | 14.190 (12.334 × 12-deriv; 1.856 × 9-deriv **sin V2/V4/V6**) de 11.643 niños | 0–14 (mediana ~8,6 a) | 500 Hz, 5–120 s | ICD-10 de alta; 3.716 con CVD en 19 categorías pediátricas; incluye pSQI/basSQI/bSQI | CC BY 4.0 | **Candidato primario** |
| Leipzig Heart Center (actual, `data/`) | 39 (29 pediátricos) | ped + adultos comparativos | 12 deriv + IEGM, WFDB | ritmo por segmento (`.atr` experto) | abierta | En uso (insumo F1–F8) |
| PTB-XL (PhysioNet) | 21.837 (18.885 pacientes) | predominantemente adulto | 12 deriv, 10 s | diagnóstico SNOMED | CC BY 4.0 | Comparativo/pre-entrenamiento (EX3) |
| CPSC 2018 (ICBEB) | 6.877 (11 hospitales) | adulto (algunas edades NaN) | 12 deriv, 6–60 s, 500 Hz | 9 clases (Normal, AF, I-AVB, LBBB, RBBB, PAC, PVC, STD, STE) | abierta | Comparativo (EX3) |
| MIMIC-IV-ECG (PhysioNet) | ~800.000 (~160.000 pacientes) | **18+** | 12 deriv, 10 s, 500 Hz | diagnóstico | credencial DUA | Comparativo (EX3); requiere tramitación |
| CinC Challenge 2020 (PhysioNet) | agregado multi-fuente (incluye CPSC/PTB-XL; tamaño por verificar) | predominantemente adulto | 12 deriv | multi-etiqueta SNOMED | abierta | Evaluar aporte marginal vs fuentes ya listadas |
| **Isatec** / hospitales locales | ? | ? | ? | ? | convenio | **Acción externa del equipo** — contactar (única vía plausible de más ritmo-anotado pediátrico SVT/Paced) |

Advertencias específicas de ZZU-pECG (verificar en la ingesta, no asumir):
- La etiqueta es **diagnóstico ICD-10 de alta**, no anotación de ritmo por
  segmento → mapear las 19 categorías a la taxonomía AP-1 y verificar
  presencia real de taquicardias/marcapasos; los registros "sin CVD"
  (~10.474) asumirlos sinusales solo tras spot-check del equipo.
- 1.856 registros de 9 derivaciones **carecen de V2** → fallback II-only del
  detector F7 en ese subconjunto; medir degradación antes de incluirlos.
- Duraciones 5–120 s: los registros < 10 s no generan ventanas; contabilizar.
- Formato Figshare ≠ WFDB → extender `io.py` con lector propio + tests.
- Hospital chino 0–14 años: población distinta de Leipzig/chilena → §5.

## 4. Protocolo de ingesta por fuente (reusar el método F1)

1. **Descarga y fijado**: snapshot de versión + SHA256 de todos los archivos
   (`results/inventario_<fuente>/`), igual que F1.
2. **Inventario automatizado**: extender `scripts/inventario.py` — edad, sexo,
   derivaciones, fs, duración, etiqueta cruda, etiqueta mapeada, distribución
   por clase y por fuente.
3. **Filtro de calidad** ("exámenes mal tomados"): SQI del dataset si existe
   (pSQI/basSQI/bSQI en ZZU-pECG) + nuestro vector (AP-6) → lista explícita
   de excluidos con causa y conteo en `results/`.
4. **Criterio de cierre**: ≥5000 estudios pediátricos aceptados tras §4.3.
   La distribución por clase primaria (Sinusal/SVT/Paced) se reporta al
   cierre; si SVT/Paced pediátricos etiquetados quedan muy por debajo de
   Sinusal en fuentes abiertas, se registra la limitación y se priorizan las
   gestiones con Isatec/hospitales (la meta numérica no puede relajar la
   validez clínica de las etiquetas).
5. **Decisión de reanudación**: con el dataset ampliado fijado, re-ejecutar
   F6 (filtros), F7 (detector) y F8 (features) sobre los datos nuevos y
   retomar F9 — los scripts de verificación ya existen y son re-ejecutables.

## 5. Riesgo domain shift (advertencia explícita del experto)

- Pediátrico es la población objetivo; corpus adultos (PTB-XL, CPSC,
  MIMIC-IV-ECG) solo comparativos o pre-entrenamiento, bajo cláusula EX3.
- Al combinar ZZU-pECG (China) + Leipzig (Alemania) + eventuales datos
  chilenos: LORO estratificado por fuente/institución; reportar métricas por
  estrato además de la global. Nunca entrenar en una población y reportar
  KPI en otra sin declararlo.

## 6. Acciones (checklist de la rama)

- [ ] **Ingesta ZZU-pECG**: descarga, SHA256, lector `io.py`, inventario,
      mapeo de etiquetas, filtro de calidad (§4) — candidato primario.
- [ ] Verificar mapeo 19 categorías ICD-10 → taxonomía AP-1; spot-check de
      registros "sin CVD" como sinusales.
- [ ] Medir degradación del detector F7 sin V2 (subconjunto 9-deriv).
- [ ] Contactar Isatec (equipo; preguntar por datos pediátricos chilenos).
- [ ] Consultar a PhysioNet errata edad x007 (AP-10) en el mismo hilo.
- [ ] Evaluar aporte marginal de CinC-2020 vs CPSC/PTB-XL ya listadas.
- [ ] Al cierre: actualizar AP-13 en `anotaciones_pendientes.txt` con cifras
      finales (aceptados/excluidos/por clase) y decisión de reanudación.

## Referencias

- ZZU-pECG — Scientific Data: https://doi.org/10.1038/s41597-025-05225-z
  (dataset en Figshare, búsqueda "ZZU pECG Zhengzhou University Pediatric
  ECG Database").
- Leipzig Heart Center: https://physionet.org/content/leipzig-heart-center-ecg/
- PTB-XL: https://physionet.org/content/ptb-xl/
- CPSC 2018: http://2018.icbeb.org/Challenge.html
- MIMIC-IV-ECG: https://physionet.org/content/mimic-iv-ecg/
