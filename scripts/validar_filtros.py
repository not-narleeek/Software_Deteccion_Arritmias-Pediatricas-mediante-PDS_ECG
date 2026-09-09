"""Validador F6 — filtros y preprocesamiento (KPI objetivo 1 del acta).

1. Respuesta en frecuencia de la cadena (RF2) → results/figuras/.
2. Protocolo de distorsión QRS §3.4 sobre ≥ 200 latidos sinusales de
   ≥ 10 registros limpios (sin anotaciones '~') → mediana < 5 %, p90 < 10 %,
   Δ duración QRS < 5 ms. El KPI rige sobre D_morfología (AP-11: la señal
   filtrada se compara contra una referencia in-band suave; la comparación
   contra el crudo, que mezcla limpieza pretendida con distorsión, se
   reporta aparte).
3. Regresión del índice de ventanas: con margen 0 debe reproducir las
   cifras del diseño (§5.1): 1971 Sinusal / 320 SVT / 186 Paced. El índice
   de producción (margen 1 s, regla §5.1/AP-12) se reporta aparte.

Exit != 0 si algún KPI no se cumple (§11 del diseño).
Uso: uv run python scripts/validar_filtros.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecg_pipeline import io, preprocess  # noqa: E402

DATA = (
    ROOT / 'data'
    / 'leipzig-heart-center-ecg-database-arrhythmias-in-children-and-'
    'patients-with-congenital-heart-disease-1.0.0'
)
OUT = ROOT / 'results' / 'validacion_filtros'
ESPERADO_VENTANAS = {'Sinusal': 1971, 'SVT': 320, 'Paced': 186}


def latidos_referencia(ruta: Path, n_por_registro: int = 20) -> np.ndarray:
    """Muestras R de latidos sinusales (anotados) espaciados uniformemente."""
    segs = io.segmentos_ritmo(ruta)
    ann = io.cargar_registro(ruta, derivaciones=['II'])[2]
    simbolos = np.asarray(ann.symbol)
    muestras = np.asarray(ann.sample)
    r = []
    for _, seg in segs[segs['clase'] == 'Sinusal'].iterrows():
        dentro = (muestras >= seg['inicio_muestra']) & (muestras < seg['fin_muestra'])
        r.append(muestras[dentro & np.isin(simbolos, list(io.SIMBOLOS_LATIDO))])
    r = np.concatenate(r) if r else np.array([], dtype=int)
    if r.size > n_por_registro:
        sel = np.linspace(0, r.size - 1, n_por_registro).astype(int)
        r = np.sort(r[sel])
    return r


def validar_distorsion() -> pd.DataFrame:
    """D_morfología (KPI) y D_crudo sobre ≥ 10 registros limpios."""
    limpios = []
    for ruta in io.registros_dataset(DATA, pediatricos=True):
        ann = io.cargar_registro(ruta, derivaciones=['II'])[2]
        if '~' in set(ann.symbol):
            continue
        if latidos_referencia(ruta).size >= 5:
            limpios.append(ruta)
        if len(limpios) >= 12:
            break
    assert len(limpios) >= 10, 'no hay 10 registros limpios (sin "~") con latidos sinusales'
    print(f'\n[2] Distorsión QRS (§3.4) sobre {len(limpios)} registros limpios: '
          + ', '.join(p.name for p in limpios))
    filas = []
    for ruta in limpios:
        x, fs, _ = io.cargar_registro(ruta, derivaciones=['II'])
        y = preprocess.preprocesar(x)
        ref = preprocess.referencia_morfologica(x)
        r = latidos_referencia(ruta)
        for etiqueta, referencia in (('morfologia', ref), ('crudo', x)):
            m = preprocess.distortion_qrs(referencia[:, 0], y[:, 0], r, fs)
            filas.append({'registro': ruta.name, 'metrica': etiqueta, **m, 'n_latidos': r.size})
        print(f'    {ruta.name}: n={r.size}  '
              f'D_morf={filas[-2]["mediana_pct"]:.2f}%  p90={filas[-2]["p90_pct"]:.2f}%  '
              f'ΔQRS={filas[-2]["delta_duracion_qrs_ms"]:.1f} ms')
    df = pd.DataFrame(filas)
    df.drop(columns=['d_pct', 'delta_ms']).to_csv(OUT / 'distorsion_qrs.csv', index=False)
    return df


def validar_indice() -> pd.DataFrame:
    registros = io.registros_dataset(DATA, pediatricos=True)
    # Regresión contra la evidencia F1/F2 (§5.1): las cifras del diseño
    # (1971/320/186) corresponden a ventanas íntegras dentro del segmento
    # (margen 0). El índice de producción usa margen_s=1 (regla §5.1 de
    # seguridad en bordes) y se reporta aparte (AP-12).
    idx_f2 = io.construir_indice_ventanas(registros, io.WindowSpec(margen_s=0.0))
    conteo = idx_f2.groupby('clase').size()
    print('\n[3] Índice de ventanas (29 registros, margen 0 = convención F2):')
    print(conteo.to_string())
    for clase, esperado in ESPERADO_VENTANAS.items():
        obtenido = int(conteo.get(clase, 0))
        assert obtenido == esperado, (
            f'Índice no reproduce F1/F2: {clase} = {obtenido}, esperado {esperado}'
        )
    idx = io.construir_indice_ventanas(registros)  # margen 1 s (producción)
    idx.to_csv(OUT / 'indice_ventanas.csv', index=False)
    prod = idx.groupby('clase').size()
    print(f'    OK — reproduce el diseño §5.1. Índice de producción (margen 1 s): '
          f'{prod.to_dict()} ({int(idx["calidad_dudosa"].sum())} calidad_dudosa AP-6)')
    return idx


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print('[1] Respuesta en frecuencia (RF2)')
    preprocess.documentar_respuesta(salida=str(ROOT / 'results' / 'figuras'))
    print('    figuras y tabla escritas en results/figuras/')
    df = validar_distorsion()
    # KPI sobre el total de latidos (§3.4: ≥ 200 latidos), no media de registros
    morf = df[df['metrica'] == 'morfologia']
    d_total = np.concatenate([np.asarray(v) for v in morf['d_pct']])
    delta_total = np.concatenate([np.asarray(v) for v in morf['delta_ms']])
    crudo = df[df['metrica'] == 'crudo']
    d_crudo = np.concatenate([np.asarray(v) for v in crudo['d_pct']])
    kpi = pd.Series(
        {
            'mediana_pct': float(np.median(d_total)),
            'p90_pct': float(np.percentile(d_total, 90)),
            'delta_duracion_qrs_ms': float(np.median(delta_total)),
            'n_latidos': d_total.size,
        }
    )
    por_registro = morf[['registro', 'mediana_pct', 'p90_pct', 'delta_duracion_qrs_ms', 'n_latidos']]
    print('\nResumen KPI objetivo 1 — D_morfología (agregado sobre %d latidos):' % d_total.size)
    print(kpi.to_string())
    print(f'(referencia: D_crudo mediana {np.median(d_crudo):.2f} % — incluye limpieza pretendida)')
    print('\nPeores registros (D_morfología mediana):')
    print(por_registro.sort_values('mediana_pct', ascending=False).head(4).to_string(index=False))
    fallos = []
    if kpi['mediana_pct'] >= 5.0:
        fallos.append(f"mediana D = {kpi['mediana_pct']:.2f} % >= 5 %")
    if kpi['p90_pct'] >= 10.0:
        fallos.append(f"p90 D = {kpi['p90_pct']:.2f} % >= 10 %")
    if kpi['delta_duracion_qrs_ms'] >= 5.0:
        fallos.append(f"Δ QRS = {kpi['delta_duracion_qrs_ms']:.2f} ms >= 5 ms")
    if fallos:
        print('\nFALLO KPI objetivo 1: ' + '; '.join(fallos))
        sys.exit(1)
    print(f'\nKPI objetivo 1 OK: D mediana {kpi["mediana_pct"]:.2f} % < 5 %, '
          f'p90 {kpi["p90_pct"]:.2f} % < 10 %, Δ QRS {kpi["delta_duracion_qrs_ms"]:.2f} ms < 5 ms')
    validar_indice()
    print('\nvalidar_filtros.py: TODO OK')


if __name__ == '__main__':
    main()
