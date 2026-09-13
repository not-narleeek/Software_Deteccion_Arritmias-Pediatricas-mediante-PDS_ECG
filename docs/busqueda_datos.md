# Búsqueda de datos — rama `busqueda-datos` (foco CHILE)

Creado: 2026-09-13, tras reunión con D. Maureira (AP-13).
Revisado: 2026-09-13 — alcance acotado exclusivamente a Chile.

## 0. Objetivo y alcance

**>5000 estudios ECG pediátricos chilenos, limpios y correctamente
clasificados**, antes de reanudar pre-procesamiento y modelado. F6–F8 ya
verificados se re-ejecutan sobre el dataset ampliado; F9 (en pausa, commit
WIP 4d52c10 en `desarrollo`) se retoma con los datos nuevos.

**Decisión de alcance (2026-09-13, equipo, en línea con el experto):**
un modelo entrenado en población 'x' no suele funcionar en población 'y'
("la taquicardia en Inglaterra no es igual que en Chile"). Consecuencias:
- Leipzig (`data/`, alemán) queda como insumo de **desarrollo del método**
  (protocolo, scripts, verificación F1–F8) y comparación — no población de
  entrenamiento del sistema final.
- Fuentes internacionales (ZZU-pECG, PTB-XL, CPSC, MIMIC-IV-ECG) pasan a
  **reserva**: `docs/reserva_datos_internacionales.md`.

## 1. Feedback del experto (D. Maureira, sep-2026)

Para **datos** (esta rama):
- "Exámenes mal tomados, filtrar" → criterio de calidad obligatorio en la
  ingesta; los excluidos se listan y contabilizan, no se descartan en
  silencio.
- "Buscar más datos" → meta >5000 estudios (este documento).
- Contactar a Isatec → acción externa del equipo (§3, prioridad 1).
- Domain shift (población 'x' → 'y') → alcance Chile; corpus no-chilenos
  solo con rol comparativo/pre-entrenamiento declarado (§0, EX3).

Para **modelado** (retomar en F8/F9, registrado para no perderlo):
- Combinaciones de canales pueden identificar patologías → features por
  derivación y combinadas.
- "Ver por canales o combinar" → ídem, decisión con evidencia.
- Serie de tiempo → imágenes: resultados suelen ser similares → línea
  opcional, no prioritaria.

No aplicable al desarrollo: precio/valor para la empresa.

## 2. Criterios de aceptación (un estudio entra solo si)

1. **Procedencia chilena** con institución identificable (población
   objetivo); datos no-chilenos solo vía reserva (§0).
2. **Trazo crudo** — señal digital reutilizable, no PDF/imagen: formatos
   aceptables SCP-ECG, DICOM-ECG, XML (Philips/GE/Mortara/MUSE), WFDB,
   MAT/CSV exportado por el equipo adquirente.
3. **Derivaciones**: 12 ideal; mínimo I/II + al menos una precordial (el
   detector F7 fusiona II+V2; sin V2 hay fallback II-only — medir
   degradación antes de aceptar subconjuntos sin V2).
4. **Etiqueta mapeable** a la taxonomía del proyecto (Sinusal/SVT/Paced u
   "Otro", AP-1): informe de cardiólogo pediatra por estudio (ideal con
   segmentación por ritmo) o etiqueta de egreso mapeable y documentada.
5. **Calidad**: SQI propio si existe + nuestro vector (AP-6); exámenes mal
   tomados excluidos con lista explícita y causa.
6. **Duración** ≥ 10 s por ventana usable (ventanas 10 s / hop 5 s).
7. **Marco legal**: convenio + CEC + anonimización verificada (§4).

## 3. Fuentes chilenas (verificadas 2026-09-13)

**Hecho verificado: en Chile NO existe repositorio público de trazos ECG
individuales.** DEIS/MINSAL/datos.gob.cl publican solo estadísticas
agregadas (series REM: nº de exámenes por establecimiento; egresos y
mortalidad), sin registros individuales, por Ley 19.628 y secreto
estadístico. El camino a >5000 estudios es necesariamente institucional
(convenio + CEC) o industrial (Isatec).

