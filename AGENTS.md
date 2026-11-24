# AGENTS.md — Software de Detección de Arritmias Pediátricas (PDS ECG)

Proyecto académico de **Proyectos en TICS II** (UDP, 2S-2026): pipeline de
procesamiento digital de señales + clasificación de ritmo cardíaco pediátrico
sobre corpus **ZZU pECG** (12 derivaciones, 500 Hz, WFDB). Visión general,
pipeline y KPI en [README.md](README.md). Este archivo cubre cómo trabajar en
el repo, no qué es el proyecto.

## Entorno

- Python `>=3.11,<3.13` fijado en `.python-version` (3.11). Gestión con **uv**;
  versiones exactas en `uv.lock` (comprometido — no regenerar sin motivo).
- **No usar `pip install` global ni crear entornos manuales** para el pipeline:

```bash
uv sync                                  # crear/actualizar .venv desde uv.lock
uv run python scripts/<script>.py        # cualquier comando del proyecto
uv run jupyter lab                       # notebooks
```

- El entrenamiento DL corre en instancias **PyTorch de Vast.ai** (no local; no
  hay GPU ni RAM para entrenar). Ver
  [docs/runbooks/vastai_dl.md](docs/runbooks/vastai_dl.md). El entorno `uv`
  local es solo para el pipeline PDS, empaquetado de datos y validaciones.
- `contrib/carlos/f22_seed14/` usa **su propio** `requirements.txt` y venv
  aislado (`.venv-f22`), separado del entorno `uv` — ver su [README](contrib/carlos/f22_seed14/README.md).

## Layout

| Ruta | Contenido |
|---|---|
| `src/ecg_pipeline/` | Librería del pipeline DSP (tipada): `io`, `preprocess`, `features`, `models`, `pacing`, `report` |
| `scripts/` | Experimentos por fase: `inventario_zzu.py`, `qc_zzu.py`, `empaquetar_shards_dl.py`, `entrenar_especialista_vt.py`, `evaluar_cascada_f22.py`, … |
| `results/` | **Solo evidencia resumida pequeña** (JSON/CSV/figuras) por fase: `fase1_limpieza/`, `fase2_pipeline/`, `dl/` |
| `ops/` | Operación GPU: `checks/` (preflight/validación por fase), `scripts/`, `supervisor/` |
| `docs/` | Documentación viva — ver abajo |
| `notebooks/` | Drivers de Colab (`05_dl_colab.ipynb`, …) |
| `web/` | Portal de demo estático (HTML/CSS/JS puro, sin dependencias ni build); acepta registros **WFDB** (`.hea` + `.dat`) y ejecuta el análisis en el navegador |
| `web/demo/` | Registros WFDB de demostración (sintéticos, 12 derivaciones, 10 s @ 500 Hz) — regenerar con `uv run python scripts/generar_demo_wfdb.py` |
| `contrib/` | Paquetes aislados de inferencia para el equipo |
| `data/` | Corpus ZZU (~12 GB) — **nunca en git**, solo local (`.gitignore`) |

## Documentación viva (leer antes de tocar su dominio)

- `docs/plan_accion.md` — plan Etapa II (PDS/SVM/RF), hitos F6–F14.
- `docs/plan_dl_zzu.md` — plan Etapa II-bis (Deep Learning, decisiones D1–D6).
- `docs/resultados_dl_f16…f23.md` — resultado por fase DL; una por hito.
- `docs/runbooks/` — procedimientos operativos (Vast.ai, empaquetado, cascadas).
- `docs/adr/0001–0004` — decisiones de diseño (rama HF paced, cascada
  morfología→gate, especialista VT). **Cambios de diseño = ADR nuevo.**
- `docs/metodologia_zzu_pecg.md`, `docs/etapa*.md` — corpus, QC, etapas.
- `docs/reunion_maureira_2026-10-12.md` — feedback del experto asesor.
- `docs/diseno_pipeline.md` §11 — protocolo de verificación por KPI.

