import {
  BookOpen,
  Database,
  ExternalLink,
  FileText,
  Github,
  HeartPulse,
  ShieldCheck,
} from "lucide-react";
import { RepoStats } from "./repo-stats";

const REPO_URL =
  "https://github.com/not-narleeek/Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG";

/* ============================================================
   Secciones estáticas del portal (contenido adaptado del
   README.md y de web/index.html del repositorio del proyecto),
   con el lenguaje visual de la landing de referencia:
   badges pill, tipografía serif, tarjetas azules sobre pasto.
   ============================================================ */

function PillBadge({
  label,
  tone = "light",
}: {
  label: string;
  tone?: "light" | "dark";
}) {
  if (tone === "dark") {
    return (
      <span className="inline-flex h-7 items-center gap-2 rounded-full bg-white/10 pl-1.5 pr-3.5">
        <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-white">
          <HeartPulse
            className="h-2.5 w-2.5 text-brand"
            strokeWidth={3}
            aria-hidden="true"
          />
        </span>
        <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-white">
          {label}
        </span>
      </span>
    );
  }
  return (
    <span className="inline-flex h-7 items-center gap-2 rounded-full bg-neutral-100 pl-1.5 pr-3.5">
      <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-neutral-950">
        <HeartPulse
          className="h-2.5 w-2.5 text-white"
          strokeWidth={3}
          aria-hidden="true"
        />
      </span>
      <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-neutral-800">
        {label}
      </span>
    </span>
  );
}

/* ------------------------------------------------------------
   Cómo funciona — cuatro pasos numerados (flujo de la demo)
   ------------------------------------------------------------ */

const PASOS = [
  {
    num: "1",
    titulo: "Prepare el registro",
    texto:
      "Un registro WFDB de 10 segundos del ECG de 12 derivaciones (idealmente 500 Hz, en mV): el encabezado .hea y sus muestras .dat.",
  },
  {
    num: "2",
    titulo: "Cargue la señal",
    texto:
      "Suba el registro en esta web o pruebe con un caso de demostración. Sus datos no salen de este navegador.",
  },
  {
    num: "3",
    titulo: "Analice",
    texto:
      "El sistema revisa el trazo, detecta los latidos y mide la variabilidad y la morfología del tramo.",
  },
  {
    num: "4",
    titulo: "Revise el resultado",
    texto:
      "Se sugiere un ritmo con certeza y advertencias. La decisión clínica siempre corresponde al profesional.",
  },
];

