"""Figuras de la Fase 1 (limpieza y caracterización del corpus ZZU) — AP-15-bis.

Consume SOLO los CSV ya versionados de results/fase1_limpieza/ (inventario,
análisis exploratorio y QC) y genera un PNG por figura en
results/fase1_limpieza/figuras/. Sin recalcular nada del dato crudo.

Figuras:
  01_clases_corpus.png     registros/pacientes/minutos por clase (inventario)
  02_demografia.png        mediana de edad + IQR y % masculino por clase
  03_enunciados_aha.png    top 15 enunciados AHA crudos
  04_qc_exclusiones.png    excluidos por causa (categorizada) y por clase
  05_qc_umbral_metricas.png distribución de las métricas de QC (rango II,
                           interferencia 50 Hz) supervivientes vs excluidos
  06_calidad_sqi.png       p05/mediana/p90 de pSQI/basSQI/bSQI por clase
  07_fc_por_clase.png      FC mediana por clase con IQR (validación
                           fisiológica del análisis exploratorio)

Uso: uv run python scripts/visualizar_fase1.py
"""

import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
F1 = RAIZ / 'results' / 'fase1_limpieza'
OUT = F1 / 'figuras'
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({'figure.dpi': 150, 'font.size': 9, 'axes.grid': True,
                     'grid.alpha': .3, 'axes.spines.top': False,
                     'axes.spines.right': False})
CLASES = ['Sinusal', 'SVT', 'VT', 'Paced', 'Otro']
COLOR = dict(zip(CLASES, plt.cm.tab10(np.linspace(0, 1, 10))))


def _guardar(fig, nombre: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / nombre)
    plt.close(fig)
    print(f'  {nombre}')


def fig_clases() -> None:
    df = pd.read_csv(F1 / 'inventario_zzu' / 'clases.csv').set_index('clase').loc[CLASES]
    fig, axs = plt.subplots(1, 3, figsize=(9.5, 3.2))
    for ax, col, tit in zip(axs, ('registros', 'pacientes', 'minutos'),
                            ('Registros', 'Pacientes', 'Minutos de señal')):
        ax.bar(df.index, df[col], color=[COLOR[c] for c in df.index])
        ax.set_title(tit)
        ax.margins(y=.15)
        for i, v in enumerate(df[col]):
            ax.text(i, v, f'{v:,.0f}', ha='center', va='bottom', fontsize=8)
    fig.suptitle('Corpus ZZU pECG por clase (14.190 registros, mapeo AP-1)', y=1.04)
    _guardar(fig, '01_clases_corpus.png')


def fig_demografia() -> None:
    df = pd.read_csv(F1 / 'analisis_zzu' / 'demografia.csv').set_index('clase').loc[CLASES]
    err = np.vstack([df.edad_med - df.edad_p25, df.edad_p75 - df.edad_med])
    fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.2))
    axs[0].bar(CLASES, df.edad_med, yerr=err, capsize=3,
               color=[COLOR[c] for c in CLASES])
    axs[0].set_ylabel('edad (años)')
    axs[0].set_title('Edad: mediana e IQR por clase')
    axs[1].bar(CLASES, df.pct_masculino, color=[COLOR[c] for c in CLASES])
    axs[1].axhline(50, ls='--', c='k', lw=.8)
    axs[1].set_ylabel('% masculino')
    axs[1].set_title('Sexo por clase')
    _guardar(fig, '02_demografia.png')


def fig_aha() -> None:
    df = pd.read_csv(F1 / 'inventario_zzu' / 'aha.csv').head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh(df.descripcion.str.slice(0, 38), df.registros, color='#4878d0')
    ax.set_xlabel('registros')
    ax.set_title('Top 15 enunciados AHA/ACC/HRS (crudo, multi-etiqueta)')
    _guardar(fig, '03_enunciados_aha.png')


def _causa(causa: str) -> str:
    if causa.startswith('duracion'):
        return 'duración <10 s'
    if causa.startswith('artefacto_II'):
        return 'artefacto II (rango >5 mV)'
    if causa.startswith('fusion'):
        return 'electrodo suelto V2/V1 (>10 mV)'
    if causa.startswith('red'):
        return 'interferencia 50 Hz (>20x)'
    return 'otras'


