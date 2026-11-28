"use client";

/* ============================================================
   Navegador interactivo del pipeline PDS en seis etapas.
   Estética editorial-clínica sobre fondo blanco: azul único
   (#2b52e8), serif de display para títulos y mono para todo
   el texto técnico (kickers, descripciones, chips, asides).
   Sin librerías de gráficos: los seis visuales son SVG
   deterministas construidos desde ./signal.
   Demo académica; no es un dispositivo médico.
   ============================================================ */

import { useEffect, useRef, useState, type ComponentType } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  HeartPulse,
  Pause,
  Play,
} from "lucide-react";
import {
  AMPLITUD_R,
  buildPath,
  CLEAN,
  DCT,
  DIAGNOSTICO,
  FC_LPM,
  INTERVALOS_RR,
  LATIDOS,
  mapPoint,
  muestra,
  PROBABILIDADES,
  R_PEAKS,
  RAW,
  REGISTRO,
  RR_MS,
  type Box,
} from "./signal";

/* Paleta fija del diseño: azul del sistema + grises de trazo. */
const PDS = "#2b52e8";
const PDS_DARK = "#1d3ab5";
const GRIS = "#94a3b8";
const NEUTRO = "#d4d4d8";
const TINTA = "#404040";

/** Área estándar de trazado dentro del viewBox 640×312. */
const LIENZO: Box = { x: 16, y: 28, w: 608, h: 240 };
const EJE_Y = 268;
const PASO_MS = 3400; // avance automático de «Recorrer»

function VisualSvg({
  label,
  viewBox = "0 0 640 312",
  children,
}: {
  label: string;
  /** recorte del área útil: elimina el margen muerto del 640×312 */
  viewBox?: string;
  children: React.ReactNode;
}) {
  return (
    <svg
      viewBox={viewBox}
      role="img"
      aria-label={label}
      className="h-full w-full"
    >
      {children}
    </svg>
  );
}

/** Eje de tiempo del visual de adquisición (0 s → 10 s). */
function EjeTiempo() {
  return (
    <g aria-hidden="true">
      <line x1={16} y1={EJE_Y} x2={624} y2={EJE_Y} stroke={NEUTRO} strokeWidth={1} />
      {[0, 5, 10].map((t) => {
        const x = 16 + (t / 10) * 608;
        return (
          <g key={t}>
            <line x1={x} y1={EJE_Y} x2={x} y2={EJE_Y + 5} stroke={NEUTRO} />
            <text
              x={x}
              y={286}
              textAnchor={t === 0 ? "start" : t === 10 ? "end" : "middle"}
              className="font-mono"
              fontSize={11}
              fill={GRIS}
            >
              {t} s
            </text>
          </g>
        );
      })}
    </g>
  );
}

/** Rótulo técnico pill negro con línea guía punteada hacia la señal. */
function Callout({
  x,
  yCaja,
  yLinea,
  texto,
  ancho,
}: {
  x: number;
  yCaja: number;
  yLinea: number;
  texto: string;
  ancho: number;
}) {
  return (
    <g aria-hidden="true">
      <line
        x1={x}
        y1={yLinea}
        x2={x}
        y2={yCaja < yLinea ? yCaja + 22 : yCaja}
        stroke={TINTA}
        strokeWidth={1}
        strokeDasharray="3 4"
      />
      <rect x={x - ancho / 2} y={yCaja} width={ancho} height={22} rx={11} fill={TINTA} />
      <text
        x={x}
        y={yCaja + 14.5}
        textAnchor="middle"
        className="font-mono"
        fontSize={10.5}
        letterSpacing="0.02em"
        fill="#ffffff"
      >
        {texto}
      </text>
    </g>
  );
}

/* ---------- 01 · Adquisición ---------- */

