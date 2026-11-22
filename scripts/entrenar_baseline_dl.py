"""F16 — Baseline DL ResNet-1D sobre shards int16 (Etapa II-bis, AP-14).

Entrena sobre los shards empaquetados en F15 (memmap, sin copiar a RAM),
con z-score por derivación usando los estadísticos de train
(results/dl/normalizacion.json). Dos modos:

  --humo      : ~1.000 ventanas, 2 épocas, CPU — verifica que la pérdida
                decrece y que el F1 macro val se calcula (gate de humo).
  (por defecto): entrenamiento completo (T4). Checkpoint por época +
                mejor modelo según F1 macro val. Gate F16: F1 macro val
                (por ventana) > 0,518 (batir a RF).

Salidas en --salida (en Vast.ai, descargar antes de destruir la instancia):
  historial.json, mejor.pt, ultimo.pt, resumen.json, predicciones_val.csv,
  matriz_confusion_val.csv y el gate indicado por --nombre-gate.
"""

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

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'src'))

from ecg_pipeline.pacing import FEATURES_HF  # noqa: E402

REPO_DL = RAIZ / 'results' / 'dl'
CLASES = ['Sinusal', 'SVT', 'VT', 'Paced', 'Otro']  # orden fijo de etiquetas
GATE_F1 = 0.518  # F1 macro val de RF (por ventana) a batir


# ---------------------------------------------------------------- datos
class VentanasDL(Dataset):
    """Memmap de shards + manifiesto; indexa (shard, offset) por partición."""

    def __init__(self, man: pd.DataFrame, particion: str, dir_shards: Path,
                 media: np.ndarray, desv: np.ndarray, recorte: int = 0,
                 augmentacion: bool = False,
                 clases_augmentacion: frozenset[str] | None = None,
                 enmascarar_ausentes: bool = False,
                 sidecar_hf: pd.DataFrame | None = None,
                 media_hf: np.ndarray | None = None,
                 desv_hf: np.ndarray | None = None):
        self.filas = man[man.particion == particion].reset_index(drop=True)
        self.shards = {s: np.load(dir_shards / f'shard_{s:03d}.npy',
                                  mmap_mode='r')
                       for s in self.filas.shard.unique()}
        # (12,1): difunde contra una ventana [12,5000] sin subir el rango
        self.media = torch.tensor(media, dtype=torch.float32).view(12, 1)
        self.desv = torch.tensor(desv, dtype=torch.float32).view(12, 1)
        self.recorte = recorte
        self.augmentacion = augmentacion
        self.clases_augmentacion = clases_augmentacion
        self.enmascarar_ausentes = enmascarar_ausentes
        self.hf: torch.Tensor | None = None
        if sidecar_hf is not None:
            if media_hf is None or desv_hf is None:
                raise ValueError('sidecar HF requiere media/desv')
            side = sidecar_hf.set_index('window_id')
            ids = self.filas.window_id.astype(str)
            faltan = [w for w in ids if w not in side.index]
            if faltan:
                raise ValueError(f'sidecar HF: faltan {len(faltan)} ventanas '
                                 f'en {particion}, primera={faltan[0]}')
            valores = side.loc[ids, list(FEATURES_HF)].to_numpy(dtype=np.float32)
            valores = np.log1p(valores)
            valores = (valores - media_hf) / desv_hf
            self.hf = torch.from_numpy(np.clip(valores, -8.0, 8.0).astype(np.float32))

    def __len__(self) -> int:
        return len(self.filas)

    def __getitem__(self, i: int):
        f = self.filas.iloc[i]
        x = torch.from_numpy(                        # copia: memmap no escribible
            np.asarray(self.shards[f.shard][f.offset]).copy())
        if self.recorte:                             # humo: 2,5 s @ 500 Hz
            x = x[:, :self.recorte]
        x = x.float() / 1000.0
        # Las derivaciones ausentes llegan como 0 mV. Tras z-score quedarían
        # como constantes distintas de cero y revelarían el formato 9/12 leads.
        presentes = x.abs().amax(dim=1) > 0
        x = (x - self.media) / self.desv
        if self.enmascarar_ausentes:
            x[~presentes] = 0.0
        if (self.augmentacion and
                (not self.clases_augmentacion or
                 f.clase in self.clases_augmentacion)):
            x = aumentar_ventana(x, presentes)
        y = CLASES.index(f.clase)
        if self.hf is not None:
            return x, self.hf[i], y
        return x, y