def fig_qc() -> None:
    exc = pd.read_csv(F1 / 'qc_zzu' / 'excluidos.csv')
    qc = pd.read_csv(F1 / 'qc_zzu' / 'qc_registros.csv')
    exc['causa_cat'] = exc.causa_exclusion.map(_causa)
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.6))
    orden = exc.causa_cat.value_counts()
    axs[0].bar(orden.index, orden.values, color='#d65f5f')
    axs[0].set_ylabel('registros excluidos')
    axs[0].set_title(f'Excluidos: {len(exc)}/14.190 (5,3 %) por causa')
    axs[0].margins(y=.15)
    for i, v in enumerate(orden.values):
        axs[0].text(i, v, str(v), ha='center', va='bottom', fontsize=8)
    sup = qc[qc.causa_exclusion.isna() | (qc.causa_exclusion == '')]
    excl_clase = exc.clase.value_counts().reindex(CLASES[:4], fill_value=0)
    sup_clase = sup.clase.value_counts().reindex(CLASES, fill_value=0)
    x = np.arange(len(CLASES))
    axs[1].bar(x - .2, sup_clase, .4, label='aceptados', color='#55a868')
    axs[1].bar(x[:4] + .2, excl_clase, .4, label='excluidos', color='#d65f5f')
    axs[1].set_xticks(x, CLASES)
    axs[1].set_yscale('log')
    axs[1].set_title('QC por clase (escala log)')
    axs[1].legend()
    _guardar(fig, '04_qc_exclusiones.png')


def fig_qc_metricas() -> None:
    qc = pd.read_csv(F1 / 'qc_zzu' / 'qc_registros.csv')
    qc['estado'] = np.where(qc.causa_exclusion.isna() | (qc.causa_exclusion == ''),
                            'aceptado', 'excluido')
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.4))
    for ax, col, umbral, tit in (
        (axs[0], 'rango_ii_mv', 5.0, 'Rango p1–p99 de II (mV)'),
        (axs[1], 'pico_50hz_x', 20.0, 'Pico 50 Hz / piso espectral (x)'),
    ):
        for estado, color in (('aceptado', '#55a868'), ('excluido', '#d65f5f')):
            v = qc.loc[qc.estado == estado, col].clip(upper=60 if col == 'rango_ii_mv' else 80)
            ax.hist(v, bins=40, alpha=.6, label=estado, color=color)
        ax.axvline(umbral, ls='--', c='k', lw=.9, label=f'umbral {umbral:g}')
        ax.set_title(tit)
        ax.legend()
    _guardar(fig, '05_qc_umbral_metricas.png')


def fig_sqi() -> None:
    df = pd.read_csv(F1 / 'inventario_zzu' / 'calidad.csv')
    sqis = ['psqi_min', 'bassqi_min', 'bsqi_min']
    fig, axs = plt.subplots(1, 3, figsize=(9.5, 3.2), sharey=True)
    for ax, sqi in zip(axs, sqis):
        d = df[df.sqi == sqi].set_index('clase').reindex(CLASES)
        y = np.arange(len(CLASES))
        ax.hlines(y, d.p05, d.p90, color='#999', lw=3)
        ax.scatter(d.mediana, y, color='#4878d0', zorder=3, label='mediana')
        ax.set_yticks(y, CLASES if sqi == 'psqi_min' else [''] * 5)
        ax.set_title(sqi.replace('_min', ' mínimo'))
        ax.set_xlabel('valor SQI')
    fig.suptitle('Índices de calidad por derivación (p05–p90) por clase', y=1.04)
    _guardar(fig, '06_calidad_sqi.png')


def fig_fc() -> None:
    df = pd.read_csv(F1 / 'analisis_zzu' / 'hr_por_clase.csv').set_index('clase')
    df = df.reindex([c for c in CLASES if c in df.index])
    err = np.vstack([df.fc_med - df.fc_p25, df.fc_p75 - df.fc_med])
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    ax.bar(df.index, df.fc_med, yerr=err, capsize=3,
           color=[COLOR[c] for c in df.index])
    ax.set_ylabel('FC (lpm)')
    ax.set_title('Frecuencia cardíaca mediana por clase (medida, muestra F12-previa)')
    for i, (v, n) in enumerate(zip(df.fc_med, df.n)):
        ax.text(i, v + err[1][i] + 6, f'n={n}', ha='center', fontsize=8)
    _guardar(fig, '07_fc_por_clase.png')


def main() -> None:
    fig_clases()
    fig_demografia()
    fig_aha()
    fig_qc()
    fig_qc_metricas()
    fig_sqi()
    fig_fc()
    print(f'{len(list(OUT.glob("*.png")))} figuras en {OUT}')


if __name__ == '__main__':
    sys.exit(main())
