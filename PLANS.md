# Publicación segura de la rama `entrega-final-f22`

## Goal

Publicar únicamente el código, configuración, documentación y evidencia resumida
necesarios para reproducir F16–F23, evitando datasets, checkpoints, corridas y
artefactos binarios pesados.

## Scope

- Incluir cambios de código, notebooks, dependencias, ADR, runbooks e informes.
- Incluir solo JSON/CSV pequeños que documenten preflight, normalización y gates.
- Excluir shards, `runs/`, checkpoints, datos derivados, temporales y entregables.

## Assumptions

- La rama de trabajo es `entrega-final-f22`.
- Los resultados extensos permanecen fuera de Git y están resumidos en `docs/`.
- Codeberg debe conceder permiso de escritura a `CarlosGebard` antes del push.

## Steps

1. Ampliar `.gitignore` para prevenir inclusiones accidentales.
2. Validar Python, notebooks y scripts shell.
3. Preparar un staging explícito y revisar tamaño, contenido y secretos.
4. Crear un commit local y publicarlo cuando Codeberg permita crear la rama.

## Validation

- `git diff --check`
- `python -m py_compile` sobre los scripts modificados y nuevos.
- `jq empty` sobre ambos notebooks operativos.
- `bash -n` sobre scripts de `ops/`.
- Revisión de `git diff --cached --stat` y tamaño de objetos antes del commit.

## Risks

- Un patrón de staging amplio podría incluir datasets o checkpoints; se usará una
  lista explícita de rutas.
- El permiso remoto aún no permite crear la rama y bloquea solamente el push.

---

# Presentación final consolidada al 17 de noviembre de 2026

## Goal

Consolidar `Avances_v5.pptx` y `Presentacion-Final-Resultados-Claros-v3.pptx`
en una única presentación de avance, actualizada al 17 de noviembre de 2026,
manteniendo el foco general del proyecto y mostrando el resultado técnico F22.

## Scope

- Conservar el lenguaje visual de las dos presentaciones fuente.
- Ubicar el estado del proyecto como segunda diapositiva.
- Actualizar portada, fecha de corte, cronograma e hitos al 17 de noviembre.
- Integrar los resultados y conclusiones ya documentados, sin incorporar datos
  o afirmaciones nuevas.
- Generar un nuevo archivo PPTX sin sobrescribir los originales.

## Assumptions

- La fecha de presentación y corte corresponde al 17 de noviembre de 2026.
- F22 seed 14 sigue siendo el candidato seleccionado y el test continúa reservado.
- La presentación se utiliza como informe de avance, por lo que debe equilibrar
  gestión del proyecto, alcance técnico, resultados y pendientes.

## Steps

1. Revisar visualmente y extraer el contenido de las ocho diapositivas fuente.
2. Reordenar la narrativa: portada, estado, alcance, cronograma, hitos,
   resultados y cierre.
3. Actualizar fechas, estado e hitos usando únicamente información de las fuentes.
4. Exportar el PPTX consolidado y renderizar todas las diapositivas.
5. Corregir cualquier problema de legibilidad, solapamiento o consistencia.

## Validation

- Importación exitosa del PPTX final con `artifact-tool`.
- Inspección de todas las diapositivas y ausencia de desbordes detectables.
- Render individual y revisión visual a tamaño completo de cada diapositiva.
- Ejecución del finalizador de presentaciones y verificación del archivo de salida.

## Risks

- El cronograma original estaba cortado al 21 de octubre y requiere sintetizar
  el avance posterior sin inventar fechas no presentes en las fuentes.
- Los resultados F22 son de una semilla; la presentación debe conservar la
  advertencia sobre estabilidad y test pendiente.

---

# Migración operativa de DL a Vast.ai

## Goal

Reemplazar los notebooks operativos de Google Colab por un flujo reproducible
para entrenar F16 en una instancia Vast.ai mediante SSH directo y shards
cargados manualmente.

## Scope

- Actualizar los notebooks F15/F16 para eliminar Tailscale y Google Drive.
- Añadir una guía operativa de Vast.ai y alinear README y plan DL.
- Mantener el formato de shards, el split por paciente y el test sin tocar.

## Assumptions

- La instancia usa la plantilla PyTorch de Vast.ai y recibe los siete shards
  en `results/dl/shards/`.
