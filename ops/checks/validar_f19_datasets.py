"""Valida manifiestos y archivos descargados por F19 sin consultar ZZU test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import wfdb


RAIZ = Path(__file__).resolve().parents[2]


def argumentos() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=RAIZ / 'data' / 'f19_paced')
    p.add_argument('--manifiestos', type=Path,
                   default=RAIZ / 'results' / 'dl' / 'f19_datasets')
    p.add_argument('--exigir-senales', action='store_true')
    return p.parse_args()


def main() -> None:
    args = argumentos()
    errores: list[str] = []
    avisos: list[str] = []
    ptb = pd.read_csv(args.manifiestos / 'ptbxl_manifest.csv')
    lei = pd.read_csv(args.manifiestos / 'leipzig_manifest.csv')

    if len(ptb[ptb.rol == 'paced']) < 290:
        errores.append('PTB-XL tiene menos de 290 registros PACE')
    if (ptb[ptb.rol == 'paced'].edad_anos < 18).any():
        avisos.append('PTB-XL contiene PACE pediatrico; revisar supuesto de dominio')
    if set(ptb.fs_hz) != {500.0} or set(ptb.n_derivaciones) != {12}:
        errores.append('PTB-XL no conserva contrato 12 derivaciones @ 500 Hz')
    if not ptb.paciente.str.startswith('ptbxl:').all():
        errores.append('IDs PTB-XL no estan namespaced')

    if set(lei.fs_hz) != {977.0}:
        errores.append('Leipzig no conserva frecuencia esperada de 977 Hz')
    if not lei.tiene_pacing.any():
        errores.append('Leipzig no contiene registros anotados con pacing')
    if not lei.paciente.str.startswith('leipzig:').all():
        errores.append('IDs Leipzig no estan namespaced')

    seleccion = pd.concat([
        ptb[['dataset', 'paciente', 'registro']],
        lei[['dataset', 'paciente', 'registro']],
    ], ignore_index=True)
    if seleccion.duplicated(['dataset', 'registro']).any():
        errores.append('registros duplicados dentro de un dataset')

    for _, r in ptb.iterrows():
        base = RAIZ / str(r.ruta_base)
        if not base.with_suffix('.hea').exists():
            errores.append(f'falta cabecera PTB {r.registro}')
            continue
        h = wfdb.rdheader(str(base))
        if h.fs != 500 or h.n_sig != 12:
            errores.append(f'cabecera PTB invalida {r.registro}')
        if args.exigir_senales:
            if not base.with_suffix('.dat').exists():
                errores.append(f'falta señal PTB {r.registro}')
            else:
                wfdb.rdrecord(str(base), sampfrom=0, sampto=min(500, h.sig_len),
                              physical=False)

    for _, r in lei.iterrows():
        base = RAIZ / str(r.ruta_base)
        if not base.with_suffix('.hea').exists() or not base.with_suffix('.atr').exists():
            errores.append(f'falta metadata Leipzig {r.registro}')
            continue
        if args.exigir_senales and bool(r.tiene_pacing):
            if not base.with_suffix('.dat').exists():
                errores.append(f'falta señal Leipzig paced {r.registro}')
            else:
                h = wfdb.rdheader(str(base))
                wfdb.rdrecord(str(base), sampfrom=0, sampto=min(977, h.sig_len),
                              physical=False)

    informe = {
        'estado': 'VERDE' if not errores else 'ROJO',
        'ptb_registros': int(len(ptb)),
        'ptb_paced': int((ptb.rol == 'paced').sum()),
        'leipzig_registros': int(len(lei)),
        'leipzig_con_pacing': int(lei.tiene_pacing.sum()),
        'senales_exigidas': args.exigir_senales,
        'avisos': avisos,
        'errores': errores,
        'test_zzu_consultado': False,
    }
    destino = args.manifiestos / 'validacion.json'
    destino.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(informe, ensure_ascii=False, indent=2))
    if errores:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
