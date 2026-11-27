/* ============================================================
   signal.ts — Señales sintéticas y datos del caso demo para
   la visualización del pipeline PDS (ECG pediátrico).

   TODO el contenido es determinista (misma salida en servidor
   y en cliente) para evitar desajustes de hidratación: el
   "ruido" se construye con sumas de senos, nunca Math.random().
   ============================================================ */

export type Point = [number, number]; // [x 0..1, y en unidades de señal]

/** Parámetros del registro simulado. */
export const REGISTRO = {
  formato: "WFDB (ZZU pECG)",
  fs: 500, // Hz
  duracion: 10, // s
  canal: "II pediátrico",
} as const;

const T = REGISTRO.duracion;
const N_PUNTOS = 620; // resolución de dibujo

/** Gaussiana unitaria centrada en mu. */
function gauss(t: number, mu: number, sigma: number): number {
  const d = (t - mu) / sigma;
  return Math.exp(-0.5 * d * d);
}

/** Morfología de un latido pediátrico centrada en t = 0. */
function latido(t: number): number {
  return (
    0.13 * gauss(t, -0.16, 0.028) + // onda P
    -0.08 * gauss(t, -0.024, 0.009) + // onda Q
    1.0 * gauss(t, 0, 0.011) + // complejo QRS (R)
    -0.24 * gauss(t, 0.032, 0.012) + // onda S
    0.3 * gauss(t, 0.21, 0.05) // onda T
  );
}

/** Espícula de marcapasos ~70 ms antes del QRS. */
function espicula(t: number): number {
  return 0.62 * gauss(t, -0.07, 0.0035);
}

/** Intervalos RR del caso demo, en segundos (media ≈ 507 ms). */
const RR_S = [0.508, 0.515, 0.502, 0.503, 0.51, 0.499, 0.513, 0.505];

/** Instantes (s) donde ocurre cada latido dentro del registro. */
const BEAT_TIMES: number[] = (() => {
  const out: number[] = [];
  let t = 0.42;
  let i = 0;
  while (t < T - 0.35) {
    out.push(t);
    t += RR_S[i % RR_S.length];
    i += 1;
  }
  return out;
})();

/** Señal limpia (tras el filtrado ideal). */
function senalLimpia(t: number): number {
  let y = 0;
  for (const tb of BEAT_TIMES) y += latido(t - tb) + espicula(t - tb);
  return y;
}

/** Señal cruda: latidos + deriva de línea base + ruido de red 50 Hz. */
function senalCruda(t: number): number {
  const deriva =
    0.16 * Math.sin(2 * Math.PI * 0.32 * t) +
    0.06 * Math.sin(2 * Math.PI * 0.13 * t + 1.1);
  const red = 0.075 * Math.sin(2 * Math.PI * 50 * t);
  const clutter =
    0.02 * Math.sin(2 * Math.PI * 117 * t + 0.4) +
    0.015 * Math.sin(2 * Math.PI * 83 * t + 0.7) +
    0.012 * Math.sin(2 * Math.PI * 153 * t + 2.1);
  return senalLimpia(t) + deriva + red + clutter;
}

const Y_ESCALA = 1.35; // rango vertical de dibujo: -1.35 .. 1.35

/** Señal cruda normalizada para dibujar. */
export const RAW: Point[] = Array.from({ length: N_PUNTOS }, (_, i) => {
  const t = (i / (N_PUNTOS - 1)) * T;
  return [t / T, senalCruda(t) / Y_ESCALA] as Point;
});

/** Señal filtrada normalizada para dibujar. */
export const CLEAN: Point[] = Array.from({ length: N_PUNTOS }, (_, i) => {
  const t = (i / (N_PUNTOS - 1)) * T;
  return [t / T, senalLimpia(t) / Y_ESCALA] as Point;
});

/** Posición de los picos R sobre la señal limpia. */
export const R_PEAKS: Point[] = BEAT_TIMES.map(
  (tb) => [tb / T, 1.0 / Y_ESCALA] as Point,
);

/** Número de latidos del registro demo. */
export const NUM_LATIDOS = BEAT_TIMES.length;

/** Intervalos RR detectados, en ms. */
export const RR_MS: number[] = RR_S.map((v) => Math.round(v * 1000));

/** Frecuencia cardíaca media del caso demo. */
export const FC_LPM = Math.round(
  60000 / ((RR_S.reduce((a, b) => a + b, 0) / RR_S.length) * 1000),
);

function puntoCrudoEn(t: number): Point {
  const i = Math.max(
    0,
    Math.min(N_PUNTOS - 1, Math.round((t / T) * (N_PUNTOS - 1))),
  );
  return RAW[i];
}

/** Ancla sobre la señal cruda para el callout de ruido 50 Hz. */
export const MARCA_RUIDO: Point = puntoCrudoEn(5.8);

/** Ancla sobre la señal cruda para el callout de deriva de línea base. */
export const MARCA_DERIVA: Point = puntoCrudoEn(4.75);

/** Coeficientes DCT (espectro del tramo) del vector F22. */
export const DCT: number[] = Array.from({ length: 24 }, (_, k) => {
  const v = Math.pow(0.865, k) * Math.cos(k * 1.9 + 0.35) * 0.95;
  return Math.round(v * 1000) / 1000;
});

/** Características morfológicas del caso demo. */
export const MORFOLOGIA = [
  { k: "Ancho QRS", v: "78 ms" },
  { k: "Amplitud R", v: "1,32 mV" },
  { k: "Intervalo QT", v: "318 ms" },
  { k: "Espícula de marcapasos", v: "presente" },
] as const;

/** Características espectrales / de variabilidad. */
export const ESPECTRO = [
  { k: "Energía 0,5–40 Hz", v: "92,4 %" },
  { k: "Varianza RR", v: "4,2 %" },
  { k: "Coef. DCT usados", v: "24" },
] as const;

export type ProbabilidadClase = { clase: string; valor: number };

/** Distribución de probabilidades que devuelve el clasificador. */
export const PROBABILIDADES: ProbabilidadClase[] = [
  { clase: "Paced", valor: 0.87 },
  { clase: "Normal", valor: 0.06 },
  { clase: "Bradicardia", valor: 0.04 },
  { clase: "Taquicardia", valor: 0.02 },
  { clase: "Indeterminado", valor: 0.01 },
];

/** Diagnóstico final del caso demo. */
export const DIAGNOSTICO = {
  ritmo: "Ritmo de marcapasos",
  clase: "Paced",
  certeza: 0.87,
  nota: "Salida probabilística calibrada · Brier 0,037",
} as const;

/* ------------------------------------------------------------
   Utilidades de dibujo (coordenadas de señal → coordenadas SVG)
   ------------------------------------------------------------ */

export type Box = { x: number; w: number; yTop: number; h: number };

const Y_MIN = -1.35;
const Y_MAX = 1.35;

/** Mapea un punto de señal al sistema de coordenadas de la caja. */
export function mapPoint(p: Point, b: Box): [number, number] {
  const x = b.x + p[0] * b.w;
  const y = b.yTop + ((Y_MAX - p[1]) / (Y_MAX - Y_MIN)) * b.h;
  return [x, y];
}

/** Construye el atributo `d` de un <path> a partir de una señal. */
export function buildPath(pts: Point[], b: Box): string {
  return pts
    .map((p, i) => {
      const [x, y] = mapPoint(p, b);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}
