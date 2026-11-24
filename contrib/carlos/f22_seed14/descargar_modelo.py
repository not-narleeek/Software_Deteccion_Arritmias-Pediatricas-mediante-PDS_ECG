"""Descarga y verifica los dos checkpoints del Release F22."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "f22-bundle/1"})
    try:
        with urllib.request.urlopen(request) as response, partial.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, default=PACKAGE_DIR / "weights")
    parser.add_argument("--forzar", action="store_true")
    args = parser.parse_args()

    manifest = json.loads((PACKAGE_DIR / "manifest.json").read_text())
    args.destino.mkdir(parents=True, exist_ok=True)
    for artifact in manifest["artifacts"]:
        path = args.destino / artifact["file"]
        valid = (
            path.is_file()
            and path.stat().st_size == artifact["bytes"]
            and sha256_file(path) == artifact["sha256"]
        )
        if valid and not args.forzar:
            print(f"OK existente: {path.name}")
            continue
        print(f"Descargando {artifact['role']}: {artifact['url']}")
        download(artifact["url"], path)
        if path.stat().st_size != artifact["bytes"]:
            path.unlink(missing_ok=True)
            raise SystemExit(f"tamaño inválido: {path.name}")
        if sha256_file(path) != artifact["sha256"]:
            path.unlink(missing_ok=True)
            raise SystemExit(f"SHA-256 inválido: {path.name}")
        print(f"OK verificado: {path.name}")


if __name__ == "__main__":
    main()
