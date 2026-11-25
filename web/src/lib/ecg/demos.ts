/* ============================================================
   Casos de demostración — registros WFDB sintéticos generados
   en el navegador (equivalente TS de scripts/generar_demo_wfdb.py
   del proyecto). Determinísticos; no representan pacientes reales.
   12 derivaciones · 10 s @ 500 Hz · formato 16 · unidades mV.
   ============================================================ */

export type TipoDemo = "demo_sinusal" | "demo_svt" | "demo_vt" | "demo_paced";

export interface InfoDemo {
  id: TipoDemo;
  nombre: string;
  descripcion: string;
  dot: string; // clase de color Tailwind del indicador
}

export const DEMOS: InfoDemo[] = [
  {
    id: "demo_sinusal",
    nombre: "Niño sano (Sinusal)",
    descripcion: "Ritmo sinusal regular, ~118 lpm, QRS estrecho",
    dot: "bg-emerald-500",
  },
  {
    id: "demo_svt",
    nombre: "Taquicardia (SVT)",
    descripcion: "Taquicardia supraventricular, ~188 lpm, QRS estrecho",
    dot: "bg-amber-500",
  },
  {
    id: "demo_vt",
    nombre: "Taquicardia ventricular (VT)",
    descripcion: "Taquicardia ventricular, ~168 lpm, QRS ancho",
    dot: "bg-red-500",
  },
  {
    id: "demo_paced",
    nombre: "Marcapasos (Paced)",
    descripcion: "Ritmo de marcapasos, ~96 lpm, espículas antes de cada QRS",
    dot: "bg-violet-500",
  },
];

/* ---------- PRNG determinístico (mulberry32) ---------- */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* ---------- morfología del latido (suma de gaussianas) ---------- */
interface Gaussiana {
  mu: number; // ms respecto del pico R
  sigma: number; // ms
  amp: number; // mV
}

interface PlantillaClase {
  bpm: number;
  jitterMs: number;
  modulacionMs: number;
  componentes: Gaussiana[];
}

const PLANTILLAS: Record<TipoDemo, PlantillaClase> = {
  demo_sinusal: {
    bpm: 118,
    jitterMs: 6,
    modulacionMs: 5,
    componentes: [
      { mu: -210, sigma: 25, amp: 0.1 }, // onda P
      { mu: -18, sigma: 8, amp: -0.06 }, // Q
      { mu: 0, sigma: 13, amp: 1.05 }, // R
      { mu: 30, sigma: 11, amp: -0.18 }, // S
      { mu: 330, sigma: 45, amp: 0.22 }, // T
    ],
  },
  demo_svt: {
    bpm: 188,
    jitterMs: 3,
    modulacionMs: 2,
    componentes: [
      { mu: -14, sigma: 7, amp: -0.05 },
      { mu: 0, sigma: 11, amp: 0.9 },
      { mu: 24, sigma: 9, amp: -0.14 },
      { mu: 180, sigma: 30, amp: 0.1 },
    ],
  },
  demo_vt: {
    bpm: 168,
    jitterMs: 4,
    modulacionMs: 3,
    componentes: [
      { mu: 0, sigma: 45, amp: 1.2 }, // QRS ancho y dominante
      { mu: 300, sigma: 50, amp: -0.3 }, // T discordante
    ],
  },
  demo_paced: {
    bpm: 96,
    jitterMs: 5,
    modulacionMs: 3,
    componentes: [
      { mu: -55, sigma: 1.8, amp: 1.1 }, // espícula de marcapasos
      { mu: -16, sigma: 8, amp: -0.05 },
      { mu: 0, sigma: 14, amp: 0.85 },
      { mu: 28, sigma: 10, amp: -0.15 },
      { mu: 330, sigma: 45, amp: 0.25 },
    ],
  },
};

/* Derivaciones del registro de 12 leads y su amplitud relativa a II */
const LEADS: { nombre: string; factor: number }[] = [
  { nombre: "I", factor: 0.55 },
  { nombre: "II", factor: 1.0 },
  { nombre: "III", factor: 0.45 },
  { nombre: "aVR", factor: -0.7 },
  { nombre: "aVL", factor: -0.25 },
  { nombre: "aVF", factor: 0.8 },
  { nombre: "V1", factor: 0.4 },
  { nombre: "V2", factor: 0.55 },
  { nombre: "V3", factor: 0.7 },
  { nombre: "V4", factor: 0.85 },
  { nombre: "V5", factor: 0.95 },
  { nombre: "V6", factor: 0.9 },
];

