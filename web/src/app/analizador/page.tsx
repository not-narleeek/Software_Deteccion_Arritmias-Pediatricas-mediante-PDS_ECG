import type { Metadata } from "next";

import { EcgAnalyzer } from "@/components/ecg-portal/ecg-analyzer";

/* ============================================================
   Página de análisis: el analizador ocupa el viewport completo
   (100dvh, sin header ni footer del portal), como una
   herramienta de producción independiente. El botón
   «Analizar un ECG» del hero enlaza aquí. El aviso de uso
   académico vive dentro de la propia aplicación (sidebar).
   Análisis heurístico 100 % en el navegador.
   ============================================================ */

export const metadata: Metadata = {
  title: "Analizar un ECG — ECG Pediátrico",
  description:
    "Cargue un registro WFDB o un caso demo: la señal se dibuja, se detectan los picos R y la clasificación ocurre en el navegador. Nada se envía a un servidor.",
};

export default function AnalizadorPage() {
  return (
    <div className="flex h-dvh flex-col overflow-hidden p-2 sm:p-3">
      <EcgAnalyzer />
      <noscript>
        <p className="absolute inset-x-4 top-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Se requiere JavaScript para usar el analizador.
        </p>
      </noscript>
    </div>
  );
}
