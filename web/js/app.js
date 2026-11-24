'use strict';

/* ============================================================
   Portal de demostración — Detección de Arritmias Pediátricas
   TICS II · UDP. Análisis heurístico 100 % en el navegador.
   NO es el modelo F22 del proyecto ni un dispositivo médico.
   ============================================================ */

const CLASES = ['Sinusal', 'SVT', 'VT', 'Paced', 'Otro'];

/* Rangos de FC normal en pediatría (aproximación por grupos de edad) */
const RANGO_EDAD = {
  lactante:     { label: 'Lactante (menos de 1 año)', lo: 100, hi: 180 },
  preescolar:   { label: '1 a 3 años',                lo: 90,  hi: 150 },
  escolarMenor: { label: '4 a 8 años',                lo: 80,  hi: 140 },
  escolarMayor: { label: '9 a 12 años',               lo: 70,  hi: 120 },
  adolescente:  { label: 'Más de 12 años',            lo: 60,  hi: 100 },
  desconocida:  { label: 'No indicada',               lo: 60,  hi: 160 },
};

const COLOR_CLASE = { Sinusal: 'verde', SVT: 'ambar', VT: 'rojo', Paced: 'violeta', Otro: 'gris' };

const el = id => document.getElementById(id);
const fmt = (x, dec = 0) => Number.isFinite(x)
  ? x.toLocaleString('es-CL', { minimumFractionDigits: dec, maximumFractionDigits: dec })
  : '—';
const clamp01 = x => Math.min(1, Math.max(0, x));

let estado = null; // { senal, fs, picos, rr, fuente, registro: {nombre, derivacion} }

/* ---------- utilidades matemáticas ---------- */
function media(a) { let s = 0; for (const v of a) s += v; return a.length ? s / a.length : NaN; }
function desv(a) { const m = media(a); let s = 0; for (const v of a) s += (v - m) * (v - m); return a.length > 1 ? Math.sqrt(s / (a.length - 1)) : NaN; }
function rmssd(a) { let s = 0; for (let i = 1; i < a.length; i++) s += (a[i] - a[i - 1]) ** 2; return a.length > 1 ? Math.sqrt(s / (a.length - 1)) : NaN; }
function pnn50(a) { if (a.length < 2) return NaN; let c = 0; for (let i = 1; i < a.length; i++) if (Math.abs(a[i] - a[i - 1]) > 50) c++; return (100 * c) / (a.length - 1); }
function mediana(a) { const s = Array.from(a).sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
function percentil(a, p) { const s = Array.from(a).sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.max(0, Math.round(p * (s.length - 1))))]; }

/* ---------- casos demo: registros WFDB en web/demo/ ---------- */
const DEMOS = {
  demo_sinusal: 'Niño sano (Sinusal)',
  demo_svt: 'Taquicardia supraventricular (SVT)',
  demo_vt: 'Taquicardia ventricular (VT)',
  demo_paced: 'Ritmo de marcapasos (Paced)',
};

/* ---------- detección de picos R (umbral simple) ---------- */
function detectarPicos(sig, fs) {
  const sm = new Float32Array(sig.length);
  const K = Math.max(1, Math.round(fs / 100)); // ~10 ms de suavizado
  let acc = 0;
  for (let i = 0; i < sig.length; i++) {
    acc += sig[i];
    if (i >= K) acc -= sig[i - K];
    sm[i] = acc / Math.min(i + 1, K);
  }
  const p95 = percentil(sm, 0.95), med = mediana(sm);
  // El umbral adaptativo p95 puede quedar a nivel de onda T / espícula (los QRS angostos
  // ocupan <5 % de las muestras); nunca baja de la mitad del nivel pico (p99).
  const thr = Math.max(med + 0.4 * (p95 - med), 0.5 * percentil(sm, 0.99));
  const minDist = Math.round(0.2 * fs); // 200 ms → máx 300 lpm
  const picos = [];
  for (let i = 1; i < sm.length - 1; i++) {
    if (sm[i] > thr && sm[i] >= sm[i - 1] && sm[i] > sm[i + 1]) {
      if (!picos.length || i - picos[picos.length - 1] >= minDist) picos.push(i);
      else if (sm[i] > sm[picos[picos.length - 1]]) picos[picos.length - 1] = i;
    }
  }
  return picos;
}