- El dato crudo ZZU no se transfiere a la instancia para F16.
- Los checkpoints se descargan antes de destruir la instancia.

## Steps

1. Sustituir las celdas Colab/Drive/Tailscale por preflight, instalación mínima
   y comandos de entrenamiento compatibles con Vast.ai.
2. Documentar el layout, carga vía SCP, verificación, monitoreo y descarga de
   resultados en un runbook.
3. Actualizar las referencias de README y plan DL al nuevo entorno operativo.
4. Validar JSON de notebooks, ausencia de referencias a Colab/Drive/Tailscale
   en F15/F16 y consistencia de los comandos con el script de entrenamiento.

## Validation

- `jq empty notebooks/05_dl_colab.ipynb notebooks/06_dl_baseline_colab.ipynb`
- `rg -n -i 'tailscale|google\.colab|drive\.mount|/content' notebooks/05_dl_colab.ipynb notebooks/06_dl_baseline_colab.ipynb`
- Revisión estática de `python scripts/entrenar_baseline_dl.py --help`.

## Risks

- El almacenamiento de contenedor actual no sobrevive a destruir/reciclar la
  instancia; los resultados deben descargarse antes.
- El dataset de 6,6 GB cabe en 16 GB, pero no junto al dato crudo ZZU.

---

# Diagnóstico y ajuste F17 del baseline DL

## Goal

Documentar el resultado F16 y ejecutar un único experimento F17 dirigido al
desbalance de clases, conservando el mismo split por paciente y la evaluación
de validación.

## Scope

- Añadir muestreo balanceado opcional y parada temprana al script de F16.
- Ejecutar F17 con los siete shards ya verificados en Vast.ai.
- Escribir un informe reproducible con métricas, interpretación y siguiente paso.

## Assumptions

- La clase `Paced` tiene 86 ventanas train y 8 val; el F16 produjo F1=0 en
  dicha clase y su mejor F1 macro fue 0,4764.
- No se toca el conjunto test ni se cambian los shards, normalización o split.

## Steps

1. Incorporar un `WeightedRandomSampler` exclusivo para train; si se activa,
   usar pérdida no ponderada para no duplicar el balanceo.
2. Incorporar parada temprana opcional basada solo en F1 macro de validación.
3. Ejecutar F17 en Vast.ai con muestreo balanceado, LR menor y paciencia.
4. Publicar historial y gate F17 junto con el informe de resultados.

## Validation

- `python -m py_compile scripts/entrenar_baseline_dl.py`
- `python scripts/entrenar_baseline_dl.py --help`
- Confirmar que F17 conserva el número de ventanas y usa solo train para el sampler.
- Revisar `historial.json` y `gate_f16.txt`/gate del experimento al finalizar.

## Risks

- Ocho ventanas de validación `Paced` producen una estimación de F1 inestable.
- El muestreo puede sobreajustar esa clase; se acepta solo si mejora F1 macro
  sin degradar materialmente las demás clases.

## Outcome

F17 terminó por parada temprana en la época 14. Su mejor F1 macro de
validación fue 0,4587 (época 9), inferior a F16 (0,4764) y al gate (0,518).
El muestreo balanceado mantuvo F1 `Paced` en 0 y degradó VT; no se usó test ni
se reemplazó el checkpoint candidato F16.

---

# F18 — datos sintéticos conservadores para Paced y despliegue reproducible

## Goal

Preparar un experimento F18 reproducible que aumente la diversidad efectiva de
`Paced` sin contaminar validación/test ni repetir el balanceo extremo de F17.

## Scope

- Auditar soporte, pacientes y señales indirectas de estimulación en `Paced`.
- Añadir augmentation online exclusivo de train y muestreo moderado por paciente.
- Corregir selección de checkpoint y guardar predicciones/matriz de validación.
- Añadir preflight y lanzador idempotente para tres semillas en Vast.ai.
- Actualizar el runbook operativo; no evaluar test.

## Assumptions

- Los shards actuales contienen señal filtrada a 40 Hz; no permiten sintetizar
  espículas fisiológicas de alta frecuencia de forma fiel.
- El dato ZZU crudo no está disponible en el workspace actual.
- F16/F17 deben seguir siendo reproducibles con los valores por defecto.