/** Guía punteada horizontal en un nivel de amplitud v (mV) dentro del Box. */
function GuiaNivel({
  caja,
  v,
  etiqueta,
  etiquetaX,
  etiquetaDebajo,
}: {
  caja: Box;
  v: number;
  etiqueta?: string;
  /** x alternativa para la etiqueta (p. ej. el margen izquierdo del gráfico) */
  etiquetaX?: number;
  /** dibuja la etiqueta bajo la línea en vez de sobre ella */
  etiquetaDebajo?: boolean;
}) {
  const [, y] = mapPoint({ t: 0, v }, caja);
  const yTxt = y + (etiquetaDebajo ? 11 : -4);
  return (
    <g aria-hidden="true">
      <line
        x1={caja.x}
        y1={y}
        x2={caja.x + caja.w}
        y2={y}
        stroke={GRIS}
        strokeOpacity={0.45}
        strokeWidth={1}
        strokeDasharray="1.5 4"
        strokeLinecap="round"
      />
      {etiqueta && (
        <text
          x={etiquetaX ?? caja.x + 3}
          y={yTxt}
          className="font-mono"
          fontSize={8.5}
          fill={GRIS}
          fillOpacity={0.85}
          stroke="#ffffff"
          strokeWidth={3}
          strokeOpacity={0.92}
          style={{ paintOrder: "stroke" }}
        >
          {etiqueta}
        </text>
      )}
    </g>
  );
}

function VisualAdquisicion() {
  const p1 = mapPoint({ t: 1.85, v: muestra(1.85, true) }, LIENZO);
  const p2 = mapPoint({ t: 7.3, v: muestra(7.3, true) }, LIENZO);
  return (
    <VisualSvg label={`Trazo ECG crudo de 10 segundos con ruido de red de 50 Hz y deriva de la línea base marcados; ${LATIDOS} latidos en total`} viewBox="0 28 640 266">
      <EjeTiempo />
      <GuiaNivel caja={LIENZO} v={1} etiqueta="1 mV" />
      <GuiaNivel caja={LIENZO} v={0} etiqueta="0 mV" />
      <path d={buildPath(RAW, LIENZO)} fill="none" stroke={GRIS} strokeWidth={1.4} />
      <Callout x={p1[0]} yCaja={38} yLinea={p1[1] - 8} texto="Ruido de red · 50 Hz" ancho={150} />
      <Callout x={p2[0]} yCaja={226} yLinea={p2[1] + 8} texto="Deriva línea base" ancho={128} />
    </VisualSvg>
  );
}

/* ---------- 02 · Preprocesado: ANTES / DESPUÉS apilados ---------- */

function VisualPreprocesado() {
  const bandaArriba: Box = { x: 118, y: 30, w: 506, h: 112 };
  const bandaAbajo: Box = { x: 118, y: 188, w: 506, h: 112 };
  return (
    <VisualSvg label="Comparación antes y después del filtrado: señal cruda con ruido arriba y señal limpia en azul abajo" viewBox="0 22 640 284">
      <text x={40} y={80} className="font-mono" fontSize={11} fontWeight={700} fill={TINTA}>
        ANTES
      </text>
      <text x={40} y={96} className="font-mono" fontSize={9.5} fill={GRIS}>
        señal cruda
      </text>
      <GuiaNivel caja={bandaArriba} v={0} etiqueta="0 mV" etiquetaX={40} />
      <path d={buildPath(RAW, bandaArriba)} fill="none" stroke={GRIS} strokeWidth={1.2} />
      <line x1={320} y1={146} x2={320} y2={184} stroke={NEUTRO} strokeDasharray="3 4" />
      <text x={40} y={238} className="font-mono" fontSize={11} fontWeight={700} fill={TINTA}>
        DESPUÉS
      </text>
      <text x={40} y={254} className="font-mono" fontSize={9.5} fill={GRIS}>
        filtrada
      </text>
      <GuiaNivel caja={bandaAbajo} v={0} etiqueta="0 mV" etiquetaX={40} etiquetaDebajo />
      <path d={buildPath(CLEAN, bandaAbajo)} fill="none" stroke={PDS} strokeWidth={1.3} />
    </VisualSvg>
  );
}

/* ---------- 03 · Detección: fila de puntos + guías + corchetes RR ---------- */

