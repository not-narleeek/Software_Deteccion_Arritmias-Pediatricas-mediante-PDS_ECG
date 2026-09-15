"""Lectura WFDB y construcción del índice de ventanas etiquetadas.

Contrato completo: docs/diseno_pipeline.md §5 (segmentación 30 s / hop 15 s).
Implementación: Etapa II, hito F6.

El mapeo ritmo→clase replica `scripts/inventario.py` (decisiones AP-1/2/3,
pendientes de validación del experto): es el ÚNICO punto del pipeline que
depende de esa validación.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb

SURFACE = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

# Mapeo aux de '+' → clase (idéntico a scripts/inventario.py; AP-1/2/3).
CLASE = {
    '(N': 'Sinusal',
    '(AVRT': 'SVT', '(AVNRT': 'SVT', '(EAT': 'SVT', '(A': 'SVT', '(J': 'SVT', '(AFIB': 'SVT',
    '(VT': 'VT', '(IVR': 'VT',
    '(AFL': 'AFL',
    '(/A': 'Paced', '(/V': 'Paced',
    '(B': 'Otro',
}

# Clases con soporte suficiente para el clasificador primario (§5.1, AP-1).
CLASES_PRIMARIAS = ('Sinusal', 'SVT', 'Paced')

# Símbolos de anotación que marcan un latido (para validar el detector R, §4).
SIMBOLOS_LATIDO = frozenset({'N', 'L', 'R', 'a', 'A', 'J', 'V', 'F', 'f', 'X', '/', '/A', '/V', 'Q'})


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


def _indices_superficie(ruta: Path) -> list[int]:
    """Índices de las 12 derivaciones superficiales en el registro (de 19 canales)."""
    hdr = wfdb.rdheader(str(ruta))
    pos = {name: i for i, name in enumerate(hdr.sig_name)}
    return [pos[d] for d in SURFACE]


def cargar_registro(
    ruta: Path, derivaciones: list[str] | None = None
) -> tuple[np.ndarray, float, wfdb.Annotation]:
    """Lee un registro WFDB quedándose solo con las 12 derivaciones superficiales.

    Returns:
        (señal física [n_muestras x 12] en mV, fs, anotaciones .atr).
    """
    canales = _indices_superficie(ruta)
    if derivaciones is not None:
        pos = {d: i for i, d in enumerate(SURFACE)}
        sel = [canales[pos[d]] for d in derivaciones]
    else:
        sel = canales
    rec = wfdb.rdrecord(str(ruta), channels=sel, physical=True)
    ann = wfdb.rdann(str(ruta), 'atr')
    x = np.asarray(rec.p_signal, dtype=np.float32)
    return x, float(rec.fs), ann


def cargar_ventana_raw(ruta: Path, inicio: int, fin: int) -> np.ndarray:
    """Señal física cruda [n x 12] del tramo [inicio, fin) sin cargar el registro completo."""
    sel = _indices_superficie(ruta)
    rec = wfdb.rdrecord(str(ruta), sampfrom=int(inicio), sampto=int(fin), channels=sel, physical=True)
    return np.asarray(rec.p_signal, dtype=np.float32)


def _leer_anotaciones(ruta: Path) -> tuple[wfdb.Annotation, int, float]:
    ann = wfdb.rdann(str(ruta), 'atr')
    hdr = wfdb.rdheader(str(ruta))
    return ann, hdr.sig_len, float(hdr.fs)


def segmentos_ritmo(ruta: Path) -> pd.DataFrame:
    """Segmentos de ritmo de un registro desde anotaciones '+'.

    Returns: DataFrame [ritmo, clase, inicio_muestra, fin_muestra, duracion_s].
    El mapeo ritmo→clase es el de scripts/inventario.py (AP-1/2/3).
    """
    ann, sig_len, fs = _leer_anotaciones(ruta)
    idx = [i for i, (s, a) in enumerate(zip(ann.symbol, ann.aux_note)) if s == '+' and a.strip()]
    filas = []
    for j, i in enumerate(idx):
        ini = int(ann.sample[i])
        fin = int(ann.sample[idx[j + 1]]) if j + 1 < len(idx) else sig_len
        ritmo = ann.aux_note[i].strip()
        filas.append(
            {
                'ritmo': ritmo,
                'clase': CLASE.get(ritmo, 'Otro'),
                'inicio_muestra': ini,
                'fin_muestra': fin,
                'duracion_s': (fin - ini) / fs,
            }
        )
    return pd.DataFrame(filas)


def construir_indice_ventanas(registros: list[Path], spec: WindowSpec = WindowSpec()) -> pd.DataFrame:
    """Índice de ventanas de entrenamiento (§5.1).

    Una fila por ventana: registro, ritmo, clase, inicio_muestra, fin_muestra,
    calidad_dudosa (bool, AP-6: intersecta anotaciones '~').
    Solo ventanas íntegras dentro de un mismo segmento con margen_s en cada
    borde; segmentos más cortos que min_seg_s no generan ventanas.
    """
    filas = []
    for ruta in registros:
        ann, _, fs = _leer_anotaciones(ruta)
        segs = segmentos_ritmo(ruta)
        muestras_dudosas = ann.sample[np.asarray(ann.symbol) == '~']
        registro = ruta.name
        for _, seg in segs.iterrows():
            if seg['duracion_s'] < spec.min_seg_s:
                continue
            ini_util = int(seg['inicio_muestra'] + spec.margen_s * fs)
            fin_util = int(seg['fin_muestra'] - spec.margen_s * fs)
            dur = int(spec.dur_s * fs)
            hop = int(spec.hop_s * fs)
            ini = ini_util
            while ini + dur <= fin_util:
                fin = ini + dur
                dudosa = bool(
                    muestras_dudosas.size
                    and np.searchsorted(muestras_dudosas, fin) > np.searchsorted(muestras_dudosas, ini)
                )
                filas.append(
                    {
                        'registro': registro,
                        'ritmo': seg['ritmo'],
                        'clase': seg['clase'],
                        'inicio_muestra': ini,
                        'fin_muestra': fin,
                        'calidad_dudosa': dudosa,
                    }
                )
                ini += hop
    return pd.DataFrame(filas)


def cargar_ventana(ruta: Path, fila: pd.Series) -> np.ndarray:
    """Señal física de la ventana indicada por una fila del índice ([n x 12] mV).

    Nota: para el pipeline de inferencia conviene preprocesar el registro
    completo y rebanar (evita bordes de filtfilt); esta función existe para
    inspección y scripts ligeros.
    """
    return cargar_ventana_raw(ruta, int(fila['inicio_muestra']), int(fila['fin_muestra']))


def demografia(ruta_registro: Path) -> tuple[float, int]:
    """(edad_años, sexo 0=F 1=M) del registro desde los CSV oficiales del dataset.

    La edad corrupta de x007 ('.14.3', AP-10) se devuelve como NaN sin
    inventar el valor.
    """
    nombre = ruta_registro.name  # p. ej. 'x001' o 'x0014'
    csv_ped = ruta_registro.parent / 'children-subject-info.csv'
    csv_adu = ruta_registro.parent / 'adults-subject-info.csv'
    fila = None
    for csv in (csv_ped, csv_adu):
        df = pd.read_csv(csv, dtype={'file_name': str})
        hit = df[df['file_name'] == nombre]
        if not hit.empty:
            fila = hit.iloc[0]
            break
    if fila is None:
        raise KeyError(f'{nombre} no está en los CSV de sujetos')
    edad = pd.to_numeric(fila['age'], errors='coerce')  # NaN si corrupta (AP-10)
    sexo = 1 if str(fila['gender']).strip() == 'M' else 0
    return float(edad) if pd.notna(edad) else float('nan'), sexo


def registros_dataset(data_dir: Path, pediatricos: bool = True) -> list[Path]:
    """Rutas de registros (base, sin extensión) del dataset: x001–x0029 o x100–x109."""
    if pediatricos:  # convención del dataset: x001..x009, luego x0010..x0029
        return [data_dir / f'x00{i}' for i in range(1, 30)]
    return [data_dir / f'x{i}' for i in range(100, 110)]
