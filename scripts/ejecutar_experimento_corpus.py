"""Experimento de clasificación sobre el corpus combinado — F14, Etapa II.

Retoma el F9 pausado (WIP 4d52c10, Leipzig solo, Paced colapsaba por falta
de datos) sobre el corpus ampliado (F13: ventanas_features.csv).

Diseño (docs/etapa1_zzu_pecg.md §4.1/§4.7):

  A. Validación dentro de ZZU: 5-fold GroupKFold por PACIENTE anidado
     (models.validacion_grupos) — SVM-RBF primario y RF comparador.
  B. Transferencia por población (cuantifica el domain shift advertido por
     el experto): entrenar en ZZU → evaluar en Leipzig pediátrico (ventanas
     10 s), y el reverso. Nunca se mezclan poblaciones en un mismo fold.

KPI (acta §5, enmienda AP-1 'por clase primaria'): Se/Sp global ≥ 85 %,
F1 ≥ 0.80 por clase primaria, Brier < 0.2 — se evalúan en el experimento A
(dentro de ZZU); B se reporta como evidencia de limitación.

Salidas: results/experimento_corpus/{svm,rf}/ + transferencia/ + resumen.

Uso:  uv run python scripts/ejecutar_experimento_corpus.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecg_pipeline.models import (  # noqa: E402
    ExperimentSpec, curvas_confiabilidad, entrenar_calibrado,
    validacion_grupos,
)

FEAT = ROOT / 'results' / 'corpus' / 'ventanas_features.csv'
OUT = ROOT / 'results' / 'experimento_corpus'
META = {'registro', 'fuente', 'paciente', 'clase', 'ritmo',
        'calidad_dudosa', 'inicio_muestra', 'fin_muestra'}


def exportar(res: dict, nombre: str, dir_out: Path) -> dict:
    dir_out.mkdir(parents=True, exist_ok=True)
    res['predicciones'].to_csv(dir_out / 'predicciones_por_ventana.csv', index=False)
    clases = res['clases']
    pd.DataFrame(res['matriz_confusion_ventanas'],
                 index=clases, columns=clases).to_csv(dir_out / 'matriz_confusion_ventanas.csv')
    pd.DataFrame(res['matriz_confusion_registros'],
                 index=clases, columns=clases).to_csv(dir_out / 'matriz_confusion_registros.csv')
    conf = curvas_confiabilidad(res['y_true'], res['probas'])
    with open(dir_out / 'metricas.json', 'w') as f:
        json.dump({'por_clase': res['metricas_por_clase'], 'macro': res['macro'],
                   'brier': res['brier_multiclase'], 'ic_bootstrap': res['ic_bootstrap'],
                   'confiabilidad': conf}, f, indent=2)
    return {'por_clase': res['metricas_por_clase'], 'macro': res['macro'],
            'brier': res['brier_multiclase']}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(FEAT)
    feats = [c for c in df.columns if c not in META]
    print(f'{len(df)} ventanas, {len(feats)} features, clases: '
          f'{df.clase.value_counts().to_dict()}')

    X, y, pac, fuente = df[feats], df.clase, df.paciente, df.fuente

    # --- A: dentro de ZZU, GroupKFold por paciente ---
    m_zzu = fuente == 'zzu'
    resumen = {}
    for modelo in ('svm', 'rf'):
        print(f'== A: {modelo} (ZZU, GroupKFold-5 por paciente) ==', flush=True)
        res = validacion_grupos(X[m_zzu], y[m_zzu], pac[m_zzu], k=5,
                                spec=ExperimentSpec(modelo=modelo))
        resumen[modelo] = exportar(res, modelo, OUT / modelo)
        mc = resumen[modelo]
        print(f"   Se {mc['macro']['sensibilidad']:.3f} Sp "
              f"{mc['macro']['especificidad']:.3f} F1 {mc['macro']['f1']:.3f} "
              f"Brier {mc['brier']:.3f}")

    # --- B: transferencia entre poblaciones ---
    print('== B: transferencia ZZU→Leipzig y Leipzig→ZZU (SVM) ==', flush=True)
    trans = {}
    for nombre, tr_m, te_m in (('zzu_a_leipzig', m_zzu, ~m_zzu),
                               ('leipzig_a_zzu', ~m_zzu, m_zzu)):
        modelo = entrenar_calibrado(X[tr_m].to_numpy(float), y[tr_m].to_numpy(),
                                    pac[tr_m].to_numpy())
        proba = modelo.predict_proba(X[te_m].to_numpy(float))
        clases = np.array(modelo.classes_)
        pred = clases[np.argmax(proba, axis=1)]
        yt = y[te_m].to_numpy()
        from ecg_pipeline.models import _resultado  # ensamblado §8.2
        res = _resultado(yt, pred, proba, pac[te_m].tolist())
        trans[nombre] = exportar(res, nombre, OUT / 'transferencia' / nombre)
        mc = trans[nombre]
        print(f"   {nombre}: F1 macro {mc['macro']['f1']:.3f} "
              f"Brier {mc['brier']:.3f}")

    # --- KPI (experimento A, modelo primario SVM) ---
    svm = resumen['svm']
    f1_ok = all(v['f1'] >= 0.80 for v in svm['por_clase'].values())
    kpi = {'se_sp': svm['macro']['sensibilidad'] >= .85
           and svm['macro']['especificidad'] >= .85,
           'f1_por_clase': f1_ok, 'brier': svm['brier'] < .2}
    pd.DataFrame([{'modelo': m, **{f'{k}_{c}': round(vv, 3)
                                   for c, d in r['por_clase'].items()
                                   for k, vv in d.items()},
                   'f1_macro': round(r['macro']['f1'], 3), 'brier': round(r['brier'], 3)}
                  for m, r in resumen.items()]).to_csv(OUT / 'resumen_svm_rf.csv', index=False)

    with open(OUT / 'kpi.json', 'w') as f:
        json.dump(kpi, f, indent=2)
    print(f'KPI: {kpi}')
    if not all(kpi.values()):
        sys.exit('F14: KPI no cumplido — diagnóstico en results/experimento_corpus/')
    print('F14 VERDE')


if __name__ == '__main__':
    main()
