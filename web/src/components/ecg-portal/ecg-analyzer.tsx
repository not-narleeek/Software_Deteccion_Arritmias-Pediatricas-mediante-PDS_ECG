"use client";

import { useEffect, useRef, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Activity,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  FileText,
  House,
  Play,
  Search,
  UploadCloud,
  Waves,
  X,
} from "lucide-react";
import { leerRegistro, elegirLead, type RegistroWfdb } from "@/lib/ecg/wfdb";
import {
  detectarPicos,
  rrDesdePicos,
  anchoQRSmedio,
  hayEspiculas,
  metricas,
  clasificar,
  generarReporte,
  COLOR_CLASE,
  CLASES_BARRA,
  RANGO_EDAD,
  fmt,
  type ClaveEdad,
  type ContextoClasificacion,
  type ResultadoClasificacion,
} from "@/lib/ecg/signal";
import { DEMOS, generarDemoWfdb, type TipoDemo } from "@/lib/ecg/demos";
import { EcgCanvas } from "./ecg-canvas";
import { ResultadoPanel } from "./resultado-panel";

/* ============================================================
   Analizador de ECG con la visual de la aplicación del
   proyecto: barra superior (logo, búsqueda, ruta, formato
   WFDB), barra lateral «Estudio», lienzo de la señal con
   picos R marcados y tarjeta de clasificación con certeza.
   Carga de registros WFDB (.hea + .dat) o casos demo,
   detección de picos R, métricas RR y clasificador
   heurístico. Todo en el navegador: ningún dato del
   paciente sale del equipo.
   ============================================================ */

const MAX_SEG = 10; // segundos analizados (ventana del proyecto)

interface EstadoSenal {
  senal: Float32Array;
  fs: number;
  picos: number[];
  rr: number[];
  fuente: string;
  registroNombre: string;
  derivacion: string;
  aviso: string;
}

type Vista = "registros" | "senal" | "reporte";

const OPCIONES_EDAD: ClaveEdad[] = [
  "desconocida",
  "lactante",
  "preescolar",
  "escolarMenor",
  "escolarMayor",
  "adolescente",
];

/* colores del sello por clase (tarjeta de clasificación) */
const SELLO: Record<string, string> = {
  Sinusal: "text-emerald-600",
  SVT: "text-amber-600",
  VT: "text-red-600",
  Paced: "text-violet-600",
  Otro: "text-slate-600",
};

const SELLO_CAB: Record<string, string> = {
  Sinusal: "bg-emerald-50 text-emerald-600",
  SVT: "bg-amber-50 text-amber-600",
  VT: "bg-red-50 text-red-600",
  Paced: "bg-violet-50 text-violet-600",
  Otro: "bg-slate-100 text-slate-600",
};

