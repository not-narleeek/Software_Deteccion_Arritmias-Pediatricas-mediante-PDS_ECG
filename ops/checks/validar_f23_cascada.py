"""Prueba prioridad VT y preservación de clases en la cascada F23."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'scripts'))

from evaluar_cascada_f23 import combinar  # noqa: E402


def main() -> None:
    base = pd.DataFrame({'window_id': ['a', 'b', 'c'],
                         'clase_real': ['VT', 'Paced', 'Sinusal'],
                         'clase_pred': ['Otro', 'Paced', 'Sinusal']})
    vt = pd.DataFrame({'window_id': ['a', 'b', 'c'],
                       'clase_real': ['VT', 'Paced', 'Sinusal'],
                       'prob_vt': [0.9, 0.1, 0.2],
                       'pred_vt': [True, False, False]})
    pred = combinar(base, vt)
    errores = []
    if pred.clase_pred.tolist() != ['VT', 'Paced', 'Sinusal']:
        errores.append('prioridad VT incorrecta')
    if pred.clase_pred_f22.tolist() != ['Otro', 'Paced', 'Sinusal']:
        errores.append('predicción F22 no preservada')
    reporte = {'estado': 'FALLA' if errores else 'OK', 'errores': errores,
               'test_consultado': False}
    print(json.dumps(reporte, indent=2))
    if errores:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