## Steps

1. Generar una auditoría train/val de `Paced` por paciente y marcar casos sin
   espículas o con soporte insuficiente.
2. Incorporar transformaciones conservadoras de señal, enmascaramiento correcto
   de derivaciones ausentes y un sampler con fracción `Paced` configurable.
3. Separar el mejor checkpoint observado del umbral usado por early stopping y
   exportar artefactos diagnósticos de validación.
4. Validar shards/configuración antes de reservar GPU y automatizar tres semillas.
5. Documentar transferencia, ejecución, rescate y criterio de detención.

## Validation

- `python -m py_compile scripts/auditar_paced.py scripts/entrenar_baseline_dl.py ops/checks/preflight_f18.py`
- `uv run python scripts/auditar_paced.py --salida /tmp/auditoria-paced`
- `uv run python ops/checks/preflight_f18.py --dir-shards shards`
- `bash -n ops/scripts/ejecutar_f18.sh`
- En Vast.ai: humo GPU y tres semillas; revisar `resumen.json`,
  `predicciones_val.csv` y `matriz_confusion_val.csv` sin abrir test.

## Risks

- La augmentation aumenta variación, pero no crea pacientes independientes.
- Validación contiene un solo paciente `Paced`; su F1 sigue siendo inestable.
- Una fracción sintética excesiva puede crear atajos o degradar otras clases.
- La síntesis de espículas queda fuera hasta recuperar crudo y validar etiquetas.

## Outcome

Implementación y ejecución terminadas. El preflight verificó 58.178 ventanas y
siete shards; el sampler produjo una fracción `Paced` esperada de 0,03 con igual
masa por paciente. La auditoría train/val marcó P02746, P04447 y P05649 para
revisión. Tres semillas alcanzaron F1 macro 0,4594 / 0,4496 / 0,4658; `Paced`
permaneció en 0 en las tres. F18 no reemplaza F16 y test continuó sin usarse.
Los artefactos fueron descargados y sus checkpoints verificados por SHA-256
antes de detener la instancia Vast.ai.

---

# F19 — adquisición y auditoría de datasets complementarios para Paced

## Goal

Construir un inventario reproducible de señales `Paced` externas y determinar
si PTB-XL y Leipzig sirven para preentrenar un detector auxiliar sin alterar el
corpus, las particiones ni la evaluación pediátrica ZZU.

## Scope

- Descargar metadatos y únicamente las señales candidatas necesarias.
- Verificar checksums, formato WFDB, derivaciones, frecuencia y etiquetas.
- Generar un manifiesto común por paciente/registro y un informe de match.
- Mantener los datos externos fuera de git y separados de los shards ZZU.
- No entrenar, no evaluar test y no cambiar todavía la arquitectura del modelo.

## Assumptions

- PTB-XL aporta señales `PACE` adultas útiles solo para preentrenamiento.
- Leipzig aporta anotaciones manuales por latido, pero incluye estimulación de
  estudios electrofisiológicos y una banda almacenada de 0,05–100 Hz.
- El dato crudo ZZU sigue ausente del workspace.
- La incorporación futura al entrenamiento requerirá una decisión de
  arquitectura documentada y una ablación separada.

## Steps

1. Implementar un preparador idempotente que descargue índices oficiales,
   filtre PTB-XL por `PACE` y obtenga Leipzig con sus anotaciones.
2. Validar SHA-256 oficiales y contratos WFDB sin cargar todas las señales en
   memoria.
3. Construir manifiestos con origen, paciente, edad, frecuencia, derivaciones,
   duración, etiqueta y limitaciones de dominio.
4. Ejecutar un baseline externo agrupado por paciente y limitado a variables
   de alta frecuencia, para comprobar si PTB-XL aporta señal separable.
5. Publicar conteos, fallos y recomendación para la siguiente ablación.

## Validation

- `python -m py_compile scripts/preparar_f19_datasets.py ops/checks/validar_f19_datasets.py`
- `uv run python scripts/preparar_f19_datasets.py --solo-metadata`
- `uv run python ops/checks/validar_f19_datasets.py --raiz data/f19_paced`
- `uv run python scripts/evaluar_f19_paced.py`
- Ejecución completa selectiva; checksums oficiales y manifiestos sin pacientes
  compartidos con ZZU.

