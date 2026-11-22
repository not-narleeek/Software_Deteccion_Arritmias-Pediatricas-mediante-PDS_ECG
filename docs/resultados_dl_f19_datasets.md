# Resultados F19 — datasets complementarios para Paced

## Adquisición validada

Se descargaron de PhysioNet y verificaron contra los SHA-256 oficiales:

| Fuente | Selección | Señales descargadas | Dominio |
| --- | ---: | ---: | --- |
| PTB-XL 1.0.3 | 294 `PACE` + 294 controles | 588 | adulto, 12 deriv., 10 s, 500 Hz |
| Leipzig 1.0.0 | 34/39 registros con pacing | 34 | 25 pediátricos + 9 adultos CHD, 977 Hz, LP 100 Hz |

PTB-XL contiene 294 registros `PACE` de 237 pacientes. No hay menores de 18
años; la edad mínima es 26 años. Leipzig aporta 13.779 latidos estimulados
anotados, de los cuales 11.685 pertenecen al grupo pediátrico. Los 25 registros
pediátricos con pacing suman 13,81 horas de señal.

El gate de lectura WFDB y checksums terminó VERDE. ZZU test no fue consultado.

## Baseline de alta frecuencia en PTB-XL

Se extrajeron ocho variables exclusivamente de señal: contador conservador de
espículas, RMS y percentiles en 80–237,5 Hz, pendientes extremas y sincronía
multiderivación. No se usaron edad, sexo, texto ni campos de marcapasos.

Protocolo: Random Forest con 5-fold `StratifiedGroupKFold` por paciente.

| Métrica | Resultado |
| --- | ---: |
| F1 Paced | 0,9757 |
| Precisión | 0,9965 |
| Sensibilidad | 0,9558 |
| Especificidad | 0,9966 |
| AUC ROC | 0,9824 |
| Matriz TN/FP/FN/TP | 293 / 1 / 13 / 281 |

La variable dominante fue la sincronía de alta frecuencia. El RMS HF mediano
fue 0,0398 mV en `PACE` frente a 0,00442 mV en controles. El detector rígido
encontró al menos una espícula en 64,3 % de `PACE`, por lo que la combinación
continua de energía, pendiente y sincronía es más informativa que un conteo
binario.

## Transferencia externa PTB-XL → Leipzig

Se ajustó el RF con todo el conjunto PTB-XL seleccionado y se aplicó sin
fine-tuning ni cambio del umbral 0,5 sobre hasta diez ventanas positivas y diez
negativas por paciente Leipzig. Las ventanas se etiquetaron mediante latidos
`/` o de fusión `f`; solo se usaron las 12 derivaciones superficiales.

| Cohorte Leipzig | Ventanas | F1 Paced | Sensibilidad | Especificidad | AUC ROC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Global | 616 | 0,8427 | 0,7722 | 0,9493 | 0,9328 |
| Pediátrica | 445 | 0,7932 | 0,7000 | 0,9469 | 0,9264 |
| Adultos CHD | 171 | 0,9506 | 0,9506 | 0,9556 | 0,9663 |

El descenso pediátrico confirma domain shift, pero la especificidad alta y el
AUC 0,926 sin ajuste externo demuestran que la señal aprendida no es exclusiva
de PTB-XL.

## Decisión

F19 respalda una rama auxiliar de alta frecuencia o un detector binario
preentrenado con PTB-XL y afinado con Leipzig pediátrico. No respalda mezclar
adultos con el clasificador multiclase ZZU ni evaluar el test.

El siguiente gate requiere recuperar el ECG crudo ZZU, recalcular estas ocho
variables en train/val y comprobar si P05649 conserva energía compatible con
pacing. Solo si hay separación en desarrollo ZZU corresponde implementar la
fusión con F16 y ejecutar una corrida GPU.
