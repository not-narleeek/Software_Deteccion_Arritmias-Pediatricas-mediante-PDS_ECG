import { NextResponse } from "next/server";

/* Metadatos públicos del repositorio del proyecto (GitHub API).
   Revalidado cada 5 minutos; ante un error devuelve ok:false y la
   interfaz muestra solo el enlace al repositorio. */

const REPO =
  "not-narleeek/Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG";

export const revalidate = 300;

export async function GET() {
  try {
    const res = await fetch(`https://api.github.com/repos/${REPO}`, {
      headers: {
        Accept: "application/vnd.github+json",
        "User-Agent": "ecg-pediatrico-portal",
      },
      next: { revalidate: 300 },
    });
    if (!res.ok) {
      throw new Error(`GitHub API respondió ${res.status}`);
    }
    const data = (await res.json()) as {
      stargazers_count?: number;
      forks_count?: number;
      open_issues_count?: number;
      pushed_at?: string;
    };
    return NextResponse.json({
      ok: true,
      estrellas: data.stargazers_count ?? 0,
      forks: data.forks_count ?? 0,
      issuesAbiertos: data.open_issues_count ?? 0,
      actualizado: data.pushed_at ?? null,
    });
  } catch {
    return NextResponse.json({ ok: false });
  }
}