export function ComoFunciona() {
  return (
    <section id="como-funciona" className="scroll-mt-16 bg-neutral-50/80">
      <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8">
        <PillBadge label="Cómo funciona" />
        <h2 className="mt-8 max-w-xl font-display text-[30px] leading-[1.06] tracking-[0.005em] text-neutral-900 sm:text-[36px]">
          Cuatro pasos, sin instalar nada
        </h2>
        <ol className="mt-10 grid gap-px overflow-hidden rounded-2xl border border-border/70 bg-border/70 sm:grid-cols-2 lg:grid-cols-4">
          {PASOS.map((p) => (
            <li key={p.num} className="bg-white p-6">
              <span className="font-display text-[34px] leading-none text-brand">
                {p.num}
              </span>
              <h3 className="mt-4 text-[15px] font-semibold">{p.titulo}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-neutral-600">
                {p.texto}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------
   Guía de resultados
   ------------------------------------------------------------ */

const TARJETAS = [
  {
    dot: "bg-emerald-500",
    titulo: "Sinusal",
    texto:
      "Ritmo normal: el impulso nace en el nodo sinusal y sigue la vía habitual. La frecuencia normal varía con la edad (p. ej., 90–150 lpm entre 1 y 3 años; 60–100 lpm sobre los 12 años).",
  },
  {
    dot: "bg-amber-500",
    titulo: "SVT · Taquicardia supraventricular",
    texto:
      "Ritmo muy rápido (en pediatría, habitualmente ≥ 150–180 lpm), regular y de complejos estrechos. Puede comprometer la estabilidad del niño: requiere evaluación clínica pronta.",
  },
  {
    dot: "bg-red-500",
    titulo: "VT · Taquicardia ventricular",
    texto:
      "Ritmo rápido originado en los ventrículos, con complejos QRS anchos (≥ 120 ms). Potencialmente grave: active la vía de urgencia según el protocolo institucional.",
  },
  {
    dot: "bg-violet-500",
    titulo: "Paced · Ritmo de marcapasos",
    texto:
      "Cada latido es precedido por una espícula eléctrica artificial. Verifique el funcionamiento del dispositivo y la captura ventricular.",
  },
  {
    dot: "bg-slate-400",
    titulo: "Otro",
    texto:
      "El tramo no calza con las clases anteriores: puede tratarse de bradicardia marcada, ritmo irregular u otro patrón. Revise la calidad de la señal y considere derivar la evaluación.",
  },
];

export function GuiaResultados() {
  return (
    <section id="guia" className="scroll-mt-16 bg-white">
      <div className="mx-auto max-w-7xl px-6 pb-24 pt-4 lg:px-8">
        <PillBadge label="Guía de resultados" />
        <div className="mt-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <h2 className="font-display text-[38px] leading-[1.04] tracking-[0.005em] text-neutral-900 sm:text-[44px]">
            Qué significa
            <br />
            cada clase sugerida
          </h2>
          <p className="max-w-[380px] text-[14.5px] leading-relaxed text-neutral-600 lg:pb-1">
            Las clases objetivo del proyecto (Sinusal, SVT, VT y Paced) más la
            categoría «Otro», explicadas para lectura clínica rápida.
          </p>
        </div>
        <div className="mt-12 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {TARJETAS.map((t) => (
            <div
              key={t.titulo}
              className="rounded-2xl border border-border/70 bg-white p-6 transition-shadow hover:shadow-md"
            >
              <h3 className="flex items-center gap-2.5 text-[15px] font-semibold">
                <span
                  className={`h-3 w-3 shrink-0 rounded-full ${t.dot}`}
                  aria-hidden
                />
                {t.titulo}
              </h3>
              <p className="mt-3 text-[13px] leading-relaxed text-neutral-600">
                {t.texto}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------
   Modelo F22 — sección oscura
   ------------------------------------------------------------ */

const F1 = [
  { metrica: "F1 macro", valor: "0,6125" },
  { metrica: "F1 Sinusal", valor: "0,6215" },
  { metrica: "F1 SVT", valor: "0,5385" },
  { metrica: "F1 VT", valor: "0,4857" },
  { metrica: "F1 Paced", valor: "0,7368" },
  { metrica: "F1 Otro", valor: "0,6800" },
];

export function ModeloF22() {
  return (
    <section id="modelo" className="scroll-mt-16 bg-brand-ink text-white">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
        <PillBadge tone="dark" label="Modelo real · F22 seed 14" />
        <h2 className="mt-8 max-w-2xl font-display text-[38px] leading-[1.04] tracking-[0.005em] sm:text-[44px]">
          La clasificación calibrada, fuera de línea
        </h2>
        <p className="mt-5 max-w-3xl text-[14.5px] leading-relaxed text-white/70">
          El modelo del proyecto (candidato F22 seed 14: red morfológica +
          especialista Paced) entrega la clasificación calibrada a partir de
          registros WFDB o matrices NumPy de 10 s a 500 Hz. También puede
          ejecutarlo fuera de línea con la CLI incluida en el repositorio:
        </p>

        <div className="mt-10 grid gap-10 lg:grid-cols-[1.2fr_1fr]">
          <div>
            <pre className="overflow-x-auto rounded-2xl border border-white/10 bg-black/40 p-5 text-[13px] leading-relaxed text-white/90">
              <code>
                {`python contrib/carlos/f22_seed14/descargar_modelo.py
python contrib/carlos/f22_seed14/predecir_ecg.py \\
    --entrada data/paciente/registro.hea --inicio 0 \\
    --salida prediccion.json`}
              </code>
            </pre>
            <a
              className="mt-4 inline-flex items-center gap-1.5 text-[13px] font-medium text-white underline underline-offset-4 transition-colors hover:text-white/80"
              href={`${REPO_URL}/blob/main/contrib/carlos/f22_seed14/README.md`}
              target="_blank"
              rel="noreferrer"
            >
              Detalles de instalación, verificación y uso
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
            </a>
          </div>

          <div>
            <h3 className="text-[15px] font-semibold">
              Desempeño en validación (corpus ZZU pECG)
            </h3>
            <table className="mt-4 w-full overflow-hidden rounded-2xl border border-white/10 text-sm">
              <thead className="bg-white/5 text-left">
                <tr>
                  <th
                    scope="col"
                    className="px-4 py-2.5 font-medium text-white/60"
                  >
                    Métrica
                  </th>
                  <th
                    scope="col"
                    className="px-4 py-2.5 text-right font-medium text-white/60"
                  >
                    Valor
                  </th>
                </tr>
              </thead>
              <tbody>
                {F1.map((f) => (
                  <tr key={f.metrica} className="border-t border-white/10">
                    <td className="px-4 py-2.5 text-white/80">{f.metrica}</td>
                    <td className="px-4 py-2.5 text-right font-semibold tabular-nums">
                      {f.valor}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs leading-relaxed text-white/50">
              Métricas de validación; el conjunto de prueba final permanece
              reservado. Etapa II cerrada sobre corpus ZZU pECG (mejor RF
              F11–F14: F1 macro 0,518 · Brier 0,037). Etapa II-bis en curso:
              Deep Learning ZZU-only + Optuna en Vast.ai.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------
   Limitaciones y alcance
   ------------------------------------------------------------ */

const LIMITACIONES = [
  {
    fuerte: "No es un dispositivo médico certificado:",
    resto:
      " uso limitado a investigación, docencia y demostración retrospectiva.",
  },
  {
    fuerte: "Clasifica tramos de ritmo sostenido",
    resto: " (ventanas de ~10 s), no latido a latido.",
  },
  {
    fuerte: "Población de desarrollo:",
    resto:
      " niños de 0 a 14 años hospitalizados (corpus ZZU pECG); no es extrapolable a otros contextos sin validación.",
  },
  {
    fuerte: "VT y Paced tienen soporte escaso",
    resto: " en el corpus (92 y 22 registros respectivamente).",
  },
  {
    fuerte: "ECG superficiales de 12 (o 9) derivaciones:",
    resto:
      " diagnostica ritmos eléctricos, no patologías estructurales del corazón; excluye electrogramas intracardíacos.",
  },
  {
    fuerte: "Ritmos irregulares (p. ej., fibrilación auricular)",
    resto: " están fuera del alcance del modelo y se reportan como «Otro».",
  },
];

export function Limitaciones() {
  return (
    <section id="limitaciones" className="scroll-mt-16 bg-white">
      <div className="mx-auto max-w-7xl px-6 pb-24 pt-4 lg:px-8">
        <PillBadge label="Alcance" />
        <h2 className="mt-8 max-w-xl font-display text-[38px] leading-[1.04] tracking-[0.005em] text-neutral-900 sm:text-[44px]">
          Limitaciones que
          <br />
          conviene conocer
        </h2>
        <ul className="mt-10 grid gap-3 md:grid-cols-2">
          {LIMITACIONES.map((l, i) => (
            <li
              key={i}
              className="flex items-start gap-3 rounded-2xl border border-border/70 bg-neutral-50/60 p-5 text-sm leading-relaxed"
            >
              <ShieldCheck
                className="mt-0.5 h-4 w-4 shrink-0 text-brand"
                aria-hidden
              />
              <span>
                <strong>{l.fuerte}</strong>
                {l.resto}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------
   Recursos del proyecto
   ------------------------------------------------------------ */

const RECURSOS = [
  {
    icono: Github,
    titulo: "Repositorio del proyecto",
    texto:
      "Código fuente, documentación, scripts y resultados del pipeline.",
    href: REPO_URL,
  },
  {
    icono: Database,
    titulo: "Dataset ZZU pECG",
    texto: "14.190 ECG pediátricos de 11.643 niños 0–14 años (Scientific Data 12:867, 2025 · CC BY 4.0).",
    href: "https://doi.org/10.6084/m9.figshare.27078763",
  },
  {
    icono: BookOpen,
    titulo: "Metodología del corpus",
    texto: "Inventario, mapeo AHA → clases, control de calidad y documentos de etapa.",
    href: `${REPO_URL}/blob/main/docs/metodologia_zzu_pecg.md`,
  },
  {
    icono: FileText,
    titulo: "PPS · Propuesta del proyecto",
    texto: "Exploración del dataset, revisión de literatura y diseño del pipeline DSP.",
    href: `${REPO_URL}/blob/main/docs/PPS.md`,
  },
];

export function RecursosProyecto() {
  return (
    <section id="recursos" className="bg-neutral-50/80">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
        <PillBadge label="Proyecto" />
        <div className="mt-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <h2 className="font-display text-[38px] leading-[1.04] tracking-[0.005em] text-neutral-900 sm:text-[44px]">
            Proyecto y datos
            <br />
            de origen
          </h2>
          <p className="max-w-[400px] text-[14.5px] leading-relaxed text-neutral-600 lg:pb-1">
            Proyecto académico de la asignatura Proyectos en TICS II (Facultad
            de Ingeniería, Universidad Diego Portales) — Segundo Semestre 2026.
            Experto asesor clínico: Diego Maureira.
          </p>
        </div>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {RECURSOS.map((r) => {
            const Icono = r.icono;
            return (
              <a
                key={r.titulo}
                href={r.href}
                target="_blank"
                rel="noreferrer"
                className="group rounded-2xl border border-border/70 bg-white p-6 transition-shadow hover:shadow-md"
              >
                <span className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand">
                  <Icono className="h-5 w-5" aria-hidden />
                </span>
                <h3 className="flex items-center gap-1.5 text-sm font-semibold">
                  {r.titulo}
                  <ExternalLink
                    className="h-3.5 w-3.5 text-neutral-400 transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-neutral-600">
                  {r.texto}
                </p>
              </a>
            );
          })}
        </div>
        <div className="mt-10">
          <RepoStats />
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------
   Footer oscuro estilo referencia
   ------------------------------------------------------------ */

const FOOTER_COLUMNS = [
  {
    heading: "Portal",
    links: [
      { label: "Pipeline PDS", href: "#pipeline" },
      { label: "Analizar ECG", href: "#analizar" },
      { label: "Guía de resultados", href: "#guia" },
      { label: "Limitaciones", href: "#limitaciones" },
    ],
  },
  {
    heading: "Recursos",
    links: [
      { label: "Repositorio en GitHub", href: REPO_URL },
      { label: "Dataset ZZU pECG", href: "https://doi.org/10.6084/m9.figshare.27078763" },
      {
        label: "Metodología del corpus",
        href: `${REPO_URL}/blob/main/docs/metodologia_zzu_pecg.md`,
      },
      {
        label: "Modelo F22 (contrib)",
        href: `${REPO_URL}/blob/main/contrib/carlos/f22_seed14/README.md`,
      },
    ],
  },
  {
    heading: "Créditos",
    links: [
      { label: "Facultad de Ingeniería · UDP", href: "https://www.udp.cl" },
      { label: "Proyectos en TICS II · 2S 2026", href: REPO_URL },
      { label: "Experto asesor: Diego Maureira", href: REPO_URL },
    ],
  },
];

export function FooterEcg() {
  return (
    <footer className="mt-auto bg-brand-ink text-white">
      <div className="mx-auto max-w-7xl px-6 py-14 lg:px-8">
        <div className="flex flex-col justify-between gap-10 lg:flex-row">
          <div className="max-w-xs">
            <span className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white p-1">
                <img
                  src="/images/logo-proyecto.svg"
                  alt=""
                  className="h-full w-full"
                  aria-hidden="true"
                />
              </span>
              <span className="text-[17px] font-bold tracking-tight">
                ECG Pediátrico
              </span>
            </span>
            <p className="mt-3 text-[13px] leading-relaxed text-white/60">
              Detección de arritmias pediátricas mediante PDS de señales ECG —
              soporte diagnóstico con porcentaje de certeza.
            </p>
          </div>
          <nav
            aria-label="Pie de página"
            className="grid grid-cols-2 gap-8 sm:grid-cols-3 lg:gap-16"
          >
            {FOOTER_COLUMNS.map((col) => (
              <div key={col.heading}>
                <h4 className="text-[10px] font-bold uppercase tracking-[0.14em] text-white/50">
                  {col.heading}
                </h4>
                <ul className="mt-3 flex flex-col gap-2">
                  {col.links.map((link) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        target={link.href.startsWith("http") ? "_blank" : undefined}
                        rel={link.href.startsWith("http") ? "noreferrer" : undefined}
                        className="text-[13px] text-white/75 transition-colors hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>
        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-white/10 pt-6 sm:flex-row sm:items-center">
          <p className="text-[12px] text-white/50">
            © 2026 Proyecto TICS-II-2026-ECG-PED · Universidad Diego Portales ·
            Datos: ZZU pECG (CC BY 4.0)
          </p>
          <div className="flex items-center gap-5 text-[12px] text-white/50">
            <span>Demo académica sin certificación médica</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
