"""Extracción de características por ventana (RF4).

Contrato completo: docs/diseno_pipeline.md §6 — grupos RR (10), QRS (9),
onda P (3), espículas (2), espectrales (10), DCT (8), calidad (2),
demográficas (2). Dimensión total 46 antes de la reducción por separabilidad.

Este módulo también aloja el detector de picos R (RF3, §4): base Kathirvel
2011 (ENLT + derivador gaussiano + umbral adaptativo) y comparador
Pan-Tompkins pediátrico (banda 8–20 Hz, refractario 120 ms).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import fftpack, signal

from .preprocess import FS

# ---------------------------------------------------------------------------
# Detección de picos R (RF3, §4)
# ---------------------------------------------------------------------------


def _derivador_gaussiano(fs: int, f0: float = 9.0) -> np.ndarray:
    """Kernel del derivador gaussiano de primer orden (FOGD) normalizado.

    f0 ≈ 9 Hz centra la respuesta en la pendiente del QRS pediátrico
    (contenido 5–25 Hz, F3-B).
    """
    sigma = fs / (2 * np.pi * f0)
    n = np.arange(-int(4 * sigma), int(4 * sigma) + 1)
    k = -n * np.exp(-(n**2) / (2 * sigma**2))
    return k / np.linalg.norm(k)


def _picos_desde_envolvente(
    e: np.ndarray, fs: int, refractario_ms: float = 200.0
) -> np.ndarray:
    """Umbral adaptativo estilo Pan-Tompkins sobre la envolvente e > 0.

    - Umbral de detección: THR = NPK + 0.25·(SPK − NPK) con estimadores
      SPK (pico de señal) y NPK (ruido) actualizados 1/8.
    - Search-back sobre huecos > 1.66·RR mediano con umbral THR/2.
    - Guarda de silencio > max(2 s, 2·RR mediano): recupera latidos de
      baja amplitud tras tramos de amplitud mayor (re-sincroniza SPK al
      50 %) — causa principal de pérdidas medida en F7 (R de 0.4 mV tras
      tramos a 0.8 mV) — aceptando solo máximos > max(THR/2, 3·NPK).
    - Período refractario pediátrico.
    """
    refr = int(refractario_ms * fs / 1000)
    # Inicialización robusta global (detección offline): el arranque en los
    # primeros 2 s es frágil ante artefactos tempranos (PT en x001–x006).
    spk = float(np.percentile(e, 99.5))
    npk = float(np.percentile(e, 50.0))
    picos: list[int] = []
    rr: list[int] = []

    def aceptar(q: int) -> None:
        picos.append(q)
        if len(picos) > 1:
            rr.append(picos[-1] - picos[-2])
            del rr[:-8]

    i = 0
    while i < e.size:
        thr = npk + 0.25 * (spk - npk)
        if e[i] >= thr:
            j0, j1 = max(0, i - int(0.060 * fs)), min(e.size, i + int(0.060 * fs))
            p = j0 + int(np.argmax(e[j0:j1]))
            if not picos or p - picos[-1] >= refr:
                if picos and rr:
                    rr_med = max(int(np.median(rr)), refr)
                    if p - picos[-1] > 1.66 * rr_med:
                        seg = e[picos[-1] + refr : p - refr]
                        if seg.size and seg.max() >= 0.5 * thr:
                            aceptar(picos[-1] + refr + int(np.argmax(seg)))
                aceptar(p)
                spk = 0.125 * float(e[p]) + 0.875 * spk
            else:  # violación refractaria: ruido (onda T o doble detección)
                npk = 0.125 * float(e[p]) + 0.875 * npk
            i = p + refr
            continue
        # Guarda de silencio (máx. 2 veces/s): recupera tramos donde la
        # amplitud cayó por debajo del THR heredado. Aceptación relativa al
        # ruido (≥ 4·NPK y > 0.3·THR) para no depender del THR congelado.
        if picos and (i - picos[-1]) % (fs // 2) == 0 and (i - picos[-1]) > 2 * refr:
            rr_med = max(int(np.median(rr)), refr) if rr else refr
            if i - picos[-1] > max(int(1.5 * fs), 1.66 * rr_med):
                seg = e[picos[-1] + refr : i]
                if seg.size and seg.max() >= max(4.0 * npk, 0.3 * thr):
                    q = picos[-1] + refr + int(np.argmax(seg))
                    aceptar(q)
                    spk = 0.6 * float(e[q]) + 0.4 * spk
                    i = q + refr
                    continue
        i += 1
    return np.asarray(picos, dtype=int)


def _alinear_a_r(x: np.ndarray, eventos: np.ndarray, fs: int) -> np.ndarray:
    """Mapea cada evento de la envolvente al pico |R| de la señal en ±50 ms."""
    out = []
    for p in eventos:
        j0, j1 = max(0, p - int(0.050 * fs)), min(x.size, p + int(0.050 * fs) + 1)
        if j1 <= j0:
            continue
        out.append(j0 + int(np.argmax(np.abs(x[j0:j1]))))
    return np.unique(np.asarray(out, dtype=int))


def _envolvente_enlt(x: np.ndarray, fs: int) -> np.ndarray:
    """Envolvente ENLT de Kathirvel 2011 (§4): sqrt(|x|) → (Δ)² → FOGD."""
    s = np.sqrt(np.abs(x))
    z = np.diff(s, prepend=s[:1]) ** 2
    return np.abs(np.convolve(z, _derivador_gaussiano(fs), mode='same'))


def detectar_picos_r_fusion(
    x_filtrada: np.ndarray, fs: int = FS, sep_ms: float = 150.0, evidencia: float = 3.0
) -> np.ndarray:
    """Detector de producción: voto II+V2 con validación cruzada (§4).

    1. ENLT por derivación (II y V2) con umbral adaptativo independiente.
    2. Unión de detecciones agrupada en clústeres de <= sep_ms (posición
       promedio del clúster).
    3. Validación cruzada: un evento se acepta solo si la OTRA derivación
       muestra energía QRS (>= evidencia·NPK de su envolvente) en ±60 ms:
       un artefacto golpea una derivación, un R verdadero aparece en ambas.
    """
    x = np.asarray(x_filtrada, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] < 8:
        raise ValueError('detectar_picos_r_fusion requiere [n x 12] (II y V2)')
    x_ii, x_v2 = x[:, 1], x[:, 7]
    e_ii, e_v2 = _envolvente_enlt(x_ii, fs), _envolvente_enlt(x_v2, fs)
    k_ii = _alinear_a_r(x_ii, _picos_desde_envolvente(e_ii, fs), fs)
    k_v2 = _alinear_a_r(x_v2, _picos_desde_envolvente(e_v2, fs), fs)
    npk_ii, npk_v2 = float(np.percentile(e_ii, 50)), float(np.percentile(e_v2, 50))
    sep = int(sep_ms * fs / 1000)
    todos = np.sort(np.concatenate([k_ii, k_v2])).astype(int)
    fusion = [int(todos[0])]
    for p in todos[1:]:
        if p - fusion[-1] > sep:
            fusion.append(int(p))
        else:
            fusion[-1] = int((fusion[-1] + p) // 2)
    w = int(0.060 * fs)
    out = [
        p
        for p in fusion
        if e_v2[max(0, p - w) : p + w].max() >= evidencia * npk_v2
        and e_ii[max(0, p - w) : p + w].max() >= evidencia * npk_ii
    ]
    return np.asarray(out, dtype=int)


def detectar_picos_r(
    x_filtrada: np.ndarray, fs: int = FS, metodo: str = 'kathirvel'
) -> np.ndarray:
    """Detector de picos R (§4): Kathirvel ENLT (base) o Pan-Tompkins
    pediátrico (comparador, banda 8–20 Hz y refractario 120 ms).

    El detector de producción (voto II+V2 con validación cruzada, §4) es
    `detectar_picos_r_fusion` y requiere la señal [n x 12].

    Args: x_filtrada [n] o [n x 12] preprocesada (usa derivación II, índice 1).
    Returns: muestras de los picos R detectados.
    KPI: Se/+P >= 95 % vs .atr (tolerancia ±100 ms) — se valida en
    scripts/validar_detector_r.py (Etapa II).
    """
    x = np.asarray(x_filtrada, dtype=np.float64)
    if x.ndim == 2:
        x = x[:, 1]  # derivación II
    if metodo == 'kathirvel':
        e = _envolvente_enlt(x, fs)
        eventos = _picos_desde_envolvente(e, fs, refractario_ms=200.0)
    elif metodo == 'pan_tompkins':
        sos = signal.butter(2, [8.0, 20.0], btype='bandpass', fs=fs, output='sos')
        b = signal.sosfiltfilt(sos, x)
        d = np.gradient(b)
        w = int(0.120 * fs)
        e = np.convolve(d**2, np.ones(w) / w, mode='same')
        eventos = _picos_desde_envolvente(e, fs, refractario_ms=120.0)
    else:
        raise ValueError(f'metodo desconocido: {metodo}')
    return _alinear_a_r(x, eventos, fs)


def evaluar_detector(
    picos: np.ndarray, anotadas: np.ndarray, fs: int = FS, tolerancia_ms: float = 100.0
) -> dict[str, float]:
    """Coincidencia uno-a-uno ávida por distancia; Se y +P (§4).

    Coincidencia si |t_detectado − t_anotado| <= 100 ms.
    """
    tol = tolerancia_ms * fs / 1000.0
    usados = np.zeros(picos.size, dtype=bool)
    tp = 0
    for a in anotadas:
        if picos.size == 0:
            break
        d = np.abs(picos.astype(float) - float(a))
        d[usados] = np.inf
        j = int(np.argmin(d))
        if d[j] <= tol:
            usados[j] = True
            tp += 1
    se = tp / anotadas.size if anotadas.size else float('nan')
    pp = tp / picos.size if picos.size else float('nan')
    return {'sensibilidad': se, 'precision_positiva': pp, 'tp': tp,
            'n_anotados': int(anotadas.size), 'n_detectados': int(picos.size)}


# ---------------------------------------------------------------------------
# Vector de características (RF4, §6)
# ---------------------------------------------------------------------------

FEATURE_NAMES: tuple[str, ...] = ()  # se fija en la implementación; orden estable
