"""Gate conservador para decidir si F20 merece confirmación multisemilla."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('resumen', type=Path)
    p.add_argument('--salida', type=Path)
    args = p.parse_args()
    r = json.loads(args.resumen.read_text())
    macro = float(r['f1_macro_val'])
    por_clase = r['f1_por_clase']
    criterios = {
        'macro_ge_0.4664': macro >= 0.4664,
        'paced_gt_0': float(por_clase['Paced']) > 0.0,
        'vt_ge_0.4115': float(por_clase['VT']) >= 0.4115,
    }
    verde = all(criterios.values())
    reporte = {
        'estado': 'VERDE' if verde else 'ROJO',
        'criterios': criterios,
        'f1_macro_val': macro,
        'f1_paced': float(por_clase['Paced']),
        'f1_vt': float(por_clase['VT']),
        'decision': ('confirmar semillas 42/73' if verde
                     else 'detener; no gastar mas GPU ni consultar test'),
    }
    texto = json.dumps(reporte, indent=2)
    destino = args.salida or args.resumen.with_name('gate_f20.json')
    destino.write_text(texto + '\n')
    print(texto)
    if not verde:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
