/* ============================================================
   Análisis de señales ECG — portal de demostración.
   Port de web/js/app.js del proyecto
   Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG.
   Análisis heurístico 100 % en el navegador.
   NO es el modelo F22 del proyecto ni un dispositivo médico.
   ============================================================ */

export const CLASES = ["Sinusal", "SVT", "VT", "Paced", "Otro"] as const;
export type Clase = (typeof CLASES)[number];

export type ColorClase = "verde" | "ambar" | "rojo" | "violeta" | "gris";

export const COLOR_CLASE: Record<Clase, ColorClase> = {
  Sinusal: "verde",
  SVT: "ambar",
  VT: "rojo",
  Paced: "violeta",
  Otro: "gris",
};

export const CLASES_BARRA: Record<ColorClase, { fill: string; texto: string }> = {
  verde: { fill: "bg-emerald-500", texto: "text-emerald-700" },
  ambar: { fill: "bg-amber-500", texto: "text-amber-700" },
  rojo: { fill: "bg-red-500", texto: "text-red-700" },
  violeta: { fill: "bg-violet-500", texto: "text-violet-700" },
  gris: { fill: "bg-slate-400", texto: "text-slate-700" },
};

/* Rangos de FC normal en pediatría (aproximación por grupos de edad) */
export interface RangoEdad {
  label: string;
  lo: number;
  hi: number;
}

export type ClaveEdad =
  | "desconocida"
  | "lactante"
  | "preescolar"
  | "escolarMenor"
  | "escolarMayor"
  | "adolescente";

export const RANGO_EDAD: Record<ClaveEdad, RangoEdad> = {
  lactante: { label: "Lactante (menos de 1 año)", lo: 100, hi: 180 },
  preescolar: { label: "1 a 3 años", lo: 90, hi: 150 },
  escolarMenor: { label: "4 a 8 años", lo: 80, hi: 140 },
  escolarMayor: { label: "9 a 12 años", lo: 70, hi: 120 },
  adolescente: { label: "Más de 12 años", lo: 60, hi: 100 },
  desconocida: { label: "No indicada", lo: 60, hi: 160 },
};

/* ---------- utilidades de formato ---------- */
export function fmt(x: number, dec = 0): string {
  return Number.isFinite(x)
    ? x.toLocaleString("es-CL", {
        minimumFractionDigits: dec,
        maximumFractionDigits: dec,
      })
    : "—";
}

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

/* ---------- utilidades matemáticas ---------- */
function media(a: number[]): number {
  if (!a.length) return NaN;
  let s = 0;
  for (const v of a) s += v;
  return s / a.length;
}

function desv(a: number[]): number {
  const m = media(a);
  if (a.length <= 1) return NaN;
  let s = 0;
  for (const v of a) s += (v - m) * (v - m);
  return Math.sqrt(s / (a.length - 1));
}

function rmssd(a: number[]): number {
  if (a.length <= 1) return NaN;
  let s = 0;
  for (let i = 1; i < a.length; i++) s += (a[i] - a[i - 1]) ** 2;
  return Math.sqrt(s / (a.length - 1));
}

function pnn50(a: number[]): number {
  if (a.length < 2) return NaN;
  let c = 0;
  for (let i = 1; i < a.length; i++) if (Math.abs(a[i] - a[i - 1]) > 50) c++;
  return (100 * c) / (a.length - 1);
}

function mediana(a: number[] | Float32Array): number {
  const s = Array.from(a).sort((x, y) => x - y);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function percentil(a: number[] | Float32Array, p: number): number {
  const s = Array.from(a).sort((x, y) => x - y);
  return s[Math.min(s.length - 1, Math.max(0, Math.round(p * (s.length - 1))))];
}

/* ---------- detección de picos R (umbral adaptativo simple) ---------- */
export function detectarPicos(sig: ArrayLike<number>, fs: number): number[] {
  const n = sig.length;
  const sm = new Float32Array(n);
  const K = Math.max(1, Math.round(fs / 100)); // ~10 ms de suavizado
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc += sig[i];
    if (i >= K) acc -= sig[i - K];
    sm[i] = acc / Math.min(i + 1, K);
  }
  const p95 = percentil(sm, 0.95);
  const med = mediana(sm);
  // El umbral adaptativo p95 puede quedar a nivel de onda T / espícula (los QRS
  // angostos ocupan <5 % de las muestras); nunca baja de la mitad del nivel pico (p99).
  const thr = Math.max(med + 0.4 * (p95 - med), 0.5 * percentil(sm, 0.99));
  const minDist = Math.round(0.2 * fs); // 200 ms → máx 300 lpm
  const picos: number[] = [];
  for (let i = 1; i < n - 1; i++) {
    if (sm[i] > thr && sm[i] >= sm[i - 1] && sm[i] > sm[i + 1]) {
      const ultimo = picos.length ? picos[picos.length - 1] : -Infinity;
      if (i - ultimo >= minDist) picos.push(i);
      else if (sm[i] > sm[ultimo]) picos[picos.length - 1] = i;
    }
  }
  return picos;
}

