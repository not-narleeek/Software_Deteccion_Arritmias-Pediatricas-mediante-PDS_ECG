"""Audita el soporte de Paced por paciente sin evaluar el conjunto test.

Combina las features F13 con el split DL y produce evidencia para decidir si
una etiqueta representa estimulación activa o solo antecedente de marcapasos.
Por defecto limita la salida a train/val; test exige un flag explícito.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FEATURES = RAIZ / 'results' / 'fase2_pipeline' / 'corpus' / 'ventanas_features.csv'
SPLITS = RAIZ / 'results' / 'dl' / 'splits.csv'


def porcentaje_verdadero(serie: pd.Series) -> float:
    valores = serie.map(lambda v: str(v).strip().lower() in {'true', '1', 'yes'})
    return 100.0 * valores.mean()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', type=Path, default=FEATURES)
    ap.add_argument('--splits', type=Path, default=SPLITS)
    ap.add_argument('--salida', type=Path,
                    default=RAIZ / 'results' / 'dl' / 'auditoria_paced')
    ap.add_argument('--incluir-test', action='store_true',
                    help='incluye metadata/features de test; no usar durante desarrollo')
    args = ap.parse_args()

    features = pd.read_csv(args.features)
    splits = pd.read_csv(args.splits, index_col=0)['particion']
    desarrollo = features.merge(splits, left_on='paciente', right_index=True,
                                 validate='many_to_one')
    particiones = ['train', 'val'] + (['test'] if args.incluir_test else [])
    desarrollo = desarrollo[desarrollo.particion.isin(particiones)].copy()
    paced = desarrollo[desarrollo.clase.eq('Paced')].copy()
    if paced.empty:
        raise SystemExit('AUDITORIA FALLA: no hay ventanas Paced en las particiones')

    resumen = paced.groupby(['particion', 'paciente']).agg(
        ventanas=('registro', 'size'),
        registros=('registro', 'nunique'),
        esp_n_media=('esp_n', 'mean'),
        esp_n_mediana=('esp_n', 'median'),
        esp_n_max=('esp_n', 'max'),
        pct_sin_espiculas=('esp_n', lambda s: 100.0 * s.eq(0).mean()),
        rms_gt100_media_uv=('cal_rms_gt100_uv', 'mean'),
        rms_gt100_mediana_uv=('cal_rms_gt100_uv', 'median'),
        pct_calidad_dudosa=('calidad_dudosa', porcentaje_verdadero),
    ).reset_index()
    resumen['requiere_revision'] = (
        resumen.pct_sin_espiculas.eq(100.0)
        | resumen.rms_gt100_mediana_uv.lt(5.0)
    )

    args.salida.mkdir(parents=True, exist_ok=True)
    resumen.to_csv(args.salida / 'paced_por_paciente.csv', index=False)
    paced[['particion', 'paciente', 'registro', 'inicio_muestra', 'fin_muestra',
           'esp_n', 'esp_por_min', 'cal_rms_gt100_uv',
           'calidad_dudosa']].to_csv(args.salida / 'paced_por_ventana.csv',
                                     index=False)

    conteos = {
        particion: {
            'ventanas': int(g.shape[0]),
            'pacientes': int(g.paciente.nunique()),
            'registros': int(g.registro.nunique()),
        }
        for particion, g in paced.groupby('particion')
    }
    hallazgos = resumen[resumen.requiere_revision]
    salida_json = {
        'particiones': particiones,
        'conteos': conteos,
        'pacientes_requieren_revision': hallazgos.paciente.tolist(),
        'criterio_revision': '100% ventanas sin espiculas o RMS >100 Hz mediano <5 uV',
        'nota': 'Las banderas son de auditoria; no corrigen etiquetas automaticamente.',
    }
    (args.salida / 'resumen.json').write_text(json.dumps(salida_json, indent=2))

    lineas = [
        '# Auditoría de la clase Paced', '',
        f'Particiones inspeccionadas: {", ".join(particiones)}.',
        'El conjunto test permanece excluido por defecto.', '',
        '## Soporte', '',
    ]
    for particion, datos in conteos.items():
        lineas.append(
            f'- {particion}: {datos["ventanas"]} ventanas, '
            f'{datos["pacientes"]} pacientes, {datos["registros"]} registros.'
        )
    lineas.extend(['', '## Revisión prioritaria', ''])
    if hallazgos.empty:
        lineas.append('Ningún paciente activó los criterios automáticos.')
    else:
        for fila in hallazgos.itertuples():
            lineas.append(
                f'- {fila.paciente} ({fila.particion}): '
                f'{fila.pct_sin_espiculas:.0f}% sin espículas; '
                f'RMS >100 Hz mediano {fila.rms_gt100_mediana_uv:.2f} µV.'
            )
    lineas.extend([
        '',
        'Estas banderas requieren revisión clínica; no deben usarse para '
        're-etiquetar automáticamente.',
    ])
    (args.salida / 'auditoria.md').write_text('\n'.join(lineas) + '\n')
    print(f'AUDITORIA PACED OK: {len(resumen)} pacientes; '
          f'{len(hallazgos)} requieren revisión -> {args.salida}')


if __name__ == '__main__':
    main()
