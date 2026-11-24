# Rediseño del landing — requerimientos de contenido y evidencia

**Estado:** especificación lista para implementación (agente implementador: sección web del portal).
**Alcance:** solo contenido nuevo de la página de inicio (`web/index.html` + `css/styles.css`
si se requieren estilos). El analizador (`js/app.js`, `js/wfdb.js`), los registros demo y el
resto de secciones no se modifican salvo la navegación.
**Convenciones del repo aplicables:** `web/` sin dependencias ni build (HTML/CSS/JS puro);
todo en español; el aviso de **uso académico / no dispositivo médico** es innegociable y
debe permanecer visible; ninguna cifra sin fuente comprometida.

---

## 1. Objetivo

La página de inicio debe contar la historia completa del proyecto en este orden:

1. **Presentar el proyecto** (hero, ya existe, ajustes menores).
2. **La problemática**: qué son las arritmias pediátricas, magnitud según la literatura,
   sus consecuencias y su mortalidad.
3. **La situación en Chile**: datos nacionales y el vacío de información que existe.
4. **La solución**: qué hace este software.
5. **Propuesta de valor social** (beneficios, no valor monetario).
6. El demo funcional actual (cómo funciona → analizar → guía → modelo → limitaciones).

## 2. Estructura y navegación

| # | Sección | `id` | Estado |
|---|---|---|---|
| 1 | Hero | `#inicio` | existente, ajustar bajada y acciones (ver §3.1) |
| 2 | Aviso académico | — | existente, sin cambios |
| 3 | El problema | `#problema` | **nueva** |
| 4 | La situación en Chile | `#chile` | **nueva** (subsección o sección propia) |
| 5 | Nuestra solución y propuesta de valor | `#propuesta` | **nueva** |
| 6 | Cómo funciona | `#como-funciona` | existente |
| 7 | Analizar ECG | `#analizar` | existente |
| 8 | Guía de resultados | `#guia` | existente |
| 9 | Modelo real del proyecto (F22) | `#modelo` | existente |
| 10 | Limitaciones y alcance | `#limitaciones` | existente |

- Nav del header: añadir «El problema» y «Propuesta» antes de «Cómo funciona».
- Las secciones nuevas son **HTML estático**: deben leerse sin JavaScript.

## 3. Contenido (copy propuesto, literal)

> El implementador adapta marcado/clases mínimamente (usar `seccion`, `tarjetas`,
> `tarjeta`, `muted`, `mini` existentes; CSS nuevo solo si falta) sin cambiar el sentido
> del texto. Cada cifra lleva su fuente enlazada (ver §4): usar un superíndice/enlace
> «[fuente]» al pie de la tarjeta o la lista, no interrumpir el texto.

### 3.1 Hero (ajuste menor)

- Bajada actual: conservar.
- Añadir acción terciaria o enlace destacado: «¿Por qué importa? → El problema»
  (`href="#problema"`).

### 3.2 Sección «El problema» (`#problema`)

**H2: Las arritmias pediátricas: un problema real y poco visible**

**Párrafo introductorio.** Una arritmia es una alteración de la frecuencia o el ritmo
cardíaco. En los niños, el sistema eléctrico del corazón madura con la edad y los valores
normales cambian entre un lactante y un adolescente, lo que complica la interpretación de
un ECG pediátrico incluso para personal entrenado. Las arritmias pediátricas pueden
aparecer con o sin cardiopatía congénita, y su frecuencia tiene una distribución bimodal,
con picos en lactantes y adolescentes [fuente 1].

**Bloque «Magnitud» (tarjetas con cifra grande + texto):**

- **55 de cada 100.000** consultas en urgencias infantiles corresponden a arritmias
  (incidencia estimada en población pediátrica general) [fuente 1].
- **1 de cada 250–1.000 niños** cursa con taquicardia supraventricular (TSV), la
  taquiarritmia más frecuente; la mitad tiene su primer episodio durante la lactancia
  [fuente 1].
