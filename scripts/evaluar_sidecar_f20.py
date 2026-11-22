"""Screening CPU del sidecar ZZU antes de autorizar GPU F20."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'src'))

from ecg_pipeline.pacing import FEATURES_HF  # noqa: E402


DL = RAIZ / 'results' / 'dl'


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sidecar', type=Path, default=DL / 'sidecar_hf_train_val.csv')
    p.add_argument('--manifiesto', type=Path, default=DL / 'manifiesto.csv')
    p.add_argument('--splits', type=Path, default=DL / 'splits.csv')
    p.add_argument('--salida', type=Path, default=DL / 'f20_sidecar_screening.json')
    p.add_argument('--predicciones', type=Path,
                   default=DL / 'f20_sidecar_predicciones_val.csv')
    p.add_argument('--distribuciones', type=Path,
                   default=DL / 'f20_sidecar_distribuciones.csv')
    args = p.parse_args()

    side = pd.read_csv(args.sidecar)
    man = pd.read_csv(args.manifiesto)
    splits = pd.read_csv(args.splits, index_col=0)['particion']
    man = man.merge(splits, left_on='paciente', right_index=True,
                    validate='many_to_one')
    datos = side.merge(man[['window_id', 'clase']], on='window_id',
                       validate='one_to_one')
    train = datos[datos.particion.eq('train')].copy()
    val = datos[datos.particion.eq('val')].copy()
    features = list(FEATURES_HF)
    modelo = RandomForestClassifier(
        n_estimators=400, max_depth=7, min_samples_leaf=5,
        class_weight='balanced_subsample', random_state=20, n_jobs=-1,
    )
    modelo.fit(train[features], train.clase.eq('Paced'))
    prob = modelo.predict_proba(val[features])[:, 1]
    pred = prob >= 0.5
    real = val.clase.eq('Paced').to_numpy()
    tn, fp, fn, tp = confusion_matrix(real, pred, labels=[False, True]).ravel()
    sensibilidad = recall_score(real, pred, zero_division=0)
    resultado = {
        'estado': 'VERDE' if sensibilidad > 0 else 'ROJO',
        'protocolo': 'RF HF train -> val fija; umbral 0.5; sin test',
        'f1_paced_binario_val': float(f1_score(real, pred, zero_division=0)),
        'precision': float(precision_score(real, pred, zero_division=0)),
        'sensibilidad': float(sensibilidad),
        'especificidad': float(tn / (tn + fp)),
        'auc_roc': float(roc_auc_score(real, prob)),
        'matriz_confusion': [[int(tn), int(fp)], [int(fn), int(tp)]],
        'paced_train': int(train.clase.eq('Paced').sum()),
        'paced_val': int(val.clase.eq('Paced').sum()),
        'test_consultado': False,
        'decision': ('habilitar humo GPU' if sensibilidad > 0 else
                     'revisar etiqueta P05649 antes de usar GPU'),
    }
    predicciones = val[['window_id', 'paciente', 'registro', 'clase']].copy()
    predicciones['prob_paced_hf'] = prob
    predicciones['pred_paced_hf'] = pred
    predicciones.to_csv(args.predicciones, index=False)

    grupos = datos.copy()
    grupos['grupo_hf'] = 'No paced desarrollo'
    grupos.loc[(grupos.clase.eq('Paced')) & (grupos.particion.eq('train')),
               'grupo_hf'] = 'Paced train'
    grupos.loc[(grupos.clase.eq('Paced')) & (grupos.particion.eq('val')),
               'grupo_hf'] = 'Paced val activo'
    distribuciones = grupos.groupby('grupo_hf')[features].agg(
        ['count', 'median', lambda x: x.quantile(.1), lambda x: x.quantile(.9)])
    distribuciones.to_csv(args.distribuciones)
    args.salida.write_text(json.dumps(resultado, indent=2) + '\n')
    print(json.dumps(resultado, indent=2))


if __name__ == '__main__':
    main()
