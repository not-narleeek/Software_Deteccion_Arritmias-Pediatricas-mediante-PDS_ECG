# ADR 0004 — especialista binario VT train-only

- Estado: aceptado para ablación F23
- Fecha: 2026-11-17

## Contexto

F22 logró el primer gate completamente verde en seed 14, pero VT varió entre
0,4857, 0,4000 y 0,3556 en seeds 14/42/73. Macro-F1 y `Paced` fueron estables;
la debilidad restante es la competencia multiclase de VT con soporte escaso.

## Decisión

F23 añade una ResNet binaria `VT vs resto`. Dentro de train activo, los
pacientes se separan 80/20 en ajuste y calibración mediante estratificación a
nivel paciente. El threshold se aprende solo en calibración interna maximizando
F1 sujeto a precisión mínima 0,50. Validación fija no interviene en el ajuste.

El sampler asigna 10% de masa esperada a VT y equilibra esa masa entre
pacientes VT. No se aplica augmentation. En inferencia, una predicción positiva
del especialista VT tiene prioridad sobre la cascada F22 completa.

## Consecuencias

- VT recibe un objetivo y threshold propios sin alterar F20/F22.
- El despliegue requiere un tercer checkpoint y su threshold versionado.
- Una calibración interna única puede seguir siendo sensible al split; F23 se
  evalúa sobre las tres seeds F22 antes de cualquier test.
- Test permanece inaccesible durante selección.

## Reversión

Omitir el especialista y su regla de prioridad restaura exactamente F22.
