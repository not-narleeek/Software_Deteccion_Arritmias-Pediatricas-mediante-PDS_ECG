# Revisión bibliográfica — Software de Detección de Arritmias Pediátricas

**Etapa I (PPS) / F3.** Bibliografía anotada y verificada. Las citas `[autorAño]` resuelven
en `referencias.bib` (solo entradas con metadatos confirmados contra fuente primaria).
Al final: candidatos pendientes de verificación y vacíos detectados.

---

## A. Dataset y recursos de señal

**[klehs2025leipzig]** — Dataset del proyecto. 39 registros (29 niños, 10 adultos con CC),
977 Hz, formato WFDB, anotado latido a latido por dos expertos con LightWAVE®.
*Datos duros clave para el diseño:*
- Los ECG provienen de **estudios electrofisiológicos (EEF)** e incluyen "segmentos con
  estimulación no fisiológica" (p. ej. la sobremarcha auricular a ~220 bpm observada en
  x009 en F2) → el pipeline debe tratar esos tramos como Paced, no como taquiarritmia
  espontánea.
- Ancho de banda de registro **0.05–100 Hz**, señales "en bruto" sin filtrado posterior
  → todo el preprocesamiento es responsabilidad nuestra y un LP a ~40 Hz (hallazgo F2)
  está dentro de la banda útil; preservar espículas exige no recortar demasiado.
- Descripción oficial: **1075.85 min y 113.924 latidos**. Nuestros archivos dan 1107.0 min
  y 115.748 anotaciones de latido → discrepancia documentada (AP-4/AP-5).
- Distribución oficial de latidos: N 33%, preexcitación 12%, CRBBB 11%, SVT 23%
  (AVRT 15% + AVNRT 8%), marcapasos 12%, prematuros 7%.
- Adultos: solo tetralogía de Fallot (TOF), alto riesgo de VT — coherente con F1
  (VT adulto 34.3 min vs pediátrico 0.9 min).

**[goldberger2000physionet]**, **[pollard2026physionet]** — Recurso PhysioNet y su evolución;
citación estándar obligatoria al usar el dataset.

**[moody2001impact]** — El impacto de MIT-BIH: contrapunto histórico; su población es
adulta, motivo por el cual el dataset Leipzig existe (subrepresentación pediátrica).

**[zheng2020twelve]**, **[wagner2020ptbxl]** — Datasets 12-derivaciones masivos (adultos).
Útiles solo para discusión (¿preentrenamiento?); el dominio pediátrico difiere
fisiológicamente → transfer learning riesgoso (brecha de dominio).

## B. ECG pediátrico normal vs adulto

**[davignon1979normal]** — Estándares ECG pediátricos clásicos (medición manual,
población canadiense). Base histórica de los criterios clínicos por edad.

**[rijnbeek2001continuous]** — Nuevos límites normales continuos por edad y sexo
(1.912 niños holandeses, 11 días–16 años, medición computarizada a 1200 Hz).
Difiere sustancialmente de Davignon (amplitudes R/S mayores).

*Implicaciones de diseño (→ F4):*
1. **La edad es covariable obligatoria**: RR, duración de QRS y amplitudes normales
   cambian con la edad (F1: 0.1–17 años en pediátricos). El vector de características
   debe incluir edad o normalizar por percentiles de [rijnbeek2001continuous].
2. QRS pediátrico más **corto y de mayor contenido en altas frecuencias** que el adulto:
   la banda clásica 5–15 Hz de detección QRS debe desplazarse hacia arriba.
3. Patrón T juvenil y dominancia derecha (R en V1) en lactantes: riesgo de que la
   discriminación T-vs-QRS de un detector adulto falle.

## C. Arritmias objetivo en pediatría / cardiopatía congénita

Síntesis clínica (validación pendiente del experto asesor, D. Maureira — AP-2/AP-3):

- **SVT** (AVRT/AVNRT): QRS estrecho (<90 ms), tasa fija >220 bpm lactantes / >180 bpm
  niños, P ocultas o retrógradas. Coincide con lo medido en F2 (x0011 AVRT a 219.6 bpm).
- **AFL**: ondas F en diente de sierra en II/III/aVF, auricular 250–500 bpm con bloqueo
  AV fijo 2:1/3:1; típica post-cirugía de CC. F2: x006, 37 s — escasez confirmada.
- **VT**: QRS ancho (>90 ms pediátrico), disociación AV, monomorfa en postoperatorio TOF;
  "taquicardia ancha = VT hasta probar lo contrario". F2: x002, 15.6 s a 123 bpm
  (TV lenta/no sostenida).
- **Paced**: espícula + QRS (ancho si ventricular). En EEF conviven ritmos estimulados
  con espontáneos → el detector de espículas importa para el etiquetado de ventanas.

## D. Preprocesamiento (filtrado)

Evidencia cruzada literatura + F2 (notebook 03):
- **Deriva basal**: ruido 0.05–0.6 Hz; alternativas HP clásico vs. spline cúbico (nudos
  en PQ) vs. wavelet. Riesgo documentado de distorsión de ST/QRS si el corte HP sube.
  El acta exige distorsión <5 % en QRS → protocolo de medición obligatorio en F4.
- **Interferencia 50 Hz**: notch fijo estándar; Q alto = banda más angosta pero riesgo
  de "ringing" sobre el QRS; notch adaptativo de resolución aguda es la alternativa
  cuando la interferencia es fuerte. F2 la medición: heterogénea (x001 domina con ~6
  órdenes de magnitud; x100 sin pico) → el diseño debe cuantificar el daño del notch
  en registros limpios (posible aplicación condicional por registro).
