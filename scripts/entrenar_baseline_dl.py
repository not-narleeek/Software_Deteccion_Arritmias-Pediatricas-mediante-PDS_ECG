"""F16 — Baseline DL ResNet-1D sobre shards int16 (Etapa II-bis, AP-14).

Entrena sobre los shards empaquetados en F15 (memmap, sin copiar a RAM),
con z-score por derivación usando los estadísticos de train
(results/dl/normalizacion.json). Dos modos:

  --humo      : ~1.000 ventanas, 2 épocas, CPU — verifica que la pérdida
                decrece y que el F1 macro val se calcula (gate de humo).
  (por defecto): entrenamiento completo (T4). Checkpoint por época +
                mejor modelo según F1 macro val. Gate F16: F1 macro val
                (por ventana) > 0,518 (batir a RF).

Salidas en --salida (apúntalo a Drive en Colab):
  historial.json, mejor.pt, ultimo.pt, gate_f16.txt
"""

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

RAIZ = Path(__file__).resolve().parents[1]
REPO_DL = RAIZ / 'results' / 'dl'
CLASES = ['Sinusal', 'SVT', 'VT', 'Paced', 'Otro']  # orden fijo de etiquetas
GATE_F1 = 0.518  # F1 macro val de RF (por ventana) a batir


# ---------------------------------------------------------------- datos
class VentanasDL(Dataset):
    """Memmap de shards + manifiesto; indexa (shard, offset) por partición."""

    def __init__(self, man: pd.DataFrame, particion: str, dir_shards: Path,
                 media: np.ndarray, desv: np.ndarray):
        self.filas = man[man.particion == particion].reset_index(drop=True)
        self.shards = {s: np.load(dir_shards / f'shard_{s:03d}.npy',
                                  mmap_mode='r')
                       for s in self.filas.shard.unique()}
        self.media = torch.tensor(media, dtype=torch.float32).view(1, 12, 1)
        self.desv = torch.tensor(desv, dtype=torch.float32).view(1, 12, 1)

    def __len__(self) -> int:
        return len(self.filas)

    def __getitem__(self, i: int):
        f = self.filas.iloc[i]
        x = torch.from_numpy(np.asarray(self.shards[f.shard][f.offset]))
        x = (x.float() / 1000.0 - self.media) / self.desv  # int16→mV→z-score
        return x, CLASES.index(f.clase)


