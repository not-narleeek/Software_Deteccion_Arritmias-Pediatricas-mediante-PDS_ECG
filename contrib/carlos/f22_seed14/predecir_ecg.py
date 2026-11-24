"""Predice una ventana ECG desde NumPy o un registro WFDB."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from .inference import F22Predictor
except ImportError:
    from inference import F22Predictor


LEADS = ("I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6")


def normalize_lead(name: str) -> str:
    return name.replace(" ", "").upper()


def load_wfdb(path: Path) -> tuple[np.ndarray, int]:
    import wfdb

    record = path.with_suffix("") if path.suffix in {".hea", ".dat"} else path
    physical, fields = wfdb.rdsamp(str(record))
    names = {normalize_lead(name): index for index, name in enumerate(fields["sig_name"])}
    output = np.zeros((physical.shape[0], len(LEADS)), dtype=np.float64)
    for index, lead in enumerate(LEADS):
        source = names.get(normalize_lead(lead))
        if source is not None:
            output[:, index] = physical[:, source]
    if sum(np.any(output != 0, axis=0)) < 9:
        raise ValueError("el registro WFDB debe contener al menos nueve derivaciones reconocibles")
    return output, int(round(fields["fs"]))


def select_window(
    values: np.ndarray, sample_rate_hz: int, start_seconds: float
) -> np.ndarray:
    start = int(round(start_seconds * sample_rate_hz))
    length = int(round(10 * sample_rate_hz))
    window = values[start : start + length]
    if len(window) != length:
        raise ValueError("no hay diez segundos disponibles desde --inicio")
    return window


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, required=True)
    parser.add_argument("--formato", choices=("auto", "npy", "wfdb"), default="auto")
    parser.add_argument("--fs", type=int, default=500, help="frecuencia para .npy")
    parser.add_argument("--inicio", type=float, default=0.0, help="segundo inicial")
    parser.add_argument("--pesos", type=Path)
    parser.add_argument("--dispositivo", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()

    file_format = args.formato
    if file_format == "auto":
        file_format = "npy" if args.entrada.suffix == ".npy" else "wfdb"
    if file_format == "npy":
        values, sample_rate = np.load(args.entrada), args.fs
        if values.ndim == 2 and values.shape[0] == 12 and values.shape[1] != 12:
            values = values.T
    else:
        values, sample_rate = load_wfdb(args.entrada)

    window = select_window(values, sample_rate, args.inicio)
    predictor = F22Predictor(args.pesos, device=args.dispositivo)
    result = predictor.predict(window, sample_rate)
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.salida:
        args.salida.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
