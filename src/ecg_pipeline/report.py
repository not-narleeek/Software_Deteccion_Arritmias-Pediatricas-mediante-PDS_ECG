"""Reporte de diagnóstico con certeza calibrada (RF6).

Contrato completo: docs/diseno_pipeline.md §8.3.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Diagnostico:
    """Resultado por ventana: clase + probabilidad calibrada por clase.

    Invariante: probs suma 1.0 (post-calibración renormalizada);
    'advertencias' lista limitaciones aplicables (ventana calidad_dudosa
    AP-6, clase con soporte escaso, etc.).
    """

    clase: str
    probs: dict[str, float]
    advertencias: tuple[str, ...] = ()


def reportar(probs: np.ndarray, clases: tuple[str, ...], advertencias: tuple[str, ...] = ()) -> Diagnostico:
    """Construye el Diagnostico desde las probabilidades calibradas de una ventana."""
    raise NotImplementedError
