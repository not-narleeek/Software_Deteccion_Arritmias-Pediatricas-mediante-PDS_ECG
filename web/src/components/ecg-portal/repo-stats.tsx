"use client";

import { useEffect, useState } from "react";
import { Github, Star, GitFork, CircleDot, Clock } from "lucide-react";

interface InfoRepo {
  ok: boolean;
  estrellas?: number;
  forks?: number;
  issuesAbiertos?: number;
  actualizado?: string;
}

const REPO_URL =
  "https://github.com/not-narleeek/Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG";

function fechaCorta(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-CL", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export function RepoStats() {
  const [info, setInfo] = useState<InfoRepo | null>(null);

  useEffect(() => {
    let vivo = true;
    fetch("/api/repo-info")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("sin respuesta"))))
      .then((data: InfoRepo) => {
        if (vivo) setInfo(data);
      })
      .catch(() => {
        if (vivo) setInfo({ ok: false });
      });
    return () => {
      vivo = false;
    };
  }, []);

  const items: { icono: typeof Star; texto: string }[] = [];
  if (info?.ok && typeof info.estrellas === "number") {
    items.push({ icono: Star, texto: `${info.estrellas.toLocaleString("es-CL")} estrellas` });
  }
  if (info?.ok && typeof info.forks === "number") {
    items.push({ icono: GitFork, texto: `${info.forks.toLocaleString("es-CL")} forks` });
  }
  if (info?.ok && typeof info.issuesAbiertos === "number") {
    items.push({ icono: CircleDot, texto: `${info.issuesAbiertos} issues y PR abiertos` });
  }
  if (info?.ok && info.actualizado) {
    items.push({
      icono: Clock,
      texto: `Último push: ${fechaCorta(info.actualizado)}`,
    });
  }

  return (
    <a
      href={REPO_URL}
      target="_blank"
      rel="noreferrer"
      className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-xl border border-border/70 bg-white px-5 py-4 transition-colors hover:border-brand/40 hover:shadow-sm"
    >
      <span className="flex min-w-0 items-center gap-2.5">
        <Github className="h-5 w-5 shrink-0 text-neutral-900" aria-hidden />
        <span className="truncate font-mono text-[13px] font-medium text-neutral-700">
          not-narleeek / Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG
        </span>
      </span>
      {items.length ? (
        <span className="ml-auto flex flex-wrap items-center gap-y-2 text-xs text-muted-foreground">
          {items.map((it, i) => {
            const Icono = it.icono;
            return (
              <span
                key={it.texto}
                className={`flex items-center gap-1.5 px-3 ${i > 0 ? "border-l border-border/70" : ""}`}
              >
                <Icono className="h-3.5 w-3.5" aria-hidden />
                {it.texto}
              </span>
            );
          })}
        </span>
      ) : (
        <span className="ml-auto text-xs text-muted-foreground">
          Ver código, issues y releases en GitHub
        </span>
      )}
    </a>
  );
}
