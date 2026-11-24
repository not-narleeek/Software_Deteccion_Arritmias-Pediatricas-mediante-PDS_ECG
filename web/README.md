# Web de demostración — Portal para personal de salud

Página estática (HTML/CSS/JS puro, sin dependencias externas) con dos partes:

1. **Landing informativo** (HTML estático, se lee sin JavaScript): el problema
   de las arritmias pediátricas, la situación en Chile y la propuesta de valor
   del proyecto. Cada cifra lleva su fuente enlazada al pie de su sección.
2. **Analizador de demostración**, con el que un profesional de la salud puede
   probar el flujo de análisis del proyecto:

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

> ⚠️ Todo el portal es una **demostración académica**: el análisis del
> navegador es **heurístico**, no es el modelo F22 ni un dispositivo médico.
> La clasificación calibrada del proyecto se ejecuta en Python
> (`contrib/carlos/f22_seed14/`).

## Uso local

```bash
python -m http.server 8000 --directory web
# → http://localhost:8000
```

(Abrir `web/index.html` directamente también funciona en Chromium; en
navegadores más estrictos los casos demo requieren servir la carpeta por HTTP.)

## Publicación (GitHub Pages)

Sin publicación automática configurada: no existe
`.github/workflows/deploy-pages.yml` en el repositorio y el sitio no está
publicado. Para servir la carpeta `web/` con GitHub Pages hay que crear ese
workflow y activar una sola vez:

**Settings → Pages → Build and deployment → Source: GitHub Actions**

## Estructura

```
web/
├── index.html      # página única: landing + analizador (incluye el guión del menú)
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

## Landing informativo

Las secciones `#problema`, `#chile` y `#propuesta` implementan
[`docs/web_landing.md`](../docs/web_landing.md), de donde salen el texto y la
tabla de fuentes (§4): ninguna cifra va sin su referencia enlazada, y cada cita
`[n]` salta a la entrada correspondiente de la lista de fuentes de su sección.
Para cambiar una cifra o añadir una, editar primero ese documento.

La barra superior es una píldora blanca flotante (logo + «PediaECG», separador y
enlaces) que enlaza las ocho secciones y resalta la sección visible. Por debajo
de 1160 px la navegación se pliega tras el botón «Menú»; sin JavaScript queda
siempre desplegada y la barra deja de ser fija. El logo es un SVG inline en
`index.html` (corazón con trazo ECG, `#1d4fa8`), redibujado a partir de la
imagen de referencia: si existe el archivo original del logo, conviene
reemplazarlo.
