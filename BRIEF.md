# Brief: InflationArg (borrar este archivo antes de abrir el PR)

Encargo de Juan (2026-10-21): un proyecto de portfolio **ultra pulido**, en **Python**, orientado a **análisis de datos / QA / BI**, con **base de datos**, que demuestre sus habilidades técnicas a reclutadores. Nada de "Java tryhard". Hay ~60 US$ de créditos de nube para esto: usarlos en **calidad y verificación**, no en relleno.

## Perfil de Juan (no inventar nada fuera de esto)

- **Juan Barros**, Caballito (CABA). Busca su **primer puesto como Analista de Datos Trainee/Junior**; secundarios: QA manual, BI/Reporting, Help Desk N1.
- UADE: Tecnicatura Univ. en Desarrollo de Software (2024–2027 est., le faltan 2 finales) + Lic. en Gestión de TI (en curso, 50 % aprobado).
- Experiencia: Soporte Técnico / Mesa de Ayuda en UNAB (2021–2023, remoto); Vendedor/Encargado en IDigital (2023–2024, +15 % ventas cruzadas); Administrador de propiedad turística Airbnb/Booking (2024–actualidad).
- Certificaciones: Full Stack (CoderHouse 2023), Excel Avanzado (Capacitarte 2022), Inglés B1 (Liceo Cultural Británico 2020).
- Skills: SQL, Python, Excel avanzado (tablas dinámicas, macros), MySQL, MongoDB, SQLite, Git/GitHub, Docker, testing manual, Scrum/Kanban. Español nativo, inglés B1.
- Contacto público: juanmbarrosf@gmail.com · linkedin.com/in/barrosjuan0 · github.com/JuanMBF. **No publicar el teléfono.**
- Otros proyectos suyos (enlazar desde la sección del autor): github.com/JuanMBF/Portfolio (HelpDesk Pro, Mongo Replica Lab, IT Support Toolkit), github.com/JuanMBF/ProyectoDB (scraper de precios de supermercados), github.com/JuanMBF/python (HelpDesk Pro en Python).

## El proyecto

Pregunta de negocio: **"¿Le ganaron los salarios a la inflación en Argentina? (2016–2026)"**, con datos oficiales (INDEC, BCRA, ANSES).

**Enfoque de RR.HH.:** no es "un análisis macro" sino una herramienta que usa cualquier área de Recursos Humanos o liquidación de sueldos del país: *¿cuánto hay que ajustar un sueldo para no perder contra la inflación?*

### Datos

Foto ya descargada en `data/raw/` con `MANIFEST.json` (URL, sha256, filas, rango de fechas). El `.gitattributes` de esa carpeta guarda los CSV byte a byte. El sandbox de la nube probablemente no llega a datos.gob.ar: **todo tiene que correr offline** desde la foto. La descarga online (`--online`) se usa en GitHub Actions y tiene que mandar un User-Agent propio: la API responde 403 al de urllib.

### Pipeline

Python 3.11+, pandas, SQLite, SQL en archivos `.sql`:

- extract (online u offline, verificación de sha256 contra el manifiesto) → staging → modelo estrella (`dim_fecha`, `dim_serie`, `fact_valor` en formato largo) → **vistas SQL** con CTEs y window functions (`LAG`, acumulados, ranking) → export.
- **`sql/consultas/`**: una consulta por pregunta de negocio, con un comentario arriba que diga qué responde y cómo se lee el resultado (es lo que mira un reclutador de datos).
- Un solo comando (`make all` o `python -m inflationarg all`) que corre todo offline en menos de un minuto.

### Preguntas a responder (todos los números salen de la base, nada hardcodeado)

1. Salario real por sector (registrado privado, público, no registrado) deflactado por IPC: ¿quién ganó, quién perdió y en qué períodos?
2. Inflación mensual e interanual; núcleo vs. regulados vs. estacionales; picos.
3. Rubros del IPC que más y menos subieron (acumulado y último año).
4. Poder de compra: cuántas Canastas Básicas Totales compra el RIPTE, el salario mínimo y la jubilación mínima.
5. Diferencias regionales (GBA, Pampeana, NEA, NOA, Cuyo, Patagonia).
6. Salario en dólares (RIPTE / tipo de cambio oficial de valuación).

### Calculadora de ajuste salarial

