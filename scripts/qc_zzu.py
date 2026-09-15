"""Control de calidad a escala completa — ZZU pECG, Etapa I sobre el corpus
ampliado (AP-13; acta §7.2 Etapa I: "identificación temprana de exámenes con
defectos de adquisición").

Evalúa TODOS los registros (no muestra) y produce la lista explícita de
excluidos con causa. Métricas por registro (derivación II por nombre; rangos
por derivación para detectar electrodos sueltos en cualquiera):

  rango_ii_mv   : p99 − p1 de la derivación II (mV). Fisiológico < ~4.
  rango_max_mv  : máximo del rango p1–p99 entre las 12 (o 9) derivaciones.
  frac_flat     : fracción de ventanas de 1 s con std == 0 en II (electrodo
                  suelto / canal muerto).
  pico_50hz_x   : pico PSD Welch en 49–51 Hz ÷ mediana 20–40 Hz (II crudo).

Reglas (evidencia: docs/analisis_zzu_pecg.md §2.C/§3.1, muestra 874):
  EXCLUIR si: duración < 10 s (sin ventana posible)  [estructural]
              rango_ii_mv > 5                        [artefacto de movimiento]
              rango_max_mv > 10                      [electrodo suelto en otra deriv.]
              frac_flat > 0.2                        [canal muerto]
              pico_50hz_x > 20                       [interferencia severa]
  MARCAR calidad_dudosa (NO excluir): bsqi_min < 0.95 (confunde con arritmia).

Salidas (results/qc_zzu/): qc_registros.csv (todo), excluidos.csv (con
causa), resumen.txt.

Uso:  uv run python scripts/qc_zzu.py
"""

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal as sps
import wfdb

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / 'data' / 'zzu_pecg' / 'Child_ecg'
REG = RAIZ / 'results' / 'inventario_zzu' / 'registros.csv'
OUT = RAIZ / 'results' / 'qc_zzu'

FS = 500
UMBRAL_II = 5.0
UMBRAL_MAX = 10.0
UMBRAL_FLAT = 0.2
UMBRAL_RED = 20.0
WORKERS = 6


def evaluar(ecg_id: str) -> dict:
    ruta = next(DATA.rglob(ecg_id + '.hea')).parent
    rec = wfdb.rdrecord(str(ruta / ecg_id))
    x = rec.p_signal
    nombres = list(rec.sig_name)
    ii = nombres.index('II')
    rangos = np.percentile(x, 99, axis=0) - np.percentile(x, 1, axis=0)
    rango = {n: round(float(r), 2) for n, r in zip(nombres, rangos)}
    v = x[:, ii]
    k = v.size // FS
    flat = (float(np.mean([v[i * FS:(i + 1) * FS].std() == 0
                           for i in range(k)])) if k else 0.0)
    f, p = sps.welch(v, fs=FS, nperseg=min(v.size, 2500))
    red = float(p[(f >= 49) & (f <= 51)].max() / np.median(p[(f >= 20) & (f <= 40)]))
    # derivaciones criticas del pipeline: II (detector/features) y la
    # precordial de fusion: V2 en 12-deriv, V1 en 9-deriv (sin V2)
    fusion = 'V2' if 'V2' in nombres else 'V1'
    otras = max((r for n, r in rango.items() if n not in ('II', fusion)),
                default=0.0)
    return {'registro': ecg_id, 'duracion_s': v.size / FS,
            'rango_ii_mv': rango['II'],
            'deriv_fusion': fusion, f'rango_{fusion.lower()}_mv': rango[fusion],
            'rango_otras_mv': round(otras, 2),
            'frac_flat': round(flat, 4), 'pico_50hz_x': round(red, 1)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    r = pd.read_csv(REG)

    with ProcessPoolExecutor(WORKERS) as ex:
        filas = list(ex.map(evaluar, r.registro, chunksize=64))
    qc = r.merge(pd.DataFrame(filas), on='registro', suffixes=('', '_qc'))

    def causa(fila):
        c = []
        if fila.duracion_s < 10:
            c.append('duracion<10s')
        if fila.rango_ii_mv > UMBRAL_II:
            c.append(f'artefacto_II_{fila.rango_ii_mv}mV')
        col_f = f'rango_{fila.deriv_fusion.lower()}_mv'
        if getattr(fila, col_f) > UMBRAL_MAX:
            c.append(f'fusion_{fila.deriv_fusion}_{getattr(fila, col_f)}mV')
        if fila.frac_flat > UMBRAL_FLAT:
            c.append(f'canal_muerto_{fila.frac_flat:.0%}')
        if fila.pico_50hz_x > UMBRAL_RED:
            c.append(f'red_{fila.pico_50hz_x:.0f}x')
        return '|'.join(c)

    qc['causa_exclusion'] = qc.apply(causa, axis=1)
    qc['calidad_dudosa'] = qc.bsqi_min < 0.95
    qc['artefacto_otras_deriv'] = qc.rango_otras_mv > UMBRAL_MAX
    qc.to_csv(OUT / 'qc_registros.csv', index=False)

    excl = qc[qc.causa_exclusion != '']
    cols = [c for c in ['registro', 'clase', 'edad_anos', 'duracion_s',
                        'rango_ii_mv', 'deriv_fusion', 'rango_v2_mv',
                        'rango_v1_mv', 'frac_flat', 'pico_50hz_x',
                        'causa_exclusion'] if c in excl.columns]
    excl[cols].to_csv(OUT / 'excluidos.csv', index=False)

    resumen = [
        f'registros evaluados: {len(qc)} (100% del corpus)',
        f'excluidos: {len(excl)} ({len(excl)/len(qc):.1%})',
        f'  por causa: '
        + ', '.join(f'{c}={n}' for c, n in
                    excl.causa_exclusion.str.split('|').str[0].value_counts().items()),
        f'excluidos por clase: '
        + ', '.join(f'{k}={v}' for k, v in excl.clase.value_counts().items()),
        f'marcados calidad_dudosa (bsqi<0.95, no se excluyen): {int(qc.calidad_dudosa.sum())}',
        '',
        '== Supervivientes por clase (registros) ==',
        qc[qc.causa_exclusion == ''].clase.value_counts().to_string(),
        '',
        '== Umbrales ==',
        f'dur<10 s | rango_II>{UMBRAL_II} mV | rango_V2/V1(fusion)>{UMBRAL_MAX} mV | '
        f'flat>{UMBRAL_FLAT:.0%} | red>{UMBRAL_RED}x | '
        f'marcas (no exclusion): otras_deriv>{UMBRAL_MAX} mV, bsqi<0.95',
    ]
    (OUT / 'resumen.txt').write_text('\n'.join(resumen))
if __name__ == '__main__':
    main()
