"use client";

/* ============================================================
   stage-visuals.tsx — Visualización SVG/HTML de cada etapa del
   pipeline PDS. Un componente por etapa, todos deterministas.
   ============================================================ */

import { useEffect, useState } from "react";
import {
  buildPath,
  mapPoint,
  R_PEAKS,
  RR_MS,
  FC_LPM,
  NUM_LATIDOS,
  MARCA_RUIDO,
  MARCA_DERIVA,
  CLEAN,
  RAW,
  DCT,
  MORFOLOGIA,
  ESPECTRO,
  PROBABILIDADES,
  DIAGNOSTICO,
  REGISTRO,
  type Box,
  type Point,
} from "./signal";

/* ---------- piezas compartidas ---------- */

function Chip({
  children,
  dark = false,
}: {
  children: React.ReactNode;
  dark?: boolean;
}) {
  return (
    <span
      className={
        dark
          ? "inline-flex items-center rounded-full bg-neutral-900 px-2.5 py-1 font-mono text-[10.5px] font-semibold text-white"
          : "inline-flex items-center rounded-full border border-neutral-200 bg-white px-2.5 py-1 font-mono text-[10.5px] font-medium text-neutral-600"
      }
    >
      {children}
    </span>
  );
}

function Fig({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <figure
      className="flex h-full w-full flex-col gap-3"
      role="img"
      aria-label={label}
    >
      {children}
    </figure>
  );
}

function GridLines({ box }: { box: Box }) {
  return (
    <g aria-hidden="true">
      {[0.25, 0.5, 0.75].map((f) => {
        const y = box.yTop + box.h * f;
        return (
          <line
            key={f}
            x1={box.x}
            y1={y}
            x2={box.x + box.w}
            y2={y}
            stroke="#e8eef8"
            strokeWidth="1"
          />
        );
      })}
    </g>
  );
}

/* ============================================================
   Etapa 01 — Señal cruda
   ============================================================ */

const BOX_RAW: Box = { x: 20, w: 600, yTop: 16, h: 288 };
const RAW_PATH_MAIN = buildPath(RAW, BOX_RAW);

function Callout({
  at,
  text,
  side,
}: {
  at: Point;
  text: string;
  side: "left" | "right";
}) {
  const [ax, ay] = mapPoint(at, BOX_RAW);
  const dir = side === "left" ? -1 : 1;
  const lx = ax + dir * 64;
  const ly = Math.max(30, ay - 74);
  return (
    <g aria-hidden="true">
      <line
        x1={ax}
        y1={ay}
        x2={lx}
        y2={ly}
        stroke="#94a3b8"
        strokeWidth="1.2"
        strokeDasharray="3 4"
      />
      <circle cx={ax} cy={ay} r="4" fill="#0f172a" />
      <g transform={`translate(${lx - 58}, ${ly - 12})`}>
        <rect width="116" height="24" rx="12" fill="#0f172a" />
        <text
          x="58"
          y="16"
          textAnchor="middle"
          fontSize="10"
          fill="#ffffff"
          className="font-mono"
        >
          {text}
        </text>
      </g>
    </g>
  );
}

export function VisualSenalCruda() {
  return (
    <Fig label="Señal ECG cruda de 10 segundos con ruido de red de 50 Hz y deriva de línea base">
      <svg
        viewBox="0 0 640 312"
        className="h-full w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <GridLines box={BOX_RAW} />
        <path
          d={RAW_PATH_MAIN}
          fill="none"
          stroke="#94a3b8"
          strokeWidth="1.4"
          strokeLinejoin="round"
        />
        <Callout at={MARCA_RUIDO} text="Ruido de red · 50 Hz" side="right" />
        <Callout at={MARCA_DERIVA} text="Deriva línea base" side="left" />
        {/* eje de tiempo */}
        <line
          x1={BOX_RAW.x}
          y1={BOX_RAW.yTop + BOX_RAW.h + 6}
          x2={BOX_RAW.x + BOX_RAW.w}
          y2={BOX_RAW.yTop + BOX_RAW.h + 6}
          stroke="#cbd5e1"
          strokeWidth="1"
        />
        <text
          x={BOX_RAW.x}
          y={BOX_RAW.yTop + BOX_RAW.h + 20}
          fontSize="10"
          fill="#94a3b8"
          className="font-mono"
        >
          0 s
        </text>
        <text
          x={BOX_RAW.x + BOX_RAW.w}
          y={BOX_RAW.yTop + BOX_RAW.h + 20}
          textAnchor="end"
          fontSize="10"
          fill="#94a3b8"
          className="font-mono"
        >
          10 s
        </text>
      </svg>
      <div className="flex flex-wrap items-center gap-2">
        <Chip>
          {REGISTRO.formato} · {REGISTRO.duracion} s · {REGISTRO.fs} Hz
        </Chip>
        <Chip dark>{NUM_LATIDOS} latidos en 10 s</Chip>
        <Chip>canal {REGISTRO.canal}</Chip>
      </div>
    </Fig>
  );
}

