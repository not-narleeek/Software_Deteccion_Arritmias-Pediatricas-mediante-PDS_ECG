# Reunión con D. Maureira — 2026-10-12

**Objetivo:** cerrar hoy las 3 decisiones bloqueantes de la Etapa II y dejar
registradas las respuestas por escrito (`docs/anotaciones_pendientes.txt`).
Evidencia completa: `docs/etapa2_corpus_combinado.md` (§2–§4) y
`results/experimento_corpus/`.

---

## 0. Contexto en 1 minuto (desde la reunión del 13-sep)

Se ejecutó la Etapa II completa sobre el corpus ampliado (>13.000 estudios):

| Resultado | Cifra |
|---|---|
| Corpus combinado ZZU pECG + Leipzig | 41.900 ventanas objetivo (Sinusal 37.872 / SVT 2.711 / VT 437 / Paced 880) |
| Detector R sobre ZZU (QC) | det_ok 100 % (13.436/13.436) |
| Mejor modelo (RF, GroupKFold por paciente) | F1 macro 0,518 · Brier 0,037 ✅ |
| KPI F1 ≥ 0,80 por clase | **No alcanzado** (Sinusal 0,95; SVT 0,35; VT 0,43; Paced 0,34) |
| Domain shift (ZZU↔Leipzig) | F1 0,36 / 0,10 según dirección |

La brecha del KPI es **estructural** del enfoque SVM/RF + features manuales
sobre ventanas de 10 s (3 iteraciones autorizadas: balanceo, submuestreo 3×,
features morfológicas P/RP/PR/V1 — mejora total solo +0,16 F1 macro).
Confusión dominante: SVT↔Sinusal (EAT vs sinuso-taquicardia, clínicamente
limítrofes a 10 s).

---

## 1. Decisión bloqueante A — Enmienda del KPI del acta (15 min)

F1 ≥ 0,80 por clase es inviable con los datos actuales. Tres opciones:

| Opción | Qué implica |
|---|---|
| (a) KPI a nivel **registro** (voto por ventanas) | Sinusal 94 % ya cumple; SVT 109/212, VT 27/51, Paced 3/10 — sigue lejos |
| (b) ≥ 0,80 solo **Sinusal + SVT**, VT/Paced como casos de estudio | Alcanzable acotando alcance; coherente con el soporte escaso de VT/Paced |
| (c) **Reposicionar como screening**: priorizar Se de arritmia + certeza calibrada (Brier ya cumple) | Cambia el relato del acta; la calibración es nuestra fortaleza medida |

**Pregunta asociada:** ¿qué Se mínima de SVT considera clínicamente útil
en screening pediátrico? (hoy: Se 0,57 / Sp 0,90).

---

## 2. Decisión bloqueante B — Clases y etiquetas (15 min)

1. **'Otro' (6.008 registros ZZU, 42 % del corpus, 24.853 ventanas):**
   ¿Sinusal implícito, clase aparte, o excluidos del sistema? Es la decisión
   con mayor impacto en datos disponibles.
2. **Mapeo AHA→clases:** ¿valida SVT = E50/E51/E52/E54/E55; VT = G70/G72/G74;
   Paced = pacing; Sinusal = A1/A2/C21–C26 (prioridad Paced>VT>SVT>Sinusal)?
   — cierra AP-1/2/3 pendientes desde septiembre.
3. **EAT (E52, 189 registros) dentro de SVT o separado?** Es la fuente
   principal de la confusión con sinuso-taquicardia (C21).
4. **VT como 4ª clase (435 ventanas) o detector binario "taquicardia ancha"
   de segundo nivel?**

---

## 3. Decisión bloqueante C — Población y datos chilenos (10 min)

La transferencia ZZU→Leipzig (F1 0,36) y el reverso (0,10) cuantifican el
domain shift que advirtió: modelo entrenado en población 'x' no sirve en 'y'.

**Estrategia propuesta:** entrenar en corpus público + declarar limitación +
fine-tuning cuando lleguen datos chilenos. ¿La respalda?

**Petición concreta:** carta de apoyo para gestiones con Isatec y los CEC de
Calvo Mackenna / Roberto del Río (Ley 19.628).

---

## 4. Menores (5 min, si queda tiempo)

- Leipzig: segmentos de sobremarcha (estimulación no fisiológica) etiquetados
  Paced — ¿correcto?
- Erratas a fuentes: edad x007 ('.14.3' en CSV oficial) y cifras del paper
  ZZU (3.516 vs 3.716 registros con ECV) — ¿consultamos?

---

## 5. Cierre y próximos pasos (según respuestas)

- Registrar cada respuesta como cierre de AP-n en `docs/anotaciones_pendientes.txt`.
- Con A+B resueltos: re-etiquetado del corpus y re-ejecución F14 final (una
  sola, con autorización previa según política de cómputo).
- Con C resuelto: enviar carta de apoyo a Isatec/CEC y redactar la limitación
  de población del FPS.
- Etapa III (nov–dic) sin cambios: informe final + demo + defensa.

---

### Registro de respuestas (llenar en la reunión)

| # | Tema | Respuesta |
|---|---|---|
| A | Enmienda KPI (a/b/c) | |
| A' | Se mínima SVT screening | |
| B1 | Tratamiento 'Otro' | |
| B2 | Mapeo AHA (AP-1/2/3) | |
| B3 | EAT ⊂ SVT o aparte | |
| B4 | VT 4ª clase o binario | |
| C | Estrategia población + carta | |
| M1 | Paced sobremarcha Leipzig | |
| M2 | Erratas a fuentes | |

---

## Registro de respuestas efectivamente recibidas (2026-10-12)

Del encuentro se retiraron dos recomendaciones (registradas como AP-14 y
planificadas en [docs/plan_dl_zzu.md](plan_dl_zzu.md)):

1. **Corpus único ZZU pECG** (el de más datos): falla de generalización entre
   poblaciones — entrenar y evaluar dentro de una sola; Leipzig deja el pool
   de entrenamiento (el plan lo conserva solo como validación externa).
2. **Deep Learning + Optuna** sobre los >13.000 estudios, entrenando en
   Google Colab o instancia gratuita (SVM/RF no dieron los resultados
   esperados).

Las demás filas de la tabla quedan pendientes de confirmación escrita
(enmienda del KPI y decisiones B1–B4, tratadas como gate F19 del plan).
Confirmado por el equipo el mismo 2026-10-12: presupuesto $0 (solo Colab
free, Kaggle únicamente como fallback) y que la exclusión de Leipzig aplica
al entrenamiento, conservándose como validación externa (D2 del plan).
