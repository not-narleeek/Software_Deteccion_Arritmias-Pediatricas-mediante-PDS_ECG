# Web de demostración — Portal para personal de salud

Página estática (HTML/CSS/JS puro, sin dependencias externas) que permite a un
profesional de la salud probar el flujo de análisis del proyecto:

1. **Elegir una señal**: caso de demostración (Sinusal / SVT / VT / Paced) o
   archivo propio (.csv/.txt con una columna: señal cruda en mV o lista de
   intervalos RR en ms).
2. **Revisar el trazo** en el visor (papel milimetrado + picos R marcados).
3. **Obtener un resultado**: ritmo sugerido con certeza, probabilidades por
   clase, medidas (FC, RR, SDNN, RMSSD, pNN50, ancho QRS, espículas de
   marcapasos), advertencias y descarga de un reporte en texto.

Todo el análisis se ejecuta **íntegramente en el navegador**: ningún dato del
paciente sale del equipo.

> ⚠️ El análisis del navegador es **heurístico y académico**: no es el modelo
> F22 ni un dispositivo médico. La clasificación calibrada del proyecto se
> ejecuta en Python (`contrib/carlos/f22_seed14/`).

## Uso local

```bash
python -m http.server 8000 --directory web
# → http://localhost:8000
```

(También funciona abriendo `web/index.html` directamente en el navegador.)

## Publicación (GitHub Pages)

`.github/workflows/deploy-pages.yml` publica la carpeta `web/` en GitHub Pages
en cada push a `main` que toque la web. Requiere activar una sola vez:

**Settings → Pages → Build and deployment → Source: GitHub Actions**

## Estructura

```
web/
├── index.html      # página única con todas las secciones
├── css/styles.css  # estilos (variables CSS, responsive, accesible)
├── js/app.js       # síntesis de casos demo, detección de picos,
│                   # métricas RR, clasificador heurístico y reporte
└── README.md
```
