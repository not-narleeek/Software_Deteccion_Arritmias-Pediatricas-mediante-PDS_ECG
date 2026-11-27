"use client";

/* ============================================================
   pipeline-section.tsx — Navegador interactivo del pipeline
   PDS en 6 etapas (la demo original): rail de etapas,
   layout ENTRADA / PROCESO / SALIDA, botón "Recorrer" con
   reproducción automática y navegación accesible.
   ============================================================ */

import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import { ArrowLeft, ArrowRight, Check, HeartPulse, Pause, Play } from "lucide-react";
import {
  VisualCaracteristicas,
  VisualClasificacion,
  VisualDiagnostico,
  VisualFiltrado,
  VisualPicosR,
  VisualSenalCruda,
} from "./stage-visuals";

type Etapa = {
  kicker: string;
  rail: string;
  titulo: string;
  desc: string;
  entrada: string[];
  salida: string[];
  Visual: ComponentType;
};

const ETAPAS: Etapa[] = [
  {
    kicker: "Adquisición",
    rail: "Señal cruda",
    titulo: "La señal, tal como llega",
    desc: "Todo parte del registro del proyecto: 10 segundos de ECG pediátrico en formato WFDB. A simple vista ya aparecen los dos enemigos clásicos — el ruido de red de 50 Hz y la deriva lenta de la línea base — que el preprocesado tendrá que eliminar.",
    entrada: [
      "Registro WFDB (ZZU pECG) · 10 s @ 500 Hz",
      "Canal ECG pediátrico único, ya digitalizado",
    ],
    salida: [
      "Muestras crudas listas para filtrar",
      "Ruido y deriva aún presentes (visibles)",
    ],
    Visual: VisualSenalCruda,
  },
  {
    kicker: "Preprocesado",
    rail: "Preprocesado",
    titulo: "Filtrar sin deformar",
    desc: "La señal cruza un FIR paso-alto (0,5 Hz) y paso-bajo (40 Hz) más un IIR notch de 50 Hz. La regla del proyecto: limpiar sin tocar la morfología clínica — QRS, onda P y espículas de marcapasos quedan intactas.",
    entrada: ["Señal cruda de la etapa 01"],
    salida: [
      "Señal limpia, lista para detectar latidos",
      "Distorsión en QRS de referencia < 5 %",
    ],
    Visual: VisualFiltrado,
  },
  {
    kicker: "Detección",
    rail: "Picos R",
    titulo: "Encontrar cada latido",
    desc: "Sobre la señal limpia, un umbral adaptativo con período refractario marca cada pico R. Los intervalos RR entre latidos consecutivos dan la frecuencia cardíaca: ≈ 118 lpm, coherente con un niño.",
    entrada: ["Señal filtrada de la etapa 02"],
    salida: [
      "Posición exacta de cada pico R",
      "Intervalos RR → FC ≈ 118 lpm",
    ],
    Visual: VisualPicosR,
  },
  {
    kicker: "Características",
    rail: "Características",
    titulo: "Convertir el trazo en números",
    desc: "Cada latido se recorta con una ventana fija y se describe numéricamente: anchos y amplitudes de la morfología más los coeficientes DCT del espectro. El resultado es el vector F22, la huella dactilar del latido.",
    entrada: ["Latidos segmentados en ventana fija"],
    salida: ["Vector de características F22 por latido"],
    Visual: VisualCaracteristicas,
  },
  {
    kicker: "Clasificación",
    rail: "Clasificación",
    titulo: "Votar entre clases de ritmo",
    desc: "El vector F22 alimenta el clasificador entrenado (Random Forest / SVM), que compara el latido contra las clases del dataset y devuelve probabilidades calibradas — no una etiqueta seca. En este caso domina Paced con 87 %.",
    entrada: ["Vector F22 de la etapa 04"],
    salida: [
      "Probabilidad por clase de ritmo",
      "Clase dominante: Paced · 87 %",
    ],
    Visual: VisualClasificacion,
  },
  {
    kicker: "Diagnóstico",
    rail: "Diagnóstico",
    titulo: "Del número al diagnóstico",
    desc: "La clase más probable se convierte en el ritmo sugerido, siempre acompañado de su porcentaje de certeza. Si la certeza fuese baja, el sistema lo declararía — prefiere admitir la duda antes que adivinar.",
    entrada: ["Distribución de probabilidades de la etapa 05"],
    salida: [
      "Ritmo sugerido: marcapasos",
      "Certeza 87 % · Brier 0,037",
    ],
    Visual: VisualDiagnostico,
  },
];

