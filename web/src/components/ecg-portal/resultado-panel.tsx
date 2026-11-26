"use client";

import { Button } from "@/components/ui/button";
import {
  TriangleAlert,
  Download,
  RotateCcw,
  CircleCheck,
} from "lucide-react";
import {
  CLASES,
  COLOR_CLASE,
  CLASES_BARRA,
  fmt,
  generarReporte,
  type Clase,
  type ClaveEdad,
  type ContextoClasificacion,
  type ResultadoClasificacion,
} from "@/lib/ecg/signal";

/* ============================================================
   Panel de resultado dentro de la vista «Reporte» de la app:
   ritmo sugerido, certeza, probabilidades por clase, medidas
   del tramo, advertencias y reporte TXT.
   ============================================================ */

const SELLO: Record<
  Clase,
  { fondo: string; borde: string; texto: string }
> = {
  Sinusal: { fondo: "bg-emerald-50", borde: "border-emerald-300", texto: "text-emerald-700" },
  SVT: { fondo: "bg-amber-50", borde: "border-amber-300", texto: "text-amber-700" },
  VT: { fondo: "bg-red-50", borde: "border-red-300", texto: "text-red-700" },
  Paced: { fondo: "bg-violet-50", borde: "border-violet-300", texto: "text-violet-700" },
  Otro: { fondo: "bg-slate-50", borde: "border-slate-300", texto: "text-slate-700" },
};

interface Props {
  res: ResultadoClasificacion;
  ctx: ContextoClasificacion;
  fuente: string;
  edadClave: ClaveEdad;
  onOtro: () => void;
}

export function ResultadoPanel({ res, ctx, fuente, edadClave, onOtro }: Props) {
  const c = COLOR_CLASE[res.clase];
  const sello = SELLO[res.clase];
  const certeza = Math.round(res.probs[res.clase] * 100);

  const descargarReporte = () => {
    const contenido = generarReporte(
      res,
      ctx,
      fuente,
      edadClave,
      new Date().toLocaleString("es-CL"),
    );
    const blob = new Blob([contenido], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "reporte_ecg_demo.txt";
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Revocar diferido: si se revoca inmediatamente después de click(),
    // Firefox/Safari pueden cancelar la descarga antes de leer el blob.
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
  };

  const regularidad =
    ctx.cv <= 0.06
      ? "Regular"
      : ctx.cv <= 0.12
        ? "Moderadamente irregular"
        : "Irregular";

  const medidas: { dt: string; dd: string }[] = [
    { dt: "FC media", dd: `${fmt(ctx.fc, 0)} lpm` },
    { dt: "RR medio", dd: `${fmt(ctx.rrMedio, 0)} ms` },
    { dt: "SDNN", dd: `${fmt(ctx.sdnn, 0)} ms` },
    { dt: "RMSSD", dd: `${fmt(ctx.rmssd, 0)} ms` },
    { dt: "pNN50", dd: Number.isFinite(ctx.pnn50) ? `${fmt(ctx.pnn50, 0)} %` : "—" },
    { dt: "Regularidad", dd: regularidad },
    {
      dt: "Ancho QRS",
      dd: ctx.anchoQRS != null ? `${fmt(ctx.anchoQRS, 0)} ms` : "No evaluable",
    },
    {
      dt: "Espículas de marcapasos",
      dd:
        ctx.espiculas === true
          ? "Detectadas"
          : ctx.espiculas === false
            ? "No detectadas"
            : "No evaluable",
    },
  ];

  return (
    <div className="space-y-5" aria-live="polite">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div
          className={`flex flex-col items-center rounded-xl border-2 px-6 py-4 ${sello.fondo} ${sello.borde} ${sello.texto}`}
        >
          <span className="text-2xl font-bold tracking-wide">{res.clase}</span>
          <span className="text-xs text-muted-foreground">ritmo sugerido</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className={`text-5xl font-bold tabular-nums ${CLASES_BARRA[c].texto}`}>
            {certeza} %
          </span>
          <span className="text-sm text-muted-foreground">
            certeza estimada
          </span>
        </div>
      </div>

      <div className="space-y-2">
        {CLASES.map((k) => {
          const pct = Math.round(res.probs[k] * 100);
          const barras = CLASES_BARRA[COLOR_CLASE[k]];
          return (
            <div key={k} className="grid grid-cols-[7rem_1fr_3.5rem] items-center gap-3">
              <span
                className={`text-sm ${k === res.clase ? `font-semibold ${barras.texto}` : "text-muted-foreground"}`}
              >
                {k}
              </span>
              <div className="h-3 overflow-hidden rounded-full bg-muted">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${barras.fill}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-right text-sm tabular-nums text-muted-foreground">
                {pct} %
              </span>
            </div>
          );
        })}
      </div>

      <div>
        <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Medidas del tramo
        </h4>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4">
          {medidas.map((m) => (
            <div key={m.dt} className="rounded-lg border border-border/60 bg-muted/40 px-3 py-2">
              <dt className="text-xs text-muted-foreground">{m.dt}</dt>
              <dd className="text-sm font-semibold tabular-nums">{m.dd}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div>
        <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Advertencias
        </h4>
        {res.advertencias.length ? (
          <ul className="space-y-2">
            {res.advertencias.map((a, i) => (
              <li
                key={i}
                className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
              >
                <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden />
                <span>{a}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="flex items-center gap-2 text-sm text-emerald-700">
            <CircleCheck className="h-4 w-4" aria-hidden />
            Sin advertencias para este tramo.
          </p>
        )}
      </div>

      <p className="text-xs leading-relaxed text-neutral-400">
        Las probabilidades provienen del clasificador calibrado del proyecto
        (F22). Confirme siempre con la evaluación clínica.
      </p>

      <div className="flex flex-wrap gap-2.5">
        <Button
          variant="outline"
          onClick={descargarReporte}
          className="h-8 border-neutral-200 text-[12px]"
        >
          <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
          Descargar reporte
        </Button>
        <Button
          variant="secondary"
          onClick={onOtro}
          className="h-8 bg-neutral-100 text-[12px] text-neutral-700 hover:bg-neutral-200"
        >
          <RotateCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
          Cargar otra señal
        </Button>
      </div>
    </div>
  );
}