function VisualDeteccion() {
  const cajaSenal: Box = { x: 56, y: 112, w: 528, h: 172 };
  const picos = R_PEAKS.map((t) => mapPoint({ t, v: AMPLITUD_R }, cajaSenal));
  const filaY = 64; // fila horizontal de puntos
  const corchetes: Array<[number, number, number]> = [
    [4, 5, 34],
    [5, 6, 52],
  ];
  return (
    <VisualSvg label={`Trazo limpio con los ${LATIDOS} picos R marcados con puntos sobre una fila guía, líneas punteadas hacia cada latido y corchetes con intervalos RR en milisegundos`} viewBox="0 20 640 286">
      {/* guías verticales desde la fila de puntos hasta la base */}
      {picos.map(([cx]) => (
        <line
          key={`g${cx}`}
          x1={cx}
          y1={filaY + 6}
          x2={cx}
          y2={300}
          stroke={PDS}
          strokeOpacity={0.25}
          strokeDasharray="2 4"
        />
      ))}
      {/* fila guía horizontal */}
      <line
        x1={picos[0][0]}
        y1={filaY}
        x2={picos[picos.length - 1][0]}
        y2={filaY}
        stroke={NEUTRO}
        strokeDasharray="2 4"
      />
      {/* corchetes RR escalonados sobre la fila de puntos */}
      {corchetes.map(([a, b, y]) => (
        <g key={`c${a}`}>
          <path
            d={`M ${picos[a][0]} ${y + 8} L ${picos[a][0]} ${y} L ${picos[b][0]} ${y} L ${picos[b][0]} ${y + 8}`}
            fill="none"
            stroke={TINTA}
            strokeWidth={1}
          />
          <text
            x={(picos[a][0] + picos[b][0]) / 2}
            y={y - 4}
            textAnchor="middle"
            className="font-mono"
            fontSize={9}
            fill={TINTA}
          >
            RR {RR_MS[a]} ms
          </text>
        </g>
      ))}
      {/* trazo filtrado */}
      <GuiaNivel caja={cajaSenal} v={AMPLITUD_R * 0.6} etiqueta="umbral adaptativo" />
      <GuiaNivel caja={cajaSenal} v={0} />
      <path d={buildPath(CLEAN, cajaSenal)} fill="none" stroke={PDS} strokeWidth={1.4} />
      {/* puntos sobre cada pico R */}
      {picos.map(([cx]) => (
        <circle key={`p${cx}`} cx={cx} cy={filaY} r={3.5} fill={PDS} />
      ))}
    </VisualSvg>
  );
}

/* ---------- 04 · Características: ventana 512 ms + espectro DCT ---------- */

function VisualCaracteristicas() {
  const cajaSenal: Box = { x: 24, y: 52, w: 372, h: 240 };
  const tR = R_PEAKS[6];
  const xIni = mapPoint({ t: tR - 0.25, v: 0 }, cajaSenal)[0];
  const xFin = mapPoint({ t: tR + 0.262, v: 0 }, cajaSenal)[0];
  const baseY = 184;
  return (
    <VisualSvg label="Trazo con una ventana fija de 512 ms resaltada alrededor de un latido y, a la derecha, el espectro de 24 coeficientes DCT como barras" viewBox="0 26 640 270">
      <text x={(xIni + xFin) / 2} y={40} textAnchor="middle" className="font-mono" fontSize={10} fill={PDS}>
        ventana fija · 512 ms
      </text>
      <text x={516} y={40} textAnchor="middle" className="font-mono" fontSize={10} fill={GRIS}>
        coef. DCT (24) → F22
      </text>
      <GuiaNivel caja={cajaSenal} v={0} />
      <path d={buildPath(CLEAN, cajaSenal)} fill="none" stroke={PDS} strokeWidth={1.3} />
      <rect
        x={xIni}
        y={52}
        width={xFin - xIni}
        height={240}
        fill={PDS}
        fillOpacity={0.05}
        stroke={PDS}
        strokeOpacity={0.55}
        strokeDasharray="4 4"
        strokeWidth={1.2}
      />
      <line x1={404} y1={baseY} x2={628} y2={baseY} stroke={NEUTRO} aria-hidden="true" />
      {DCT.map((c, i) => {
        const h = Math.abs(c) * 140;
        return (
          <rect
            key={i}
            x={416 + i * 9}
            y={c > 0 ? baseY - h : baseY}
            width={7}
            height={h}
            rx={1.5}
            fill={c > 0 ? PDS : GRIS}
          />
        );
      })}
    </VisualSvg>
  );
}

/* ---------- 05 · Clasificación (barras HTML animadas) ---------- */

