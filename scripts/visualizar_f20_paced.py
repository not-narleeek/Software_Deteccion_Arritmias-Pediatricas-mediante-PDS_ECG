"""Genera una lámina técnica de evidencia y arquitectura F20."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
F19 = RAIZ / 'results' / 'dl' / 'f19_datasets'
SALIDA = RAIZ / 'output' / 'f20_rama_hf.png'
SALIDA_ZZU = RAIZ / 'output' / 'f20_gate_zzu.png'


def caja(ax, xy, ancho, alto, texto, color):
    p = FancyBboxPatch(xy, ancho, alto, boxstyle='round,pad=0.02',
                       facecolor=color, edgecolor='#20242b', linewidth=1.2)
    ax.add_patch(p)
    ax.text(xy[0] + ancho / 2, xy[1] + alto / 2, texto,
            ha='center', va='center', fontsize=9, color='#111418')


def main() -> None:
    ptb = pd.read_csv(F19 / 'ptbxl_features_hf.csv')
    resultado = json.loads((F19 / 'baseline_hf_ptbxl.json').read_text())
    trans = resultado['transferencia_ptb_a_leipzig']
    fig = plt.figure(figsize=(13, 7.5), facecolor='#f5f3ee')
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.2], hspace=.35, wspace=.28)

    ax = fig.add_subplot(gs[0, :])
    ax.set_xlim(0, 12); ax.set_ylim(0, 3); ax.axis('off')
    caja(ax, (.2, 1.65), 2.2, .85, 'Shards LP 40 Hz\n12 × 5.000', '#b7d8e8')
    caja(ax, (3.0, 1.65), 2.2, .85, 'ResNet-1D\nmorfología', '#8fc0da')
    caja(ax, (.2, .35), 2.2, .85, 'ECG crudo\ntrain / val', '#f2cf8d')
    caja(ax, (3.0, .35), 2.2, .85, '8 features HF\nlog1p + z-score', '#e9b96e')
    caja(ax, (5.8, .35), 2.2, .85, 'MLP\n8 → 32 → 32', '#df9f55')
    caja(ax, (8.6, 1.0), 1.3, .85, 'Fusión', '#c7b2dd')
    caja(ax, (10.5, 1.0), 1.3, .85, '5 clases', '#a993c7')
    flechas = [((2.4,2.08),(3,2.08)), ((2.4,.78),(3,.78)),
               ((5.2,.78),(5.8,.78)), ((5.2,2.08),(8.6,1.55)),
               ((8, .78),(8.6,1.3)), ((9.9,1.43),(10.5,1.43))]
    for a,b in flechas:
        ax.annotate('', xy=b, xytext=a, arrowprops={'arrowstyle':'->','lw':1.6})
    ax.set_title('F20 · arquitectura propuesta', loc='left', fontsize=15, weight='bold')

    ax = fig.add_subplot(gs[1, 0])
    for y, etiqueta, color in [(0, 'Control', '#3c83a8'), (1, 'PACE', '#d98b39')]:
        valores = np.log10(ptb.loc[ptb.y_paced.eq(y), 'hf_rms_mediana'] + 1e-5)
        ax.hist(valores, bins=28, alpha=.62, density=True, label=etiqueta, color=color)
    ax.set_xlabel('log10 RMS 80–237,5 Hz [mV]')
    ax.set_ylabel('Densidad')
    ax.set_title('Señal HF en PTB-XL', loc='left', weight='bold')
    ax.legend(frameon=False)
    ax.grid(axis='y', alpha=.18)

    ax = fig.add_subplot(gs[1, 1])
    nombres = ['PTB-XL\nCV paciente', 'Leipzig\nglobal', 'Leipzig\npediátrico']
    f1 = [resultado['f1_paced'], trans['global']['f1_paced'],
          trans['pediatrico']['f1_paced']]
    barras = ax.bar(nombres, f1, color=['#3c83a8', '#8d6cab', '#d98b39'], width=.62)
    ax.set_ylim(0, 1.05); ax.set_ylabel('F1 Paced')
    ax.set_title('Generalización sin ajuste', loc='left', weight='bold')
    ax.grid(axis='y', alpha=.18)
    for b, v in zip(barras, f1):
        ax.text(b.get_x()+b.get_width()/2, v+.025, f'{v:.3f}', ha='center', weight='bold')

    fig.suptitle('Paced: conservar morfología y recuperar la banda perdida',
                 x=.06, y=.98, ha='left', fontsize=18, weight='bold')
    fig.text(.06, .015, 'F19 → F20 · test ZZU no consultado', fontsize=9, color='#555')
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SALIDA, dpi=180, bbox_inches='tight')
    print(SALIDA)

    side = pd.read_csv(RAIZ / 'results/dl/sidecar_hf_train_val.csv')
    man = pd.read_csv(RAIZ / 'results/dl/manifiesto.csv')
    splits = pd.read_csv(RAIZ / 'results/dl/splits.csv', index_col=0)['particion']
    man = man.merge(splits, left_on='paciente', right_index=True)
    zzu = side.merge(man[['window_id', 'clase']], on='window_id')
    zzu['grupo'] = 'No-Paced desarrollo'
    zzu.loc[(zzu.clase == 'Paced') & (zzu.particion == 'train'), 'grupo'] = 'Paced train'
    zzu.loc[(zzu.clase == 'Paced') & (zzu.particion == 'val'), 'grupo'] = 'Paced val\nP05649'
    orden = ['No-Paced desarrollo', 'Paced train', 'Paced val\nP05649']
    colores = ['#7fa8bb', '#dc963e', '#b84c4c']
    fig2, axs = plt.subplots(1, 2, figsize=(12, 5.6), facecolor='#f5f3ee')
    for ax, feature, titulo in [
        (axs[0], 'hf_rms_mediana', 'Energía HF'),
        (axs[1], 'sincronia_hf_q999', 'Sincronía multiderivación'),
    ]:
        datos = []
        for grupo in orden:
            valores = zzu.loc[zzu.grupo == grupo, feature]
            if len(valores) > 3000:
                valores = valores.sample(3000, random_state=20)
            datos.append(np.log10(valores.to_numpy() + 1e-6))
        b = ax.boxplot(datos, tick_labels=orden, patch_artist=True, showfliers=False,
                       medianprops={'color':'#20242b','linewidth':1.8})
        for caja_plot, color in zip(b['boxes'], colores):
            caja_plot.set_facecolor(color); caja_plot.set_alpha(.82)
        ax.set_title(titulo, loc='left', weight='bold')
        ax.set_ylabel(f'log10 {feature}')
        ax.grid(axis='y', alpha=.2)
    fig2.suptitle('Gate F20 · P05649 no presenta la firma HF de Paced train',
                  x=.06, ha='left', fontsize=17, weight='bold')
    fig2.text(.06, .02,
              'Screening train→val: 0/8 Paced detectadas · GPU detenida · test no consultado',
              fontsize=10, color='#8f2f2f', weight='bold')
    fig2.tight_layout(rect=(0, .06, 1, .93))
    fig2.savefig(SALIDA_ZZU, dpi=180, bbox_inches='tight')
    print(SALIDA_ZZU)


if __name__ == '__main__':
    main()