const FS = 500; // Hz
const SEGUNDOS = 10;
const N_MUESTRAS = FS * SEGUNDOS; // 5000
const GANANCIA = 200; // unidades ADC por mV

function plantilla(componentes: Gaussiana[], dt: number): number {
  let v = 0;
  for (const d of componentes) {
    const x = (dt - d.mu) / d.sigma;
    v += d.amp * Math.exp(-0.5 * x * x);
  }
  return v;
}

/* Deriva los tiempos de los picos R para la clase indicada */
function tiemposBeats(p: PlantillaClase, rng: () => number): number[] {
  const rrBase = 60000 / p.bpm;
  const beats: number[] = [];
  let t = 250; // primer latido completo dentro de la ventana
  let k = 0;
  while (t < SEGUNDOS * 1000 - 400) {
    beats.push(t);
    const rr =
      rrBase +
      p.modulacionMs * Math.sin((2 * Math.PI * k) / 9) +
      (rng() * 2 - 1) * p.jitterMs;
    t += rr;
    k++;
  }
  return beats;
}

/* Señal de la derivación II (mV) con deriva respiratoria y ruido */
function senalLeadII(p: PlantillaClase, rng: () => number): Float64Array {
  const beats = tiemposBeats(p, rng);
  const senal = new Float64Array(N_MUESTRAS);
  for (const tR of beats) {
    const ini = Math.max(0, Math.floor((tR - 450) / (1000 / FS)));
    const fin = Math.min(N_MUESTRAS - 1, Math.ceil((tR + 600) / (1000 / FS)));
    for (let i = ini; i <= fin; i++) {
      const t = (i * 1000) / FS;
      senal[i] += plantilla(p.componentes, t - tR);
    }
  }
  for (let i = 0; i < N_MUESTRAS; i++) {
    const t = (i * 1000) / FS;
    const deriva =
      0.02 * Math.sin(2 * Math.PI * 0.25 * t + 0.8) +
      0.012 * Math.sin(2 * Math.PI * 0.6 * t + 1.3);
    const ruido = (rng() * 2 - 1) * 0.006;
    senal[i] += deriva + ruido;
  }
  return senal;
}

/* Genera el registro WFDB sintético (.hea + .dat) del caso indicado */
export function generarDemoWfdb(tipo: TipoDemo): { hea: string; dat: ArrayBuffer } {
  const p = PLANTILLAS[tipo];
  const rngPrincipal = mulberry32(
    tipo.split("").reduce((acc, c) => acc + c.charCodeAt(0) * 7, 42),
  );
  const leadII = senalLeadII(p, rngPrincipal);

  // .dat: muestras int16 LE entrelazadas por cuadro (12 señales)
  const dat = new ArrayBuffer(N_MUESTRAS * LEADS.length * 2);
  const vista = new DataView(dat);
  LEADS.forEach((lead, canal) => {
    const rng = mulberry32(
      canal * 1013 + tipo.split("").reduce((acc, c) => acc + c.charCodeAt(0), 7),
    );
    for (let i = 0; i < N_MUESTRAS; i++) {
      const ruido = (rng() * 2 - 1) * 0.005;
      const mv = leadII[i] * lead.factor + ruido;
      let adc = Math.round(mv * GANANCIA);
      adc = Math.max(-32000, Math.min(32000, adc));
      vista.setInt16((i * LEADS.length + canal) * 2, adc, true);
    }
  });

  // .hea: línea de registro + una línea de señal por derivación
  const lineasSenal = LEADS.map(
    (l) => `${tipo}.dat 16 200(0)/mV 12 0 0 0 0 ${l.nombre}`,
  );
  const hea = [`${tipo} 12 ${FS} ${N_MUESTRAS}`, ...lineasSenal].join("\n") + "\n";

  return { hea, dat };
}