function VisualClasificacion() {
  const [montado, setMontado] = useState(false);
  useEffect(() => {
    const id = setTimeout(() => setMontado(true), 80);
    return () => clearTimeout(id);
  }, []);
  const resumen = PROBABILIDADES.map((r) => `${r.clase} ${Math.round(r.p * 100)} %`).join(", ");
  return (
    <div
      role="img"
      aria-label={`Barras de probabilidad por clase de ritmo: ${resumen}`}
      className="flex h-full flex-col justify-center gap-4 pr-1"
    >
      {PROBABILIDADES.map((r, i) => (
        <div key={r.clase} className="flex items-center gap-4">
          <span
            className={`w-[110px] shrink-0 font-mono text-[12px] ${
              i === 0 ? "font-bold text-pds" : "text-neutral-500"
            }`}
          >
            {r.clase}
          </span>
          <div className="h-6 min-w-0 flex-1 overflow-hidden rounded-md bg-neutral-100">
            <div
              className={`h-full rounded-md motion-reduce:transition-none ${
                i === 0 ? "bg-pds" : "bg-slate-300"
              } transition-[width] duration-700 ease-out`}
              style={{
                width: montado ? `${r.p * 100}%` : "0%",
                transitionDelay: `${80 + i * 70}ms`,
              }}
            />
          </div>
          <span
            className={`w-11 shrink-0 text-right font-mono text-[12px] tabular-nums ${
              i === 0 ? "font-bold text-neutral-800" : "text-neutral-500"
            }`}
          >
            {Math.round(r.p * 100)} %
          </span>
        </div>
      ))}
    </div>
  );
}

/* ---------- 06 · Diagnóstico: medidor semicircular ---------- */

function VisualDiagnostico() {
  const cx = 320;
  const cy = 284;
  const r = 192;
  const pct = Math.round(DIAGNOSTICO.certeza * 100);
  const arco = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const ang = Math.PI * (1 - DIAGNOSTICO.certeza);
  const aguja = r - 22;
  return (
    <VisualSvg label={`Medidor semicircular de certeza al ${pct} % a favor del ritmo sugerido: ${DIAGNOSTICO.ritmo}`} viewBox="0 56 640 256">
      <path d={arco} fill="none" stroke="#e8ecf4" strokeWidth={22} strokeLinecap="round" pathLength={100} />
      <path
        d={arco}
        fill="none"
        stroke={PDS}
        strokeWidth={22}
        strokeLinecap="round"
        pathLength={100}
        strokeDasharray={`${DIAGNOSTICO.certeza * 100} 100`}
      />
      <text x={cx - r} y={cy + 22} textAnchor="middle" className="font-mono" fontSize={9} fill={GRIS}>
        0
      </text>
      <text x={cx} y={cy - r - 26} textAnchor="middle" className="font-mono" fontSize={9} fill={GRIS}>
        50
      </text>
      <text x={cx + r} y={cy + 22} textAnchor="middle" className="font-mono" fontSize={9} fill={GRIS}>
        100
      </text>
      <line
        x1={cx}
        y1={cy}
        x2={cx + aguja * Math.cos(ang)}
        y2={cy - aguja * Math.sin(ang)}
        stroke="#171717"
        strokeWidth={3.5}
        strokeLinecap="round"
      />
      <circle cx={cx} cy={cy} r={7} fill="#171717" />
      <text x={cx} y={cy - 66} textAnchor="middle" className="font-mono text-[44px] font-bold" fill="#171717">
        {pct} %
      </text>
      <text x={cx} y={cy - 42} textAnchor="middle" className="font-mono" fontSize={11} fill={GRIS}>
        certeza
      </text>
    </VisualSvg>
  );
}

/* ---------- definición de las seis etapas ---------- */

interface ChipEtapa {
  texto: string;
  /** chip clave: píldora negra con el dato determinante */
  clave?: boolean;
}

interface EtapaDef {
  corto: string;
  kicker: string;
  titulo: string;
  descripcion: string;
  entrada: string[];
  salida: string[];
  chips: ChipEtapa[];
  visual: ComponentType;
}

const pct = (p: number) => `${Math.round(p * 100)} %`;
const brierTxt = `Brier ${DIAGNOSTICO.brier.toFixed(3).replace(".", ",")}`;

