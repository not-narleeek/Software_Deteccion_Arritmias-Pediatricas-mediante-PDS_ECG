# ADR 0003 — cascada morfológica con gate Paced F20

- Estado: aceptado para ablación F22
- Fecha: 2026-11-16

## Contexto

F20 resolvió pacing activo (F1 0,6667) pero dejó VT en 0,3797. F21 restringió
HF al logit `Paced`, pero augmentation VT elevó los falsos positivos y redujo
F1 VT a 0,3462. El gate F20 predijo siete de diez ventanas `Paced`, pero también
clasificó cuatro ventanas VT como `Paced`.

El checkpoint F16 antiguo no puede evaluarse directamente sobre el split
activo: P05281 pertenecía a su train y ahora es el paciente `Paced` de val.

## Decisión

F22 entrena desde cero un modelo morfológico con configuración F16 sobre el
split activo. En inferencia se ignora su logit `Paced` y se elige por argmax
entre Sinusal, SVT, VT y Otro. Después, la predicción se reemplaza por `Paced`
solo cuando el especialista F20 predijo esa clase y morfología no predijo VT.
VT tiene prioridad explícita para impedir los cuatro errores observados.

No se ajusta un umbral nuevo sobre val. Se reutiliza la decisión categórica
F20 fijada antes de F22. Ambos especialistas se alinean estrictamente por
`window_id` y deben declarar la misma etiqueta real.

## Consecuencias

- VT no compite con features HF durante el entrenamiento morfológico.
- La protección VT limita el daño del gate `Paced` sobre esa clase.
- El despliegue requiere dos checkpoints y una regla de prioridad.
- El resultado sigue siendo desarrollo: F20 y F22 comparten validación y test
  permanece bloqueado hasta confirmación multisemilla.

## Reversión

F20 permanece intacto. Eliminar la etapa de cascada restaura sus predicciones;
no se modifican datos, splits ni checkpoints existentes.
