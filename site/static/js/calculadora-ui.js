// Interfaz de la calculadora: lee el formulario, llama a calcular() y muestra el resultado.
import { calcular, ErrorCalculadora, leerMonto } from "./calculadora.js";

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const indices = JSON.parse(document.getElementById("datos-indices").textContent);
const form = document.getElementById("form-calculadora");
const cuerpo = document.getElementById("resultado-cuerpo");
const error = document.getElementById("error");

// Espacio no separable: "$ 1.000" y "12,3 %" no se cortan entre líneas.
const pesos = (v) =>
  "$\u00a0" + new Intl.NumberFormat("es-AR", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v);
const pct = (v, signo = false) =>
  (signo && v > 0 ? "+" : "") +
  new Intl.NumberFormat("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v).replace("-", "−") +
  "\u00a0%";
const mes = (aaaamm) => MESES[Number(aaaamm.slice(5, 7)) - 1] + "-" + aaaamm.slice(0, 4);

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

function dato(valor, etiqueta) {
  return `<div class="dato"><p class="dato__valor">${valor}</p><p class="dato__etiqueta">${etiqueta}</p></div>`;
}

function mostrar(r, sueldo) {
  let html = `
    <p class="resultado__principal">${pesos(r.sueldo_equivalente)}</p>
    <p class="resultado__etiqueta">es lo que hay que cobrar en ${mes(r.hasta)} para tener el mismo poder de compra que
    ${pesos(sueldo)} en ${mes(r.desde)}.</p>
    <div class="resultado__grilla">
      ${dato(pct(r.inflacion_pct), `Inflación entre ${mes(r.desde)} y ${mes(r.hasta)}`)}
      ${dato(pesos(r.sueldo_equivalente - sueldo), "Aumento necesario sobre el sueldo mensual")}`;
  if (r.sector) {
    const s = r.sector;
    html += `
      ${dato(pct(s.aumento_pct), `Aumento salarial del sector ${escapar(s.nombre.toLowerCase())} hasta ${mes(s.hasta)}`)}
      ${dato(pesos(s.sueldo_segun_sector), "Sueldo si hubiera seguido al sector")}`;
  }
  html += `</div>`;
  if (r.aviso_sector) {
    html += `<p class="nota">${escapar(r.aviso_sector)}</p>`;
  }
  if (r.sector) {
    const s = r.sector;
    const gana = s.resultado_real_pct >= 0;
    const empate = Math.abs(s.resultado_real_pct) < 0.05;
    const clase = empate ? "veredicto" : `veredicto veredicto--${gana ? "gana" : "pierde"}`;
    html += `<p class="${clase}">
      ${empate ? "=" : gana ? "▲" : "▼"} Entre ${mes(r.desde)} y ${mes(s.hasta)} los salarios del sector
      ${escapar(s.nombre.toLowerCase())} ${
        empate
          ? "empataron con la inflación."
          : `${gana ? "le ganaron" : "le perdieron"} a la inflación por ${pct(Math.abs(s.resultado_real_pct))} en términos reales.`
      }</p>`;
  }
  if (r.actual) {
    const a = r.actual;
    const gana = a.diferencia_pesos >= 0;
    html += Math.abs(a.resultado_real_pct) < 0.05
      ? `<p class="veredicto">= Con ${pesos(a.sueldo_actual)} en ${mes(r.hasta)}, el sueldo empata con la inflación.</p>`
      : gana
      ? `<p class="veredicto veredicto--gana">▲ Con ${pesos(a.sueldo_actual)} en ${mes(r.hasta)}, se cobra ${pesos(a.diferencia_pesos)}
         más de lo necesario: ${pct(a.resultado_real_pct, true)} real.</p>`
      : `<p class="veredicto veredicto--pierde">▼ Con ${pesos(a.sueldo_actual)} en ${mes(r.hasta)}, faltan ${pesos(-a.diferencia_pesos)}
         por mes: hay que ajustar ${pct(a.ajuste_para_empatar_pct)} para empatar con la inflación
         (pérdida real de ${pct(Math.abs(a.resultado_real_pct))}).</p>`;
  }
  // Guion no separable: "feb-2026" no se corta entre líneas.
  cuerpo.innerHTML = html.replace(/\b([a-z]{3})-(\d{4})\b/g, "$1\u2011$2");
}

function marcarError(campo, mensaje) {
  error.textContent = mensaje;
  error.hidden = false;
  if (campo) {
    campo.setAttribute("aria-invalid", "true");
    campo.focus();
  }
}

form.addEventListener("submit", (evento) => {
  evento.preventDefault();
  error.hidden = true;
  // Nunca mostrar un resultado viejo junto a un error nuevo.
  cuerpo.innerHTML = '<p class="nota">Completá el sueldo y tocá <strong>Calcular</strong>.</p>';
  form.querySelectorAll("[aria-invalid]").forEach((c) => c.removeAttribute("aria-invalid"));

  const sueldo = leerMonto(form.sueldo.value);
  const actualTexto = form.actual.value.trim();
  const actual = actualTexto === "" ? null : leerMonto(actualTexto);
  if (!(sueldo > 0)) return marcarError(form.sueldo, "Ingresá un sueldo válido, por ejemplo 850.000.");
  if (actual !== null && !(actual > 0)) return marcarError(form.actual, "El sueldo actual no es un número válido.");

  try {
    const r = calcular(indices, {
      sueldo,
      desde: form.desde.value,
      hasta: form.hasta.value,
      sector: form.sector.value || null,
      sueldoActual: actual,
    });
    mostrar(r, sueldo);
  } catch (e) {
    if (e instanceof ErrorCalculadora) {
      marcarError(e.codigo === "periodo_invertido" ? form.hasta : null, e.message);
    } else {
      throw e;
    }
  }
});