/* ============================================================
   Etapa 02 — Preprocesado (antes / después)
   ============================================================ */

const BOX_MINI: Box = { x: 4, w: 560, yTop: 6, h: 84 };
const RAW_PATH_MINI = buildPath(RAW, BOX_MINI);
const CLEAN_PATH_MINI = buildPath(CLEAN, BOX_MINI);

export function VisualFiltrado() {
  return (
    <Fig label="Comparación antes y después del filtrado FIR e IIR notch de 50 Hz">
      <div className="flex h-full min-h-0 flex-col justify-center gap-1">
        <div className="flex items-center gap-3">
          <div className="w-20 shrink-0">
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-neutral-500">
              Antes
            </p>
            <p className="text-[10.5px] leading-tight text-neutral-400">
              señal cruda
            </p>
          </div>
          <svg
            viewBox="0 0 568 96"
            className="h-[84px] flex-1"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              d={RAW_PATH_MINI}
              fill="none"
              stroke="#b6bfcc"
              strokeWidth="1.2"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        </div>

        <div className="flex items-center justify-center py-0.5" aria-hidden="true">
          <span className="h-6 w-px bg-neutral-200" />
        </div>

        <div className="flex items-center gap-3">
          <div className="w-20 shrink-0">
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-pds-dark">
              Después
            </p>
            <p className="text-[10.5px] leading-tight text-neutral-400">
              filtrada
            </p>
          </div>
          <svg
            viewBox="0 0 568 96"
            className="h-[84px] flex-1"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              d={CLEAN_PATH_MINI}
              fill="none"
              stroke="#2b52e8"
              strokeWidth="1.6"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Chip>FIR paso-alto 0,5 Hz</Chip>
        <Chip>FIR paso-bajo 40 Hz</Chip>
        <Chip>IIR notch 50 Hz</Chip>
        <Chip dark>distorsión QRS &lt; 5 %</Chip>
      </div>
    </Fig>
  );
}

/* ============================================================
   Etapa 03 — Detección de picos R e intervalos RR
   ============================================================ */

const BOX_PEAKS: Box = { x: 20, w: 600, yTop: 16, h: 288 };
const CLEAN_PATH_MAIN = buildPath(CLEAN, BOX_PEAKS);

function corcheteRR(i: number, y: number): React.ReactNode {
  const p1 = mapPoint(R_PEAKS[i], BOX_PEAKS);
  const p2 = mapPoint(R_PEAKS[i + 1], BOX_PEAKS);
  const x1 = p1[0];
  const x2 = p2[0];
  return (
    <g key={`rr-${i}`} aria-hidden="true">
      <line
        x1={x1}
        y1={y}
        x2={x2}
        y2={y}
        stroke="#1d3ab5"
        strokeWidth="1.2"
      />
      <line x1={x1} y1={y - 5} x2={x1} y2={y + 5} stroke="#1d3ab5" strokeWidth="1.2" />
      <line x1={x2} y1={y - 5} x2={x2} y2={y + 5} stroke="#1d3ab5" strokeWidth="1.2" />
      <text
        x={(x1 + x2) / 2}
        y={y - 7}
        textAnchor="middle"
        fontSize="10.5"
        fill="#1d3ab5"
        className="font-mono font-semibold"
      >
        RR {RR_MS[i]} ms
      </text>
    </g>
  );
}

