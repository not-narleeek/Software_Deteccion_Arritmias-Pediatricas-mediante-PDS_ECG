"""F19: prepara datasets externos candidatos para estudiar la clase Paced.

El corpus objetivo ZZU y sus splits no se modifican. Este script descarga desde
PhysioNet metadatos oficiales, selecciona PTB-XL PACE + controles emparejados y
localiza registros Leipzig con anotaciones de pacing. Las señales externas se
guardan bajo ``data/f19_paced`` (fuera de git) y los manifiestos auditables bajo
``results/dl/f19_datasets``.

Uso:
    uv run python scripts/preparar_f19_datasets.py --solo-metadata
    uv run python scripts/preparar_f19_datasets.py --descargar-senales
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import wfdb


RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / 'data' / 'f19_paced'
OUT = RAIZ / 'results' / 'dl' / 'f19_datasets'

PTB_VERSION = '1.0.3'
PTB_URL = f'https://physionet.org/files/ptb-xl/{PTB_VERSION}'
LEIPZIG_VERSION = '1.0.0'
LEIPZIG_URL = (
    f'https://physionet.org/files/leipzig-heart-center-ecg/{LEIPZIG_VERSION}'
)


def argumentos() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    modo = p.add_mutually_exclusive_group()
    modo.add_argument('--solo-metadata', action='store_true',
                      help='no descarga archivos .dat')
    modo.add_argument('--descargar-senales', action='store_true',
                      help='descarga PTB seleccionado y Leipzig con pacing')
    p.add_argument('--controles-ptb', type=int, default=294,
                   help='cantidad máxima de controles PTB-XL emparejados')
    p.add_argument('--raiz-datos', type=Path, default=DATA)
    p.add_argument('--salida', type=Path, default=OUT)
    return p.parse_args()


def descargar(url: str, destino: Path) -> Path:
    """Descarga atómica con reanudación HTTP cuando el servidor la admite."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        return destino
    parcial = destino.with_suffix(destino.suffix + '.part')
    inicio = parcial.stat().st_size if parcial.exists() else 0
    headers = {'User-Agent': 'f19-paced-audit/1.0'}
    if inicio:
        headers['Range'] = f'bytes={inicio}-'
    req = urllib.request.Request(url, headers=headers)
    try:
        respuesta = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and parcial.exists():
            parcial.replace(destino)
            return destino
        raise
    with respuesta:
        reanuda = inicio > 0 and getattr(respuesta, 'status', None) == 206
        modo = 'ab' if reanuda else 'wb'
        with parcial.open(modo) as f:
            shutil.copyfileobj(respuesta, f, length=1024 * 1024)
    parcial.replace(destino)
    return destino


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open('rb') as f:
        for bloque in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(bloque)
    return h.hexdigest()


