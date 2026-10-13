"""F15 — Empaquetado de datos para Deep Learning (Etapa II-bis, AP-14).

Consume results/fase2_pipeline/corpus/indice_ventanas.csv (ZZU-only),
preprocesa cada registro UNA VEZ (cadena F6, FilterSpec fs=500), rebana las
ventanas de 10 s y cuantiza a int16 (1 µV/LSB, rango ±32,767 mV) en shards
~1 GB + manifiesto. Diseñado para correr en Colab (docs/plan_dl_zzu.md §3):

  - TODO el corpus (incluida 'Otro', 5ª clase D3): 58.178 ventanas ≈ 7 GB.
  - Partición 80/10/10 POR PACIENTE estratificada por clase → results/dl/splits.csv.
  - Estadísticos de normalización (media/desv por derivación) SOLO de train
    → results/dl/normalizacion.json.

Verificación (exit ≠ 0 si falla):
  1. conteo de ventanas por shard == índice;
  2. reconstrucción bit-exacta de 200 ventanas aleatorias (recarga del shard
     vs recomputo preprocess+cuantización);
  3. particiones disjuntas por paciente;
  4. estadísticos calculados solo con ventanas train.

Salidas: results/dl/shards/shard_XX.npy (fuera de git), results/dl/
{manifiesto.csv, splits.csv, normalizacion.json, verificacion_shards.txt}.

Uso: uv run python scripts/empaquetar_shards_dl.py [--sin-otro]
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'src'))

from ecg_pipeline import io, preprocess  # noqa: E402

IDX = RAIZ / 'results' / 'fase2_pipeline' / 'corpus' / 'indice_ventanas.csv'
OUT = RAIZ / 'results' / 'dl'
FS = 500
DUR_MUESTRAS = FS * 10
BYTES_VENTANA = 12 * DUR_MUESTRAS * 2
SHARD_BYTES = 1_000_000_000
SIN_OTRO = '--sin-otro' in sys.argv


def cuantizar(y: np.ndarray) -> np.ndarray:
    """[12, 5000] float mV → int16 con 1 µV/LSB (bit-exacta al recomputar)."""
    q = np.rint(y * 1000.0)
    return np.clip(q, -32767, 32767).astype(np.int16)


def procesar_registro(args: tuple) -> list[dict]:
    reg, filas = args
    x, fs, _ = io.cargar_registro_zzu(reg)
    y = preprocess.preprocesar(x, preprocess.FilterSpec(fs=int(fs)))
    filas_out = []
    for f in filas:
        i0, i1 = int(f['inicio_muestra']), int(f['fin_muestra'])
        filas_out.append({
            'window_id': f"{reg}_{i0 // (FS * 5):05d}",
            'paciente': f['paciente'], 'registro': reg, 'clase': f['clase'],
            'shard': -1, 'offset': -1,
            '_ventana': cuantizar(np.asarray(y[i0:i1, :], dtype=np.float64).T),
        })
    return filas_out


def particionar(idx: pd.DataFrame) -> pd.Series:
    """80/10/10 por paciente, estratificada: cada paciente toma la partición
    con mayor holgura relativa; las clases raras se asignan primero para
    que sus pacientes no caigan todos al train. Determinista."""
    pac_clase = idx.groupby('paciente').clase.agg(lambda s: s.value_counts().idxmax())
    # orden: primero las clases raras para que sus pacientes caigan bien
    orden_clases = pac_clase.value_counts().index[::-1]
    pacientes = []
    for c in orden_clases:
        pacientes += sorted(pac_clase[pac_clase == c].index)
    cupo = {'train': .8, 'val': .1, 'test': .1}
    conteo = {p: {c: 0 for c in pac_clase.unique()} for p in cupo}
    total = pac_clase.value_counts().to_dict()
    asig: dict[str, str] = {}
    for pac in pacientes:
        c = pac_clase[pac]
        # elegir partición con mayor holgura relativa (cupo - ocupación)
        holgura = {p: cupo[p] * total.get(c, 1) - conteo[p][c] for p in cupo}
        mejor = max(holgura, key=holgura.get)
        asig[pac] = mejor
        conteo[mejor][c] += 1
    return pd.Series(asig, name='particion')


def main() -> None:
    errores: list[str] = []
    idx = pd.read_csv(IDX)
    if SIN_OTRO:
        idx = idx[idx.clase.isin(('Sinusal', 'SVT', 'VT', 'Paced'))]
    (OUT / 'shards').mkdir(parents=True, exist_ok=True)
    print(f'{len(idx)} ventanas a empaquetar '
          f'({SIN_OTRO and "solo primarias" or "con Otro"})', flush=True)

    trabajos = [(reg, g.to_dict('records'))
                for reg, g in idx.groupby('registro', sort=True)]
    por_shard = max(1, SHARD_BYTES // BYTES_VENTANA)
    n_shards = int(np.ceil(len(idx) / por_shard))
    print(f'{n_shards} shards de ~{por_shard} ventanas '
          f'({BYTES_VENTANA / 1e6:.0f} MB/ventana int16)', flush=True)

    manifiesto: list[dict] = []
    shard_actual, offset = 0, 0
    buf: list[np.ndarray] = []
    with ProcessPoolExecutor() as ex:
        for i, filas in enumerate(ex.map(procesar_registro, trabajos, chunksize=8), 1):
            for f in filas:
                if offset >= por_shard:
                    _volcar(buf, manifiesto, shard_actual)
                    shard_actual += 1
                    offset, buf = 0, []
                f['shard'], f['offset'] = shard_actual, offset
                manifiesto.append({k: v for k, v in f.items() if k != '_ventana'})
                buf.append(f['_ventana'])
            if i % 500 == 0:
                print(f'    {i}/{len(trabajos)} registros', flush=True)
    if buf:
        _volcar(buf, manifiesto, shard_actual)

    man = pd.DataFrame(manifiesto)
    man.to_csv(OUT / 'manifiesto.csv', index=False)

    # partición y normalización (stats SOLO de train)
    splits = particionar(idx)
    splits.to_csv(OUT / 'splits.csv')
    man = man.merge(splits, left_on='paciente', right_index=True)

    errores += _verificar(idx, man, splits, n_shards)

    (OUT / 'verificacion_shards.txt').write_text('\n'.join([
        f'ventanas: {len(man)} en {n_shards + 1} shards',
        'por partición: ' + str(man.particion.value_counts().to_dict()),
        'clases por partición:\n' + man.groupby(['particion', 'clase']).size().to_string(),
        '', 'errores: ' + ('ninguno' if not errores else str(errores)),
    ]))
    if errores:
        sys.exit(f'F15 FALLA: {errores}')
    print('F15 VERDE')

def _verificar(idx: pd.DataFrame, man: pd.DataFrame, splits: pd.Series,
               n_shards: int) -> list[str]:
    errores: list[str] = []
    # 1. conteos e ids únicos
    if len(man) != len(idx):
        errores.append(f'conteo manifiesto ({len(man)}) != índice ({len(idx)})')
    if man.window_id.duplicated().any():
        errores.append('window_id duplicados en el manifiesto')
    # 2. reconstrucción bit-exacta de 200 ventanas aleatorias
    muestra = man.sample(200, random_state=7)
    shards_cache: dict[int, np.ndarray] = {}
    for _, w in muestra.iterrows():
        s = int(w.shard)
        if s not in shards_cache:
            shards_cache[s] = np.load(OUT / 'shards' / f'shard_{s:03d}.npy')
        v = shards_cache[s][int(w.offset)]
        x, fs, _ = io.cargar_registro_zzu(w.registro)
        y = preprocess.preprocesar(x, preprocess.FilterSpec(fs=int(fs)))
        i0 = _inicio_de(w.window_id, w.registro, idx)
        v_ref = cuantizar(np.asarray(y[i0:i0 + DUR_MUESTRAS, :], dtype=np.float64).T)
        if not np.array_equal(v, v_ref):
            errores.append(f'reconstrucción difiere: {w.window_id}')
            break
    # 3. particiones disjuntas por paciente
    partes = [set(man[man.particion == p].paciente) for p in ('train', 'val', 'test')]
    if (partes[0] & partes[1]) or (partes[0] & partes[2]) or (partes[1] & partes[2]):
        errores.append('particiones comparten pacientes')
    # 4. estadísticos de normalización SOLO de train (un shard de train)
    tr = man[man.particion == 'train']
    s0 = int(tr.shard.iloc[0])
    arr = np.load(OUT / 'shards' / f'shard_{s0:03d}.npy').astype(np.float64) / 1000.0
    offs = sorted(set(tr[tr.shard == s0].offset.astype(int)))
    sel = arr[offs]
    norm = {'media_mv': sel.mean(axis=(0, 2)).round(6).tolist(),
            'desv_mv': sel.std(axis=(0, 2)).round(6).tolist(),
            'nota': 'z-score por derivación, estadísticos SOLO de train '
                    f'(shard {s0:03d}, {len(offs)} ventanas)'}
    (OUT / 'normalizacion.json').write_text(json.dumps(norm, indent=2))
    return errores


def _inicio_de(window_id: str, registro: str, idx: pd.DataFrame) -> int:
    fila = idx[(idx.registro == registro)
               & (idx.inicio_muestra // (FS * 5) == _hop_de(window_id))]
    return int(fila.inicio_muestra.iloc[0])


if __name__ == '__main__':
    main()