export function VisualPicosR() {
  return (
    <Fig label="Señal filtrada con picos R marcados e intervalos RR entre latidos">
      <svg
        viewBox="0 0 640 312"
        className="h-full w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <GridLines box={BOX_PEAKS} />
        {R_PEAKS.map((p, idx) => {
          const [x] = mapPoint(p, BOX_PEAKS);
          return (
            <line
              key={idx}
              x1={x}
              y1={BOX_PEAKS.yTop}
              x2={x}
              y2={BOX_PEAKS.yTop + BOX_PEAKS.h}
              stroke="#cbd5e1"
              strokeWidth="1"
              strokeDasharray="2 5"
              aria-hidden="true"
            />
          );
        })}
        <path
          d={CLEAN_PATH_MAIN}
          fill="none"
          stroke="#2b52e8"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        {R_PEAKS.map((p, idx) => {
          const [x, y] = mapPoint(p, BOX_PEAKS);
          return (
            <circle
              key={idx}
              cx={x}
              cy={y}
              r="4.5"
              className="fill-pds stroke-white"
              strokeWidth="1.5"
            />
          );
        })}
        {corcheteRR(6, 46)}
        {corcheteRR(7, 84)}
      </svg>
      <div className="flex flex-wrap items-center gap-2">
        <Chip dark>FC ≈ {FC_LPM} lpm</Chip>
        <Chip>{R_PEAKS.length - 1} intervalos RR</Chip>
        <Chip>umbral adaptativo + refractario</Chip>
      </div>
    </Fig>
  );
}

/* ============================================================
   Etapa 04 — Extracción de características (morfología + DCT)
   ============================================================ */

const BOX_SEG: Box = { x: 12, w: 296, yTop: 26, h: 252 };
const CLEAN_PATH_SEG = buildPath(CLEAN, BOX_SEG);

/** Latido destacado dentro del tramo (índice sobre BEAT_TIMES). */
const BEAT_HIGHLIGHT = 6;
const VENTANA_S = 0.512; // ventana fija de recorte, en segundos

export function VisualCaracteristicas() {
  const tb = R_PEAKS[BEAT_HIGHLIGHT][0] * 10; // tiempo del latido, en s
  const x1 = BOX_SEG.x + ((tb - VENTANA_S / 2) / 10) * BOX_SEG.w;
  const x2 = BOX_SEG.x + ((tb + VENTANA_S / 2) / 10) * BOX_SEG.w;
  const midY = 178;

  return (
    <Fig label="Latido recortado en ventana fija y coeficientes DCT del espectro">
      <svg
        viewBox="0 0 640 312"
        className="h-full w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* tramo de señal con ventana destacada */}
        <GridLines box={BOX_SEG} />
        <rect
          x={x1}
          y={BOX_SEG.yTop}
          width={x2 - x1}
          height={BOX_SEG.h}
          fill="rgba(43,82,232,0.07)"
          stroke="#2b52e8"
          strokeWidth="1"
          strokeDasharray="3 4"
        />
        <text
          x={(x1 + x2) / 2}
          y={BOX_SEG.yTop - 8}
          textAnchor="middle"
          fontSize="10.5"
          fill="#1d3ab5"
          className="font-mono font-semibold"
        >
          ventana fija · 512 ms
        </text>
        <path
          d={CLEAN_PATH_SEG}
          fill="none"
          stroke="#2b52e8"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />

        {/* espectro DCT */}
        <line x1="352" y1={midY} x2="616" y2={midY} stroke="#e2e8f0" strokeWidth="1" />
        <text x="352" y="26" fontSize="10.5" fill="#64748b" className="font-mono">
          coef. DCT (24) → F22
        </text>
        {DCT.map((v, k) => {
          const h = Math.abs(v) * 118;
          const bx = 356 + k * 10.6;
          return (
            <rect
              key={k}
              x={bx}
              y={v >= 0 ? midY - h : midY}
              width="6.4"
              height={Math.max(2, h)}
              rx="1.5"
              className={v >= 0 ? "fill-pds" : "fill-slate-400"}
            />
          );
        })}
      </svg>
      <div className="flex flex-wrap items-center gap-2">
        {MORFOLOGIA.slice(0, 3).map((m) => (
          <Chip key={m.k}>
            {m.k} · {m.v}
          </Chip>
        ))}
        <Chip>{ESPECTRO[0].k} · {ESPECTRO[0].v}</Chip>
        <Chip dark>DCT × 24 → vector F22</Chip>
      </div>
    </Fig>
  );
}

