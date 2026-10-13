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

from . import preprocess
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
    x_filtrada: np.ndarray, fs: int = FS, sep_ms: float = 150.0, evidencia: float = 3.0,
    idx_ii: int = 1, idx_v: int = 7,
) -> np.ndarray:
    """Detector de producción: voto II+V2 con validación cruzada (§4).

    1. ENLT por derivación (II y V2) con umbral adaptativo independiente.
    2. Unión de detecciones agrupada en clústeres de <= sep_ms (posición
       promedio del clúster).
    3. Validación cruzada: un evento se acepta solo si la OTRA derivación
       muestra energía QRS (>= evidencia·NPK de su envolvente) en ±60 ms:
       un artefacto golpea una derivación, un R verdadero aparece en ambas.

    idx_v permite sustituir la precordial de fusión: en los registros ZZU
    de 9 derivaciones (< 7 años, sin V2) se usa V1 (índice 6) — §4.3 de la
    Etapa I-bis. Por defecto mantiene II (1) + V2 (7) del diseño original.
    """
    x = np.asarray(x_filtrada, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] < 8:
        raise ValueError('detectar_picos_r_fusion requiere [n x 12] (II y V2)')
    x_ii, x_v = x[:, idx_ii], x[:, idx_v]
    e_ii, e_v = _envolvente_enlt(x_ii, fs), _envolvente_enlt(x_v, fs)
    k_ii = _alinear_a_r(x_ii, _picos_desde_envolvente(e_ii, fs), fs)
    k_v = _alinear_a_r(x_v, _picos_desde_envolvente(e_v, fs), fs)
    npk_ii, npk_v = float(np.percentile(e_ii, 50)), float(np.percentile(e_v, 50))
    sep = int(sep_ms * fs / 1000)
    todos = np.sort(np.concatenate([k_ii, k_v])).astype(int)
    if todos.size == 0:
        return np.asarray([], dtype=int)
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
        if e_v[max(0, p - w) : p + w].max() >= evidencia * npk_v
        and e_ii[max(0, p - w) : p + w].max() >= evidencia * npk_ii
    ]
    return np.asarray(out, dtype=int)


FEATURE_NAMES: tuple[str, ...] = (
    # RR (12): intervalos + frecuencia normalizada por edad (Davignon, F3-B)
    'rr_media_s', 'rr_mediana_s', 'rr_sdnn_s', 'rr_rmssd_s', 'rr_pnn50',
    'rr_cv', 'rr_pendiente_ms_s', 'rr_n_picos',
    'fc_norm_media', 'fc_norm_max',
    'qrs_dur_ms', 'qrs_dur_cv', 'qrs_r_ii_mv', 'qrs_s_ii_mv',
    'qrs_r_v2_mv', 'qrs_s_v2_mv', 'qrs_rs_ii', 'qrs_rs_v2', 'qrs_fwhm_ms',
    # Onda P (3)
    'p_presencia', 'p_amp_mv', 'p_r_rel',
    # Espículas (2)
    'esp_n', 'esp_por_min',
    # Espectrales (10) — energía relativa por banda (0.5–4, 4–8, 8–16, 16–25, 25–40 Hz)
    'esp_b1_ii', 'esp_b2_ii', 'esp_b3_ii', 'esp_b4_ii', 'esp_b5_ii',
    'esp_b1_v2', 'esp_b2_v2', 'esp_b3_v2', 'esp_b4_v2', 'esp_b5_v2',
    # DCT (8) — coeficientes 1–8 del latido promedio (II); cláusula F3-1
    'dct_c1', 'dct_c2', 'dct_c3', 'dct_c4', 'dct_c5', 'dct_c6', 'dct_c7', 'dct_c8',
    # Calidad (2)
    'cal_flat_frac', 'cal_rms_gt100_uv',
    # Demográficas (2)
    'edad', 'sexo',
)

NOMBRES_WAVELET: tuple[str, ...] = tuple(f'wav_c{i}' for i in range(1, 9))


def _seguro(valor: float) -> float:
    return float(valor) if np.isfinite(valor) else float('nan')


# Vector final de 46 features (decisión F8 / cláusula F3-1: wavelet db4
# sustituye a la DCT; results/features/decision_dct_wavelet.txt).
FEATURES_FINALES: tuple[str, ...] = tuple(
    c for c in FEATURE_NAMES if not c.startswith('dct_')
) + NOMBRES_WAVELET

