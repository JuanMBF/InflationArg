// QA del sitio generado (build/site) con Playwright + axe-core.
//
//   node tests/sitio/qa_sitio.mjs [--capturas] [--solo-capturas]
//
// Sirve el sitio bajo /InflationArg/ (igual que GitHub Pages), y para cada página
// en 375/768/1280 px y en modo claro y oscuro verifica: sin errores de consola, sin
// scroll horizontal, gráficos dibujados y auditoría de accesibilidad (axe, WCAG 2.1 AA).
// También prueba los links internos, la calculadora y el menú móvil.
// ECharts se sirve desde node_modules (el CDN puede no estar disponible al testear).

import { createServer } from "node:http";
import { readFile, mkdir, stat } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const require = createRequire(import.meta.url);
const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const SITIO = path.join(RAIZ, "build", "site");
const CAPTURAS = path.join(RAIZ, "build", "capturas");
const BASE = "/InflationArg/";
const ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.min.js";
const PAGINAS = process.env.PAGINAS ? process.env.PAGINAS.split(",") : ["", "dashboard/", "calculadora/", "sql/", "metodologia/", "sobre-mi/", "no-existe/"];
const ANCHOS = [375, 768, 1280];
const TEMAS = ["light", "dark"];
const conCapturas = process.argv.includes("--capturas") || process.argv.includes("--solo-capturas");
const soloCapturas = process.argv.includes("--solo-capturas");

const TIPOS = {
  ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".xml": "application/xml", ".txt": "text/plain",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".zip": "application/zip",
  ".db": "application/vnd.sqlite3",
};

function servidor() {
  return createServer(async (req, res) => {
    const url = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if (!url.startsWith(BASE)) {
      res.writeHead(404).end();
      return;
    }
    let archivo = path.join(SITIO, url.slice(BASE.length));
    try {
      if ((await stat(archivo)).isDirectory()) archivo = path.join(archivo, "index.html");
      const cuerpo = await readFile(archivo);
      res.writeHead(200, { "content-type": TIPOS[path.extname(archivo)] || "application/octet-stream" }).end(cuerpo);
    } catch {
      res.writeHead(404, { "content-type": TIPOS[".html"] }).end(await readFile(path.join(SITIO, "404.html")));
    }
  });
}

const fallas = [];
function fallar(msj) {
  fallas.push(msj);
  console.log("  ✗ " + msj);
}

async function prepararPagina(navegador, origen, ancho, tema) {
  const contexto = await navegador.newContext({
    viewport: { width: ancho, height: 900 },
    colorScheme: tema,
    deviceScaleFactor: ancho <= 768 ? 2 : 1,
    reducedMotion: "reduce",
  });
  const echarts = await readFile(require.resolve("echarts/dist/echarts.min.js"));
  // Playwright prueba primero la ruta registrada al final: el bloqueo general va antes.
  await contexto.route(/^https?:\/\/(?!127\.0\.0\.1)/, (ruta) => ruta.abort());
  await contexto.route(ECHARTS_CDN, (ruta) =>
    ruta.fulfill({ body: echarts, contentType: "text/javascript", headers: { "access-control-allow-origin": "*" } })
  );
  const pagina = await contexto.newPage();
  const errores = [];
  pagina.on("console", (m) => m.type() === "error" && errores.push(m.text()));
  pagina.on("pageerror", (e) => errores.push(e.message));
  return { contexto, pagina, errores };
}

