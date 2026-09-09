# Plan de acción — Etapas II y III

**Rama:** `desarrollo` (fallback: `main` queda intacta en el estado de la Etapa I hasta el
feedback de D. Maureira).
**Fecha:** 9 de septiembre de 2026. Semana 2 de 16 (fin: 20-dic).

---

## 0. Estado

| Etapa | Contenido | Estado |
|---|---|---|
| I — Propuesta (PPS, E1) | Exploración dataset, literatura, diseño pipeline | **Completa** (F1–F5); PPS v0.1 pendiente de validación del experto (AP-1/2/3) |
| II — Avance + Prototipo (APS) | Implementación del pipeline completo en Python | **Por desarrollar** — desde hoy |
| III — Informe Final + Defensa (FPS/DPS) | Sistema completo, métricas, casos clínicos, demo | Por desarrollar |

Insumos listos: dataset verificado en `data/` (126/126 SHA256), inventario automatizado
(`results/inventario/`), diseño formal con contratos tipados (`src/ecg_pipeline/` —
esqueleto con `NotImplementedError`), protocolos de verificación por KPI
(`docs/diseno_pipeline.md` §11).

## 1. Bloqueante externo y estrategia

**RS4:** la validación de D. Maureira sobre AP-1 (3 clases + VT/AFL como casos),
AP-2 (AFIB→SVT) y AP-3 (excluir `(B`) sigue pendiente.

Estrategia: **no esperar**. El único punto del código que depende de AP-1/2/3 es el mapeo
ritmo→clase, aislado en `io.segmentos_ritmo()` (reusa el mapeo de `scripts/inventario.py`).
Todo lo demás (filtros, detector R, features, protocolo de validación, reporte) es
agnóstico a la decisión del experto. Si el experto rechaza la propuesta de 3 clases, el
cambio se concentra en ese mapeo y en las tablas de resultado — no en el pipeline.

Acción inmediata (esta semana): enviar PPS v0.1 a D. Maureira solicitando validación
**por escrito** de AP-1/2/3 (ya comprometido en PPS §7). Registrar respuesta en
`docs/anotaciones_pendientes.txt` (bitácora de cierre).

## 2. Etapa II — hitos de implementación

Numeración de commits: F6, F7, … (continúa la serie). Cada hito = código + script de
verificación + resultados comprometidos. Cada script de verificación **falla (exit ≠ 0) si
su KPI no se cumple** (§11 del diseño).

### Hito F6 — IO + preprocesamiento (semanas 1–2 del cronograma PPS)

- Implementar `io.py`: `cargar_registro`, `segmentos_ritmo`, `construir_indice_ventanas`,
  `cargar_ventana`.
- Implementar `preprocess.py`: `preprocesar` (HP 0.5 → notch 50 Q=35 → LP 40, SOS +
  `sosfiltfilt`), `detectar_espiculas` (banda 80–250 Hz, §3.2),
  `documentar_respuesta` (RF2).
- Crear `scripts/validar_filtros.py`: respuesta en frecuencia (figuras
  `results/figuras/respuesta_frecuencia_*.png`) + protocolo de distorsión §3.4 sobre
  ≥ 200 latidos sinusales de ≥ 10 registros limpios.
- **Aceptación:** mediana(D) < 5 %, p90(D) < 10 %, ΔQRS < 5 ms. Además,
  `construir_indice_ventanas` debe reproducir las cifras del diseño (1.971/320/186
  ventanas Sinusal/SVT/Paced) — prueba de regresión contra F1/F2.

### Hito F7 — Detector de picos R (semanas 2–3)

- Implementar `features.detectar_picos_r` (base Kathirvel 2011) + variante comparadora
  Pan-Tompkins (banda 8–20 Hz, refractario 120 ms, §4).
- Crear `scripts/validar_detector_r.py`: validación contra `.atr` (tolerancia ±100 ms),
  por registro y global.
- **Aceptación:** Se y +P ≥ 95 % (KPI del acta). Si Kathirvel no alcanza, el comparador
  PT adaptado ya está especificado como fallback.

### Hito F8 — Features + separabilidad (semanas 3–5)

- Implementar `features.vector_caracteristicas` (46 features, §6: RR 10 + QRS 9 + P 3 +
  espículas 2 + espectrales 10 + DCT 8 + calidad 2 + demográficas 2) con
  `FEATURE_NAMES` estable.
- Implementar `features.separabilidad` (ANOVA + Fisher) y experimento **DCT vs wavelet**
  (db4 nivel 4) — cláusula justificar-o-sustituir del diseño (vacío F3-1).