| Fuente | Qué tiene | Vía de acceso | Estado |
|---|---|---|---|
| **Isatec** (Instituto de Salud y Tecnología de Chile Ltda., desde 2009) | Plataformas de tele-informe ECG reposo 12 deriv + Holter de ritmo en decenas de establecimientos de todo el país; **decenas de miles de pacientes/mes**; proyecto propio de IA (CardIA-ECG, Corfo); ISO 9001 | Contacto/convenio directo (sugerido por D. Maureira) | **Prioridad 1 — contactar (equipo)** |
| **Hospital Luis Calvo Mackenna** (pediátrico, RM) | Ficha clínica electrónica con ECG digitales; Centro Cardiovascular; Unidad de Investigación con protocolo formal de registros/bases de datos + CEC | Protocolo a Unidad de Investigación / CEC | Prioridad 2 |
| **Hospital Roberto del Río** (pediátrico, RM) | Policlínico de cardiología pediátrica de referencia; registros en ficha electrónica | Ídem | Prioridad 2 |
| Red UC Christus / Hospital Clínico U. de Chile | Registros ECG académicos | CEC institucional + convenio | Prioridad 3 |
| Registro Nacional de Cardiopatías Congénitas (iniciativa: Calvo Mackenna + Roberto del Río + Instituto Nacional del Tórax) | Variables clínicas, imagenográficas y electrocardiográficas | Gestionar adhesión vía contactos clínicos | Explorar |
| datos.gob.cl / DEIS-MINSAL | SOLO estadísticas agregadas (REM, egresos, mortalidad) | Descarga pública | Uso: dimensionar oferta (justificación del protocolo), NO entrenamiento |

Nota Isatec: son la única fuente con volumen ya agregado a escala nacional
(decenas de miles/mes). Preguntar explícitamente por: pediátricos con
informe de especialista, trazo crudo (no solo informe), derivaciones
disponibles, fs, y condiciones de uso/anonimización; evaluar NDA/convenio
de colaboración (también posible socio tecnológico — tienen su propio
proyecto de IA cardiológica).

## 4. Requisitos legales y éticos (Ley 19.628)

- Protocolo de investigación aprobado por el CEC del establecimiento.
- Disociación/anonimización estricta (sin identificadores directos;
   fechas desplazadas; sin datos re-identificables).
- Convenio de uso de datos institución-equipo, con formato de entrega
  definido (crudo convertible, §2.2).
- Checklist operativa a completar cuando exista el primer contacto formal.

## 5. Protocolo de ingesta (reusa el método F1)

1. **Fijado**: snapshot de versión + SHA256 de todo lo entregado
   (`results/inventario_<fuente>/`).
2. **Conversión**: SCP-ECG/DICOM-ECG/XML → representación interna WFDB o
   equivalente; extender `io.py` con lector propio + verificación de
   round-trip (amplitudes/fs).
3. **Inventario automatizado**: extender `scripts/inventario.py` — edad,
   sexo, derivaciones, fs, duración, etiqueta cruda, etiqueta mapeada
   (AP-1), distribución por clase y por institución.
4. **Filtro de calidad** ("exámenes mal tomados"): SQI del proveedor si
   existe + nuestro vector (AP-6) → lista explícita de excluidos con causa
   y conteo en `results/`.
5. **Criterio de cierre**: ≥5000 estudios chilenos aceptados tras §5.4,
   con distribución por clase reportada. Si tras las gestiones la realidad
   institucional no permite alcanzar >5000 chilenos dentro del horizonte
   del proyecto, la decisión (relajar la meta, extender plazos, enmendar
   alcance con respaldo del experto) se documenta en AP-13 — **no se
   resuelve en silencio ni mezclando poblaciones**.
6. **Reanudación**: dataset ampliado fijado → re-ejecutar F6/F7/F8 sobre
   datos nuevos y retomar F9.

## 6. Riesgo domain shift (advertencia explícita del experto)

- Población objetivo: pediátrico chileno. Corpus no-chilenos solo
  comparativos/pre-entrenamiento declarado (reserva).
- Si se combinan fuentes chilenas (Isatec + hospitales): LORO estratificado
  por institución; reportar métricas por estrato además de la global.
- Nunca entrenar en una población y reportar KPI en otra sin declararlo.

## 7. Acciones (checklist de la rama)

- [ ] **Contactar Isatec** (equipo; pedir pediátricos con trazo crudo +
      informe; condiciones de uso) — prioridad 1.
- [ ] Preparar protocolo CEC Calvo Mackenna / Roberto del Río (equipo +
      tutor clínico; usar tutor de la universidad como puerta de entrada).
- [ ] Dimensionar oferta con DEIS (ECG/mes por establecimiento, egresos
      por arritmia pediátrica) para justificar el protocolo.
- [ ] Conversor de formatos (SCP-ECG/DICOM-ECG/XML) en `io.py` cuando
      llegue la primera entrega.
- [ ] Consultar errata edad x007 a PhysioNet (AP-10).
- [ ] Al cierre: actualizar AP-13 con cifras finales (aceptados/excluidos/
      por clase) y decisión de reanudación.

## Referencias (verificación 2026-09-13)

- Isatec: https://www.isatec.cl/ (secciones quienes-somos, innovación,
  clientes) y https://www.isatec.cl/innovachile/ (CardIA-ECG, Corfo).
- Calvo Mackenna, Unidad de Investigación:
  https://www.calvomackenna.cl/informacion_academica/unidad_investigacion
- Roberto del Río: https://www.hrrio.cl/
- DEIS: https://deis.minsal.cl — datos abiertos: https://datos.gob.cl
- Ley 19.628 (protección de datos personales) — condiciona todo el acceso.