def leer_checksums(ruta: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for linea in ruta.read_text().splitlines():
        partes = linea.strip().split(maxsplit=1)
        if len(partes) != 2:
            continue
        nombre = partes[1].lstrip('*').removeprefix('./')
        checksums[nombre] = partes[0]
    return checksums


def verificar(ruta: Path, relativo: str, checksums: dict[str, str]) -> str:
    esperado = checksums.get(relativo)
    if esperado is None:
        raise RuntimeError(f'sin checksum oficial para {relativo}')
    real = sha256(ruta)
    if real != esperado:
        raise RuntimeError(f'checksum inválido para {relativo}: {real} != {esperado}')
    return real


def descargar_verificar(url: str, ruta: Path, relativo: str,
                        checksums: dict[str, str]) -> str:
    descargar(url, ruta)
    return verificar(ruta, relativo, checksums)


def _edad_num(valor: object) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float('nan')


def seleccionar_controles(ptb: pd.DataFrame, positivos: pd.DataFrame,
                          limite: int) -> pd.DataFrame:
    """Control no-PACE más cercano por sexo/edad, un registro por paciente."""
    candidatos = ptb[~ptb.es_pace].copy()
    candidatos = candidatos.drop_duplicates('patient_id')
    candidatos['edad_num'] = candidatos.age.map(_edad_num)
    candidatos = candidatos[candidatos.edad_num.between(18, 100)]
    disponibles = set(candidatos.index)
    elegidos: list[int] = []
    objetivos = positivos.drop_duplicates('patient_id').sort_values('ecg_id')
    for _, objetivo in objetivos.iterrows():
        if len(elegidos) >= limite or not disponibles:
            break
        pool = candidatos.loc[sorted(disponibles)]
        mismo_sexo = pool[pool.sex == objetivo.sex]
        if not mismo_sexo.empty:
            pool = mismo_sexo
        edad_obj = _edad_num(objetivo.age)
        if pd.isna(edad_obj):
            idx = int(pool.sort_values('ecg_id').index[0])
        else:
            distancia = (pool.edad_num - edad_obj).abs()
            idx = int(pool.assign(_dist=distancia)
                      .sort_values(['_dist', 'ecg_id']).index[0])
        elegidos.append(idx)
        disponibles.remove(idx)
    if len(elegidos) < limite and disponibles:
        faltan = limite - len(elegidos)
        relleno = candidatos.loc[sorted(disponibles)].sort_values('ecg_id').head(faltan)
        elegidos.extend(int(i) for i in relleno.index)
    return candidatos.loc[elegidos].copy()


def preparar_ptb(raiz: Path, out: Path, descargar_senales: bool,
                 n_controles: int) -> pd.DataFrame:
    base = raiz / 'ptb-xl' / PTB_VERSION
    archivos = ('ptbxl_database.csv', 'scp_statements.csv', 'SHA256SUMS.txt')
    for nombre in archivos:
        descargar(f'{PTB_URL}/{nombre}', base / nombre)
    checksums = leer_checksums(base / 'SHA256SUMS.txt')
    verificar(base / 'ptbxl_database.csv', 'ptbxl_database.csv', checksums)
    verificar(base / 'scp_statements.csv', 'scp_statements.csv', checksums)

    ptb = pd.read_csv(base / 'ptbxl_database.csv')
    ptb['codigos'] = ptb.scp_codes.map(ast.literal_eval)
    ptb['es_pace'] = ptb.codigos.map(lambda d: 'PACE' in d)
    positivos = ptb[ptb.es_pace].copy()
    controles = seleccionar_controles(ptb, positivos, n_controles)
    positivos['rol'] = 'paced'
    controles['rol'] = 'control'
    seleccion = pd.concat([positivos, controles], ignore_index=True)

    relativos_hea = [str(r.filename_hr) + '.hea'
                     for _, r in seleccion.iterrows()]
    with ThreadPoolExecutor(max_workers=8) as ex:
        hashes_hea = dict(zip(
            relativos_hea,
            ex.map(
                lambda relativo: descargar_verificar(
                    f'{PTB_URL}/{relativo}', base / relativo, relativo, checksums),
                relativos_hea,
            ),
        ))
    hashes_dat: dict[str, str] = {}
    if descargar_senales:
        relativos_dat = [str(r.filename_hr) + '.dat'
                         for _, r in seleccion.iterrows()]
        with ThreadPoolExecutor(max_workers=6) as ex:
            hashes_dat = dict(zip(
                relativos_dat,
                ex.map(
                    lambda relativo: descargar_verificar(
                        f'{PTB_URL}/{relativo}', base / relativo, relativo, checksums),
                    relativos_dat,
                ),
            ))

    filas: list[dict] = []
    for _, r in seleccion.sort_values(['rol', 'ecg_id']).iterrows():
        relativo_base = str(r.filename_hr)
        relativo_hea = relativo_base + '.hea'
        relativo_dat = relativo_base + '.dat'
        local_hea = base / relativo_hea
        local_dat = base / relativo_dat
        hash_hea = hashes_hea[relativo_hea]
        hash_dat = hashes_dat.get(relativo_dat, '')
        cabecera = wfdb.rdheader(str(local_hea.with_suffix('')))
        filas.append({
            'dataset': 'ptb-xl',
            'version': PTB_VERSION,
            'registro': int(r.ecg_id),
            'paciente': f"ptbxl:{int(r.patient_id)}",
            'rol': r.rol,
            'edad_anos': _edad_num(r.age),
            'sexo': int(r.sex) if not pd.isna(r.sex) else '',
            'fs_hz': float(cabecera.fs),
            'n_derivaciones': int(cabecera.n_sig),
            'duracion_s': cabecera.sig_len / cabecera.fs,
            'etiqueta': 'PACE' if r.es_pace else 'NO_PACE',
            'pacemaker_metadata': '' if pd.isna(r.pacemaker) else str(r.pacemaker),
            'ruta_base': str((base / relativo_base).relative_to(RAIZ)),
            'tiene_senal': local_dat.exists(),
            'sha256_hea': hash_hea,
            'sha256_dat': hash_dat,
            'limitacion': 'poblacion adulta; usar solo para preentrenamiento',
        })
    man = pd.DataFrame(filas)
    out.mkdir(parents=True, exist_ok=True)
    man.to_csv(out / 'ptbxl_manifest.csv', index=False)
    return man


def _metadata_sujeto(tablas: list[pd.DataFrame], registro: str) -> dict:
    buscados = {registro, registro.lstrip('x'), registro.replace('x0', '')}
    for tabla in tablas:
        for columna in tabla.columns:
            valores = tabla[columna].astype(str).str.strip()
            mascara = valores.isin(buscados)
            if mascara.any():
                return tabla[mascara].iloc[0].to_dict()
    return {}


def preparar_leipzig(raiz: Path, out: Path,
                     descargar_senales: bool) -> pd.DataFrame:
    base = raiz / 'leipzig' / LEIPZIG_VERSION
    indices = ('RECORDS', 'SHA256SUMS.txt', 'children-subject-info.csv',
               'adults-subject-info.csv', 'dataset_info.csv')
    for nombre in indices:
        descargar(f'{LEIPZIG_URL}/{nombre}', base / nombre)
    checksums = leer_checksums(base / 'SHA256SUMS.txt')
    for nombre in indices:
        if nombre != 'SHA256SUMS.txt':
            verificar(base / nombre, nombre, checksums)

    tablas = [pd.read_csv(base / nombre, sep=None, engine='python')
              for nombre in ('children-subject-info.csv', 'adults-subject-info.csv')]
    registros = [r.strip() for r in (base / 'RECORDS').read_text().splitlines()
                 if r.strip()]
    filas: list[dict] = []
    for registro in registros:
        hashes: dict[str, str] = {}
        for extension in ('.hea', '.atr'):
            relativo = registro + extension
            local = base / relativo
            descargar(f'{LEIPZIG_URL}/{relativo}', local)
            hashes[extension] = verificar(local, relativo, checksums)
        cabecera = wfdb.rdheader(str(base / registro))
        ann = wfdb.rdann(str(base / registro), 'atr')
        aux = [str(x or '') for x in ann.aux_note]
        n_paced = sum(s == '/' for s in ann.symbol)
        n_atrial = sum('/A' in a or '(/A' in a for a in aux)
        n_vent = sum('/V' in a or '(/V' in a for a in aux)
        tiene_pacing = n_paced > 0 or n_atrial > 0 or n_vent > 0
        local_dat = base / f'{registro}.dat'
        meta = _metadata_sujeto(tablas, registro)
        filas.append({
            'dataset': 'leipzig-heart-center-ecg',
            'version': LEIPZIG_VERSION,
            'registro': registro,
            'paciente': f'leipzig:{registro}',
            'grupo': 'pediatrico' if registro.startswith('x0') else 'adulto_chd',
            'fs_hz': float(cabecera.fs),
            'n_canales': int(cabecera.n_sig),
            'duracion_s': cabecera.sig_len / cabecera.fs,
            'paced_beats': n_paced,
            'anotaciones_atrial': n_atrial,
            'anotaciones_ventricular': n_vent,
            'tiene_pacing': tiene_pacing,
            'metadata_sujeto': json.dumps(meta, ensure_ascii=False, default=str),
            'ruta_base': str((base / registro).relative_to(RAIZ)),
            'tiene_senal': local_dat.exists(),
            'sha256_hea': hashes['.hea'],
            'sha256_atr': hashes['.atr'],
            'sha256_dat': '',
            'limitacion': ('estudio electrofisiologico; LP de adquisicion 100 Hz; '
                           'pacing no equivale necesariamente a marcapasos implantado'),
        })
    man = pd.DataFrame(filas)
    if descargar_senales:
        relativos_dat = [f'{r}.dat' for r in man.loc[man.tiene_pacing, 'registro']]
        with ThreadPoolExecutor(max_workers=3) as ex:
            hashes_dat = dict(zip(
                relativos_dat,
                ex.map(
                    lambda relativo: descargar_verificar(
                        f'{LEIPZIG_URL}/{relativo}', base / relativo,
                        relativo, checksums),
                    relativos_dat,
                ),
            ))
        for i, r in man.iterrows():
            relativo = f'{r.registro}.dat'
            if relativo in hashes_dat:
                man.at[i, 'sha256_dat'] = hashes_dat[relativo]
                man.at[i, 'tiene_senal'] = True
    out.mkdir(parents=True, exist_ok=True)
    man.to_csv(out / 'leipzig_manifest.csv', index=False)
    return man


def escribir_resumen(out: Path, ptb: pd.DataFrame, leipzig: pd.DataFrame) -> None:
    l_paced = leipzig[leipzig.tiene_pacing]
    resumen = {
        'ptb_xl': {
            'registros_paced': int((ptb.rol == 'paced').sum()),
            'pacientes_paced': int(ptb[ptb.rol == 'paced'].paciente.nunique()),
            'controles': int((ptb.rol == 'control').sum()),
            'edad_min_paced': float(ptb[ptb.rol == 'paced'].edad_anos.min()),
            'pediatricos_paced': int(
                (ptb[ptb.rol == 'paced'].edad_anos < 18).sum()),
            'senales_descargadas': int(ptb.tiene_senal.sum()),
        },
        'leipzig': {
            'registros_total': int(len(leipzig)),
            'registros_con_pacing': int(len(l_paced)),
            'pediatricos_con_pacing': int(
                (l_paced.grupo == 'pediatrico').sum()),
            'paced_beats': int(leipzig.paced_beats.sum()),
            'senales_descargadas': int(leipzig.tiene_senal.sum()),
        },
        'politica': {
            'test_zzu_consultado': False,
            'mezcla_automatica_con_zzu': False,
            'uso_previsto': 'preentrenamiento/ablacion externa solamente',
        },
    }
    (out / 'resumen.json').write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


def main() -> None:
    args = argumentos()
    descargar_senales = bool(args.descargar_senales and not args.solo_metadata)
    ptb = preparar_ptb(args.raiz_datos, args.salida, descargar_senales,
                       args.controles_ptb)
    leipzig = preparar_leipzig(args.raiz_datos, args.salida, descargar_senales)
    escribir_resumen(args.salida, ptb, leipzig)


if __name__ == '__main__':
    main()
