import sys
from pathlib import Path

import numpy as np
import pytest


pytest.importorskip("torch")
PACKAGE_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_DIR.parents[2]
sys.path.insert(0, str(PACKAGE_DIR))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from inference import combine_predictions  # noqa: E402


def test_paced_gate_recovers_paced():
    morphology = np.array([0.7, 0.1, 0.05, 0.1, 0.05])
    paced = np.array([0.05, 0.05, 0.05, 0.8, 0.05])
    result = combine_predictions(morphology, paced)
    assert result["class"] == "Paced"
    assert result["paced_gate_applied"] is True


def test_vt_has_priority_over_paced_gate():
    morphology = np.array([0.05, 0.1, 0.7, 0.1, 0.05])
    paced = np.array([0.05, 0.05, 0.05, 0.8, 0.05])
    result = combine_predictions(morphology, paced)
    assert result["class"] == "VT"
    assert result["protected_by_vt"] is True
    assert result["paced_gate_applied"] is False