function rrDesdePicos(picos, fs) {
  const rr = [];
  for (let i = 1; i < picos.length; i++) {
    const ms = ((picos[i] - picos[i - 1]) * 1000) / fs;
    if (ms >= 250 && ms <= 2500) rr.push(ms); // descarta intervalos imposibles
  }
  return rr;
}

/* ---------- morfología: ancho QRS medio (ms) ---------- */
function anchoQRSmedio(sig, fs, picos) {
  const base = mediana(sig);
  const anchos = [];
  for (const p of picos) {
    let A = 0;
    for (let k = Math.max(0, p - 3); k <= Math.min(sig.length - 1, p + 3); k++) A = Math.max(A, Math.abs(sig[k] - base));
    if (A < 0.15) continue; // latido demasiado pequeño
    const thr = 0.12 * A;
    let l = p, r = p;
    while (l > 0 && Math.abs(sig[l - 1] - base) > thr && p - l < 0.25 * fs) l--;
    while (r < sig.length - 1 && Math.abs(sig[r + 1] - base) > thr && r - p < 0.25 * fs) r++;
    anchos.push(((r - l + 1) * 1000) / fs);
  }
  return anchos.length ? mediana(anchos) : null;
}

/* ---------- morfología: espículas de marcapasos ---------- */
function hayEspiculas(sig, fs, picos) {
  const ventana = Math.round(0.09 * fs); // 90 ms antes del pico R
  const maxAnchos = Math.max(2, Math.round(0.01 * fs)); // subida muy angosta
  let conEspicula = 0, evaluados = 0;
  for (const p of picos) {
    const ini = Math.max(1, p - ventana);
    const fin = Math.max(1, p - Math.round(0.01 * fs));
    if (fin <= ini) continue;
    let dmax = 0;
    for (let i = ini; i <= fin; i++) dmax = Math.max(dmax, Math.abs(sig[i] - sig[i - 1]));
    if (dmax <= 0) continue;
    const pend = (dmax * fs) / 1000; // mV por ms
    let anchos = 0;
    for (let i = ini; i <= fin; i++) if ((Math.abs(sig[i] - sig[i - 1]) * fs) / 1000 > 0.5 * pend) anchos++;
    evaluados++;
    if (pend > 0.08 && anchos <= maxAnchos) conEspicula++;
  }
  return evaluados >= 3 ? conEspicula / evaluados > 0.5 : null;
}

/* ---------- métricas de variabilidad ---------- */
function metricas(rr) {
  const m = media(rr);
  return {
    n: rr.length,
    fc: 60000 / m,
    rrMedio: m,
    sdnn: desv(rr),
    rmssd: rmssd(rr),
    pnn50: pnn50(rr),
    cv: desv(rr) / m,
  };
}

