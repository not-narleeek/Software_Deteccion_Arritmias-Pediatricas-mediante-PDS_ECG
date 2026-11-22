"""Resume estabilidad de gates F23 en semillas F22 confirmatorias."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('gates', nargs='+', type=Path)
    p.add_argument('--salida', type=Path, required=True)
    args = p.parse_args()
    filas = []
    for ruta in args.gates:
        r = json.loads(ruta.read_text())
        filas.append({'seed': int(ruta.parent.name.split('_')[-1]),
                      'estado': r['estado'], 'macro': r['f1_macro_val'],
                      'paced': r['f1_por_clase']['Paced'],
                      'vt': r['f1_por_clase']['VT']})
    resumen = {
        'estado': 'VERDE' if all(x['estado'] == 'VERDE' for x in filas) else 'ROJO',
        'seeds_verdes': sum(x['estado'] == 'VERDE' for x in filas),
        'seeds_total': len(filas),
        'metricas': filas,
        'media': {k: float(np.mean([x[k] for x in filas]))
                  for k in ('macro', 'paced', 'vt')},
        'desv': {k: float(np.std([x[k] for x in filas], ddof=1))
                 for k in ('macro', 'paced', 'vt')},
        'test_consultado': False,
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(resumen, indent=2) + '\n')
    print(json.dumps(resumen, indent=2))


if __name__ == '__main__':
    main()
