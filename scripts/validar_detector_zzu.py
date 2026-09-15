"""Validación del detector R sobre el corpus ZZU — F12, Etapa II.

ZZU no tiene anotación latido a latido (`.atr`), por lo que la validación
F7 clásica (Se/+P vs anotaciones) no aplica. Protocolo sustituto
(docs/etapa1_zzu_pecg.md §4.3): consistencia fisiológica a escala completa.

Sobre TODOS los supervivientes del QC (13.436):
  - preprocesar registro completo (FilterSpec fs=500) + fusión II+V2
    (12-deriv) o II+V1 (9-deriv) según derivaciones presentes;
  - det_ok: >= 8 latidos y FC plausible (30–300 lpm si edad < 1 año —
    SVT neonatal medida hasta 273 lpm —, si no 30–260);
  - FC mediana por clase debe ordenarse VT ≈ SVT > Sinusal/Otro.

Degradación de la fusión con V1 (proxy 9-deriv): muestra estratificada de
400 registros de 12 derivaciones comparando fusión V2 vs V1 — diferencia
de FC y razón de latidos.

ACEPTACIÓN (KPI análogo F7): det_ok >= 95 % global y por clase primaria;
orden de FC verificado.

Salidas: results/validacion_detector_zzu/{deteccion.csv, resumen.txt}.

Uso:  uv run python scripts/validar_detector_zzu.py
"""

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecg_pipeline import io, preprocess  # noqa: E402
from ecg_pipeline.features import detectar_picos_r_fusion  # noqa: E402

QC = ROOT / 'results' / 'qc_zzu' / 'qc_registros.csv'
OUT = ROOT / 'results' / 'validacion_detector_zzu'
FS = 500
WORKERS = 6
SEED = 11
def evaluar_registro(reg: str) -> dict:
    x, fs, presentes = io.cargar_registro_zzu(reg)
    y = preprocess.preprocesar(x, preprocess.FilterSpec(fs=int(fs)))
    idx_v = 7 if 'V2' in presentes else 6
    picos = detectar_picos_r_fusion(y.astype(np.float64), fs, idx_v=idx_v)
    rr = np.diff(picos) / fs
    fc = 60 / np.median(rr) if rr.size >= 4 else np.nan
    return {'registro': reg, 'n_latidos': int(picos.size),
            'fc_bpm': round(float(fc), 1) if np.isfinite(fc) else np.nan}


def evaluar_par(reg: str) -> dict:
    """Fusión V2 vs V1 sobre un registro de 12 derivaciones (degradación)."""
    x, fs, _ = io.cargar_registro_zzu(reg)
    y = preprocess.preprocesar(x, preprocess.FilterSpec(fs=int(fs))).astype(np.float64)
    out = {'registro': reg}
    for nombre, idx_v in (('v2', 7), ('v1', 6)):
        picos = detectar_picos_r_fusion(y, fs, idx_v=idx_v)
        rr = np.diff(picos) / fs
        out[f'n_{nombre}'] = int(picos.size)
        out[f'fc_{nombre}'] = round(float(60 / np.median(rr)), 1) if rr.size >= 4 else np.nan
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    qc = pd.read_csv(QC)
    sup = qc[qc.causa_exclusion.isna() | (qc.causa_exclusion == '')][
        ['registro', 'clase', 'edad_anos', 'n_deriv']]

    with ProcessPoolExecutor(WORKERS) as ex:
        det = pd.DataFrame(list(ex.map(evaluar_registro, sup.registro, chunksize=64)))
    det = sup.merge(det, on='registro')
    cota = np.where(det.edad_anos < 1, 300, 260)
    det['det_ok'] = (det.n_latidos >= 8) & det.fc_bpm.between(30, cota)
    det.to_csv(OUT / 'deteccion.csv', index=False)

    por_clase = det.groupby('clase').agg(
        n=('registro', 'count'), det_ok=('det_ok', 'sum'),
        pct=('det_ok', lambda s: 100 * s.mean()),
        fc_med=('fc_bpm', 'median'), fc_p25=('fc_bpm', lambda s: s.quantile(.25)),
        fc_p75=('fc_bpm', lambda s: s.quantile(.75))).round(1)
    por_deriv = det.groupby('n_deriv').det_ok.agg(['count', 'sum', 'mean'])

    # degradación V1 vs V2 en 12-deriv (muestra estratificada por clase)
    rng = np.random.default_rng(SEED)
    d12 = sup[sup.n_deriv == 12]
    muestra = (d12.groupby('clase', group_keys=False)
               .apply(lambda g: g.sample(min(100, len(g)), random_state=rng)))
    with ProcessPoolExecutor(WORKERS) as ex:
        deg = pd.DataFrame(list(ex.map(evaluar_par, muestra.registro, chunksize=32)))
    deg['d_fc'] = (deg.fc_v1 - deg.fc_v2).abs()
    deg['razon_latidos'] = deg.n_v1 / deg.n_v2.replace(0, np.nan)
    deg.to_csv(OUT / 'degradacion_v1v2.csv', index=False)

    global_ok = det.det_ok.mean()
    orden_ok = por_clase.loc['SVT', 'fc_med'] > por_clase.loc['Sinusal', 'fc_med']
    por_clase_ok = (por_clase.pct >= 95).all()

    resumen = [
        f'corpus: {len(det)} registros | det_ok global: {det.det_ok.mean():.1%}',
        '', '== det_ok y FC por clase ==', por_clase.to_string(),
        '', '== det_ok por nº derivaciones ==', por_deriv.to_string(),
        '', f'== degradación V1 vs V2 (n={len(deg)}, 12-deriv) ==',
        f'|ΔFC| mediana: {deg.d_fc.median():.1f} lpm | p90: {deg.d_fc.quantile(.9):.1f}',
        f'razón latidos V1/V2 mediana: {deg.razon_latidos.median():.3f}',
        '', f'ACEPTACIÓN: det_ok≥95% global {global_ok >= .95} | por clase {por_clase_ok} '
        f'| FC SVT>Sinusal {orden_ok}',
    ]
    (OUT / 'resumen.txt').write_text('\n'.join(resumen))
    print('\n'.join(resumen))

    if not (global_ok >= 0.95 and por_clase_ok and orden_ok):
        sys.exit('F12 FALLA: KPI de consistencia no cumplido')
    print('F12 VERDE')


if __name__ == '__main__':
    main()