_HR_NORM_EDAD = ((0.0, 127.0), (1.0, 123.0), (3.0, 116.0), (5.0, 112.0),
                 (8.0, 104.0), (12.0, 100.0), (16.0, 90.0), (18.1, 80.0))


def fc_normalizada(edad: float, rr_s: float) -> float:
    """FC media de la ventana normalizada por la FC media esperada a esa
    edad (Davignon 1979, promedios por grupo etario interpolados; F3-B:
    límites normales edad-dependientes).

    >1 ≈ taquicardia para la edad; separa un AVRT de 130 bpm a los 14 años
    (≈1.4) de un sinusal de 130 bpm en un lactante (≈1.0).
    """
    if not np.isfinite(edad) or not np.isfinite(rr_s) or rr_s <= 0 or edad < 0:
        return float('nan')
    edades = np.array([e for e, _ in _HR_NORM_EDAD])
    fcs = np.array([f for _, f in _HR_NORM_EDAD])
    ref = float(np.interp(min(edad, edades[-1]), edades, fcs))
    return (60.0 / rr_s) / ref


def _feat_rr(picos: np.ndarray, fs: int, dur_s: float) -> dict[str, float]:
    rr = np.diff(picos) / fs  # s
    n = float(picos.size)
    out = {
        'rr_n_picos': n,
        'rr_media_s': _seguro(rr.mean()) if rr.size else np.nan,
        'rr_mediana_s': _seguro(np.median(rr)) if rr.size else np.nan,
        'rr_min_s': _seguro(rr.min()) if rr.size else np.nan,
        'rr_max_s': _seguro(rr.max()) if rr.size else np.nan,
    }
    if rr.size >= 2:
        d = np.diff(rr) * 1000.0  # ms
        out['rr_sdnn_s'] = _seguro(rr.std(ddof=1))
        out['rr_rmssd_s'] = _seguro(np.sqrt(np.mean(d**2)) / 1000.0)
        out['rr_pnn50'] = _seguro(np.mean(np.abs(d) > 50.0))
        out['rr_cv'] = _seguro(rr.std(ddof=1) / rr.mean()) if rr.mean() > 0 else np.nan
    else:
        out.update(rr_sdnn_s=np.nan, rr_rmssd_s=np.nan, rr_pnn50=np.nan, rr_cv=np.nan)
    if rr.size >= 3:
        t = picos[1:] / fs
        pend = np.polyfit(t, rr, 1)[0] * 1000.0  # ms de RR por s
        out['rr_pendiente_ms_s'] = _seguro(pend)
    else:
        out['rr_pendiente_ms_s'] = np.nan
    _ = dur_s
    return out


def _feat_qrs(ventana: np.ndarray, picos: np.ndarray, fs: int) -> dict[str, float]:
    ii, v2 = ventana[:, 1].astype(float), ventana[:, 7].astype(float)
    dur, r_ii, s_ii, r_v2, s_v2, fwhm = [], [], [], [], [], []
    for p in picos:
        dur.append(preprocess.duracion_qrs(ii, int(p), fs))
        r_ii.append(ii[max(0, p - int(0.04 * fs)) : p + int(0.04 * fs)].max())
        s_ii.append(ii[p : p + int(0.07 * fs)].min())
        r_v2.append(v2[max(0, p - int(0.04 * fs)) : p + int(0.04 * fs)].max())
        s_v2.append(v2[p : p + int(0.07 * fs)].min())
        # FWHM de la onda R sobre la base local (mediana de R±90..±60 ms)
        i0 = max(0, p - int(0.090 * fs))
        i1 = min(ii.size, p + int(0.090 * fs))
        base = np.median(np.r_[ii[i0 : max(i0, p - int(0.060 * fs))],
                               ii[min(i1, p + int(0.060 * fs)) : i1]])
        seg = ii[i0:i1] - base
        pico = int(np.argmax(seg)) + i0
        h = seg[pico - i0]
        if h <= 0:
            continue
        izq = pico
        while izq > i0 and seg[izq - i0] > h / 2:
            izq -= 1
        der = pico
        while der < i1 - 1 and seg[der - i0] > h / 2:
            der += 1
        fwhm.append((der - izq) / fs * 1000.0)
    out = {
        'qrs_dur_ms': _seguro(np.median(dur)) if dur else np.nan,
        'qrs_dur_cv': _seguro(np.std(dur) / np.mean(dur)) if dur and np.mean(dur) > 0 else np.nan,
        'qrs_r_ii_mv': _seguro(np.median(r_ii)) if r_ii else np.nan,
        'qrs_s_ii_mv': _seguro(np.median(s_ii)) if s_ii else np.nan,
        'qrs_r_v2_mv': _seguro(np.median(r_v2)) if r_v2 else np.nan,
        'qrs_s_v2_mv': _seguro(np.median(s_v2)) if s_v2 else np.nan,
        'qrs_fwhm_ms': _seguro(np.median(fwhm)) if fwhm else np.nan,
    }
    for clave, num, den in (('qrs_rs_ii', out['qrs_r_ii_mv'], abs(out['qrs_s_ii_mv'])),
                            ('qrs_rs_v2', out['qrs_r_v2_mv'], abs(out['qrs_s_v2_mv']))):
        out[clave] = _seguro(num / den) if np.isfinite(num) and den and den > 1e-6 else np.nan
    return out


