# Web de demostración — Portal para personal de salud

Página estática (HTML/CSS/JS puro, sin dependencias externas) que permite a un
profesional de la salud probar el flujo de análisis del proyecto:

1. **Elegir un registro ECG**: caso de demostración (Sinusal / SVT / VT /
   Paced) o un **registro WFDB propio** (`.hea` + `.dat`, el formato estándar
   de PhysioNet usado por el proyecto y por el corpus ZZU pECG). Se analiza la
   derivación II (o la primera disponible) del primer tramo de 10 segundos; la
   frecuencia de muestreo se lee del encabezado.
2. **Revisar el trazo** en el visor (papel milimetrado + picos R marcados).
3. **Obtener un resultado**: ritmo sugerido con certeza, probabilidades por
   clase, medidas (FC, RR, SDNN, RMSSD, pNN50, ancho QRS, espículas de
   marcapasos), advertencias y descarga de un reporte en texto.

Todo el análisis se ejecuta **íntegramente en el navegador**: ningún dato del
paciente sale del equipo. No se aceptan archivos CSV.

> ⚠️ El análisis del navegador es **heurístico y académico**: no es el modelo
> F22 ni un dispositivo médico. La clasificación calibrada del proyecto se
> ejecuta en Python (`contrib/carlos/f22_seed14/`).

## Uso local

```bash
python -m http.server 8000 --directory web
# → http://localhost:8000
```

(Abrir `web/index.html` directamente también funciona en Chromium; en
navegadores más estrictos los casos demo requieren servir la carpeta por HTTP.)

## Publicación (GitHub Pages)

`.github/workflows/deploy-pages.yml` publica la carpeta `web/` en GitHub Pages
en cada push a `main` que toque la web. Requiere activar una sola vez:

**Settings → Pages → Build and deployment → Source: GitHub Actions**

## Estructura

```
web/
├── index.html      # página única con todas las secciones
├── css/styles.css  # estilos (variables CSS, responsive, accesible)
├── js/wfdb.js      # lector WFDB en el navegador (.hea + .dat; formatos
│                   # 16, 24, 32, 80, 160, 212; semántica de wfdb-python)
├── js/app.js       # carga de registros, detección de picos, métricas RR,
│                   # clasificador heurístico y reporte
├── demo/           # registros WFDB de demostración (sintéticos, 12
│                   # derivaciones, 10 s @ 500 Hz) — regenerables con
│                   # scripts/generar_demo_wfdb.py
└── README.md
```

Los casos demo son señales **sintéticas** generadas por
`scripts/generar_demo_wfdb.py` (determinístico); no representan pacientes
reales.