async function revisarPagina(navegador, origen, ruta, ancho, tema, axeFuente) {
  const nombre = `${ruta.replace(/\/$/, "") || "inicio"} ${ancho}px ${tema}`;
  const { contexto, pagina, errores } = await prepararPagina(navegador, origen, ancho, tema);
  await pagina.goto(origen + BASE + ruta, { waitUntil: "networkidle" });
  // QA_FUENTE="DejaVu Sans" reproduce las fuentes más anchas de los runners de Ubuntu.
  if (process.env.QA_FUENTE) {
    await pagina.addStyleTag({ content: `*{font-family:"${process.env.QA_FUENTE}"!important}` });
  }
  await pagina.waitForTimeout(300);

  if (!soloCapturas) {
    const desborde = await pagina.evaluate(() => {
      const exceso = document.documentElement.scrollWidth - window.innerWidth;
      const culpable = [...document.querySelectorAll("body *")].find(
        (e) => {
          if (e.getBoundingClientRect().right <= window.innerWidth + 1) return false;
          for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) {
            if (getComputedStyle(a).overflowX !== "visible") return false;
          }
          return true;
        }
      );
      return { exceso, culpable: culpable ? culpable.tagName.toLowerCase() + "." + culpable.className + " " + (culpable.textContent || "").slice(0, 40) : "" };
    });
    if (desborde.exceso > 1) fallar(`${nombre}: scroll horizontal de ${desborde.exceso}px (${desborde.culpable})`);

    const graficos = await pagina.$$eval("[data-grafico]", (els) =>
      els.map((el) => ({ id: el.id, ok: !!el.querySelector("svg") }))
    );
    for (const g of graficos) if (!g.ok) fallar(`${nombre}: el gráfico ${g.id} no se dibujó`);

    {
      await pagina.addScriptTag({ content: axeFuente });
      const resultado = await pagina.evaluate(async () => {
        // Abrir los <details> para auditar también las tablas.
        document.querySelectorAll("details").forEach((d) => (d.open = true));
        return await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] } });
      });
      for (const v of resultado.violations) {
        fallar(`${nombre}: axe ${v.id} (${v.impact}) en ${v.nodes.length} nodo(s): ${v.nodes[0].target.join(" ")}`);
      }
      await pagina.evaluate(() => document.querySelectorAll("details").forEach((d) => (d.open = false)));
    }
    // La 404 se pide a propósito: su error de red es esperado.
    const relevantes = errores.filter((e) => !(ruta === "no-existe/" && e.includes("404")));
    if (relevantes.length) fallar(`${nombre}: errores de consola: ${relevantes.join(" | ")}`);
  }

  if (conCapturas) {
    await mkdir(CAPTURAS, { recursive: true });
    const archivo = `${(ruta.replace(/\/$/, "") || "inicio").replace("/", "-")}-${ancho}-${tema}.png`;
    await pagina.screenshot({ path: path.join(CAPTURAS, archivo), fullPage: true });
  }
  await contexto.close();
}

async function revisarLinks(navegador, origen) {
  const { contexto, pagina } = await prepararPagina(navegador, origen, 1280, "light");
  const vistos = new Set();
  const pendientes = PAGINAS.filter((p) => p !== "no-existe/").map((p) => BASE + p);
  const enlaces = new Map();
  for (const ruta of pendientes) {
    await pagina.goto(origen + ruta);
    const hrefs = await pagina.$$eval("a[href], link[href], script[src]", (els) =>
      els.map((e) => e.getAttribute("href") || e.getAttribute("src"))
    );
    for (const h of hrefs) if (h.startsWith("/") || h.startsWith("#")) enlaces.set(h.startsWith("#") ? ruta + h : h, ruta);
  }
  for (const [enlace, origenPagina] of enlaces) {
    const [ruta, ancla] = enlace.split("#");
    if (!vistos.has(ruta)) {
      vistos.add(ruta);
      const r = await pagina.request.get(origen + ruta);
      if (r.status() !== 200) fallar(`link roto ${ruta} (desde ${origenPagina}): HTTP ${r.status()}`);
    }
    if (ancla) {
      await pagina.goto(origen + ruta);
      if (!(await pagina.$("#" + CSS.escape(ancla)))) fallar(`ancla inexistente ${enlace} (desde ${origenPagina})`);
    }
  }
  const r404 = await pagina.request.get(origen + BASE + "no-existe/");
  if (r404.status() !== 404) fallar("una página inexistente no devuelve 404");
  console.log(`  ✓ ${vistos.size} rutas internas revisadas`);
  await contexto.close();
}

// CSS.escape no existe en Node: alcanza con esta versión para ids simples.
const CSS = { escape: (s) => s.replace(/([^\w-])/g, "\\$1") };

