"""Verificación del corpus combinado Leipzig+ZZU — F11, Etapa II (rama
etapa2-corpus-combinado).

Construye el índice de ventanas combinado (io.construir_indice_corpus) y
FALLA (exit ≠ 0) si alguna comprobación no se cumple:

  1. Regresión Leipzig: el subconjunto leipzig del índice reproduce el
     índice de producción de F6 (results/validacion_filtros/
     indice_ventanas.csv: 2427 ventanas, 1944/307/176/1 por clase).
  2. Totales ZZU por clase == esperados desde el QC (misma fórmula de
     ventanas; docs/etapa1_zzu_pecg.md §2).
  3. Carga de muestra: 5 ventanas por fuente×tipo (zzu 12-deriv, zzu
     9-deriv, leipzig): forma [n×12] en orden SURFACE, valores finitos,
     escala mV.
  4. Humo de pipeline: preprocesar (fs 500/977) + detector fusión
     (V2 índice 7 en 12-deriv; V1 índice 6 en 9-deriv) devuelven picos.

Salida: results/corpus/indice_ventanas.csv + verificacion_corpus.txt.

Uso:  uv run python scripts/validar_corpus.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecg_pipeline import io, preprocess  # noqa: E402
from ecg_pipeline.features import detectar_picos_r_fusion  # noqa: E402

OUT = ROOT / 'results' / 'corpus'
IDX_F6 = ROOT / 'results' / 'validacion_filtros' / 'indice_ventanas.csv'
QC_ZZU = ROOT / 'results' / 'qc_zzu' / 'qc_registros.csv'

errores: list[str] = []


def check(nombre: str, ok: bool, detalle: str = '') -> None:
    print(f"[{'OK' if ok else 'FALLA'}] {nombre}" + (f' — {detalle}' if detalle else ''))
    if not ok:
        errores.append(nombre)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data_leipzig = next(
        (ROOT / 'data').glob('leipzig-heart-center-ecg-database*')
    )
    idx = io.construir_indice_corpus(data_leipzig, QC_ZZU)
    idx.to_csv(OUT / 'indice_ventanas.csv', index=False)

    lei, zzu = idx[idx.fuente == 'leipzig'], idx[idx.fuente == 'zzu']
    print(f'índice combinado: {len(idx)} ventanas '
          f'(leipzig {len(lei)} / zzu {len(zzu)})')
    rng = np.random.default_rng(7)
    # 1a. regresión spec F6: WindowSpec() por defecto (30 s/15 s/margen 1)
    #     reproduce el índice de producción de F6 (AP-12).
    f6_arch = pd.read_csv(IDX_F6)
    f6_calc = io.construir_indice_ventanas(io.registros_dataset(data_leipzig))
    check('regresión spec F6 (30 s/15 s): total', len(f6_calc) == len(f6_arch),
          f'{len(f6_calc)} vs {len(f6_arch)}')
    check('regresión spec F6: por clase',
          f6_calc.clase.value_counts().to_dict() == f6_arch.clase.value_counts().to_dict())

    # 1b. Leipzig producción (10 s/5 s, spec corpus): cada ventana dentro de
    #     su segmento de ritmo con margen 1 s (muestreo de 5 registros).
    ok_seg = True
    for reg in rng.choice(lei.registro.unique(), 5, replace=False):
        segs = io.segmentos_ritmo(data_leipzig / reg)
        for _, w in lei[lei.registro == reg].iterrows():
            dentro = ((segs.inicio_muestra + 977 <= w.inicio_muestra)
                      & (w.fin_muestra <= segs.fin_muestra - 977)
                      & (segs.clase == w.clase)).any()
            ok_seg &= bool(dentro)
    check('Leipzig 10 s/5 s: ventanas dentro de segmento con margen', ok_seg)

    # 2. totales ZZU por clase == esperados desde QC
    qc = pd.read_csv(QC_ZZU)
    sup = qc[qc.causa_exclusion.isna() | (qc.causa_exclusion == '')]
    esp = ((sup.duracion_s_qc - 10) // 5 + 1).clip(lower=0).groupby(sup.clase).sum() \
        .astype(int).to_dict()
    cl_zzu = zzu.clase.value_counts().to_dict()
    check('totales ZZU por clase == QC', cl_zzu == esp,
          f'{cl_zzu} vs {esp}')

    # 3. carga de muestra por fuente y tipo
    zzu_reg = zzu.registro.unique()
    hea9 = set(qc.loc[qc.n_deriv == 9, 'registro'])
    muestras = {
        'leipzig': rng.choice(lei.registro.unique(), 5, replace=False).tolist(),
        'zzu_12d': rng.choice([r for r in zzu_reg if r not in hea9], 5, replace=False).tolist(),
        'zzu_9d': rng.choice(sorted(hea9), 5, replace=False).tolist(),
    }
    for grupo, regs in muestras.items():
        ok_forma = ok_fin = ok_escala = True
        for r in regs:
            if grupo == 'leipzig':
                ruta = data_leipzig / r
                x, fs, _ = io.cargar_registro(ruta)
                presentes = io.SURFACE
                edad, sexo = io.demografia(ruta)
            else:
                x, fs, presentes = io.cargar_registro_zzu(r)
                edad, sexo = float('nan'), 0
            ok_forma &= x.shape[1] == 12 and fs in (500.0, 977.0)
            ok_fin &= bool(np.isfinite(x).all())
            ok_escala &= bool(np.percentile(np.abs(x), 99) < 10)
        check(f'carga {grupo}: [n×12] finitas, escala mV',
              ok_forma and ok_fin and ok_escala)

    # 4. humo: preprocesar + fusión (V2 en 12-deriv, V1 en 9-deriv)
    for grupo, regs in (('zzu_12d', muestras['zzu_12d'][:2]),
                        ('zzu_9d', muestras['zzu_9d'][:2])):
        n_picos = []
        for r in regs:
            x, fs, presentes = io.cargar_registro_zzu(r)
            spec = preprocess.FilterSpec(fs=int(fs))
            y = preprocess.preprocesar(x, spec)
            idx_v = 7 if 'V2' in presentes else 6
            picos = detectar_picos_r_fusion(y.astype(np.float64), fs, idx_v=idx_v)
            n_picos.append(picos.size)
            rr = np.diff(picos) / fs
            fc = 60 / np.median(rr) if rr.size >= 4 else float('nan')
            assert np.isfinite(fc) and 30 <= fc <= 300, f'{r}: FC={fc}'
        check(f'humo fusión {grupo}: detecta latidos', all(n > 5 for n in n_picos),
              f'picos={n_picos}')

    informe = [
        f'ventanas combinadas: {len(idx)} (leipzig {len(lei)} / zzu {len(zzu)})',
        f'por fuente×clase:',
        idx.groupby(['fuente', 'clase']).size().to_string(),
        f'calidad_dudosa: {int(idx.calidad_dudosa.sum())} ventanas',
        '', 'errores: ' + ('ninguno' if not errores else str(errores)),
    ]
    (OUT / 'verificacion_corpus.txt').write_text('\n'.join(informe))
    if errores:
        sys.exit(f'F11 FALLA: {errores}')
    print('F11 VERDE')


if __name__ == '__main__':
    main()
