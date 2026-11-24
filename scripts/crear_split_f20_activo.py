"""Crea el split F20 para pacing activo sin modificar el split histórico."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
DL = RAIZ / 'results' / 'dl'
FEATURES_HF = [
    'espiculas_n', 'hf_rms_mediana', 'hf_rms_max', 'hf_q995_mediana',
    'hf_q995_max', 'slew_q999_mediana', 'slew_q999_max',
    'sincronia_hf_q999',
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--splits', type=Path, default=DL / 'splits.csv')
    p.add_argument('--manifiesto', type=Path, default=DL / 'manifiesto.csv')
    p.add_argument('--sidecar', type=Path, default=DL / 'sidecar_hf_train_val.csv')
    p.add_argument('--paciente-incierto', default='P05649')
    p.add_argument('--paciente-val-activo', default='P05281')
    p.add_argument('--salida-splits', type=Path,
                   default=DL / 'splits_f20_active.csv')
    p.add_argument('--salida-sidecar', type=Path,
                   default=DL / 'sidecar_hf_f20_active.csv')
    p.add_argument('--salida-normalizacion', type=Path,
                   default=DL / 'sidecar_hf_f20_active_normalizacion.json')
    p.add_argument('--salida-reporte', type=Path,
                   default=DL / 'f20_active_split.json')
    args = p.parse_args()

    splits = pd.read_csv(args.splits, index_col=0)
    if list(splits.columns) != ['particion']:
        raise ValueError('splits debe contener únicamente la columna particion')
    original = splits.particion.copy()
    if original.get(args.paciente_incierto) != 'val':
        raise ValueError(f'{args.paciente_incierto} no está en val')
    if original.get(args.paciente_val_activo) != 'train':
        raise ValueError(f'{args.paciente_val_activo} no está en train')
    splits.loc[args.paciente_incierto, 'particion'] = 'holdout_uncertain'
    splits.loc[args.paciente_val_activo, 'particion'] = 'val'
    if not original[original.eq('test')].index.equals(
            splits.particion[splits.particion.eq('test')].index):
        raise RuntimeError('la partición test cambió')

    man = pd.read_csv(args.manifiesto)
    clases = man.groupby('paciente').clase.agg(lambda x: sorted(set(x)))
    if clases.get(args.paciente_val_activo) != ['Paced']:
        raise ValueError('el paciente de val activo no es exclusivamente Paced')
    side = pd.read_csv(args.sidecar).drop(columns='particion')
    mapa = splits.particion.rename('particion')
    side = side.merge(mapa, left_on='paciente', right_index=True,
                      validate='many_to_one')
    side = side[side.particion.isin(['train', 'val'])].copy()
    columnas = ['window_id', 'paciente', 'registro', 'particion', *FEATURES_HF]
    side = side[columnas]

    train = np.log1p(side.loc[side.particion.eq('train'), FEATURES_HF]
                     .to_numpy(dtype=np.float64))
    media, desv = train.mean(axis=0), train.std(axis=0)
    if not np.isfinite(train).all() or (desv <= 0).any():
        raise ValueError('estadísticos HF train inválidos')
    norm = {
        'features': FEATURES_HF,
        'transformacion': 'log1p',
        'media_train': media.tolist(),
        'desv_train': desv.tolist(),
        'incluye_test': False,
        'split': str(args.salida_splits),
    }
    reporte = {
        'definicion_objetivo': 'Paced con evidencia de pacing activo',
        'paciente_holdout_uncertain': args.paciente_incierto,
        'paciente_val_activo': args.paciente_val_activo,
        'cambios': {
            args.paciente_incierto: ['val', 'holdout_uncertain'],
            args.paciente_val_activo: ['train', 'val'],
        },
        'ventanas_sidecar': int(len(side)),
        'ventanas_por_particion': {
            k: int(v) for k, v in side.particion.value_counts().items()
        },
        'ventanas_paced_val': int(man[
            man.paciente.eq(args.paciente_val_activo)].window_id.nunique()),
        'test_modificado': False,
        'test_consultado': False,
    }

    for ruta in (args.salida_splits, args.salida_sidecar,
                 args.salida_normalizacion, args.salida_reporte):
        ruta.parent.mkdir(parents=True, exist_ok=True)
    splits.to_csv(args.salida_splits)
    side.to_csv(args.salida_sidecar, index=False)
    args.salida_normalizacion.write_text(
        json.dumps(norm, ensure_ascii=False, indent=2) + '\n')
    args.salida_reporte.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(reporte, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
