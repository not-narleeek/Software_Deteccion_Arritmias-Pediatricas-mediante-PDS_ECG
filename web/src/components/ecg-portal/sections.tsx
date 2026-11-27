import {
  Activity,
  BookOpen,
  ChevronRight,
  Database,
  ExternalLink,
  FileText,
  Github,
  HeartPulse,
  ShieldAlert,
  Timer,
  Users,
  Waves,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { RepoStats } from "./repo-stats";
import { CopiarCli } from "./copiar-cli";

const REPO_URL =
  "https://github.com/not-narleeek/Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG";

/* ============================================================
   Secciones estáticas del portal (contenido adaptado del
   README.md y de web/index.html del repositorio del proyecto),
   con el lenguaje visual de la landing de referencia:
   badges pill, tipografía serif, tarjetas azules sobre pasto.
   ============================================================ */

export function PillBadge({
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
        <ol className="mt-12 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {PASOS.map((p, i) => {
            const ultimo = i === PASOS.length - 1;
            return (
              <li key={p.num} className="flex flex-col">
                <div className="flex items-center">
                  <span
                    className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full border font-display text-[22px] leading-none ${
                      ultimo
                        ? "border-brand bg-brand text-white"
                        : "border-brand/30 bg-pds-soft/70 text-brand"
                    }`}
                    aria-hidden="true"
                  >
                    {p.num}
                  </span>
                  {!ultimo && (
                    <span
                      className="ml-4 hidden flex-1 items-center gap-1 lg:flex"
                      aria-hidden="true"
                    >
                      <span className="h-px flex-1 bg-border" />
                      <ChevronRight className="h-4 w-4 shrink-0 text-neutral-300" />
                    </span>
                  )}
                </div>
                <h3 className="mt-5 text-[15px] font-semibold text-neutral-900">
                  {p.titulo}
                </h3>
                <p className="mt-2 text-[13px] leading-relaxed text-neutral-600">
                  {p.texto}
                </p>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------
   Guía de resultados
   ------------------------------------------------------------ */

/* Cada tarjeta lleva un trazo esquemático del patrón (viewBox 240×36,
   línea base y = 22). Los colores replican SELLO_CAB del analizador
   para que la guía y el resultado se lean como un mismo sistema. */
const TARJETAS = [
  {
    dot: "bg-emerald-500",
    banda: "bg-emerald-50",
    chip: "border-emerald-200/80 bg-emerald-50 text-emerald-700",
    trazo: "text-emerald-600",
    titulo: "Sinusal",
    tag: "Ritmo normal",
    texto:
      "El impulso nace en el nodo sinusal y sigue la vía habitual. La frecuencia normal varía con la edad (p. ej., 90–150 lpm entre 1 y 3 años; 60–100 lpm sobre los 12 años).",
    datos: ["Onda P presente", "QRS estrecho", "60–100 lpm > 12 años"],
    span: "xl:col-span-2",
    trazoD:
      "M0 22 C2 15 6 15 8 22 L12 22 L14 26 L16 7 L18 25 L22 25 C24 17 28 17 30 22 L60 22 C62 15 66 15 68 22 L72 22 L74 26 L76 7 L78 25 L82 25 C84 17 88 17 90 22 L120 22 C122 15 126 15 128 22 L132 22 L134 26 L136 7 L138 25 L142 25 C144 17 148 17 150 22 L180 22 C182 15 186 15 188 22 L192 22 L194 26 L196 7 L198 25 L202 25 C204 17 208 17 210 22 L240 22",
  },
  {
    dot: "bg-amber-500",
    banda: "bg-amber-50",
    chip: "border-amber-200/80 bg-amber-50 text-amber-700",
    trazo: "text-amber-600",
    titulo: "SVT · Taquicardia supraventricular",
    tag: "Evaluar pronto",
    texto:
      "Ritmo muy rápido (en pediatría, habitualmente ≥ 150–180 lpm), regular y de complejos estrechos. Puede comprometer la estabilidad del niño: requiere evaluación clínica pronta.",
    datos: ["≥ 150–180 lpm", "QRS estrecho", "Ritmo regular"],
    span: "xl:col-span-2",
    trazoD:
      "M0 22 L10 22 L11 8 L13 26 L14 22 L28 22 L29 8 L31 26 L32 22 L46 22 L47 8 L49 26 L50 22 L64 22 L65 8 L67 26 L68 22 L82 22 L83 8 L85 26 L86 22 L100 22 L101 8 L103 26 L104 22 L118 22 L119 8 L121 26 L122 22 L136 22 L137 8 L139 26 L140 22 L154 22 L155 8 L157 26 L158 22 L172 22 L173 8 L175 26 L176 22 L190 22 L191 8 L193 26 L194 22 L208 22 L209 8 L211 26 L212 22 L226 22 L227 8 L229 26 L230 22 L240 22",
  },
  {
    dot: "bg-red-500",
    banda: "bg-red-50",
    chip: "border-red-200/80 bg-red-50 text-red-700",
    trazo: "text-red-600",
    titulo: "VT · Taquicardia ventricular",
    tag: "Vía de urgencia",
    texto:
      "Ritmo rápido originado en los ventrículos, con complejos QRS anchos (≥ 120 ms). Potencialmente grave: active la vía de urgencia según el protocolo institucional.",
    datos: ["QRS ≥ 120 ms", "Ritmo rápido regular"],
    span: "xl:col-span-2",
    trazoD:
      "M0 22 Q10 -12 20 22 Q30 44 40 22 Q50 -12 60 22 Q70 44 80 22 Q90 -12 100 22 Q110 44 120 22 Q130 -12 140 22 Q150 44 160 22 Q170 -12 180 22 Q190 44 200 22 Q210 -12 220 22 Q230 44 240 22",
  },
  {
    dot: "bg-violet-500",
    banda: "bg-violet-50",
    chip: "border-violet-200/80 bg-violet-50 text-violet-700",
    trazo: "text-violet-600",
    titulo: "Paced · Ritmo de marcapasos",
    tag: "Verificar dispositivo",
    texto:
      "Cada latido es precedido por una espícula eléctrica artificial. Verifique el funcionamiento del dispositivo y la captura ventricular.",
    datos: ["Espícula + QRS", "Ritmo regular"],
    span: "md:col-span-2 xl:col-span-3",
    trazoD:
      "M0 22 L10 22 L10 12 L10 27 L11 22 L13 22 L14 8 L16 24 L17 22 C19 17 23 17 25 22 L70 22 L70 12 L70 27 L71 22 L73 22 L74 8 L76 24 L77 22 C79 17 83 17 85 22 L130 22 L130 12 L130 27 L131 22 L133 22 L134 8 L136 24 L137 22 C139 17 143 17 145 22 L190 22 L190 12 L190 27 L191 22 L193 22 L194 8 L196 24 L197 22 C199 17 203 17 205 22 L240 22",
  },
  {
    dot: "bg-slate-400",
    banda: "bg-slate-100",
    chip: "border-slate-200/80 bg-slate-100 text-slate-600",
    trazo: "text-slate-500",
    titulo: "Otro",
    tag: "Revisar señal",
    texto:
      "El tramo no calza con las clases anteriores: puede tratarse de bradicardia marcada, ritmo irregular u otro patrón. Revise la calidad de la señal y considere derivar la evaluación.",
    datos: ["Patrón no clasificado", "Verificar calidad"],
    span: "md:col-span-2 xl:col-span-3",
    trazoD:
      "M0 22 L10 22 L11 9 L13 25 L14 22 C16 17 20 17 22 22 L32 22 L33 9 L35 25 L36 22 L48 22 L49 9 L51 25 L52 22 C54 17 58 17 60 22 L76 22 L77 9 L79 25 L80 22 L90 22 L91 9 L93 25 L94 22 C96 17 100 17 102 22 L114 22 L115 9 L117 25 L118 22 L136 22 L137 9 L139 25 L140 22 C142 17 146 17 148 22 L170 22 L171 9 L173 25 L174 22 L186 22 L187 9 L189 25 L190 22 C192 17 196 17 198 22 L212 22 L213 9 L215 25 L216 22 L240 22",
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
            categoría «Otro», explicadas para lectura clínica rápida. Cada
            tarjeta muestra el patrón esperado, la conducta sugerida y los
            datos clave para reconocerlo.
          </p>
        </div>
        <div className="mt-12 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          {TARJETAS.map((t) => (
            <article
              key={t.titulo}
              className={`flex flex-col overflow-hidden rounded-2xl border border-border/70 bg-white transition-shadow hover:shadow-md ${t.span}`}
            >
              <div
                className={`flex h-14 items-center border-b border-black/[0.04] px-6 ${t.banda}`}
              >
                <svg
                  viewBox="0 0 240 36"
                  className={`h-10 w-auto max-w-full ${t.trazo}`}
                  role="img"
                  aria-label={`Trazo esquemático de ${t.titulo}`}
                >
                  <path
                    d={t.trazoD}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    vectorEffect="non-scaling-stroke"
                  />
                </svg>
              </div>
              <div className="flex flex-1 flex-col p-6 pt-5">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`h-2.5 w-2.5 shrink-0 rounded-full ${t.dot}`}
                    aria-hidden="true"
                  />
                  <h3 className="text-[15px] font-semibold text-neutral-900">
                    {t.titulo}
                  </h3>
                </div>
                <span
                  className={`mt-2.5 self-start rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${t.chip}`}
                >
                  {t.tag}
                </span>
                <p className="mt-3 text-[13px] leading-relaxed text-neutral-600">
                  {t.texto}
                </p>
                <ul
                  className="mt-auto flex flex-wrap gap-1.5 pt-5"
                  aria-label={`Datos clave de ${t.titulo}`}
                >
                  {t.datos.map((d) => (
                    <li
                      key={d}
                      className="rounded-md border border-border/60 bg-neutral-50 px-2 py-1 font-mono text-[11px] leading-none text-neutral-500"
                    >
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------
   Modelo F22 — sección oscura
   ------------------------------------------------------------ */

const CLI_COMANDOS = `python contrib/carlos/f22_seed14/descargar_modelo.py
python contrib/carlos/f22_seed14/predecir_ecg.py \\
    --entrada data/paciente/registro.hea --inicio 0 \\
    --salida prediccion.json`;

const F1_MACRO = { valor: "0,6125", pct: 61.25 };

/* Barras en nivel 400 (sobre fondo oscuro) replicando la paleta de clases
   de la guía de resultados y del analizador. */
const F1_CLASES = [
  { clase: "Sinusal", valor: "0,6215", pct: 62.15, fill: "bg-emerald-400" },
  { clase: "SVT", valor: "0,5385", pct: 53.85, fill: "bg-amber-400" },
  { clase: "VT", valor: "0,4857", pct: 48.57, fill: "bg-red-400" },
  { clase: "Paced", valor: "0,7368", pct: 73.68, fill: "bg-violet-400" },
  { clase: "Otro", valor: "0,6800", pct: 68, fill: "bg-slate-400" },
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
            <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/40">
              <div className="flex items-center justify-between border-b border-white/10 px-5 py-2.5">
                <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-white/40">
                  CLI · Bash
                </span>
                <CopiarCli comandos={CLI_COMANDOS} />
              </div>
              <pre className="overflow-x-auto p-5 text-[13px] leading-relaxed text-white/90">
                <code>{CLI_COMANDOS}</code>
              </pre>
            </div>
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

            <div className="mt-4 flex items-center gap-4 rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
              <span className="font-display text-[42px] leading-none tracking-[0.005em]">
                {F1_MACRO.valor}
              </span>
              <span className="text-[12px] leading-snug text-white/60">
                F1 macro
                <br />
                candidato F22 seed 14
              </span>
            </div>

            <ul className="mt-5 space-y-3" aria-label="F1 por clase">
              {F1_CLASES.map((f) => (
                <li
                  key={f.clase}
                  className="grid grid-cols-[108px_1fr_60px] items-center gap-3"
                >
                  <span className="flex items-center gap-2 text-[13px] text-white/80">
                    <span
                      className={`h-2 w-2 shrink-0 rounded-full ${f.fill}`}
                      aria-hidden="true"
                    />
                    {f.clase}
                  </span>
                  <span
                    className="h-1.5 overflow-hidden rounded-full bg-white/10"
                    aria-hidden="true"
                  >
                    <span
                      className={`block h-full rounded-full ${f.fill}`}
                      style={{ width: `${f.pct}%` }}
                    />
                  </span>
                  <span className="text-right font-mono text-[12px] tabular-nums text-white/90">
                    {f.valor}
                  </span>
                </li>
              ))}
            </ul>

            <p className="mt-4 text-xs leading-relaxed text-white/50">
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

/* El descargo crítico (no dispositivo médico) vive aparte, en el banner.
   El resto se agrupa por tipo: alcance técnico vs. corpus y población. */
const GRUPOS_LIMITACIONES = [
  {
    titulo: "Alcance técnico",
    items: [
      {
        icono: Timer,
        titulo: "Clasifica tramos de ritmo sostenido",
        detalle: "Ventanas de ~10 s, no latido a latido.",
      },
      {
        icono: Activity,
        titulo: "ECG superficiales de 12 (o 9) derivaciones",
        detalle:
          "Diagnostica ritmos eléctricos, no patologías estructurales del corazón; excluye electrogramas intracardíacos.",
      },
      {
        icono: Waves,
        titulo: "Ritmos irregulares fuera de alcance",
        detalle:
          "La fibrilación auricular, por ejemplo, se reporta como «Otro».",
      },
    ],
  },
  {
    titulo: "Corpus y población",
    items: [
      {
        icono: Users,
        titulo: "Población de desarrollo",
        detalle:
          "Niños de 0 a 14 años hospitalizados (corpus ZZU pECG); no es extrapolable a otros contextos sin validación.",
      },
      {
        icono: Database,
        titulo: "Soporte escaso en VT y Paced",
        detalle:
          "92 y 22 registros en el corpus, respectivamente.",
      },
    ],
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

        <div className="mt-10 flex items-start gap-4 rounded-2xl border border-brand/25 bg-pds-soft/60 p-6">
          <ShieldAlert
            className="mt-0.5 h-5 w-5 shrink-0 text-brand"
            aria-hidden="true"
          />
          <div>
            <p className="text-[15px] font-semibold text-neutral-900">
              No es un dispositivo médico certificado
            </p>
            <p className="mt-1 text-sm leading-relaxed text-neutral-600">
              Uso limitado a investigación, docencia y demostración
              retrospectiva.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {GRUPOS_LIMITACIONES.map((g) => (
            <div
              key={g.titulo}
              className="rounded-2xl border border-border/70 bg-white p-6"
            >
              <h3 className="text-[12px] font-bold uppercase tracking-[0.1em] text-neutral-500">
                {g.titulo}
              </h3>
              <ul className="mt-2 divide-y divide-border/60">
                {g.items.map((it) => (
                  <li
                    key={it.titulo}
                    className="flex gap-3 py-4 first:pt-3 last:pb-0"
                  >
                    <it.icono
                      className="mt-0.5 h-4 w-4 shrink-0 text-brand"
                      aria-hidden="true"
                    />
                    <div>
                      <p className="text-[14px] font-semibold text-neutral-900">
                        {it.titulo}
                      </p>
                      <p className="mt-1 text-[13px] leading-relaxed text-neutral-600">
                        {it.detalle}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------
   Recursos del proyecto
   ------------------------------------------------------------ */

const RECURSOS: {
  icono: LucideIcon;
  titulo: string;
  texto: string;
  href: string;
  stats?: string[];
}[] = [
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
    stats: ["14.190 ECG", "11.643 niños", "0–14 años"],
    texto: "Corpus pediátrico publicado en Scientific Data 12:867 (2025), con licencia CC BY 4.0.",
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
                className="group flex flex-col rounded-2xl border border-border/70 bg-white p-6 transition-[border-color,box-shadow] hover:border-brand/40 hover:shadow-md"
              >
                <span className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand transition-colors group-hover:bg-brand/15">
                  <Icono className="h-5 w-5" aria-hidden />
                </span>
                <h3 className="flex items-center gap-1.5 text-sm font-semibold text-neutral-900">
                  {r.titulo}
                  <ExternalLink
                    className="h-3.5 w-3.5 text-neutral-400 transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </h3>
                {r.stats ? (
                  <ul
                    className="mt-3 flex flex-wrap gap-1.5"
                    aria-label={`Datos de ${r.titulo}`}
                  >
                    {r.stats.map((s) => (
                      <li
                        key={s}
                        className="rounded-md border border-border/60 bg-neutral-50 px-2 py-1 font-mono text-[11px] leading-none text-neutral-500"
                      >
                        {s}
                      </li>
                    ))}
                  </ul>
                ) : null}
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