export function rrDesdePicos(picos: number[], fs: number): number[] {
  const rr: number[] = [];
  for (let i = 1; i < picos.length; i++) {
    const ms = ((picos[i] - picos[i - 1]) * 1000) / fs;
    if (ms >= 250 && ms <= 2500) rr.push(ms); // descarta intervalos imposibles
  }
  return rr;
}

/* ---------- morfología: ancho QRS medio (ms) ---------- */
export function anchoQRSmedio(
  sig: ArrayLike<number>,
  fs: number,
  picos: number[],
): number | null {
  const base = mediana(Array.from(sig));
  const anchos: number[] = [];
  for (const p of picos) {
    let A = 0;
    for (let k = Math.max(0, p - 3); k <= Math.min(sig.length - 1, p + 3); k++) {
      A = Math.max(A, Math.abs(sig[k] - base));
    }
    if (A < 0.15) continue; // latido demasiado pequeño
    const thr = 0.12 * A;
    let l = p;
    let r = p;
    while (l > 0 && Math.abs(sig[l - 1] - base) > thr && p - l < 0.25 * fs) l--;
    while (r < sig.length - 1 && Math.abs(sig[r + 1] - base) > thr && r - p < 0.25 * fs) r++;
    anchos.push(((r - l + 1) * 1000) / fs);
  }
  return anchos.length ? mediana(anchos) : null;
}

/* ---------- morfología: espículas de marcapasos ---------- */
export function hayEspiculas(
  sig: ArrayLike<number>,
  fs: number,
  picos: number[],
): boolean | null {
  const ventana = Math.round(0.09 * fs); // 90 ms antes del pico R
  const maxAnchos = Math.max(2, Math.round(0.01 * fs)); // subida muy angosta
  let conEspicula = 0;
  let evaluados = 0;
  for (const p of picos) {
    const ini = Math.max(1, p - ventana);
    const fin = Math.max(1, p - Math.round(0.01 * fs));
    if (fin <= ini) continue;
    let dmax = 0;
    for (let i = ini; i <= fin; i++) {
      dmax = Math.max(dmax, Math.abs(sig[i] - sig[i - 1]));
    }
    if (dmax <= 0) continue;
    const pend = (dmax * fs) / 1000; // mV por ms
    let anchos = 0;
    for (let i = ini; i <= fin; i++) {
      if ((Math.abs(sig[i] - sig[i - 1]) * fs) / 1000 > 0.5 * pend) anchos++;
    }
    evaluados++;
    if (pend > 0.08 && anchos <= maxAnchos) conEspicula++;
  }
  return evaluados >= 3 ? conEspicula / evaluados > 0.5 : null;
}

/* ---------- métricas de variabilidad ---------- */
export interface MetricasRR {
  n: number;
  fc: number;
  rrMedio: number;
  sdnn: number;
  rmssd: number;
  pnn50: number;
  cv: number;
}

export function metricas(rr: number[]): MetricasRR {
  const m = media(rr);
  return {
    n: rr.length,
    fc: 60000 / m,
    rrMedio: m,
    sdnn: desv(rr),
    rmssd: rmssd(rr),
    pnn50: pnn50(rr),
    cv: desv(rr) / m,
  };
}

/* ---------- clasificador heurístico de demostración ---------- */
export interface ContextoClasificacion extends MetricasRR {
  anchoQRS: number | null;
  espiculas: boolean | null;
  edad: ClaveEdad;
}

export interface ResultadoClasificacion {
  clase: Clase;
  probs: Record<Clase, number>;
  advertencias: string[];
}

