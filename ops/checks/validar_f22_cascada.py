"""Prueba contratos de prioridad, alineación y métricas de la cascada F22."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'scripts'))

from evaluar_cascada_f22 import combinar, metricas  # noqa: E402


def main() -> None:
    base = pd.DataFrame({
        'window_id': ['a', 'b', 'c'],
        'paciente': ['p1', 'p2', 'p3'],
        'registro': ['r1', 'r2', 'r3'],
        'clase_real': ['VT', 'Paced', 'Sinusal'],
        'clase_pred': ['Paced', 'Otro', 'Sinusal'],
        'prob_Sinusal': [0.05, 0.10, 0.80],
        'prob_SVT': [0.10, 0.10, 0.05],
        'prob_VT': [0.70, 0.20, 0.05],
        'prob_Paced': [0.10, 0.20, 0.05],
        'prob_Otro': [0.05, 0.40, 0.05],
    })
    gate = base[['window_id', 'paciente', 'registro', 'clase_real']].copy()
    gate['clase_pred'] = ['Paced', 'Paced', 'Sinusal']
    gate['prob_Paced'] = [0.90, 0.90, 0.01]
    combinado = combinar(base, gate)
    esperadas = ['VT', 'Paced', 'Sinusal']
    f1, _ = metricas(combinado)
    errores = []
    if combinado.clase_pred.tolist() != esperadas:
        errores.append('prioridad de especialistas incorrecta')
    if combinado.gate_paced_f20.tolist() != [True, True, False]:
        errores.append('gate Paced incorrecto')
    if combinado.gate_paced_aplicado.tolist() != [False, True, False]:
        errores.append('protección VT incorrecta')
    if any(f1[c] != 1.0 for c in ('Sinusal', 'VT', 'Paced')):
        errores.append('métricas sintéticas incorrectas')
    reporte = {'estado': 'FALLA' if errores else 'OK', 'errores': errores,
               'predicciones': combinado.clase_pred.tolist(),
               'test_consultado': False}
    print(json.dumps(reporte, indent=2))
    if errores:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
