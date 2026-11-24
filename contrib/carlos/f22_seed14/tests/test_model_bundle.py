import json
import sys
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_DIR))

from validar_modelo import validate_manifest  # noqa: E402


def test_manifest_matches_config():
    artifacts = validate_manifest(PACKAGE_DIR)
    assert {artifact["role"] for artifact in artifacts} == {
        "morphology",
        "paced_gate",
    }


def test_normalizations_have_expected_dimensions():
    ecg = json.loads((PACKAGE_DIR / "normalizacion_ecg.json").read_text())
    hf = json.loads((PACKAGE_DIR / "normalizacion_hf.json").read_text())
    assert len(ecg["media_mv"]) == len(ecg["desv_mv"]) == 12
    assert len(hf["features"]) == len(hf["media_train"]) == len(hf["desv_train"]) == 8
    assert all(value > 0 for value in ecg["desv_mv"])
    assert all(value > 0 for value in hf["desv_train"])