- **1 de cada 2.000 personas** porta un síndrome de QT largo congénito, la enfermedad
  genética arritmogénica más común [fuente 1].
- **2–3%** de los niños tamizados con ECG escolar en Japón presenta anormalidades
  cardiovasculares o arritmias, evidencia de que hay enfermedad oculta que un ECG puede
  pesquisar [fuente 4].

**Bloque «Consecuencias»:**

- En lactantes, las taquiarritmias pueden presentarse de forma inespecífica: taquipnea,
  dificultad para alimentarse, vómitos y agitación; según la severidad, progresan a
  palidez, cianosis, insuficiencia cardíaca y shock [fuente 1].
- En escolares y adolescentes: molestias torácicas, palpitaciones, disnea y síncope, y
  raramente, la primera manifestación es una muerte súbita [fuente 1].
- La muerte súbita del niño y el adolescente es rara pero devastadora; en los registros
  poblacionales la mayoría de estos casos queda **sin causa aclarada incluso tras autopsia**
  [fuente 2].

**Bloque «Mortalidad»:**

- La mortalidad del síndrome de QT largo congénito **sintomático sin tratamiento** alcanza
  **21% en el año posterior al primer síncope y 50% a 10 años**; los pacientes tratados
  bajan a **0,05% anual**. Detectar a tiempo cambia el pronóstico [fuente 1].
- El QT largo se atribuye entre **3.000 y 4.000 muertes súbitas por año en Estados Unidos**
  [fuente 1].
- En el registro poblacional SDY (EE.UU.), la muerte súbita inesperada afecta a
  **120 de cada 100.000 nacidos vivos** en lactantes y **1,9 de cada 100.000 niños**
  (1–17 años) al año; internacionalmente, la muerte súbita cardíaca del joven se estima
  entre **0,3 y 9,1 por 100.000 persona-años**, un rango amplio que refleja subregistro y
  metodologías heterogéneas [fuente 2].
- Alrededor de **25%** de las muertes súbitas cardíacas en niños y adolescentes ocurre
  durante la práctica deportiva [fuente 3].

### 3.3 Sección «La situación en Chile» (`#chile`)

**H2: ¿Y en Chile?**

- **Contexto nacional:** las enfermedades del sistema circulatorio son la **primera causa
  de muerte en Chile**: explicaron el **23,1% de las defunciones en 2021** (31.729 de
  137.629), por sobre los tumores (21,4%); las cifras preliminares de 2024 (DEIS)
  confirman que siguen primero [fuente 6].
- **Vacío de tamizaje reconocido oficialmente:** el informe de vigilancia epidemiológica
  de MINSAL (2025) concluye que Chile «persiste la falta de métodos de tamizaje
  poblacional en la etapa preclínica, lo que limita las oportunidades de diagnóstico
  temprano, particularmente en enfermedades cardiovasculares» [fuente 6].
- Las cardiopatías congénitas afectan a **5–10 de cada 1.000 nacidos vivos** y representan
  cerca del **20% de las muertes neonatales y de lactantes**; su manejo está garantizado
  por el AUGE/GES en menores de 15 años [fuente 5].
- En la población infantil la mortalidad ha caído sostenidamente (análisis DEIS
  2017–2024), y las **malformaciones congénitas** —grupo que incluye las cardiopatías—
  son la **principal causa de muerte en menores de 1 año**; en los niños mayores ganan
  peso el cáncer y las enfermedades neurológicas [fuente 7].
- La evidencia nacional de muerte súbita cardiovascular es escasa: la revisión de
  certificados de defunción 2000–2010 identificó **1.131 muertes súbitas cardiovasculares**
  en una década; menos del 20% correspondió a personas de 15 años o menos, y en ese grupo
  etario 2% de las defunciones tuvo diagnósticos compatibles; **no existen estudios
  nacionales que cuantifiquen la muerte súbita vinculada al deporte** [fuente 4].
