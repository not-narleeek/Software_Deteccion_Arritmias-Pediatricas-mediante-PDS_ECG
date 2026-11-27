import { EcgAnalyzer } from "@/components/ecg-portal/ecg-analyzer";
import { HeroEcg } from "@/components/ecg-portal/hero-ecg";
import {
  ComoFunciona,
  GuiaResultados,
  Limitaciones,
  ModeloF22,
  RecursosProyecto,
  FooterEcg,
} from "@/components/ecg-portal/sections";
import { PipelineSection } from "@/components/ecg-portal/pipeline/pipeline-section";
import { HeartPulse } from "lucide-react";

/* ============================================================
   Portal de demostración — Detección de Arritmias Pediátricas
   mediante PDS de señales ECG (TICS II · UDP).
   Contenido adaptado del repositorio del proyecto con la
   visual de la landing de referencia: hero azul con serif,
   mockup sobre praderas, badges pill y tarjetas sobre pasto.
   Análisis heurístico 100 % en el navegador.
   ============================================================ */

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      <main className="flex-1">
        <HeroEcg />
        <PipelineSection />
        <ComoFunciona />

        <section id="analizar" className="scroll-mt-16 bg-brand">
          <div className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
            <span className="inline-flex h-7 items-center gap-2 rounded-full bg-white/10 pl-1.5 pr-3.5">
              <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-white">
                <HeartPulse
                  className="h-2.5 w-2.5 text-brand"
                  strokeWidth={3}
                  aria-hidden="true"
                />
              </span>
              <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-white">
                Analizador en línea
              </span>
            </span>
            <div className="mt-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <h2 className="max-w-xl font-display text-[38px] leading-[1.04] tracking-[0.005em] text-white sm:text-[44px]">
                Analizar un ECG,
                <br />
                aquí y ahora
              </h2>
              <p className="max-w-[380px] text-[14.5px] leading-relaxed text-white/75 lg:pb-1">
                Cargue un registro WFDB o un caso demo: la señal se dibuja, se detectan los
                picos R y la clasificación ocurre aquí mismo, en este navegador.
              </p>
            </div>
            <noscript>
              <p className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                Se requiere JavaScript para usar el analizador de esta página.
              </p>
            </noscript>
            <div className="mt-10 rounded-2xl bg-white p-2 shadow-[0_32px_80px_-24px_rgba(9,14,43,0.55)] ring-1 ring-black/10 sm:p-3">
              <EcgAnalyzer />
            </div>
          </div>
        </section>

        <GuiaResultados />
        <ModeloF22 />
        <Limitaciones />
        <RecursosProyecto />
      </main>
      <FooterEcg />
    </div>
  );
}
