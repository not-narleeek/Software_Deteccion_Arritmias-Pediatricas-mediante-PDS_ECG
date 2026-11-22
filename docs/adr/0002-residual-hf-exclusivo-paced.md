# ADR 0002 — residual HF exclusivo para el logit Paced

- Estado: aceptado para ablación F21
- Fecha: 2026-11-16

## Contexto

F20 concatenó el embedding morfológico con ocho variables HF antes de una
cabeza común de cinco clases. La semilla 14 mejoró F1 macro a 0,5927 y F1
`Paced` a 0,6667, pero redujo F1 VT a 0,3797, bajo el gate 0,4115. Cuatro de 48
ventanas VT se clasificaron como `Paced`, y las features HF podían modificar
directamente cualquiera de los cinco logits.

## Decisión

F21 conserva la rama morfológica y su cabeza de cinco clases. El MLP HF produce
un único residual que se suma exclusivamente al logit `Paced`; los logits
Sinusal, SVT, VT y Otro son funciones solo de la rama morfológica. La última
capa residual se inicializa en cero para comenzar como un modelo morfológico
neutral y aprender después la corrección de pacing.

El modo queda disponible como `--fusion-hf paced_logit`. `concat` continúa
siendo el valor por defecto para cargar y reproducir F20 sin migraciones.

F21 aplica augmentation conservadora únicamente a VT, LR 2e-4, scheduler
coseno, pesos inversos completos y parada temprana con paciencia 10. No cambia
split, sidecar, test ni thresholds.

## Consecuencias

- HF no puede crear confusiones directas entre VT y las clases no-Paced.
- `Paced` conserva una vía específica para evidencia de espículas.
- La interacción HF–morfología queda limitada a la competencia softmax con el
  logit `Paced`; no se modelan interacciones complejas para otras clases.
- Si F1 `Paced` cae o VT no supera 0,4115, el gate detiene la simulación y F20
  no se reemplaza.

## Reversión

Usar `--fusion-hf concat` reproduce F20; omitir sidecar reproduce el baseline
morfológico. No se requiere migrar datos ni checkpoints existentes.
