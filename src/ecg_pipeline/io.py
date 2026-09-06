"""Lectura WFDB y construcción del índice de ventanas etiquetadas.

Contrato completo: docs/diseno_pipeline.md §5 (segmentación 30 s / hop 15 s).
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SURFACE = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']


@dataclass(frozen=True)
class WindowSpec:
    """Especificación de ventaneo (§5.1 / §5.3).

    dur_s: duración de la ventana en segundos (30 entrenamiento, 10 caso).
    hop_s: paso entre ventanas consecutivas (15 entrenamiento, 5 caso).
    min_seg_s: duración mínima de segmento para generar ventanas (§5.1).
    margen_s: margen de seguridad a cada borde de transición de ritmo.
    """

    dur_s: int = 30
    hop_s: int = 15
    min_seg_s: int = 30
    margen_s: float = 1.0


def cargar_registro(ruta: Path, derivaciones: list[str] | None = None) -> tuple[np.ndarray, float, np.ndarray]:
    """Lee un registro WFDB quedándose solo con las 12 derivaciones superficiales.

    Returns:
        (señal física [n_muestras x 12], fs, anotaciones .atr como Record).
    """
    raise NotImplementedError


def segmentos_ritmo(ruta: Path) -> pd.DataFrame:
    """Segmentos de ritmo de un registro desde anotaciones '+'.

    Returns: DataFrame [ritmo, clase, inicio_muestra, fin_muestra, duracion_s].
    El mapeo ritmo→clase es el de scripts/inventario.py (AP-1/2/3).
    """
    raise NotImplementedError


def construir_indice_ventanas(registros: list[Path], spec: WindowSpec = WindowSpec()) -> pd.DataFrame:
    """Índice de ventanas de entrenamiento (§5.1).

    Una fila por ventana: registro, clase, inicio_muestra, fin_muestra,
    calidad_dudosa (bool, AP-6: intersecta anotaciones '~').
    Solo ventanas íntegras dentro de un mismo segmento, con margen.
    """
    raise NotImplementedError


def cargar_ventana(ruta: Path, fila: pd.Series) -> np.ndarray:
    """Señal física de la ventana indicada por una fila del índice (12 x n)."""
    raise NotImplementedError
