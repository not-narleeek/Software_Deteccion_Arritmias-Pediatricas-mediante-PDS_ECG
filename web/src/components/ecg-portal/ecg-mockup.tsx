import {
  Activity,
  ChevronDown,
  ChevronLeft,
  FileText,
  House,
  Search,
  Waves,
} from "lucide-react";

/* ============================================================
   Mockup de la aplicación del proyecto: ventana blanca con la
   señal ECG de la derivación II, marcadores de picos R y el
   panel de clasificación con porcentaje de certeza. Recreado
   en DOM a tamaño fijo 880x216 y escalado responsivamente.
   ============================================================ */

const SIDEBAR_ITEMS = [
  { label: "Registros", icon: House, active: false },
  { label: "Derivación II", icon: Activity, active: true },
  { label: "Reporte", icon: FileText, active: false },
];

/** Un complejo P-QRS-T cada 160 px, línea base y=70. */
function trazoEcg(complejos: number): string {
  const seg = (dx: number) =>
    `M${dx},70 L${dx + 20},70 C${dx + 25},62 ${dx + 31},62 ${dx + 36},70 ` +
    `L${dx + 48},70 L${dx + 50},78 L${dx + 54},70 ` +
    `L${dx + 60},16 L${dx + 66},112 L${dx + 70},78 L${dx + 72},70 ` +
    `L${dx + 86},70 C${dx + 96},56 ${dx + 112},56 ${dx + 122},70 ` +
    `L${dx + 160},70`;
  return Array.from({ length: complejos }, (_, i) => seg(i * 160)).join(" ");
}

