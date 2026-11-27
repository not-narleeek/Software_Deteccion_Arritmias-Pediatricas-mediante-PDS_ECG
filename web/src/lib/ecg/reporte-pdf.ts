/* ============================================================
   Reporte PDF del análisis — portal de demostración.
   Genera un documento A4 con logo del proyecto, datos del
   paciente, datos del ECG (métricas + trazo), desglose
   auditable del diagnóstico (reglas y puntajes del
   clasificador heurístico) y el diagnóstico final.
   Todo se genera en el navegador con jsPDF: ningún dato
   sale del equipo. No es un dispositivo médico.
   ============================================================ */

import type { jsPDF } from "jspdf";
import {
  CLASES,
  RANGO_EDAD,
  fmt,
  type Clase,
  type ClaveEdad,
  type ContextoClasificacion,
  type ResultadoClasificacion,
} from "./signal";

/** Metadatos del registro analizado que aparecen en el reporte. */
export interface MetadatosRegistro {
  /** Nombre del registro WFDB (archivo .hea). */
  nombre: string;
  /** Derivación analizada (p. ej. «II»). */
  derivacion: string;
  /** Frecuencia de muestreo en Hz. */
  fs: number;
  /** Duración analizada en segundos. */
  duracionS: number;
  /** Picos R detectados en el tramo. */
  nPicos: number;
  /** Intervalos RR válidos en el tramo. */
  nRR: number;
}

/** Datos completos que necesita el reporte PDF. */
export interface DatosReportePdf {
  res: ResultadoClasificacion;
  ctx: ContextoClasificacion;
  /** Origen del registro (caso demo o archivo del usuario). */
  fuente: string;
  edadClave: ClaveEdad;
  registro: MetadatosRegistro;
  /** Señal analizada: incluye el trazo en el PDF si se entrega. */
  senal?: ArrayLike<number>;
  picos?: number[];
  fechaStr: string;
}

/* ---------- constantes de estilo ---------- */

const PAGE_W = 210;
const PAGE_H = 297;
const MARGEN = 15;
const ANCHO = PAGE_W - 2 * MARGEN; // 180 mm de contenido
const PIE_Y = 283; // el pie ocupa desde esta línea hacia abajo

const COLOR_TEXTO = "#111827";
const COLOR_GRIS = "#6b7280";
const COLOR_GRIS_CLARO = "#9ca3af";
const COLOR_LINEA = "#e5e7eb";
const COLOR_MARCA = "#2156ef";

const COLOR_CLASE_PDF: Record<Clase, string> = {
  Sinusal: "#059669",
  SVT: "#d97706",
  VT: "#dc2626",
  Paced: "#7c3aed",
  Otro: "#64748b",
};

const NOMBRE_CLASE: Record<Clase, string> = {
  Sinusal: "Ritmo sinusal",
  SVT: "Taquicardia supraventricular (QRS estrecho)",
  VT: "Taquicardia ventricular (QRS ancho)",
  Paced: "Ritmo estimulado por marcapasos",
  Otro: "Ritmo no determinado (fuera del alcance del clasificador)",
};

/* jsPDF con fuentes estándar usa CP1252: los glifos fuera de esa
   página de código se sustituyen antes de dibujar. */
function limpiar(t: string): string {
  return t.replace(/\u2264/g, "<=").replace(/\u2265/g, ">=").replace(/\u2192/g, "->");
}

/* ---------- rasterización de imágenes (logo y trazo) ---------- */

/** Convierte el logo SVG del proyecto en un PNG de alta resolución. */
async function logoDataUrl(): Promise<string | null> {
  const { promise, resolve, reject } = Promise.withResolvers<void>();
  const img = new Image();
  img.onload = () => resolve();
  img.onerror = () => reject(new Error("No se pudo cargar el logo"));
  img.src = "/images/logo-proyecto.svg";
  try {
    await promise;
  } catch {
    return null;
  }
  const S = 576;
  const canvas = document.createElement("canvas");
  canvas.width = S;
  canvas.height = S;
  const g = canvas.getContext("2d");
  if (!g) return null;
  g.fillStyle = "#ffffff"; // fondo blanco: el JPEG no tiene alfa y el logo tiene esquinas redondeadas
  g.fillRect(0, 0, S, S);
  g.drawImage(img, 0, 0, S, S);
  return canvas.toDataURL("image/jpeg", 0.92);
}

