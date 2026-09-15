"""Análisis exploratorio del dataset ZZU pECG — Etapa II-B (rama busqueda-datos).

Metodología completa y hallazgos: docs/analisis_zzu_pecg.md.

Cuatro bloques:

  A. Demografía y duraciones por clase (14.190 registros).
  B. Estructura de etiquetas AHA: nº de enunciados por registro,
     co-ocurrencia de grupos de clase y contradicciones (A1 'Normal ECG'
     junto a enunciados anormales).
  C. Validación fisiológica por frecuencia cardíaca sobre MUESTRA
     estratificada (semilla 42): todos Paced/VT/SVT + 200 Sinusal + 200
     Otro. Pipeline por registro: derivación II (por nombre, no índice)
     -> preprocesar (FilterSpec fs=500) -> detectar_picos_r (Kathirvel,

     -> preprocesar (FilterSpec fs=500) -> detectar_picos_r (Kathirvel,
     II-only, fs=500) -> RR -> FC = 60/mediana(RR), CV_RR = std/mean.
  D. Señal y calidad sobre la misma muestra: rango p1–p99 (mV), fracción
     flatline (ventanas 1 s con std==0), pico espectral en 49–51 Hz vs
     piso 20–40 Hz (interferencia de red), potencia < 0,5 Hz (deriva).

Salidas (results/analisis_zzu/): demografia.csv, multietiqueta.csv,
coocurrencia.csv, hr_muestra.csv, hr_por_clase.csv, senal_muestra.csv,
resumen.txt.

Uso:  uv run python scripts/analisis_zzu.py
"""

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal as sps
import wfdb

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'src'))

from ecg_pipeline import preprocess  # noqa: E402
from ecg_pipeline.features import detectar_picos_r  # noqa: E402
from inventario_zzu import CLASES, base, tokens  # noqa: E402

DATA = RAIZ / 'data' / 'zzu_pecg' / 'Child_ecg'
REG = RAIZ / 'results' / 'inventario_zzu' / 'registros.csv'
OUT = RAIZ / 'results' / 'analisis_zzu'

FS = 500
SEED = 42
N_SINUSAL = N_OTRO = 200
GRUPOS = ['Paced', 'VT', 'SVT', 'Sinusal']  # para co-ocurrencia
GRUPO_CODIGOS = {
    'Paced': ['N(180'],
    'VT': ['G70', 'G72', 'G74'],
    'SVT': ['E50', 'E51', 'E52', 'E54', 'E55'],
    'Sinusal': ['A1', 'A2', 'C21', 'C22', 'C23', 'C25', 'C26'],
}
GRUPO_TEXTO = {'Paced': 'Pacing rhythm'}
ESPERADOS = {'Paced': 23, 'VT': 103, 'SVT': 348}


def grupos_de(toks: list[str]) -> set[str]:
    g = set()
    for grupo in GRUPOS:
        texto = GRUPO_TEXTO.get(grupo)
        if any(base(t) in GRUPO_CODIGOS[grupo] or (texto and texto in t)
               for t in toks):
            g.add(grupo)
    return g


