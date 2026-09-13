# Análisis exploratorio ZZU pECG — metodología y hallazgos

Creado: 2026-09-13 (rama `busqueda-datos`, AP-13). Script:
`scripts/analisis_zzu.py` → salidas en `results/analisis_zzu/`
(demografia.csv, multietiqueta.csv, coocurrencia.csv, hr_muestra.csv,
hr_por_clase.csv, senal_muestra.csv, resumen.txt). Insumo:
`results/inventario_zzu/registros.csv` (ingesta verificada,
`docs/metodologia_zzu_pecg.md`).

## 1. Metodología

**A. Demografía y duraciones** (los 14.190 registros): mediana y cuartiles
de edad, % masculino y duración mediana por clase.

**B. Estructura de etiquetas AHA** (14.190): nº de enunciados por registro;
co-ocurrencia de grupos de clase (Paced/VT/SVT/Sinusal; códigos base sin
`+Modifier`); contradicciones = registros A1 ('Normal ECG') con algún
enunciado anormal no-modificador.

**C. Validación fisiológica por FC** — muestra estratificada con semilla
fija 42: TODOS los Paced (23), VT (103) y SVT (348) + 200 Sinusal y 200
Otro aleatorios (874). Pipeline por registro: derivación II **por nombre**
(inmune al orden/nomenclatura ZZU) → `preprocess.preprocesar`
(`FilterSpec(fs=500)`: HP 0,5 + notch 50 + LP 40, fase cero) →
`features.detectar_picos_r` Kathirvel II-only fs=500 (el detector de
producción F7, validado Se 98,9 % en Leipzig — su transferencia a ZZU es
una hipótesis de trabajo razonable al ser método, no población) →
FC = 60/mediana(RR); irregularidad CV_RR = std(RR)/mean(RR). Criterio
det_ok: 8 ≤ latidos y 30 ≤ FC ≤ 260 lpm (cota revisada tras resultados,
ver §2.C).

**D. Señal y calidad** (misma muestra, derivación II cruda): rango
p1–p99 (mV); fracción flatline (ventanas 1 s con std==0); interferencia de
red = pico PSD Welch (nperseg 2.500) en 49–51 Hz ÷ mediana 20–40 Hz;
deriva = potencia < 0,5 Hz / total.

Reproducible: `uv run python scripts/analisis_zzu.py` (~3 min).

## 2. Hallazgos

### A. Demografía coherente con la epidemiología pediátrica

| Clase | Registros | Pacientes | Edad med (IQR) | %M |
|---|---|---|---|---|
| Paced | 23 | 11 | 10,1 (8,4–11,9) | 56 % |
| VT | 103 | 53 | 8,8 (2,1–11,5) | 58 % |
| SVT | 348 | 222 | **5,3 (0,9–11,1)** | 50 % |
| Sinusal | 7.708 | 6.742 | 8,2 (4,0–12,2) | 56 % |
| Otro | 6.008 | 5.402 | 9,2 (5,0–12,7) | 59 % |

SVT concentra a los menores (mediana 5,3 a; cuartil inferior 0,9 a) —
consistente con el pico de taquicardias supraventriculares en lactantes.
Duración mediana 30 s en todas las clases.

### B. Etiquetas internamente consistentes

- Enunciados por registro: mediana 1, p90 3, máx 11; 49,8 % con >1
  enunciado — **coincide exactamente con el 49,80 % declarado por el
  paper** (validación cruzada paper↔datos).
- Solo 89 registros (0,6 %) tienen enunciados de >1 grupo de clase → la
  regla de prioridad (Paced>VT>SVT>Sinusal) afecta a pocos registros.
  Co-ocurrencias dominantes: SVT+Sinusal 60 (p. ej. EAT con enunciado
  sinusal concomitante), Sinusal+VT 14, SVT+VT 10, Paced+Sinusal 4.
- Contradicciones A1+anormal: 0,2 % — despreciable. Normales puros (solo
  A1): 1.882.

### C. La FC valida fisiológicamente las etiquetas (hallazgo central)

Muestra 874; det_ok 862 (98,6 %):

| Clase | n | FC med (IQR) | CV_RR med |
|---|---|---|---|
| VT | 101 | **156 (130–179)** | 0,11 |
| SVT | 340 | **151 (106–182)** | 0,15 |
| Paced | 23 | 111 (85–140) | 0,23 |
| Sinusal | 198 | 95 (76–123) | 0,06 |
| Otro | 200 | 86 (79–98) | 0,06 |

Ordenación exactamente como la clínica manda: VT ≈ SVT taquicárdicas,
Sinusal/Otro en rango pediátrico normal. Dentro de Sinusal, por
subgrupo (validación fina de etiquetas):

| Subgrupo | n | FC med (IQR) |
|---|---|---|
| C21 sinuso-taquicardia | 71 | **133 (118–155)** |
| C23 arritmia sinusal | 40 | 79 (73–89) |
| A1 normal | 48 | 89 (79–103) |
| A2 casi normal | 10 | 84 (76–93) |
| C22 sinuso-braquicardia | 29 | **57 (52–58)** |

C21 > A1 > C22 sin solapamiento de cuartiles: **los códigos AHA contienen
señal fisiológica real, no ruido administrativo** — la base de todo el
mapeo AP-1 se sostiene.

Los 12 registros sin det_ok se descomponen en dos causas:
1. **5 son detecciones correctas con FC real 268–273 lpm en neonatos**
   (0,02–0,13 años; SVT neonatal genuina — la cota 260 era demasiado
   ajustada). La cota debe ser 300 lpm para < 1 año.
2. **7 son tomas defectuosas** con amplitudes imposibles (rango_mv 5–43 mV;
   el máximo fisiológico en II es ~4 mV) donde el detector cuenta
   artefactos de movimiento/electrodo (1–4 "latidos"). Uno además con
   pico de red 271×.

### D. Señal limpia (a diferencia de Leipzig)

Medianas por clase: interferencia 50 Hz 0–0,3× el piso espectral
(**prácticamente ausente** — el MedEx MECG-300 filtra en origen, como
declaraba el paper), flatline 0 %, deriva <0,5 Hz ≈ 0,1 % de la potencia,
rango mediano 1,2–1,8 mV. Sin saturación.

## 3. Implicaciones para el diseño

1. **Marcador de "examen mal tomado" mejor que bSQI**: rango_mv > 5 mV en
   derivación II (0,8 % de la muestra; ~110 registros extrapolados).
   bSQI bajo se confunde con arritmia (§3.4 de busqueda_datos.md); el
   rango fisiológico no. Regla propuesta al construir el índice: excluir
   rango_mv > 5 mV (lista explícita), mantener marca bsqi < 0,95.
2. **Cota de FC para neonatos**: hasta 300 lpm en < 1 año (valores
   limítrofes 260–273 aparecen como SVT neonatal legítima).
3. **Notch 50 Hz**: innecesario en ZZU (ausente) pero inofensivo —
   mantener la cadena única (requerida por Leipzig).
4. **CV_RR confundido**: SVT (0,15) más "irregular" que Sinusal (0,06)
   porque el grupo mezcla EAT/AFIB con SVT regular — como feature hay que
   acompañarlo del subtipo; no usarlo solo como separador.
5. **Desequilibrio etario dentro de SVT** (mediana 5,3 a): estratificar
   por edad la validación (LORO adicional por banda etaria) para no
   esconder el rendimiento en neonatos.
6. **Transferencia del detector F7 Leipzig→ZZU funciona** (98,6 % det_ok
   con II-only en ZZU): la integración en `io.py` es de bajo riesgo;
   queda medir la fusión II+V2 en 12-deriv.
