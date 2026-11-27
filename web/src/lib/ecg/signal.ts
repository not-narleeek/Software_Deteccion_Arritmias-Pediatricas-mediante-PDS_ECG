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
  /** Puntajes brutos por clase antes de la normalización. */
  puntajes: Record<Clase, number>;
  /** Desglose auditable: cada regla aplicada y su efecto sobre los puntajes. */
  pasos: PasoAuditoria[];
}

/** Un paso del desglose auditable del diagnóstico. */
export interface PasoAuditoria {
  /** Magnitud evaluada (p. ej. «FC media»). */
  criterio: string;
  /** Valor observado, formateado para el reporte. */
  valor: string;
  /** Regla del clasificador que se aplica a ese valor. */
  regla: string;
  /** Efecto sobre los puntajes (p. ej. «SVT +0,42 · Sinusal ×0,40»). */
  efecto: string;
}

export function clasificar(ctx: ContextoClasificacion): ResultadoClasificacion {
  if (ctx.n < 3 || !Number.isFinite(ctx.fc)) {
    const p = 0.2;
    return {
      clase: "Otro",
      probs: { Sinusal: p, SVT: p, VT: p, Paced: p, Otro: p },
      puntajes: { Sinusal: p, SVT: p, VT: p, Paced: p, Otro: p },
      pasos: [
        {
          criterio: "Latidos detectados",
          valor: `${ctx.n} intervalos RR`,
          regla:
            "Se requieren al menos 3 intervalos RR válidos para clasificar el ritmo.",
          efecto: "Sin puntaje: «Otro» con certeza uniforme de 20 %.",
        },
      ],
      advertencias: [
        "No se detectaron suficientes latidos en el tramo: revise la calidad o el formato de la señal.",
      ],
    };
  }
  const rango = RANGO_EDAD[ctx.edad] || RANGO_EDAD.desconocida;
  const adv: string[] = [];
  const pasos: PasoAuditoria[] = [];
  const paso = (
    criterio: string,
    valor: string,
    regla: string,
    efecto: string,
  ) => pasos.push({ criterio, valor, regla, efecto });
  const s: Record<Clase, number> = {
    Sinusal: 0.06,
    SVT: 0.06,
    VT: 0.05,
    Paced: 0.03,
    Otro: 0.06,
  };
  paso(
    "Puntaje base",
    "—",
    "Inicialización del clasificador heurístico.",
    `Sinusal +${fmt(0.06, 2)} · SVT +${fmt(0.06, 2)} · VT +${fmt(0.05, 2)} · Paced +${fmt(0.03, 2)} · Otro +${fmt(0.06, 2)}`,
  );
  const hr = ctx.fc;
  const regular = ctx.cv <= 0.06 ? 1 : ctx.cv <= 0.12 ? 0.5 : 0;
  const descRegular =
    ctx.cv <= 0.06 ? "regular" : ctx.cv <= 0.12 ? "moderadamente irregular" : "irregular";

  /* Taquicardia supraventricular: rápida y regular */
  const dSvtHr = clamp01((hr - 145) / 35);
  const dSvtReg = 0.2 * regular * (hr >= 130 ? 1 : 0);
  s.SVT += dSvtHr + dSvtReg;
  if (dSvtHr > 0) {
    paso(
      "FC media",
      `${fmt(hr, 0)} lpm`,
      "FC sobre 145 lpm suma evidencia de taquicardia supraventricular (SVT), proporcional al exceso.",
      `SVT +${fmt(dSvtHr, 2)}`,
    );
  }
  if (dSvtReg > 0) {
    paso(
      "Regularidad del ritmo (CV de RR)",
      `${fmt(ctx.cv, 3)} (${descRegular})`,
      "FC ≥ 130 lpm con intervalos RR regulares refuerza la hipótesis de SVT.",
      `SVT +${fmt(dSvtReg, 2)}`,
    );
  }

  /* VT: complejos anchos y frecuencia elevada */
  if (ctx.anchoQRS != null) {
    const dVt = clamp01((ctx.anchoQRS - 115) / 50) * 2.2 * (hr >= 100 ? 1 : 0.3);
    s.VT += dVt;
    if (dVt > 0) {
      paso(
        "Ancho QRS medio",
        `${fmt(ctx.anchoQRS, 0)} ms`,
        `QRS sobre 115 ms suma evidencia de taquicardia ventricular (VT)${hr >= 100 ? "" : ", atenuada por FC bajo 100 lpm"}.`,
        `VT +${fmt(dVt, 2)}`,
      );
    }
  }

  /* Sinusal vs Otro según rango esperado para la edad */
  if (hr >= rango.lo && hr <= rango.hi) {
    const dSin = 0.8 * regular + 0.3 * clamp01((rango.hi - hr) / 50);
    s.Sinusal += dSin;
    paso(
      "FC vs. rango esperado (edad)",
      `${fmt(hr, 0)} lpm · rango ${rango.lo}–${rango.hi} lpm`,
      `FC dentro del rango esperado para «${rango.label}» suma a ritmo sinusal (más si el RR es regular y la FC se acerca al límite inferior).`,
      `Sinusal +${fmt(dSin, 2)}`,
    );
  } else if (hr < rango.lo) {
    s.Otro += 0.7;
    adv.push(
      `FC bajo el rango esperado para la edad indicada (${rango.lo}–${rango.hi} lpm): ${fmt(hr, 0)} lpm (bradicardia relativa).`,
    );
    paso(
      "FC vs. rango esperado (edad)",
      `${fmt(hr, 0)} lpm · rango ${rango.lo}–${rango.hi} lpm`,
      `FC bajo el rango esperado para «${rango.label}» (bradicardia relativa) suma a «Otro».`,
      `Otro +${fmt(0.7, 2)}`,
    );
  } else if (hr <= rango.hi + 15) {
    s.Otro += 0.5;
    adv.push(
      `FC sobre el rango esperado para la edad indicada (${rango.lo}–${rango.hi} lpm): ${fmt(hr, 0)} lpm.`,
    );
    paso(
      "FC vs. rango esperado (edad)",
      `${fmt(hr, 0)} lpm · rango ${rango.lo}–${rango.hi} lpm`,
      `FC levemente sobre el rango esperado para «${rango.label}» suma a «Otro».`,
      `Otro +${fmt(0.5, 2)}`,
    );
  } else {
    s.SVT += 0.5;
    adv.push(
      `FC sobre el rango esperado para la edad indicada (${rango.lo}–${rango.hi} lpm): ${fmt(hr, 0)} lpm (taquicardia).`,
    );
    paso(
      "FC vs. rango esperado (edad)",
      `${fmt(hr, 0)} lpm · rango ${rango.lo}–${rango.hi} lpm`,
      `FC muy sobre el rango esperado para «${rango.label}» (taquicardia) suma a SVT.`,
      `SVT +${fmt(0.5, 2)}`,
    );
  }

  /* QRS ancho (≥120 ms): la SVT se define por complejos estrechos; descuenta SVT */
  if (ctx.anchoQRS != null && ctx.anchoQRS >= 120) {
    s.SVT *= 0.35;
    paso(
      "Ancho QRS medio",
      `${fmt(ctx.anchoQRS, 0)} ms`,
      "QRS ancho (≥ 120 ms) descuenta SVT: la SVT se define por complejos estrechos.",
      "SVT ×0,35",
    );
  }

  /* Irregularidad marcada: fuera del alcance del modelo */
  if (ctx.cv > 0.12) {
    s.Otro += 0.7;
    adv.push(
      "Ritmo irregular (variabilidad de RR alta): los ritmos irregulares están fuera del alcance del modelo.",
    );
    paso(
      "Regularidad del ritmo (CV de RR)",
      `${fmt(ctx.cv, 3)} (irregular)`,
      "CV > 0,12 (ritmo irregular) suma a «Otro»: los ritmos irregulares están fuera del alcance del modelo.",
      `Otro +${fmt(0.7, 2)}`,
    );
  }
  if (ctx.n < 6) {
    adv.push(
      `Pocos latidos en el tramo (${ctx.n} intervalos RR): resultado poco confiable.`,
    );
    paso(
      "Latidos detectados",
      `${ctx.n} intervalos RR`,
      "Menos de 6 intervalos RR: resultado poco confiable (solo advertencia).",
      "Sin cambio de puntaje.",
    );
  }

  /* Espículas de marcapasos: evidencia fuerte de ritmo Paced */
  if (ctx.espiculas === true) {
    s.Paced += 2.0;
    s.Sinusal *= 0.4;
    s.SVT *= 0.5;
    s.VT *= 0.5;
    paso(
      "Espículas de marcapasos",
      "Detectadas antes de cada QRS",
      "Espículas de estimulación detectadas: evidencia fuerte de ritmo estimulado (Paced); atenúa el resto de las hipótesis.",
      `Paced +${fmt(2, 2)} · Sinusal ×0,40 · SVT ×0,50 · VT ×0,50`,
    );
  } else {
    paso(
      "Espículas de marcapasos",
      ctx.espiculas === false ? "No detectadas" : "No evaluable",
      "Sin evidencia de estimulación electrónica en el tramo.",
      "Sin cambio de puntaje.",
    );
  }

  let tot = 0;
  for (const k of CLASES) tot += s[k];
  const probs = {} as Record<Clase, number>;
  for (const k of CLASES) probs[k] = s[k] / tot;
  paso(
    "Normalización",
    `Puntaje total ${fmt(tot, 2)}`,
    "Probabilidad de cada clase = puntaje bruto ÷ suma de los puntajes brutos.",
    "—",
  );
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

  return { clase, probs, puntajes: s, pasos, advertencias: adv };
}