## Convenciones

1. **Todo en español**: código documentado, docs, mensajes de commit. Los
   commits de fase siguen la serie `F<n>:` (continúa la última fase de
   `docs/resultados_dl_*` / `PLANS.md`); fixes posteriores usan `F<n> fix:`.
2. **Un hito = código + script de verificación + evidencia comprometida.** Los
   scripts de verificación **fallan (exit ≠ 0) si su KPI no se cumple** — no
   "suavizar" ese comportamiento ni convertir fallos de KPI en warnings.
3. **Evidencia pequeña y explícita**: a `results/` solo entran resúmenes
   (JSON/CSV/figuras) que documentan preflight, gates y métricas. Shards,
   checkpoints (`*.pt`), `runs/`, predicciones completas y datasets están
   excluidos por `.gitignore` — nunca forzar su inclusión.
4. **Test reservado**: el split de test (80/10/10 por paciente) no se consulta
   ni ajusta durante iteraciones; los splits agrupan por PACIENTE (nunca
   mezclar estudios del mismo niño entre train/val/test).
5. **Corpus ZZU-only**: Leipzig fue eliminado del proyecto (13-oct-2026). No
   reintroducirlo ni referenciarlo como corpus activo; el historial git lo
   conserva como evidencia.
6. **`contrib/carlos/f22_seed14/` es un bundle congelado**: `manifest.json`
   fija nombre, tamaño y SHA-256 de los checkpoints del Release
   `f22-seed14-v1`. No editar arquitectura, hashes ni normalizaciones sin
   versionar el bundle; los pesos **nunca** van al historial de git.
7. **`web/` sin dependencias**: HTML/CSS/JS puro; el lector WFDB propio
   (`web/js/wfdb.js`, semántica idéntica a wfdb-python) acepta registros
   `.hea` + `.dat`, nunca CSV. Todo el análisis corre en el navegador. Su
   clasificación es **heurística y académica** — no presentarla nunca como el
   modelo F22 ni como dispositivo médico. Servir con
   `python -m http.server 8000 --directory web`.

## Verificación (mínimo antes de considerar algo listo)

```bash
python -m py_compile <scripts .py tocados>       # sintaxis
uv run --with pytest pytest contrib/carlos/f22_seed14/tests   # tests del bundle
python contrib/carlos/f22_seed14/validar_modelo.py --solo-manifiesto
bash -n ops/scripts/*.sh ops/supervisor/*.sh     # scripts de shell
jq empty notebooks/*.ipynb                       # notebooks operativos
git diff --check                                 # whitespace
```

La validación de cada fase vive en `ops/checks/` (GPU) y en
`scripts/validar_*.py` / `evaluar_*.py` (local); correr la que corresponda al
área tocada. El resultado verificado se compromete como evidencia.

## Ramas y entrega

- `main` = estado de entrega; el trabajo va en rama por fase
  (`busqueda-datos`, `etapa2-corpus-combinado`, `entrega-final-f22`,
  `web-portal` son ejemplos históricos) y se integra por PR.
- Remote: `github.com:not-narleeek/Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG`.
- Higiene: no commitear secretos (claves SSH/API de Vast.ai, Colab,
  Tailscale); los runbooks exigen claves públicas, nunca privadas.

## Reglas duras (no negociables)

- **Nunca** commitear `data/`, shards, checkpoints ni entregables binarios
  pesados (PPTX/ZIP están en `.gitignore` a propósito).
- **Nunca** reportar métricas sin el resultado que las respalda comprometido
  en `results/` o `docs/`.
- **Nunca** tocar el split de test para mejorar métricas; las mejoras de
  modelos van por iteración autorizada (F<n>-bis, -ter) documentada.
- El sistema **no es un dispositivo médico**: cualquier salida nueva (web,
  reportes, demo) debe mantener el aviso de uso académico/no certificado.
