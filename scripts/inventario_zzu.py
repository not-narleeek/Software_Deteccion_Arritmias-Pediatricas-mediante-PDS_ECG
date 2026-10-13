"""Inventario del dataset ZZU-pECG — Etapa II-B (rama busqueda-datos, AP-13).

ZZU pECG (Zhengzhou University, Sci Data 12:867, 2025): 14.190 registros
ECG (500 Hz, WFDB) de 11.643 niños 0–14 años hospitalizados. Etiquetas por
registro: enunciados ECG AHA/ACC/HRS 2007 + CHN 2019 (multi-etiqueta con
';') e ICD-10 de alta; SQI por derivación (pSQI/basSQI/bSQI).

Genera (results/fase1_limpieza/inventario_zzu/):

  registros.csv   — metadatos + clase mapeada + SQI mínimo por registro
  aha.csv         — frecuencia de cada enunciado AHA (código base)
  clases.csv      — registros, minutos y ventanas estimadas por clase
  calidad.csv     — distribución de SQI por clase (para el filtro AP-13)
  verificacion.txt— consistencia diccionario vs cabeceras WFDB

Mapeo de enunciados AHA a la taxonomía AP-1 (prioridad de arriba a abajo;
un registro con varias etiquetas queda en la clase más específica):

  Paced   : 'Pacing rhythm' N(180+181)
  VT      : G70, G72, G74
  SVT     : E50 (AFIB, AP-2), E51 (AFL), E52 (EAT), E54 (juncional), E55
  Sinusal : A1, A2, C21, C22, C23, C25, C26 (familia sinusal)
  Otro    : resto (escapes, bloqueos AV sin marcapasos, etc.)

NOTA: igual que en F1, este mapeo es propuesta del equipo pendiente de
validación del experto (AP-1/2/3); aha.csv conserva la distribución cruda.

Uso:  uv run python scripts/inventario_zzu.py
"""

import re
from collections import Counter
from pathlib import Path

import pandas as pd
import wfdb

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / 'data' / 'zzu_pecg' / 'Child_ecg'
DICC = RAIZ / 'data' / 'zzu_pecg' / 'downloads' / 'AttributesDictionary.csv'
CODIGOS = RAIZ / 'data' / 'zzu_pecg' / 'downloads' / 'ECGCode.csv'
OUT = RAIZ / 'results' / 'fase1_limpieza' / 'inventario_zzu'

FS_ESPERADA = 500

# Códigos base por clase (el token del diccionario puede traer sufijos
# '+ModifierNNN'; se comparan códigos base).
CLASE_CODIGOS = {
    'Paced': ['N(180'],
    'VT': ['G70', 'G72', 'G74'],
    'SVT': ['E50', 'E51', 'E52', 'E54', 'E55'],
    'Sinusal': ['A1', 'A2', 'C21', 'C22', 'C23', 'C25', 'C26'],
}
CLASE_TEXTO = {'Paced': 'Pacing rhythm'}
CLASES = ['Paced', 'VT', 'SVT', 'Sinusal', 'Otro']  # prioridad descendente

VENTANA_S, HOP_S = 10, 5  # diseño §5.1; estimación con margen 0 (comparabilidad F2)


def tokens(celda: str) -> list[str]:
    """Tokens AHA de una celda multi-valor (';' separa, comillas simples)."""
    return [t.strip().strip("'") for t in str(celda).split(';') if t.strip()]


def base(token: str) -> str:
    """Código base sin modificadores: 'L145+Modifier362' -> 'L145'."""
    return token.split('+')[0].strip()


def clase_de(toks: list[str]) -> str:
    for clase in CLASES[:-1]:
        texto = CLASE_TEXTO.get(clase)
        if any(base(t) in CLASE_CODIGOS[clase] or (texto and texto in t)
               for t in toks):
            return clase
    return 'Otro'


