"""Genera los registros WFDB de demostración del portal web (web/demo/).

## Qué hace

Sintetiza 4 casos ECG pediátricos de 10 s @ 500 Hz (Sinusal, SVT, VT, Paced)
con los mismos parámetros de forma de onda que usaba la síntesis del portal
web, y los escribe como registros WFDB de 12 derivaciones en formato 16:

- `web/demo/demo_sinusal/` — ritmo sinusal normal
- `web/demo/demo_svt/` — taquicardia supraventricular
- `web/demo/demo_vt/` — taquicardia ventricular (QRS ancho)
- `web/demo/demo_paced/` — ritmo de marcapasos (espícula + QRS)

Las señales son **sintéticas, solo para demostración**. La derivación II lleva
la forma de onda sintetizada; las otras 11 se derivan de II con reglas fijas
(documentadas abajo) para que el registro sea un ECG de 12 derivaciones
verosímil. No representan pacientes reales ni reemplazan al corpus ZZU pECG.

## Uso

```bash
uv run python scripts/generar_demo_wfdb.py
```

Determinista: RNG semillado por caso; re-ejecutar produce bytes idénticos
(mismo checksum WFDB). Tras escribir cada registro lo relee con `rdrecord` y
verifica la conversión física contra la señal original.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import wfdb

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "web" / "demo"

FS = 500
N_SEG = FS * 10  # 10 segundos

LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]

# Parámetros de síntesis idénticos a los que tenía la síntesis JS del portal
# (gaussiana por onda: amplitud, centro y anchura en ms; rr en ms).
CASOS = {
    "demo_sinusal": dict(
        semilla=11, rr=545, jit=18, p=(0.15, -80, 22), espiga=0.0,
        r=(1.10, 0, 10), s=(-0.22, 16, 10), t=(0.30, 200, 45),
    ),
    "demo_svt": dict(
        semilla=22, rr=315, jit=8, p=None, espiga=0.0,
        r=(0.95, 0, 11), s=(-0.18, 16, 10), t=(0.18, 150, 35),
    ),
    "demo_vt": dict(
        semilla=33, rr=333, jit=10, p=None, espiga=0.0,
        r=(1.70, 0, 55), s=(-1.30, 88, 60), t=(-0.45, 280, 70),
    ),
    "demo_paced": dict(
        semilla=44, rr=667, jit=10, p=(0.10, -80, 22), espiga=0.60,
        r=(0.85, 0, 12), s=(-0.18, 16, 10), t=(0.28, 210, 45),
    ),
}


def gauss(t_ms: np.ndarray, mu: float, sigma: float, amp: float) -> np.ndarray:
    z = (t_ms - mu) / sigma
    return amp * np.exp(-0.5 * z * z)


def sintetizar_lead_ii(caso: dict) -> np.ndarray:
    """Señal lead II sintética de 10 s @ 500 Hz en mV (misma receta que el portal)."""
    rng = np.random.default_rng(caso["semilla"])
    sig = np.zeros(N_SEG)
    t = 800.0
    w = int(0.35 * FS)
    idx_ms = np.arange(-w, w + 1) * 1000.0 / FS
    while t < 9200:
        centro = int(t * FS / 1000)
        ini, fin = centro - w, centro + w
        if fin > 0 and ini < N_SEG:
            v = np.zeros(len(idx_ms))
            if caso["p"]:
                amp, mu, sigma = caso["p"]
                v = v + gauss(idx_ms, mu, sigma, amp)
            if caso["espiga"]:
                v = v + gauss(idx_ms, -45, 2.5, caso["espiga"])
            amp, mu, sigma = caso["r"]
            v = v + gauss(idx_ms, mu, sigma, amp)
            amp, mu, sigma = caso["s"]
            v = v + gauss(idx_ms, mu, sigma, amp)
            amp, mu, sigma = caso["t"]
            v = v + gauss(idx_ms, mu, sigma, amp)
            lo, hi = max(ini, 0), min(fin + 1, N_SEG)
            sig[lo:hi] += v[lo - ini : hi - ini]
        t += caso["rr"] + rng.uniform(-1, 1) * caso["jit"]
    sig += 0.018 * rng.uniform(-1, 1, N_SEG)
    sig += 0.05 * np.sin(2 * np.pi * 0.4 * np.arange(N_SEG) / FS)
    return sig


def derivar_12_leads(ii: np.ndarray) -> np.ndarray:
    """Deriva las otras 11 caras desde II con reglas fijas (demo sintética).

    Einthoven exacto: I = II - III con III = 0.6·II (eje eléctrico fijo),
    aumentadas por sus fórmulas y precordiales con progresión R sintética.
    """
    I = 0.40 * ii          # II = I + III  (III = 0.6·II)
    III = 0.60 * ii
    aVR = -0.70 * ii       # -(I + II)/2
    aVL = -0.10 * ii       # I - II/2
    aVF = 0.80 * ii        # II - I/2
    v = {
        "V1": -0.35 * ii + 0.05,
        "V2": -0.15 * ii,
        "V3": 0.25 * ii,
        "V4": 0.60 * ii,
        "V5": 0.75 * ii,
        "V6": 0.70 * ii,
    }
    cols = [I, ii, III, aVR, aVL, aVF] + [v[l] for l in LEADS[6:]]
    return np.column_stack(cols)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    fallos = []
    for nombre, caso in CASOS.items():
        ii = sintetizar_lead_ii(caso)
        p_signal = derivar_12_leads(ii)
        carpeta = DESTINO / nombre
        carpeta.mkdir(parents=True, exist_ok=True)
        wfdb.wrsamp(
            nombre, fs=FS, units=["mV"] * 12, sig_name=LEADS,
            p_signal=p_signal, write_dir=str(carpeta), fmt=["16"] * 12,
        )
        # Verificación: releer y comparar contra la señal sintetizada (cuantización fmt 16)
        rec = wfdb.rdrecord(str(carpeta / nombre))
        delta = np.abs(rec.p_signal - p_signal).max()
        ok = delta < 1.5 / rec.adc_gain[LEADS.index("II")]
        print(f"{nombre}: fmt {rec.fmt[0]} · ganancia {rec.adc_gain[0]:.1f} ADC/mV · "
              f"{rec.sig_len} muestras · max|Δ| {delta:.2e} mV {'✅' if ok else '❌'}")
        if not ok:
            fallos.append(nombre)
    if fallos:
        print(f"VERIFICACIÓN FALLIDA: {', '.join(fallos)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
