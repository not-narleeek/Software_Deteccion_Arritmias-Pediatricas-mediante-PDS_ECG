"""Evalúa si PTB-XL aporta señal de alta frecuencia útil para detectar PACE.

La evaluación es interna al dataset adulto externo, agrupada por paciente y
sin edad, sexo ni metadatos clínicos como variables. No consulta ZZU ni cambia
el clasificador multiclase. Su propósito es decidir si vale la pena una rama
auxiliar de espículas antes de entrenar en GPU.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedGroupKFold


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'src'))

from ecg_pipeline.pacing import FEATURES_HF, extraer_features_hf  # noqa: E402


FEATURES = list(FEATURES_HF)


def argumentos() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifiesto', type=Path,
                   default=RAIZ / 'results/dl/f19_datasets/ptbxl_manifest.csv')
    p.add_argument('--salida', type=Path,
                   default=RAIZ / 'results/dl/f19_datasets')
    p.add_argument('--leipzig-manifiesto', type=Path,
                   default=RAIZ / 'results/dl/f19_datasets/leipzig_manifest.csv')
    p.add_argument('--recalcular', action='store_true')
    return p.parse_args()


def extraer_array(x: np.ndarray, fs: int) -> dict[str, float]:
    return extraer_features_hf(x, fs)


def extraer(ruta_base: Path, fs: int) -> dict[str, float]:
    rec = wfdb.rdrecord(str(ruta_base), physical=True)
    return extraer_array(rec.p_signal, fs)


def construir_features(man: pd.DataFrame, destino: Path) -> pd.DataFrame:
    filas = []
    for i, (_, r) in enumerate(man.iterrows(), 1):
        f = extraer(RAIZ / str(r.ruta_base), int(r.fs_hz))
        filas.append({
            'dataset': r.dataset,
            'registro': r.registro,
            'paciente': r.paciente,
            'y_paced': int(r.rol == 'paced'),
            **f,
        })
        if i % 50 == 0:
            print(f'features {i}/{len(man)}', flush=True)
    features = pd.DataFrame(filas)
    features.to_csv(destino, index=False)
    return features


def evaluar(features: pd.DataFrame) -> dict:
    x = features[FEATURES].to_numpy(dtype=np.float64)
    y = features.y_paced.to_numpy(dtype=int)
    grupos = features.paciente.to_numpy()
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=19)
    proba = np.zeros(len(features), dtype=np.float64)
    pred = np.zeros(len(features), dtype=int)
    folds = []
    for fold, (tr, va) in enumerate(cv.split(x, y, grupos), 1):
        modelo = RandomForestClassifier(
            n_estimators=300,
            max_depth=6,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=100 + fold,
            n_jobs=-1,
        )
        modelo.fit(x[tr], y[tr])
        proba[va] = modelo.predict_proba(x[va])[:, 1]
        pred[va] = (proba[va] >= 0.5).astype(int)
        folds.append({
            'fold': fold,
            'registros': int(len(va)),
            'pacientes': int(len(set(grupos[va]))),
            'f1': float(f1_score(y[va], pred[va], zero_division=0)),
            'sensibilidad': float(recall_score(y[va], pred[va], zero_division=0)),
            'auc_roc': float(roc_auc_score(y[va], proba[va])),
        })
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        'protocolo': '5-fold StratifiedGroupKFold por paciente; solo señal',
        'n_registros': int(len(features)),
        'n_pacientes': int(features.paciente.nunique()),
        'f1_paced': float(f1_score(y, pred, zero_division=0)),
        'precision_paced': float(precision_score(y, pred, zero_division=0)),
        'sensibilidad_paced': float(recall_score(y, pred, zero_division=0)),
        'especificidad': float(tn / (tn + fp)),
        'auc_roc': float(roc_auc_score(y, proba)),
        'matriz_confusion': [[int(tn), int(fp)], [int(fn), int(tp)]],
        'folds': folds,
        'test_zzu_consultado': False,
    }


def _muestra_uniforme(valores: list[int], limite: int = 10) -> list[int]:
    if len(valores) <= limite:
        return valores
    pos = np.linspace(0, len(valores) - 1, limite).round().astype(int)
    return [valores[i] for i in pos]


def construir_features_leipzig(man: pd.DataFrame, destino: Path) -> pd.DataFrame:
    """Hasta 10 ventanas positivas y 10 negativas por paciente Leipzig."""
    filas = []
    seleccion = man[man.tiene_senal.astype(bool)].sort_values('registro')
    for i, (_, r) in enumerate(seleccion.iterrows(), 1):
        base = RAIZ / str(r.ruta_base)
        h = wfdb.rdheader(str(base))
        if list(h.sig_name[:12]) != [
            'I', 'II', 'III', 'aVR', 'aVL', 'aVF',
            'V1', 'V2', 'V3', 'V4', 'V5', 'V6',
        ]:
            raise ValueError(f'orden de superficie inesperado en {r.registro}')
        fs = int(h.fs)
        largo = fs * 10
        ann = wfdb.rdann(str(base), 'atr')
        muestras_paced = np.asarray([
            s for s, simbolo in zip(ann.sample, ann.symbol)
            if simbolo in ('/', 'f')
        ], dtype=int)
        positivos: list[int] = []
        negativos: list[int] = []
        for inicio in range(0, h.sig_len - largo + 1, largo):
            tiene = bool(np.any((muestras_paced >= inicio)
                                & (muestras_paced < inicio + largo)))
            (positivos if tiene else negativos).append(inicio)
        ventanas = ([(j, 1) for j in _muestra_uniforme(positivos)]
                    + [(j, 0) for j in _muestra_uniforme(negativos)])
        for inicio, y in ventanas:
            rec = wfdb.rdrecord(str(base), sampfrom=inicio,
                                sampto=inicio + largo, channels=list(range(12)),
                                physical=True)
            filas.append({
                'dataset': 'leipzig-heart-center-ecg',
                'registro': r.registro,
                'paciente': r.paciente,
                'grupo': r.grupo,
                'inicio_muestra': inicio,
                'y_paced': y,
                **extraer_array(rec.p_signal, fs),
            })
        print(f'leipzig {i}/{len(seleccion)}: {r.registro} '
              f'({len(ventanas)} ventanas)', flush=True)
    features = pd.DataFrame(filas)
    features.to_csv(destino, index=False)
    return features


def evaluar_transferencia(train: pd.DataFrame, externo: pd.DataFrame) -> dict:
    modelo = RandomForestClassifier(
        n_estimators=500,
        max_depth=6,
        min_samples_leaf=5,
        class_weight='balanced',
        random_state=19,
        n_jobs=-1,
    )
    modelo.fit(train[FEATURES], train.y_paced)
    proba = modelo.predict_proba(externo[FEATURES])[:, 1]
    pred = (proba >= 0.5).astype(int)
    y = externo.y_paced.to_numpy(dtype=int)

    def metricas(mask: np.ndarray) -> dict:
        yy, pp, pr = y[mask], pred[mask], proba[mask]
        tn, fp, fn, tp = confusion_matrix(yy, pp, labels=[0, 1]).ravel()
        return {
            'ventanas': int(mask.sum()),
            'positivas': int(yy.sum()),
            'f1_paced': float(f1_score(yy, pp, zero_division=0)),
            'precision_paced': float(precision_score(yy, pp, zero_division=0)),
            'sensibilidad_paced': float(recall_score(yy, pp, zero_division=0)),
            'especificidad': float(tn / (tn + fp)) if tn + fp else None,
            'auc_roc': float(roc_auc_score(yy, pr)) if len(set(yy)) == 2 else None,
            'matriz_confusion': [[int(tn), int(fp)], [int(fn), int(tp)]],
        }

    grupos = externo.grupo.to_numpy()
    return {
        'protocolo': ('RF ajustado en todo PTB-XL seleccionado; umbral 0.5 fijo; '
                      'transferencia sin ajuste a Leipzig'),
        'global': metricas(np.ones(len(externo), dtype=bool)),
        'pediatrico': metricas(grupos == 'pediatrico'),
        'adulto_chd': metricas(grupos == 'adulto_chd'),
        'test_zzu_consultado': False,
    }


def main() -> None:
    args = argumentos()
    args.salida.mkdir(parents=True, exist_ok=True)
    man = pd.read_csv(args.manifiesto)
    if not man.tiene_senal.astype(bool).all():
        raise SystemExit('faltan señales PTB-XL; ejecute F19 con --descargar-senales')
    destino_features = args.salida / 'ptbxl_features_hf.csv'
    if destino_features.exists() and not args.recalcular:
        features = pd.read_csv(destino_features)
    else:
        features = construir_features(man, destino_features)
    resultado = evaluar(features)
    leipzig_man = pd.read_csv(args.leipzig_manifiesto)
    destino_leipzig = args.salida / 'leipzig_features_hf.csv'
    if destino_leipzig.exists() and not args.recalcular:
        features_leipzig = pd.read_csv(destino_leipzig)
    else:
        features_leipzig = construir_features_leipzig(leipzig_man,
                                                       destino_leipzig)
    transferencia = evaluar_transferencia(features, features_leipzig)
    resultado['transferencia_ptb_a_leipzig'] = transferencia
    (args.salida / 'baseline_hf_ptbxl.json').write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