# ---------------------------------------------------------------- modelo
class Bloque(nn.Module):
    def __init__(self, c_in: int, c_out: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv1d(c_in, c_out, 15, stride, 7, bias=False)
        self.bn1 = nn.BatchNorm1d(c_out)
        self.conv2 = nn.Conv1d(c_out, c_out, 15, 1, 7, bias=False)
        self.bn2 = nn.BatchNorm1d(c_out)
        self.atajo = (nn.Identity() if (stride == 1 and c_in == c_out) else
                      nn.Sequential(nn.Conv1d(c_in, c_out, 1, stride, bias=False),
                                    nn.BatchNorm1d(c_out)))

    def forward(self, x):
        y = torch.relu(self.bn1(self.conv1(x)))
        y = self.bn2(self.conv2(y))
        return torch.relu(y + self.atajo(x))


class ResNet1D(nn.Module):
    """ResNet-1D sensata por defecto: stem 12→64 + 4 etapas → AvgPool → FC."""

    def __init__(self, n_clases: int = len(CLASES)):
        super().__init__()
        self.stem = nn.Sequential(nn.Conv1d(12, 64, 15, 2, 7, bias=False),
                                  nn.BatchNorm1d(64), nn.ReLU())
        etapas, c = [], 64
        for c_out, stride in ((64, 1), (128, 2), (256, 2), (512, 2)):
            etapas.append(Bloque(c, c_out, stride))
            c = c_out
        self.etapas = nn.Sequential(*etapas)
        self.cabeza = nn.Sequential(nn.AdaptiveAvgPool1d(1), nn.Flatten(),
                                    nn.Dropout(0.2), nn.Linear(c, n_clases))

    def forward(self, x):
        return self.cabeza(self.etapas(self.stem(x)))


# ---------------------------------------------------------------- entrenamiento
def f1_macro(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """F1 por clase (sin sklearn) + vector por clase; la macro es .mean()."""
    f1s = []
    for k in range(len(CLASES)):
        tp = ((y_pred == k) & (y_true == k)).sum()
        fp = ((y_pred == k) & (y_true != k)).sum()
        fn = ((y_pred != k) & (y_true == k)).sum()
        f1s.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return np.array(f1s)


@torch.no_grad()
def evaluar(modelo, loader, dispositivo):
    modelo.eval()
    ys, ps, perdida = [], [], 0.0
    for x, y in loader:
        x, y = x.to(dispositivo), y.to(dispositivo)
        logits = modelo(x)
        perdida += nn.functional.cross_entropy(logits, y,
                                               reduction='sum').item()
        ps.append(logits.argmax(1).cpu().numpy())
        ys.append(y.cpu().numpy())
    ys, ps = np.concatenate(ys), np.concatenate(ps)
    return perdida / len(ys), f1_macro(ys, ps)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--humo', action='store_true',
                    help='humo CPU: ~1.000 ventanas, 2 épocas, sin gate')
    ap.add_argument('--epocas', type=int, default=30)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--lr', type=float, default=3e-4)
    ap.add_argument('--semilla', type=int, default=14)
    ap.add_argument('--salida', type=Path, default=REPO_DL / 'baseline')
    args = ap.parse_args()

    random.seed(args.semilla)
    np.random.seed(args.semilla)
    torch.manual_seed(args.semilla)

    man = pd.read_csv(REPO_DL / 'manifiesto.csv')
    man = man.merge(pd.read_csv(REPO_DL / 'splits.csv', index_col=0)['particion'],
                    left_on='paciente', right_index=True)
    norm = json.loads((REPO_DL / 'normalizacion.json').read_text())
    media, desv = np.array(norm['media_mv']), np.array(norm['desv_mv'])

    if args.humo:  # submuestreo determinista: ≤200 ventanas por clase
        man = (man.groupby('clase', group_keys=False)
                  .apply(lambda g: g.sample(min(len(g), 200),
                                            random_state=args.semilla)))

    train_ds = VentanasDL(man, 'train', REPO_DL / 'shards', media, desv)
    val_ds = VentanasDL(man, 'val', REPO_DL / 'shards', media, desv)
    dispositivo = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'train={len(train_ds)} val={len(val_ds)} '
          f'epocas={2 if args.humo else args.epocas} dispositivo={dispositivo}',
          flush=True)

    cargador = (lambda ds, entrena: DataLoader(
        ds, batch_size=args.batch, shuffle=entrena, num_workers=2,
        pin_memory=dispositivo == 'cuda', drop_last=entrena))
    train_dl, val_dl = cargador(train_ds, True), cargador(val_ds, False)

    modelo = ResNet1D().to(dispositivo)
    # pesos de clase balanceados (Otro/Sinusal dominan; Paced 86 ventanas)
    conteo = train_ds.filas.clase.value_counts()
    pesos = torch.tensor([len(train_ds) / (len(CLASES) * conteo[c])
                          for c in CLASES], dtype=torch.float32).to(dispositivo)
    criterio = nn.CrossEntropyLoss(weight=pesos)
    opt = torch.optim.AdamW(modelo.parameters(), lr=args.lr)
    amp_dtype = torch.bfloat16 if dispositivo == 'cuda' else torch.bfloat16

    args.salida.mkdir(parents=True, exist_ok=True)
    historial, mejor_f1 = [], -1.0
    n_epocas = 2 if args.humo else args.epocas
    for epoca in range(1, n_epocas + 1):
        t0, perdida_acum = time.time(), 0.0
        modelo.train()
        for x, y in train_dl:
            x, y = x.to(dispositivo), y.to(dispositivo)
            opt.zero_grad()
            with torch.autocast(dispositivo, dtype=amp_dtype):
                perdida = criterio(modelo(x), y)
            perdida.backward()
            opt.step()
            perdida_acum += perdida.item() * len(y)
        perdida_ent = perdida_acum / len(train_ds)
        perdida_val, f1s = evaluar(modelo, val_dl, dispositivo)
        macro = float(f1s.mean())
        historial.append({'epoca': epoca, 'perdida_train': perdida_ent,
                          'perdida_val': perdida_val, 'f1_macro_val': macro,
                          'f1_por_clase': f1s.round(4).tolist(),
                          'segundos': round(time.time() - t0, 1)})
        print(f'epoca {epoca}: train={perdida_ent:.4f} val={perdida_val:.4f} '
              f'f1_macro_val={macro:.4f} ({historial[-1]["segundos"]}s)',
              flush=True)
        if not args.humo:
            ckpt = {'modelo': modelo.state_dict(), 'epoca': epoca,
                    'f1_macro_val': macro, 'clases': CLASES}
            torch.save(ckpt, args.salida / 'ultimo.pt')
            if macro > mejor_f1:
                mejor_f1 = macro
                torch.save(ckpt, args.salida / 'mejor.pt')

    (args.salida / 'historial.json').write_text(json.dumps(historial, indent=2))

    if args.humo:  # gate de humo: pérdida decrece y F1 se calculó
        assert historial[0]['perdida_train'] > historial[-1]['perdida_train'], \
            'la pérdida no decrece en el humo'
        assert 0.0 <= historial[-1]['f1_macro_val'] <= 1.0
        print('F16 HUMO VERDE')
        return

    gate = (f'F1 macro val (ventana): {mejor_f1:.4f} vs gate {GATE_F1} -> '
            f'{"VERDE" if mejor_f1 > GATE_F1 else "ROJO (1 diagnostico max.)"}')
    (args.salida / 'gate_f16.txt').write_text(gate + '\n')
    print(gate, flush=True)


if __name__ == '__main__':
    main()
