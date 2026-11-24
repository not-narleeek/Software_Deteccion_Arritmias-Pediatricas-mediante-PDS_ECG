"""Evalúa late fusion: morfología 4 clases + gate Paced F20, sin test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


CLASES = ['Sinusal', 'SVT', 'VT', 'Paced', 'Otro']
CLASES_MORFOLOGIA = ['Sinusal', 'SVT', 'VT', 'Otro']


def combinar(pred_morfologia: pd.DataFrame,
             pred_paced: pd.DataFrame) -> pd.DataFrame:
    """Alinea ambos especialistas y aplica prioridad binaria a Paced."""
    requeridas = {'window_id', 'clase_real', 'clase_pred'}
    probs = {f'prob_{c}' for c in CLASES_MORFOLOGIA}
    if not requeridas | probs <= set(pred_morfologia.columns):
        raise ValueError('predicciones morfológicas incompletas')
    if not requeridas <= set(pred_paced.columns):
        raise ValueError('predicciones F20 incompletas')
    if pred_morfologia.window_id.duplicated().any():
        raise ValueError('window_id duplicado en morfología')
    if pred_paced.window_id.duplicated().any():
        raise ValueError('window_id duplicado en gate Paced')

    morf = pred_morfologia.set_index('window_id').sort_index()
    paced = pred_paced.set_index('window_id').sort_index()
    if not morf.index.equals(paced.index):
        faltan = len(morf.index.difference(paced.index))
        sobran = len(paced.index.difference(morf.index))
        raise ValueError(f'cobertura distinta: faltan={faltan}, sobran={sobran}')
    if not morf.clase_real.equals(paced.clase_real):
        raise ValueError('clase_real difiere entre especialistas')

    matriz_prob = morf[[f'prob_{c}' for c in CLASES_MORFOLOGIA]].to_numpy()
    pred_base = np.asarray(CLASES_MORFOLOGIA)[matriz_prob.argmax(axis=1)]
    gate = paced.clase_pred.eq('Paced').to_numpy()
    gate_aplicado = gate & (pred_base != 'VT')
    pred_final = pred_base.copy()
    pred_final[gate_aplicado] = 'Paced'

    salida = morf[['paciente', 'registro', 'clase_real']].copy()
    salida['clase_pred_morfologia'] = pred_base
    salida['gate_paced_f20'] = gate
    salida['proteccion_vt'] = gate & (pred_base == 'VT')
    salida['gate_paced_aplicado'] = gate_aplicado
    salida['clase_pred'] = pred_final
    if 'prob_Paced' in paced:
        salida['prob_paced_f20'] = paced.prob_Paced
    return salida.reset_index()


def metricas(pred: pd.DataFrame) -> tuple[dict[str, float], np.ndarray]:
    real = pred.clase_real.to_numpy()
    estimada = pred.clase_pred.to_numpy()
    matriz = np.zeros((len(CLASES), len(CLASES)), dtype=int)
    f1 = {}
    for i, clase in enumerate(CLASES):
        for j, otra in enumerate(CLASES):
            matriz[i, j] = int(((real == clase) & (estimada == otra)).sum())
        tp = matriz[i, i]
        fp = int(((real != clase) & (estimada == clase)).sum())
        fn = int(((real == clase) & (estimada != clase)).sum())
        f1[clase] = 0.0 if tp == 0 else float(2 * tp / (2 * tp + fp + fn))
    return f1, matriz


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predicciones-morfologia', type=Path, required=True)
    p.add_argument('--predicciones-paced', type=Path, required=True)
    p.add_argument('--salida', type=Path, required=True)
    p.add_argument('--matriz', type=Path, required=True)
    p.add_argument('--gate', type=Path, required=True)
    args = p.parse_args()

    pred = combinar(pd.read_csv(args.predicciones_morfologia),
                    pd.read_csv(args.predicciones_paced))
    f1, matriz = metricas(pred)
    macro = float(np.mean(list(f1.values())))
    criterios = {
        'macro_ge_0.4664': macro >= 0.4664,
        'paced_gt_0': f1['Paced'] > 0.0,
        'vt_ge_0.4115': f1['VT'] >= 0.4115,
    }
    reporte = {
        'estado': 'VERDE' if all(criterios.values()) else 'ROJO',
        'arquitectura': ('late fusion: argmax morfologia no-Paced + gate F20 '
                         'con prioridad VT'),
        'criterios': criterios,
        'f1_macro_val': macro,
        'f1_por_clase': f1,
        'gate_paced_positivos': int(pred.gate_paced_f20.sum()),
        'gate_paced_aplicados': int(pred.gate_paced_aplicado.sum()),
        'gate_paced_vetados_por_vt': int(pred.proteccion_vt.sum()),
        'test_consultado': False,
        'decision': ('confirmar semillas 42/73' if all(criterios.values())
                     else 'detener; no gastar mas GPU ni consultar test'),
    }
    for ruta in (args.salida, args.matriz, args.gate):
        ruta.parent.mkdir(parents=True, exist_ok=True)
    pred.to_csv(args.salida, index=False)
    pd.DataFrame(matriz, index=CLASES, columns=CLASES).to_csv(args.matriz)
    args.gate.write_text(json.dumps(reporte, indent=2) + '\n')
    print(json.dumps(reporte, indent=2))


if __name__ == '__main__':
    main()
