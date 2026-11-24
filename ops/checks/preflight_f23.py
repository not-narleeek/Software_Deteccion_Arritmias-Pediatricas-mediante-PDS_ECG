"""Valida split interno por paciente del especialista VT sin cargar señales."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedKFold


RAIZ = Path(__file__).resolve().parents[2]
DL = RAIZ / 'results' / 'dl'


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifiesto', type=Path, default=DL / 'manifiesto.csv')
    p.add_argument('--splits', type=Path, default=DL / 'splits_f20_active.csv')
    p.add_argument('--semilla', type=int, default=23)
    p.add_argument('--salida', type=Path)
    args = p.parse_args()
    man = pd.read_csv(args.manifiesto)
    splits = pd.read_csv(args.splits, index_col=0)['particion']
    man = man.merge(splits, left_on='paciente', right_index=True,
                    validate='many_to_one')
    train = man[man.particion.eq('train')]
    pacientes = (train.groupby('paciente').clase
                 .apply(lambda x: bool(x.eq('VT').any()))
                 .rename('es_vt').reset_index())
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.semilla)
    fit_i, cal_i = next(cv.split(pacientes.paciente, pacientes.es_vt))
    fit = set(pacientes.iloc[fit_i].paciente)
    cal = set(pacientes.iloc[cal_i].paciente)
    fit_w = train[train.paciente.isin(fit)]
    cal_w = train[train.paciente.isin(cal)]
    errores = []
    if fit & cal:
        errores.append('pacientes solapados')
    for nombre, d in (('fit', fit_w), ('calibracion', cal_w)):
        if not d.clase.eq('VT').any() or d.clase.eq('VT').all():
            errores.append(f'{nombre} no contiene VT y no-VT')
    reporte = {
        'estado': 'FALLA' if errores else 'OK', 'errores': errores,
        'semilla': args.semilla,
        'pacientes_fit': len(fit), 'pacientes_calibracion': len(cal),
        'pacientes_vt_fit': int(fit_w[fit_w.clase.eq('VT')].paciente.nunique()),
        'pacientes_vt_calibracion': int(
            cal_w[cal_w.clase.eq('VT')].paciente.nunique()),
        'ventanas_fit': int(len(fit_w)), 'ventanas_calibracion': int(len(cal_w)),
        'vt_fit': int(fit_w.clase.eq('VT').sum()),
        'vt_calibracion': int(cal_w.clase.eq('VT').sum()),
        'particiones_test_modificadas': False, 'test_consultado': False,
    }
    texto = json.dumps(reporte, indent=2)
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(texto + '\n')
    print(texto)
    if errores:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