## Risks

- Adultos PTB-XL pueden inducir atajos de edad/dispositivo; nunca entran en la
  validación pediátrica.
- `PACE` a nivel de registro puede incluir estimulación no visible en los 10 s.
- Leipzig no representa necesariamente un marcapasos implantado y su LP de
  100 Hz limita el análisis de espículas.
- Descargas interrumpidas deben reanudarse sin corromper artefactos existentes.

## Outcome

F19 descargó y verificó 588 señales PTB-XL (294 `PACE`, 294 controles) y 34
registros Leipzig con pacing. Leipzig aporta 25 pacientes pediátricos con
11.685 latidos estimulados. El baseline HF agrupado por paciente logró F1
0,9757 en PTB-XL; la transferencia ciega a Leipzig logró F1 0,8427 global y
0,7932 pediátrico (Se 0,70, Sp 0,947). El test ZZU permaneció sin consultar.
La siguiente decisión queda condicionada a recuperar el crudo ZZU y comprobar
el sidecar HF en desarrollo antes de modificar F16 o reservar GPU.

---

# F20 — rama auxiliar de alta frecuencia para Paced

## Goal

Implementar y validar una arquitectura de dos ramas que fusione la morfología
ECG de F16 con un sidecar de alta frecuencia generado desde el crudo ZZU,
dejando una corrida de screening reproducible lista para Vast.ai.

## Scope

- Recuperar y verificar ZZU pECG v1 desde Figshare.
- Factorizar el extractor HF validado en F19 y generar sidecar solo train/val.
- Añadir una rama MLP opcional a la ResNet sin cambiar el comportamiento F16.
- Añadir preflight, gate y lanzador F20 de una semilla.
- Documentar la decisión de arquitectura, operación y resultados de humo.
- No consultar ni generar features del test ZZU.

## Assumptions

- La señal cruda ZZU conserva 500 Hz y suficiente banda para las variables HF.
- El sidecar se alinea estrictamente por `window_id` y se normaliza solo con
  train.
- F20 es una ablación: F16 sigue siendo el checkpoint candidato hasta superar
  gates de macro-F1, Paced y VT.

## Steps

1. Descargar, verificar MD5 y extraer ZZU pECG de forma reanudable.
2. Mover el extractor HF a `ecg_pipeline` y conservar la regresión F19.
3. Generar sidecar train/val + estadísticos train-only, sin filas test.
4. Fusionar ResNet y MLP HF de forma opcional y probar compatibilidad F16.
5. Añadir preflight/gate/lanzador; ejecutar humo local y dejar paquete Vast.ai.
6. Publicar visualización, ADR, runbook y evidencia de validación.

## Validation

- `python -m py_compile` sobre scripts F20 y entrenamiento.
- MD5 oficial de seis archivos ZZU y 14.190 cabeceras/datos extraídos.
- Regresión F19 con métricas previamente guardadas.
- Preflight F20: cobertura exacta train/val, cero test, finitud y stats train.
- Humo CPU con sidecar de fixture y humo GPU antes de screening.
- `bash -n ops/scripts/descargar_zzu.sh ops/scripts/ejecutar_f20.sh`.

## Risks

- `Pacing rhythm` sigue siendo etiqueta de registro y puede no indicar pacing
  activo en cada ventana.
- El sidecar podría aprender dispositivo/calidad en lugar de fisiología; se
  mantiene transferencia externa y ablación contra F16.
- Un único paciente Paced en val hace inestable el gate; screening no autoriza
  test ni reemplazo del checkpoint.

## Outcome

Implementación terminada. ZZU pECG fue recuperado con 6/6 MD5 y 14.190 pares
WFDB. El sidecar train/val contiene 52.607 ventanas, cero test y normalización
train-only; preflight VERDE. La rama opcional ResNet+MLP HF, el gate y el
lanzador Vast.ai quedaron listos. Sin embargo, el screening HF train→val
detectó 0/8 ventanas `Paced` (F1 0, AUC 0,287): P05649 tiene energía HF de
no-Paced y cero espículas, frente a mediana de dos en Paced train. El lanzador
se detiene con código 2 antes de GPU. Se requiere revisión clínica/redefinición
de P05649 antes de autorizar la simulación; test no fue consultado.

