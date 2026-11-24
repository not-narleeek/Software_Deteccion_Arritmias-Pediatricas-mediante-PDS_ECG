# Model card — F22 seed 14

## Identificación

- Versión: `f22-seed14-v1`.
- Población de desarrollo: corpus pediátrico ZZU pECG.
- Entrada: ventana de 10 segundos, 500 Hz, hasta 12 derivaciones, expresada en
  milivoltios.
- Salida: Sinusal, SVT, VT, Paced u Otro.

F22 combina un clasificador morfológico con el especialista F20 para Paced. El
gate Paced solo reemplaza la salida morfológica cuando F20 predice Paced; una
predicción morfológica VT tiene prioridad y queda protegida.

## Resultado de selección

| Métrica de validación | F22 seed 14 |
| --- | ---: |
| F1 macro | 0,6125 |
| F1 Sinusal | 0,6215 |
| F1 SVT | 0,5385 |
| F1 VT | 0,4857 |
| F1 Paced | 0,7368 |
| F1 Otro | 0,6800 |

El candidato superó el gate interno definido para la entrega. Las métricas
corresponden a validación; el test final permaneció reservado.

## Limitaciones

- No es un dispositivo médico ni reemplaza la interpretación de un profesional.
- El número de pacientes Paced y VT es reducido.
- La estabilidad multisemilla y la evaluación final sobre test siguen
  pendientes.
- `confidence` es la probabilidad del especialista que tomó la decisión; no
  debe interpretarse como certeza clínica prospectiva.
- Señales con unidades, orden de derivaciones o frecuencia incorrectos producen
  resultados no comparables con la validación.

Uso permitido: investigación, docencia y demostración retrospectiva.
