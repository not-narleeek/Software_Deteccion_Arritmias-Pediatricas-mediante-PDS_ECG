"""Preflight local/remoto para F18; no ejecuta inferencia sobre test."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DL = RAIZ / 'results' / 'dl'
CLASES = ['Sinusal', 'SVT', 'VT', 'Paced', 'Otro']


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifiesto', type=Path, default=DL / 'manifiesto.csv')
    ap.add_argument('--splits', type=Path, default=DL / 'splits.csv')
    ap.add_argument('--normalizacion', type=Path,
                    default=DL / 'normalizacion.json')
    ap.add_argument('--dir-shards', type=Path, default=DL / 'shards')
    ap.add_argument('--fraccion-paced', type=float, default=0.03)
    ap.add_argument('--salida', type=Path)
    args = ap.parse_args()

    errores: list[str] = []
    advertencias: list[str] = []
    for ruta in (args.manifiesto, args.splits, args.normalizacion):
        if not ruta.is_file():
            errores.append(f'falta archivo: {ruta}')
    if not args.dir_shards.is_dir():
        errores.append(f'falta directorio de shards: {args.dir_shards}')
    if errores:
        terminar(errores, advertencias, {}, args.salida)

    man = pd.read_csv(args.manifiesto)
    requeridas = {'window_id', 'paciente', 'registro', 'clase', 'shard', 'offset'}
    faltantes = requeridas - set(man.columns)
    if faltantes:
        errores.append(f'columnas ausentes en manifiesto: {sorted(faltantes)}')
        terminar(errores, advertencias, {}, args.salida)
    if man.window_id.duplicated().any():
        errores.append('window_id duplicados')
    desconocidas = sorted(set(man.clase) - set(CLASES))
    if desconocidas:
        errores.append(f'clases desconocidas: {desconocidas}')

    splits = pd.read_csv(args.splits, index_col=0)['particion']
    if splits.index.duplicated().any():
        errores.append('pacientes duplicados en splits.csv')
    sin_split = sorted(set(man.paciente) - set(splits.index))
    if sin_split:
        errores.append(f'{len(sin_split)} pacientes sin split')
    man = man.merge(splits, left_on='paciente', right_index=True,
                    validate='many_to_one')
    if not set(man.particion).issubset({'train', 'val', 'test'}):
        errores.append('splits contiene particiones distintas de train/val/test')

    norm = json.loads(args.normalizacion.read_text())
    media = np.asarray(norm.get('media_mv', []), dtype=float)
    desv = np.asarray(norm.get('desv_mv', []), dtype=float)
    if media.shape != (12,) or desv.shape != (12,):
        errores.append('normalizacion debe contener 12 medias y 12 desv')
    elif not np.isfinite(media).all() or not np.isfinite(desv).all() or (desv <= 0).any():
        errores.append('normalizacion contiene valores no finitos o desv <= 0')

    shards_info = {}
    for shard, filas in man.groupby('shard'):
        ruta = args.dir_shards / f'shard_{int(shard):03d}.npy'
        if not ruta.is_file():
            errores.append(f'falta {ruta.name}')
            continue
        arr = np.load(ruta, mmap_mode='r')
        shards_info[ruta.name] = {'shape': list(arr.shape), 'dtype': str(arr.dtype)}
        if arr.ndim != 3 or arr.shape[1:] != (12, 5000):
            errores.append(f'{ruta.name} shape inesperado: {arr.shape}')
        if arr.dtype != np.int16:
            errores.append(f'{ruta.name} dtype inesperado: {arr.dtype}')
        offsets = filas.offset.astype(int)
        if offsets.min() < 0 or offsets.max() >= arr.shape[0]:
            errores.append(f'{ruta.name} contiene offsets fuera de rango')

    if not 0.0 < args.fraccion_paced < 1.0:
        errores.append('fraccion-paced debe estar entre 0 y 1')
    train = man[man.particion.eq('train')]
    val = man[man.particion.eq('val')]
    paced_train = train[train.clase.eq('Paced')]
    paced_val = val[val.clase.eq('Paced')]
    if paced_train.paciente.nunique() < 2:
        errores.append('Paced train tiene menos de 2 pacientes')
    if paced_val.paciente.nunique() <= 1:
        advertencias.append('Paced val contiene un solo paciente; F1 inestable')
    if args.fraccion_paced > 0.05:
        advertencias.append('fraccion-paced >5% puede repetir en exceso la clase')

    conteos = (man.groupby(['particion', 'clase']).size()
               .unstack(fill_value=0).reindex(columns=CLASES, fill_value=0))
    resumen = {
        'ventanas': int(len(man)),
        'shards': shards_info,
        'conteos': {p: {c: int(v) for c, v in fila.items()}
                    for p, fila in conteos.to_dict('index').items()},
        'paced_train_pacientes': int(paced_train.paciente.nunique()),
        'paced_val_pacientes': int(paced_val.paciente.nunique()),
        'fraccion_paced_objetivo': args.fraccion_paced,
    }
    terminar(errores, advertencias, resumen, args.salida)


def terminar(errores: list[str], advertencias: list[str], resumen: dict,
             salida: Path | None) -> None:
    reporte = {'estado': 'FALLA' if errores else 'OK', 'errores': errores,
               'advertencias': advertencias, **resumen}
    texto = json.dumps(reporte, indent=2)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + '\n')
    print(texto)
    if errores:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
