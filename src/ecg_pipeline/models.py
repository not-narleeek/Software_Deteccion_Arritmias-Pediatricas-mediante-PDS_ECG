"""Clasificación, calibración y validación LORO anidada.

Contrato completo: docs/diseno_pipeline.md §7–§8. Implementación: Etapa II, F9.

- SVM-RBF primario / Random Forest comparador, ambos con class_weight
  balanceado y calibración Platt (sigmoid).
- Selección de hiperparámetros SOLO en folds internos agrupados por
  registro (GroupKFold) dentro de cada fold LORO externo (§8.1, Cawley).
- Reducción de features por separabilidad (§6) re-ajustada en cada fold
  (SelectorAnova: p > 0.05 o Fisher < 1e-6 se descartan).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import f_classif
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    brier_score_loss,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.base import BaseEstimator, TransformerMixin, clone


@dataclass(frozen=True)
class ExperimentSpec:
    """Configuración de un experimento (§7, §8).

    modelo: 'svm' (primario) | 'rf' (comparador obligatorio).
    calibracion: 'sigmoid' (Platt) — isónica solo como experimento extra.
    grillas mínimas explícitas; selección SOLO en folds internos.
    """

    modelo: str = 'svm'
    calibracion: str = 'sigmoid'
    grupo_kfolds: int = 4
    grilla_svm: tuple[tuple[float, ...], tuple[float, ...]] = (
        (0.1, 1, 10, 100),
        (1e-4, 1e-3, 1e-2, 1e-1),
    )
    grilla_rf: tuple[tuple[int, ...], tuple[int, ...]] = ((200, 500), (None, 5, 10))


class SelectorAnova(BaseEstimator, TransformerMixin):
    """Descarta features con ANOVA p > umbral o Fisher < min_fisher (§6).

    Se ajusta dentro de cada fold de entrenamiento (§8.1).
    """

    def __init__(self, p_umbral: float = 0.05, min_fisher: float = 1e-6) -> None:
        self.p_umbral = p_umbral
        self.min_fisher = min_fisher

    def fit(self, X: np.ndarray, y: np.ndarray):
        X = np.asarray(X, dtype=float)
        self.mascara_ = np.ones(X.shape[1], dtype=bool)
        if X.shape[1] == 0:
            return self
        Xi = np.nan_to_num(X, nan=np.nanmedian(X, axis=0))
        F, p = f_classif(Xi, y)
        mu = Xi.mean(axis=0)
        clases = np.unique(y)
        for j in range(X.shape[1]):
            entre = intra = 0.0
            for c in clases:
                xc = Xi[y == c, j]
                if xc.size == 0:
                    continue
                entre += xc.size * (xc.mean() - mu[j]) ** 2
                intra += xc.size * (xc.var(ddof=1) if xc.size > 1 else 0.0)
            fisher = entre / intra if intra > 0 else 0.0
            self.mascara_[j] = bool(np.isfinite(p[j]) and p[j] <= self.p_umbral and fisher >= self.min_fisher)
        self.n_features_out_ = int(self.mascara_.sum())
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(X, dtype=float)[:, self.mascara_]


def _pipeline_base(spec: ExperimentSpec) -> Pipeline:
    if spec.modelo == 'svm':
        clf = SVC(kernel='rbf', class_weight='balanced', probability=False)
    elif spec.modelo == 'rf':
        clf = RandomForestClassifier(
            n_estimators=300, class_weight='balanced_subsample', random_state=42, n_jobs=-1
        )
    else:
        raise ValueError(f'modelo desconocido: {spec.modelo}')
    return Pipeline(
        [
            ('imp', SimpleImputer(strategy='median')),
            ('sel', SelectorAnova()),
            ('sc', StandardScaler()),
            ('clf', clf),
        ]
    )


def _grilla(spec: ExperimentSpec) -> dict:
    if spec.modelo == 'svm':
        cs, gs = spec.grilla_svm
        return {'clf__C': list(cs), 'clf__gamma': list(gs)}
    ns, ds = spec.grilla_rf
    return {'clf__n_estimators': list(ns), 'clf__max_depth': list(ds)}


def entrenar_calibrado(
    X: np.ndarray, y: np.ndarray, grupos: np.ndarray, spec: ExperimentSpec = ExperimentSpec()
):
    """Entrena el modelo con calibración Platt, seleccionando hiperparámetros
    con GroupKFold por registro SOLO dentro del training set (§8.1).

    Returns: estimador ajustado (SVC/RF calibrado; predict_proba disponible).
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    grupos = np.asarray(grupos)
    pipe = _pipeline_base(spec)
    folds_internos = list(GroupKFold(n_splits=spec.grupo_kfolds).split(X, y, grupos))
    gs = GridSearchCV(
        pipe, _grilla(spec), cv=folds_internos, scoring='f1_macro', n_jobs=-1
    )
    gs.fit(X, y)
    mejor = _pipeline_base(spec).set_params(**gs.best_params_)
    calibrado = CalibratedClassifierCV(
        mejor, method=spec.calibracion, cv=list(GroupKFold(n_splits=spec.grupo_kfolds).split(X, y, grupos))
    )
    calibrado.fit(X, y)
    return calibrado