const KPIS = [
  { valor: "< 5 %", label: "distorsión en QRS de referencia" },
  { valor: "ANOVA / Fisher", label: "separabilidad inter-clase" },
  { valor: "Brier 0,037", label: "calibración probabilística" },
  { valor: "≥ 85 %", label: "sensibilidad y especificidad" },
];

const NUM = ETAPAS.length;

export function PipelineSection() {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(
      () => setIndex((v) => (v + 1) % NUM),
      3400,
    );
    return () => window.clearInterval(id);
  }, [playing]);

  const etapa = ETAPAS[index];
  const num = `${index + 1}`.padStart(2, "0");
  const Visual = etapa.Visual;

  return (
    <section id="pipeline" className="scroll-mt-20 bg-white">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:px-8 lg:py-24">
        {/* encabezado de la sección */}
        <span className="inline-flex h-7 items-center gap-2 rounded-full bg-neutral-100 pl-1.5 pr-3.5">
          <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-neutral-950">
            <HeartPulse className="h-2.5 w-2.5 text-white" strokeWidth={3} aria-hidden="true" />
          </span>
          <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-neutral-800">
            Pipeline PDS
          </span>
        </span>

        <div className="mt-6 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <h2 className="font-display text-[38px] leading-[1.04] tracking-[0.005em] text-neutral-900 sm:text-[44px]">
            De la señal al diagnóstico,
            <br />
            <span className="italic text-pds-dark">en seis etapas</span>
          </h2>
          <p className="max-w-[430px] text-[14.5px] leading-relaxed text-neutral-600 lg:pb-1">
            El mismo flujo que ejecuta el software del proyecto, etapa por
            etapa: qué entra, qué se procesa y qué sale. Pulse «Recorrer» para
            verlo en secuencia automática.
          </p>
        </div>

        {/* KPI del proyecto */}
        <div className="mt-10 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {KPIS.map((k) => (
            <div
              key={k.valor}
              className="rounded-2xl border border-neutral-200 bg-white p-4"
            >
              <p className="font-mono text-lg font-bold text-pds-dark">{k.valor}</p>
              <p className="mt-1 text-[11px] leading-snug text-neutral-500">
                {k.label}
              </p>
            </div>
          ))}
        </div>

        {/* navegador de etapas */}
        <div className="mt-8 overflow-hidden rounded-3xl border border-neutral-200 bg-white shadow-[0_28px_70px_-30px_rgba(15,23,42,0.28)]">
          {/* barra superior */}
          <div className="flex items-center justify-between gap-3 bg-pds px-5 py-3 text-white">
            <span className="whitespace-nowrap font-mono text-[11px] font-semibold uppercase tracking-[0.18em]">
              Pipeline PDS<span className="hidden sm:inline"> · demo interactiva</span>
            </span>
            <span className="whitespace-nowrap font-mono text-[11px] font-bold tracking-[0.1em]">
              {num} / 06
            </span>
          </div>

          {/* rail de etapas (selección horizontal en móvil) */}
          <nav aria-label="Etapas del pipeline" className="px-4 pt-4 sm:px-6">
            <ol className="scrollbar-x flex gap-2 overflow-x-auto pb-1 sm:gap-2.5">
              {ETAPAS.map((e, idx) => {
                const activo = idx === index;
                return (
                  <li key={e.rail} className="shrink-0">
                    <button
                      type="button"
                      onClick={() => setIndex(idx)}
                      aria-current={activo ? "step" : undefined}
                      className={`flex items-center gap-2 rounded-full border px-3.5 py-2 text-[12.5px] font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-pds ${
                        activo
                          ? "border-pds bg-pds text-white shadow-[0_8px_20px_-8px_rgba(43,82,232,0.7)]"
                          : "border-neutral-200 bg-white text-neutral-600 hover:border-pds/50 hover:text-pds-dark"
                      }`}
                    >
                      <span
                        className={`font-mono text-[10.5px] ${activo ? "text-white/75" : "text-pds"}`}
                      >
                        {`${idx + 1}`.padStart(2, "0")}
                      </span>
                      {e.rail}
                    </button>
                  </li>
                );
              })}
            </ol>
          </nav>

          {/* contenido de la etapa activa */}
          <div aria-live="polite" className="px-4 pb-4 pt-5 sm:px-6 sm:pb-6">
            <p className="font-mono text-[10.5px] font-semibold uppercase tracking-[0.18em] text-pds">
              Etapa {num} · {etapa.kicker}
            </p>
            <h3 className="mt-1.5 font-display text-[30px] leading-[1.05] text-neutral-900 sm:text-[34px]">
              {etapa.titulo}
            </h3>
            <p className="mt-2 max-w-[660px] text-[14px] leading-relaxed text-neutral-600">
              {etapa.desc}
            </p>

            <div className="mt-5 grid gap-3 lg:grid-cols-[200px_minmax(0,1fr)_200px]">
              {/* ENTRADA */}
              <aside className="rounded-2xl bg-pds-soft p-4 ring-1 ring-pds/15">
                <p className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-pds-dark">
                  Entrada
                </p>
                <ul className="mt-2.5 space-y-2">
                  {etapa.entrada.map((t) => (
                    <li
                      key={t}
                      className="flex gap-2 text-[12.5px] leading-snug text-neutral-700"
                    >
                      <span
                        className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-pds"
                        aria-hidden="true"
                      />
                      {t}
                    </li>
                  ))}
                </ul>
              </aside>

              {/* PROCESO — visual de la etapa */}
              <div className="relative overflow-hidden rounded-2xl border border-neutral-200 bg-white">
                <span className="absolute left-3 top-3 z-10 rounded-full bg-neutral-900/90 px-2.5 py-1 font-mono text-[9.5px] font-bold uppercase tracking-[0.14em] text-white">
                  Proceso
                </span>
                <div className="h-[320px] p-3 sm:h-[350px]">
                  <Visual />
                </div>
              </div>

              {/* SALIDA */}
              <aside className="rounded-2xl border border-pds/25 bg-white p-4">
                <p className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-pds-dark">
                  Salida
                </p>
                <ul className="mt-2.5 space-y-2">
                  {etapa.salida.map((t) => (
                    <li
                      key={t}
                      className="flex gap-2 text-[12.5px] leading-snug text-neutral-700"
                    >
                      <Check
                        className="mt-[2px] h-3.5 w-3.5 shrink-0 text-pds"
                        aria-hidden="true"
                      />
                      {t}
                    </li>
                  ))}
                </ul>
              </aside>
            </div>
          </div>

          {/* barra inferior de navegación */}
          <div className="flex items-center justify-between gap-3 border-t border-neutral-100 px-4 py-3 sm:px-6">
            <button
              type="button"
              aria-label="Etapa anterior"
              onClick={() => setIndex((v) => (v + NUM - 1) % NUM)}
              className="rounded-full border border-neutral-200 bg-white p-2.5 text-neutral-600 transition-colors hover:border-pds/50 hover:text-pds-dark focus-visible:outline-2 focus-visible:outline-pds"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            </button>

            <div className="flex items-center gap-1.5" aria-hidden="true">
              {ETAPAS.map((_, idx) => (
                <span
                  key={idx}
                  className={`h-1.5 rounded-full transition-all duration-300 ${
                    idx === index ? "w-5 bg-pds" : "w-1.5 bg-neutral-300"
                  }`}
                />
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPlaying((p) => !p)}
                aria-pressed={playing}
                className="inline-flex items-center gap-2 rounded-full bg-pds-soft px-4 py-2 text-[12.5px] font-semibold text-pds-dark ring-1 ring-pds/25 transition-colors hover:bg-pds hover:text-white focus-visible:outline-2 focus-visible:outline-pds"
              >
                {playing ? (
                  <Pause className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <Play className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                {playing ? "Pausar" : "Recorrer"}
              </button>
              <button
                type="button"
                aria-label="Etapa siguiente"
                onClick={() => setIndex((v) => (v + 1) % NUM)}
                className="rounded-full bg-pds p-2.5 text-white transition-colors hover:bg-pds-dark focus-visible:outline-2 focus-visible:outline-pds"
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
