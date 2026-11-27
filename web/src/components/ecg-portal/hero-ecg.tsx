import {
  Activity,
  BrainCircuit,
  Database,
  FileText,
  Github,
  GraduationCap,
  Play,
  Server,
  Grid2x2,
} from "lucide-react";

import { EcgMockup } from "./ecg-mockup";

const REPO_URL =
  "https://github.com/not-narleeek/Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG";

const NAV_ITEMS = [
  { href: "#pipeline", label: "Pipeline" },
  { href: "#analizar", label: "Analizar ECG" },
  { href: "#guia", label: "Guía" },
  { href: "#modelo", label: "Modelo F22" },
  { href: "#limitaciones", label: "Limitaciones" },
];

const PARTNERS = [
  { name: "UDP Ingeniería", icon: GraduationCap },
  { name: "ZZU pECG", icon: Database },
  { name: "PhysioNet", icon: Activity },
  { name: "WFDB", icon: FileText },
  { name: "scikit-learn", icon: BrainCircuit },
  { name: "NumPy", icon: Grid2x2 },
  { name: "Vast.ai", icon: Server },
];

export function SiteHeaderEcg() {
  return (
    <header className="relative z-30">
      <div className="flex h-16 items-center px-5 lg:px-8">
        <a
          href="#inicio"
          className="flex items-center gap-2 text-white"
          aria-label="ECG Pediátrico · inicio"
        >
          <span className="flex h-12 w-12 items-center justify-center">
            <img
              src="/images/logo-proyecto-blanco.svg"
              alt=""
              className="h-full w-full"
              aria-hidden="true"
            />
          </span>
          <span className="text-[19px] font-bold tracking-tight">
            ECG Pediátrico
          </span>
        </a>
        <nav aria-label="Principal" className="ml-10 hidden md:block">
          <ul className="flex items-center gap-8">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  className="text-[12.5px] font-semibold uppercase tracking-[0.08em] text-white/85 transition-colors hover:text-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="flex h-9 items-center gap-2 whitespace-nowrap rounded-lg border border-white/25 bg-white/10 px-4 text-[13.5px] font-medium text-white transition-colors hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <Github className="h-4 w-4" aria-hidden="true" />
            GitHub
          </a>
          <a
            href="#analizar"
            className="flex h-9 items-center whitespace-nowrap rounded-lg bg-white px-4 text-[13.5px] font-semibold text-neutral-900 transition-colors hover:bg-neutral-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            Analizar ahora
          </a>
        </div>
      </div>
    </header>
  );
}

function PartnerLogo({
  name,
  icon: Icon,
  dim,
}: {
  name: string;
  icon: typeof Activity;
  dim?: boolean;
}) {
  return (
    <span
      className={`flex shrink-0 items-center gap-2 text-white transition-opacity ${
        dim ? "opacity-60" : "opacity-90"
      } hover:opacity-100`}
    >
      <Icon className="h-[18px] w-[18px]" strokeWidth={2.4} aria-hidden="true" />
      <span className="text-[17px] font-bold tracking-tight">{name}</span>
    </span>
  );
}

