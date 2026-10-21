// Calculadora de ajuste salarial: la misma lógica que inflationarg/calculadora.py.
// Los casos de tests/casos_calculadora.json los corren pytest y `node --test`.

export const SECTORES = {
  sal_total: "Total",
  sal_privado: "Privado registrado",
  sal_publico: "Público",
  sal_no_registrado: "Privado no registrado",
};

export class ErrorCalculadora extends Error {
  constructor(codigo, mensaje) {
    super(mensaje);
    this.codigo = codigo;
  }
}

// Redondeo "half up", idéntico a formato.redondear de Python.
export function redondear(valor, decimales = 2) {
  const factor = 10 ** decimales;
  return Math.floor(valor * factor + 0.5) / factor;
}

function variacion(serie, desde, hasta) {
  return serie[hasta] / serie[desde] - 1;
}

/**
 * Ajuste por inflación de `sueldo` entre `desde` y `hasta` (meses "AAAA-MM").
 * @param {{ipc: Object<string, number>, salarios: Object<string, Object<string, number>>}} indices
 * @param {{sueldo: number, desde: string, hasta?: string, sector?: string, sueldoActual?: number}} entrada
 */
export function calcular(indices, { sueldo, desde, hasta = null, sector = null, sueldoActual = null }) {
  const mesesIpc = Object.keys(indices.ipc).sort();
  hasta = hasta || mesesIpc[mesesIpc.length - 1];
  if (typeof sueldo !== "number" || !Number.isFinite(sueldo) || sueldo <= 0) {
    throw new ErrorCalculadora("sueldo_invalido", "El sueldo tiene que ser un número mayor a cero.");
  }
  if (sueldoActual !== null && !(sueldoActual > 0)) {
    throw new ErrorCalculadora("sueldo_invalido", "El sueldo actual tiene que ser un número mayor a cero.");
  }
  for (const mes of [desde, hasta]) {
    if (!(mes in indices.ipc)) {
      throw new ErrorCalculadora(
        "mes_fuera_de_rango",
        `No hay IPC para ${mes}: elegí un mes entre ${mesesIpc[0]} y ${mesesIpc[mesesIpc.length - 1]}.`
      );
    }
  }
  if (hasta < desde) {
    throw new ErrorCalculadora("periodo_invertido", "El mes final no puede ser anterior al inicial.");
  }

  const inflacion = variacion(indices.ipc, desde, hasta);
  const equivalente = sueldo * (1 + inflacion);
  const resultado = {
    desde,
    hasta,
    inflacion_pct: redondear(100 * inflacion, 2),
    sueldo_equivalente: redondear(equivalente, 2),
    sector: null,
    actual: null,
  };

  if (sector !== null) {
    if (!(sector in indices.salarios)) {
      throw new ErrorCalculadora("sector_desconocido", `Sector desconocido: ${sector}.`);
    }
    const serie = indices.salarios[sector];
    if (!(desde in serie)) {
      throw new ErrorCalculadora("mes_fuera_de_rango", `No hay índice de salarios para ${desde}.`);
    }
    const ultimoSector = Object.keys(serie).sort().pop();
    const hastaSector = hasta < ultimoSector ? hasta : ultimoSector;
    const aumento = variacion(serie, desde, hastaSector);
    const inflacionSector = variacion(indices.ipc, desde, hastaSector);
    resultado.sector = {
      sector,
      nombre: SECTORES[sector],
      hasta: hastaSector,
      aumento_pct: redondear(100 * aumento, 2),
      inflacion_pct: redondear(100 * inflacionSector, 2),
      sueldo_segun_sector: redondear(sueldo * (1 + aumento), 2),
      resultado_real_pct: redondear(100 * ((1 + aumento) / (1 + inflacionSector) - 1), 2),
    };
  }

  if (sueldoActual !== null) {
    resultado.actual = {
      sueldo_actual: sueldoActual,
      diferencia_pesos: redondear(sueldoActual - equivalente, 2),
      resultado_real_pct: redondear(100 * (sueldoActual / equivalente - 1), 2),
      ajuste_para_empatar_pct: redondear(100 * (equivalente / sueldoActual - 1), 2),
    };
  }
  return resultado;
}

// "1.234.567,89" / "1234567.89" / "$ 850000" -> número (formato es-AR primero).
export function leerMonto(texto) {
  if (texto === null || texto === undefined) return null;
  let limpio = String(texto).replace(/[\s$]/g, "");
  if (limpio === "") return null;
  if (limpio.includes(",")) {
    limpio = limpio.replace(/\./g, "").replace(",", ".");
  } else if (/^\d{1,3}(\.\d{3})+$/.test(limpio)) {
    limpio = limpio.replace(/\./g, "");
  }
  if (!/^\d+(\.\d+)?$/.test(limpio)) return NaN;
  return Number(limpio);
}