export function clasificar(ctx: ContextoClasificacion): ResultadoClasificacion {
  if (ctx.n < 3 || !Number.isFinite(ctx.fc)) {
    const p = 0.2;
    return {
      clase: "Otro",
      probs: { Sinusal: p, SVT: p, VT: p, Paced: p, Otro: p },
      advertencias: [
        "No se detectaron suficientes latidos en el tramo: revise la calidad o el formato de la señal.",
      ],
    };
  }
  const rango = RANGO_EDAD[ctx.edad] || RANGO_EDAD.desconocida;
  const adv: string[] = [];
  const s: Record<Clase, number> = {
    Sinusal: 0.06,
    SVT: 0.06,
    VT: 0.05,
    Paced: 0.03,
    Otro: 0.06,
  };
  const hr = ctx.fc;
  const regular = ctx.cv <= 0.06 ? 1 : ctx.cv <= 0.12 ? 0.5 : 0;

  /* Taquicardia supraventricular: rápida y regular */
  s.SVT += clamp01((hr - 145) / 35) + 0.2 * regular * (hr >= 130 ? 1 : 0);

  /* VT: complejos anchos y frecuencia elevada */
  if (ctx.anchoQRS != null) {
    s.VT += clamp01((ctx.anchoQRS - 115) / 50) * 2.2 * (hr >= 100 ? 1 : 0.3);
  }

  /* Sinusal vs Otro según rango esperado para la edad */
  if (hr >= rango.lo && hr <= rango.hi) {
    s.Sinusal += 0.8 * regular + 0.3 * clamp01((rango.hi - hr) / 50);
  } else if (hr < rango.lo) {
    s.Otro += 0.7;
    adv.push(
      `FC bajo el rango esperado para la edad indicada (${rango.lo}–${rango.hi} lpm): ${fmt(hr, 0)} lpm (bradicardia relativa).`,
    );
  } else if (hr <= rango.hi + 15) {
    s.Otro += 0.5;
    adv.push(
      `FC sobre el rango esperado para la edad indicada (${rango.lo}–${rango.hi} lpm): ${fmt(hr, 0)} lpm.`,
    );
  } else {
    s.SVT += 0.5;
    adv.push(
      `FC sobre el rango esperado para la edad indicada (${rango.lo}–${rango.hi} lpm): ${fmt(hr, 0)} lpm (taquicardia).`,
    );
  }

  /* QRS ancho (≥120 ms): la SVT se define por complejos estrechos; descuenta SVT */
  if (ctx.anchoQRS != null && ctx.anchoQRS >= 120) s.SVT *= 0.35;

  /* Irregularidad marcada: fuera del alcance del modelo */
  if (ctx.cv > 0.12) {
    s.Otro += 0.7;
    adv.push(
      "Ritmo irregular (variabilidad de RR alta): los ritmos irregulares están fuera del alcance del modelo.",
    );
  }
  if (ctx.n < 6) {
    adv.push(
      `Pocos latidos en el tramo (${ctx.n} intervalos RR): resultado poco confiable.`,
    );
  }

  /* Espículas de marcapasos: evidencia fuerte de ritmo Paced */
  if (ctx.espiculas === true) {
    s.Paced += 2.0;
    s.Sinusal *= 0.4;
    s.SVT *= 0.5;
    s.VT *= 0.5;
  }

  let tot = 0;
  for (const k of CLASES) tot += s[k];
  const probs = {} as Record<Clase, number>;
  for (const k of CLASES) probs[k] = s[k] / tot;
  let clase: Clase = "Otro";
  let mejor = 0;
  for (const k of CLASES) {
    if (probs[k] > mejor) {
      mejor = probs[k];
      clase = k;
    }
  }

  if (clase === "VT") {
    adv.push("La clase VT tiene soporte escaso en el corpus de desarrollo (92 casos).");
  }
  if (clase === "Paced") {
    adv.push("La clase Paced tiene muy pocos casos en el corpus (22 registros).");
  }
  if (mejor < 0.5) {
    adv.push("Diferencia débil entre clases: repita con otra ventana o revise la calidad de la señal.");
  }

  return { clase, probs, advertencias: adv };
}

/* ---------- reporte de texto descargable ---------- */
export function generarReporte(
  res: ResultadoClasificacion,
  ctx: ContextoClasificacion,
  fuente: string,
  edadClave: ClaveEdad,
  fechaStr: string,
): string {
  const rango = RANGO_EDAD[edadClave] || RANGO_EDAD.desconocida;
  const lineas: string[] = [
    "REPORTE DE ANÁLISIS — PORTAL DE DEMOSTRACIÓN (académico, no certificado)",
    "Proyecto TICS-II-2026-ECG-PED · Universidad Diego Portales",
    `Fecha: ${fechaStr}`,
    `Fuente: ${fuente}`,
    `Edad indicada: ${rango.label} (rango Sinusal ${rango.lo}–${rango.hi} lpm)`,
    "",
    "RESULTADO",
    `  Ritmo sugerido: ${res.clase}`,
    `  Certeza estimada: ${Math.round(res.probs[res.clase] * 100)} %`,
    ...CLASES.map((k) => `  P(${k}): ${Math.round(res.probs[k] * 100)} %`),
    "",
    "MEDIDAS",
    `  FC media: ${fmt(ctx.fc, 0)} lpm`,
    `  RR medio: ${fmt(ctx.rrMedio, 0)} ms`,
    `  SDNN: ${fmt(ctx.sdnn, 0)} ms | RMSSD: ${fmt(ctx.rmssd, 0)} ms | pNN50: ${fmt(ctx.pnn50, 0)} %`,
    `  Ancho QRS: ${ctx.anchoQRS != null ? fmt(ctx.anchoQRS, 0) + " ms" : "No evaluable"}`,
    `  Espículas de marcapasos: ${ctx.espiculas === true ? "Detectadas" : ctx.espiculas === false ? "No detectadas" : "No evaluable"}`,
    "",
    "ADVERTENCIAS",
    ...(res.advertencias.length
      ? res.advertencias.map((a) => `  - ${a}`)
      : ["  - Ninguna"]),
    "",
    "AVISO: Esta demo no es un dispositivo médico. No diagnostica ni reemplaza el juicio profesional.",
  ];
  return lineas.join("\n");
}