- Las sociedades científicas chilenas (SOCHIPE, SOCHICAR, SOCHMEDEP) recomiendan la
  evaluación preparticipativa cardiovascular y destacan dos datos clave: la historia y el
  examen físico solos detectan solo ~**20%** de los trastornos con riesgo de muerte súbita,
  mientras que **~60%** de esos trastornos presenta anomalías detectables en un **ECG de
  12 derivaciones** [fuente 4].
- Conclusión de la sección (texto destacado): en Chile la detección depende de la
  interpretación del ECG, recurso concentrado en centros especializados. Aumentar la
  capacidad de triaje ECG pediátrico en la red asistencial y en la formación clínica es
  una necesidad concreta que este proyecto busca aportar a explorar.

### 3.4 Sección «Nuestra solución y propuesta de valor» (`#propuesta`)

**H2: Nuestra solución: análisis asistido de ECG pediátrico**

**Párrafo.** Este proyecto desarrolla software de procesamiento digital de señales (PDS) y
clasificación de ritmo cardíaco pediátrico sobre ECG de 12 derivaciones, entrenado y
evaluado con el corpus público **ZZU pECG** (niños hospitalizados de 0 a 14 años,
10 s @ 500 Hz, WFDB). El portal carga un registro WFDB, analiza un tramo de 10 segundos y
entrega una **sugerencia de ritmo con nivel de certeza y advertencias**, para apoyar —no
reemplazar— la evaluación del profesional de la salud.

**Propuesta de valor social (tarjetas):**

- **Detección más temprana, donde importa.** Un triaje ECG asistido ayuda a escalar antes
  los casos con sospecha de taquiarritmia o canalopatía; en el QT largo congénito, el
  tratamiento oportuno reduce la mortalidad desde 21% en el primer año post-síncope a
  0,05% anual [fuente 1].
- **Equidad territorial.** El software corre en hardware común y el demo funciona íntegro
  en el navegador: acerca una primera lectura asistida de ECG a hospitales y consultas
  lejos de los centros con cardiólogo pediátrico.
- **Privacidad del menor.** En la demo, la señal del paciente **no sale del equipo**:
  todo el análisis ocurre localmente en el navegador; nada se envía a servidores.
- **Formación y docencia.** Herramienta educativa para estudiantes y residentes: ECG
  pediátrico con criterios por edad, casos demo sintéticos (sinusal, SVT, VT, marcapasos)
  y guía de interpretación de resultados.
- **Ciencia abierta y reproducible.** Pipeline documentado paso a paso, código versionado
  y corpus público ZZU pECG (CC BY 4.0) como base de entrenamiento y evaluación.
- **Alcance honesto.** Es una demostración académica, no un dispositivo médico ni un
  diagnóstico: cada salida reitera que la decisión clínica corresponde al profesional.

**Nota de cierre** (una línea, estilo `mini`): el modelo calibrado del proyecto (F22) se
ejecuta fuera de este navegador; esta web usa un clasificador heurístico de demostración
(ver «Modelo real» y «Limitaciones»).

## 4. Cifras y fuentes (obligatorias, verificadas)

Reglas: **ninguna cifra sin su fuente**; en la página, las fuentes se citan como enlaces
numerados al pie de la sección (lista `mini`) o superíndices; no inventar ni redondear.