Se adoptó posteriormente la primera definición acordada: `Paced` con evidencia
de pacing activo. Sin alterar el split original ni test, P05649 quedó como
`holdout_uncertain` y P05281 (10 ventanas exclusivamente `Paced`) pasó de train
a val. El preflight del split derivado quedó OK y el screening HF quedó VERDE:
sensibilidad 0,60, especificidad 0,9966 y AUC 0,9585. Esto habilita el humo GPU
y una corrida inicial de semilla 14; no habilita todavía evaluación sobre test.

La corrida GPU semilla 14 terminó con parada temprana en época 24 y mejor
checkpoint en época 16. Obtuvo F1 macro 0,5927 y F1 `Paced` 0,6667, pero F1 VT
0,3797 quedó bajo el gate 0,4115. El gate conjunto quedó ROJO, se omitieron las
semillas 42/73 y test permaneció sin consultar. Los artefactos fueron rescatados
en `runs/f20_hf_fusion/` con hashes coincidentes y la instancia se apagó.

---

# F21 — residual HF exclusivo para Paced y regularización VT

## Goal

Conservar la ganancia F20 en `Paced` activo y recuperar F1 VT ≥0,4115,
impidiendo que las features HF alteren directamente los logits de las otras
cuatro clases.

## Scope

- Añadir una fusión opcional donde la rama HF corrige solo el logit `Paced`.
- Permitir augmentation selectiva por clase y aplicarla únicamente a VT.
- Crear lanzador, supervisor, gate y runbook F21 independientes.
- Ejecutar humo GPU y una semilla 14 sobre el split activo F20.
- No modificar shards, sidecar, split histórico/activo, test ni gates.

## Assumptions

- Parte de la caída VT de F20 proviene de permitir que el sidecar HF modifique
  todos los logits mediante una cabeza concatenada.
- La morfología sigue siendo la señal primaria para VT; HF debe actuar como
  evidencia residual específica de pacing.
- Augmentation solo VT y scheduler coseno pueden reducir su sobreajuste sin
  degradar las espículas de `Paced`.

## Steps

1. Añadir `paced_logit` como modo de fusión HF compatible con `concat` F20.
2. Añadir filtro opcional de clases para la augmentation de train.
3. Crear checks y lanzador F21: LR 2e-4, cosine, VT-only, paciencia 10.
4. Documentar arquitectura y operación; validar sintaxis y compatibilidad.
5. Ejecutar preflights, humo CUDA y seed 14; confirmar semillas solo si el gate
   macro/Paced/VT queda VERDE.

## Validation

- `python -m py_compile` de entrenamiento, checks y scripts F21.
- Prueba de forward: `concat`, `paced_logit` y baseline sin sidecar.
- Regresión de claves del modo `concat` F20.
- `bash -n` de lanzador y wrapper supervisor.
- Preflight F18/F20, screening HF activo y cero consultas a test.
- Gate: macro ≥0,4664, Paced >0 y VT ≥0,4115.

## Risks

- Restringir HF puede reducir F1 `Paced` si la interacción con morfología era
  necesaria; el gate evita confirmación en ese caso.
- La validación tiene un solo paciente `Paced` y 48 ventanas VT; no autoriza
  conclusiones clínicas ni evaluación de test.
- Augmentation VT puede elevar recall a costa de precisión; se controla con F1
  de clase y macro-F1 conjunta.

## Outcome

F21 completó humo GPU y semilla 14 en RTX 5070 Ti. La validación arquitectónica
fue verde y el mejor checkpoint (época 11; parada en 21) obtuvo macro-F1 0,5881,
Paced 0,6364 y VT 0,3462. El gate quedó ROJO por VT; no se ejecutaron semillas
42/73 ni test. VT aumentó TP de 15 a 18, pero los FP crecieron de 16 a 38
(20 Sinusal, 18 Otro), confirmando sobrecompensación de precisión por
augmentation VT + pesos inversos. Artefactos rescatados con hashes coincidentes
en `runs/f21_paced_logit_vt/`; instancia detenida.

---

# F22 — cascada morfología activa + gate Paced F20

## Goal

Combinar un clasificador morfológico entrenado desde cero sobre el split activo
con el gate `Paced` de alta precisión de F20, para recuperar VT ≥0,4115 sin
perder detección de pacing activo.