const ETAPAS: EtapaDef[] = [
  {
    corto: "Señal cruda",
    kicker: "Adquisición",
    titulo: "La señal, tal como llega",
    descripcion:
      "Todo empieza con el registro tal como sale del equipo: 10 segundos de ECG pediátrico con el ruido de la sala encima. Antes de medir nada, hay que saber qué llegó.",
    entrada: ["Registro WFDB del corpus ZZU pECG"],
    salida: ["Serie temporal de 10 s a 500 Hz", "Ruido y deriva identificados a simple vista"],
    chips: [
      { texto: `${REGISTRO.formato} (${REGISTRO.corpus}) · ${REGISTRO.duracion} · ${REGISTRO.muestreo}`, clave: true },
      { texto: `${LATIDOS} latidos en 10 s` },
      { texto: `canal ${REGISTRO.canal}` },
    ],
    visual: VisualAdquisicion,
  },
  {
    corto: "Preprocesado",
    kicker: "Preprocesado",
    titulo: "Filtrar sin deformar",
    descripcion:
      "La señal cruza un FIR paso-alto (0,5 Hz) y paso-bajo (40 Hz) más un IIR notch de 50 Hz. La regla del proyecto: limpiar sin tocar la morfología clínica — QRS, onda P y espículas de marcapasos quedan intactas.",
    entrada: ["Señal cruda de la etapa 01"],
    salida: ["Señal limpia, lista para detectar latidos", "Distorsión en QRS de referencia < 5 %"],
    chips: [
      { texto: "FIR paso-alto 0,5 Hz" },
      { texto: "FIR paso-bajo 40 Hz" },
      { texto: "IIR notch 50 Hz" },
      { texto: "distorsión QRS < 5 %", clave: true },
    ],
    visual: VisualPreprocesado,
  },
  {
    corto: "Picos R",
    kicker: "Detección",
    titulo: "Encontrar cada latido",
    descripcion: `Sobre la señal limpia, un umbral adaptativo con período refractario marca cada pico R. Los intervalos RR entre latidos consecutivos dan la frecuencia cardiaca: ≈ ${FC_LPM} lpm, coherente con un niño.`,
    entrada: ["Señal filtrada de la etapa 02"],
    salida: ["Posición exacta de cada pico R", `Intervalos RR → FC ≈ ${FC_LPM} lpm`],
    chips: [
      { texto: `FC ≈ ${FC_LPM} lpm`, clave: true },
      { texto: `${INTERVALOS_RR} intervalos RR` },
      { texto: "umbral adaptativo + refractario" },
    ],
    visual: VisualDeteccion,
  },
  {
    corto: "Características",
    kicker: "Características",
    titulo: "Convertir el trazo en números",
    descripcion:
      "Cada latido se recorta con una ventana fija y se describe numéricamente: anchos y amplitudes de la morfología más los coeficientes DCT del espectro. El resultado es el vector F22, la huella dactilar del latido.",
    entrada: ["Latidos segmentados en ventana fija"],
    salida: ["Vector de características F22 por latido"],
    chips: [
      { texto: "Ancho QRS · 78 ms" },
      { texto: `Amplitud R · ${AMPLITUD_R.toFixed(2).replace(".", ",")} mV` },
      { texto: "Intervalo QT · 318 ms" },
      { texto: "Energía 0,5-40 Hz · 92,4 %" },
      { texto: `DCT × ${DCT.length} → vector F22`, clave: true },
    ],
    visual: VisualCaracteristicas,
  },
  {
    corto: "Clasificación",
    kicker: "Clasificación",
    titulo: "Votar entre clases de ritmo",
    descripcion: `El vector F22 alimenta el clasificador entrenado (Random Forest / SVM), que compara el latido contra las clases del dataset y devuelve probabilidades calibradas — no una etiqueta seca. En este caso domina ${PROBABILIDADES[0].clase} con ${pct(PROBABILIDADES[0].p)}.`,
    entrada: ["Vector F22 de la etapa 04"],
    salida: ["Probabilidad por clase de ritmo", `Clase dominante: ${PROBABILIDADES[0].clase} · ${pct(PROBABILIDADES[0].p)}`],
    chips: [
      { texto: `clase dominante: ${PROBABILIDADES[0].clase} · ${pct(PROBABILIDADES[0].p)}`, clave: true },
      { texto: "salida probabilística, no etiqueta seca" },
    ],
    visual: VisualClasificacion,
  },
  {
    corto: "Diagnóstico",
    kicker: "Diagnóstico",
    titulo: "Del número al diagnóstico",
    descripcion:
      "La clase más probable se convierte en el ritmo sugerido, siempre acompañado de su porcentaje de certeza. Si la certeza fuese baja, el sistema lo declararía — prefiere admitir la duda antes que adivinar.",
    entrada: ["Distribución de probabilidades de la etapa 05"],
    salida: [`Ritmo sugerido: ${DIAGNOSTICO.ritmo}`, `Certeza ${pct(DIAGNOSTICO.certeza)} · ${brierTxt}`],
    chips: [
      { texto: `ritmo sugerido: ${DIAGNOSTICO.ritmo} (Paced)`, clave: true },
      { texto: `${brierTxt} · calibrado` },
    ],
    visual: VisualDiagnostico,
  },
];