def _metricas_clase(y_true: np.ndarray, y_pred: np.ndarray, clases: np.ndarray) -> dict:
    out: dict[str, dict[str, float]] = {}
    for c in clases:
        tp = np.sum((y_pred == c) & (y_true == c))
        fn = np.sum((y_pred != c) & (y_true == c))
        fp = np.sum((y_pred == c) & (y_true != c))
        tn = np.sum((y_pred != c) & (y_true != c))
        se = tp / (tp + fn) if tp + fn else float('nan')
        sp = tn / (tn + fp) if tn + fp else float('nan')
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else float('nan')
        out[str(c)] = {'sensibilidad': float(se), 'especificidad': float(sp), 'f1': float(f1),
                       'soporte': int(tp + fn)}
    return out


def _voto_mayoritario(df_pred: pd.DataFrame) -> pd.DataFrame:
    """Predicción por (registro, clase real) por voto mayoritario (§8.2)."""
    filas = []
    for (reg, real), g in df_pred.groupby(['registro', 'clase_real']):
        pred = g['clase_pred'].value_counts().idxmax()
        filas.append({'registro': reg, 'clase_real': real, 'clase_pred': pred, 'n_ventanas': len(g)})
    return pd.DataFrame(filas)


def validacion_loro(
    X: pd.DataFrame, y: pd.Series, registros: pd.Series, spec: ExperimentSpec = ExperimentSpec()
) -> dict:
    """Leave-one-record-out anidado sobre los registros presentes (§8.1).

    Returns: {'metricas_por_clase', 'macro', 'brier_multiclase',
    'matriz_confusion_ventanas', 'matriz_confusion_registros', 'ic_bootstrap',
    'predicciones'} (predicciones: DataFrame por ventana para confiabilidad).
    KPI (§8.2): Se/Sp global >= 85 %, F1 por clase >= 0.80 (3 clases primarias).
    """
    Xv = X.to_numpy(dtype=float)
    yv = y.to_numpy()
    clases = np.unique(yv)
    regs = registros.to_numpy()
    y_true, y_pred, probas, reg_col = [], [], [], []
    for r in np.unique(regs):
        te = regs == r
        tr = ~te
        modelo = entrenar_calibrado(Xv[tr], yv[tr], regs[tr], spec)
        proba = modelo.predict_proba(Xv[te])
        pred = clases[np.argmax(proba, axis=1)]
        y_true.extend(yv[te])
        y_pred.extend(pred)
        probas.append(proba)
        reg_col.extend([r] * int(te.sum()))
        print(f'    fold {r}: n_test={int(te.sum())}', flush=True)
    return _resultado(y_true, y_pred, probas, reg_col)


