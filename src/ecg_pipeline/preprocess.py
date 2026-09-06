"""Preprocesamiento: filtros, espículas y medición de distorsión QRS.

Contrato completo: docs/diseno_pipeline.md §3.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FilterSpec:
    """Especificación de la cadena de filtros (§3.1).

    hp_hz=0.5, notch_hz=50, notch_q=35, lp_hz=40, orden=4; fase cero
    (sosfiltfilt) obligatoria.
    """

    hp_hz: float = 0.5
    notch_hz: float = 50.0
    notch_q: float = 35.0
    lp_hz: float = 40.0
    orden: int = 4
    fs: int = 977


def preprocesar(x: np.ndarray, spec: FilterSpec = FilterSpec()) -> np.ndarray:
    """Aplica HP -> notch -> LP (fase cero) a la señal [n x 12].

    Invariante: misma forma y unidades que la entrada (mV físicos).
    """
    raise NotImplementedError


def detectar_espiculas(x_crudo: np.ndarray, fs: int = 977) -> np.ndarray:
    """Detecta espículas de marcapasos sobre copia sin filtrar (§3.2).

    Banda 80–250 Hz + umbral adaptativo; transientes < 10 ms.
    Returns: muestras (índices) de eventos espícula.
    """
    raise NotImplementedError


def documentar_respuesta(spec: FilterSpec = FilterSpec(), salida: str = 'results/figuras') -> None:
    """Genera módulo/fase vs frecuencia por filtro y tabla de ganancias
    en 0.5/40/49.5/50/50.5 Hz (RF2, §3.3)."""
    raise NotImplementedError


def distortion_qrs(x: np.ndarray, y: np.ndarray, picos_r: np.ndarray, fs: int = 977) -> dict[str, float]:
    """Distorsión del QRS tras el filtrado (KPI objetivo 1, §3.4).

    D = 100·||y−x||₂/||x||₂ en ventanas R±60 ms por latido.
    Returns: {'mediana_pct', 'p90_pct', 'delta_duracion_qrs_ms'}.
    Criterio: mediana < 5 % y p90 < 10 %.
    """
    raise NotImplementedError
