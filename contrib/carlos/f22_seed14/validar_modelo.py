"""Valida contrato, manifiesto y opcionalmente los checkpoints F22."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


PACKAGE_DIR = Path(__file__).resolve().parent
EXPECTED_ROLES = {"morphology", "paced_gate"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(package_dir: Path = PACKAGE_DIR) -> list[dict]:
    manifest = read_json(package_dir / "manifest.json")
    config = read_json(package_dir / "config.json")
    if manifest.get("schema_version") != 1 or config.get("schema_version") != 1:
        raise ValueError("schema_version debe ser 1")
    if manifest.get("model_version") != config.get("model_version"):
        raise ValueError("model_version difiere entre config y manifest")
    artifacts = manifest.get("artifacts", [])
    if {item.get("role") for item in artifacts} != EXPECTED_ROLES:
        raise ValueError("el manifiesto debe declarar morphology y paced_gate")
    filenames = {item.get("file") for item in artifacts}
    expected_files = {
        config.get("morphology_checkpoint"),
        config.get("paced_checkpoint"),
    }
    if filenames != expected_files:
        raise ValueError("los checkpoints de config y manifest no coinciden")
    for item in artifacts:
        if not isinstance(item.get("bytes"), int) or item["bytes"] <= 0:
            raise ValueError(f"tamaño inválido para {item.get('file')}")
        sha = item.get("sha256", "")
        if len(sha) != 64 or any(character not in "0123456789abcdef" for character in sha):
            raise ValueError(f"SHA-256 inválido para {item.get('file')}")
        parsed = urlparse(item.get("url", ""))
        if parsed.scheme != "https" or parsed.netloc != "github.com":
            raise ValueError(f"URL inválida para {item.get('file')}")
    if len(config.get("lead_order", [])) != 12:
        raise ValueError("config debe declarar doce derivaciones")
    if len(config.get("classes", [])) != 5:
        raise ValueError("config debe declarar cinco clases")
    return artifacts


def validate_weights(weights_dir: Path, artifacts: list[dict]) -> None:
    for item in artifacts:
        path = weights_dir / item["file"]
        if not path.is_file():
            raise FileNotFoundError(f"falta {path}")
        if path.stat().st_size != item["bytes"]:
            raise ValueError(f"tamaño inesperado para {path.name}")
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"SHA-256 inválido para {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pesos", type=Path, default=PACKAGE_DIR / "weights")
    parser.add_argument("--solo-manifiesto", action="store_true")
    args = parser.parse_args()
    artifacts = validate_manifest()
    if not args.solo_manifiesto:
        validate_weights(args.pesos, artifacts)
    print("F22 bundle VERDE")


if __name__ == "__main__":
    main()