def _feat_p(ventana: np.ndarray, picos: np.ndarray, fs: int) -> dict[str, float]:
    ii = ventana[:, 1].astype(float)
    presentes, amps, r_amps = [], [], []
    for p in picos:
        i0, i1 = int(p) - int(0.160 * fs), int(p) - int(0.040 * fs)
        if i0 < 0 or i1 >= ii.size:
            continue
        seg = ii[i0:i1]
        base = np.median(np.r_[seg[: int(0.02 * fs)], seg[-int(0.02 * fs) :]])
        pico = np.abs(seg - base).max()
        r_amps.append(ii[max(0, p - int(0.04 * fs)) : p + int(0.04 * fs)].max() - base)
        ok = pico > 0.04 and pico > 3.0 * (np.median(np.abs(seg - base)) * 1.4826 + 1e-9)
        presentes.append(bool(ok))
        if ok:
            amps.append(pico)
    if presentes:
        pres = float(np.mean(presentes))
        amp = _seguro(np.mean(amps)) if amps else np.nan
        r_med = float(np.mean(r_amps)) if r_amps else np.nan
        rel = _seguro(amp / r_med) if np.isfinite(amp) and r_med and r_med > 1e-6 else np.nan
        return {'p_presencia': pres, 'p_amp_mv': amp, 'p_r_rel': rel}
    return {'p_presencia': np.nan, 'p_amp_mv': np.nan, 'p_r_rel': np.nan}


def _pico_p_signed(seg: np.ndarray, base: float) -> tuple[int, float]:
    """(índice, amplitud con signo) del pico P de un segmento PR."""
    j = int(np.argmax(np.abs(seg - base)))
    return j, float(seg[j] - base)


