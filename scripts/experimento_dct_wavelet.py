"""Experimento F8 — cláusula justificar-o-sustituir DCT vs wavelet (F3-1).

El acta exige DCT (RF4) pero la revisión bibliográfica no halló soporte
sólido (vacío F3-1). Diseño §6: si la separabilidad del grupo wavelet
(db4 nivel 4) supera a la de la DCT, se sustituye y se documenta.

Criterio (objetivo 2 del acta): índice de Fisher medio por grupo +
f1_macro (CV agrupada por registro, SVM-RBF) usando solo el grupo en
cuestión junto al resto de features comunes.

Uso: uv run python scripts/experimento_dct_wavelet.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecg_pipeline import features, io  # noqa: E402
from sklearn.model_selection import GroupKFold, cross_val_score  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.svm import SVC  # noqa: E402

DATA = (
    ROOT / 'data'
    / 'leipzig-heart-center-ecg-database-arrhythmias-in-children-and-'
    'patients-with-congenital-heart-disease-1.0.0'
)
OUT = ROOT / 'results' / 'features'


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = features.construir_dataset(
        io.registros_dataset(DATA, pediatricos=True),
        cache=OUT / 'ventanas_features.csv',
    )
    df = df[df['clase'].isin(io.CLASES_PRIMARIAS)].reset_index(drop=True)
    print(f"\nDataset: {len(df)} ventanas ({df['clase'].value_counts().to_dict()})")

    base = [c for c in features.FEATURE_NAMES if not c.startswith('dct_')]
    dct = [f'dct_c{i}' for i in range(1, 9)]
    wav = list(features.NOMBRES_WAVELET)

    y = df['clase']
    grupos = df['registro']
    sep_base = features.separabilidad(df[base], y)
    sep_base.to_csv(OUT / 'separabilidad_base.csv', index=False)

    filas = []
    for nombre, grupo in (('dct', dct), ('wavelet', wav)):
        sep = features.separabilidad(df[grupo], y)
        fisher_medio = float(sep['fisher'].mean())
        # f1_macro con CV agrupada por registro (5 folds)
        X = df[base + grupo]
        pipe = Pipeline(
            [
                ('imp', SimpleImputer(strategy='median')),
                ('sc', StandardScaler()),
                ('svm', SVC(kernel='rbf', class_weight='balanced')),
            ]
        )
        gkf = GroupKFold(n_splits=5)
        f1 = cross_val_score(pipe, X, y, groups=grupos, cv=gkf, scoring='f1_macro')
        filas.append(
            {
                'grupo': nombre,
                'fisher_medio': fisher_medio,
                'fisher_max': float(sep['fisher'].max()),
                'f1_macro_media': float(f1.mean()),
                'f1_macro_std': float(f1.std()),
            }
        )
        print(f"{nombre:8s} Fisher_medio={fisher_medio:.4f}  Fisher_max={sep['fisher'].max():.4f}"
              f"  f1_macro={f1.mean():.4f} ± {f1.std():.4f}")
    res = pd.DataFrame(filas)
    res.to_csv(OUT / 'dct_vs_wavelet.csv', index=False)
    print("\nTop-15 separabilidad (base):")
    print(sep_base.head(15).to_string(index=False))
    reglas = res.set_index('grupo')
    decision = (
        'wavelet' if reglas.loc['wavelet', 'f1_macro_media'] > reglas.loc['dct', 'f1_macro_media']
        else 'dct'
    )
    (OUT / 'decision_dct_wavelet.txt').write_text(
        f"DECISION F8 (cláusula F3-1): grupo morfológico = {decision}\n"
        f"Criterio: f1_macro CV agrupada por registro\n{res.to_string(index=False)}\n"
        f"Fecha: 2026-09-09 (Etapa II, scripts/experimento_dct_wavelet.py)\n"
    )
    print(f"\nDECISIÓN: {decision} (ver results/features/decision_dct_wavelet.txt)")


if __name__ == '__main__':
    main()