def bloque_ab(r: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """A: demografía por clase; B: estructura de etiquetas."""
    demo = r.groupby('clase').agg(
        registros=('registro', 'count'), pacientes=('paciente', 'nunique'),
        edad_med=('edad_anos', 'median'), edad_p25=('edad_anos', lambda s: s.quantile(.25)),
        edad_p75=('edad_anos', lambda s: s.quantile(.75)),
        pct_masculino=('sexo', lambda s: 100 * (s == 'Male').mean()),
        dur_med_s=('duracion_s', 'median'),
    ).reindex(CLASES).round(2).reset_index()

    r = r.copy()
    r['toks'] = r.aha_crudo.str.split('|')
    r['n_enunciados'] = r.toks.map(len)
    r['grupos'] = r.toks.map(grupos_de)
    r['n_grupos'] = r.grupos.map(len)

    multi = pd.DataFrame({
        'metrica': [
            'enunciados por registro (mediana / p90 / max)',
            'registros con >1 enunciado',
            'registros con enunciados de >1 grupo de clase',
            'registros A1 con algun enunciado anormal',
            'registros solo A1 (normal puro)',
        ],
        'valor': [
            f"{r.n_enunciados.median():.0f} / {r.n_enunciados.quantile(.9):.0f} / {r.n_enunciados.max()}",
            f"{(r.n_enunciados > 1).mean():.1%}",
            f"{(r.n_grupos > 1).mean():.1%} ({(r.n_grupos > 1).sum()})",
            f"{r.toks.map(lambda t: 'A1' in t and any(x != 'A1' and not x.startswith('Modifier') for x in t)).mean():.1%}",
            f"{r.toks.map(lambda t: t == ['A1']).sum()}",
        ],
    })

    pares = Counter()
    for gs in r.grupos:
        gs = sorted(gs)
        for i in range(len(gs)):
            for j in range(i + 1, len(gs)):
                pares[(gs[i], gs[j])] += 1
    coo = (pd.DataFrame([{'grupo_1': a, 'grupo_2': b, 'registros': n}
                         for (a, b), n in pares.items()])
           .sort_values('registros', ascending=False))
    return demo, multi, coo


def leer_ii(ecg_id: str) -> np.ndarray:
    ruta = next(DATA.rglob(ecg_id + '.hea')).parent
    rec = wfdb.rdrecord(str(ruta / ecg_id))
    return rec.p_signal[:, rec.sig_name.index('II')].astype(np.float64)


def analizar_registro(ecg_id: str) -> dict:
    """Bloques C y D para un registro (derivación II)."""
    x = leer_ii(ecg_id)
    n = x.size
    spec = preprocess.FilterSpec(fs=FS)
    y = preprocess.preprocesar(x, spec)
    picos = detectar_picos_r(y, fs=FS)
    rr = np.diff(picos) / FS
    fc = 60 / np.median(rr) if rr.size >= 4 else np.nan
    cv = rr.std(ddof=1) / rr.mean() if rr.size >= 4 else np.nan

    f, p = sps.welch(x, fs=FS, nperseg=min(n, 2500))
    pico_red = p[(f >= 49) & (f <= 51)].max() / np.median(p[(f >= 20) & (f <= 40)])
    deriva = p[f < 0.5].sum() / p.sum()
    vent = FS
    k = n // vent
    flat = float(np.mean([x[i * vent:(i + 1) * vent].std() == 0 for i in range(k)])) if k else np.nan

    return {'registro': ecg_id, 'n_latidos': int(picos.size), 'fc_bpm': round(fc, 1),
            'cv_rr': round(cv, 3), 'rango_mv': round(np.percentile(x, 99) - np.percentile(x, 1), 2),
            'frac_flat': round(flat, 4), 'pico_50hz_x': round(float(pico_red), 1),
            'p_pot_lt_05hz': round(float(deriva), 4)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    r = pd.read_csv(REG)

    demo, multi, coo = bloque_ab(r)
    demo.to_csv(OUT / 'demografia.csv', index=False)
    multi.to_csv(OUT / 'multietiqueta.csv', index=False)
    coo.to_csv(OUT / 'coocurrencia.csv', index=False)

    # muestra estratificada reproducible
    rng = np.random.default_rng(SEED)
    muestra = pd.concat([
        r[r.clase.isin(ESPERADOS)],
        r[r.clase == 'Sinusal'].sample(N_SINUSAL, random_state=rng),
        r[r.clase == 'Otro'].sample(N_OTRO, random_state=rng),
    ])
    filas = [analizar_registro(reg) for reg in muestra.registro]
    hr = muestra.merge(pd.DataFrame(filas), on='registro')
    hr.to_csv(OUT / 'hr_muestra.csv', index=False)

    hr['det_ok'] = hr.fc_bpm.between(30, 260) & (hr.n_latidos >= 8)
    hr['subgrupo'] = hr.aha_crudo.map(
        lambda s: next((c for c in ('C21', 'C22', 'C23', 'A1', 'A2')
                        if c in s.split('|')), 'otro'))

    por_clase = (hr[hr.det_ok].groupby('clase')
                 .agg(n=('registro', 'count'), det_ok=('det_ok', 'sum'),
                      fc_med=('fc_bpm', 'median'),
                      fc_p25=('fc_bpm', lambda s: s.quantile(.25)),
                      fc_p75=('fc_bpm', lambda s: s.quantile(.75)),
                      cv_rr_med=('cv_rr', 'median'))
                 .reindex(CLASES).round(2).reset_index())
    por_clase.to_csv(OUT / 'hr_por_clase.csv', index=False)

    hr.groupby('clase')[['rango_mv', 'frac_flat', 'pico_50hz_x', 'p_pot_lt_05hz']] \
        .median().round(3).to_csv(OUT / 'senal_muestra.csv')

    resumen = [
        f'registros analizados (A/B): {len(r)} | muestra C/D: {len(hr)} '
        f'(det_ok {hr.det_ok.sum()}/{len(hr)})',
        '',
        '== A. Demografia por clase ==', demo.to_string(index=False),
        '', '== B. Estructura de etiquetas ==', multi.to_string(index=False),
        '', '== Co-ocurrencia de grupos (top 8) ==',
        coo.head(8).to_string(index=False),
        '', '== C. FC por clase (muestra, det_ok) ==', por_clase.to_string(index=False),
        '', '== C2. FC por subgrupo sinusal ==',
        hr[hr.det_ok & (hr.clase == 'Sinusal')].groupby('subgrupo')
        .fc_bpm.agg(['count', 'median', lambda s: s.quantile(.25), lambda s: s.quantile(.75)])
        .round(0).to_string(),
        '', '== D. Senal (medianas por clase) ==',
        hr.groupby('clase')[['rango_mv', 'frac_flat', 'pico_50hz_x', 'p_pot_lt_05hz']]
        .median().round(3).to_string(),
    ]
    (OUT / 'resumen.txt').write_text('\n'.join(resumen))
    print('\n'.join(resumen))


if __name__ == '__main__':
    main()
