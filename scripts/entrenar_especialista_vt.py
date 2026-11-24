"""F23: especialista ResNet binario VT con calibración agrupada train-only."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from sklearn.model_selection import StratifiedKFold


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'scripts'))

from entrenar_baseline_dl import (  # noqa: E402
    CLASES, ResNet1D, VentanasDL, sembrar_worker,
)


DL = RAIZ / 'results' / 'dl'


class BinarioVT(Dataset):
    def __init__(self, base: VentanasDL):
        self.base = base
        self.filas = base.filas

    def __len__(self) -> int:
        return len(self.base)

    def __getitem__(self, i: int):
        x, y = self.base[i]
        return x, int(CLASES[y] == 'VT')


def dividir_pacientes(train: pd.DataFrame, semilla: int) -> tuple[set[str], set[str]]:
    pacientes = (train.groupby('paciente').clase
                 .apply(lambda x: bool(x.eq('VT').any()))
                 .rename('es_vt').reset_index())
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=semilla)
    fit_i, cal_i = next(cv.split(pacientes.paciente, pacientes.es_vt))
    return set(pacientes.iloc[fit_i].paciente), set(pacientes.iloc[cal_i].paciente)


def pesos_sampler(filas: pd.DataFrame, fraccion_vt: float) -> np.ndarray:
    es_vt = filas.clase.eq('VT').to_numpy()
    if not es_vt.any() or es_vt.all():
        raise ValueError('fit requiere VT y no-VT')
    pesos = np.full(len(filas), (1.0 - fraccion_vt) / (~es_vt).sum())
    positivos = filas.loc[es_vt, 'paciente']
    por_paciente = positivos.value_counts()
    for paciente, n in por_paciente.items():
        mascara = es_vt & filas.paciente.eq(paciente).to_numpy()
        pesos[mascara] = fraccion_vt / (len(por_paciente) * n)
    return pesos


def evaluar(modelo: nn.Module, loader: DataLoader, dispositivo: str):
    modelo.eval()
    ys, probs, perdida = [], [], 0.0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(dispositivo, non_blocking=True), y.to(dispositivo)
            with torch.autocast(dispositivo, dtype=torch.bfloat16):
                logits = modelo(x)
                loss = nn.functional.cross_entropy(logits, y, reduction='sum')
            perdida += loss.item()
            ys.append(y.cpu().numpy())
            probs.append(logits.softmax(1)[:, 1].float().cpu().numpy())
    y = np.concatenate(ys)
    p = np.concatenate(probs)
    return perdida / len(y), y, p


def calibrar_umbral(y: np.ndarray, prob: np.ndarray,
                    precision_minima: float) -> dict:
    orden = np.argsort(-prob, kind='stable')
    po, yo = prob[orden], y[orden].astype(bool)
    tp = np.cumsum(yo)
    fp = np.cumsum(~yo)
    finales = np.r_[np.flatnonzero(po[:-1] != po[1:]), len(po) - 1]
    tp, fp = tp[finales], fp[finales]
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / max(int(yo.sum()), 1)
    f1 = np.divide(2 * precision * recall, precision + recall,
                   out=np.zeros_like(precision, dtype=float),
                   where=(precision + recall) > 0)
    validos = np.flatnonzero(precision >= precision_minima)
    candidatos = validos if len(validos) else np.arange(len(finales))
    mejor = candidatos[np.lexsort((po[finales][candidatos],
                                    precision[candidatos],
                                    f1[candidatos]))[-1]]
    return {
        'umbral': float(po[finales][mejor]),
        'f1': float(f1[mejor]),
        'precision': float(precision[mejor]),
        'sensibilidad': float(recall[mejor]),
        'precision_minima_cumplida': bool(precision[mejor] >= precision_minima),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--splits', type=Path, default=DL / 'splits_f20_active.csv')
    p.add_argument('--dir-shards', type=Path, default=DL / 'shards')
    p.add_argument('--salida', type=Path, required=True)
    p.add_argument('--semilla', type=int, default=23)
    p.add_argument('--epocas', type=int, default=30)
    p.add_argument('--batch', type=int, default=64)
    p.add_argument('--lr', type=float, default=3e-4)
    p.add_argument('--fraccion-vt', type=float, default=0.10)
    p.add_argument('--precision-minima', type=float, default=0.50)
    p.add_argument('--paciencia', type=int, default=8)
    p.add_argument('--humo', action='store_true')
    args = p.parse_args()
    if not 0 < args.fraccion_vt < 1:
        p.error('--fraccion-vt debe estar en (0,1)')
    if not 0 < args.precision_minima <= 1:
        p.error('--precision-minima debe estar en (0,1]')
    if not torch.cuda.is_available() and not args.humo:
        p.error('entrenamiento completo requiere CUDA')

    random.seed(args.semilla)
    np.random.seed(args.semilla)
    torch.manual_seed(args.semilla)
    man = pd.read_csv(DL / 'manifiesto.csv')
    splits = pd.read_csv(args.splits, index_col=0)['particion']
    man = man.merge(splits, left_on='paciente', right_index=True,
                    validate='many_to_one')
    train = man[man.particion.eq('train')].copy()
    fit_p, cal_p = dividir_pacientes(train, args.semilla)
    if fit_p & cal_p:
        raise RuntimeError('pacientes solapados en split interno')
    train.loc[train.paciente.isin(fit_p), 'particion'] = 'fit'
    train.loc[train.paciente.isin(cal_p), 'particion'] = 'calibracion'
    val = man[man.particion.eq('val')].copy()
    datos = pd.concat([train, val], ignore_index=True)
    norm = json.loads((DL / 'normalizacion.json').read_text())
    media = np.asarray(norm['media_mv'])
    desv = np.asarray(norm['desv_mv'])
    recorte, escala = (1250, 4) if args.humo else (0, 1)

    if args.humo:
        partes = []
        for particion, limite in (('fit', 1600), ('calibracion', 800), ('val', 800)):
            d = datos[datos.particion.eq(particion)]
            partes.append(pd.concat([
                g.sample(min(len(g), max(20, limite // max(d.clase.nunique(), 1))),
                         random_state=args.semilla)
                for _, g in d.groupby('clase')
            ]))
        datos = pd.concat(partes, ignore_index=True)

    fit_ds = BinarioVT(VentanasDL(datos, 'fit', args.dir_shards, media, desv,
                                  recorte=recorte,
                                  enmascarar_ausentes=True))
    cal_ds = BinarioVT(VentanasDL(datos, 'calibracion', args.dir_shards,
                                  media, desv, recorte=recorte,
                                  enmascarar_ausentes=True))
    val_ds = BinarioVT(VentanasDL(datos, 'val', args.dir_shards, media, desv,
                                  recorte=recorte,
                                  enmascarar_ausentes=True))
    for nombre, ds in (('fit', fit_ds), ('calibracion', cal_ds), ('val', val_ds)):
        if not ds.filas.clase.eq('VT').any() or ds.filas.clase.eq('VT').all():
            raise ValueError(f'{nombre} debe contener VT y no-VT')

    pesos = pesos_sampler(fit_ds.filas, args.fraccion_vt)
    gen = torch.Generator().manual_seed(args.semilla)
    sampler = WeightedRandomSampler(pesos, len(fit_ds), replacement=True,
                                    generator=gen)
    workers = 2
    fit_dl = DataLoader(fit_ds, batch_size=args.batch, sampler=sampler,
                        num_workers=workers, worker_init_fn=sembrar_worker,
                        pin_memory=torch.cuda.is_available(), drop_last=True)
    cal_dl = DataLoader(cal_ds, batch_size=args.batch, shuffle=False,
                        num_workers=workers, pin_memory=torch.cuda.is_available())
    val_dl = DataLoader(val_ds, batch_size=args.batch, shuffle=False,
                        num_workers=workers, pin_memory=torch.cuda.is_available())
    dispositivo = 'cuda' if torch.cuda.is_available() else 'cpu'
    modelo = ResNet1D(n_clases=2, escala=escala).to(dispositivo)
    opt = torch.optim.AdamW(modelo.parameters(), lr=args.lr, weight_decay=1e-2)
    args.salida.mkdir(parents=True, exist_ok=True)

    split_reporte = {
        'semilla': args.semilla,
        'pacientes_fit': len(fit_p),
        'pacientes_calibracion': len(cal_p),
        'solapamiento_pacientes': len(fit_p & cal_p),
        'ventanas_fit': int(len(fit_ds)),
        'ventanas_calibracion': int(len(cal_ds)),
        'vt_fit': int(fit_ds.filas.clase.eq('VT').sum()),
        'vt_calibracion': int(cal_ds.filas.clase.eq('VT').sum()),
        'test_consultado': False,
    }
    (args.salida / 'split_interno.json').write_text(
        json.dumps(split_reporte, indent=2) + '\n')
    print(json.dumps(split_reporte), flush=True)

    historial = []
    mejor_f1, sin_mejora = -1.0, 0
    n_epocas = 1 if args.humo else args.epocas
    for epoca in range(1, n_epocas + 1):
        t0 = time.time()
        modelo.train()
        perdida, n = 0.0, 0
        for x, y in fit_dl:
            x, y = x.to(dispositivo, non_blocking=True), y.to(dispositivo)
            opt.zero_grad()
            with torch.autocast(dispositivo, dtype=torch.bfloat16):
                loss = nn.functional.cross_entropy(modelo(x), y)
            loss.backward()
            opt.step()
            perdida += loss.item() * len(y)
            n += len(y)
        perdida_cal, y_cal, p_cal = evaluar(modelo, cal_dl, dispositivo)
        calibracion = calibrar_umbral(y_cal, p_cal, args.precision_minima)
        fila = {'epoca': epoca, 'perdida_fit': perdida / n,
                'perdida_calibracion': perdida_cal, **calibracion,
                'segundos': round(time.time() - t0, 1)}
        historial.append(fila)
        print(f'epoca {epoca}: fit={fila["perdida_fit"]:.4f} '
              f'cal_f1={fila["f1"]:.4f} p={fila["precision"]:.4f} '
              f'r={fila["sensibilidad"]:.4f} t={fila["umbral"]:.4f} '
              f'({fila["segundos"]}s)', flush=True)
        if fila['f1'] > mejor_f1:
            mejor_f1 = fila['f1']
            sin_mejora = 0
            torch.save({'modelo': modelo.state_dict(), 'epoca': epoca,
                        'calibracion': calibracion, 'config': vars(args)},
                       args.salida / 'mejor.pt')
        else:
            sin_mejora += 1
            if args.paciencia and sin_mejora >= args.paciencia:
                print('parada temprana especialista VT', flush=True)
                break
    (args.salida / 'historial.json').write_text(json.dumps(historial, indent=2))

    try:
        ckpt = torch.load(args.salida / 'mejor.pt', map_location=dispositivo,
                          weights_only=False)
    except TypeError:
        ckpt = torch.load(args.salida / 'mejor.pt', map_location=dispositivo)
    modelo.load_state_dict(ckpt['modelo'])
    _, y_val, p_val = evaluar(modelo, val_dl, dispositivo)
    umbral = float(ckpt['calibracion']['umbral'])
    pred_val = p_val >= umbral
    tp = int(((y_val == 1) & pred_val).sum())
    fp = int(((y_val == 0) & pred_val).sum())
    fn = int(((y_val == 1) & ~pred_val).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1_val = 0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn)
    pred = val_ds.filas[['window_id', 'paciente', 'registro', 'clase']].copy()
    pred = pred.rename(columns={'clase': 'clase_real'})
    pred['prob_vt'] = p_val
    pred['pred_vt'] = pred_val
    pred.to_csv(args.salida / 'predicciones_val.csv', index=False)
    resumen = {
        'mejor_epoca': int(ckpt['epoca']),
        'calibracion_train': ckpt['calibracion'],
        'umbral_fijo': umbral,
        'vt_val': {'f1': f1_val, 'precision': precision,
                   'sensibilidad': recall, 'tp': tp, 'fp': fp, 'fn': fn},
        'split_interno': split_reporte,
        'test_consultado': False,
        'config': {k: str(v) if isinstance(v, Path) else v
                   for k, v in vars(args).items()},
    }
    (args.salida / 'resumen.json').write_text(json.dumps(resumen, indent=2) + '\n')
    print(json.dumps(resumen, indent=2), flush=True)


if __name__ == '__main__':
    main()