## Scope

- Entrenar el baseline morfológico F16 sobre `splits_f20_active.csv`, sin HF.
- En inferencia, elegir Sinusal/SVT/VT/Otro por probabilidades morfológicas.
- Reemplazar por `Paced` únicamente donde F20 predijo `Paced`.
- Evaluar la cascada sobre val activa y aplicar el gate macro/Paced/VT.
- No reutilizar F16 antiguo, modificar F20, consultar test ni calibrar umbrales
  sobre val.

## Assumptions

- El gate F20 obtuvo 7/10 TP `Paced`, pero también 4 VT→Paced; por ello la
  cascada da prioridad a una predicción morfológica VT sobre el gate.
- El baseline morfológico puede recuperar el comportamiento VT de F16 sin la
  interferencia de HF.
- El checkpoint F16 antiguo no es válido para esta evaluación: P05281 estaba
  en su train y ahora pertenece a val activa.

## Steps

1. Implementar evaluación de cascada con alineación estricta por `window_id`.
2. Añadir gate con veto VT, predicciones y matriz reproducibles, sin test.
3. Crear lanzador/supervisor F22 con preflight, humo y una semilla 14.
4. Documentar ADR/runbook y validar sintaxis/contratos localmente.
5. Ejecutar GPU; confirmar semillas 42/73 solo si la cascada queda VERDE.

## Validation

- Prueba unitaria sintética de prioridad del gate y exclusión de `Paced`
  morfológico.
- Cobertura e igualdad de etiquetas por `window_id` entre ambos especialistas.
- `python -m py_compile`, `bash -n` y `git diff --check`.
- Preflights F18/F20 y cero consultas a test.
- Gate: macro ≥0,4664, Paced >0 y VT ≥0,4115.

## Risks

- La selección F20 y la evaluación F22 comparten val; los resultados siguen
  siendo de desarrollo y requieren confirmación multisemilla antes de test.
- Un gate de alta precisión puede omitir ventanas `Paced`; se acepta mientras
  F1 sea positivo y no degrade las otras clases.
- Dos checkpoints aumentan costo de despliegue; el beneficio debe justificarlo.

## Outcome

F22 ejecutó semillas 14/42/73. La seed 14 fue la primera corrida totalmente
VERDE (macro 0,6125; Paced 0,7368; VT 0,4857); seeds 42 y 73 conservaron macro
y Paced pero VT quedó en 0,4000 y 0,3556. Los tres artefactos fueron rescatados
con SHA-256 coincidente y test no fue consultado. La cascada es prometedora,
pero VT continúa sensible a la inicialización.

---

# F23 — especialista binario VT sobre cascada F22

## Goal

Estabilizar la detección VT entre semillas F22 mediante un especialista binario
entrenado y calibrado exclusivamente dentro de train, sin degradar `Paced` ni
consultar test.

## Scope

- Entrenar ResNet binaria `VT vs resto` desde cero sobre shards existentes.
- Reservar 20% de pacientes train para calibración interna estratificada.
- Elegir threshold con precisión mínima dentro de calibración train-only.
- Aplicar prioridad VT sobre las predicciones de cascada F22 de tres semillas.
- Crear checks, lanzador, supervisor, ADR y runbook F23.
- No modificar F20/F22, splits, sidecar, gates ni test.

## Assumptions

- Un objetivo binario reduce la competencia multiclase responsable de la
  varianza VT observada entre seeds.
- Un umbral train-only limita los falsos positivos sin sobreajustar val fija.
- El soporte de pacientes VT en train permite una partición interna agrupada.

## Steps

1. Crear split interno determinista por paciente con auditoría de solapamiento.
2. Implementar entrenamiento binario, calibración de threshold y predicción val.
3. Implementar fusión VT-prioritaria sobre cada seed F22.
4. Añadir pruebas sintéticas, launcher y supervisor idempotentes.
5. Validar localmente; solo entonces solicitar encendido de GPU.
6. Ejecutar especialista una vez y evaluar F23 sobre seeds 14/42/73.

## Validation

