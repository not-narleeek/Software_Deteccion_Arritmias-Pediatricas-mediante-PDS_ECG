"""Extracción de características por ventana (RF4).

Contrato completo: docs/diseno_pipeline.md §6 — grupos RR (10), QRS (9),
onda P (3), espículas (2), espectrales (10), DCT (8), calidad (2),
demográficas (2). Dimensión total 46 antes de la reducción por separabilidad.
"""

import numpy as np
import pandas as pd

FEATURE_NAMES: tuple[str, ...] = ()  # se fija en la implementación; orden estable


def detectar_picos_r(x_filtrada: np.ndarray, fs: int = 977) -> np.ndarray:
    """Detector de picos R base Kathirvel 2011 (§4); fallback comparativo
    Pan-Tompkins con banda 8–20 Hz y refractario 120 ms.

    Returns: muestras de los picos R detectados en la ventana.
    KPI: Se/+P >= 95 % vs .atr (tolerancia ±100 ms) — se valida en
    scripts/validar_detector_r.py (Etapa II).
    """
    raise NotImplementedError


def vector_caracteristicas(
    ventana: np.ndarray,
    picos_r: np.ndarray,
    espiculas: np.ndarray,
    edad: float,
    sexo: int,
    fs: int = 977,
) -> dict[str, float]:
    """Calcula el vector §6 para una ventana.

    Args: ventana [n x 12] preprocesada; picos/espiculas en muestras;
    edad en años (NaN si desconocida, AP-10); sexo codificado 0/1.
    Returns: dict nombre→valor alineado con FEATURE_NAMES.
    """
    raise NotImplementedError


def separabilidad(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """ANOVA univariada + índice de Fisher por feature (objetivo 2 del acta).

    Returns: DataFrame [feature, F, p_valor, fisher] ordenado por Fisher.
    Regla de descarte (§6): p > 0.05 y Fisher nulo.
    """
    raise NotImplementedError
