"""Extracción de features sobre el corpus ZZU — F13, Etapa II.

Dataset de ventanas (una fila por ventana de results/corpus/
indice_ventanas.csv) con el vector §6 de 46 features + wavelet, para las
CLASES PRIMARIAS (Sinusal/SVT/VT/Paced; 'Otro' es clase reportada, no
objetivo — docs/etapa1_zzu_pecg.md §4.5).

Pipeline por registro (paralelo, 6 workers): cargar → preprocesar
completo (FilterSpec fs por fuente) → detectar R (fusión II+V2 o II+V1 si
no hay V2) y espículas sobre la señal completa → rebanar ventanas del
índice → features.vector_caracteristicas por ventana.

Salidas: results/corpus/ventanas_features.csv y separabilidad.csv
(ANOVA+Fisher entre las 4 clases) + resumen.txt.

Uso:  uv run python scripts/extraer_features_corpus.py
"""

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecg_pipeline import io, preprocess  # noqa: E402
from ecg_pipeline.features import (  # noqa: E402
    detectar_picos_r_fusion, separabilidad, vector_caracteristicas,
)

IDX = ROOT / 'results' / 'corpus' / 'indice_ventanas.csv'
OUT = ROOT / 'results' / 'corpus'
WORKERS = 6
PRIMARIAS = ('Sinusal', 'SVT', 'VT', 'Paced')


def procesar_registro(args: tuple) -> list[dict]:
    reg, fuente, filas_idx = args
    x, fs, presentes = io.cargar_registro_zzu(reg)
    edad = float(filas_idx[0]['edad_anos'])
    sexo = int(filas_idx[0]['sexo'])
    spec = preprocess.FilterSpec(fs=int(fs))
    y = preprocess.preprocesar(x, spec)
    idx_v = 7 if 'V2' in presentes else 6
    picos = detectar_picos_r_fusion(y.astype(np.float64), fs, idx_v=idx_v)
    espiculas = preprocess.detectar_espiculas_multiderivacion(
        x.astype(np.float64), fs)
    filas = []
    for f in filas_idx:
        i0, i1 = f['inicio_muestra'], f['fin_muestra']
        loc = picos[(picos >= i0) & (picos < i1)] - i0
        esp = espiculas[(espiculas >= i0) & (espiculas < i1)] - i0
        fv = vector_caracteristicas(
            y[i0:i1], loc, esp, edad, sexo, fs, ventana_raw=x[i0:i1])
        fv.update(registro=reg, fuente=fuente, paciente=f['paciente'],
                  clase=f['clase'], ritmo=f['ritmo'],
                  calidad_dudosa=bool(f['calidad_dudosa']),
                  inicio_muestra=i0, fin_muestra=i1)
        filas.append(fv)
    return filas


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    idx = pd.read_csv(IDX)
    idx = idx[idx.clase.isin(PRIMARIAS)].copy()
    idx['clase'] = idx.clase.astype(str)

    trabajos = [
        (reg, g.fuente.iloc[0],
         g[['paciente', 'clase', 'ritmo', 'inicio_muestra', 'fin_muestra',
            'calidad_dudosa', 'edad_anos', 'sexo']].to_dict('records'))
        for reg, g in idx.groupby('registro', sort=True)
    ]
    print(f'{len(idx)} ventanas primarias en {len(trabajos)} registros', flush=True)

    filas: list[dict] = []
    with ProcessPoolExecutor(WORKERS) as ex:
        for i, filas_reg in enumerate(ex.map(procesar_registro, trabajos, chunksize=16), 1):
            filas.extend(filas_reg)
            if i % 500 == 0:
                print(f'    {i}/{len(trabajos)} registros', flush=True)

    df = pd.DataFrame(filas)
    df.to_csv(OUT / 'ventanas_features.csv', index=False)

    feats = [c for c in df.columns if c not in
             ('registro', 'fuente', 'paciente', 'clase', 'ritmo', 'calidad_dudosa',
              'inicio_muestra', 'fin_muestra')]
    sep = separabilidad(df[feats], df.clase)
    sep.to_csv(OUT / 'separabilidad.csv', index=False)

    resumen = [
        f'ventanas: {len(df)} | por clase: ' + str(df.clase.value_counts().to_dict()),
        f'por fuente: ' + str(df.fuente.value_counts().to_dict()),
        f'calidad_dudosa: {int(df.calidad_dudosa.sum())}',
        '', '== separabilidad (top 15 por Fisher) ==',
        sep.head(15).to_string(index=False),
    ]
    (OUT / 'resumen_features.txt').write_text('\n'.join(resumen))
    print('\n'.join(resumen))


if __name__ == '__main__':
    main()