/* ---------- clasificador heurístico de demostración ---------- */
function clasificar(ctx) {
  if (ctx.n < 3 || !Number.isFinite(ctx.fc)) {
    const p = 0.2;
    return {
      clase: 'Otro',
      probs: { Sinusal: p, SVT: p, VT: p, Paced: p, Otro: p },
      advertencias: ['No se detectaron suficientes latidos en el tramo: revise la calidad o el formato de la señal.'],
    };
  }
  const rango = RANGO_EDAD[ctx.edad] || RANGO_EDAD.desconocida;
  const adv = [];
  const s = { Sinusal: 0.06, SVT: 0.06, VT: 0.05, Paced: 0.03, Otro: 0.06 };
  const hr = ctx.fc;
  const regular = ctx.cv <= 0.06 ? 1 : ctx.cv <= 0.12 ? 0.5 : 0;

  /* Taquicardia supraventricular: rápida y regular */
  s.SVT += clamp01((hr - 145) / 35) + 0.2 * regular * (hr >= 130 ? 1 : 0);

  /* VT: complejos anchos y frecuencia elevada */
  if (ctx.anchoQRS != null) s.VT += clamp01((ctx.anchoQRS - 115) / 50) * 2.2 * (hr >= 100 ? 1 : 0.3);

  /* Sinusal vs Otro según rango esperado para la edad */
  if (hr >= rango.lo && hr <= rango.hi) {
    s.Sinusal += 0.8 * regular + 0.3 * clamp01((rango.hi - hr) / 50);
  } else if (hr < rango.lo) {
    s.Otro += 0.7;
    adv.push('FC bajo el rango esperado para la edad indicada (' + rango.lo + '–' + rango.hi + ' lpm): ' + fmt(hr, 0) + ' lpm (bradicardia relativa).');
  } else if (hr <= rango.hi + 15) {
    s.Otro += 0.5;
    adv.push('FC sobre el rango esperado para la edad indicada (' + rango.lo + '–' + rango.hi + ' lpm): ' + fmt(hr, 0) + ' lpm.');
  } else {
    s.SVT += 0.5;
    adv.push('FC sobre el rango esperado para la edad indicada (' + rango.lo + '–' + rango.hi + ' lpm): ' + fmt(hr, 0) + ' lpm (taquicardia).');
  }

  /* QRS ancho (≥120 ms): la SVT se define por complejos estrechos; descuenta SVT */
  if (ctx.anchoQRS != null && ctx.anchoQRS >= 120) s.SVT *= 0.35;

  /* Irregularidad marcada: fuera del alcance del modelo */
  if (ctx.cv > 0.12) {
    s.Otro += 0.7;
    adv.push('Ritmo irregular (variabilidad de RR alta): los ritmos irregulares están fuera del alcance del modelo.');
  }
  if (ctx.n < 6) adv.push('Pocos latidos en el tramo (' + ctx.n + ' intervalos RR): resultado poco confiable.');

  /* Espículas de marcapasos: evidencia fuerte de ritmo Paced */
  if (ctx.espiculas === true) {
    s.Paced += 2.0;
    s.Sinusal *= 0.4;
    s.SVT *= 0.5;
    s.VT *= 0.5;
  }

  let tot = 0;
  for (const k of CLASES) tot += s[k];
  const probs = {};
  for (const k of CLASES) probs[k] = s[k] / tot;
  let clase = 'Otro', mejor = 0;
  for (const k of CLASES) if (probs[k] > mejor) { mejor = probs[k]; clase = k; }

  if (clase === 'VT') adv.push('La clase VT tiene soporte escaso en el corpus de desarrollo (92 casos).');
  if (clase === 'Paced') adv.push('La clase Paced tiene muy pocos casos en el corpus (22 registros).');
  if (mejor < 0.5) adv.push('Diferencia débil entre clases: repita con otra ventana o revise la calidad de la señal.');

  return { clase, probs, advertencias: adv };
}

/* ---------- gráficos ---------- */
function prepararCanvas(canvas, w, h) {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}

