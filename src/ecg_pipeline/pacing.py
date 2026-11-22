"""Características de alta frecuencia para detectar actividad de pacing.

Este módulo opera siempre sobre señal física sin el paso-bajo de 40 Hz. Las
variables fueron verificadas en F19 con PTB-XL y transferencia a Leipzig.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

FEATURES_HF = (
    'espiculas_n',
    'hf_rms_mediana',
    'hf_rms_max',
    'hf_q995_mediana',
    'hf_q995_max',
    'slew_q999_mediana',
    'slew_q999_max',
    'sincronia_hf_q999',
)


def _contar_espiculas(x: np.ndarray, hf_abs: np.ndarray, fs: int,
                      slew_k: float = 2.5) -> int:
    """Equivalente multiderivación que reutiliza la banda HF ya filtrada."""
    eventos: list[int] = []
    max_muestras = int(round(0.010 * fs))
    refract = int(round(0.100 * fs))
    for j in range(x.shape[1]):
        b = hf_abs[:, j]
        mediana = np.median(b)
        mad = np.median(np.abs(b - mediana)) * 1.4826
        if mad <= 0:
            continue
        sobre = b > mediana + 10.0 * mad
        flancos = np.diff(sobre.astype(np.int8))
        inicios = np.flatnonzero(flancos == 1) + 1
        fines = np.flatnonzero(flancos == -1) + 1
        if sobre[0]:
            inicios = np.r_[0, inicios]
        if sobre[-1]:
            fines = np.r_[fines, b.size]
        d = np.abs(np.diff(x[:, j]))
        escala = float(np.percentile(d, 99.5)) + 1e-12
        picos: list[int] = []
        for inicio, fin in zip(inicios, fines):
            if fin - inicio > max_muestras:
                continue
            pico = int(inicio + np.argmax(b[inicio:fin]))
            if d[max(0, pico - 2):pico + 3].max() < slew_k * escala:
                continue
            if picos and pico - picos[-1] < refract:
                continue
            picos.append(pico)
        eventos.extend(picos)
    if not eventos:
        return 0
    ordenados = sorted(eventos)
    fusion = [ordenados[0]]
    separacion = int(0.030 * fs)
    for pico in ordenados[1:]:
        if pico - fusion[-1] > separacion:
            fusion.append(pico)
    return len(fusion)


def extraer_features_hf(x_crudo: np.ndarray, fs: int) -> dict[str, float]:
    """Extrae ocho variables de pacing desde señal cruda multiderivación.

    Args:
        x_crudo: matriz ``[muestras, derivaciones]`` en unidades físicas.
        fs: frecuencia de muestreo en Hz; debe permitir la banda desde 80 Hz.
    """
    x = np.asarray(x_crudo, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] < 2:
        raise ValueError(f'se requiere señal [muestras, derivaciones], recibido {x.shape}')
    if fs <= 170:
        raise ValueError(f'fs={fs} insuficiente para features HF desde 80 Hz')
    f_hi = min(237.5, 0.95 * fs / 2)
    sos = signal.butter(3, [80.0, f_hi], btype='bandpass', fs=fs, output='sos')
    hf = signal.sosfiltfilt(sos, x, axis=0)
    hf_abs = np.abs(hf)
    rms = np.sqrt(np.mean(hf ** 2, axis=0))
    q995 = np.percentile(hf_abs, 99.5, axis=0)
    slew = np.percentile(np.abs(np.diff(x, axis=0)), 99.9, axis=0)
    sincronia = np.percentile(np.median(hf_abs, axis=1), 99.9)
    n_espiculas = _contar_espiculas(x, hf_abs, fs)
    return {
        'espiculas_n': float(n_espiculas),
        'hf_rms_mediana': float(np.median(rms)),
        'hf_rms_max': float(np.max(rms)),
        'hf_q995_mediana': float(np.median(q995)),
        'hf_q995_max': float(np.max(q995)),
        'slew_q999_mediana': float(np.median(slew)),
        'slew_q999_max': float(np.max(slew)),
        'sincronia_hf_q999': float(sincronia),
    }
