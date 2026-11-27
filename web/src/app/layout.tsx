import type { Metadata, Viewport } from "next";
import { DM_Sans, Instrument_Serif, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  weight: "400",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Detector de Arritmias Pediátricas · Portal de demostración",
  description:
    "Demostración web del proyecto de detección de arritmias pediátricas mediante PDS de señales ECG (TICS II, UDP). Uso académico; no es un dispositivo médico.",
  keywords: [
    "ECG pediátrico",
    "arritmias",
    "procesamiento digital de señales",
    "WFDB",
    "ZZU pECG",
    "TICS II UDP",
  ],
  openGraph: {
    title: "Detector de Arritmias Pediátricas · Portal de demostración",
    description:
      "Análisis asistido de ECG pediátrico: cargue un registro WFDB de 10 s y reciba una sugerencia de ritmo con nivel de certeza. Demo académica.",
    siteName: "ECG Pediátrico · UDP TICS II",
    type: "website",
  },
  icons: {
    icon: [{ url: "/images/logo-proyecto.svg", type: "image/svg+xml" }],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body
        className={`${dmSans.variable} ${instrumentSerif.variable} ${jetbrainsMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
