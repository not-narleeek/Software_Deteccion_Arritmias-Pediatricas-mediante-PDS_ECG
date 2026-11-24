# Runbook F19 — datasets complementarios para Paced

## Propósito

Descargar y auditar señales externas para un detector auxiliar de pacing sin
modificar el corpus ni las particiones ZZU. PTB-XL y Leipzig son fuentes de
preentrenamiento/ablación; nunca reemplazan la validación pediátrica ZZU.

## Fuentes y almacenamiento

- PTB-XL 1.0.3: `data/f19_paced/ptb-xl/1.0.3/`.
- Leipzig Heart Center 1.0.0: `data/f19_paced/leipzig/1.0.0/`.
- Manifiestos/resultados: `results/dl/f19_datasets/`.

`data/` está excluido de git. Las descargas usan archivos `.part`, rango HTTP
y sustitución atómica; una ejecución interrumpida puede repetirse. Cada archivo
se acepta únicamente cuando su SHA-256 coincide con `SHA256SUMS.txt` oficial.

## Ejecución

Inventario sin señales grandes:

```bash
uv run python scripts/preparar_f19_datasets.py --solo-metadata
uv run python ops/checks/validar_f19_datasets.py
```

Descarga selectiva completa y validación de lectura:

```bash
uv run python scripts/preparar_f19_datasets.py --descargar-senales
uv run python ops/checks/validar_f19_datasets.py --exigir-senales
```

Baseline de alta frecuencia y transferencia PTB-XL → Leipzig:

```bash
uv run python scripts/evaluar_f19_paced.py
```

Use `--recalcular` solo si cambió el extractor; de lo contrario se reutilizan
los CSV de features.

## Contratos

- PTB-XL: todos los `PACE` de la versión 1.0.3 y controles no-PACE
  emparejados aproximadamente por edad/sexo; IDs namespaced por paciente.
- Leipzig: se descargan señales solo para registros que poseen latidos `/` o
  anotaciones auriculares/ventriculares de pacing.
- El baseline no usa edad, sexo ni texto clínico como variables.
- La validación cruzada PTB-XL agrupa todos los registros del mismo paciente.
- La transferencia Leipzig usa un umbral fijo de 0,5 sin ajuste externo.
- El conjunto test ZZU no se consulta.

## Recuperación

- Una descarga interrumpida: repetir el mismo comando; los `.part` se reanudan.
- Checksum inválido: conservar el mensaje, eliminar solamente el archivo
  individual indicado y repetir. No borrar directorios completos.
- Cambio de versión del dataset: usar un directorio/versionado distinto y no
  mezclar checksums ni manifiestos.

## Limitaciones

- PTB-XL `PACE` es adulto y no entra directamente en validación pediátrica.
- Leipzig proviene de estudios electrofisiológicos y está limitado a 100 Hz;
  pacing inducido no equivale necesariamente a marcapasos implantado.
- Una etiqueta de registro PTB-XL puede no contener espículas visibles durante
  los diez segundos completos.
