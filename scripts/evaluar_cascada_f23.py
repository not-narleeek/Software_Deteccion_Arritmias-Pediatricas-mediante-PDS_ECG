"""Aplica especialista VT train-only sobre una predicción de cascada F22."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'scripts'))

from evaluar_cascada_f22 import CLASES, metricas  # noqa: E402


def combinar(base: pd.DataFrame, vt: pd.DataFrame) -> pd.DataFrame:
    requeridas_base = {'window_id', 'clase_real', 'clase_pred'}
    requeridas_vt = {'window_id', 'clase_real', 'prob_vt', 'pred_vt'}
    if not requeridas_base <= set(base):
        raise ValueError('predicciones F22 incompletas')
    if not requeridas_vt <= set(vt):
        raise ValueError('predicciones especialista VT incompletas')
    a = base.set_index('window_id').sort_index()
    b = vt.set_index('window_id').sort_index()
    if not a.index.equals(b.index):
        raise ValueError('cobertura window_id distinta')
    if not a.clase_real.equals(b.clase_real):
        raise ValueError('clase_real distinta')
    salida = a.copy()
    salida['clase_pred_f22'] = salida.clase_pred
    salida['prob_vt_especialista'] = b.prob_vt
    salida['gate_vt'] = b.pred_vt.astype(bool)
    salida.loc[salida.gate_vt, 'clase_pred'] = 'VT'
    return salida.reset_index()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predicciones-f22', type=Path, required=True)
    p.add_argument('--predicciones-vt', type=Path, required=True)
    p.add_argument('--salida', type=Path, required=True)
    p.add_argument('--matriz', type=Path, required=True)
    p.add_argument('--gate', type=Path, required=True)
    args = p.parse_args()
    pred = combinar(pd.read_csv(args.predicciones_f22),
                    pd.read_csv(args.predicciones_vt))
    f1, matriz = metricas(pred)
    macro = float(np.mean(list(f1.values())))
    criterios = {'macro_ge_0.4664': macro >= 0.4664,
                 'paced_gt_0': f1['Paced'] > 0,
                 'vt_ge_0.4115': f1['VT'] >= 0.4115}
    cambios = (pred[pred.gate_vt]
               .groupby(['clase_real', 'clase_pred_f22']).size())
    reporte = {
        'estado': 'VERDE' if all(criterios.values()) else 'ROJO',
        'arquitectura': 'especialista VT > cascada F22',
        'criterios': criterios,
        'f1_macro_val': macro,
        'f1_por_clase': f1,
        'gate_vt_positivos': int(pred.gate_vt.sum()),
        'overrides_por_real_y_previa': {
            f'{real}->{previa}': int(n)
            for (real, previa), n in cambios.items()
        },
        'test_consultado': False,
    }
    for ruta in (args.salida, args.matriz, args.gate):
        ruta.parent.mkdir(parents=True, exist_ok=True)
    pred.to_csv(args.salida, index=False)
    pd.DataFrame(matriz, index=CLASES, columns=CLASES).to_csv(args.matriz)
    args.gate.write_text(json.dumps(reporte, indent=2) + '\n')
    print(json.dumps(reporte, indent=2))


if __name__ == '__main__':
    main()
