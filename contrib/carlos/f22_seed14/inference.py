"""Inferencia reproducible para la cascada F22 seed 14."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
from scipy import signal

try:
    from .model import CLASSES, ResNet1D
except ImportError:  # ejecución directa desde esta carpeta
    from model import CLASSES, ResNet1D


PACKAGE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_DIR.parents[2]
SRC_DIR = REPOSITORY_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecg_pipeline.pacing import FEATURES_HF, extraer_features_hf  # noqa: E402


MORPHOLOGY_INDICES = (0, 1, 2, 4)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def combine_predictions(
    morphology_probabilities: np.ndarray,
    paced_probabilities: np.ndarray,
) -> dict[str, Any]:
    """Aplica la misma prioridad VT usada en la evaluación F22."""
    morphology_probabilities = np.asarray(morphology_probabilities, dtype=float)
    paced_probabilities = np.asarray(paced_probabilities, dtype=float)
    if morphology_probabilities.shape != (len(CLASSES),):
        raise ValueError("morphology_probabilities debe tener cinco valores")
    if paced_probabilities.shape != (len(CLASSES),):
        raise ValueError("paced_probabilities debe tener cinco valores")

    morphology_index = MORPHOLOGY_INDICES[
        int(np.argmax(morphology_probabilities[list(MORPHOLOGY_INDICES)]))
    ]
    paced_index = int(np.argmax(paced_probabilities))
    paced_positive = paced_index == CLASSES.index("Paced")
    protected_vt = paced_positive and CLASSES[morphology_index] == "VT"
    paced_applied = paced_positive and not protected_vt
    final_index = CLASSES.index("Paced") if paced_applied else morphology_index
    source_probabilities = (
        paced_probabilities if paced_applied else morphology_probabilities
    )
    return {
        "class": CLASSES[final_index],
        "confidence": float(source_probabilities[final_index]),
        "morphology_class": CLASSES[morphology_index],
        "paced_gate_positive": paced_positive,
        "paced_gate_applied": paced_applied,
        "protected_by_vt": protected_vt,
    }


class F22Predictor:
    """Carga el bundle verificado y predice una ventana ECG de 10 segundos."""

    def __init__(
        self,
        weights_dir: Path | str | None = None,
        device: str = "cpu",
    ):
        self.package_dir = PACKAGE_DIR
        self.weights_dir = Path(weights_dir or self.package_dir / "weights")
        self.config = self._read_json(self.package_dir / "config.json")
        self.manifest = self._read_json(self.package_dir / "manifest.json")
        self.ecg_norm = self._read_json(
            self.package_dir / self.config["ecg_normalization"]
        )
        self.hf_norm = self._read_json(
            self.package_dir / self.config["hf_normalization"]
        )
        self.device = torch.device(device)
        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("se solicitó CUDA, pero PyTorch no detecta una GPU")
        self._verify_artifacts()
        self.morphology_model = ResNet1D().to(self.device)
        self.paced_model = ResNet1D(hf_dim=len(FEATURES_HF)).to(self.device)
        self._load_checkpoint(
            self.morphology_model, self.config["morphology_checkpoint"]
        )
        self._load_checkpoint(self.paced_model, self.config["paced_checkpoint"])

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _verify_artifacts(self) -> None:
        for artifact in self.manifest["artifacts"]:
            path = self.weights_dir / artifact["file"]
            if not path.is_file():
                raise FileNotFoundError(
                    f"falta {path}; ejecuta descargar_modelo.py primero"
                )
            if path.stat().st_size != artifact["bytes"]:
                raise ValueError(f"tamaño inesperado para {path.name}")
            if sha256_file(path) != artifact["sha256"]:
                raise ValueError(f"SHA-256 inválido para {path.name}")

    def _load_checkpoint(self, model: ResNet1D, filename: str) -> None:
        path = self.weights_dir / filename
        try:
            checkpoint = torch.load(
                path, map_location=self.device, weights_only=False
            )
        except TypeError:
            checkpoint = torch.load(path, map_location=self.device)
        if tuple(checkpoint.get("clases", ())) != CLASSES:
            raise ValueError(f"orden de clases incompatible en {filename}")
        model.load_state_dict(checkpoint["modelo"], strict=True)
        model.eval()

    def _prepare_window(
        self, ecg: np.ndarray, sample_rate_hz: int
    ) -> np.ndarray:
        values = np.asarray(ecg, dtype=np.float64)
        if values.ndim != 2:
            raise ValueError("el ECG debe ser una matriz [muestras, 12 derivaciones]")
        if values.shape[0] == 12 and values.shape[1] != 12:
            values = values.T
        if values.shape[1] != 12:
            raise ValueError(f"se esperaban 12 derivaciones, recibido {values.shape}")
        if not np.isfinite(values).all():
            raise ValueError("el ECG contiene NaN o infinito")
        target_rate = int(self.config["sample_rate_hz"])
        if sample_rate_hz <= 170:
            raise ValueError("la frecuencia debe superar 170 Hz para la rama HF")
        if sample_rate_hz != target_rate:
            divisor = int(np.gcd(sample_rate_hz, target_rate))
            values = signal.resample_poly(
                values,
                target_rate // divisor,
                sample_rate_hz // divisor,
                axis=0,
            )
        required = int(self.config["window_samples"])
        if values.shape[0] != required:
            raise ValueError(
                f"la ventana debe contener {required} muestras a {target_rate} Hz; "
                f"recibido {values.shape[0]}"
            )
        return values

    def _prepare_morphology(self, window: np.ndarray) -> torch.Tensor:
        values = window.T.copy()
        present = np.max(np.abs(values), axis=1) > 0
        mean = np.asarray(self.ecg_norm["media_mv"], dtype=np.float64)[:, None]
        std = np.asarray(self.ecg_norm["desv_mv"], dtype=np.float64)[:, None]
        values = (values - mean) / std
        values[~present] = 0.0
        return torch.from_numpy(values.astype(np.float32))[None].to(self.device)

    def _prepare_hf(self, window: np.ndarray) -> torch.Tensor:
        extracted = extraer_features_hf(
            window, int(self.config["sample_rate_hz"])
        )
        if tuple(self.hf_norm["features"]) != FEATURES_HF:
            raise ValueError("orden de características HF incompatible")
        values = np.asarray([extracted[name] for name in FEATURES_HF])
        values = np.log1p(values)
        mean = np.asarray(self.hf_norm["media_train"])
        std = np.asarray(self.hf_norm["desv_train"])
        values = np.clip((values - mean) / std, -8.0, 8.0)
        return torch.from_numpy(values.astype(np.float32))[None].to(self.device)

    @torch.inference_mode()
    def predict(self, ecg: np.ndarray, sample_rate_hz: int = 500) -> dict[str, Any]:
        window = self._prepare_window(ecg, sample_rate_hz)
        morphology_input = self._prepare_morphology(window)
        hf_input = self._prepare_hf(window)
        morphology_probabilities = (
            self.morphology_model(morphology_input).softmax(1)[0].cpu().numpy()
        )
        paced_probabilities = (
            self.paced_model(morphology_input, hf_input)
            .softmax(1)[0]
            .cpu()
            .numpy()
        )
        result = combine_predictions(
            morphology_probabilities, paced_probabilities
        )
        result.update(
            {
                "model_version": self.config["model_version"],
                "input_unit": self.config["input_unit"],
                "morphology_probabilities": {
                    name: float(value)
                    for name, value in zip(CLASSES, morphology_probabilities)
                },
                "paced_gate_probabilities": {
                    name: float(value)
                    for name, value in zip(CLASSES, paced_probabilities)
                },
            }
        )
        return result