def _feat_pqrs_morfologia(ventana: np.ndarray, picos: np.ndarray, fs: int) -> dict[str, float]:
    """Discriminantes morfológicos SVT↔Sinusal (F14-ter, Etapa II).

    La confusión dominante del corpus ZZU es EAT (grupo SVT) vs
    sinuso-taquicardia C21 (grupo Sinusal): se separan clínicamente por
    morfología/eje de P y relación RP (docs/analisis_zzu_pecg.md). Todas
    usan derivaciones presentes en 12 y 9 derivaciones (II, III, V1).
    """
    ii = ventana[:, 1].astype(float)
    iii = ventana[:, 2].astype(float)
    v1 = ventana[:, 6].astype(float)
    pol_ii, pol_v1, amp_iii, amp_ii, p_durs, rps, prs = [], [], [], [], [], [], []
    for i, p in enumerate(picos):
        i0, i1 = int(p) - int(0.160 * fs), int(p) - int(0.040 * fs)
        if i0 < 0 or i1 >= ii.size:
            continue
        for arr, acum in ((ii, pol_ii), (v1, pol_v1)):
            seg = arr[i0:i1]
            base = np.median(np.r_[seg[: int(0.02 * fs)], seg[-int(0.02 * fs) :]])
            _, amp = _pico_p_signed(seg, base)
            acum.append(amp)
        seg_ii = ii[i0:i1]
        base_ii = np.median(np.r_[seg_ii[: int(0.02 * fs)], seg_ii[-int(0.02 * fs) :]])
        seg_iii = iii[i0:i1]
        base_iii = np.median(np.r_[seg_iii[: int(0.02 * fs)], seg_iii[-int(0.02 * fs) :]])
        _, a_ii = _pico_p_signed(seg_ii, base_ii)
        _, a_iii = _pico_p_signed(seg_iii, base_iii)
        amp_ii.append(a_ii)
        amp_iii.append(a_iii)
        # duración de P al 25 % de su amplitud (solo si hay P apreciable)
        if abs(a_ii) > 0.04:
            j = int(np.argmax(np.abs(seg_ii - base_ii)))
            umbral = abs(a_ii) * 0.25
            izq = j
            while izq > 0 and abs(seg_ii[izq] - base_ii) > umbral:
                izq -= 1
            der = j
            while der < seg_ii.size - 1 and abs(seg_ii[der] - base_ii) > umbral:
                der += 1
            p_durs.append((der - izq) / fs * 1000.0)
        # RP (P actual tras el R previo) y PR (P actual -> R actual)
        j = int(np.argmax(np.abs(seg_ii - base_ii)))
        t_p = i0 + j
        prs.append((p - t_p) / fs * 1000.0)
        if i > 0:
            rps.append((t_p - picos[i - 1]) / fs * 1000.0)

    r_v1, s_v1 = [], []
    for p in picos:
        r_v1.append(v1[max(0, p - int(0.04 * fs)) : p + int(0.04 * fs)].max())
        s_v1.append(v1[p : p + int(0.07 * fs)].min())
    med = lambda xs: _seguro(np.median(xs)) if xs else np.nan
    out = {
        'p_pol_ii_mv': med(pol_ii),
        'p_pol_v1_mv': med(pol_v1),
        'p_neg_ii_frac': _seguro(np.mean([a < 0 for a in pol_ii])) if pol_ii else np.nan,
        'p_amp_ratio_iii_ii': _seguro(abs(med(amp_iii)) / abs(med(amp_ii)))
        if np.isfinite(med(amp_ii)) and abs(med(amp_ii)) > 1e-6 else np.nan,
        'p_dur_ms': med(p_durs),
        'p_rp_ms': med(rps),
        'p_pr_ms': med(prs),
        'qrs_r_v1_mv': med(r_v1),
        'qrs_s_v1_mv': med(s_v1),
    }
    den = abs(out['qrs_s_v1_mv'])
    out['qrs_rs_v1'] = _seguro(out['qrs_r_v1_mv'] / den) \
        if np.isfinite(den) and den > 1e-6 else np.nan
    return out



def _feat_espectrales(ventana: np.ndarray, fs: int) -> dict[str, float]:
    bandas = [(0.5, 4.0), (4.0, 8.0), (8.0, 16.0), (16.0, 25.0), (25.0, 40.0)]
    out = {}
    for sufijo, col in (('ii', 1), ('v2', 7)):
        f, p = signal.welch(ventana[:, col].astype(float), fs=fs, nperseg=2048)
        total = p[(f >= 0.5) & (f <= 40.0)].sum()
        for j, (b0, b1) in enumerate(bandas, start=1):
            frac = p[(f >= b0) & (f < b1)].sum() / total if total > 0 else np.nan
            out[f'esp_b{j}_{sufijo}'] = _seguro(frac)
    return out


def _latido_promedio(x: np.ndarray, picos: np.ndarray, fs: int) -> np.ndarray | None:
    pre, post = int(0.120 * fs), int(0.200 * fs)
    latidos = [x[p - pre : p + post] for p in picos if p - pre >= 0 and p + post <= x.size]
    if len(latidos) < 3:
        return None
    return np.mean(np.asarray(latidos, dtype=float), axis=0)


def _feat_dct_wavelet(ventana: np.ndarray, picos: np.ndarray, fs: int) -> dict[str, float]:
    ii = ventana[:, 1].astype(float)
    out = {f'dct_c{i}': np.nan for i in range(1, 9)}
    out.update({f'wav_c{i}': np.nan for i in range(1, 9)})
    prom = _latido_promedio(ii, picos, fs)
    if prom is None:
        return out
    c = fftpack.dct(prom, type=2, norm='ortho')[1:9]
    for i in range(8):
        out[f'dct_c{i + 1}'] = _seguro(c[i])
    import pywt

    _, _, _, _, cA4 = pywt.wavedec(prom, 'db4', level=4)
    for i in range(min(8, cA4.size)):
        out[f'wav_c{i + 1}'] = _seguro(cA4[i])
    return out


