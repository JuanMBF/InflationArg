// Genera site/static/img/og.png (1200×630) y apple-touch-icon.png (180×180) con Playwright.
// Usa los datos del pipeline: correr antes `python -m inflationarg all`.
//
//   node scripts/generar_imagenes.mjs

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DESTINO = path.join(RAIZ, "site", "static", "img");
const datos = JSON.parse(await readFile(path.join(RAIZ, "build", "datos", "dashboard.json"), "utf8"));

const g = datos.graficos.salario_real;
const series = [
  ["sal_privado", "#2a78d6", ""],
  ["sal_publico", "#eb6834", ""],
  ["sal_no_registrado", "#1baf7a", ""],
  ["sal_total", "#121211", "6 5"],
];
const [W, H, x0, y0] = [560, 330, 10, 10];
const valores = series.flatMap(([id]) => g.series[id]).filter((v) => v !== null);
const [vMin, vMax] = [Math.floor(Math.min(...valores) / 10) * 10, Math.ceil(Math.max(...valores) / 10) * 10];
const x = (i) => x0 + (i / (g.fechas.length - 1)) * (W - 2 * x0);
const y = (v) => y0 + (1 - (v - vMin) / (vMax - vMin)) * (H - 2 * y0);
const lineas = series
  .map(([id, color, guion]) => {
    const d = g.series[id]
      .map((v, i) => (v === null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`))
      .filter(Boolean)
      .join(" L");
    return `<path d="M${d}" fill="none" stroke="${color}" stroke-width="4" stroke-linejoin="round" stroke-dasharray="${guion}"/>`;
  })
  .join("");
const total = datos.kpis.salario_real_total;
const pct = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(
  Math.abs(total.var_real_pct)
);

const og = `<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;width:1200px;height:630px;background:#f7f7f4;font-family:system-ui,"Segoe UI",Roboto,sans-serif;color:#121211}
  .marco{display:flex;height:100%;padding:64px;box-sizing:border-box;gap:40px;align-items:center}
  .texto{flex:1} .ante{color:#1f63b8;font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:20px;margin:0 0 20px}
  h1{font-size:60px;line-height:1.05;letter-spacing:-.03em;margin:0 0 24px}
  .resp{font-size:30px;line-height:1.3;margin:0;color:#4c4b47} .resp b{color:#b42323}
  .pie{margin-top:36px;font-size:20px;color:#6c6b66}
  .graf{width:560px;height:330px;background:#fdfdfb;border:1px solid rgba(0,0,0,.1);border-radius:18px;padding:16px}
</style></head><body><div class="marco"><div class="texto">
  <p class="ante">InflationArg · Python + SQL</p>
  <h1>¿Le ganaron los salarios a la inflación?</h1>
  <p class="resp"><b>No.</b> El salario real promedio cayó ${pct} % entre dic-2016 y ${total.hasta}.</p>
  <p class="pie">Datos oficiales INDEC · BCRA · ANSES — Juan Barros</p>
</div><div class="graf"><svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
  <line x1="${x0}" x2="${W - x0}" y1="${y(100)}" y2="${y(100)}" stroke="#c3c2b7" stroke-dasharray="4 4" stroke-width="2"/>
  ${lineas}</svg></div></div></body></html>`;

const icono = `<!doctype html><html><body style="margin:0"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="180" height="180" style="display:block">
  <rect width="32" height="32" fill="#1f63b8"/>
  <path d="M7 22 L13 15 L18 19 L25 10" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</svg></body></html>`;

const navegador = await chromium.launch();
const pagina = await navegador.newPage({ viewport: { width: 1200, height: 630 } });
await pagina.setContent(og);
await pagina.screenshot({ path: path.join(DESTINO, "og.png") });
await pagina.setViewportSize({ width: 180, height: 180 });
await pagina.setContent(icono);
await pagina.screenshot({ path: path.join(DESTINO, "apple-touch-icon.png") });
await navegador.close();
console.log("Imágenes generadas en site/static/img/");
