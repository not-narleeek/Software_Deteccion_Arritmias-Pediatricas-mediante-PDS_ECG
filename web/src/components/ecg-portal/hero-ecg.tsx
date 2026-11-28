import { Github, Play } from "lucide-react";

import { EcgMockup } from "./ecg-mockup";
import { PillBadge } from "./sections";

const REPO_URL =
  "https://github.com/not-narleeek/Software_Deteccion_Arritmias-Pediatricas-mediante-PDS_ECG";

const NAV_ITEMS = [
  { href: "#pipeline", label: "Pipeline" },
  { href: "#analizar", label: "Analizar ECG" },
  { href: "#guia", label: "Guía" },
  { href: "#modelo", label: "Modelo F22" },
  { href: "#limitaciones", label: "Limitaciones" },
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

export function HeroEcg() {
  return (
    <section id="inicio" className="relative isolate overflow-hidden bg-brand">
      {/* foto de cielo continua como fondo del hero, fundida al azul de marca */}
      <div className="absolute inset-0 -z-10" aria-hidden="true">
        <img
          src="/images/sky-hero.jpg"
          alt=""
          className="h-full w-full object-cover"
          style={{ objectPosition: "center bottom" }}
        />
        <div className="blend-sky absolute inset-0" />
      </div>

      <SiteHeaderEcg />

      {/* copia del hero */}
      <div className="px-6 pt-12 text-center lg:pt-14">
        <PillBadge tone="dark" label="Demo académica · UDP 2026" />
        <h1 className="mx-auto mt-6 max-w-4xl font-display text-[52px] leading-[1.0] tracking-[0.005em] text-white sm:text-[68px] lg:text-[76px]">
          Detección de arritmias
          <br />
          en pacientes pediátricos
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-[15px] leading-relaxed text-white/85 lg:text-base">
          Cargue una señal de 10 segundos y reciba una{" "}
          <strong className="font-semibold text-white">
            sugerencia de ritmo con porcentaje de certeza
          </strong>
          , pensada para apoyar —no reemplazar— la evaluación del profesional de
          la salud.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3.5">
          <a
            href="#analizar"
            className="flex h-12 items-center whitespace-nowrap rounded-lg bg-neutral-950 px-6 text-[14px] font-semibold text-white transition-colors hover:bg-neutral-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            Analizar un ECG
          </a>
          <a
            href="#pipeline"
            className="group flex h-12 items-center gap-2.5 whitespace-nowrap rounded-lg px-3 text-[14px] font-medium text-white/90 transition-colors hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full border border-white/40 bg-white/10 transition-colors group-hover:bg-white/25">
              <Play
                className="ml-px h-3 w-3 fill-white text-white"
                aria-hidden="true"
              />
            </span>
            Ver cómo funciona
          </a>
        </div>
        <ul
          className="mt-6 flex flex-wrap items-center justify-center gap-2.5"
          aria-label="Características de la demo"
        >
          {["Corre en el navegador", "Sin registro", "WFDB · 10 s · 500 Hz"].map(
            (c) => (
              <li
                key={c}
                className="rounded-full border border-white/20 bg-white/10 px-3.5 py-1.5 text-[12.5px] font-medium text-white/85"
              >
                {c}
              </li>
            ),
          )}
        </ul>
      </div>

      {/* mockup del producto sobrepuesto al cielo */}
      <div className="relative z-20 mt-12 px-5">
        <EcgMockup />
      </div>

      {/* respiro bajo el mockup: deja ver la capa de nubes */}
      <div className="h-[236px] lg:h-[296px]" />
    </section>
  );
}