def _feat_calidad(ventana: np.ndarray, ventana_raw: np.ndarray | None, fs: int) -> dict[str, float]:
    if ventana_raw is not None:
        ii_raw = ventana_raw[:, 1].astype(float)
    else:
        ii_raw = ventana[:, 1].astype(float)
    d = np.abs(np.diff(ii_raw))
    flat = float(np.mean(d < 1e-4))
    if ventana_raw is not None:
        sos = signal.butter(3, 100.0, btype='highpass', fs=fs, output='sos')
        residuo = signal.sosfiltfilt(sos, ventana_raw[:, 1].astype(float))
        rms = float(np.sqrt(np.mean(residuo**2))) * 1000.0  # µV
    else:
        rms = np.nan
    return {'cal_flat_frac': flat, 'cal_rms_gt100_uv': _seguro(rms)}


def vector_caracteristicas(
    ventana: np.ndarray,
    picos_r: np.ndarray,
    espiculas: np.ndarray,
    edad: float,
    sexo: int,
    fs: int = FS,
    ventana_raw: np.ndarray | None = None,
) -> dict[str, float]:
    """Calcula el vector §6 para una ventana.

    Args: ventana [n x 12] preprocesada; picos/espiculas en muestras LOCALES
    a la ventana; edad en años (NaN si desconocida, AP-10); sexo 0/1;
    ventana_raw [n x 12] opcional para las features de calidad (RMS > 100 Hz
    exige contenido fuera de banda; si se omite, cal_rms_gt100_uv = NaN).
    Returns: dict nombre→valor con las 46 de FEATURE_NAMES más wav_c1..8
    (grupo alternativo de la cláusula DCT-vs-wavelet F3-1).
    """
    ventana = np.asarray(ventana)
    picos = np.asarray(picos_r, dtype=int)
    out: dict[str, float] = {}
    out.update(_feat_rr(picos, fs, ventana.shape[0] / fs))
    out.update(_feat_qrs(ventana, picos, fs))
    out.update(_feat_p(ventana, picos, fs))
    out.update(_feat_pqrs_morfologia(ventana, picos, fs))
    n_esp = float(np.asarray(espiculas).size)
    out['esp_n'] = n_esp
    out['esp_por_min'] = _seguro(n_esp / (ventana.shape[0] / fs / 60.0))
    out.update(_feat_espectrales(ventana, fs))
    out.update(_feat_dct_wavelet(ventana, picos, fs))
    out.update(_feat_calidad(ventana, ventana_raw, fs))
    out['fc_norm_media'] = fc_normalizada(edad, out.get('rr_media_s', float('nan')))
    out['fc_norm_max'] = fc_normalizada(edad, out.get('rr_min_s', float('nan')))
    out['edad'] = _seguro(edad)
    out['sexo'] = float(sexo)
    return out


def separabilidad(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """ANOVA univariada + índice de Fisher por feature (objetivo 2 del acta).

    Returns: DataFrame [feature, F, p_valor, fisher] ordenado por Fisher.
    Regla de descarte (§6): p > 0.05 y Fisher nulo (< 1e-6).
    """
    from sklearn.feature_selection import f_classif

    filas = []
    clases = np.unique(y)
    for col in X.columns:
        m = X[col].notna()
        if m.sum() < 10:
            filas.append({'feature': col, 'F': np.nan, 'p_valor': np.nan, 'fisher': np.nan})
            continue
        xi, yi = X.loc[m, col].to_numpy(float), y.loc[m].to_numpy()
        F, p = f_classif(xi.reshape(-1, 1), yi)
        mu = xi.mean()
        entre, intra = 0.0, 0.0
        for c in clases:
            xc = xi[yi == c]
            if xc.size == 0:
                continue
            entre += xc.size * (xc.mean() - mu) ** 2
            intra += xc.size * (xc.var(ddof=1) if xc.size > 1 else 0.0)
        fisher = entre / intra if intra > 0 else 0.0
        filas.append({'feature': col, 'F': float(F[0]), 'p_valor': float(p[0]), 'fisher': float(fisher)})
    return pd.DataFrame(filas).sort_values('fisher', ascending=False, ignore_index=True)
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

