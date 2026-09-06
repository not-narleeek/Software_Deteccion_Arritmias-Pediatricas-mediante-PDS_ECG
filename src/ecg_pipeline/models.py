"""Clasificación, calibración y validación LORO anidada.

Contrato completo: docs/diseno_pipeline.md §7–§8.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


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
    grilla_svm: tuple[tuple[float, ...], tuple[float, ...]] = ((0.1, 1, 10, 100), (1e-4, 1e-3, 1e-2, 1e-1))
    grilla_rf: tuple[tuple[int, ...], tuple[int, ...]] = ((200, 500), (None, 5, 10))


def entrenar_calibrado(X: np.ndarray, y: np.ndarray, grupos: np.ndarray, spec: ExperimentSpec = ExperimentSpec()):
    """Entrena el modelo con calibración Platt, seleccionando hiperparámetros
    con GroupKFold por registro SOLO dentro del training set (§8.1).

    Returns: estimador ajustado (pipeline escalado + modelo calibrado).
    """
    raise NotImplementedError


def validacion_loro(X: pd.DataFrame, y: pd.Series, registros: pd.Series, spec: ExperimentSpec = ExperimentSpec()) -> dict:
    """Leave-one-record-out anidado sobre los 29 registros (§8.1).

    Returns: {'metricas_por_clase', 'macro', 'brier_multiclase',
    'matriz_confusion_ventanas', 'matriz_confusion_registros', 'ic_bootstrap'}.
    KPI (§8.2): Se/Sp global >= 85 %, F1 por clase >= 0.80 (3 clases primarias).
    """
    raise NotImplementedError


def curvas_confiabilidad(y_true: np.ndarray, p_proba: np.ndarray) -> dict:
    """Diagramas de confiabilidad por clase (§8.3)."""
    raise NotImplementedError