def sqi_minimo(celda: str) -> float:
    """Mínimo SQI entre derivaciones presentes ('Null' = derivación ausente)."""
    valores = [float(v) for v in re.findall(r':\s*([0-9.]+)\b', str(celda))]
    return min(valores) if valores else float('nan')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dic = pd.read_csv(DICC)
    ecgcode = pd.read_csv(CODIGOS)
    desc = dict(zip(ecgcode['AHA(Category&Code)'], ecgcode.Description))

    dic['aha'] = dic.AHA_code.map(tokens)
    dic['clase'] = dic.aha.map(clase_de)
    dic['psqi_min'] = dic.pSQI.map(sqi_minimo)
    dic['bassqi_min'] = dic.basSQI.map(sqi_minimo)
    dic['bsqi_min'] = dic.bSQI.map(sqi_minimo)
    dic['edad_anos'] = dic.Age.str.rstrip('d').astype(int) / 365.25
    dic['duracion_s'] = dic.Sampling_point / FS_ESPERADA

    # --- verificación contra cabeceras WFDB (muestra completa) ---
    heas = {p.with_suffix('').name: p.parent for p in DATA.rglob('*.hea')}
    assert heas, f'no se encontraron .hea bajo {DATA} — ¿zip extraído?'
    problemas = []
    filas = []
    for _, r in dic.iterrows():
        ecg_id, ruta = r.ECG_ID, heas.get(r.ECG_ID)
        if ruta is None:
            problemas.append(f'{ecg_id}: sin archivo WFDB')
            continue
        h = wfdb.rdheader(str(ruta / ecg_id))
        if h.fs != FS_ESPERADA:
            problemas.append(f'{ecg_id}: fs={h.fs}')
        if h.n_sig != r.Lead:
            problemas.append(f'{ecg_id}: n_sig={h.n_sig} != Lead={r.Lead}')
        if h.sig_len != r.Sampling_point:
            problemas.append(f'{ecg_id}: sig_len={h.sig_len} != {r.Sampling_point}')
        filas.append({
            'registro': ecg_id,
            'paciente': r.Patient_ID,
            'edad_anos': round(r.edad_anos, 2),
            'sexo': r.Gender.strip("'"),
            'fs_hz': h.fs,
            'duracion_s': round(r.duracion_s, 1),
            'n_deriv': int(r.Lead),
            'tiene_v2': 'V2' in h.sig_name,
            'clase': r.clase,
            'aha_crudo': '|'.join(r.aha),
            'icd10_crudo': str(r['ICD-10 code']),
            'psqi_min': round(r.psqi_min, 3),
            'bassqi_min': round(r.bassqi_min, 3),
            'bsqi_min': round(r.bsqi_min, 3),
            'descarta_dur': r.duracion_s < VENTANA_S,
        })
    registros = pd.DataFrame(filas)
    registros.to_csv(OUT / 'registros.csv', index=False)

    # --- distribución cruda de enunciados AHA (códigos base) ---
    conteo = Counter(base(t) for toks in dic.aha for t in toks)
    aha = pd.DataFrame(
        [{'codigo': c, 'descripcion': desc.get(c, '?'), 'registros': n}
         for c, n in conteo.most_common()])
    aha.to_csv(OUT / 'aha.csv', index=False)

    # --- clases: registros, minutos, ventanas estimadas (margen 0) ---
    registros['ventanas_est'] = registros.duracion_s.map(
        lambda d: max(0, int((d - VENTANA_S) // HOP_S) + 1) if d >= VENTANA_S else 0)
    clases = registros.groupby('clase').agg(
        registros=('registro', 'count'),
        pacientes=('paciente', 'nunique'),
        minutos=('duracion_s', lambda s: round(s.sum() / 60, 1)),
        ventanas_est=('ventanas_est', 'sum'),
        dur_menor_10s=('descarta_dur', 'sum'),
    ).reindex(CLASES).fillna(0).astype(int).reset_index()
    clases.to_csv(OUT / 'clases.csv', index=False)

    # --- calidad: SQI mínimo por derivación, distribución por clase ---
    filas_cal = []
    for clase, g in registros.groupby('clase'):
        for col in ('psqi_min', 'bassqi_min', 'bsqi_min'):
            q = g[col].quantile([.05, .5, .9]).round(3)
            filas_cal.append({'clase': clase, 'sqi': col,
                              'p05': q[.05], 'mediana': q[.5], 'p90': q[.9]})
    pd.DataFrame(filas_cal).to_csv(OUT / 'calidad.csv', index=False)

    (OUT / 'verificacion.txt').write_text(
        f'registros diccionario: {len(dic)}\n'
        f'cabeceras leidas: {len(filas)}\n'
        f'inconsistencias: {len(problemas)}\n' + '\n'.join(problemas[:50]))

    print(f"== ZZU pECG: {len(registros)} registros, "
          f"{registros.paciente.nunique()} pacientes ==")
    print(f"Duración total: {registros.duracion_s.sum()/60:.1f} min | "
          f"fs única 500 Hz: {set(registros.fs_hz) == {FS_ESPERADA}} | "
          f"12-deriv: {(registros.n_deriv == 12).sum()} / "
          f"9-deriv: {(registros.n_deriv == 9).sum()}")
    print(f"Sin V2 (9-deriv): {(~registros.tiene_v2).sum()} | "
          f"duración <10 s: {registros.descarta_dur.sum()}")
    print(f"Inconsistencias diccionario vs WFDB: {len(problemas)}")
    print('\n== Registros/minutos/ventanas por clase (mapeo AP-1 propuesto) ==')
    print(clases.to_string(index=False))
    print('\n== Top 15 enunciados AHA (crudo) ==')
    print(aha.head(15).to_string(index=False))


if __name__ == '__main__':
    main()