function dibujarSenal(sig, fs, picos) {
  const canvas = el('lienzo');
  const w = canvas.clientWidth || 640, h = 240;
  const ctx = prepararCanvas(canvas, w, h);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, w, h);
  /* papel milimetrado */
  const paso = Math.max(16, w / 40);
  ctx.lineWidth = 1;
  for (let x = 0; x <= w; x += paso) { ctx.strokeStyle = '#f6dcdc'; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let yy = 0; yy <= h; yy += paso) { ctx.strokeStyle = '#f6dcdc'; ctx.beginPath(); ctx.moveTo(0, yy); ctx.lineTo(w, yy); ctx.stroke(); }
  for (let x = 0; x <= w; x += paso * 5) { ctx.strokeStyle = '#eec3c3'; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let yy = 0; yy <= h; yy += paso * 5) { ctx.strokeStyle = '#eec3c3'; ctx.beginPath(); ctx.moveTo(0, yy); ctx.lineTo(w, yy); ctx.stroke(); }
  /* escala vertical (percentiles 1–99) */
  const orden = Array.from(sig).sort((a, b) => a - b);
  const lo = orden[Math.floor(orden.length * 0.01)], hi = orden[Math.floor(orden.length * 0.99)];
  const y = v => h / 2 - (v - (lo + hi) / 2) * ((h * 0.72) / Math.max(0.2, hi - lo));
  ctx.strokeStyle = '#0e7490';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let i = 0; i < sig.length; i++) {
    const x = (i / (sig.length - 1)) * w;
    if (i) ctx.lineTo(x, y(sig[i])); else ctx.moveTo(x, y(sig[i]));
  }
  ctx.stroke();
  ctx.fillStyle = '#b91c1c';
  for (const p of picos) {
    const x = (p / (sig.length - 1)) * w;
    ctx.beginPath();
    ctx.arc(x, y(sig[p]), 3, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = '#5c6b7a';
  ctx.font = '12px system-ui';
  ctx.fillText('Señal ECG — ' + fmt(sig.length / fs, 1) + ' s @ ' + fs + ' Hz (mV)', 10, 16);
}

/* ---------- flujo de la interfaz ---------- */
function prepararPanel() {
  el('panel-senal').hidden = false;
  el('resultado').hidden = true;
  el('btn-analizar').disabled = false;
  el('panel-senal').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function limpiar() {
  estado = null;
  el('panel-senal').hidden = true;
  el('resultado').hidden = true;
  el('archivo').value = '';
}

/* ---------- carga de registros WFDB ---------- */
const MAX_SEG = 10; // segundos analizados (ventana del proyecto)

function mostrarRegistro(registro, fuente) {
  const lead = WFDB.elegirLead(registro.leads);
  const fs = lead.fs;
  const maxN = Math.round(MAX_SEG * fs);
  let senal = lead.senal;
  let aviso = '';
  if (senal.length > maxN) {
    senal = senal.subarray(0, maxN);
    aviso = ' Se analizó solo el primer tramo de 10 segundos.';
  } else if (senal.length < maxN) {
    aviso = ' Registro más corto que 10 s: revise el resultado con cautela.';
  }
  const picos = detectarPicos(senal, fs);
  const rr = rrDesdePicos(picos, fs);
  estado = { senal: Float32Array.from(senal), fs, picos, rr, fuente, registro: { nombre: registro.nombre, derivacion: lead.nombre } };
  prepararPanel();
  dibujarSenal(estado.senal, fs, picos);
  el('info-senal').textContent =
    'Registro "' + registro.nombre + '" · derivación ' + lead.nombre +
    ' · ' + fmt(senal.length / fs, 1) + ' s @ ' + fmt(fs, 0) + ' Hz · ' +
    rr.length + ' intervalos RR detectados.' + aviso;
}

async function cargarDemo(nombre) {
  const base = 'demo/' + nombre + '/' + nombre;
  try {
    const textoHeader = await (await fetch(base + '.hea')).text();
    const buffer = await (await fetch(base + '.dat')).arrayBuffer();
    const registro = WFDB.leerRegistro(textoHeader, () => buffer);
    mostrarRegistro(registro, 'Caso de demostración — ' + DEMOS[nombre]);
  } catch (e) {
    const nota = location.protocol === 'file:'
      ? ' Nota: si abrió esta página como archivo local (file://), el navegador bloquea la lectura de los casos demo. Sirva la carpeta con: python -m http.server 8000 --directory web'
      : '';
    alert('No se pudo cargar el caso demo: ' + e.message + nota);
  }
}

async function leerArchivos(archivos) {
  const lista = Array.from(archivos || []);
  const hea = lista.find(f => /\.hea$/i.test(f.name));
  if (!hea) {
    alert('Seleccione el archivo .hea del registro WFDB junto con su .dat (formato del proyecto, como ZZU pECG).');
    return;
  }
  try {
    const textoHeader = await hea.text();
    const buffers = new Map();
    for (const f of lista.filter(f => /\.dat$/i.test(f.name))) {
      buffers.set(f.name.toLowerCase(), await f.arrayBuffer());
    }
    const registro = WFDB.leerRegistro(textoHeader, nombre => buffers.get(nombre.toLowerCase()) ?? null);
    mostrarRegistro(registro, 'Registro WFDB: ' + hea.name.replace(/\.hea$/i, ''));
  } catch (e) {
    alert('No se pudo leer el registro: ' + e.message);
  }
}

function analizar() {
  if (!estado) return;
  const edad = el('edad').value;
  const met = metricas(estado.rr);
  const ctx = {
    ...met,
    anchoQRS: anchoQRSmedio(estado.senal, estado.fs, estado.picos),
    espiculas: hayEspiculas(estado.senal, estado.fs, estado.picos),
    edad,
  };
  const res = clasificar(ctx);
  mostrarResultado(res, ctx);
}

function mostrarResultado(res, ctx) {
  const c = COLOR_CLASE[res.clase];
  const barras = CLASES.map(k => {
    const pct = Math.round(res.probs[k] * 100);
    return '<div class="barra-fila">' +
      '<span class="barra-nombre ' + (k === res.clase ? 'fuerte' : '') + '">' + k + '</span>' +
      '<span class="barra-pista"><span class="barra-fill ' + c + '" style="width:' + pct + '%"></span></span>' +
      '<span class="barra-pct">' + pct + ' %</span>' +
      '</div>';
  }).join('');
  const advs = res.advertencias.length
    ? '<ul class="advertencias">' + res.advertencias.map(a => '<li>⚠️ ' + a + '</li>').join('') + '</ul>'
    : '<p class="mini ok">Sin advertencias para este tramo.</p>';
  const qrs = ctx.anchoQRS != null ? fmt(ctx.anchoQRS, 0) + ' ms' : 'No evaluable';
  const esp = ctx.espiculas === true ? 'Detectadas' : ctx.espiculas === false ? 'No detectadas' : 'No evaluable';
  const reg = ctx.cv <= 0.06 ? 'Regular' : ctx.cv <= 0.12 ? 'Moderadamente irregular' : 'Irregular';

  el('resultado').innerHTML =
    '<h3>Paso 3 · Resultado de la demostración</h3>' +
    '<div class="veredicto">' +
    '<div class="sello ' + c + '"><span class="sello-txt">' + res.clase + '</span><span class="sello-sub">ritmo sugerido</span></div>' +
    '<div class="certeza"><span class="num-grande">' + Math.round(res.probs[res.clase] * 100) + ' %</span><span class="mini">certeza estimada (heurística)</span></div>' +
    '</div>' +
    '<div class="barras">' + barras + '</div>' +
    '<h4>Medidas del tramo</h4>' +
    '<dl class="metricas">' +
    '<div><dt>FC media</dt><dd>' + fmt(ctx.fc, 0) + ' lpm</dd></div>' +
    '<div><dt>RR medio</dt><dd>' + fmt(ctx.rrMedio, 0) + ' ms</dd></div>' +
    '<div><dt>SDNN</dt><dd>' + fmt(ctx.sdnn, 0) + ' ms</dd></div>' +
    '<div><dt>RMSSD</dt><dd>' + fmt(ctx.rmssd, 0) + ' ms</dd></div>' +
    '<div><dt>pNN50</dt><dd>' + (Number.isFinite(ctx.pnn50) ? fmt(ctx.pnn50, 0) + ' %' : '—') + '</dd></div>' +
    '<div><dt>Regularidad</dt><dd>' + reg + '</dd></div>' +
    '<div><dt>Ancho QRS</dt><dd>' + qrs + '</dd></div>' +
    '<div><dt>Espículas de marcapasos</dt><dd>' + esp + '</dd></div>' +
    '</dl>' +
    '<h4>Advertencias</h4>' + advs +
    '<p class="mini">Las probabilidades provienen de reglas heurísticas de demostración ejecutadas en su navegador; no corresponden al modelo calibrado del proyecto (F22). Confirme siempre con la evaluación clínica.</p>' +
    '<div class="acciones">' +
    '<button class="boton secundario" id="btn-reporte">⬇ Descargar reporte</button>' +
    '<button class="boton secundario" id="btn-otro">Analizar otra señal</button>' +
    '</div>';
  el('resultado').hidden = false;
  el('btn-reporte').addEventListener('click', () => descargarReporte(res, ctx));
  el('btn-otro').addEventListener('click', limpiar);
  el('resultado').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function descargarReporte(res, ctx) {
  const rango = RANGO_EDAD[el('edad').value] || RANGO_EDAD.desconocida;
  const lineas = [
    'REPORTE DE ANÁLISIS — PORTAL DE DEMOSTRACIÓN (académico, no certificado)',
    'Proyecto TICS-II-2026-ECG-PED · Universidad Diego Portales',
    'Fecha: ' + new Date().toLocaleString('es-CL'),
    'Fuente: ' + (estado && estado.fuente ? estado.fuente : '—'),
    'Edad indicada: ' + rango.label + ' (rango Sinusal ' + rango.lo + '–' + rango.hi + ' lpm)',
    '',
    'RESULTADO',
    '  Ritmo sugerido: ' + res.clase,
    '  Certeza estimada (heurística): ' + Math.round(res.probs[res.clase] * 100) + ' %',
  ].concat(CLASES.map(k => '  P(' + k + '): ' + Math.round(res.probs[k] * 100) + ' %')).concat([
    '',
    'MEDIDAS',
    '  FC media: ' + fmt(ctx.fc, 0) + ' lpm',
    '  RR medio: ' + fmt(ctx.rrMedio, 0) + ' ms',
    '  SDNN: ' + fmt(ctx.sdnn, 0) + ' ms | RMSSD: ' + fmt(ctx.rmssd, 0) + ' ms | pNN50: ' + fmt(ctx.pnn50, 0) + ' %',
    '  Ancho QRS: ' + (ctx.anchoQRS != null ? fmt(ctx.anchoQRS, 0) + ' ms' : 'No evaluable'),
    '  Espículas de marcapasos: ' + (ctx.espiculas === true ? 'Detectadas' : ctx.espiculas === false ? 'No detectadas' : 'No evaluable'),
    '',
    'ADVERTENCIAS',
  ]).concat(res.advertencias.length ? res.advertencias.map(a => '  - ' + a) : ['  - Ninguna']).concat([
    '',
    'AVISO: Esta demo no es un dispositivo médico. No diagnostica ni reemplaza el juicio profesional.',
  ]);
  const blob = new Blob([lineas.join('\n')], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'reporte_ecg_demo.txt';
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ---------- inicialización ---------- */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.chip[data-demo]').forEach(b => b.addEventListener('click', () => cargarDemo(b.dataset.demo)));
  el('archivo').addEventListener('change', e => { if (e.target.files.length) leerArchivos(e.target.files); });
  const zona = el('zona');
  zona.addEventListener('dragover', e => { e.preventDefault(); zona.classList.add('activa'); });
  zona.addEventListener('dragleave', () => zona.classList.remove('activa'));
  zona.addEventListener('drop', e => {
    e.preventDefault();
    zona.classList.remove('activa');
    if (e.dataTransfer.files && e.dataTransfer.files.length) leerArchivos(e.dataTransfer.files);
  });
  el('btn-analizar').addEventListener('click', analizar);
  el('btn-limpiar').addEventListener('click', limpiar);
  window.addEventListener('resize', () => {
    if (!estado) return;
    dibujarSenal(estado.senal, estado.fs, estado.picos);
  });
});