def _resultado(
    y_true: np.ndarray, y_pred: np.ndarray, probas: np.ndarray, reg_col: list,
) -> dict:
    """Ensamblado común de métricas (§8.2) para cualquier esquema de folds."""
    clases = np.unique(y_true)
    df_pred = pd.DataFrame(
        {'registro': reg_col, 'clase_real': y_true, 'clase_pred': y_pred}
    )
    metricas = _metricas_clase(y_true, y_pred, clases)
    macro = {
        m: float(np.nanmean([v[m] for v in metricas.values()]))
        for m in ('sensibilidad', 'especificidad', 'f1')
    }
    brier = float(
        np.mean(
            [brier_score_loss((y_true == c).astype(int), probas[:, j]) for j, c in enumerate(clases)]
        )
    )
    rng = np.random.default_rng(42)
    regs_unicos = np.unique(reg_col)
    idx_por_reg = {r: np.flatnonzero(np.asarray(reg_col) == r) for r in regs_unicos}
    macros = []
    for _ in range(1000):
        muestra = rng.choice(regs_unicos, size=regs_unicos.size, replace=True)
        idx = np.concatenate([idx_por_reg[r] for r in muestra])
        met = _metricas_clase(y_true[idx], y_pred[idx], clases)
        macros.append(np.nanmean([v['f1'] for v in met.values()]))
    ic = {'f1_macro_p2.5': float(np.percentile(macros, 2.5)),
          'f1_macro_p97.5': float(np.percentile(macros, 97.5))}
    voto = _voto_mayoritario(df_pred)
    return {
        'metricas_por_clase': metricas,
        'macro': macro,
        'brier_multiclase': brier,
        'matriz_confusion_ventanas': confusion_matrix(y_true, y_pred, labels=clases).tolist(),
        'matriz_confusion_registros': confusion_matrix(
            voto['clase_real'], voto['clase_pred'], labels=clases).tolist(),
        'clases': clases.tolist(),
        'ic_bootstrap': ic,
        'predicciones': df_pred.assign(**{
            f'proba_{c}': probas[:, j] for j, c in enumerate(clases)
        }),
        'probas': probas,
        'y_true': y_true,
    }


def validacion_grupos(
    X: pd.DataFrame, y: pd.Series, grupos: pd.Series, k: int = 5,
    spec: ExperimentSpec = ExperimentSpec(),
) -> dict:
    """Validación cruzada GroupKFold anidada por PACIENTE (corpus ZZU,
    Etapa II/F14). Sustituye al LORO por registro cuando hay miles de
    registros: k folds externos por paciente, selección de hiperparámetros
    en folds internos agrupados (§8.1). Mismo ensamblado de métricas §8.2.
    """
    Xv = X.to_numpy(dtype=float)
    yv = y.to_numpy()
    gv = grupos.to_numpy()
    clases = np.unique(yv)
    y_true, y_pred, probas, reg_col = [], [], [], []
    for i, (tr, te) in enumerate(GroupKFold(n_splits=k).split(Xv, yv, gv), 1):
        modelo = entrenar_calibrado(Xv[tr], yv[tr], gv[tr], spec)
        proba = modelo.predict_proba(Xv[te])
        pred = clases[np.argmax(proba, axis=1)]
        y_true.extend(yv[te])
        y_pred.extend(pred)
        probas.append(proba)
        reg_col.extend(gv[te].tolist())
        print(f'    fold {i}/{k}: n_test={int(te.sum())}', flush=True)
    return _resultado(
        np.asarray(y_true), np.asarray(y_pred), np.vstack(probas), reg_col)


def curvas_confiabilidad(y_true: np.ndarray, p_proba: np.ndarray) -> dict:
    """Diagramas de confiabilidad por clase (§8.3).

    Returns: {clase: {'fraccion_positivos': [...], 'confianza_media': [...],
    'n_por_bin': [...], 'brier': float}} con 10 bins equipoblados por cuantiles.
    """
    clases = np.unique(y_true)
    out: dict = {}
    for j, c in enumerate(clases):
        binaria = (y_true == c).astype(int)
        conf = p_proba[:, j]
        qs = np.quantile(conf, np.linspace(0, 1, 11))
        qs[0], qs[-1] = -np.inf, np.inf
        fr, cm, nb = [], [], []
        for b in range(10):
            m = (conf > qs[b]) & (conf <= qs[b + 1])
            if m.sum() < 5:
                continue
            fr.append(float(binaria[m].mean()))
            cm.append(float(conf[m].mean()))
            nb.append(int(m.sum()))
        out[str(c)] = {
            'fraccion_positivos': fr,
            'confianza_media': cm,
            'n_por_bin': nb,
            'brier': float(brier_score_loss(binaria, conf)),
        }
    return out