| # | Dato | Valor | Fuente |
|---|---|---|---|
| 1 | Incidencia arritmias en urgencias pediátricas | 55,1 por 100.000 consultas; distribución bimodal (lactantes/adolescentes) | Cáceres D, Mena M, Eltit R. *Arritmias en población pediátrica general: una revisión de la literatura.* Rev Chilena de Anestesia 2024;53(2):135–150. DOI [10.25237/revchilanestv53n2-09](https://revistachilenadeanestesia.cl/revchilanestv53n2-09/) |
| 1 | Frecuencia relativa en población pediátrica general | taquicardia sinusal 50%, TSV 13%, bradicardia 6%, contracciones prematuras suprav./ventriculares | ídem |
| 1 | TSV | incidencia 1:250–1:1.000; 50% primer episodio en lactancia (90% resolución espontánea); diagnóstico después del año: solo 15% resolución; asociación a cardiopatía congénita 9–32% | ídem |
| 1 | QT largo congénito | enfermedad genética arritmogénica más común; prevalencia 1:2.000; incidencia descrita 1:10.000–1:15.000; 3.000–4.000 muertes súbitas/año en EE.UU.; mortalidad sin tratamiento (sintomático) 21% al año / 50% a 10 años; tratado 0,05% anual | ídem |
| 1 | Consecuencias por edad | lactantes: taquipnea, intolerancia alimentaria, IC/shock; escolares: palpitaciones, síncope; rara vez muerte súbita como presentación | ídem |
| 2 | Muerte súbita del joven (EE.UU.) | registro SDY 2015–2016: 120/100.000 nacidos vivos (lactantes), 1,9/100.000 niños 1–17 años; causa cardíaca explicada 2,7 y 0,3; mayoría de casos sin causa aclarada; rango internacional SCDY 0,3–9,1/100.000 persona-años | Burns KM et al. *Epidemiology of Sudden Death in a Population-Based Study of Infants and Children.* J Pediatr X 2020;2:100023. DOI [10.1016/j.ympdx.2020.100023](https://pmc.ncbi.nlm.nih.gov/articles/PMC7394394/) |
| 3 | Muerte súbita y deporte | ~25% de los casos ocurren durante el deporte; mayoría con cardiopatía subyacente (miocardiopatía hipertrófica y anomalías coronarias las más comunes) | Behr ER et al. *Sudden cardiac death in children and adolescents (excluding Sudden Infant Death Syndrome).* [PMC3017912](https://pmc.ncbi.nlm.nih.gov/articles/PMC3017912/) |
| 4 | Chile: muerte súbita cardiovascular | 1.131 MSCV en certificados de defunción 2000–2010; <20% en ≤15 años; 2% en ese grupo con diagnósticos compatibles; 75% varones; sin estudios de MS vinculada al deporte; historia+examen físico sensibilidad ~20%; ~60% de trastornos asociados a MS con anomalías ECG detectables; tamizaje escolar japonés detecta 2–3% | González F et al. *Evaluación Preparticipativa Cardiovascular Pediátrica* (SOCHIPE/SOCHMEDEP/SOCHICAR). Rev Chil Pediatr 2018;89(4). DOI [10.4067/S0370-41062018005000607](https://www.scielo.cl/scielo.php?pid=S0370-41062018005000607&script=sci_arttext) |
| 5 | Chile: cardiopatías congénitas | 5–10 por 1.000 nacidos vivos; ~20% de muertes neonatales y de lactantes; GES operables <15 años | MINSAL/DIPRECE. *Guía Clínica Cardiopatías congénitas operables en menores de 15 años*, [Descripción y Epidemiología](https://diprece.minsal.cl/le-informamos/auge/acceso-guias-clinicas/guias-clinicas-desarrolladas-utilizando-manual-metodologico/cardiopatias-congenitas-en-menores-de-15-anos/descripcion-y-epidemiologia) |
| 6 | Chile: ECV primera causa de muerte y vacío de tamizaje | sistema circulatorio: 23,1% de defunciones en 2021 (31.729 de 137.629); tumores 21,4%; el informe concluye que «persiste la falta de métodos de tamizaje poblacional en la etapa preclínica, lo que limita las oportunidades de diagnóstico temprano, particularmente en enfermedades cardiovasculares» | MINSAL, Depto. Epidemiología. *Informe de Vigilancia Epidemiológica de Enfermedades Cardiovasculares y Metabólicas en Chile: Incidencia, Mortalidad y Sobrevida.* 2025 (datos DEIS). [PDF oficial](https://epi.minsal.cl/wp-content/uploads/2026/09/Informe_de_vigilancia_cardiovascular_y_metabolica_2025.pdf) |
| 7 | Chile: mortalidad pediátrica 2017–2024 | análisis DEIS: mortalidad pediátrica disminuida de forma sostenida; en <1 año las principales causas son malformaciones congénitas y prematuridad extrema; en niños mayores, cáncer y enfermedades neurológicas | Gallegos B, Henríquez J, Ortega E, Aravena J, Figueroa G. *Principales causas de mortalidad no traumática en menores de 16 años en Chile, 2017–2024.* Rev ANACEM 2025;19(2). DOI [10.70536/RevANACEM/V19N2-202546](https://revanacem.cl/index.php/Revista/article/view/46) |
| 8 | Chile: defunciones 2024 (preliminar) | 125.300 decesos preliminares; enfermedades del sistema circulatorio se mantienen como primera causa, seguidas de tumores y respiratorias | DEIS, datos abiertos (análisis de [24horas/Data IE](https://www.24horas.cl/informe-especial/data/estas-son-las-10-principales-causas-de-muerte-en-chile-durante-2024-)); citar preferentemente como «cifras preliminares DEIS 2024» |

Notas de honestidad para el copy:

- «55 por 100.000» es por **consultas de urgencia infantil**, no prevalencia poblacional:
  redactarlo siempre con esa precisión.
- El 1,9/100.000 del registro SDY incluye muertes súbitas **explicadas y no explicadas**
  (no solo cardíacas); el copy ya lo aclara como «muerte súbita inesperada».
- Las cifras de QT largo y mortalidad provienen de la revisión chilena de 2024, que cita a
  su vez fuentes primarias: mantener la atribución «según la revisión chilena de 2024»
  implícita citando la fuente 1, nunca presentarlas como datos chilenos.
- Antigüedad de los datos chilenos (etiquetar en el copy cuando aporte): contexto ECV
  nacional = dato 2021 de un informe oficial 2025; MSCV/Donoso = serie 2000–2010 (el
  statement lo señala como lo último disponible); defunciones 2024 = **preliminar**;
  mortalidad pediátrica = serie 2017–2024. No mezclar años en una misma cifra.

## 5. Restricciones técnicas

1. `web/` **sin dependencias ni build**: HTML/CSS/JS puro; nada de frameworks, CDNs ni
   fuentes externas.
2. No modificar `js/wfdb.js` ni `js/app.js`; no cambiar los registros `web/demo/`.
3. Secciones nuevas: HTML estático legible sin JavaScript; sin `content` generado por JS.
4. Mantener visible el aviso académico («no es un dispositivo médico») y reproducir la
   advertencia en `#propuesta` (ver copy).
5. Accesibilidad: jerarquía `h2` → `h3` correcta, textos alternativos, contraste, focus
   visible; responsive verificado a 375 px y 1280 px.
6. Reusar clases existentes (`seccion`, `tarjetas`/`tarjeta`, `muted`, `mini`, `etiqueta`);
   agregar CSS nuevo solo para cifras destacadas (estilo «stat»), dentro de `styles.css`
   con las variables ya definidas.
7. Actualizar `<meta name="description">` para incluir el carácter informativo
   (problemática, Chile, propuesta de valor).
8. Español; tono sobrio y factual; sin promesas clínicas.

## 6. Criterios de aceptación

1. Servido con `python -m http.server 8000 --directory web`, la página muestra en orden:
   hero → aviso → El problema → Chile → Solución/propuesta → Cómo funciona → Analizar →
   Guía → Modelo → Limitaciones; la nav enlaza todas las secciones nuevas.
2. Toda cifra numérica de las secciones nuevas tiene fuente enlazada visible.
3. Sin regresión funcional: los 4 casos demo cargan y el análisis devuelve resultado.
4. `git diff --check` sin errores de whitespace.
5. Verificación visual en navegador (captura a 1280 px y 375 px) incluida en la
   verificación del agente.
