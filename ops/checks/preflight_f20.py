"""Preflight del sidecar HF F20; excluye y no consulta test."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'src'))

from ecg_pipeline.pacing import FEATURES_HF  # noqa: E402


DL = RAIZ / 'results' / 'dl'


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifiesto', type=Path, default=DL / 'manifiesto.csv')
    p.add_argument('--splits', type=Path, default=DL / 'splits.csv')
    p.add_argument('--sidecar', type=Path, default=DL / 'sidecar_hf_train_val.csv')
    p.add_argument('--normalizacion', type=Path,
                   default=DL / 'sidecar_hf_normalizacion.json')
    p.add_argument('--salida', type=Path)
    args = p.parse_args()
    errores: list[str] = []

    for ruta in (args.manifiesto, args.splits, args.sidecar, args.normalizacion):
        if not ruta.is_file():
            errores.append(f'falta archivo: {ruta}')
    if errores:
        terminar(errores, {}, args.salida)

    man = pd.read_csv(args.manifiesto)
    splits = pd.read_csv(args.splits, index_col=0)['particion']
    man = man.merge(splits, left_on='paciente', right_index=True,
                    validate='many_to_one')
    desarrollo = man[man.particion.isin(['train', 'val'])].copy()
    side = pd.read_csv(args.sidecar)
    requeridas = {'window_id', 'paciente', 'registro', 'particion', *FEATURES_HF}
    faltantes = requeridas - set(side.columns)
    if faltantes:
        errores.append(f'columnas sidecar ausentes: {sorted(faltantes)}')
        terminar(errores, {}, args.salida)
    if side.window_id.duplicated().any():
        errores.append('window_id duplicados en sidecar')
    if side.particion.eq('test').any():
        errores.append('sidecar contiene filas test')
    esperadas, observadas = set(desarrollo.window_id), set(side.window_id)
    if esperadas != observadas:
        errores.append(f'cobertura incorrecta: faltan={len(esperadas-observadas)} '
                        f'sobran={len(observadas-esperadas)}')
    unido = desarrollo[['window_id', 'paciente', 'registro', 'particion', 'clase']].merge(
        side, on='window_id', suffixes=('_man', '_side'), validate='one_to_one')
    for campo in ('paciente', 'registro', 'particion'):
        if not unido[f'{campo}_man'].astype(str).equals(
                unido[f'{campo}_side'].astype(str)):
            errores.append(f'{campo} difiere entre manifiesto y sidecar')
    valores = side[list(FEATURES_HF)].to_numpy(dtype=np.float64)
    if not np.isfinite(valores).all():
        errores.append('features HF contienen valores no finitos')
    if (valores < 0).any():
        errores.append('features HF deben ser no negativas antes de log1p')

    norm = json.loads(args.normalizacion.read_text())
    if norm.get('features') != list(FEATURES_HF):
        errores.append('orden de features en normalizacion incompatible')
    if norm.get('transformacion') != 'log1p':
        errores.append('transformacion HF distinta de log1p')
    media = np.asarray(norm.get('media_train', []), dtype=float)
    desv = np.asarray(norm.get('desv_train', []), dtype=float)
    if media.shape != (len(FEATURES_HF),) or desv.shape != (len(FEATURES_HF),):
        errores.append('media/desv HF tienen dimensión incorrecta')
    elif not np.isfinite(media).all() or not np.isfinite(desv).all() or (desv <= 0).any():
        errores.append('media/desv HF inválidas')
    else:
        train = side[side.particion.eq('train')]
        z = np.log1p(train[list(FEATURES_HF)].to_numpy(dtype=float))
        if not np.allclose(media, z.mean(axis=0), rtol=1e-8, atol=1e-10):
            errores.append('media HF no corresponde exclusivamente a train')
        if not np.allclose(desv, z.std(axis=0), rtol=1e-8, atol=1e-10):
            errores.append('desv HF no corresponde exclusivamente a train')

    resumen = {
        'ventanas': int(len(side)),
        'particiones': {k: int(v) for k, v in side.particion.value_counts().items()},
        'pacientes': int(side.paciente.nunique()),
        'clases': {k: int(v) for k, v in unido.clase.value_counts().items()},
        'features_hf': list(FEATURES_HF),
        'test_consultado': False,
    }
    terminar(errores, resumen, args.salida)


def terminar(errores: list[str], resumen: dict, salida: Path | None) -> None:
    reporte = {'estado': 'FALLA' if errores else 'OK', 'errores': errores,
               **resumen}
    texto = json.dumps(reporte, ensure_ascii=False, indent=2)
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + '\n')
    print(texto)
    if errores:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
