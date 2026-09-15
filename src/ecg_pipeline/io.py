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

# Clases con soporte suficiente para el clasificador primario (§5.1; AP-1
# + Etapa I-bis §4.5: VT asciende a clase con el corpus ZZU — 435 ventanas).
CLASES_PRIMARIAS = ('Sinusal', 'SVT', 'VT', 'Paced')

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


# ---------------------------------------------------------------------------
# Corpus ZZU pECG (Etapa I-bis, AP-13) — docs/etapa1_zzu_pecg.md §4
# ---------------------------------------------------------------------------

# Nomenclatura ZZU: derivaciones unipolares en MAYÚSCULAS ('AVR'...) ≠
# Leipzig ('aVR'...). Se normaliza al leer.
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


def construir_indice_corpus(
    data_leipzig: Path, qc_zzu: Path, spec_zzu: WindowSpec | None = None,
) -> pd.DataFrame:
    """Índice combinado Leipzig (pediátricos, 10 s/5 s/margen 1) + ZZU (10 s/5 s/margen 0)."""
    idx_lei = construir_indice_ventanas(
        registros_dataset(data_leipzig, pediatricos=True),
        WindowSpec(dur_s=10, hop_s=5, min_seg_s=10, margen_s=1.0),
    )
    idx_lei.insert(1, 'fuente', 'leipzig')
    idx_lei.insert(2, 'paciente', idx_lei['registro'])
    idx_zzu = construir_indice_ventanas_zzu(
        qc_zzu, spec_zzu or WindowSpec(dur_s=10, hop_s=5, min_seg_s=10, margen_s=0.0)
    )
    return pd.concat([idx_lei, idx_zzu], ignore_index=True)
