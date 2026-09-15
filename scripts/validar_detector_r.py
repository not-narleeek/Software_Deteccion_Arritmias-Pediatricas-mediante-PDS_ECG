"""Validador F7 — detección de picos R (RF3, KPI del acta).

Detector de producción: voto II+V2 con validación cruzada
(features.detectar_picos_r_fusion, implementación de §4). Comparadores:
Kathirvel ENLT en derivación II sola y Pan-Tompkins pediátrico.

KPI: sensibilidad y precisión positiva >= 95 % por registro y global,
coincidencia |t_det − t_ann| <= 100 ms contra todas las anotaciones de
latido del .atr. Exit != 0 si el detector de producción no lo cumple.

Uso: uv run python scripts/validar_detector_r.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecg_pipeline import io, preprocess, features  # noqa: E402

DATA = (
    ROOT / 'data'
    / 'leipzig-heart-center-ecg-database-arrhythmias-in-children-and-'
    'patients-with-congenital-heart-disease-1.0.0'
)
OUT = ROOT / 'results' / 'validacion_detector'


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    filas = []
    print(f"{'reg':7s} {'FUSION Se':>9s} {'+P':>6s} {'| II sola':>9s} {'+P':>6s} {'| PT':>6s} {'+P':>6s}  n_ann")
    tot = {'tp': 0, 'n_ann': 0, 'n_det': 0}
    for ruta in io.registros_dataset(DATA, pediatricos=True):
        x, fs, ann = io.cargar_registro(ruta)
        y = preprocess.preprocesar(x)
        sim = np.asarray(ann.symbol)
        mus = np.asarray(ann.sample)
        anot = mus[np.isin(sim, list(io.SIMBOLOS_LATIDO))]
        yf = y.astype(np.float64)
        k_fus = features.detectar_picos_r_fusion(yf, fs)
        k_ii = features.detectar_picos_r(yf[:, 1], fs, 'kathirvel')
        k_pt = features.detectar_picos_r(yf[:, 1], fs, 'pan_tompkins')
        e_f = features.evaluar_detector(k_fus, anot, fs)
        e_i = features.evaluar_detector(k_ii, anot, fs)
        e_p = features.evaluar_detector(k_pt, anot, fs)
        tot['tp'] += e_f['tp']
        tot['n_ann'] += e_f['n_anotados']
        tot['n_det'] += e_f['n_detectados']
        filas.append(
            {
                'registro': ruta.name,
                'fusion_se': e_f['sensibilidad'],
                'fusion_pp': e_f['precision_positiva'],
                'ii_se': e_i['sensibilidad'],
                'ii_pp': e_i['precision_positiva'],
                'pt_se': e_p['sensibilidad'],
                'pt_pp': e_p['precision_positiva'],
                'n_anotados': e_f['n_anotados'],
                'n_detectados': e_f['n_detectados'],
            }
        )
        print(f"{ruta.name:7s} {e_f['sensibilidad']:9.4f} {e_f['precision_positiva']:6.4f}"
              f" | {e_i['sensibilidad']:9.4f} {e_i['precision_positiva']:6.4f}"
              f" | {e_p['sensibilidad']:6.4f} {e_p['precision_positiva']:6.4f}  {anot.size}",
              flush=True)
    df = pd.DataFrame(filas)
    df.to_csv(OUT / 'detector_por_registro.csv', index=False)
    se_g = tot['tp'] / tot['n_ann']
    pp_g = tot['tp'] / tot['n_det']
    print(f"\nGLOBAL fusión II+V2: Se={se_g:.4f}  +P={pp_g:.4f}  "
          f"({tot['tp']} TP / {tot['n_ann']} anotados / {tot['n_det']} detectados)")
    fallos = df[(df['fusion_se'] < 0.95) | (df['fusion_pp'] < 0.95)]
    if se_g < 0.95 or pp_g < 0.95 or not fallos.empty:
        if not fallos.empty:
            print('\nRegistros bajo el KPI (< 95 %):')
            print(fallos.to_string(index=False))
        print('\nFALLO KPI detector R')
        sys.exit(1)
    print(f"KPI RF3 OK: Se y +P >= 95 % global y en los {len(df)} registros "
          f"(peor registro: Se {df['fusion_se'].min():.4f}, +P {df['fusion_pp'].min():.4f})")


if __name__ == '__main__':
    main()