export function EcgMockup() {
  return (
    <div
      className="relative mx-auto w-full max-w-[880px]"
      style={{ aspectRatio: "880 / 216" }}
      role="img"
      aria-label="Aplicación del proyecto mostrando la señal ECG de la derivación II con picos R detectados y clasificación Sinusal con 94 por ciento de certeza"
    >
      <div
        className="absolute left-0 top-0 h-[216px] w-[880px] origin-top-left rounded-xl bg-white text-neutral-800 shadow-[0_32px_80px_-12px_rgba(9,14,43,0.45)] ring-1 ring-black/10"
        style={{
          transform: "scale(min(1, calc((100vw - 40px) / 880)))",
        }}
      >
        {/* barra superior */}
        <div className="flex h-10 items-center gap-3 border-b border-neutral-100 px-3 text-[11px]">
          <span className="flex items-center gap-1.5">
            <img
              src="/images/logo-proyecto.svg"
              alt=""
              className="h-5 w-5 rounded-[5px]"
              aria-hidden="true"
            />
            <span className="text-[12px] font-semibold tracking-tight text-neutral-900">
              ECG Pediátrico
            </span>
          </span>
          <span className="h-4 w-px bg-neutral-200" />
          <span className="flex h-6 w-40 items-center gap-1.5 rounded-md bg-neutral-100 px-2 text-neutral-400">
            <Search className="h-3 w-3" />
            Buscar registro...
          </span>
          <span className="h-4 w-px bg-neutral-200" />
          <span className="flex items-center gap-1 text-neutral-400">
            Pacientes <span className="text-neutral-300">/</span> 042-A{" "}
            <span className="text-neutral-300">/</span>
            <span className="font-medium text-neutral-800">Derivación II</span>
          </span>
          <span className="ml-auto flex items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-md border border-neutral-200 px-2 py-1 text-[10px] font-medium text-neutral-600">
              <Waves className="h-3 w-3 text-neutral-500" />
              WFDB · 500 Hz · 10 s
            </span>
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-teal-400 to-emerald-300 text-[9px] font-bold text-white">
              P
            </span>
            <ChevronDown className="h-3 w-3 text-neutral-400" />
          </span>
        </div>

        <div className="flex h-[176px]">
          {/* barra lateral */}
          <div className="w-[150px] shrink-0 border-r border-neutral-100 p-2.5">
            <div className="flex h-7 items-center justify-between rounded-md border border-neutral-200 px-2 text-[10px] text-neutral-400">
              <span className="flex items-center gap-1.5">
                <Search className="h-3 w-3" />
                Buscar...
              </span>
              <span className="rounded border border-neutral-200 bg-neutral-50 px-1 text-[8px] text-neutral-400">
                K
              </span>
            </div>
            <p className="mt-3 px-1 text-[8px] font-semibold uppercase tracking-[0.16em] text-neutral-400">
              Estudio
            </p>
            <div className="mt-1.5 flex flex-col gap-0.5">
              {SIDEBAR_ITEMS.map((item) => (
                <span
                  key={item.label}
                  className={
                    item.active
                      ? "flex items-center gap-2 rounded-md bg-brand/10 px-2 py-1.5 text-[10.5px] font-semibold text-brand"
                      : "flex items-center gap-2 rounded-md px-2 py-1.5 text-[10.5px] font-medium text-neutral-500"
                  }
                >
                  <item.icon className="h-3.5 w-3.5" />
                  {item.label}
                </span>
              ))}
            </div>
          </div>

          {/* lienzo de la señal */}
          <div className="relative flex-1 overflow-hidden rounded-br-xl bg-[#F7F8FB] bg-dots-dark">
            {/* fila de título */}
            <div className="absolute left-3 right-3 top-2 flex items-center gap-1.5">
              <ChevronLeft className="h-3.5 w-3.5 text-neutral-400" />
              <span className="text-[12px] font-semibold text-neutral-900">
                Registro 042-A · 10 s
              </span>
              <span className="rounded border border-pink-300 bg-pink-50 px-1 py-px text-[7.5px] font-bold tracking-[0.08em] text-pink-500">
                500 Hz
              </span>
              <span className="ml-auto flex items-center gap-3">
                <span className="flex items-center gap-1 text-[9.5px] text-neutral-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  8 picos R detectados
                </span>
                <span className="flex h-6 items-center rounded-md bg-neutral-900 px-2.5 text-[9.5px] font-medium text-white">
                  Exportar
                </span>
                <span className="flex h-6 items-center rounded-md border border-neutral-200 bg-white px-2.5 text-[9.5px] font-medium text-neutral-700">
                  Reporte
                </span>
              </span>
            </div>

            {/* chip RR */}
            <span className="absolute left-[24%] top-[52px] z-10 flex items-center gap-1 rounded-full border border-neutral-200/80 bg-white px-2 py-0.5 text-[9px] font-semibold text-neutral-600 shadow-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-brand" />
              RR 505 ms
            </span>

            {/* señal ECG */}
            <svg
              viewBox="0 0 640 130"
              preserveAspectRatio="none"
              className="absolute inset-x-3 bottom-3 top-[38px] h-[calc(100%-52px)] w-[calc(100%-24px)]"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="ecgFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(22,42,200,0.10)" />
                  <stop offset="100%" stopColor="rgba(22,42,200,0)" />
                </linearGradient>
              </defs>
              {[40, 70, 100].map((y) => (
                <line
                  key={y}
                  x1="0"
                  y1={y}
                  x2="640"
                  y2={y}
                  stroke="rgba(18,22,38,0.08)"
                  strokeDasharray="2 6"
                  strokeWidth="1"
                />
              ))}
              <path d={`${trazoEcg(4)} L640,70 L640,130 L0,130 Z`} fill="url(#ecgFill)" />
              <path
                d={trazoEcg(4)}
                fill="none"
                stroke="var(--brand)"
                strokeWidth="2"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {/* marcadores de picos R */}
              {[60, 220, 380, 540].map((x) => (
                <g key={x}>
                  <circle cx={x} cy="16" r="3.2" fill="white" stroke="var(--brand)" strokeWidth="1.6" />
                </g>
              ))}
            </svg>

            {/* panel de clasificación */}
            <div className="absolute right-4 top-[38px] w-[176px] rounded-lg border border-neutral-200/80 bg-white shadow-md">
              <div className="flex items-center gap-1.5 border-b border-neutral-100 px-2.5 py-1.5">
                <span className="flex h-4 w-4 items-center justify-center rounded bg-emerald-50 text-emerald-600">
                  <svg
                    viewBox="0 0 24 24"
                    className="h-2.5 w-2.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    aria-hidden="true"
                  >
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                </span>
                <span className="text-[10px] font-semibold text-neutral-800">
                  Clasificación
                </span>
              </div>
              <div className="px-2.5 py-2">
                <div className="flex items-baseline justify-between">
                  <p className="text-[12px] font-bold text-neutral-900">Sinusal</p>
                  <p className="text-[9.5px] font-semibold text-emerald-600">94,2 %</p>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
                  <div className="h-full w-[94%] rounded-full bg-emerald-500" />
                </div>
                <div className="mt-1.5 flex gap-1">
                  {["QRS 88 ms", "FC 119"].map((tag) => (
                    <span
                      key={tag}
                      className="rounded bg-neutral-100 px-1.5 py-0.5 text-[8px] font-medium text-neutral-500"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-neutral-100 px-2.5 py-1.5 text-[9px] text-neutral-400">
                Salida calibrada
                <span className="flex items-center gap-1 font-medium text-neutral-500">
                  F22
                </span>
              </div>
            </div>

            {/* pie */}
            <span className="absolute bottom-2.5 left-3 flex items-center gap-1 text-[8.5px] font-medium text-neutral-400">
              <svg
                viewBox="0 0 24 24"
                className="h-2.5 w-2.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                aria-hidden="true"
              >
                <path d="M20 6 9 17l-5-5" />
              </svg>
              Analizado en el navegador
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