- **Aceptación:** tabla ANOVA/Fisher por feature (KPI objetivo 2); descartes documentados
  (p > 0.05 y Fisher nulo); decisión DCT/wavelet con evidencia escrita.

### Hito F9 — Clasificador + validación LORO (semanas 5–7)

- Implementar `models.py`: `entrenar_calibrado` (SVM-RBF primario / RF comparador,
  calibración Platt), `validacion_loro` (LORO 29 folds, GroupKFold interior por registro,
  §8.1), `curvas_confiabilidad`.
- Crear `scripts/ejecutar_experimento.py`: experimento completo, SVM y RF, tabla de
  métricas §8.2 (Se/Sp por clase y macro, F1, matrices por ventanas y por registros,
  IC bootstrap), Brier multiclase, reliability diagrams.
- **Aceptación:** Se/Sp ≥ 85 % global, F1 ≥ 0.80 en las 3 clases primarias, Brier < 0.2
  (KPI 3/4). Si no se alcanza: diagnóstico (matriz de confusión, features top), ajuste de
  grilla/reducción de features, re-ejecución — todo registrado en `results/`.

### Hito F10 — Reporte + estudios de caso + demo (semanas 7–8)

- Implementar `report.py`: `reportar` → `Diagnostico` (clase + probs calibradas
  renormalizadas + advertencias AP-6/soporte escaso).
- Estudio de caso VT: detector binario **solo con los 10 registros adultos** (ventanas
  10 s / hop 5 s, EX3 — nunca mezclado con el conjunto pediátrico).
- Estudio de caso AFL: análisis morfológico descriptivo del único segmento (x006).
- CLI o notebook de demo: señal WFDB → pipeline → diagnóstico con certeza (entregable E5).

### Cierre de Etapa II

- Notas metodológicas AP-4/5 (cifras dataset vs acta) — redactar en el informe de avance.
- Si el experto validó 3 clases: enmienda menor del KPI del acta ("F1 ≥ 0.80 por clase"
  → "por clase primaria") y bitácora de cierre de AP-1/2/3.
- Merge a `main` del estado validado (fin del rol de fallback de main).

## 3. Etapa III — informe final + defensa (nov–dic)

1. **FPS (informe final):** consolidar resultados de Etapa II con limitaciones explícitas
   (VT/AFL como casos, calibración, validación retrospectiva), casos clínicos
   representativos por clase, figuras de resultados ya generadas en `results/`.
2. **Demo funcional (E5):** reproducción en vivo del pipeline sobre registros del dataset
   (script + notebook; sin dependencia de red).
3. **DPS (defensa):** presentación con arquitectura, evidencia de KPIs cumplidos (salidas
   de los 3 scripts de verificación) y desviaciones documentadas (AP-1/2/3, AP-4/5).
4. Reproducibilidad: `uv sync` + scripts → mismos resultados; `requirements.txt` exportable
   si la cátedra lo exige.

## 4. Calendario propuesto (ajustar con el equipo)

| Fechas | Trabajo | Verificación |
|---|---|---|
| 09–20 sep | F6: io + filtros | `validar_filtros.py` verde |
| 21–30 sep | F7: detector R | `validar_detector_r.py` ≥ 95 % |
| 01–17 oct | F8: features + separabilidad | Tabla ANOVA/Fisher + decisión DCT/wavelet |
| 18 oct–06 nov | F9: modelos + LORO | `ejecutar_experimento.py`: KPI 3/4 |
| 07–20 nov | F10: reporte + VT/AFL + demo | Demo E5 funcional |
| 21 nov–04 dic | Informe final (FPS) + revisión experto | PPS→FPS consistente |
| 05–20 dic | Defensa (DPS) + buffer | — |

Margen: ~2 semanas de holgura antes del 20-dic para absorbimiento de retrasos (principal
riesgo: RS4 respuesta tardía del experto → no bloquea F6–F8; solo F9-final y la enmienda
del acta).

## 5. Convenciones de trabajo en `desarrollo`

- Un commit por hito (F6, F7, …), mensaje con prefijo del hito; resultados y figuras
  comprometidos en el mismo commit que el código que los genera.
- Todo se ejecuta con `uv run python …` (entorno fijado por `uv.lock`).
- `main` no recibe nada hasta cierre validado de Etapa II (fallback del acta original).
- Toda decisión nueva que surja se registra como AP-n nueva en
  `docs/anotaciones_pendientes.txt` (no solo en el mensaje de commit).
