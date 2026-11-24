'use strict';

/* ============================================================
   Lector WFDB en el navegador — portal de demostración.
   Parsea registros WFDB (.hea + .dat), el formato del proyecto
   (corpus ZZU pECG) y de PhysioNet. Sin dependencias externas.
   Formatos de muestra soportados: 16, 24, 32, 80, 160, 212.
   Semántica de decodificación idéntica a wfdb-python (la misma
   librería que usa el pipeline del proyecto).
   ============================================================ */

const WFDB = (() => {
  const FORMATOS = new Set(['16', '24', '32', '80', '160', '212']);

  /* Factores hacia mV (el pipeline del proyecto trabaja en mV) */
  const FACTOR_MV = { V: 1000, mV: 1, uV: 0.001, µV: 0.001, nV: 1e-6 };

  const error = (msg) => { throw new Error(msg); };

  /* ---------- línea de registro ---------- */
  function parsearLineaRegistro(linea, nombreArchivos) {
    const tok = linea.trim().split(/\s+/);
    if (tok.length < 2) error('La primera línea del .hea está incompleta.');
    if (/\//.test(tok[0]) || /\//.test(tok[1])) {
      error('Registros multi-segmento (n_señales/n_segmentos) no están soportados en esta demo.');
    }
    const fs = parseFloat(tok[2]);
    if (!Number.isFinite(fs) || fs <= 0) error('Frecuencia de muestreo inválida en el .hea: "' + tok[2] + '".');
    let nMuestras = parseInt(tok[3], 10);
    if (!Number.isFinite(nMuestras) || nMuestras <= 0) nMuestras = null; // ausente → derivar del .dat
    return { nombre: tok[0], nSenales: parseInt(tok[1], 10), fs, nMuestras };
  }

  /* ---------- líneas de señal ----------
     Estilos soportados (ambos reales, verificados contra
     wfdb-python rx_signal y headers de PhysioNet/GitHub):
     clásico:    <archivo> <fmt>[xN][:skew][+off] <ganancia>(<base>)/<unid> <res> <zero> <init> <chk> <blk> <nombre>
     paréntesis: <archivo> <fmt>(res,zero,chk,blk) <ganancia>(<base>)/<unid> ... <nombre>            */
  function parsearLineaSenal(linea, nombreRegistro) {
    const tok = linea.trim().split(/\s+/);
    const sig = { archivo: null, fmt: null, mpp: 1, skew: 0, byteOffset: 0,
      adcRes: null, adcZero: null, ganancia: 200, base: null, unidades: 'mV' };

    // Nombre de derivación = último token; se descarta un lead-spec previo tipo (0) o [x]
    sig.nombre = tok.pop();
    if (tok.length && /^[\[({<].*[\])}>]$/.test(tok[tok.length - 1])) tok.pop();

    // Archivo: primer token con punto (p. ej. registro.dat); ausente → <registro>.dat
    if (tok.length && /[.]/.test(tok[0]) && !/[()]/.test(tok[0])) {
      sig.archivo = tok.shift();
      if (sig.archivo === '~') error('El registro declara una señal sin archivo ("~"): no se puede leer en esta demo.');
    }

    // Token de formato: fmt [x mpp] [: skew] [+ byteOffset] [(res,zero,chk,blk)]
    if (!tok.length) error('Línea de señal sin formato: "' + linea + '".');
    let tFmt = tok.shift();
    const pIdx = tFmt.indexOf('(');
    if (pIdx >= 0) {
      const paren = tFmt.slice(pIdx + 1, tFmt.endsWith(')') ? -1 : undefined);
      tFmt = tFmt.slice(0, pIdx);
      const campos = paren.split(',').map(x => parseInt(x, 10));
      if (Number.isFinite(campos[0])) sig.adcRes = campos[0];
      if (Number.isFinite(campos[1])) sig.adcZero = campos[1];
    }
    const mFmt = /^(\d+)(?:x(\d+))?(?::(\d+))?(?:\+(\d+))?$/.exec(tFmt);
    if (!mFmt) error('Formato de muestra no reconocido: "' + tFmt + '".');
    sig.fmt = mFmt[1];
    if (mFmt[2]) sig.mpp = parseInt(mFmt[2], 10);
    if (mFmt[3]) sig.skew = parseInt(mFmt[3], 10);
    if (mFmt[4]) sig.byteOffset = parseInt(mFmt[4], 10);
    if (!FORMATOS.has(sig.fmt)) {
      error('Formato de muestra ' + sig.fmt + ' no soportado en esta demo (soportados: 16, 24, 32, 80, 160, 212).');
    }
    if (sig.fmt === '212' && sig.mpp !== 1) {
      error('Formato 212 con muestras por cuadro (x' + sig.mpp + ') no soportado en esta demo.');
    }

    // Token de ganancia: ganancia [(base)] [/unidades] — ganancia 0 → 200 (regla wfdb)
    let tGan = tok.shift() || '';
    const mGan = /^(-?[\d.]+(?:[eE][+-]?\d+)?)(?:\((-?\d+)\))?(?:\/([\w^?%.-]+))?$/.exec(tGan);
    if (!mGan) error('Ganancia no reconocida en línea de señal: "' + tGan + '".');
    sig.ganancia = parseFloat(mGan[1]);
    if (sig.ganancia === 0) sig.ganancia = 200;
    if (mGan[2] !== undefined) sig.base = parseInt(mGan[2], 10);
    if (mGan[3]) sig.unidades = mGan[3];

    // Campos posicionales restantes: adc_res, adc_zero, init_value, checksum, block_size
    let pos = 0;
    for (const t of tok) {
      const v = parseInt(t, 10);
      if (!Number.isFinite(v)) continue;
      if (pos === 0 && sig.adcRes === null) sig.adcRes = v;
      else if (pos === 1 && sig.adcZero === null) sig.adcZero = v;
      pos++;
    }
    if (sig.base === null) sig.base = sig.adcZero !== null ? sig.adcZero : 0;

    if (!sig.archivo) sig.archivo = nombreRegistro + '.dat';
    return sig;
  }

  /* ---------- decodificación por formato (idéntica a wfdb-python) ----------
     digital = muestra en unidades ADC; físico = (digital - base) / ganancia  */
  function decodificar(fmt, vista, inicio, nCuadros, nSenalesArchivo) {
    // Para 212 el stream contiene pares alternados (señal 0, señal 1, …):
    const n = fmt === '212' ? nCuadros * 2 : nCuadros * nSenalesArchivo;
    const out = new Float64Array(n);
    let o = 0;
    switch (fmt) {
      case '16': // int16 LE directo, sin sesgo
        for (let i = 0; i < n; i++, o += 2) out[i] = vista.getInt16(inicio + o, true);
        break;
      case '80': // uint8 con desplazamiento −128
        for (let i = 0; i < n; i++, o += 1) out[i] = vista.getUint8(inicio + o) - 128;
        break;
      case '160': // uint16 con desplazamiento −32768
        for (let i = 0; i < n; i++, o += 2) out[i] = vista.getUint16(inicio + o, true) - 32768;
        break;
      case '32': // int32 LE directo
        for (let i = 0; i < n; i++, o += 4) out[i] = vista.getInt32(inicio + o, true);
        break;
      case '24': { // 3 bytes LE, complemento a 2
        for (let i = 0; i < n; i++, o += 3) {
          let v = vista.getUint8(inicio + o) | (vista.getUint8(inicio + o + 1) << 8) | (vista.getUint8(inicio + o + 2) << 16);
          if (v > 0x7fffff) v -= 0x1000000;
          out[i] = v;
        }
        break;
      }
      case '212': { // 12 bits por muestra, pares por terceto LE
        const bytes = nCuadros * 3;
        for (let b = 0; b + 2 < bytes; b += 3, o += 2) {
          const b0 = vista.getUint8(inicio + b), b1 = vista.getUint8(inicio + b + 1), b2 = vista.getUint8(inicio + b + 2);
          let v0 = b0 + 256 * (b1 & 0x0f);
          let v1 = b2 + 256 * ((b1 >> 4) & 0x0f);
          if (v0 > 2047) v0 -= 4096;
          if (v1 > 2047) v1 -= 4096;
          out[o] = v0; out[o + 1] = v1;
        }
        break;
      }
      default: error('Formato no soportado: ' + fmt);
    }
    return out;
  }

  function bytesPorMuestra(fmt) {
    if (fmt === '16' || fmt === '160') return 2;
    if (fmt === '24') return 3;
    if (fmt === '32') return 4;
    if (fmt === '80') return 1;
    return 0;
  }

  /* Bytes de un cuadro completo del archivo (todas sus señales) */
  function bytesPorCuadro(fmt, nSenales, mpp) {
    if (fmt === '212') return 3; // un terceto por cuadro (par de muestras)
    return nSenales * mpp * bytesPorMuestra(fmt);
  }

  /* ---------- API principal ----------
     textoHeader: contenido del .hea
     obtenerDatos(nombreArchivo) → ArrayBuffer | null                       */
  function leerRegistro(textoHeader, obtenerDatos) {
    const lineas = textoHeader.split(/\r?\n/).filter(l => l.trim() && !l.trim().startsWith('#'));
    if (!lineas.length) error('El .hea está vacío.');
    const rec = parsearLineaRegistro(lineas[0]);
    const lineasSenal = lineas.slice(1, 1 + rec.nSenales);
    if (lineasSenal.length !== rec.nSenales) {
      error('El .hea declara ' + rec.nSenales + ' señales pero tiene ' + lineasSenal.length + ' líneas de señal.');
    }
    const senales = lineasSenal.map(l => parsearLineaSenal(l, rec.nombre));

    // Agrupar señales por archivo y validar compatibilidad dentro de cada uno
    const porArchivo = new Map();
    senales.forEach((s, canal) => {
      const clave = s.archivo.toLowerCase();
      if (!porArchivo.has(clave)) porArchivo.set(clave, { senales: [], canales: [] });
      const g = porArchivo.get(clave);
      g.senales.push(s); g.canales.push(canal);
    });
    for (const [clave, g] of porArchivo) {
      const fmts = new Set(g.senales.map(s => s.fmt));
      if (fmts.size > 1) error('El archivo ' + g.senales[0].archivo + ' mezcla formatos de muestra; no está soportado.');
      const mpp = new Set(g.senales.map(s => s.mpp));
      if (mpp.size > 1) error('El archivo ' + g.senales[0].archivo + ' tiene derivaciones con muestras por cuadro distintas; no está soportado en esta demo.');
      if (g.senales[0].fmt === '212' && g.senales.length !== 2) {
        error('El formato 212 almacena pares de señales: se declararon ' + g.senales.length + ' para ' + g.senales[0].archivo + '.');
      }
      if (obtenerDatos(clave) == null) {
        error('Falta el archivo de muestras "' + g.senales[0].archivo + '". Seleccione el .hea junto con todos los .dat del registro.');
      }
    }

    // Decodificar cada archivo → canales físicos
    const canales = new Array(senales.length).fill(null);
    for (const [clave, g] of porArchivo) {
      const buffer = obtenerDatos(clave);
      const s0 = g.senales[0];
      const vista = new DataView(buffer);
      const bytesCuadro = bytesPorCuadro(s0.fmt, g.senales.length, s0.mpp);
      const disponibles = Math.max(0, Math.floor((buffer.byteLength - s0.byteOffset) / bytesCuadro));
      const nCuadros = rec.nMuestras !== null ? Math.min(rec.nMuestras, disponibles) : disponibles;
      if (nCuadros < 2) error('El archivo ' + s0.archivo + ' parece vacío o truncado.');
      const stream = decodificar(s0.fmt, vista, s0.byteOffset, nCuadros, g.senales.length);

      // Repartir el stream entre señales del archivo
      const mpp = s0.mpp;
      g.senales.forEach((s, i) => {
        let serie;
        if (s.fmt === '212') {
          serie = new Float64Array(nCuadros); // alternado 0,1,0,1…
          for (let j = i, w = 0; j < stream.length; j += 2, w++) serie[w] = stream[j];
        } else {
          serie = new Float64Array(nCuadros);
          // Cuadro: [señal 0: mpp muestras][señal 1: mpp muestras]… ; tomamos la 1.ª de cada cuadro
          for (let f = 0; f < nCuadros; f++) {
            serie[f] = stream[f * s.mpp * g.senales.length + i * s.mpp];
          }
        }
        // Skew: recortar «skew» cuadros del inicio (comportamiento de wfdb)
        const recorte = s.skew * mpp;
        const serieSkew = recorte > 0 ? serie.subarray(Math.min(recorte, serie.length)) : serie;

        const factor = FACTOR_MV[s.unidades] !== undefined ? FACTOR_MV[s.unidades] : 1;
        const fisica = new Float32Array(serieSkew.length);
        for (let j = 0; j < serieSkew.length; j++) {
          fisica[j] = (serieSkew[j] - s.base) / s.ganancia * factor;
        }
        canales[g.canales[i]] = {
          nombre: s.nombre,
          unidades: 'mV',
          fs: rec.fs * mpp,
          muestras: fisica.length,
          senal: fisica,
        };
      });
    }
    if (canales.some(c => c === null)) error('No se pudieron decodificar todas las señales del registro.');
    return { nombre: rec.nombre, fs: rec.fs, nMuestras: rec.nMuestras, leads: canales };
  }

  /* Derivación para el análisis: II si existe (cualquier variante de caso),
     si no la primera disponible. */
  function elegirLead(leads) {
    return leads.find(l => /^ii$/i.test(l.nombre)) || leads[0];
  }

  return { leerRegistro, elegirLead };
})();
