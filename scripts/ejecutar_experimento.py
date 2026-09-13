"""Experimento F9 — clasificación LORO anidada, calibración y KPIs 3/4.

Dataset: results/features/ventanas_features.csv (cache de F8; se construye
si no existe). Clases primarias (AP-1): Sinusal / SVT / Paced. Features:
46 finales (base + wavelet db4, decisión F8).

Ejecuta SVM-RBF (primario) y Random Forest (comparador obligatorio), ambos
con calibración Platt, LORO anidado por registro; reporta Se/Sp/F1 por
clase y macro, matrices (ventanas y voto por registro), Brier multiclase,
IC bootstrap y curvas de confiabilidad.

KPI (acta): Se y Sp >= 85 % global, F1 >= 0.80 por clase primaria (SVM),
Brier < 0.2. Exit != 0 si el modelo primario no los cumple.

Uso: uv run python scripts/ejecutar_experimento.py
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ecg_pipeline import features, io, models  # noqa: E402

DATA = (
    ROOT / 'data'
    / 'leipzig-heart-center-ecg-database-arrhythmias-in-children-and-'
    'patients-with-congenital-heart-disease-1.0.0'
)
OUT = ROOT / 'results' / 'experimento'
KPI = {'se_macro': 0.85, 'sp_macro': 0.85, 'f1_clase': 0.80, 'brier': 0.20}


def graficar_confiabilidad(conf: dict, titulo: str, ruta: Path) -> None:
    clases = list(conf.keys())
    fig, axs = plt.subplots(1, len(clases), figsize=(4.5 * len(clases), 4), sharey=True)
    if len(clases) == 1:
        axs = [axs]
    for ax, c in zip(axs, clases):
        d = conf[c]
        ax.plot([0, 1], [0, 1], 'k--', lw=0.8)
        ax.plot(d['confianza_media'], d['fraccion_positivos'], 'o-')
        ax.set_title(f"{c} (Brier {d['brier']:.3f})")
        ax.set_xlabel('Confianza media')
        ax.grid(alpha=0.3)
    axs[0].set_ylabel('Fracción de positivos')
    fig.suptitle(f'Diagrama de confiabilidad — {titulo} (Platt)')
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def ejecutar(df: pd.DataFrame, spec: models.ExperimentSpec, nombre: str) -> dict:
    print(f'\n=== {nombre} (modelo={spec.modelo}) ===')
    res = models.validacion_loro(df[list(features.FEATURES_FINALES)], df['clase'], df['registro'], spec)
    salida = OUT / nombre
    salida.mkdir(parents=True, exist_ok=True)
    res['predicciones'].to_csv(salida / 'predicciones_por_ventana.csv', index=False)
    clases = res['clases']
    pd.DataFrame(
        res['matriz_confusion_ventanas'], index=clases, columns=clases
    ).to_csv(salida / 'matriz_confusion_ventanas.csv')
    pd.DataFrame(
        res['matriz_confusion_registros'], index=clases, columns=clases
    ).to_csv(salida / 'matriz_confusion_registros.csv')
    conf = models.curvas_confiabilidad(res['y_true'], res['probas'])
    graficar_confiabilidad(conf, nombre, salida / 'confiabilidad.png')
    resumen = {
        'macro': res['macro'],
        'por_clase': res['metricas_por_clase'],
        'brier_multiclase': res['brier_multiclase'],
        'ic_bootstrap': res['ic_bootstrap'],
        'brier_por_clase': {c: conf[c]['brier'] for c in conf},
    }
    (salida / 'metricas.json').write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"macro: Se={res['macro']['sensibilidad']:.4f} Sp={res['macro']['especificidad']:.4f} "
          f"F1={res['macro']['f1']:.4f} | Brier={res['brier_multiclase']:.4f} "
          f"| IC95 F1=[{res['ic_bootstrap']['f1_macro_p2.5']:.3f}, {res['ic_bootstrap']['f1_macro_p97.5']:.3f}]")
    for c, m in res['metricas_por_clase'].items():
        print(f"  {c:8s} Se={m['sensibilidad']:.4f} Sp={m['especificidad']:.4f} F1={m['f1']:.4f} (n={m['soporte']})")
    return resumen


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cache = ROOT / 'results' / 'features' / 'ventanas_features.csv'
    df = features.construir_dataset(io.registros_dataset(DATA, pediatricos=True), cache=cache)
    df = df[df['clase'].isin(io.CLASES_PRIMARIAS)].reset_index(drop=True)
    print(f"Dataset: {len(df)} ventanas de {df['registro'].nunique()} registros "
          f"({df['clase'].value_counts().to_dict()})")
    svm = ejecutar(df, models.ExperimentSpec(modelo='svm'), 'svm')
    rf = ejecutar(df, models.ExperimentSpec(modelo='rf'), 'rf')
    pd.DataFrame(
        {
            'svm': {**svm['macro'], 'brier': svm['brier_multiclase']},
            'rf': {**rf['macro'], 'brier': rf['brier_multiclase']},
        }
    ).to_csv(OUT / 'resumen_svm_rf.csv')
    fallos = []
    if svm['macro']['sensibilidad'] < KPI['se_macro']:
        fallos.append(f"Se macro {svm['macro']['sensibilidad']:.3f} < {KPI['se_macro']}")
    if svm['macro']['especificidad'] < KPI['sp_macro']:
        fallos.append(f"Sp macro {svm['macro']['especificidad']:.3f} < {KPI['sp_macro']}")
    for c, m in svm['por_clase'].items():
        if m['f1'] < KPI['f1_clase']:
            fallos.append(f"F1 {c} {m['f1']:.3f} < {KPI['f1_clase']}")
    if svm['brier_multiclase'] >= KPI['brier']:
        fallos.append(f"Brier {svm['brier_multiclase']:.3f} >= {KPI['brier']}")
    if fallos:
        print('\nFALLO KPI 3/4: ' + '; '.join(fallos))
        sys.exit(1)
    print('\nKPI 3/4 OK (SVM primario): Se/Sp macro >= 85 %, F1 por clase >= 0.80, Brier < 0.2')


if __name__ == '__main__':
    main()