/** Dibuja la señal con rejilla y picos R marcados; devuelve un PNG. */
function trazoDataUrl(senal: ArrayLike<number>, picos: number[]): string | null {
  const W = 1600;
  const H = 420;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const g = canvas.getContext("2d");
  if (!g) return null;

  g.fillStyle = "#ffffff";
  g.fillRect(0, 0, W, H);

  g.strokeStyle = "#e8eef7";
  g.lineWidth = 1;
  for (let x = 57; x < W; x += 57) {
    g.beginPath();
    g.moveTo(x + 0.5, 0);
    g.lineTo(x + 0.5, H);
    g.stroke();
  }
  for (let y = 57; y < H; y += 57) {
    g.beginPath();
    g.moveTo(0, y + 0.5);
    g.lineTo(W, y + 0.5);
    g.stroke();
  }

  /* escala robusta: percentiles 0,5–99,5 para no recortar los QRS */
  const orden = Array.from(senal).sort((a, b) => a - b);
  const p = (q: number) => orden[Math.min(orden.length - 1, Math.max(0, Math.round(q * (orden.length - 1))))] ?? 0;
  const lo = p(0.005);
  const hi = p(0.995);
  const centro = (lo + hi) / 2;
  const escala = (H * 0.3) / Math.max(1e-9, (hi - lo) / 2);
  const X = (i: number) => 10 + (i / Math.max(1, senal.length - 1)) * (W - 20);
  const Y = (v: number) => H / 2 - (v - centro) * escala;

  g.strokeStyle = COLOR_MARCA;
  g.lineWidth = 2.2;
  g.lineJoin = "round";
  g.beginPath();
  for (let i = 0; i < senal.length; i++) {
    const x = X(i);
    const y = Y(senal[i]);
    if (i === 0) g.moveTo(x, y);
    else g.lineTo(x, y);
  }
  g.stroke();

  g.fillStyle = "#ffffff";
  g.strokeStyle = "#dc2626";
  g.lineWidth = 2;
  for (const pc of picos) {
    if (pc < 0 || pc >= senal.length) continue;
    const ym = Math.min(H - 9, Math.max(9, Y(senal[pc])));
    g.beginPath();
    g.arc(X(pc), ym, 6, 0, 2 * Math.PI);
    g.fill();
    g.stroke();
  }

  return canvas.toDataURL("image/jpeg", 0.92);
}

/* ---------- armado del documento ---------- */

/**
 * Ensambla el PDF. Recibe la clase jsPDF (importación dinámica para
 * no cargar la librería hasta descargar) y las imágenes ya
 * rasterizadas (data URL PNG), de modo que el armado sea verificable
 * de forma aislada.
 */