/* ============================================================
   Etapa 05 — Clasificación (barras de probabilidad animadas)
   ============================================================ */

export function VisualClasificacion() {
  const [go, setGo] = useState(false);

  useEffect(() => {
    const id = window.setTimeout(() => setGo(true), 80);
    return () => window.clearTimeout(id);
  }, []);

  return (
    <Fig label="Probabilidades por clase de ritmo: Paced 87 por ciento, clase dominante">
      <div className="flex min-h-0 flex-1 flex-col justify-center gap-2.5">
        {PROBABILIDADES.map((p, i) => {
          const top = i === 0;
          const pct = Math.round(p.valor * 100);
          return (
            <div key={p.clase} className="flex items-center gap-3">
              <span
                className={`w-28 shrink-0 font-mono text-[11.5px] ${
                  top ? "font-bold text-pds-dark" : "text-neutral-500"
                }`}
              >
                {p.clase}
              </span>
              <div
                className={`h-7 flex-1 overflow-hidden rounded-lg border bg-neutral-50 ${
                  top ? "border-pds/30" : "border-neutral-200"
                }`}
              >
                <div
                  className={`h-full rounded-lg transition-[width] duration-700 ease-out ${
                    top ? "bg-pds" : "bg-slate-300"
                  }`}
                  style={{
                    width: go ? `${pct}%` : "0%",
                    transitionDelay: `${i * 70}ms`,
                  }}
                />
              </div>
              <span
                className={`w-12 shrink-0 text-right font-mono text-[12px] ${
                  top ? "font-bold text-pds-dark" : "text-neutral-500"
                }`}
              >
                {pct} %
              </span>
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Chip dark>clase dominante: Paced · 87 %</Chip>
        <Chip>salida probabilística, no etiqueta seca</Chip>
      </div>
    </Fig>
  );
}

/* ============================================================
   Etapa 06 — Diagnóstico (medidor de certeza)
   ============================================================ */

export function VisualDiagnostico() {
  const cx = 320;
  const cy = 268;
  const r = 206;
  const ang = Math.PI * (1 - DIAGNOSTICO.certeza); // 180° → 0°
  const nx = cx + Math.cos(ang) * (r - 44);
  const ny = cy - Math.sin(ang) * (r - 44);
  const pct = Math.round(DIAGNOSTICO.certeza * 100);

  return (
    <Fig label="Medidor de certeza del diagnóstico: 87 por ciento, ritmo de marcapasos">
      <svg
        viewBox="0 0 640 300"
        className="h-full w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="#e8edf7"
          strokeWidth="24"
          strokeLinecap="round"
        />
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          className="stroke-pds"
          strokeWidth="24"
          strokeLinecap="round"
          pathLength={100}
          strokeDasharray={`${pct} 100`}
        />
        {/* marcas 0 / 50 / 100 */}
        <text x={cx - r} y={cy + 22} textAnchor="middle" fontSize="10.5" fill="#94a3b8" className="font-mono">0</text>
        <text x={cx} y={cy - r - 14} textAnchor="middle" fontSize="10.5" fill="#94a3b8" className="font-mono">50</text>
        <text x={cx + r} y={cy + 22} textAnchor="middle" fontSize="10.5" fill="#94a3b8" className="font-mono">100</text>
        {/* aguja */}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="#0f172a" strokeWidth="3" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="7" fill="#0f172a" />
        {/* etiqueta central */}
        <text x={cx} y={cy - 74} textAnchor="middle" fontSize="46" fontWeight="700" fill="#1d3ab5" className="font-mono">
          {pct} %
        </text>
        <text x={cx} y={cy - 48} textAnchor="middle" fontSize="12.5" fill="#64748b" className="font-mono">
          certeza
        </text>
      </svg>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Chip dark>ritmo sugerido: marcapasos (Paced)</Chip>
        <Chip>Brier 0,037 · calibrado</Chip>
      </div>
    </Fig>
  );
}
