# Resultados F23 — especialista binario VT

## Formulación

F23 añadió una ResNet binaria `VT vs resto` delante de la cascada F22. El
especialista se entrenó una sola vez con seed 23 y un split interno por paciente
creado exclusivamente dentro de train: 7.132 pacientes para ajuste y 1.783 para
calibración, sin solapamiento ni consulta de test. El umbral se eligió en esa
calibración con una precisión mínima de 0,50.

El mejor checkpoint fue la época 6. En calibración obtuvo F1 0,7152, precisión
0,8676 y sensibilidad 0,6082 con umbral 0,9961. Al transferir ese umbral a la
validación fija, el especialista obtuvo F1 0,3051, precisión 0,8182 y
sensibilidad 0,1875: 9 TP, 2 FP y 39 FN.

## Resultado multisemilla

| Seed F22 | Estado F23 | F1 macro | F1 Paced | F1 VT |
| ---: | :---: | ---: | ---: | ---: |
| 14 | VERDE | 0,6079 | 0,7368 | 0,4722 |
| 42 | ROJO | 0,6027 | 0,6667 | 0,3896 |
| 73 | ROJO | 0,5708 | 0,7368 | 0,3478 |
| Media | **ROJO (1/3)** | 0,5938 | 0,7135 | 0,4032 |

La desviación estándar fue 0,0201 para macro, 0,0405 para Paced y 0,0633 para
VT. F23 no estabilizó VT ni superó al mejor resultado F22.

## Diagnóstico y decisión

Los 9 verdaderos VT activados por el especialista ya eran VT correctos en F22.
Por tanto, la rama no recuperó ningún VT adicional. Sus únicas modificaciones
efectivas fueron 2 SVT que F22 clasificaba correctamente y que pasaron a falsos
VT. El problema no fue precisión del especialista sino cobertura y falta de
complementariedad con el modelo base.

Se descarta F23 para la entrega. El candidato se mantiene en F22 seed 14:
F1 macro 0,6125, Paced 0,7368 y VT 0,4857, con gate completamente verde. Test
permanece sin consultar.

## Evidencia y cierre

Los artefactos están en `runs/f23_especialista_vt/`. El rescate incluye el
checkpoint, predicciones, split interno, gates por seed, resumen multisemilla y
log de supervisor. Los hashes críticos se verificaron contra Vast.ai antes de
detener la instancia.
