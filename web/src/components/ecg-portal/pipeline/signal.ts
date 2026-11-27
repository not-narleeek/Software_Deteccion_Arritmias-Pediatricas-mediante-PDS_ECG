/* ============================================================
   Datos deterministas de la demo interactiva del pipeline PDS.
   Series sintéticas de un ECG pediátrico de 10 s a 500 Hz
   (canal i): mismas formas de onda en cada carga, sin
   aleatoriedad, para que los seis visuales del navegador de
   etapas sean reproducibles y comparables entre sesiones.
   ============================================================ */

/** Punto de una serie: t en segundos (0…10) y v en mV. */
export interface Punto {
  t: number;
  v: number;
}

/** Recuadro de proyección en coordenadas del viewBox SVG. */
export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export const FS = 500; // muestreo del registro (Hz)
export const DURACION = 10; // largo del tramo (s)
export const T_MAX = DURACION;
export const V_MIN = -0.6; // dominio vertical del lienzo (mV)
export const V_MAX = 1.5;

/* ---------- ritmo del ejemplo: FC ≈ 118 lpm ---------- */

const T_PRIMER_LATIDO = 0.68; // primer pico R (s)

/** 17 intervalos RR (ms); media ≈ 509 ms → FC ≈ 118 lpm. */
export const RR_MS: number[] = Array.from({ length: 17 }, (_, i) =>
  509 + Math.round(9 * Math.sin(i * 2.4)),
);

/** 18 picos R (s) derivados de los RR sobre la base de 0,68 s. */
export const R_PEAKS: number[] = (() => {
  const picos: number[] = [T_PRIMER_LATIDO];
  for (const rr of RR_MS) picos.push(picos[picos.length - 1] + rr / 1000);
  return picos;
})();

export const FC_LPM = Math.round(
  60000 / (RR_MS.reduce((a, b) => a + b, 0) / RR_MS.length),
); // ≈ 118

export const LATIDOS = R_PEAKS.length; // 18
export const INTERVALOS_RR = RR_MS.length; // 17

/** Amplitud del pico R del ejemplo (mV), para anclar marcadores. */
export const AMPLITUD_R = 1.32;

/* ---------- forma de onda sintética del latido ---------- */

const gauss = (dt: number, mu: number, sigma: number) =>
  Math.exp(-((dt - mu) ** 2) / (2 * sigma * sigma));

/** Complejo P-QRS-T analítico centrado en el pico R del latido. */
function latido(dt: number): number {
  return (
    0.1 * gauss(dt, -0.16, 0.022) + // onda P
    -0.09 * gauss(dt, -0.022, 0.008) + // onda Q
    1.05 * gauss(dt, 0, 0.01) + // pico R
    -0.22 * gauss(dt, 0.026, 0.009) + // onda S
    0.28 * gauss(dt, 0.32, 0.045) // onda T
  );
}

/** Deriva lenta de la línea base (mV). */
function deriva(t: number): number {
  return (
    0.07 * Math.sin(2 * Math.PI * 0.28 * t + 0.4) +
    0.03 * Math.sin(2 * Math.PI * 0.11 * t + 2.1)
  );
}

/** Ruido de red de 50 Hz + ruido muscular de alta frecuencia (mV). */
function ruidoRed(t: number): number {
  return (
    0.035 * Math.sin(2 * Math.PI * 50 * t + 0.7) +
    0.008 * Math.sin(2 * Math.PI * 185 * t)
  );
}

function senalBase(t: number): number {
  let v = 0;
  for (const r of R_PEAKS) v += latido(t - r);
  return v;
}

/** Valor de la señal en un instante t; cruda incluye ruido y deriva. */
export function muestra(t: number, cruda = false): number {
  const base = senalBase(t);
  return cruda ? base + deriva(t) + ruidoRed(t) : base;
}

/** Serie lista para dibujar: 1.251 puntos (500 Hz, cada 4 muestras). */
function serie(cruda: boolean): Punto[] {
  const puntos: Punto[] = [];
  for (let n = 0; n <= DURACION * FS; n += 4) {
    const t = n / FS;
    const base = senalBase(t);
    puntos.push({
      t,
      v: cruda ? base + deriva(t) + ruidoRed(t) : base,
    });
  }
  return puntos;
}

/** Señal cruda tal como llega del registro. */
export const RAW: Punto[] = serie(true);

/** Señal filtrada (sin ruido de red ni deriva). */
export const CLEAN: Punto[] = serie(false);

/* ---------- características ---------- */

/** 24 coeficientes DCT del tramo (positivos y negativos). */
export const DCT: number[] = [
  0.86, 0.62, -0.34, 0.48, 0.21, -0.27, 0.18, -0.12, 0.14, 0.09, -0.11, 0.07,
  -0.08, 0.06, -0.05, 0.05, -0.04, 0.03, 0.03, -0.03, 0.02, -0.02, 0.01, -0.01,
];

/* ---------- clasificación y diagnóstico ---------- */

/** Probabilidades por clase de ritmo; Paced dominante, suma 1,00. */
export const PROBABILIDADES = [
  { clase: "Paced", p: 0.87 },
  { clase: "Normal", p: 0.06 },
  { clase: "Bradicardia", p: 0.04 },
  { clase: "Taquicardia", p: 0.02 },
  { clase: "Indeterminado", p: 0.01 },
] as const;

export const DIAGNOSTICO = {
  ritmo: "marcapasos",
  certeza: 0.87,
  brier: 0.037,
} as const;

/** Registro de ejemplo de la etapa de adquisición. */
export const REGISTRO = {
  formato: "WFDB",
  corpus: "ZZU pECG",
  duracion: "10 s",
  muestreo: "500 Hz",
  canal: "i",
} as const;

/* ---------- proyección a coordenadas SVG ---------- */

/** Proyecta un punto (t, v) al sistema de coordenadas del SVG. */
export function mapPoint(p: Punto, box: Box): [number, number] {
  return [
    Math.round((box.x + (p.t / T_MAX) * box.w) * 10) / 10,
    Math.round((box.y + box.h * (1 - (p.v - V_MIN) / (V_MAX - V_MIN))) * 10) / 10,
  ];
}

/** Camino SVG (polilínea) para una serie dibujada dentro de un Box. */
export function buildPath(points: Punto[], box: Box): string {
  let d = "";
  for (let i = 0; i < points.length; i += 1) {
    const [x, y] = mapPoint(points[i], box);
    d += `${i === 0 ? "M" : " L"}${x} ${y}`;
  }
  return d;
}