- Bandas del dataset (0.05–100 Hz) fijan el techo físicamente defendible del LP.

## E. Detección de picos R

**[pan1985real]** — Algoritmo de referencia (bandpass 5–15 Hz + derivada + umbral
adaptativo). Diseñado para adultos: HR 60–100, QRS 80–120 ms.

*Adaptación pediátrica requerida* (de B y C): banda desplazada a frecuencias mayores,
ventanas de búsqueda acortadas (RR pediátrico corto, hasta 220+ bpm en SVT), umbral
robusto a amplitudes variables con la edad, y validación **sobre dataset pediátrico**
(no MIT-BIH). KPI del acta: precisión ≥95 % contra `.atr`.

**[kathirvel2011efficient]** — Detector R basado en transformación no lineal + derivador
gaussiano de primer orden. **Es el algoritmo usado por los autores del dataset para
rellenar las anotaciones por rango** (ref. [8] de la página de PhysioNet) → usarlo como
detector base alinea nuestro pipeline con el proceso de anotación; candidatura fuerte
para F4 frente a Pan-Tompkins puro.

## F. Características morfológicas y espectrales

Consenso de la literatura de ML-ECG clásico: con datasets pequeños, las características
"diseñadas a mano" superan al aprendizaje de representaciones: intervalos RR (media,
SDNN, RMSSD, proporción de diferenciales), duración/amplitud de QRS y onda P,
energía por bandas, coeficientes de transformadas (wavelet con amplio respaldo;
**DCT —mandatada por el acta RF4— con soporte bibliográfico débil hasta ahora**,
ver "Vacíos"). Edad del paciente como covariable (sección B).

## G. Clasificación con datasets pequeños

**[teich2023apple]** — Mismo grupo Leipzig: análisis automatizado de iECG pediátricos
(Apple Watch). Antecedente directo de viabilidad del enfoque en esta población.

Decisiones metodológicas respaldadas:
1. **Modelos clásicos (SVM/RF) sobre features** — robustos en espacios de dimensión
   media con pocos samples; RF tolera ruido y desbalance moderado.
2. **Validación por registro** (leave-one-record-out) — obligatoria: ventanas del mismo
   registro están correlacionadas; F1/F2 muestran registros con mezclas de ritmos.
   **[cawley2010over]**: la selección de hiperparámetros sobre el mismo CV que reporta
   el desempeño infla los resultados → CV anidado (o LORO exterior + selección interior).
3. **Desbalance severo** (F2: Sinusal 617 min vs VT 0.9 min) — **[chawla2002smote]**
   (oversampling sintético en el espacio de features); con cautela: las ventanas de un
   mismo registro no son intercambiables, y con <1 min de VT pediátrico el oversampling
   no sustituye la revisión del conjunto de clases (AP-1). Alternativas: pesos de clase,
   métricas por clase, fusión de clases minoritarias.
4. **Calibración de probabilidades** (RF6, Brier <0.2) — **[platt1999probabilistic]**
   (sigmoide paramétrica), **[zadrozny2002transforming]** (regresión isogónica
   multiclase), **[niculescu2005predicting]** (evaluación empírica: SVM y ensambles
   mejoran drásticamente tras calibrar; con pocos datos isónica tiende a sobreajustar
   → Platt/sigmoid como primera opción). Métrica: **[brier1950verification]**.

---

## Coincidencias y contrastes con F1/F2

| Afirmación de literatura | Medido en F1/F2 | Veredicto |
|---|---|---|
| SVT pediátrica >180–220 bpm, QRS estrecho | x0011 AVRT 219.6 bpm, estrecho | ✓ |
| AFL 2:1, diente de sierra inferior | x006: ~300:~175, sierra en II/III/aVF | ✓ |
| VT post-TOF en adultos | VT adulto 34.3 min vs ped 0.9 min | ✓ (AP-1) |
| Interferencia de red variable entre registros | pico 50 Hz en 3/4 registros, x001 ~10⁶× | ✓ |
| 1075.85 min / 113.924 latidos (oficial) | 1107.0 min / 115.748 anotaciones | ✗ discrepancia (AP-4/5) |

## Vacíos detectados (insumo para F4/F5)

1. **DCT como feature ECG**: sin referencia sólida encontrada aún. El acta la exige
   (RF4); F4 debe justificarla experimentalmente (separabilidad) o documentar la
   sustitución por wavelet.
2. **Notch adaptativo**: candidatos identificados pero metadatos sin verificar
   (ver abajo); decidir notch fijo de Q moderado vs adaptativo según el presupuesto
   de complejidad.
3. **Filtrado previo 0.05 Hz del amplificador**: al estar ya limitado el paso bajo en
   el registro, la deriva residual medida en F2 es la que el HP del pipeline debe
   atacar; documentar el corte mínimo defendible (<0.5 Hz) para no tocar ST.

## Candidatos pendientes de verificación (NO en referencias.bib)

- *ECG Baseline Wander Removal and Impact on Beats Morphology* (análisis comparativo,
  ResearchGate) — autores/año por confirmar.
- *Removal of Power Line Interference From ECG Signals Using Adaptive Notch Filters of
  Sharp Resolution* (IEEE Access ~2019) — autores por confirmar.
- Revisión clínica formal de taquiarritmias pediátricas (SVT/AFL/VT) para la sección C
  — candidata a pedirla al experto asesor (D. Maureira) junto con la validación de AP-1/2/3.