function LogoMarquee() {
  return (
    <div
      className="overflow-hidden"
      style={{
        maskImage:
          "linear-gradient(to right, transparent, black 8%, black 92%, transparent)",
        WebkitMaskImage:
          "linear-gradient(to right, transparent, black 8%, black 92%, transparent)",
      }}
    >
      <div className="animate-marquee flex w-max items-center gap-16 pr-16">
        {[0, 1].map((copy) => (
          <div
            key={copy}
            className="flex items-center gap-16"
            aria-hidden={copy === 1}
          >
            {PARTNERS.map((p, i) => (
              <PartnerLogo key={`${p.name}-${copy}`} {...p} dim={i % 3 === 1} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function Cloud({
  className,
  style,
}: {
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <svg
      viewBox="0 0 240 130"
      fill="none"
      aria-hidden="true"
      focusable="false"
      className={className}
      style={style}
    >
      <g fill="#ffffff" filter="url(#ecg-cloud-soft)">
        <ellipse cx="120" cy="90" rx="82" ry="22" />
        <ellipse cx="72" cy="64" rx="36" ry="26" />
        <ellipse cx="116" cy="48" rx="46" ry="34" />
        <ellipse cx="164" cy="66" rx="34" ry="24" />
        <ellipse cx="142" cy="78" rx="44" ry="26" />
      </g>
    </svg>
  );
}

const HERO_CLOUDS: {
  className: string;
  duration: string;
  delay: string;
  flip?: boolean;
}[] = [
  {
    className: "left-[1.5%] top-[9%] w-[210px] opacity-50 sm:w-[240px]",
    duration: "34s",
    delay: "-6s",
  },
  {
    className: "right-[2%] top-[6%] w-[180px] opacity-45 sm:w-[210px]",
    duration: "28s",
    delay: "-14s",
    flip: true,
  },
  {
    className: "left-[30%] top-[5%] hidden w-[130px] opacity-30 md:block",
    duration: "40s",
    delay: "-22s",
    flip: true,
  },
  {
    className: "right-[20%] top-[24%] w-[150px] opacity-25",
    duration: "26s",
    delay: "-9s",
  },
  {
    className: "left-[12%] top-[33%] w-[160px] opacity-30",
    duration: "31s",
    delay: "-18s",
    flip: true,
  },
];

function HeroClouds() {
  return (
    <div
      className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
      aria-hidden="true"
    >
      {/* filtro de desenfoque compartido por todas las nubes */}
      <svg width="0" height="0" aria-hidden="true" focusable="false">
        <defs>
          <filter
            id="ecg-cloud-soft"
            x="-30%"
            y="-30%"
            width="160%"
            height="160%"
          >
            <feGaussianBlur stdDeviation="4" />
          </filter>
        </defs>
      </svg>
      {HERO_CLOUDS.map((cloud, i) => (
        <Cloud
          key={i}
          className={`absolute animate-cloud-drift ${
            cloud.flip ? "-scale-x-100 " : ""
          }${cloud.className}`}
          style={{
            animationDuration: cloud.duration,
            animationDelay: cloud.delay,
          }}
        />
      ))}
    </div>
  );
}

export function HeroEcg() {
  return (
    <section id="inicio" className="relative isolate bg-brand">
      <HeroClouds />
      <SiteHeaderEcg />

      {/* copia del hero */}
      <div className="px-6 pt-14 text-center lg:pt-16">
        <h1 className="mx-auto mt-7 max-w-3xl font-display text-[46px] leading-[1.02] tracking-[0.005em] text-white sm:text-[58px] lg:text-[64px]">
          Detección de arritmias
          <br />
          en pacientes pediátricos
        </h1>
        <p className="mx-auto mt-5 max-w-lg text-[13.5px] leading-relaxed text-white/80 lg:text-sm">
          Cargue una señal de 10 segundos y reciba una{" "}
          <strong className="font-semibold text-white">
            sugerencia de ritmo con porcentaje de certeza
          </strong>
          , pensada para apoyar —no reemplazar— la evaluación del profesional de
          la salud.
        </p>
        <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
          <a
            href="#analizar"
            className="flex h-10 items-center whitespace-nowrap rounded-lg bg-neutral-950 px-5 text-[13px] font-semibold text-white transition-colors hover:bg-neutral-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            Analizar un ECG
          </a>
          <a
            href="#pipeline"
            className="group flex h-10 items-center gap-2.5 whitespace-nowrap rounded-lg px-3 text-[13px] font-medium text-white/90 transition-colors hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full border border-white/40 bg-white/10 transition-colors group-hover:bg-white/25">
              <Play
                className="ml-px h-2.5 w-2.5 fill-white text-white"
                aria-hidden="true"
              />
            </span>
            Ver cómo funciona
          </a>
        </div>
      </div>

      {/* mockup del producto sobrepuesto a la pradera */}
      <div className="relative z-20 mt-12 px-5">
        <EcgMockup />
      </div>

      {/* franja de pradera con logos */}
      <div className="relative z-10 -mt-[104px]">
        <div className="relative h-[340px] overflow-hidden lg:h-[400px]">
          <img
            src="/images/grass-hero.png"
            alt="Colinas de pasto verde con flores rosadas"
            className="absolute inset-0 h-full w-full object-cover"
            style={{ objectPosition: "center 62%" }}
          />
          <div className="blend-sky absolute inset-0" aria-hidden="true" />
          <div
            className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-b from-transparent to-black/15"
            aria-hidden="true"
          />
          {/* logos del ecosistema */}
          <div className="absolute inset-x-0 bottom-7 z-10">
            <LogoMarquee />
          </div>
        </div>
      </div>
    </section>
  );
}
