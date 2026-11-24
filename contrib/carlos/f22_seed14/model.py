"""Arquitectura exacta de los checkpoints F20/F22 publicados."""

from __future__ import annotations

import torch
import torch.nn as nn


CLASSES = ("Sinusal", "SVT", "VT", "Paced", "Otro")


class ResidualBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv1d(
            in_channels, out_channels, 15, stride, 7, bias=False
        )
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Conv1d(out_channels, out_channels, 15, 1, 7, bias=False)
        self.bn2 = nn.BatchNorm1d(out_channels)
        # El nombre ``atajo`` forma parte de las claves de los checkpoints.
        self.atajo = (
            nn.Identity()
            if stride == 1 and in_channels == out_channels
            else nn.Sequential(
                nn.Conv1d(
                    in_channels, out_channels, 1, stride, bias=False
                ),
                nn.BatchNorm1d(out_channels),
            )
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = torch.relu(self.bn1(self.conv1(x)))
        residual = self.bn2(self.conv2(residual))
        return torch.relu(residual + self.atajo(x))


class ResNet1D(nn.Module):
    """ResNet-1D usada por morfología F22 y el gate Paced F20."""

    def __init__(
        self,
        n_classes: int = len(CLASSES),
        hf_dim: int = 0,
        hf_fusion: str = "concat",
    ):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(12, 64, 15, 2, 7, bias=False),
            nn.BatchNorm1d(64),
            nn.ReLU(),
        )
        stages: list[nn.Module] = []
        channels = 64
        for out_channels, stride in ((64, 1), (128, 2), (256, 2), (512, 2)):
            stages.append(ResidualBlock(channels, out_channels, stride))
            channels = out_channels
        self.etapas = nn.Sequential(*stages)
        self.cabeza = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Dropout(0.2),
            nn.Linear(channels, n_classes),
        )
        self.hf_dim = hf_dim
        self.hf_fusion = hf_fusion
        if hf_dim:
            self.rama_hf = nn.Sequential(
                nn.Linear(hf_dim, 32),
                nn.LayerNorm(32),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(32, 32),
                nn.ReLU(),
            )
            if hf_fusion != "concat":
                raise ValueError("F20 publicado requiere hf_fusion='concat'")
            self.pool_morfologia = nn.Sequential(
                nn.AdaptiveAvgPool1d(1), nn.Flatten()
            )
            self.cabeza_fusion = nn.Sequential(
                nn.Dropout(0.2), nn.Linear(channels + 32, n_classes)
            )

    def forward(
        self, x: torch.Tensor, hf: torch.Tensor | None = None
    ) -> torch.Tensor:
        morphology = self.etapas(self.stem(x))
        if not self.hf_dim:
            return self.cabeza(morphology)
        if hf is None:
            raise ValueError("el modelo F20 requiere ocho características HF")
        hf_embedding = self.rama_hf(hf)
        combined = torch.cat(
            (self.pool_morfologia(morphology), hf_embedding), dim=1
        )
        return self.cabeza_fusion(combined)