def aumentar_ventana(x: torch.Tensor, presentes: torch.Tensor) -> torch.Tensor:
    """Variaciones conservadoras; solo se invoca desde el Dataset de train.

    Opera en espacio z-score y aplica la misma familia de perturbaciones a todas
    las clases. El sobremuestreo de Paced produce variantes nuevas sin convertir
    un artefacto exclusivo en atajo de clase.
    """
    x = x.clone()
    if torch.rand(()) < 0.8:  # desplazamiento máximo ±200 ms @ 500 Hz
        desplazamiento = int(torch.randint(-100, 101, ()).item())
        if desplazamiento > 0:
            x[:, desplazamiento:] = x[:, :-desplazamiento].clone()
            x[:, :desplazamiento] = 0.0
        elif desplazamiento < 0:
            corte = -desplazamiento
            x[:, :-corte] = x[:, corte:].clone()
            x[:, -corte:] = 0.0
    if torch.rand(()) < 0.8:
        x *= 0.9 + 0.2 * torch.rand(())
    if torch.rand(()) < 0.5:
        t = torch.arange(x.shape[1], dtype=x.dtype) / 500.0
        frecuencia = 0.1 + 0.4 * torch.rand(())
        fase = 2 * torch.pi * torch.rand(())
        amplitud = 0.1 * torch.rand((x.shape[0], 1), dtype=x.dtype)
        x += amplitud * torch.sin(2 * torch.pi * frecuencia * t + fase)
    if torch.rand(()) < 0.5:
        x += torch.randn_like(x) * (0.03 * torch.rand(()))
    if torch.rand(()) < 0.3:
        candidatas = torch.nonzero(presentes, as_tuple=False).flatten()
        if len(candidatas) > 1:
            x[candidatas[torch.randint(len(candidatas), ())]] = 0.0
    x[~presentes] = 0.0
    return x


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
    """ResNet-1D: stem 12→64 + 4 etapas → AvgPool → FC (±anchura en escala)."""

    def __init__(self, n_clases: int = len(CLASES), escala: int = 1,
                 hf_dim: int = 0, fusion_hf: str = 'concat'):
        super().__init__()
        w = (lambda c: max(16, c // escala))
        self.stem = nn.Sequential(nn.Conv1d(12, w(64), 15, 2, 7, bias=False),
                                  nn.BatchNorm1d(w(64)), nn.ReLU())
        etapas, c = [], w(64)
        for c_out, stride in ((64, 1), (128, 2), (256, 2), (512, 2)):
            etapas.append(Bloque(c, w(c_out), stride))
            c = w(c_out)
        self.etapas = nn.Sequential(*etapas)
        self.cabeza = nn.Sequential(nn.AdaptiveAvgPool1d(1), nn.Flatten(),
                                    nn.Dropout(0.2), nn.Linear(c, n_clases))
        self.hf_dim = hf_dim
        self.fusion_hf = fusion_hf
        if hf_dim:
            self.rama_hf = nn.Sequential(
                nn.Linear(hf_dim, 32), nn.LayerNorm(32), nn.ReLU(),
                nn.Dropout(0.1), nn.Linear(32, 32), nn.ReLU(),
            )
            if fusion_hf == 'concat':
                self.pool_morfologia = nn.Sequential(
                    nn.AdaptiveAvgPool1d(1), nn.Flatten())
                self.cabeza_fusion = nn.Sequential(
                    nn.Dropout(0.2), nn.Linear(c + 32, n_clases),
                )
            elif fusion_hf == 'paced_logit':
                self.ajuste_paced = nn.Linear(32, 1)
                nn.init.zeros_(self.ajuste_paced.weight)
                nn.init.zeros_(self.ajuste_paced.bias)
            else:
                raise ValueError(f'fusion HF desconocida: {fusion_hf}')

    def forward(self, x, hf=None):
        morfologia = self.etapas(self.stem(x))
        if not self.hf_dim:
            return self.cabeza(morfologia)
        if hf is None:
            raise ValueError('modelo F20 requiere features HF')
        z_hf = self.rama_hf(hf)
        if self.fusion_hf == 'concat':
            z = torch.cat((self.pool_morfologia(morfologia), z_hf), dim=1)
            return self.cabeza_fusion(z)
        logits = self.cabeza(morfologia)
        delta = self.ajuste_paced(z_hf)
        mascara = logits.new_tensor([0.0, 0.0, 0.0, 1.0, 0.0])
        return logits + delta * mascara


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


def matriz_confusion(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    matriz = np.zeros((len(CLASES), len(CLASES)), dtype=int)
    for real, pred in zip(y_true, y_pred):
        matriz[int(real), int(pred)] += 1
    return matriz


def pesos_sampler_paced(filas: pd.DataFrame, fraccion: float) -> np.ndarray:
    """Masas para una fracción esperada de Paced, equilibrada por paciente."""
    if not 0.0 < fraccion < 1.0:
        raise ValueError('--fraccion-paced debe estar entre 0 y 1')
    es_paced = filas.clase.eq('Paced').to_numpy()
    if not es_paced.any() or es_paced.all():
        raise ValueError('se requieren ejemplos Paced y no-Paced en train')
    pesos = np.ones(len(filas), dtype=np.float64)
    masa_paced = fraccion * (~es_paced).sum() / (1.0 - fraccion)
    pacientes = filas.loc[es_paced, 'paciente']
    n_pacientes = pacientes.nunique()
    por_paciente = pacientes.value_counts()
    for paciente, cantidad in por_paciente.items():
        mascara = es_paced & filas.paciente.eq(paciente).to_numpy()
        pesos[mascara] = masa_paced / (n_pacientes * cantidad)
    return pesos


def pesos_perdida(filas: pd.DataFrame, exponente: float,
                  pesos_muestra: np.ndarray | None = None) -> np.ndarray:
    """Pesos de clase según la distribución efectiva del loader."""
    if not 0.0 <= exponente <= 1.0:
        raise ValueError('--exponente-pesos debe estar entre 0 y 1')
    masas = []
    for clase in CLASES:
        mascara = filas.clase.eq(clase).to_numpy()
        masas.append(float(mascara.sum() if pesos_muestra is None
                           else pesos_muestra[mascara].sum()))
    probabilidades = np.asarray(masas) / np.sum(masas)
    return (1.0 / (len(CLASES) * probabilidades)) ** exponente


def sembrar_worker(worker_id: int) -> None:
    semilla = torch.initial_seed() % (2 ** 32)
    np.random.seed(semilla)
    random.seed(semilla)


def desempaquetar_lote(lote, dispositivo):
    if len(lote) == 3:
        x, hf, y = lote
        return x.to(dispositivo), hf.to(dispositivo), y.to(dispositivo)
    x, y = lote
    return x.to(dispositivo), None, y.to(dispositivo)


@torch.no_grad()
def evaluar(modelo, loader, dispositivo):
    modelo.eval()
    ys, ps, probabilidades, perdida = [], [], [], 0.0
    for lote in loader:
        x, hf, y = desempaquetar_lote(lote, dispositivo)
        logits = modelo(x, hf)
        perdida += nn.functional.cross_entropy(logits, y,
                                               reduction='sum').item()
        ps.append(logits.argmax(1).cpu().numpy())
        probabilidades.append(logits.softmax(1).cpu().numpy())
        ys.append(y.cpu().numpy())
    ys, ps = np.concatenate(ys), np.concatenate(ps)
    return (perdida / len(ys), f1_macro(ys, ps), ys, ps,
            np.concatenate(probabilidades))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--humo', action='store_true',
                    help='humo CPU: ~1.000 ventanas, 2 épocas, sin gate')
    ap.add_argument('--epocas', type=int, default=30)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--lr', type=float, default=3e-4)
    ap.add_argument('--weight-decay', type=float, default=1e-2)
    ap.add_argument('--scheduler-coseno', action='store_true',
                    help='reduce LR con CosineAnnealing durante la corrida')
    ap.add_argument('--semilla', type=int, default=14)
    ap.add_argument('--muestreo-balanceado', action='store_true',
                    help='entrena con clases equiprobables; no combina '
                         'pesos de pérdida para no sobrecompensar')
    ap.add_argument('--fraccion-paced', type=float, default=0.0,
                    help='fracción esperada de Paced por época, equilibrada '
                         'por paciente (recomendado F18: 0.03)')
    ap.add_argument('--augmentacion', action='store_true',
                    help='augmentation conservadora online, solo en train')
    ap.add_argument('--augmentacion-clases', nargs='+', choices=CLASES,
                    help='limita augmentation a estas clases; requiere --augmentacion')
    ap.add_argument('--enmascarar-derivaciones-ausentes', action='store_true',
                    help='representa leads ausentes como 0 tras normalizar')
    ap.add_argument('--exponente-pesos', type=float, default=1.0,
                    help='potencia de pesos inversos de clase [0,1]; F18: 0.5')
    ap.add_argument('--label-smoothing', type=float, default=0.0,
                    help='suavizado de etiquetas [0,1); F18: 0.05')
    ap.add_argument('--paciencia', type=int, default=0,
                    help='detiene si F1 macro no mejora tras N épocas; 0 desactiva')
    ap.add_argument('--min-delta', type=float, default=0.001,
                    help='mejora mínima de F1 macro para reiniciar paciencia')
    ap.add_argument('--nombre-gate', default='gate_f16.txt',
                    help='nombre del archivo de gate dentro de --salida')
    ap.add_argument('--dir-shards', type=Path, default=REPO_DL / 'shards')
    ap.add_argument('--splits', type=Path, default=REPO_DL / 'splits.csv',
                    help='split por paciente; permite una ablación sin alterar el histórico')
    ap.add_argument('--salida', type=Path, default=REPO_DL / 'baseline')
    ap.add_argument('--sidecar-hf', type=Path,
                    help='CSV F20 por window_id con ocho features HF')
    ap.add_argument('--normalizacion-hf', type=Path,
                    help='JSON F20 con log1p + estadísticos train-only')
    ap.add_argument('--fusion-hf', choices=['concat', 'paced_logit'],
                    default='concat',
                    help='concat F20 o residual HF exclusivo del logit Paced')
    args = ap.parse_args()

    if args.muestreo_balanceado and args.fraccion_paced:
        ap.error('--muestreo-balanceado y --fraccion-paced son excluyentes')
    if not 0.0 <= args.label_smoothing < 1.0:
        ap.error('--label-smoothing debe estar en [0,1)')
    if bool(args.sidecar_hf) != bool(args.normalizacion_hf):
        ap.error('--sidecar-hf y --normalizacion-hf deben usarse juntos')
    if args.fusion_hf != 'concat' and not args.sidecar_hf:
        ap.error('--fusion-hf paced_logit requiere sidecar HF')
    if args.augmentacion_clases and not args.augmentacion:
        ap.error('--augmentacion-clases requiere --augmentacion')

    random.seed(args.semilla)
    np.random.seed(args.semilla)
    torch.manual_seed(args.semilla)

    man = pd.read_csv(REPO_DL / 'manifiesto.csv')
    man = man.merge(pd.read_csv(args.splits, index_col=0)['particion'],
                    left_on='paciente', right_index=True)
    norm = json.loads((REPO_DL / 'normalizacion.json').read_text())
    media, desv = np.array(norm['media_mv']), np.array(norm['desv_mv'])
    sidecar_hf = media_hf = desv_hf = None
    clases_augmentacion = (frozenset(args.augmentacion_clases)
                           if args.augmentacion_clases else None)
    if args.sidecar_hf:
        sidecar_hf = pd.read_csv(args.sidecar_hf)
        norm_hf = json.loads(args.normalizacion_hf.read_text())
        if norm_hf.get('features') != list(FEATURES_HF):
            ap.error('orden de features HF incompatible')
        if norm_hf.get('transformacion') != 'log1p':
            ap.error('normalizacion HF debe declarar transformacion log1p')
        media_hf = np.asarray(norm_hf['media_train'], dtype=np.float32)
        desv_hf = np.asarray(norm_hf['desv_train'], dtype=np.float32)

    if args.humo:  # submuestreo determinista: ≤200 ventanas por clase
        man = pd.concat([g.sample(min(len(g), 200), random_state=args.semilla)
                         for _, g in man.groupby('clase')])

    # humo: misma tubería con config ligera (ventanas de 2,5 s, anchura /4)
    # para que quepa en la CPU de 2 vCPU del runtime gratuito en ~1 min
    recorte, escala = (1250, 4) if args.humo else (0, 1)

    train_ds = VentanasDL(man, 'train', args.dir_shards, media, desv,
                          recorte=recorte, augmentacion=args.augmentacion,
                          clases_augmentacion=clases_augmentacion,
                          enmascarar_ausentes=args.enmascarar_derivaciones_ausentes,
                          sidecar_hf=sidecar_hf, media_hf=media_hf,
                          desv_hf=desv_hf)
    if not args.humo and not torch.cuda.is_available():
        sys.exit('F16 FALLA: el entrenamiento completo exige GPU (runtime T4); '
                 'usa --humo para el humo en CPU')
    val_ds = VentanasDL(man, 'val', args.dir_shards, media, desv,
                        recorte=recorte,
                        enmascarar_ausentes=args.enmascarar_derivaciones_ausentes,
                        sidecar_hf=sidecar_hf, media_hf=media_hf,
                        desv_hf=desv_hf)
    dispositivo = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'train={len(train_ds)} val={len(val_ds)} '
          f'epocas={2 if args.humo else args.epocas} dispositivo={dispositivo}',
          flush=True)

    pin_memory = dispositivo == 'cuda'
    generador = torch.Generator().manual_seed(args.semilla)
    pesos_muestra = None
    if args.muestreo_balanceado:
        conteo = train_ds.filas.clase.value_counts()
        pesos_muestra = train_ds.filas.clase.map(
            {c: 1.0 / conteo[c] for c in CLASES}).to_numpy(copy=True)
        muestreador = WeightedRandomSampler(pesos_muestra, len(train_ds),
                                             replacement=True,
                                             generator=generador)
        train_dl = DataLoader(train_ds, batch_size=args.batch,
                              sampler=muestreador, num_workers=2,
                              worker_init_fn=sembrar_worker,
                              pin_memory=pin_memory, drop_last=True)
    elif args.fraccion_paced:
        pesos_muestra = pesos_sampler_paced(train_ds.filas,
                                             args.fraccion_paced)
        muestreador = WeightedRandomSampler(pesos_muestra, len(train_ds),
                                             replacement=True,
                                             generator=generador)
        train_dl = DataLoader(train_ds, batch_size=args.batch,
                              sampler=muestreador, num_workers=2,
                              worker_init_fn=sembrar_worker,
                              pin_memory=pin_memory, drop_last=True)
    else:
        train_dl = DataLoader(train_ds, batch_size=args.batch, shuffle=True,
                              num_workers=2, worker_init_fn=sembrar_worker,
                              generator=generador, pin_memory=pin_memory,
                              drop_last=True)
    val_dl = DataLoader(val_ds, batch_size=args.batch, shuffle=False,
                        num_workers=2, worker_init_fn=sembrar_worker,
                        pin_memory=pin_memory)

    modelo = ResNet1D(
        escala=escala,
        hf_dim=len(FEATURES_HF) if sidecar_hf is not None else 0,
        fusion_hf=args.fusion_hf,
    ).to(dispositivo)
    # El sampler totalmente balanceado conserva el comportamiento F17. El
    # sampler moderado de F18 calcula pesos sobre su distribución efectiva.
    pesos = None if args.muestreo_balanceado else torch.tensor(
        pesos_perdida(train_ds.filas, args.exponente_pesos, pesos_muestra),
        dtype=torch.float32).to(dispositivo)
    criterio = nn.CrossEntropyLoss(weight=pesos,
                                   label_smoothing=args.label_smoothing)
    opt = torch.optim.AdamW(modelo.parameters(), lr=args.lr,
                            weight_decay=args.weight_decay)
    scheduler = (torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=2 if args.humo else args.epocas, eta_min=args.lr / 20)
        if args.scheduler_coseno else None)
    amp_dtype = torch.bfloat16 if dispositivo == 'cuda' else torch.bfloat16

    args.salida.mkdir(parents=True, exist_ok=True)
    historial, mejor_f1, mejor_paciencia, mejor_epoca = [], -1.0, -1.0, 0
    sin_mejora = 0
    n_epocas = 2 if args.humo else args.epocas
    for epoca in range(1, n_epocas + 1):
        t0, perdida_acum, n_procesadas = time.time(), 0.0, 0
        modelo.train()
        for lote in train_dl:
            x, hf, y = desempaquetar_lote(lote, dispositivo)
            opt.zero_grad()
            with torch.autocast(dispositivo, dtype=amp_dtype):
                perdida = criterio(modelo(x, hf), y)
            perdida.backward()
            opt.step()
            perdida_acum += perdida.item() * len(y)
            n_procesadas += len(y)
        perdida_ent = perdida_acum / n_procesadas
        perdida_val, f1s, _, _, _ = evaluar(modelo, val_dl, dispositivo)
        macro = float(f1s.mean())
        lr_actual = opt.param_groups[0]['lr']
        historial.append({'epoca': epoca, 'perdida_train': perdida_ent,
                          'perdida_val': perdida_val, 'f1_macro_val': macro,
                          'f1_por_clase': f1s.round(4).tolist(),
                          'lr': lr_actual,
                          'segundos': round(time.time() - t0, 1)})
        print(f'epoca {epoca}: train={perdida_ent:.4f} val={perdida_val:.4f} '
              f'f1_macro_val={macro:.4f} ({historial[-1]["segundos"]}s)',
              flush=True)
        if scheduler is not None:
            scheduler.step()
        if not args.humo:
            ckpt = {'modelo': modelo.state_dict(), 'epoca': epoca,
                    'f1_macro_val': macro, 'clases': CLASES,
                    'config': vars(args)}
            torch.save(ckpt, args.salida / 'ultimo.pt')
            if macro > mejor_f1:
                mejor_f1 = macro
                mejor_epoca = epoca
                torch.save(ckpt, args.salida / 'mejor.pt')
            if macro > mejor_paciencia + args.min_delta:
                mejor_paciencia = macro
                sin_mejora = 0
            else:
                sin_mejora += 1
                if args.paciencia and sin_mejora >= args.paciencia:
                    print(f'parada temprana: sin mejora >= {args.min_delta} '
                          f'durante {args.paciencia} épocas', flush=True)
                    break

    (args.salida / 'historial.json').write_text(json.dumps(historial, indent=2))

    if args.humo:  # gate de humo: pérdida decrece y F1 se calculó
        assert historial[0]['perdida_train'] > historial[-1]['perdida_train'], \
            'la pérdida no decrece en el humo'
        assert 0.0 <= historial[-1]['f1_macro_val'] <= 1.0
        print('F16 HUMO VERDE')
        return

    try:
        mejor_ckpt = torch.load(args.salida / 'mejor.pt',
                                 map_location=dispositivo, weights_only=False)
    except TypeError:  # compatibilidad con versiones antiguas de PyTorch
        mejor_ckpt = torch.load(args.salida / 'mejor.pt', map_location=dispositivo)
    modelo.load_state_dict(mejor_ckpt['modelo'])
    perdida_val, f1s, ys, ps, probs = evaluar(modelo, val_dl, dispositivo)
    pred = val_ds.filas[['window_id', 'paciente', 'registro', 'clase']].copy()
    pred = pred.rename(columns={'clase': 'clase_real'})
    pred['clase_pred'] = [CLASES[i] for i in ps]
    for i, clase in enumerate(CLASES):
        pred[f'prob_{clase}'] = probs[:, i]
    pred.to_csv(args.salida / 'predicciones_val.csv', index=False)
    pd.DataFrame(matriz_confusion(ys, ps), index=CLASES,
                 columns=CLASES).to_csv(args.salida / 'matriz_confusion_val.csv')
    resumen = {
        'mejor_epoca': mejor_epoca,
        'f1_macro_val': mejor_f1,
        'f1_por_clase': dict(zip(CLASES, f1s.tolist())),
        'perdida_val': perdida_val,
        'conteos_train': train_ds.filas.clase.value_counts().to_dict(),
        'conteos_val': val_ds.filas.clase.value_counts().to_dict(),
        'config': {k: str(v) if isinstance(v, Path) else v
                   for k, v in vars(args).items()},
    }
    (args.salida / 'resumen.json').write_text(json.dumps(resumen, indent=2))

    gate = (f'F1 macro val (ventana): {mejor_f1:.4f} vs gate {GATE_F1} -> '
            f'{"VERDE" if mejor_f1 > GATE_F1 else "ROJO (1 diagnostico max.)"}')
    (args.salida / args.nombre_gate).write_text(gate + '\n')
    print(gate, flush=True)


if __name__ == '__main__':
    main()
