"""Inventario del dataset Leipzig Heart Center ECG — F1, Etapa I (PPS).

Recorre los 39 registros (29 pediátricos + 10 adultos) leyendo únicamente
cabeceras (.hea) y anotaciones (.atr), y genera:

  results/inventario/registros.csv   — metadatos por registro + demografía
  results/inventario/latidos.csv     — conteo de símbolos de latido por registro
  results/inventario/ritmos.csv      — segmentos y minutos por ritmo por registro
  results/inventario/clases.csv      — minutos por clase objetivo (mapeo del acta)

Mapeo de ritmos (WFDB aux de anotaciones '+', según dataset_info.csv) a las
5 clases objetivo del acta:

  Sinusal : (N
  SVT     : (AVRT (AVNRT (EAT (A (J (AFIB   — taquiarritmias supraventriculares
  VT      : (VT (IVR
  AFL     : (AFL
  Paced   : (/A (/V
  Otro    : (B (bigeminismo ventricular; patrón ectópico, no ritmo sostenido)

NOTA: clasificar AFIB bajo SVT y excluir (B son decisiones de diseño
propuestas por el equipo, pendientes de validación del experto asesor
(Diego Maureira). ritmos.csv conserva la distribución cruda para revisarla.

Uso:  uv run python scripts/inventario.py
"""

from collections import Counter
from pathlib import Path

import pandas as pd
import wfdb

DATA = Path(__file__).resolve().parents[1] / 'data' / (
    'leipzig-heart-center-ecg-database-arrhythmias-in-children-and-'
    'patients-with-congenital-heart-disease-1.0.0'
)
OUT = Path(__file__).resolve().parents[1] / 'results' / 'inventario'

SURFACE = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

CLASE = {
    '(N': 'Sinusal',
    '(AVRT': 'SVT', '(AVNRT': 'SVT', '(EAT': 'SVT', '(A': 'SVT', '(J': 'SVT', '(AFIB': 'SVT',
    '(VT': 'VT', '(IVR': 'VT',
    '(AFL': 'AFL',
    '(/A': 'Paced', '(/V': 'Paced',
    '(B': 'Otro',
}


def segmentos_ritmo(ann, sig_len, fs):
    """Duración en minutos de cada segmento de ritmo (anotaciones '+')."""
    idx = [i for i, (s, a) in enumerate(zip(ann.symbol, ann.aux_note)) if s == '+' and a]
    segs = []
    for j, i in enumerate(idx):
        ini = ann.sample[i]
        fin = ann.sample[idx[j + 1]] if j + 1 < len(idx) else sig_len
        segs.append((ann.aux_note[i].strip(), (fin - ini) / fs / 60))
    return segs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = [r.strip() for r in (DATA / 'RECORDS').read_text().splitlines() if r.strip()]

    demo = pd.concat([
        pd.read_csv(DATA / 'children-subject-info.csv').assign(grupo='pediatrico'),
        pd.read_csv(DATA / 'adults-subject-info.csv').assign(grupo='adulto'),
    ], ignore_index=True)

    filas_reg, filas_lat, filas_rit = [], [], []
    for name in records:
        header = wfdb.rdheader(str(DATA / name))
        ann = wfdb.rdann(str(DATA / name), 'atr')

        d = demo.loc[demo.file_name == name].iloc[0]
        filas_reg.append({
            'registro': name,
            'grupo': d.grupo,
            'edad_anos': d.age,
            'sexo': d.gender,
            'diagnostico': d.diagnosis,
            'fs_hz': header.fs,
            'duracion_min': round(header.sig_len / header.fs / 60, 2),
            'n_canales': header.n_sig,
            'n_deriv_superf': sum(1 for s in header.sig_name if s in SURFACE),
            'anot_calidad': ann.symbol.count('~'),
        })

        latidos = Counter(s for s in ann.symbol if s not in ('+', '~'))
        for simbolo, n in sorted(latidos.items()):
            filas_lat.append({'registro': name, 'simbolo': simbolo, 'descripcion': SIMBOLOS.get(simbolo, '?'), 'conteo': n})

        for ritmo, minutos in segmentos_ritmo(ann, header.sig_len, header.fs):
            filas_rit.append({'registro': name, 'grupo': d.grupo, 'ritmo': ritmo,
                              'clase': CLASE.get(ritmo, '?'), 'minutos': round(minutos, 4)})

    registros = pd.DataFrame(filas_reg)
    latidos = pd.DataFrame(filas_lat)
    ritmos = pd.DataFrame(filas_rit)

    registros.to_csv(OUT / 'registros.csv', index=False)
    latidos.to_csv(OUT / 'latidos.csv', index=False)
    ritmos.to_csv(OUT / 'ritmos.csv', index=False)

    clases = (ritmos.groupby(['registro', 'grupo', 'clase'], as_index=False)['minutos'].sum()
              .pivot_table(index=['registro', 'grupo'], columns='clase', values='minutos', fill_value=0)
              .round(2).reset_index())
    clases.to_csv(OUT / 'clases.csv', index=False)

    print(f"== Registros: {len(registros)} "
          f"(pediatricos={len(registros[registros.grupo == 'pediatrico'])}, "
          f"adultos={len(registros[registros.grupo == 'adulto'])}) ==")
    print(f"Duración total: {registros.duracion_min.sum():.1f} min | "
          f"fs único: {registros.fs_hz.unique()} | "
          f"deriv. superficiales siempre 12: {set(registros.n_deriv_superf) == {12}}")
    print(f"Latidos anotados: {latidos.conteo.sum()}")
    print('\n== Minutos por ritmo (crudo, todos los grupos) ==')
    print(ritmos.groupby('ritmo')['minutos'].sum().round(1).sort_values(ascending=False).to_string())
    print('\n== Minutos por clase objetivo (solo pediátricos) ==')
    ped = ritmos[ritmos.grupo == 'pediatrico']
    print(ped.groupby('clase')['minutos'].sum().round(1).sort_values(ascending=False).to_string())
    print('\n== Minutos por clase objetivo (adultos, comparativo) ==')
    adu = ritmos[ritmos.grupo == 'adulto']
    print(adu.groupby('clase')['minutos'].sum().round(1).sort_values(ascending=False).to_string())


# Descripción de símbolos de latido según dataset_info.csv (dataset_symbol).
SIMBOLOS = {
    'N': 'Latido normal',
    'L': 'BRI completo (cLBBBB)',
    'R': 'BRD completo (cRBBBB)',
    'a': 'PAC aberrado (aPAC)',
    'A': 'PAC', 'A-Prex': 'PAC preexcitado (pPAC)',
    'J': 'PJC',
    'V': 'PVC',
    'F': 'Fusión (FB)',
    'f': 'Fusión VPB+NB',
    'X': 'Latido en ritmo arrítmico (AVNRT/AVRT/AFL/AF/IVR/VT/EAT)',
    '/': 'Latido marcapasos', '/A': 'Marcapasos auricular (APB)', '/V': 'Marcapasos ventricular (VPB)',
    'Q': 'Latido no clasificable',
}


if __name__ == '__main__':
    main()
