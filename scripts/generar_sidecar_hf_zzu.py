"""Genera sidecar HF F20 desde ECG crudo ZZU, solo para train/val.

El test se excluye por defecto y no se leen sus señales. La salida se alinea
uno-a-uno por ``window_id`` con el manifiesto DL existente. La normalización
``log1p + z-score`` se estima exclusivamente sobre train.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'src'))

from ecg_pipeline import io  # noqa: E402
from ecg_pipeline.pacing import FEATURES_HF, extraer_features_hf  # noqa: E402


DL = RAIZ / 'results' / 'dl'
FS = 500
MUESTRAS_VENTANA = 10 * FS
MUESTRAS_HOP = 5 * FS


def argumentos() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifiesto', type=Path, default=DL / 'manifiesto.csv')
    p.add_argument('--splits', type=Path, default=DL / 'splits.csv')
    p.add_argument('--salida', type=Path, default=DL / 'sidecar_hf_train_val.csv')
    p.add_argument('--normalizacion', type=Path,
                   default=DL / 'sidecar_hf_normalizacion.json')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--limite-registros', type=int, default=0,
                   help='solo para humo local; 0 procesa todos')
    p.add_argument('--incluir-test', action='store_true',
                   help='reservado para evaluación final autorizada')
    return p.parse_args()


def _inicio(window_id: str) -> int:
    return int(str(window_id).rsplit('_', 1)[1]) * MUESTRAS_HOP


def procesar_registro(args: tuple[str, list[dict]]) -> list[dict]:
    registro, ventanas = args
    x, fs, presentes = io.cargar_registro_zzu(registro)
    if int(fs) != FS:
        raise ValueError(f'{registro}: fs={fs}, esperado {FS}')
    indices = [io.SURFACE.index(d) for d in presentes]
    x = x[:, indices]
    filas = []
    for ventana in ventanas:
        inicio = _inicio(ventana['window_id'])
        fin = inicio + MUESTRAS_VENTANA
        if fin > len(x):
            raise ValueError(f'{ventana["window_id"]}: fuera de {len(x)} muestras')
        filas.append({
            'window_id': ventana['window_id'],
            'paciente': ventana['paciente'],
            'registro': registro,
            'particion': ventana['particion'],
            **extraer_features_hf(x[inicio:fin], FS),
        })
    return filas


def main() -> None:
    args = argumentos()
    man = pd.read_csv(args.manifiesto)
    splits = pd.read_csv(args.splits, index_col=0)['particion']
    man = man.merge(splits, left_on='paciente', right_index=True,
                    validate='many_to_one')
    permitidas = {'train', 'val', 'test'} if args.incluir_test else {'train', 'val'}
    man = man[man.particion.isin(permitidas)].copy()
    if args.limite_registros:
        registros = sorted(man.registro.unique())[:args.limite_registros]
        man = man[man.registro.isin(registros)]
    trabajos = [
        (registro, grupo[['window_id', 'paciente', 'particion']].to_dict('records'))
        for registro, grupo in man.groupby('registro', sort=True)
    ]
    filas: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, resultado in enumerate(ex.map(procesar_registro, trabajos,
                                              chunksize=8), 1):
            filas.extend(resultado)
            if i % 500 == 0:
                print(f'registros {i}/{len(trabajos)}', flush=True)
    sidecar = pd.DataFrame(filas).sort_values('window_id').reset_index(drop=True)
    if sidecar.window_id.duplicated().any():
        raise SystemExit('F20 FALLA: window_id duplicados en sidecar')
    esperadas = set(man.window_id)
    obtenidas = set(sidecar.window_id)
    if esperadas != obtenidas:
        raise SystemExit(f'F20 FALLA: cobertura sidecar difiere: '
                         f'faltan={len(esperadas-obtenidas)} sobran={len(obtenidas-esperadas)}')
    if not np.isfinite(sidecar[list(FEATURES_HF)].to_numpy()).all():
        raise SystemExit('F20 FALLA: features HF no finitas')
    if not args.incluir_test and sidecar.particion.eq('test').any():
        raise SystemExit('F20 FALLA: sidecar de desarrollo contiene test')

    train = sidecar[sidecar.particion.eq('train')]
    z = np.log1p(train[list(FEATURES_HF)].to_numpy(dtype=np.float64))
    media = z.mean(axis=0)
    desv = z.std(axis=0)
    if (desv <= 0).any():
        raise SystemExit('F20 FALLA: feature HF constante en train')
    norm = {
        'features': list(FEATURES_HF),
        'transformacion': 'log1p',
        'media_train': media.tolist(),
        'desv_train': desv.tolist(),
        'n_train': int(len(train)),
        'incluye_test': bool(args.incluir_test),
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    sidecar.to_csv(args.salida, index=False)
    args.normalizacion.write_text(json.dumps(norm, indent=2) + '\n')
    print(json.dumps({
        'estado': 'OK',
        'ventanas': int(len(sidecar)),
        'particiones': sidecar.particion.value_counts().to_dict(),
        'registros': int(sidecar.registro.nunique()),
        'pacientes': int(sidecar.paciente.nunique()),
        'incluye_test': bool(args.incluir_test),
    }, indent=2))


if __name__ == '__main__':
    main()