- Cero pacientes compartidos entre fit/calibración y cero test consultado.
- Ambas particiones internas contienen VT y no-VT.
- Threshold derivado solo de calibración interna con métricas guardadas.
- Prueba de prioridad VT/Paced y alineación exacta por `window_id`.
- `python -m py_compile`, `bash -n`, preflight y humo GPU.
- Gate por seed: macro ≥0,4664, Paced >0 y VT ≥0,4115.

## Risks

- Una sola calibración interna puede mantener varianza; se documenta antes de
  considerar ensamble o CV más costosa.
- Prioridad VT puede convertir falsos positivos de otras clases; la precisión
  mínima y el gate macro limitan el daño.
- El especialista añade un tercer checkpoint al despliegue.

## Outcome

F23 completó entrenamiento y evaluación sobre las tres seeds F22. El
especialista seleccionó la época 6 y umbral 0,9961 dentro de calibración
train-only (F1 0,7152, precisión 0,8676, sensibilidad 0,6082), pero en la
validación fija cayó a F1 0,3051 y sensibilidad 0,1875. Sus 9 TP ya eran
aciertos VT de F22 y sus 2 FP eran SVT previamente correctos, de modo que no
aportó ningún rescate complementario.

El resumen quedó ROJO: solo seed 14 fue verde; las medias fueron macro 0,5938,
Paced 0,7135 y VT 0,4032. F23 se descarta y F22 seed 14 permanece como candidato
final (macro 0,6125, Paced 0,7368, VT 0,4857). Test no fue consultado. Los
artefactos se rescataron y verificaron antes de detener la instancia.

# Presentación final — reconstrucción narrativa y visual

## Goal

Transformar `Presentacion-Final.pptx` en una defensa final centrada en el
problema resuelto, la evidencia F16–F23 y las limitaciones vigentes, conservando
su sistema visual. La actual última lámina pasa a la posición 2 y se reescribe
como estado ejecutivo y explicación de las correcciones realizadas.

## Scope

- Usar el PPT actual como plantilla visual editable.
- Incorporar los acuerdos y cambios formalizados en la última entrega ZIP.
- Incorporar la evolución real del modelo hasta F23 y seleccionar F22 seed 14.
- Condensar planificación, hitos y riesgos históricos que ya no sostienen la
  narrativa final.
- No presentar validación de test ni uso clínico como completados.

## Assumptions

- La audiencia es la cátedra y el experto asesor en una defensa académica.
- El objetivo es explicar decisiones y resultados, no repetir un informe de
  avance semanal.
- Se mantendrán formato 16:9, Arial/Courier New y la paleta del archivo fuente.

## Steps

1. Duplicar el PPT fuente y conservar masters, dimensiones y elementos útiles.
2. Reordenar la lámina de salud a la posición 2 y reconstruirla como resumen de
   problema, corrección, evidencia y riesgo restante.
3. Sustituir las láminas PMO obsoletas por una narrativa técnica de 10 láminas:
   objetivo, estado, datos/QC, PDS, diagnóstico, datos externos/sintéticos,
   arquitectura F22, resultados, ablación F23 y cierre.
4. Reutilizar los mejores gráficos existentes y crear gráficos editables para
   la evolución F16–F23 y la comparación RF/F22.
5. Añadir notas de fuente y dejar explícitos el split por paciente, el test no
   consultado y el alcance académico.

## Validation

- Contrastar cada cifra con los JSON/Markdown de resultados.
- Verificar orden, cobertura narrativa y coherencia de clases.
- Renderizar las 10 láminas y revisar legibilidad, solapamientos y consistencia
  visual a tamaño de proyección.
- Confirmar que tablas y gráficos permanecen editables.

## Risks

- El mejor resultado proviene de una sola seed verde; debe mostrarse junto con
  la variabilidad multisemilla.
- La entrega ZIP contiene planes anteriores a F20–F23; se usa como trazabilidad
  de decisiones, no como estado técnico vigente.
- El deck actual usa texto de 5–8 pt en varias láminas; la reconstrucción debe
  reducir densidad antes de disminuir tipografía.

## Outcome

Se generó `output/presentations/Presentacion-Final-Reestructurada-v1.pptx`
con 10 láminas y se mantuvo intacto el archivo fuente. El deck conserva la
identidad visual, la fotografía clínica y las figuras PDS/QC; reemplaza el
relato de avance por estado ejecutivo, técnicas F16–F23, procedencia de datos,
justificación del descarte de augmentation, arquitectura F22, resultados por
clase/semilla y límites de la entrega.

