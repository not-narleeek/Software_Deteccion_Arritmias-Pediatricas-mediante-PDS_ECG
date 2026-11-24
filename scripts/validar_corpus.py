"""Verificación del corpus ZZU pECG — F11 (depuración ZZU-only, oct-2026).

Construye el índice de ventanas ZZU (io.construir_indice_ventanas_zzu,
10 s/hop 5 s/margen 0) y FALLA (exit ≠ 0) si alguna comprobación no se
cumple:

  1. Totales por clase == esperados desde el QC (misma fórmula de
     ventanas; docs/etapa1_zzu_pecg.md §2).
  2. Carga de muestra: 5 ventanas por tipo (zzu 12-deriv, zzu 9-deriv):
     forma [n×12] en orden SURFACE, valores finitos, escala mV.
  3. Humo de pipeline: preprocesar (fs 500) + detector fusión (V2 índice
     7 en 12-deriv; V1 índice 6 en 9-deriv) devuelven picos con FC
     plausible.

Salida: results/fase2_pipeline/corpus/indice_ventanas.csv + verificacion_corpus.txt.

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

OUT = ROOT / 'results' / 'fase2_pipeline' / 'corpus'
QC_ZZU = ROOT / 'results' / 'fase1_limpieza' / 'qc_zzu' / 'qc_registros.csv'

errores: list[str] = []


def check(nombre: str, ok: bool, detalle: str = '') -> None:
    print(f"[{'OK' if ok else 'FALLA'}] {nombre}" + (f' — {detalle}' if detalle else ''))
    if not ok:
        errores.append(nombre)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    idx = io.construir_indice_ventanas_zzu(
        QC_ZZU, io.WindowSpec(dur_s=10, hop_s=5, min_seg_s=10, margen_s=0.0)
    )
    idx.to_csv(OUT / 'indice_ventanas.csv', index=False)
    print(f'índice ZZU: {len(idx)} ventanas')
    rng = np.random.default_rng(7)

    # 1. totales por clase == esperados desde QC
    qc = pd.read_csv(QC_ZZU)
    sup = qc[qc.causa_exclusion.isna() | (qc.causa_exclusion == '')]
    esp = ((sup.duracion_s_qc - 10) // 5 + 1).clip(lower=0).groupby(sup.clase).sum() \
        .astype(int).to_dict()
    cl = idx.clase.value_counts().to_dict()
    check('totales ZZU por clase == QC', cl == esp, f'{cl} vs {esp}')

    # 2. carga de muestra por tipo
    zzu_reg = idx.registro.unique()
    hea9 = set(idx.registro) & set(qc.loc[qc.n_deriv == 9, 'registro'])
    muestras = {
        'zzu_12d': rng.choice([r for r in zzu_reg if r not in hea9], 5, replace=False).tolist(),
        'zzu_9d': rng.choice(sorted(hea9), 5, replace=False).tolist(),
    }
    for grupo, regs in muestras.items():
        ok_forma = ok_fin = ok_escala = True
        for r in regs:
            x, fs, _ = io.cargar_registro_zzu(r)
            ok_forma &= x.shape[1] == 12 and fs == 500.0
            ok_fin &= bool(np.isfinite(x).all())
            ok_escala &= bool(np.percentile(np.abs(x), 99) < 10)
        check(f'carga {grupo}: [n×12] finitas, escala mV, fs 500',
              ok_forma and ok_fin and ok_escala)

    # 3. humo: preprocesar + fusión (V2 en 12-deriv, V1 en 9-deriv)
    for grupo, regs in muestras.items():
        n_picos = []
        for r in regs[:2]:
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
        f'ventanas ZZU: {len(idx)}',
        'por clase:',
        idx.groupby('clase').size().to_string(),
        f'calidad_dudosa: {int(idx.calidad_dudosa.sum())} ventanas',
        '', 'errores: ' + ('ninguno' if not errores else str(errores)),
    ]
    (OUT / 'verificacion_corpus.txt').write_text('\n'.join(informe))
    if errores:
        sys.exit(f'F11 FALLA: {errores}')
    print('F11 VERDE')


if __name__ == '__main__':
    main()
