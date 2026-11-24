"""Paquete colaborativo del candidato F22 seed 14."""

from typing import Any


__all__ = ["F22Predictor"]


def __getattr__(name: str) -> Any:
    """Evita exigir PyTorch para inspeccionar configuración y manifiesto."""
    if name == "F22Predictor":
        from .inference import F22Predictor

        return F22Predictor
    raise AttributeError(name)
