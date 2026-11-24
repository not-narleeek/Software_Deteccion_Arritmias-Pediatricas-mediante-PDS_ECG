"""Valida contratos de arquitectura F21 sin consultar datos ni test."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch


RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'scripts'))

from entrenar_baseline_dl import FEATURES_HF, ResNet1D  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint-f20', type=Path)
    p.add_argument('--salida', type=Path)
    args = p.parse_args()

    torch.manual_seed(21)
    x = torch.randn(2, 12, 500)
    hf_a = torch.zeros(2, len(FEATURES_HF), requires_grad=True)
    hf_b = torch.ones(2, len(FEATURES_HF))
    base = ResNet1D(escala=4).eval()
    concat = ResNet1D(escala=4, hf_dim=len(FEATURES_HF),
                      fusion_hf='concat').eval()
    residual = ResNet1D(escala=4, hf_dim=len(FEATURES_HF),
                        fusion_hf='paced_logit').eval()

    with torch.no_grad():
        forma_base = list(base(x).shape)
        forma_concat = list(concat(x, hf_b).shape)
        logits_a = residual(x, hf_a)
        logits_b = residual(x, hf_b)
    otras = [0, 1, 2, 4]
    invariancia = torch.equal(logits_a[:, otras], logits_b[:, otras])
    inicial_neutro = torch.equal(logits_a[:, 3], logits_b[:, 3])

    grad = torch.autograd.grad(
        residual(x, hf_a)[:, otras].sum(), hf_a, allow_unused=True)[0]
    grad_otras_cero = grad is None or torch.count_nonzero(grad).item() == 0

    compatibilidad_f20 = None
    if args.checkpoint_f20:
        try:
            ckpt = torch.load(args.checkpoint_f20, map_location='cpu',
                              weights_only=False)
        except TypeError:
            ckpt = torch.load(args.checkpoint_f20, map_location='cpu')
        modelo_f20 = ResNet1D(hf_dim=len(FEATURES_HF), fusion_hf='concat')
        esperadas = set(modelo_f20.state_dict())
        observadas = set(ckpt['modelo'])
        compatibilidad_f20 = {
            'ok': esperadas == observadas,
            'faltantes': sorted(esperadas - observadas),
            'sobrantes': sorted(observadas - esperadas),
        }

    errores = []
    if forma_base != [2, 5] or forma_concat != [2, 5]:
        errores.append('formas de salida incorrectas')
    if not invariancia or not grad_otras_cero:
        errores.append('HF altera logits no-Paced en paced_logit')
    if not inicial_neutro:
        errores.append('residual HF no inicia en cero')
    if compatibilidad_f20 and not compatibilidad_f20['ok']:
        errores.append('claves concat incompatibles con checkpoint F20')

    reporte = {
        'estado': 'FALLA' if errores else 'OK',
        'errores': errores,
        'forma_base': forma_base,
        'forma_concat': forma_concat,
        'hf_no_altera_logits_no_paced': invariancia,
        'gradiente_hf_no_paced_cero': grad_otras_cero,
        'residual_inicial_cero': inicial_neutro,
        'compatibilidad_checkpoint_f20': compatibilidad_f20,
        'test_consultado': False,
    }
    texto = json.dumps(reporte, indent=2)
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(texto + '\n')
    print(texto)
    if errores:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
