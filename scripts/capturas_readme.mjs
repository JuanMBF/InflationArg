// Capturas del sitio para el README (docs/capturas/). Correr antes `python -m inflationarg all`.
//
//   node scripts/capturas_readme.mjs

import { createServer } from "node:http";
import { readFile, mkdir, stat } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SITIO = path.join(RAIZ, "build", "site");
const DESTINO = path.join(RAIZ, "docs", "capturas");
const BASE = "/InflationArg/";
const TIPOS = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml", ".png": "image/png" };

const http = createServer(async (req, res) => {
  let archivo = path.join(SITIO, decodeURIComponent(new URL(req.url, "http://x").pathname).slice(BASE.length));
  try {
    if ((await stat(archivo)).isDirectory()) archivo = path.join(archivo, "index.html");
    res.writeHead(200, { "content-type": TIPOS[path.extname(archivo)] || "application/octet-stream" }).end(await readFile(archivo));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((ok) => http.listen(0, "127.0.0.1", ok));
const origen = `http://127.0.0.1:${http.address().port}${BASE}`;
const echarts = await readFile(require.resolve("echarts/dist/echarts.min.js"));

const navegador = await chromium.launch();
async function captura(nombre, ruta, { ancho, alto, tema = "light", antes, selector, recorte }) {
  const contexto = await navegador.newContext({
    viewport: { width: ancho, height: alto }, colorScheme: tema, deviceScaleFactor: 2, reducedMotion: "reduce",
  });
  await contexto.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await contexto.route(/cdn\.jsdelivr\.net\/npm\/echarts/, (r) =>
    r.fulfill({ body: echarts, contentType: "text/javascript", headers: { "access-control-allow-origin": "*" } })
  );
  const pagina = await contexto.newPage();
  await pagina.goto(origen + ruta, { waitUntil: "networkidle" });
  if (antes) await antes(pagina);
  await pagina.waitForTimeout(400);
  const destino = path.join(DESTINO, nombre);
  if (selector) await pagina.locator(selector).screenshot({ path: destino });
  else await pagina.screenshot({ path: destino, clip: recorte });
  await contexto.close();
  console.log("  " + nombre);
}

await mkdir(DESTINO, { recursive: true });
await captura("inicio-escritorio.png", "", { ancho: 1280, alto: 900 });
await captura("inicio-movil.png", "", { ancho: 375, alto: 812 });
await captura("dashboard-oscuro-movil.png", "dashboard/#salario-real", { ancho: 375, alto: 812, tema: "dark" });
await captura("salario-real.png", "dashboard/", { ancho: 1100, alto: 900, selector: "#salario-real" });
await captura("canastas.png", "dashboard/", { ancho: 1100, alto: 900, selector: "#canastas" });
await captura("rubros.png", "dashboard/", { ancho: 1100, alto: 900, selector: "#rubros" });
await captura("calculadora.png", "calculadora/", {
  ancho: 1280,
  alto: 1000,
  antes: async (p) => {
    await p.fill("#sueldo", "1.000.000");
    await p.selectOption("#desde", "2025-01");
    await p.fill("#actual", "1.300.000");
    await p.click("button[type=submit]");
  },
  selector: ".calculadora",
});
await captura("qa.png", "metodologia/", { ancho: 1100, alto: 900, selector: ".qa-lista" });
await captura("sql.png", "sql/", {
  ancho: 1100,
  alto: 900,
  antes: async (p) => p.locator("#consulta-01_respuesta_principal details.codigo-detalle summary").click(),
  selector: "#consulta-01_respuesta_principal",
});
await navegador.close();
http.close();
