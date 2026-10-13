"""Experimento de clasificación sobre el corpus ZZU — F14, Etapa II.

Corpus ZZU-only (depuración oct-2026: Leipzig eliminado del proyecto).

Diseño (docs/etapa1_zzu_pecg.md §4.1/§4.7):

  Validación dentro de ZZU: 5-fold GroupKFold por PACIENTE anidado
  (models.validacion_grupos) — SVM-RBF primario y RF comparador.
  KPI (acta §5, enmienda AP-1 'por clase primaria'): Se/Sp global >= 85 %,
  F1 >= 0.80 por clase primaria, Brier < 0.2.

F14-bis: submuestreo de la clase mayoritaria (ratio 3x segunda clase) SOLO
en entrenamiento (diagnóstico F14: colapso a Sinusal con 95 % de mayoría).
"""

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore', category=FutureWarning)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecg_pipeline.models import (  # noqa: E402
    ExperimentSpec, curvas_confiabilidad, validacion_grupos,
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

    X, y, pac = df[feats], df.clase, df.paciente
    resumen = {}
    for modelo in ('svm', 'rf'):
        print(f'== {modelo} (ZZU, GroupKFold-5 por paciente, equilibrar 3x) ==',
              flush=True)
        res = validacion_grupos(X, y, pac, k=5,
                                spec=ExperimentSpec(modelo=modelo), equilibrar=3.0)
        resumen[modelo] = exportar(res, modelo, OUT / modelo)
        mc = resumen[modelo]
        print(f"   Se {mc['macro']['sensibilidad']:.3f} Sp "
              f"{mc['macro']['especificidad']:.3f} F1 {mc['macro']['f1']:.3f} "
              f"Brier {mc['brier']:.3f}")

    # --- KPI (modelo primario SVM) ---
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
