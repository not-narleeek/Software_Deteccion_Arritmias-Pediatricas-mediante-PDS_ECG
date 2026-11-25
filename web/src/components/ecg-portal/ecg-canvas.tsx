"use client";

import { useEffect, useRef } from "react";

/* ============================================================
   Visor de señal ECG en canvas con la visual de la app del
   proyecto: fondo de puntos, líneas de referencia punteadas,
   trazo azul de la marca con relleno degradado y marcadores
   de picos R como círculos blancos. Port de dibujarSenal() de
   web/js/app.js con soporte DPR y redibujado responsivo.
   ============================================================ */

interface Props {
  senal: ArrayLike<number>;
  fs: number;
  picos: number[];
  altura?: number;
}

/** Lee --brand del tema; usa un azul equivalente como reserva. */
function colorBrand(): string {
  if (typeof window === "undefined") return "#3b54e0";
  const v = getComputedStyle(document.documentElement)
    .getPropertyValue("--brand")
    .trim();
  return v || "#3b54e0";
}

export function EcgCanvas({ senal, fs, picos, altura = 250 }: Props) {
  const contenedorRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const contenedor = contenedorRef.current;
    if (!canvas || !contenedor) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dibujar = () => {
      const w = contenedor.clientWidth || 640;
      const h = altura;
      const dpr = window.devicePixelRatio || 1;
      const targetW = Math.round(w * dpr);
      const targetH = Math.round(h * dpr);
      if (canvas.width !== targetW || canvas.height !== targetH) {
        canvas.width = targetW;
        canvas.height = targetH;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      /* transparente: deja ver la cuadrícula de puntos del contenedor */
      ctx.clearRect(0, 0, w, h);

      /* líneas de referencia punteadas, como en la app */
      ctx.save();
      ctx.setLineDash([2, 6]);
      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(18,22,38,0.10)";
      for (const f of [0.26, 0.52, 0.78]) {
        const yy = Math.round(h * f) + 0.5;
        ctx.beginPath();
        ctx.moveTo(0, yy);
        ctx.lineTo(w, yy);
        ctx.stroke();
      }
      ctx.restore();

      /* escala vertical (percentiles 1–99) */
      const orden = Array.from(senal).sort((a, b) => a - b);
      const lo = orden[Math.floor(orden.length * 0.01)];
      const hi = orden[Math.floor(orden.length * 0.99)];
      const y = (v: number) =>
        h / 2 - (v - (lo + hi) / 2) * ((h * 0.72) / Math.max(0.2, hi - lo));

      const n = senal.length;
      const brand = colorBrand();

      /* trazado de la señal */
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const x = (i / Math.max(1, n - 1)) * w;
        if (i === 0) ctx.moveTo(x, y(senal[i]));
        else ctx.lineTo(x, y(senal[i]));
      }

      /* relleno degradado bajo el trazo */
      const trazo = new Path2D();
      for (let i = 0; i < n; i++) {
        const x = (i / Math.max(1, n - 1)) * w;
        if (i === 0) trazo.moveTo(x, y(senal[i]));
        else trazo.lineTo(x, y(senal[i]));
      }
      const relleno = new Path2D(trazo);
      relleno.lineTo(w, h);
      relleno.lineTo(0, h);
      relleno.closePath();
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, "rgba(59,84,224,0.10)");
      grad.addColorStop(1, "rgba(59,84,224,0)");
      ctx.fillStyle = grad;
      ctx.fill(relleno);

      /* trazo azul de la marca */
      ctx.strokeStyle = brand;
      ctx.lineWidth = 2;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.stroke(trazo);

      /* marcadores de picos R: círculos blancos con borde azul */
      for (const p of picos) {
        if (p < 0 || p >= n) continue;
        const x = (p / Math.max(1, n - 1)) * w;
        ctx.beginPath();
        ctx.arc(x, y(senal[p]), 4, 0, Math.PI * 2);
        ctx.fillStyle = "#ffffff";
        ctx.fill();
        ctx.lineWidth = 1.8;
        ctx.strokeStyle = brand;
        ctx.stroke();
      }
    };

    dibujar();

    const observer = new ResizeObserver(() => dibujar());
    observer.observe(contenedor);
    return () => observer.disconnect();
  }, [senal, fs, picos, altura]);

  return (
    <div ref={contenedorRef} className="w-full">
      <canvas
        ref={canvasRef}
        role="img"
        aria-label="Gráfico de la señal ECG cargada con los picos R detectados"
        style={{ height: altura }}
        className="w-full"
      />
    </div>
  );
}