export function armarPdf(
  JsPDF: typeof jsPDF,
  d: DatosReportePdf,
  logoPng: string | null,
  trazoPng: string | null,
): jsPDF {
  const doc = new JsPDF({ unit: "mm", format: "a4" });
  const rango = RANGO_EDAD[d.edadClave] || RANGO_EDAD.desconocida;
  const clase = d.res.clase;
  const color = COLOR_CLASE_PDF[clase];
  const certeza = Math.round(d.res.probs[clase] * 100);

  let y = 0;
  let pagina: number;

  const nuevoRenglon = (h: number) => {
    if (y + h > PIE_Y - 4) {
      doc.addPage();
      pagina = doc.getNumberOfPages();
      doc.setPage(pagina);
      y = 20;
      doc.setFont("helvetica", "normal");
      doc.setFontSize(8);
      doc.setTextColor(COLOR_GRIS);
      doc.text(
        limpiar("Reporte de análisis de ECG pediátrico — continuación"),
        MARGEN,
        14,
      );
      doc.setDrawColor(COLOR_LINEA);
      doc.setLineWidth(0.3);
      doc.line(MARGEN, 16, PAGE_W - MARGEN, 16);
      y = 22;
    }
  };

  const t = (
    texto: string,
    x: number,
    yy: number,
    size: number,
    estilo: "normal" | "bold" | "italic",
    color: string,
    anchoMax?: number,
  ): string[] => {
    doc.setFont("helvetica", estilo);
    doc.setFontSize(size);
    doc.setTextColor(color);
    const lineas = doc.splitTextToSize(limpiar(texto), anchoMax ?? ANCHO);
    doc.text(lineas, x, yy);
    return lineas;
  };

  const seccion = (titulo: string) => {
    nuevoRenglon(14);
    doc.setFillColor(COLOR_MARCA);
    doc.rect(MARGEN, y - 3.6, 1.6, 4.6, "F");
    t(titulo.toUpperCase(), MARGEN + 4, y, 10.5, "bold", COLOR_TEXTO);
    y += 6.5;
  };

  const kv = (pares: [string, string][], cols: number) => {
    const anchoCol = ANCHO / cols;
    const filas = Math.ceil(pares.length / cols);
    const altoFila = 10.5;
    nuevoRenglon(filas * altoFila + 3);
    pares.forEach(([et, val], i) => {
      const cx = MARGEN + (i % cols) * anchoCol;
      const cy = y + Math.floor(i / cols) * altoFila;
      t(et, cx, cy, 7.5, "normal", COLOR_GRIS);
      t(val, cx, cy + 4.4, 9.5, "bold", COLOR_TEXTO, anchoCol - 4);
    });
    y += filas * altoFila + 3;
  };

  /* formato de la imagen según el prefijo del data URL (PNG o JPEG) */
  const formato = (img: string) => (img.startsWith("data:image/jpeg") ? "JPEG" : "PNG");

  /* ===== cabecera (solo primera página) ===== */
  const anchoSello = 62;
  y = 14;
  if (logoPng) doc.addImage(logoPng, formato(logoPng), MARGEN, y, 21, 21);
  t(
    "Reporte de análisis de ECG pediátrico",
    MARGEN + 26,
    y + 6,
    12.5,
    "bold",
    COLOR_TEXTO,
    PAGE_W - MARGEN - anchoSello - (MARGEN + 26) - 4,
  );
  t(
    "Portal de demostración · Proyecto TICS-II-2026-ECG-PED · Universidad Diego Portales",
    MARGEN + 26,
    y + 11.5,
    8.5,
    "normal",
    COLOR_GRIS,
    PAGE_W - MARGEN - anchoSello - (MARGEN + 26) - 3,
  );
  doc.setDrawColor("#fca5a5");
  doc.setFillColor("#fef2f2");
  doc.rect(PAGE_W - MARGEN - anchoSello, y + 1, anchoSello, 6.4, "FD");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(7);
  doc.setTextColor("#dc2626");
  doc.text(
    limpiar("ACADÉMICO · NO CERTIFICADO"),
    PAGE_W - MARGEN - anchoSello / 2,
    y + 5,
    { align: "center" },
  );
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(COLOR_GRIS);
  doc.text(limpiar(`Generado: ${d.fechaStr}`), PAGE_W - MARGEN, y + 12, {
    align: "right",
  });
  doc.setTextColor(COLOR_GRIS_CLARO);
  doc.text("Procesamiento 100 % local en el navegador", PAGE_W - MARGEN, y + 15.5, {
    align: "right",
  });
  doc.setDrawColor(COLOR_LINEA);
  doc.setLineWidth(0.4);
  doc.line(MARGEN, y + 24, PAGE_W - MARGEN, y + 24);
  y += 31;

  /* ===== 1 · datos del paciente ===== */
  seccion("1. Datos del paciente");
  kv(
    [
      ["Grupo de edad indicado", rango.label],
      ["Rango FC de referencia (sinusal)", `${rango.lo}–${rango.hi} lpm`],
      ["Identificación", "No aplica — análisis anónimo"],
    ],
    3,
  );
  t(
    "El portal no recoge datos personales: el registro se procesa íntegramente en el navegador y ningún dato del paciente sale del equipo.",
    MARGEN,
    y,
    7.8,
    "italic",
    COLOR_GRIS_CLARO,
  );
  y += 8;

  /* ===== 2 · datos del ECG ===== */
  seccion("2. Datos del ECG");
  kv(
    [
      ["Registro", d.registro.nombre],
      ["Derivación analizada", d.registro.derivacion],
      ["Frecuencia de muestreo", `${fmt(d.registro.fs, 0)} Hz`],
      ["Duración analizada", `${fmt(d.registro.duracionS, 1)} s`],
      ["Picos R detectados", `${d.registro.nPicos}`],
      ["Intervalos RR válidos", `${d.registro.nRR}`],
    ],
    3,
  );
  t("Origen del registro", MARGEN, y, 7.5, "normal", COLOR_GRIS);
  t(d.fuente, MARGEN, y + 4.4, 9.5, "bold", COLOR_TEXTO, ANCHO - 4);
  y += 10;
  kv(
    [
      ["FC media", `${fmt(d.ctx.fc, 0)} lpm`],
      ["RR medio", `${fmt(d.ctx.rrMedio, 0)} ms`],
      ["SDNN", Number.isFinite(d.ctx.sdnn) ? `${fmt(d.ctx.sdnn, 0)} ms` : "—"],
      ["RMSSD", Number.isFinite(d.ctx.rmssd) ? `${fmt(d.ctx.rmssd, 0)} ms` : "—"],
      ["pNN50", Number.isFinite(d.ctx.pnn50) ? `${fmt(d.ctx.pnn50, 0)} %` : "—"],
      [
        "Regularidad (CV de RR)",
        `${fmt(d.ctx.cv, 3)}${d.ctx.cv <= 0.06 ? " (regular)" : d.ctx.cv <= 0.12 ? " (mod. irregular)" : " (irregular)"}`,
      ],
      [
        "Ancho QRS medio",
        d.ctx.anchoQRS != null ? `${fmt(d.ctx.anchoQRS, 0)} ms` : "No evaluable",
      ],
      [
        "Espículas de marcapasos",
        d.ctx.espiculas === true
          ? "Detectadas"
          : d.ctx.espiculas === false
            ? "No detectadas"
            : "No evaluable",
      ],
    ],
    4,
  );
  if (trazoPng) {
    const altoTrazo = (ANCHO * 420) / 1600;
    nuevoRenglon(altoTrazo + 7);
    doc.addImage(trazoPng, formato(trazoPng), MARGEN, y, ANCHO, altoTrazo);
    doc.setDrawColor(COLOR_LINEA);
    doc.rect(MARGEN, y, ANCHO, altoTrazo);
    y += altoTrazo + 4;
    t(
      `Trazo de la derivación ${d.registro.derivacion} analizada; los círculos rojos marcan los picos R detectados.`,
      MARGEN,
      y,
      7.8,
      "italic",
      COLOR_GRIS_CLARO,
    );
    y += 5;
  }

  /* ===== 3 · desglose auditable ===== */
  seccion("3. Desglose auditable del diagnóstico");
  t(
    "Cada regla del clasificador heurístico, el valor observado en el tramo y su efecto sobre los puntajes brutos de las cinco clases.",
    MARGEN,
    y,
    8.5,
    "normal",
    COLOR_GRIS,
  );
  y += 6;

  const COLS = [
    { titulo: "#", ancho: 8 },
    { titulo: "Criterio", ancho: 38 },
    { titulo: "Valor observado", ancho: 40 },
    { titulo: "Regla aplicada", ancho: 62 },
    { titulo: "Efecto", ancho: 32 },
  ];
  const X0 = MARGEN;
  const cabTabla = () => {
    nuevoRenglon(7);
    doc.setFillColor("#f3f4f6");
    doc.rect(X0, y - 4.4, ANCHO, 6.2, "F");
    let cx = X0;
    for (const col of COLS) {
      t(col.titulo, cx + 1.6, y, 7.8, "bold", "#374151", col.ancho - 3);
      cx += col.ancho;
    }
    y += 4.6;
  };
  cabTabla();
  doc.setFont("helvetica", "normal");
  d.res.pasos.forEach((p, i) => {
    const celdas = [
      `${i + 1}`,
      p.criterio,
      p.valor,
      p.regla,
      p.efecto,
    ] as const;
    doc.setFontSize(7.8);
    const lineas = celdas.map((c, j) =>
      doc.splitTextToSize(limpiar(c), COLS[j].ancho - 3),
    );
    const maxL = Math.max(...lineas.map((l) => l.length));
    const alto = maxL * 3.5 + 2.4;
    nuevoRenglon(alto + 1);
    if (i % 2 === 1) {
      doc.setFillColor("#fafafa");
      doc.rect(X0, y - 3.4, ANCHO, alto, "F");
    }
    let cx = X0;
    lineas.forEach((l, j) => {
      doc.setFont("helvetica", j === 4 ? "bold" : "normal");
      doc.setTextColor(j === 4 ? COLOR_MARCA : "#374151");
      doc.text(l, cx + 1.6, y);
      cx += COLS[j].ancho;
    });
    doc.setDrawColor(COLOR_LINEA);
    doc.setLineWidth(0.2);
    doc.line(X0, y + alto - 3.2, X0 + ANCHO, y + alto - 3.2);
    y += alto;
  });
  y += 2;
  /* reserva la altura del bloque completo: la intro no queda huérfana */
  nuevoRenglon(5.5 + CLASES.length * 6.4 + 4);
  t(
    "Puntajes brutos y normalización (probabilidad = puntaje bruto ÷ puntaje total):",
    MARGEN,
    y,
    8.5,
    "bold",
    COLOR_TEXTO,
  );
  y += 5.5;
  for (const k of CLASES) {
    const puntaje = d.res.puntajes[k];
    const pct = Math.round(d.res.probs[k] * 100);
    const ganador = k === clase;
    nuevoRenglon(7);
    if (ganador) {
      doc.setFillColor("#eff6ff");
      doc.rect(MARGEN, y - 3.6, ANCHO, 6.4, "F");
    }
    doc.setFont("helvetica", ganador ? "bold" : "normal");
    doc.setFontSize(8.5);
    doc.setTextColor(ganador ? COLOR_CLASE_PDF[k] : COLOR_TEXTO);
    doc.text(limpiar(`${k} — ${NOMBRE_CLASE[k]}`), MARGEN + 2, y);
    doc.text(limpiar(fmt(puntaje, 2)), MARGEN + 104, y);
    doc.text(limpiar(`${pct} %`), MARGEN + 124, y);
    doc.setFillColor("#e5e7eb");
    doc.rect(MARGEN + 136, y - 2.6, 42, 3, "F");
    doc.setFillColor(COLOR_CLASE_PDF[k]);
    doc.rect(MARGEN + 136, y - 2.6, Math.max(0.8, (42 * pct) / 100), 3, "F");
    y += 6.4;
  }
  y += 2;

  /* ===== 4 · diagnóstico ===== */
  seccion("4. Diagnóstico");
  const altoCaja = 22;
  nuevoRenglon(altoCaja + 4);
  doc.setDrawColor(color);
  doc.setFillColor("#ffffff");
  doc.setLineWidth(0.6);
  doc.rect(MARGEN, y - 4, ANCHO, altoCaja, "FD");
  doc.setFillColor(color);
  doc.rect(MARGEN, y - 4, 3, altoCaja, "F");
  t(clase, MARGEN + 7, y + 4, 16, "bold", color);
  t(NOMBRE_CLASE[clase], MARGEN + 7, y + 10, 9, "normal", COLOR_TEXTO);
  t(
    `Certeza estimada: ${certeza} %`,
    MARGEN + 7,
    y + 15.4,
    9.5,
    "bold",
    COLOR_TEXTO,
  );
  y += altoCaja + 7;
  for (const k of CLASES) {
    const pct = Math.round(d.res.probs[k] * 100);
    nuevoRenglon(7);
    doc.setFont("helvetica", k === clase ? "bold" : "normal");
    doc.setFontSize(9);
    doc.setTextColor(k === clase ? COLOR_CLASE_PDF[k] : COLOR_GRIS);
    doc.text(limpiar(k), MARGEN + 2, y);
    doc.setFillColor("#f3f4f6");
    doc.rect(MARGEN + 30, y - 2.9, 122, 3.6, "F");
    doc.setFillColor(COLOR_CLASE_PDF[k]);
    doc.rect(MARGEN + 30, y - 2.9, Math.max(0.8, (122 * pct) / 100), 3.6, "F");
    doc.setTextColor(COLOR_TEXTO);
    doc.text(limpiar(`${pct} %`), MARGEN + 158, y);
    y += 6.6;
  }
  y += 2;

  /* ===== 5 · advertencias ===== */
  seccion("5. Advertencias y limitaciones");
  if (d.res.advertencias.length) {
    for (const a of d.res.advertencias) {
      const lineas = doc.splitTextToSize(limpiar(a), ANCHO);
      nuevoRenglon(lineas.length * 4 + 2);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(8.8);
      doc.setTextColor("#dc2626");
      doc.text(lineas, MARGEN, y);
      y += lineas.length * 4 + 2.5;
    }
  } else {
    nuevoRenglon(7);
    doc.setFillColor("#059669");
    doc.circle(MARGEN + 2, y - 1, 1.1, "F");
    t("Sin advertencias para este tramo.", MARGEN + 6, y, 8.5, "normal", "#065f46");
    y += 6;
  }
  const aviso =
    "AVISO: herramienta de demostración académica del proyecto TICS-II-2026-ECG-PED. No es un dispositivo médico: no diagnostica ni reemplaza el juicio profesional. La clasificación es heurística y didáctica; no corresponde al modelo F22 del proyecto.";
  const lineasAviso = doc.splitTextToSize(limpiar(aviso), ANCHO - 6);
  const altoAviso = lineasAviso.length * 3.8 + 4;
  nuevoRenglon(altoAviso + 2);
  doc.setDrawColor(COLOR_LINEA);
  doc.setFillColor("#f9fafb");
  doc.rect(MARGEN, y - 3.2, ANCHO, altoAviso, "FD");
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.8);
  doc.setTextColor(COLOR_GRIS);
  doc.text(lineasAviso, MARGEN + 3, y);
  y += altoAviso;

  /* ===== pie de página en todas las páginas ===== */
  const nPaginas = doc.getNumberOfPages();
  for (let pg = 1; pg <= nPaginas; pg++) {
    doc.setPage(pg);
    doc.setDrawColor(COLOR_LINEA);
    doc.setLineWidth(0.3);
    doc.line(MARGEN, PIE_Y, PAGE_W - MARGEN, PIE_Y);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.setTextColor(COLOR_GRIS_CLARO);
    doc.text(
      limpiar(
        "Software de Detección de Arritmias Pediátricas mediante PDS de ECG · Universidad Diego Portales",
      ),
      MARGEN,
      PIE_Y + 4,
    );
    doc.text(
      limpiar(`Página ${pg} de ${nPaginas}`),
      PAGE_W - MARGEN,
      PIE_Y + 4,
      { align: "right" },
    );
  }

  return doc;
}

/** Genera el PDF completo y lo descarga como archivo. */
export async function generarReportePdf(d: DatosReportePdf): Promise<void> {
  const [{ jsPDF }, logo] = await Promise.all([
    import("jspdf"),
    logoDataUrl(),
  ]);
  const trazo = d.senal ? trazoDataUrl(d.senal, d.picos ?? []) : null;
  const doc = armarPdf(jsPDF, d, logo, trazo);
  const nombre = `reporte_ecg_${d.registro.nombre.replace(/[^\w.-]+/g, "_").slice(0, 48) || "demo"}.pdf`;
  doc.save(nombre);
}
