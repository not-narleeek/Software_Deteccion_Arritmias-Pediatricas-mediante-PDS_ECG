"""Lectura WFDB del corpus ZZU pECG y construcción del índice de ventanas.

Contrato completo: docs/diseno_pipeline.md §5 e
docs/etapa1_zzu_pecg.md §4 (ventanas 10 s / hop 5 s, etiqueta por
registro). Implementación: Etapa I-bis/II, hitos F11+.

Decisiones AP-1/2/3 (mapeo de clases) pendientes de validación del
experto; el único punto del pipeline que depende de esa validación es
`scripts/inventario_zzu.py`.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb

SURFACE = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

# Clases con soporte suficiente para el clasificador primario (§5.1; AP-1
# + Etapa I-bis §4.5: VT asciende a clase con el corpus ZZU — 435 ventanas).
CLASES_PRIMARIAS = ('Sinusal', 'SVT', 'VT', 'Paced')


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


# Nomenclatura ZZU: derivaciones unipolares en MAYÚSCULAS ('AVR'...) —
# se normaliza al leer.
_NORMALIZA = {'AVR': 'aVR', 'AVL': 'aVL', 'AVF': 'aVF', 'I': 'I', 'II': 'II',
              'III': 'III', 'V1': 'V1', 'V2': 'V2', 'V3': 'V3', 'V4': 'V4',
              'V5': 'V5', 'V6': 'V6'}

_ZZU_RUTAS: dict[str, Path] | None = None


def rutas_zzu() -> dict[str, Path]:
    """{ECG_ID: ruta base} de todos los registros ZZU (cacheado)."""
    global _ZZU_RUTAS
    if _ZZU_RUTAS is None:
        raiz = Path(__file__).resolve().parents[2] / 'data' / 'zzu_pecg' / 'Child_ecg'
        _ZZU_RUTAS = {p.stem: p.parent for p in raiz.rglob('*.hea')}
    return _ZZU_RUTAS


def reordenar_superficie(x: np.ndarray, nombres: list[str]) -> tuple[np.ndarray, list[str]]:
    """Reordena [n x k] al orden SURFACE; derivaciones ausentes quedan en 0.0.

    Los registros ZZU de 9 derivaciones (< 7 años) traen V1/V3/V5 en lugar
    de V2/V4/V6: las ausentes se rellenan con ceros (columna muerta, sin
    NaN que envenenaría los filtros) y el llamador decide la derivación de
    fusión del detector según `presentes` (V2 si está, si no V1 — §4.3).
    """
    pos = {_NORMALIZA.get(n, n): j for j, n in enumerate(nombres)}
    out = np.zeros((x.shape[0], len(SURFACE)), dtype=np.float32)
    for i, d in enumerate(SURFACE):
        if d in pos:
            out[:, i] = x[:, pos[d]]
    return out, [d for d in SURFACE if d in pos]


def cargar_registro_zzu(ecg_id: str) -> tuple[np.ndarray, float, list[str]]:
    """Registro ZZU como [n x 12] en orden SURFACE (mV), fs y presentes."""
    ruta = rutas_zzu()[ecg_id]
    rec = wfdb.rdrecord(str(ruta / ecg_id))
    x, presentes = reordenar_superficie(rec.p_signal, list(rec.sig_name))
    return x, float(rec.fs), presentes


def construir_indice_ventanas_zzu(
    qc_csv: Path, spec: WindowSpec = WindowSpec()
) -> pd.DataFrame:
    """Índice de ventanas del corpus ZZU desde el QC (Etapa I-bis §2/§4.4).

    Solo supervivientes del QC (causa_exclusion vacía); la ventana hereda
    la clase del registro (etiqueta por registro completo, sin `.atr`);
    margen 0 (el registro entero es el segmento); calidad_dudosa = bSQI
    bajo o artefacto en derivaciones no críticas (marcas, no exclusiones).
    """
    qc = pd.read_csv(qc_csv)
    qc = qc[qc.causa_exclusion.isna() | (qc.causa_exclusion == '')]
    filas = []
    for _, r in qc.iterrows():
        fs = 500.0
        dur = int(spec.dur_s * fs)
        hop = int(spec.hop_s * fs)
        dudosa = bool(r.get('calidad_dudosa', False) or r.get('artefacto_otras_deriv', False))
        ini = 0
        while ini + dur <= r.duracion_s_qc * fs:
            filas.append({
                'registro': r.registro, 'fuente': 'zzu', 'paciente': r.paciente,
                'ritmo': 'zzu_registro', 'clase': r.clase,
                'edad_anos': r.edad_anos,
                'sexo': 1 if str(r.sexo).strip() == 'Male' else 0,
                'inicio_muestra': ini, 'fin_muestra': ini + dur,
                'calidad_dudosa': dudosa,
            })
            ini += hop
    return pd.DataFrame(filas)