async function revisarCalculadora(navegador, origen) {
  const { contexto, pagina, errores } = await prepararPagina(navegador, origen, 375, "light");
  await pagina.goto(origen + BASE + "calculadora/");
  await pagina.fill("#sueldo", "abc");
  await pagina.click("button[type=submit]");
  if (!(await pagina.isVisible("#error"))) fallar("calculadora: no muestra error con un sueldo inválido");
  await pagina.fill("#sueldo", "1.000.000");
  await pagina.selectOption("#desde", "2024-01");
  await pagina.fill("#actual", "2.500.000");
  await pagina.click("button[type=submit]");
  // Los meses usan guion no separable (U+2011): se normaliza para comparar.
  const leer = async (selector) => ((await pagina.textContent(selector)) || "").replace(/\u2011/g, "-");
  const texto = await leer("#resultado-cuerpo");
  if (!/\$\s?[\d.]+/.test(texto) || !texto.includes("ene-2024")) fallar("calculadora: el resultado no aparece");
  // Si el sueldo actual es justo el equivalente, empata: ni ▲ ni ▼.
  const equivalente = (await leer(".resultado__principal")).replace(/[^\d]/g, "");
  await pagina.fill("#actual", equivalente);
  await pagina.click("button[type=submit]");
  const empate = pagina.locator(".veredicto", { hasText: "empata con la inflación" });
  if ((await empate.count()) !== 1 || (await empate.getAttribute("class")) !== "veredicto") {
    fallar("calculadora: un sueldo actual igual al equivalente no se muestra como empate");
  }
  if (await pagina.isVisible("#error")) fallar("calculadora: muestra error con datos válidos");
  // Mes inicial posterior al último dato del sector: calcula el IPC y avisa (sin error ni veredicto).
  await pagina.selectOption("#desde", "2026-08");
  await pagina.fill("#actual", "");
  await pagina.click("button[type=submit]");
  const aviso = await leer("#resultado-cuerpo");
  if (await pagina.isVisible("#error") || !aviso.includes("llega hasta") || aviso.includes("le ganaron")) {
    fallar("calculadora: con un mes inicial sin datos del sector no muestra el ajuste por IPC con el aviso");
  }
  // Un error nuevo no puede convivir con el resultado anterior.
  await pagina.fill("#sueldo", "abc");
  await pagina.click("button[type=submit]");
  if ((await pagina.textContent("#resultado-cuerpo")).includes("$")) fallar("calculadora: queda un resultado viejo junto al error");
  if (errores.length) fallar("calculadora: errores de consola: " + errores.join(" | "));
  console.log("  ✓ calculadora: validación, resultado y avisos");

  await pagina.goto(origen + BASE + "dashboard/", { waitUntil: "networkidle" });
  const antes = await leer("#lectura-base");
  await pagina.selectOption("#base-salario", "2023-12");
  const despues = await leer("#lectura-base");
  if (!antes.startsWith("Desde dic-2016") || !despues.startsWith("Entre dic-2023") || antes === despues) {
    fallar(`dashboard: el selector de mes base no actualiza la lectura (${antes} → ${despues})`);
  }
  const etiqueta = await pagina.locator("#g-salario-real svg text", { hasText: "dic-2023 = 100" }).count();
  if (!etiqueta) fallar("dashboard: el gráfico no se rebasó al cambiar el mes base");
  console.log("  ✓ dashboard: selector de mes base");

  await pagina.goto(origen + BASE);
  const nav = pagina.locator("#navegacion");
  if (await nav.isVisible()) fallar("menú móvil: la navegación debería empezar cerrada en 375px");
  await pagina.click(".menu-boton");
  if (!(await nav.isVisible())) fallar("menú móvil: no se abre");
  await pagina.keyboard.press("Escape");
  if (await nav.isVisible()) fallar("menú móvil: Escape no lo cierra");
  console.log("  ✓ menú móvil");
  await contexto.close();
}

const http = servidor();
await new Promise((ok) => http.listen(0, "127.0.0.1", ok));
const origen = `http://127.0.0.1:${http.address().port}`;
const navegador = await chromium.launch(
  process.env.PLAYWRIGHT_CHROMIUM ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM } : {}
);
const axeFuente = await readFile(require.resolve("axe-core/axe.min.js"), "utf8");

try {
  for (const ruta of PAGINAS) {
    for (const ancho of ANCHOS) {
      for (const tema of TEMAS) await revisarPagina(navegador, origen, ruta, ancho, tema, axeFuente);
    }
    console.log(`  ✓ ${BASE}${ruta}`);
  }
  if (!soloCapturas) {
    await revisarLinks(navegador, origen);
    await revisarCalculadora(navegador, origen);
  }
} finally {
  await navegador.close();
  http.close();
}

if (fallas.length) {
  console.log(`\n${fallas.length} problema(s) en el sitio.`);
  process.exit(1);
}
console.log("\nQA del sitio: todo en orden.");