const KPIS = [
  { valor: "< 5 %", etiqueta: "distorsión en QRS de referencia" },
  { valor: "ANOVA / Fisher", etiqueta: "separabilidad inter-clase" },
  { valor: "Brier 0,037", etiqueta: "calibración probabilística" },
  { valor: "≥ 85 %", etiqueta: "sensibilidad y especificidad" },
];

/* ============================================================
   Sección completa: cabecera, barra KPI y navegador de etapas.
   ============================================================ */

export function PipelineSection() {
  const [etapa, setEtapa] = useState(0);
  const [recorriendo, setRecorriendo] = useState(false);
  const railRef = useRef<HTMLOListElement>(null);

  /* «Recorrer»: avanza en bucle cada 3,4 s hasta pausar. */
  useEffect(() => {
    if (!recorriendo) return;
    const id = setInterval(
      () => setEtapa((e) => (e + 1) % ETAPAS.length),
      PASO_MS,
    );
    return () => clearInterval(id);
  }, [recorriendo]);

  /* Mantiene visible la pastilla activa cuando el rail se desplaza. */
  useEffect(() => {
    const activo = railRef.current?.children[etapa];
    if (!(activo instanceof HTMLElement) || !railRef.current) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    activo.scrollIntoView({
      behavior: reduce ? "auto" : "smooth",
      block: "nearest",
      inline: "center",
    });
  }, [etapa]);

  const actual = ETAPAS[etapa];
  const Visual = actual.visual;
  const num = (i: number) => String(i + 1).padStart(2, "0");

  return (
    <section id="pipeline" className="scroll-mt-16 bg-white">
      <div className="mx-auto max-w-[1680px] px-6 pb-20 pt-16 lg:px-8">
        {/* Cabecera: ancho de lectura; KPI y demo van a todo el ancho */}
        <div className="mx-auto max-w-7xl">
        <span className="inline-flex h-7 items-center gap-2 rounded-full bg-neutral-100 pl-1.5 pr-3.5">
          <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-neutral-950">
            <HeartPulse
              className="h-2.5 w-2.5 text-white"
              strokeWidth={3}
              aria-hidden="true"
            />
          </span>
          <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-neutral-800">
            Pipeline PDS
          </span>
        </span>
        <div className="mt-6 flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <h2 className="font-display text-[38px] leading-[1.04] tracking-[0.005em] text-neutral-900 sm:text-[44px]">
            De la señal al diagnóstico,
            <br />
            <em className="italic text-pds-dark">en seis etapas</em>
          </h2>
          <p className="max-w-[440px] font-mono text-[13px] leading-relaxed text-neutral-700">
            El mismo flujo que ejecuta el software del proyecto, etapa por
            etapa: qué entra, qué se procesa y qué sale. Pulse «Recorrer» para
            verlo en secuencia automática.
          </p>
        </div>
        </div>

        {/* Barra KPI: banda reglada con numerales serif, sin tarjetas sueltas */}
        <div className="mt-8 overflow-hidden rounded-2xl border border-neutral-200/80 bg-white">
          <div className="grid grid-cols-2 lg:grid-cols-4">
            {KPIS.map((k, i) => (
              <div
                key={k.valor}
                className={`border-neutral-200/80 p-4 sm:p-5 ${
                  i % 2 === 1 ? "border-l" : ""
                } ${i >= 2 ? "border-t lg:border-t-0" : ""} ${
                  i > 0 ? "lg:border-l" : ""
                }`}
              >
                <p className="font-display text-[23px] leading-none tracking-[0.005em] text-pds-dark sm:text-[25px]">
                  {k.valor}
                </p>
                <p className="mt-2.5 font-mono text-[10.5px] leading-snug text-neutral-500">
                  {k.etiqueta}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Navegador de etapas */}
        <div className="mt-10 overflow-hidden rounded-3xl border border-neutral-200/80 bg-white shadow-[0_24px_60px_-32px_rgba(15,23,42,0.25)]">
          {/* Barra superior */}
          <div className="flex items-center justify-between gap-4 bg-pds px-5 py-3.5 sm:px-6">
            <span className="whitespace-nowrap font-mono text-[10.5px] font-semibold uppercase tracking-[0.2em] text-white">
              Pipeline PDS<span className="hidden sm:inline"> · Demo interactiva</span>
            </span>
            <span className="whitespace-nowrap font-mono text-[12px] tabular-nums text-white/85">
              <span className="font-bold text-white">{num(etapa)}</span> /{" "}
              {num(ETAPAS.length - 1)}
            </span>
          </div>

          {/* Rail de etapas */}
          <div className="px-4 pt-5 sm:px-6">
            <ol
              ref={railRef}
              className="ecg-scroll flex gap-2 overflow-x-auto pb-2 [scrollbar-width:thin]"
            >
              {ETAPAS.map((e, i) => {
                const activo = i === etapa;
                return (
                  <li key={e.corto} className="shrink-0">
                    <button
                      type="button"
                      onClick={() => setEtapa(i)}
                      aria-current={activo ? "step" : undefined}
                      className={`inline-flex h-11 items-center gap-2 whitespace-nowrap rounded-full border px-4 font-mono text-[12px] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pds ${
                        activo
                          ? "border-transparent bg-pds font-bold text-white shadow-[0_10px_24px_-10px_rgba(43,82,232,0.65)]"
                          : "border-neutral-200/90 bg-white text-neutral-600 hover:border-pds/50 hover:text-pds"
                      }`}
                    >
                      <span className="tabular-nums opacity-75">{num(i)}</span>
                      {e.corto}
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>

          {/* Contenido de la etapa activa */}
          <div aria-live="polite" className="px-4 py-6 sm:px-6 sm:py-7">
            <div
              key={etapa}
              className="min-h-[872px] animate-in fade-in slide-in-from-bottom-2 [animation-duration:320ms] motion-reduce:animate-none lg:min-h-[704px]"
            >
              {/* Cabecera: numeral serif + kicker + título */}
              <div className="flex items-start gap-4 sm:gap-5">
                <span
                  aria-hidden="true"
                  className="mt-1 font-display text-[48px] leading-[0.8] text-pds sm:text-[60px]"
                >
                  {num(etapa)}
                </span>
                <div className="border-l border-neutral-200/80 pl-4 sm:pl-5">
                  <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-pds">
                    {actual.kicker}
                  </p>
                  <h3 className="mt-2 font-display text-[26px] leading-[1.05] tracking-[0.005em] text-neutral-900 sm:text-[30px]">
                    {actual.titulo}
                  </h3>
                </div>
              </div>
              {/* alto fijo: reserva las 3 líneas máximas para que el flujo
                  ENTRADA → PROCESO → SALIDA arranque siempre a la misma altura */}
              <p className="mt-3 min-h-[64px] max-w-[680px] font-mono text-[13px] leading-relaxed text-neutral-700">
                {actual.descripcion}
              </p>

              {/* Flujo ENTRADA → PROCESO → SALIDA */}
              <div className="mt-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:gap-3">
                {/* ENTRADA */}
                <aside className="rounded-2xl bg-pds-soft p-4 sm:p-5 lg:w-[196px] lg:shrink-0">
                  <h4 className="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-pds-dark">
                    <span
                      className="h-1.5 w-1.5 rounded-full bg-pds"
                      aria-hidden="true"
                    />
                    Entrada
                  </h4>
                  <ul className="mt-3 flex flex-col gap-2.5">
                    {actual.entrada.map((it) => (
                      <li
                        key={it}
                        className="flex items-start gap-2 font-mono text-[12px] leading-relaxed text-neutral-700"
                      >
                        <span
                          className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-pds"
                          aria-hidden="true"
                        />
                        {it}
                      </li>
                    ))}
                  </ul>
                </aside>

                <span
                  aria-hidden="true"
                  className="hidden h-7 w-7 shrink-0 items-center justify-center rounded-full border border-pds/35 text-pds lg:mt-[14px] lg:flex"
                >
                  <ArrowRight className="h-3.5 w-3.5" />
                </span>

                {/* PROCESO */}
                <div className="min-w-0 flex-1 rounded-2xl border border-neutral-200/80 bg-white p-4 sm:p-5">
                  <h4 className="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-neutral-900">
                    <span
                      className="h-1.5 w-1.5 rounded-full bg-neutral-950"
                      aria-hidden="true"
                    />
                    Proceso
                  </h4>
                  <div className="mt-3 h-[220px] sm:h-[320px] lg:h-[370px]">
                    <Visual />
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {actual.chips.map((c) => (
                      <span
                        key={c.texto}
                        className={`rounded-full px-2.5 py-1 font-mono text-[10.5px] tracking-[0.02em] ${
                          c.clave
                            ? "bg-neutral-950 font-bold text-white"
                            : "bg-neutral-100 text-neutral-600"
                        }`}
                      >
                        {c.texto}
                      </span>
                    ))}
                  </div>
                </div>

                <span
                  aria-hidden="true"
                  className="hidden h-7 w-7 shrink-0 items-center justify-center rounded-full border border-pds/35 text-pds lg:mt-[14px] lg:flex"
                >
                  <ArrowRight className="h-3.5 w-3.5" />
                </span>

                {/* SALIDA */}
                <aside className="rounded-2xl border border-pds/40 bg-white p-4 sm:p-5 lg:w-[196px] lg:shrink-0">
                  <h4 className="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-pds-dark">
                    <span
                      className="h-1.5 w-1.5 rounded-full bg-pds"
                      aria-hidden="true"
                    />
                    Salida
                  </h4>
                  <ul className="mt-3 flex flex-col gap-2.5">
                    {actual.salida.map((it) => (
                      <li
                        key={it}
                        className="flex items-start gap-2 font-mono text-[12px] leading-relaxed text-neutral-700"
                      >
                        <Check
                          className="mt-[3px] h-3.5 w-3.5 shrink-0 text-pds"
                          strokeWidth={2.5}
                          aria-hidden="true"
                        />
                        {it}
                      </li>
                    ))}
                  </ul>
                </aside>
              </div>
            </div>
          </div>

          {/* Navegación inferior: flecha · progreso · recorrer + flecha */}
          <div className="flex items-center gap-4 border-t border-neutral-200/80 px-4 py-4 sm:px-6">
            <button
              type="button"
              onClick={() => setEtapa(Math.max(0, etapa - 1))}
              disabled={etapa === 0}
              aria-label="Etapa anterior"
              className="flex h-11 w-11 items-center justify-center rounded-full border border-neutral-200/90 text-neutral-600 transition-colors hover:border-pds/60 hover:text-pds focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pds disabled:opacity-40 disabled:hover:border-neutral-200/90 disabled:hover:text-neutral-600"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            </button>

            {/* progreso de la secuencia; responde al modo «Recorrer» */}
            <div
              className="relative h-1 min-w-0 flex-1 overflow-hidden rounded-full bg-neutral-100"
              aria-hidden="true"
            >
              <div
                className="h-full rounded-full bg-pds transition-[width] duration-500 ease-out"
                style={{ width: `${((etapa + 1) / ETAPAS.length) * 100}%` }}
              />
            </div>
            <span className="hidden whitespace-nowrap font-mono text-[10px] uppercase tracking-[0.16em] text-neutral-400 lg:block">
              {actual.corto}
            </span>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setRecorriendo((r) => !r)}
                aria-pressed={recorriendo}
                className={`inline-flex h-11 items-center gap-2 rounded-full px-5 font-mono text-[11px] font-bold uppercase tracking-[0.16em] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pds ${
                  recorriendo
                    ? "bg-pds text-white"
                    : "bg-pds-soft text-pds-dark hover:bg-pds/15"
                }`}
              >
                {recorriendo ? (
                  <Pause className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <Play className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                {recorriendo ? "Pausar" : "Recorrer"}
              </button>
              <button
                type="button"
                onClick={() => setEtapa(Math.min(ETAPAS.length - 1, etapa + 1))}
                disabled={etapa === ETAPAS.length - 1}
                aria-label="Etapa siguiente"
                className="flex h-11 w-11 items-center justify-center rounded-full bg-pds text-white transition-colors hover:bg-pds-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pds disabled:opacity-40"
              >
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