export function EcgAnalyzer() {
  const [estado, setEstado] = useState<EstadoSenal | null>(null);
  const [edad, setEdad] = useState<ClaveEdad>("desconocida");
  const [resultado, setResultado] = useState<{
    res: ResultadoClasificacion;
    ctx: ContextoClasificacion;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [vista, setVista] = useState<Vista>("registros");
  const [consulta, setConsulta] = useState("");

  const inputArchivoRef = useRef<HTMLInputElement | null>(null);
  const busquedaRef = useRef<HTMLInputElement | null>(null);
  const ventanaRef = useRef<HTMLDivElement | null>(null);

  /* ---------- vista efectiva según el estado disponible ---------- */
  const vistaEfectiva: Vista =
    vista === "reporte" && resultado
      ? "reporte"
      : vista === "reporte" && estado
        ? "senal"
        : vista === "senal" && estado
          ? "senal"
          : "registros";

  const duracion = estado ? estado.senal.length / estado.fs : 0;

  /* ---------- flujo interno ---------- */
  const mostrarRegistro = (registro: RegistroWfdb, fuente: string) => {
    const lead = elegirLead(registro.leads);
    const fs = lead.fs;
    const maxN = Math.round(MAX_SEG * fs);
    let senal: Float32Array = lead.senal;
    let aviso = "";
    if (senal.length > maxN) {
      senal = senal.subarray(0, maxN);
      aviso = "Se analizó solo el primer tramo de 10 segundos.";
    } else if (senal.length < maxN) {
      aviso = "Registro más corto que 10 s: revise el resultado con cautela.";
    }
    const picos = detectarPicos(senal, fs);
    const rr = rrDesdePicos(picos, fs);
    setEstado({
      senal: Float32Array.from(senal),
      fs,
      picos,
      rr,
      fuente,
      registroNombre: registro.nombre,
      derivacion: lead.nombre,
      aviso,
    });
    setResultado(null);
    setError(null);
    setVista("senal");
  };

  useEffect(() => {
    if (estado) {
      ventanaRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [estado]);

  useEffect(() => {
    if (vistaEfectiva === "reporte") {
      ventanaRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [vistaEfectiva]);

  /* atajo ⌘K / Ctrl+K para la búsqueda de la barra superior */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        busquedaRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const cargarDemo = (nombre: TipoDemo) => {
    try {
      const { hea, dat } = generarDemoWfdb(nombre);
      const registro = leerRegistro(hea, () => dat);
      const info = DEMOS.find((d) => d.id === nombre);
      mostrarRegistro(
        registro,
        `Caso de demostración — ${info ? info.nombre : nombre}`,
      );
    } catch (e) {
      setError(
        `No se pudo cargar el caso demo: ${e instanceof Error ? e.message : String(e)}`,
      );
    }
  };

  const leerArchivos = async (archivos: FileList | null) => {
    const lista = Array.from(archivos ?? []);
    const hea = lista.find((f) => /\.hea$/i.test(f.name));
    if (!hea) {
      setError(
        "Seleccione el archivo .hea del registro WFDB junto con su .dat (formato del proyecto, como ZZU pECG).",
      );
      return;
    }
    try {
      const textoHeader = await hea.text();
      const buffers = new Map<string, ArrayBuffer>();
      for (const f of lista.filter((f) => /\.dat$/i.test(f.name))) {
        buffers.set(f.name.toLowerCase(), await f.arrayBuffer());
      }
      const registro = leerRegistro(textoHeader, (nombre) =>
        buffers.get(nombre.toLowerCase()),
      );
      mostrarRegistro(registro, `Registro WFDB: ${hea.name.replace(/\.hea$/i, "")}`);
    } catch (e) {
      setError(
        `No se pudo leer el registro: ${e instanceof Error ? e.message : String(e)}`,
      );
    }
  };

  const limpiar = () => {
    setEstado(null);
    setResultado(null);
    setError(null);
    setVista("registros");
    if (inputArchivoRef.current) inputArchivoRef.current.value = "";
  };

  const computar = () => {
    if (!estado) return null;
    const met = metricas(estado.rr);
    const ctx: ContextoClasificacion = {
      ...met,
      anchoQRS: anchoQRSmedio(estado.senal, estado.fs, estado.picos),
      espiculas: hayEspiculas(estado.senal, estado.fs, estado.picos),
      edad,
    };
    return { res: clasificar(ctx), ctx };
  };

  const analizar = () => {
    const r = computar();
    if (r) setResultado(r);
  };

  const descargarReporteDe = (r: {
    res: ResultadoClasificacion;
    ctx: ContextoClasificacion;
  }) => {
    if (!estado) return;
    const contenido = generarReporte(
      r.res,
      r.ctx,
      estado.fuente,
      edad,
      new Date().toLocaleString("es-CL"),
    );
    const blob = new Blob([contenido], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "reporte_ecg_demo.txt";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
  };

  const exportar = () => {
    const r = resultado ?? computar();
    if (!r) return;
    if (!resultado) setResultado(r);
    descargarReporteDe(r);
  };

  const irAReporte = () => {
    if (!resultado) {
      const r = computar();
      if (!r) return;
      setResultado(r);
    }
    setVista("reporte");
  };

  /* ---------- elementos de la barra lateral ---------- */
  const navegacion: {
    id: Vista;
    label: string;
    icon: typeof House;
    deshabilitado: boolean;
  }[] = [
    { id: "registros", label: "Registros", icon: House, deshabilitado: false },
    {
      id: "senal",
      label: estado ? estado.derivacion : "Derivación II",
      icon: Activity,
      deshabilitado: !estado,
    },
    {
      id: "reporte",
      label: "Reporte",
      icon: FileText,
      deshabilitado: !estado,
    },
  ];

  const itemNav = (
    item: (typeof navegacion)[number],
    compacto: boolean,
  ) => {
    const activo = vistaEfectiva === item.id;
    return (
      <button
        key={item.id}
        type="button"
        disabled={item.deshabilitado}
        aria-current={activo ? "page" : undefined}
        onClick={() => setVista(item.id)}
        className={`flex ${compacto ? "flex-1" : "w-full"} items-center gap-2 rounded-md px-2 py-1.5 text-[11px] transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
          activo
            ? "bg-brand/10 font-semibold text-brand"
            : "font-medium text-neutral-500 hover:bg-neutral-50 hover:text-neutral-800 disabled:hover:bg-transparent"
        }`}
      >
        <item.icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span className="truncate">{item.label}</span>
      </button>
    );
  };

  const selectorEdad = (id: string) => (
    <Select value={edad} onValueChange={(v) => setEdad(v as ClaveEdad)}>
      <SelectTrigger id={id} aria-label="Edad del paciente" className="h-7 w-full gap-1 text-[11px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {OPCIONES_EDAD.map((o) => (
          <SelectItem key={o} value={o} className="text-[12px]">
            {RANGO_EDAD[o].label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  /* ---------- campo de búsqueda compartido ---------- */
  const demosFiltradas = DEMOS.filter((d) =>
    `${d.nombre} ${d.descripcion}`.toLowerCase().includes(consulta.trim().toLowerCase()),
  );

  const campoBusqueda = (ref: typeof busquedaRef, conKbd: boolean) => (
    <div className="flex h-7 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-2 focus-within:border-brand/50">
      <Search className="h-3 w-3 shrink-0 text-neutral-400" aria-hidden="true" />
      <input
        ref={ref}
        type="search"
        value={consulta}
        onChange={(e) => setConsulta(e.target.value)}
        placeholder="Buscar..."
        aria-label="Buscar casos de demostración"
        className="w-full bg-transparent text-[10.5px] text-neutral-700 placeholder:text-neutral-400 focus:outline-none"
      />
      {conKbd ? (
        <kbd className="rounded border border-neutral-200 bg-neutral-50 px-1 text-[8px] font-medium text-neutral-400">
          K
        </kbd>
      ) : null}
    </div>
  );

  return (
    <div className="space-y-3">
      <div
        ref={ventanaRef}
        className="scroll-mt-24 overflow-hidden rounded-xl bg-white text-neutral-800 ring-1 ring-black/10"
      >
        {/* barra superior */}
        <div className="flex h-12 items-center gap-2.5 border-b border-neutral-100 bg-white px-3 sm:gap-3 sm:px-4">
          <span className="flex items-center gap-1.5">
            <img
              src="/images/logo-proyecto.svg"
              alt=""
              className="h-6 w-6 shrink-0 rounded-md"
              aria-hidden="true"
            />
            <span className="hidden text-[13px] font-semibold tracking-tight text-neutral-900 sm:block">
              ECG Pediátrico
            </span>
          </span>
          <span className="hidden h-4 w-px bg-neutral-200 md:block" aria-hidden="true" />
          <div className="hidden h-7 w-full max-w-[220px] items-center rounded-md bg-neutral-100 px-2 md:flex">
            <div className="flex w-full items-center gap-1.5 text-neutral-400">
              <Search className="h-3 w-3 shrink-0" aria-hidden="true" />
              <input
                ref={busquedaRef}
                type="search"
                value={consulta}
                onChange={(e) => setConsulta(e.target.value)}
                placeholder="Buscar registro..."
                aria-label="Buscar registro"
                className="w-full bg-transparent text-[11px] text-neutral-700 placeholder:text-neutral-400 focus:outline-none"
              />
            </div>
          </div>
          <span className="hidden h-4 w-px bg-neutral-200 lg:block" aria-hidden="true" />
          <span
            className="hidden min-w-0 items-center gap-1 truncate text-[11px] text-neutral-400 lg:flex"
            aria-label="Ruta del registro"
          >
            Pacientes
            <span className="text-neutral-300" aria-hidden="true">/</span>
            <span className="truncate">{estado ? estado.registroNombre : "—"}</span>
            <span className="text-neutral-300" aria-hidden="true">/</span>
            <span className="truncate font-medium text-neutral-800">
              {estado ? estado.derivacion : "—"}
            </span>
          </span>
          <span className="ml-auto flex shrink-0 items-center gap-2">
            <span className="hidden items-center gap-1.5 rounded-md border border-neutral-200 px-2 py-1 text-[10px] font-medium text-neutral-600 sm:flex">
              <Waves className="h-3 w-3 text-neutral-500" aria-hidden="true" />
              WFDB
              {estado
                ? ` · ${fmt(estado.fs, 0)} Hz · ${fmt(duracion, 1)} s`
                : " · 500 Hz · 10 s"}
            </span>
            <span
              className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-teal-400 to-emerald-300 text-[10px] font-bold text-white"
              aria-hidden="true"
            >
              P
            </span>
            <ChevronDown className="hidden h-3 w-3 text-neutral-400 sm:block" aria-hidden="true" />
          </span>
        </div>

        <div className="flex min-h-[460px] flex-col md:flex-row">
          {/* barra lateral (escritorio) */}
          <aside className="hidden w-[178px] shrink-0 flex-col border-r border-neutral-100 bg-white p-2.5 md:flex">
            {campoBusqueda(busquedaRef, true)}
            <p className="mt-4 px-1 text-[8.5px] font-semibold uppercase tracking-[0.16em] text-neutral-400">
              Estudio
            </p>
            <nav
              className="mt-1.5 flex flex-col gap-0.5"
              aria-label="Vistas del analizador"
            >
              {navegacion.map((item) => itemNav(item, false))}
            </nav>
            <p className="mt-5 px-1 text-[8.5px] font-semibold uppercase tracking-[0.16em] text-neutral-400">
              Paciente
            </p>
            <div className="mt-1.5">{selectorEdad("edad-sidebar")}</div>
            <p className="mt-1.5 px-1 text-[9px] leading-snug text-neutral-400">
              La edad ajusta los rangos de FC normales en pediatría al clasificar.
            </p>
            <div className="mt-auto flex items-center gap-1.5 rounded-md bg-neutral-50 px-2 py-1.5 text-[9px] font-medium text-neutral-400">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" aria-hidden="true" />
              Procesamiento 100 % local
            </div>
          </aside>

          {/* pestañas (móvil) */}
          <div
            className="flex items-center gap-1 border-b border-neutral-100 bg-white px-2 py-1.5 md:hidden"
            role="tablist"
            aria-label="Vistas del analizador"
          >
            {navegacion.map((item) => itemNav(item, true))}
          </div>

          {/* área principal */}
          <div className="relative min-w-0 flex-1 bg-[#F7F8FB] bg-dots-dark">
            {error ? (
              <div
                role="alert"
                className="mx-3 mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[11.5px] leading-snug text-red-800 sm:mx-4"
              >
                <CircleAlert className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span className="flex-1">{error}</span>
                <button
                  type="button"
                  onClick={() => setError(null)}
                  aria-label="Descartar aviso"
                  className="shrink-0 rounded p-0.5 text-red-400 transition-colors hover:bg-red-100 hover:text-red-600"
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            ) : null}

            {/* ======== vista Registros: carga de la señal ======== */}
            {vistaEfectiva === "registros" ? (
              <div className="px-3 py-4 pb-10 sm:px-4 sm:py-5">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-[14px] font-semibold text-neutral-900">
                    Cargar registro
                  </h3>
                  <span className="rounded border border-pink-300 bg-pink-50 px-1.5 py-px text-[9px] font-bold tracking-[0.08em] text-pink-600">
                    WFDB
                  </span>
                  <span className="ml-auto hidden text-[10.5px] text-neutral-400 sm:block">
                    Nada se envía a un servidor
                  </span>
                </div>
                <p className="mt-1 text-[11.5px] text-neutral-500">
                  Casos de demostración o su propio registro .hea + .dat (corpus ZZU pECG).
                </p>

                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                  {/* casos de demostración */}
                  <div className="rounded-lg border border-neutral-200/80 bg-white shadow-sm">
                    <p className="border-b border-neutral-100 px-3 py-2 text-[9.5px] font-semibold uppercase tracking-[0.14em] text-neutral-400">
                      Casos de demostración · 10 s @ 500 Hz
                    </p>
                    <div className="p-1.5" role="group" aria-label="Casos de demostración">
                      {demosFiltradas.length ? (
                        demosFiltradas.map((d) => (
                          <button
                            key={d.id}
                            type="button"
                            onClick={() => cargarDemo(d.id)}
                            className="group flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors hover:bg-brand/5"
                          >
                            <span
                              className={`h-2 w-2 shrink-0 rounded-full ${d.dot}`}
                              aria-hidden="true"
                            />
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-[12.5px] font-semibold text-neutral-800">
                                {d.nombre}
                              </span>
                              <span className="block truncate text-[11px] text-neutral-400">
                                {d.descripcion}
                              </span>
                            </span>
                            <ChevronRight
                              className="h-3.5 w-3.5 shrink-0 text-neutral-300 transition-colors group-hover:text-brand"
                              aria-hidden="true"
                            />
                          </button>
                        ))
                      ) : (
                        <p className="px-2.5 py-3 text-[11.5px] text-neutral-400">
                          Sin resultados para «{consulta}».
                        </p>
                      )}
                    </div>
                  </div>

                  {/* carga de archivos propios */}
                  <div className="flex flex-col gap-3">
                    <div
                      className={`rounded-lg border-2 border-dashed px-4 py-6 text-center shadow-sm transition-colors ${
                        arrastrando
                          ? "border-brand bg-brand/5"
                          : "border-neutral-200 bg-white"
                      }`}
                      onDragOver={(e) => {
                        e.preventDefault();
                        setArrastrando(true);
                      }}
                      onDragLeave={() => setArrastrando(false)}
                      onDrop={(e) => {
                        e.preventDefault();
                        setArrastrando(false);
                        if (e.dataTransfer.files && e.dataTransfer.files.length) {
                          void leerArchivos(e.dataTransfer.files);
                        }
                      }}
                    >
                      <UploadCloud
                        className="mx-auto mb-1.5 h-7 w-7 text-neutral-400"
                        aria-hidden="true"
                      />
                      <p className="text-[12px] text-neutral-500">
                        Arrastre aquí el registro (.hea y .dat) o{" "}
                        <button
                          type="button"
                          className="font-semibold text-brand underline underline-offset-2 hover:text-brand-deep"
                          onClick={() => inputArchivoRef.current?.click()}
                        >
                          selecciónelos
                        </button>
                      </p>
                      <input
                        ref={inputArchivoRef}
                        type="file"
                        accept=".hea,.dat"
                        multiple
                        hidden
                        aria-label="Seleccionar archivos WFDB"
                        onChange={(e) => {
                          if (e.target.files?.length) void leerArchivos(e.target.files);
                        }}
                      />
                    </div>
                    <p className="text-[10.5px] leading-relaxed text-neutral-400">
                      Formato <strong className="text-neutral-500">WFDB</strong>: el estándar
                      de PhysioNet usado por el proyecto (corpus ZZU pECG). Un registro se
                      compone del encabezado{" "}
                      <code className="rounded bg-neutral-100 px-1 text-neutral-600">.hea</code>{" "}
                      y las muestras{" "}
                      <code className="rounded bg-neutral-100 px-1 text-neutral-600">.dat</code>
                      ; no se aceptan CSV. Se analiza la derivación II del registro (o la
                      primera disponible) y la frecuencia de muestreo se lee del encabezado.
                    </p>
                    <div className="md:hidden">
                      <p className="mb-1 px-1 text-[9.5px] font-semibold uppercase tracking-[0.14em] text-neutral-400">
                        Paciente · edad
                      </p>
                      {selectorEdad("edad-movil")}
                    </div>
                  </div>
                </div>
              </div>
            ) : null}

            {/* ======== vista Señal: lienzo + clasificación ======== */}
            {vistaEfectiva === "senal" && estado ? (
              <div>
                <div className="flex flex-wrap items-center gap-2 px-3 pt-3 sm:px-4">
                  <button
                    type="button"
                    onClick={() => setVista("registros")}
                    aria-label="Volver a los registros"
                    className="-ml-1 rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
                  >
                    <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                  </button>
                  <h3 className="min-w-0 truncate text-[14px] font-semibold text-neutral-900">
                    Registro {estado.registroNombre} · {fmt(duracion, 1)} s
                  </h3>
                  <span className="rounded border border-pink-300 bg-pink-50 px-1.5 py-px text-[9px] font-bold tracking-[0.08em] text-pink-600">
                    {fmt(estado.fs, 0)} Hz
                  </span>
                  {estado.aviso ? (
                    <span
                      className="hidden max-w-[220px] truncate text-[10px] text-amber-600 md:block"
                      title={estado.aviso}
                    >
                      {estado.aviso}
                    </span>
                  ) : null}
                  <span className="ml-auto flex items-center gap-2.5">
                    <span className="hidden items-center gap-1.5 text-[11px] text-neutral-500 sm:flex">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
                      {estado.picos.length} picos R detectados
                    </span>
                    <button
                      type="button"
                      onClick={exportar}
                      className="flex h-8 items-center rounded-md bg-neutral-900 px-3 text-[11.5px] font-medium text-white transition-colors hover:bg-neutral-700"
                    >
                      Exportar
                    </button>
                    <button
                      type="button"
                      onClick={irAReporte}
                      className="flex h-8 items-center rounded-md border border-neutral-200 bg-white px-3 text-[11.5px] font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
                    >
                      Reporte
                    </button>
                  </span>
                </div>

                {/* lienzo con la señal y el chip RR */}
                <div className="relative px-3 pt-1 sm:px-4">
                  <EcgCanvas
                    senal={estado.senal}
                    fs={estado.fs}
                    picos={estado.picos}
                    altura={250}
                  />
                  {estado.rr.length > 0 && estado.picos.length > 1 ? (
                    <span
                      className="absolute top-[46px] z-10 flex -translate-x-1/2 items-center gap-1 rounded-full border border-neutral-200/80 bg-white px-2 py-0.5 text-[9.5px] font-semibold text-neutral-600 shadow-sm"
                      style={{
                        left: `${Math.min(85, Math.max(10, (estado.picos[1] / estado.senal.length) * 100))}%`,
                      }}
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-brand" aria-hidden="true" />
                      RR {fmt(estado.rr[0], 0)} ms
                    </span>
                  ) : null}

                  {/* tarjeta de clasificación */}
                  <div className="mt-3 w-full max-w-[280px] lg:absolute lg:right-6 lg:top-[54px] lg:mt-0 lg:w-[210px] lg:max-w-none">
                    {resultado ? (
                      <div className="overflow-hidden rounded-lg border border-neutral-200/80 bg-white shadow-md">
                        <div className="flex items-center gap-1.5 border-b border-neutral-100 px-3 py-2">
                          <span
                            className={`flex h-4 w-4 items-center justify-center rounded ${SELLO_CAB[resultado.res.clase]}`}
                          >
                            <Check className="h-2.5 w-2.5" strokeWidth={3} aria-hidden="true" />
                          </span>
                          <span className="text-[11px] font-semibold text-neutral-800">
                            Clasificación
                          </span>
                        </div>
                        <div className="px-3 py-2.5">
                          <div className="flex items-baseline justify-between gap-2">
                            <p className="text-[15px] font-bold tracking-tight text-neutral-900">
                              {resultado.res.clase}
                            </p>
                            <p
                              className={`text-[11px] font-semibold ${SELLO[resultado.res.clase]}`}
                            >
                              {fmt(Math.round(resultado.res.probs[resultado.res.clase] * 1000) / 10, 1)} %
                            </p>
                          </div>
                          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                CLASES_BARRA[COLOR_CLASE[resultado.res.clase]].fill
                              }`}
                              style={{
                                width: `${Math.round(resultado.res.probs[resultado.res.clase] * 100)}%`,
                              }}
                            />
                          </div>
                          <div className="mt-2 flex flex-wrap gap-1">
                            <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[8.5px] font-medium text-neutral-500">
                              QRS{" "}
                              {resultado.ctx.anchoQRS != null
                                ? `${fmt(resultado.ctx.anchoQRS, 0)} ms`
                                : "n/d"}
                            </span>
                            <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[8.5px] font-medium text-neutral-500">
                              FC {fmt(resultado.ctx.fc, 0)}
                            </span>
                            <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-[8.5px] font-medium text-neutral-500">
                              RR {fmt(resultado.ctx.rrMedio, 0)} ms
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center justify-between border-t border-neutral-100 px-3 py-1.5 text-[9px] text-neutral-400">
                          Salida calibrada
                          <span className="font-medium text-neutral-500">F22</span>
                        </div>
                      </div>
                    ) : (
                      <div className="rounded-lg border border-dashed border-neutral-200 bg-white/70 shadow-sm">
                        <div className="flex items-center gap-1.5 border-b border-neutral-100 px-3 py-2">
                          <span className="flex h-4 w-4 items-center justify-center rounded bg-neutral-100 text-neutral-400">
                            <Activity className="h-2.5 w-2.5" aria-hidden="true" />
                          </span>
                          <span className="text-[11px] font-semibold text-neutral-500">
                            Clasificación
                          </span>
                        </div>
                        <div className="px-3 py-2.5">
                          <p className="text-[12px] font-semibold text-neutral-500">
                            Aún sin clasificar
                          </p>
                          <p className="mt-0.5 text-[10px] leading-snug text-neutral-400">
                            Pulse «Analizar señal» para obtener el ritmo sugerido y su certeza.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* acciones */}
                <div className="flex flex-wrap items-center gap-2 px-3 pb-9 pt-3 sm:px-4">
                  <button
                    type="button"
                    onClick={analizar}
                    className="flex h-8 items-center gap-1.5 rounded-md bg-neutral-900 px-3 text-[11.5px] font-medium text-white transition-colors hover:bg-neutral-700"
                  >
                    <Play className="h-3 w-3 fill-white" aria-hidden="true" />
                    Analizar señal
                  </button>
                  <button
                    type="button"
                    onClick={limpiar}
                    className="flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-[11.5px] font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
                  >
                    <X className="h-3 w-3" aria-hidden="true" />
                    Limpiar
                  </button>
                  <p className="ml-auto hidden max-w-[300px] truncate text-[10px] text-neutral-400 sm:block">
                    {estado.fuente}
                  </p>
                </div>

                <span className="absolute bottom-2.5 left-3 flex items-center gap-1 text-[9px] font-medium text-neutral-400 sm:left-4">
                  <Check
                    className="h-2.5 w-2.5"
                    strokeWidth={3}
                    aria-hidden="true"
                  />
                  {resultado ? "Analizado en el navegador" : "Señal procesada en el navegador"}
                </span>
              </div>
            ) : null}

            {/* ======== vista Reporte ======== */}
            {vistaEfectiva === "reporte" && resultado ? (
              <div className="px-3 py-4 pb-10 sm:px-4 sm:py-5">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setVista("senal")}
                    aria-label="Volver a la señal"
                    className="-ml-1 rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
                  >
                    <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                  </button>
                  <h3 className="text-[14px] font-semibold text-neutral-900">
                    Reporte del análisis
                  </h3>
                  <span
                    className={`rounded border px-1.5 py-px text-[9px] font-bold tracking-[0.08em] ${
                      SELLO_CAB[resultado.res.clase]
                    }`}
                  >
                    {resultado.res.clase}
                  </span>
                </div>
                <div className="mt-3 rounded-lg border border-neutral-200/80 bg-white p-4 shadow-sm sm:p-5">
                  <ResultadoPanel
                    res={resultado.res}
                    ctx={resultado.ctx}
                    fuente={estado?.fuente ?? "—"}
                    edadClave={edad}
                    onOtro={limpiar}
                  />
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