Sueldo y mes de referencia → sueldo equivalente hoy por IPC, comparación contra el índice de salarios del sector elegido, ganancia o pérdida en % y en pesos. Lógica en Python con tests, replicada en JS para el sitio con **los mismos casos de prueba** (un JSON de casos compartido que corren pytest y el test de JS).

### QA de datos (el ángulo QA del perfil: tiene que lucirse)

Suite de chequeos con reporte legible: completitud, unicidad de fecha+serie, fechas mensuales contiguas, base 100 donde corresponde (dic-2016 en IPC, oct-2016 en salarios), rangos, frescura y sha256 contra el manifiesto. Casos **reales** encontrados al bajar los datos, que el pipeline tiene que detectar y documentar:

- La API devolvió **vacías** 4 series (recreación, restaurantes, IPC NOA, RIPTE) que en los CSV de origen están completas → chequeo de consistencia API vs. CSV con `api_series_mensuales.csv`.
- **RIPTE agosto-2026 = junio-2026 exacto** (1.915.878,76): valor repetido sospechoso → alerta.
- **Salario mínimo con valores a futuro** hasta abr-2027 (ya fijados por resolución) → excluir del análisis y avisar.
- Las series terminan en meses distintos (salarios jul-2026, IPC sep-2026) → alinear y decir hasta cuándo vale cada conclusión.

### Excel y Power BI

- Export a `.xlsx` con openpyxl: tablas con formato, una hoja por pregunta, gráfico nativo si sale prolijo (conecta con "Excel avanzado" del CV).
- Modelo estrella exportado a CSV listo para **Power BI** + `docs/power-bi.md`: guía paso a paso para que Juan arme el dashboard él mismo (no se puede hacer en la nube: es una app de escritorio de Windows).

### Sitio web (GitHub Pages)

- Generado con **Python** (Jinja2), publicado con GitHub Actions en `https://juanmbf.github.io/InflationArg/` (respetar el base path en links y assets). Juan tiene que activar Pages una vez (Settings → Pages → Source: GitHub Actions) y mergear el PR: avisarle.
- Páginas: inicio con la respuesta a la pregunta en una frase, KPIs y gráfico principal; dashboard interactivo (librería por CDN con versión fija, p. ej. Apache ECharts) alimentado por el JSON que exporta el pipeline; la calculadora; metodología y QA de datos; y una sección **sobre el autor** con el perfil de Juan y links a sus otros proyectos (el sitio también funciona como su carta de presentación).
- Inspiración visual: elegir de <https://github.com/emmabostian/developer-portfolios> un portfolio de analista de datos que se parezca al perfil (candidatos: danialkhilji.github.io/portfolio, keerthana-raghu.vercel.app, khushm.netlify.app, chauhan-mihir.vercel.app). Tomar ideas de estructura, sin copiar código, y nombrarlo en el README.
- Pulido: modo claro/oscuro, responsive (375 / 768 / 1280), números en formato es-AR, accesible (contraste, foco, alt), Open Graph, favicon, sitemap, 404, sin trackers.
- QA del sitio: tests de build (todas las páginas renderizan, links internos válidos, JSON con esquema), validación HTML, auditoría de accesibilidad con Playwright + axe, capturas en `docs/` para el README.
- Workflow programado mensual: baja datos nuevos, corre la QA y, si pasa, redespliega; si falla, despliega con la foto.

### Repo

- pytest (transformaciones, vistas SQL con fixtures chicos, QA, calculadora, pipeline completo offline) + ruff, cobertura alta, CI en GitHub Actions.
- **README** en español impecable con un resumen corto en inglés al principio (algunas empresas piden inglés): hallazgos clave con gráficos, link al sitio en vivo, diagrama mermaid, diccionario de datos, sección de QA, cómo correrlo, sección del autor. Licencia MIT para el código; los datos son de datos.gob.ar (CC BY 4.0).

## Plazo

Tiene que estar en vivo antes de la **UADE Job Week del lunes 26/10/2026**, para que Juan lo muestre desde el celular en los stands. Primero una versión completa de punta a punta, después el pulido.

## Definición de terminado

Todo corre offline, tests y ruff en verde, el sitio se ve impecable en móvil y escritorio (verificado con capturas), textos revisados, cada número verificado contra los datos, `BRIEF.md` borrado, rama pusheada y PR listo para revisión contra `main`.
