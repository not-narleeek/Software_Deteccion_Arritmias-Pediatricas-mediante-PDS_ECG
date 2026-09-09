"""Preprocesamiento: filtros, espículas y medición de distorsión QRS.

Contrato completo: docs/diseno_pipeline.md §3. Implementación: Etapa II, F6.
Cadena: HP 0.5 Hz (ord 4) → notch 50 Hz (Q=35) → LP 40 Hz (ord 4), todo en
SOS con `sosfiltfilt` (fase cero, requisito del KPI de distorsión < 5 %).
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

FS = 977


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
    fs: int = FS


def _sos_notch(f0: float, q: float, fs: int) -> np.ndarray:
    """Sección SOS (biquad) del notch IIR a f0 con factor Q."""
    b, a = signal.iirnotch(f0, q, fs=fs)
    return np.array([[b[0], b[1], b[2], 1.0, a[1], a[2]]], dtype=float)


def _sos_cadena(spec: FilterSpec) -> list[tuple[str, np.ndarray]]:
    """[(nombre, coeficientes SOS)] de la cadena en orden de aplicación."""
    hp = signal.butter(spec.orden, spec.hp_hz, btype='highpass', fs=spec.fs, output='sos')
    notch = _sos_notch(spec.notch_hz, spec.notch_q, spec.fs)
    lp = signal.butter(spec.orden, spec.lp_hz, btype='lowpass', fs=spec.fs, output='sos')
    return [('paso_alto', hp), ('notch', notch), ('paso_bajo', lp)]


def preprocesar(x: np.ndarray, spec: FilterSpec = FilterSpec()) -> np.ndarray:
    """Aplica HP -> notch -> LP (fase cero) a la señal [n x 12] (o [n]).

    Invariante: misma forma y unidades que la entrada (mV físicos).
    """
    y = np.asarray(x, dtype=np.float64)
    for _, sos in _sos_cadena(spec):
        y = signal.sosfiltfilt(sos, y, axis=0)
    return y.astype(np.float32)


def detectar_espiculas(x_crudo: np.ndarray, fs: int = FS) -> np.ndarray:
    """Detecta espículas de marcapasos sobre copia sin filtrar (§3.2).

    Banda 80–250 Hz + umbral adaptativo (mediana + 10·MAD del enrollado);
    eventos de duración < 10 ms; a lo sumo un pico por 100 ms.

    Args: x_crudo [n] o [n x 12] (usa derivación II, índice 1).
    Returns: muestras (índices) de eventos espícula.
    """
    x = np.asarray(x_crudo, dtype=np.float64)
    if x.ndim == 2:
        x = x[:, 1]  # derivación II
    sos = signal.butter(3, [80.0, 250.0], btype='bandpass', fs=fs, output='sos')
    b = np.abs(signal.sosfiltfilt(sos, x))
    med = np.median(b)
    mad = np.median(np.abs(b - med)) * 1.4826
    if mad <= 0:
        return np.array([], dtype=int)
    umbral = med + 10.0 * mad
    sobre = b > umbral
    # Rotular eventos contiguos
    flancos = np.diff(sobre.astype(np.int8))
    inicios = np.flatnonzero(flancos == 1) + 1
    fines = np.flatnonzero(flancos == -1) + 1
    if sobre[0]:
        inicios = np.r_[0, inicios]
    if sobre[-1]:
        fines = np.r_[fines, b.size]
    max_ms = int(round(0.010 * fs))  # transiente < 10 ms
    refract = int(round(0.100 * fs))
    picos: list[int] = []
    for ini, fin in zip(inicios, fines):
        if fin - ini > max_ms:
            continue  # demasiado largo para ser espícula
        pico = ini + int(np.argmax(b[ini:fin]))
        if picos and pico - picos[-1] < refract:
            continue
        picos.append(int(pico))
    return np.asarray(picos, dtype=int)


def documentar_respuesta(spec: FilterSpec = FilterSpec(), salida: str = 'results/figuras') -> None:
    """Genera módulo/fase vs frecuencia por filtro y tabla de ganancias
    en 0.5/40/49.5/50/50.5 Hz (RF2, §3.3)."""
    out = Path(salida)
    out.mkdir(parents=True, exist_ok=True)
    freqs = np.logspace(np.log10(0.1), np.log10(200), 2000)
    puntos = [0.5, 40.0, 49.5, 50.0, 50.5]
    h_total = np.ones_like(freqs, dtype=complex)
    tabla = []
    fig, axs = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    for nombre, sos in _sos_cadena(spec):
        w, h = signal.sosfreqz(sos, worN=freqs, fs=spec.fs)
        h_total *= h
        axs[0].semilogx(freqs, 20 * np.log10(np.maximum(np.abs(h), 1e-12)), label=nombre)
        axs[1].semilogx(freqs, np.unwrap(np.angle(h)) * 180 / np.pi, label=nombre)
        for f in puntos:
            _, hf = signal.sosfreqz(sos, worN=[f], fs=spec.fs)
            tabla.append({'filtro': nombre, 'frecuencia_hz': f, 'ganancia_veces': float(abs(hf[0]))})
    axs[0].set_ylabel('Módulo (dB)')
    axs[1].set_ylabel('Fase (°)')
    axs[1].set_xlabel('Frecuencia (Hz)')
    for ax in axs:
        ax.legend()
        ax.grid(True, which='both', alpha=0.3)
    fig.suptitle('Respuesta en frecuencia de la cadena de filtrado (RF2)')
    fig.tight_layout()
    fig.savefig(out / 'respuesta_frecuencia_filtros.png', dpi=150)
    plt.close(fig)
    for f in puntos:
        _, hf = signal.sosfreqz(
            np.vstack([sos for _, sos in _sos_cadena(spec)]), worN=[f], fs=spec.fs
        )
        tabla.append({'filtro': 'cadena_total', 'frecuencia_hz': f, 'ganancia_veces': float(abs(hf[0]))})
    import pandas as pd

    pd.DataFrame(tabla).to_csv(out / 'respuesta_frecuencia_ganancias.csv', index=False)


def referencia_morfologica(x: np.ndarray, fs: int = FS) -> np.ndarray:
    """Instrumento de medición para el KPI de distorsión (§3.4, AP-11).

    Cadena suave HP 0.4 Hz (ord 2) + notch 50 Hz (Q=35) + LP 45 Hz (ord 2),
    fase cero: preserva íntegra la banda de diagnóstico 0.5–40 Hz y elimina
    solo lo claramente fuera de banda. Comparar y_filtrada contra esta
    referencia mide la distorsión de morfología; compararla contra el crudo
    mezcla la limpieza pretendida (ruido EMG in-band, > 45 Hz) con la
    distorsión. Ambas se reportan; el KPI del acta rige sobre la primera.
    """
    y = np.asarray(x, dtype=np.float64)
    for sos in (
        signal.butter(2, 0.4, btype='highpass', fs=fs, output='sos'),
        _sos_notch(50.0, 35.0, fs),
        signal.butter(2, 45, btype='lowpass', fs=fs, output='sos'),
    ):
        y = signal.sosfiltfilt(sos, y, axis=0)
    return y.astype(np.float32)


def _duracion_qrs(x: np.ndarray, pico_r: int, fs: int) -> float:
    """Duración del QRS (ms) por umbral sobre la derivada, en R±60 ms (§3.4).

    Operador de medición idéntico para señal cruda y filtrada: suavizado
    previo de 10 ms (boxcar) para que el umbral sobre la derivada mida la
    pendiente del QRS y no el ruido > 40 Hz del crudo.
    """
    i0 = max(0, pico_r - int(0.060 * fs))
    i1 = min(x.size - 1, pico_r + int(0.060 * fs))
    seg = x[i0 : i1 + 1].astype(np.float64)
    w = int(0.010 * fs) | 1  # boxcar ~10 ms, impar
    seg = np.convolve(seg, np.ones(w) / w, mode='same')
    dx = np.gradient(seg)
    umbral = 0.25 * np.max(np.abs(dx))
    sostenido = max(5, int(0.015 * fs))  # 15 ms por debajo del umbral
    r_local = pico_r - i0
    onset = 0
    for j in range(r_local, sostenido, -1):
        if np.all(np.abs(dx[j - sostenido : j]) < umbral):
            onset = j
            break
    offset = len(seg) - 1
    for j in range(r_local, len(seg) - sostenido):
        if np.all(np.abs(dx[j : j + sostenido]) < umbral):
            offset = j
            break
    return (offset - onset) / fs * 1000.0


def distortion_qrs(
    x: np.ndarray, y: np.ndarray, picos_r: np.ndarray, fs: int = FS, centrar: bool = True
) -> dict[str, float]:
    """Distorsión del QRS tras el filtrado (KPI objetivo 1, §3.4).

    D = 100·||y−x||₂/||x||₂ en ventanas R±60 ms por latido. Con `centrar`
    (por defecto) ambas ventanas se centran en su media antes de comparar:
    el offset DC que elimina el paso-alto es limpieza pretendida, no
    distorsión de morfología; ambos valores se reportan en el validador.

    Returns: {'mediana_pct', 'p90_pct', 'delta_duracion_qrs_ms', 'd_pct'
    (lista por latido, para agrupar KPIs sobre el total de latidos)}.
    Criterio: mediana < 5 % y p90 < 10 %.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    d_vals, delta_dur = [], []
    for r in np.asarray(picos_r, dtype=int):
        i0 = max(0, r - int(0.060 * fs))
        i1 = min(x.size, r + int(0.060 * fs))
        if i1 - i0 < int(0.100 * fs):
            continue
        xw, yw = x[i0:i1], y[i0:i1]
        if centrar:
            xw = xw - xw.mean()
            yw = yw - yw.mean()
        nx = np.linalg.norm(xw)
        if nx <= 0:
            continue
        d_vals.append(100.0 * np.linalg.norm(yw - xw) / nx)
        delta_dur.append(abs(_duracion_qrs(x, r, fs) - _duracion_qrs(y, r, fs)))
    if not d_vals:
        raise ValueError('sin latidos válidos para medir distorsión')
    return {
        'mediana_pct': float(np.median(d_vals)),
        'p90_pct': float(np.percentile(d_vals, 90)),
        'delta_duracion_qrs_ms': float(np.median(delta_dur)),
        'd_pct': d_vals,
        'delta_ms': delta_dur,
    }
