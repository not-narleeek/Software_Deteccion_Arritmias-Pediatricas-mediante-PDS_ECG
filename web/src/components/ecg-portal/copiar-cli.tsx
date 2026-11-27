"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";

/* Botón para copiar los comandos del bloque CLI de la sección Modelo F22.
   Con feedback visual de 2 s tras copiar. */
export function CopiarCli({ comandos }: { comandos: string }) {
  const [copiado, setCopiado] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(
    () => () => {
      clearTimeout(timer.current);
    },
    [],
  );

  async function copiar() {
    try {
      await navigator.clipboard.writeText(comandos);
      setCopiado(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopiado(false), 2000);
    } catch {
      /* portapapeles no disponible (contexto no seguro); el botón queda sin efecto */
    }
  }

  return (
    <button
      type="button"
      onClick={copiar}
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 font-mono text-[11px] text-white/50 transition-colors hover:bg-white/10 hover:text-white/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white/70"
      aria-label="Copiar comandos de la CLI"
    >
      {copiado ? (
        <Check className="h-3.5 w-3.5" aria-hidden="true" />
      ) : (
        <Copy className="h-3.5 w-3.5" aria-hidden="true" />
      )}
      {copiado ? "Copiado" : "Copiar"}
    </button>
  );
}