La validación confirmó 10 láminas 16:9, cero hallazgos geométricos, importación
correcta mediante Artifact Tool y un gráfico nativo editable en la lámina 9.
Las diez láminas finales fueron renderizadas e inspeccionadas individualmente.

# Presentación final — segunda iteración enfocada en la entrega

## Goal

Reducir antecedentes antiguos y devolver a la lámina 2 un estado de proyecto
muy cercano al tablero de salud del PPT original, actualizado con F22 y las
limitaciones vigentes.

## Scope

- Reducir el deck de 10 a 8 láminas.
- Eliminar las láminas independientes de objetivo general, QC detallado y
  pipeline PDS, conservando sólo las condiciones necesarias para interpretar
  esta entrega.
- Crear una lámina 2 de salud del proyecto con estado global, indicadores,
  dimensiones e hitos técnicos.
- Mantener el foco en corrección de Paced, experimentos F16–F23, datos usados,
  arquitectura F22, resultados y cierre.

## Assumptions

- El estado global correcto es ÁMBAR porque existe un candidato verde, pero
  sólo una de tres semillas cumple el gate y el test permanece reservado.
- Los hitos históricos pueden representarse como cerrados sin repetir sus
  gráficos ni desarrollo completo.

## Steps

1. Reestructurar el generador a 8 láminas.
2. Construir el tablero de salud en la posición 2 con el lenguaje visual del
   último slide original.
3. Convertir la antigua lámina 2 en “Cambios de esta entrega” y moverla a la
   posición 3.
4. Mantener las láminas de técnicas, datos, arquitectura, resultados y cierre.
5. Renderizar, revisar y finalizar como una nueva versión sin sobrescribir la
   entrega anterior.

## Validation

- Comparar la nueva lámina 2 con el tablero de salud original.
- Verificar 8 láminas, tamaño 16:9, integridad e importación.
- Inspeccionar cada lámina final a tamaño completo.

## Risks

- La reducción puede borrar contexto metodológico; se conservarán en una sola
  línea ZZU-only, split por paciente, train-only y test reservado.
- El tablero puede parecer más favorable de lo que permite la evidencia; el
  estado global y la validación se mantienen en ÁMBAR.

## Outcome

Se generó `output/presentations/Presentacion-Final-Enfocada-v2.pptx` con ocho
láminas. La lámina 2 recupera el tablero de salud del proyecto con el formato
del original y métricas vigentes: F22, resultados por clase, 1/3 semillas
verdes y test reservado.

Se retiraron las láminas independientes de objetivo general, QC y pipeline PDS.
El contenido restante quedó centrado en los cambios de esta entrega, técnicas
F16–F23, datos usados, descarte de augmentation, arquitectura F22, resultados
y límites. Las ocho láminas finales se renderizaron y revisaron a tamaño
completo.

# Presentación final — resultados comprensibles en la lámina 3

## Goal

Reestructurar la lámina 3 para presentar el avance del candidato F22 de forma
positiva, comprensible y respaldada por las métricas existentes.

## Scope

- Mantener las ocho láminas y el diseño de la versión enfocada.
- Cambiar la lámina 3 desde una lista de problemas a una síntesis de impacto.
- Mostrar mejora frente a RF, superación del gate, recuperación de Paced y
  desempeño positivo en las cinco clases.
- Conservar una nota breve sobre estabilidad y test pendiente.

## Validation

- Verificar los porcentajes derivados de F1 macro.
- Renderizar la lámina 3 antes y después.
- Revisar nuevamente las ocho láminas y finalizar como una versión nueva.

## Outcome

La lámina 3 quedó reestructurada como síntesis de resultados. Presenta primero
el avance del mejor candidato: 31,3 % sobre el gate global, 18,2 % sobre RF,
F1 Paced 0,7368, F1 positivo en las cinco clases y VT sobre su umbral. La nota
de estabilidad y test pendiente se mantuvo como cierre secundario.

Se generó `output/presentations/Presentacion-Final-Resultados-Claros-v3.pptx`.
Las ocho láminas finales se renderizaron e inspeccionaron individualmente.
