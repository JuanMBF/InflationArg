"""Generador del sitio estático (Jinja2) para GitHub Pages.

Todas las cifras y frases con números se arman acá a partir del JSON que exporta
el pipeline: no hay números escritos a mano en las plantillas.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import zipfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from . import config, formato

SITE_URL = "https://juanmbf.github.io/InflationArg/"
REPO_URL = "https://github.com/JuanMBF/InflationArg"
ECHARTS = {
    "url": "https://cdn.jsdelivr.net/npm/echarts@6.0.0/dist/echarts.min.js",
    "sri": "sha384-F07Cpw5v8spSU0H113F33m2NQQ/o6GqPTnTjf45ssG4Q6q58ZwhxBiQtIaqvnSpR",
}

PAGINAS = [
    # (ruta, plantilla, título de navegación, título de la página, descripción)
    (
        "",
        "index.html",
        "Inicio",
        "¿Le ganaron los salarios a la inflación?",
        "Análisis de datos oficiales de Argentina 2016–2026: salario real por sector, inflación, "
        "canastas y salario en dólares. Python, SQL y QA de datos.",
    ),
    (
        "dashboard/",
        "dashboard.html",
        "Dashboard",
        "Dashboard interactivo",
        "Salario real, inflación, rubros, canastas, regiones y salario en dólares en gráficos interactivos.",
    ),
    (
        "calculadora/",
        "calculadora.html",
        "Calculadora",
        "Calculadora de ajuste salarial",
        "¿Cuánto hay que ajustar un sueldo para no perder contra la inflación? Calculadora con IPC del INDEC.",
    ),
    (
        "sql/",
        "sql.html",
        "SQL",
        "Modelo de datos y consultas SQL",
        "Modelo estrella en SQLite, vistas con window functions y una consulta por pregunta de negocio.",
    ),
    (
        "metodologia/",
        "metodologia.html",
        "Metodología y QA",
        "Metodología y QA de datos",
        "Fuentes, método de cálculo, chequeos automáticos de calidad de datos y anomalías encontradas.",
    ),
    (
        "sobre-mi/",
        "sobre-mi.html",
        "Sobre mí",
        "Juan Barros – Analista de datos",
        "Juan Barros: analista de datos trainee/junior en Buenos Aires. SQL, Python, Excel, QA y BI.",
    ),
]

ETIQUETAS = {
    "serie_id": "Serie",
    "nombre": "Serie",
    "hasta": "Hasta",
    "indice_real": "Índice real",
    "var_real_pct": "Var. real %",
    "maximo": "Máximo",
    "fecha_maximo": "Mes del máximo",
    "minimo": "Mínimo",
    "fecha_minimo": "Mes del mínimo",
    "distancia_al_maximo_pct": "Distancia al máximo %",
    "ranking": "Puesto",
    "anio": "Año",
    "privado_registrado": "Privado registrado %",
    "publico": "Público %",
    "no_registrado": "No registrado %",
    "total": "Total %",
    "ganador": "Ganó",
    "perdedor": "Perdió",
    "puesto": "Puesto",
    "mes": "Mes",
    "inflacion_mensual_pct": "Mensual %",
    "inflacion_interanual_pct": "Interanual %",
    "puesto_interanual": "Puesto interanual",
    "nivel_general": "Nivel general %",
    "nucleo": "Núcleo %",
    "regulados": "Regulados %",
    "estacionales": "Estacionales %",
    "regulados_menos_nucleo": "Regulados − núcleo (pp)",
    "puesto_acumulado": "Puesto",
    "rubro": "Rubro",
    "veces": "Veces",
    "acumulado_desde_dic2016_pct": "Acumulado desde dic-2016 %",
    "acumulado_vs_general_pct": "Vs. nivel general %",
    "puesto_ultimo_anio": "Puesto último año",
    "ultimo_anio_pct": "Último año %",
    "ultimo_anio_vs_general_pp": "Vs. general (pp)",
    "cbt_pesos": "CBT ($)",
    "cbt_por_ripte": "CBT por RIPTE",
    "cbt_por_salario_minimo": "CBT por salario mínimo",
    "cbt_por_jubilacion_minima": "CBT por jubilación mínima",
    "es_ultimo": "Último",
    "region": "Región",
    "interanual_pct": "Interanual %",
    "diferencia_vs_pais_pp": "Vs. país (pp)",
    "meses": "Meses",
    "ripte_usd": "RIPTE (US$)",
    "salario_minimo_usd": "Salario mínimo (US$)",
    "jubilacion_minima_usd": "Jubilación mínima (US$)",
    "tipo_cambio_promedio": "Tipo de cambio ($/US$)",
    "analisis": "Análisis",
    "vale_hasta": "Vale hasta",
    "grupos": "Grupos de series",
    "rezago_maximo_meses": "Rezago máx. (meses)",
}

# Columnas que no aportan a la tabla del sitio.
OCULTAS = {"serie_id", "es_ultimo", "grupos", "region"}

PALABRAS_SQL = (
    "WITH RECURSIVE|WITH|SELECT|FROM|WHERE|JOIN|LEFT JOIN|CROSS JOIN|ON|AND|OR|AS|GROUP BY|ORDER BY|"
    "PARTITION BY|OVER|WINDOW|ROWS BETWEEN|UNBOUNDED PRECEDING|CURRENT ROW|CASE|WHEN|THEN|ELSE|END|"
    "IS NOT NULL|IS NULL|NOT|IN|LIMIT|DESC|ASC|UNION ALL|VALUES|DISTINCT|INSERT INTO|CREATE VIEW|BETWEEN"
)
FUNCIONES_SQL = "LAG|RANK|ROW_NUMBER|FIRST_VALUE|MAX|MIN|AVG|COUNT|SUM|ROUND|GROUP_CONCAT|substr|date|strftime"


def resaltar_sql(sql: str) -> Markup:
    """Resaltado mínimo de SQL (comentarios, palabras clave, funciones, textos) sin JS."""
    salida = []
    for linea in html.escape(sql).splitlines():
        codigo, _, comentario = linea.partition("--")
        codigo = re.sub(r"(&#x27;[^&]*?&#x27;)", r'<span class="s">\1</span>', codigo)
        codigo = re.sub(rf"\b({PALABRAS_SQL})\b", r'<span class="k">\1</span>', codigo)
        codigo = re.sub(rf"\b({FUNCIONES_SQL})(?=\()", r'<span class="f">\1</span>', codigo)
        if _:
            codigo += f'<span class="c">--{comentario}</span>'
        salida.append(codigo)
    return Markup("\n".join(salida))


def celda(valor, columna: str) -> str:
    if valor is None:
        return "–"
    if isinstance(valor, float):
        if columna in {"cbt_pesos"}:
            return formato.numero(valor, 0)
        decimales = 1 if columna in {"veces", "acumulado_desde_dic2016_pct", "acumulado_vs_general_pct"} else 2
        if columna.endswith("_usd"):
            decimales = 0
        return formato.numero(valor, decimales)
    if isinstance(valor, int) and columna in {"anio"}:
        return str(valor)
    if isinstance(valor, int):
        return formato.numero(valor, 0)
    if isinstance(valor, str) and re.fullmatch(r"\d{4}-\d{2}-01", valor):
        return formato.mes(valor)
    if isinstance(valor, str) and valor.startswith("Salarios – "):
        return valor.removeprefix("Salarios – ").capitalize()
    if isinstance(valor, str) and valor.startswith("IPC nivel general – "):
        return valor.removeprefix("IPC nivel general – ")
    return str(valor)


def clase_celda(valor, columna: str) -> str:
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        signo = ""
        if columna.endswith(("_pct", "_pp")) or columna in {"privado_registrado", "publico", "no_registrado", "total"}:
            signo = " neg" if valor < 0 else ""
        return "num" + signo
    return ""


# ---------------------------------------------------------------------------
# Textos derivados de los datos
# ---------------------------------------------------------------------------


def _mes_largo(etiqueta: str) -> str:
    """ "jul-2026" -> "julio de 2026"."""
    m, anio = etiqueta.split("-")
    return f"{formato.MESES_LARGOS[formato.MESES.index(m)]} de {anio}"


def textos(datos: dict) -> dict:
    k = datos["kpis"]
    c = datos["consultas"]
    total = k["salario_real_total"]
    sectores = [f for f in c["01_respuesta_principal"]["filas"] if f["serie_id"] not in {"sal_total", "sal_registrado"}]
    peor = min(sectores, key=lambda f: f["indice_real"])
    mejor = max(sectores, key=lambda f: f["indice_real"])
    nombre = lambda f: f["nombre"].removeprefix("Salarios – ")  # noqa: E731

    gano = total["indice_real"] >= 100
    respuesta_corta = "Sí." if gano else "No."
    respuesta_resto = (
        f"En {_mes_largo(total['hasta'])} el salario promedio compraba "
        f"{formato.porcentaje(abs(total['var_real_pct']), 1)} {'más' if gano else 'menos'} "
        "que en diciembre de 2016."
    )
    detalle = (
        f"Perdieron todos los sectores, pero no por igual: el {nombre(peor)} quedó "
        f"{formato.porcentaje(peor['var_real_pct'], 1)} y el {nombre(mejor)}, "
        f"{formato.porcentaje(mejor['var_real_pct'], 1)}."
        if all(f["indice_real"] < 100 for f in sectores)
        else f"El {nombre(mejor)} terminó en {formato.porcentaje(mejor['var_real_pct'], 1, signo=True)} "
        f"y el {nombre(peor)} en {formato.porcentaje(peor['var_real_pct'], 1, signo=True)}."
    )

    recuperacion = 100 * (total["indice_real"] / total["minimo"] - 1)
    rubros = c["05_rubros_ranking"]["filas"]
    regiones = [f for f in c["07_regiones"]["filas"] if f["region"] != "nacional"]
    reg_max = max(regiones, key=lambda f: f["interanual_pct"])
    reg_min = min(regiones, key=lambda f: f["interanual_pct"])
    canastas = k["canastas_ripte"]
    usd = k["ripte_usd"]
    poder = datos["graficos"]["poder_compra"]
    debajo_smvm = next(
        (
            poder["fechas"][i]
            for i, v in enumerate(poder["series"]["smvm"])
            if v is not None and v < 1 and all(x is None or x < 1 for x in poder["series"]["smvm"][i:])
        ),
        None,
    )
    usd_min = min(c["08_salario_en_dolares"]["filas"], key=lambda f: f["ripte_usd"])
    ipc_nacional = next(f for f in c["07_regiones"]["filas"] if f["region"] == "nacional")
    veces_general = 1 + ipc_nacional["acumulado_desde_dic2016_pct"] / 100
    usd_abajo = usd["ultimo"]["ripte_usd"] < usd["inicio"]["ripte_usd"]

    hallazgos = [
        {
            "titulo": f"El piso fue en {total['fecha_minimo'][-4:]} y la recuperación "
            + ("es parcial" if total["distancia_al_maximo_pct"] < 0 else "ya es completa"),
            "texto": f"En {_mes_largo(total['fecha_minimo'])} el salario real total tocó "
            f"{formato.numero(total['minimo'], 1)} puntos (dic-2016 = 100). Desde ahí recuperó "
            f"{formato.porcentaje(recuperacion, 1)}, pero sigue "
            f"{formato.porcentaje(abs(total['distancia_al_maximo_pct']), 1)} debajo de su máximo "
            f"de {total['fecha_maximo']}.",
            "enlace": "dashboard/#salario-real",
        },
        {
            "titulo": f"{_mes_largo(k['pico_mensual']['mes']).capitalize()}, el peor mes",
            "texto": "La inflación mensual llegó a "
            f"{formato.porcentaje(k['pico_mensual']['inflacion_mensual_pct'], 1)} en {k['pico_mensual']['mes']} "
            "y la interanual tocó "
            f"{formato.porcentaje(k['pico_interanual']['inflacion_interanual_pct'], 1)} en "
            f"{k['pico_interanual']['mes']}. En {k['inflacion_mensual']['mes']} fue "
            f"{formato.porcentaje(k['inflacion_mensual']['valor'], 1)} mensual y "
            f"{formato.porcentaje(k['inflacion_interanual']['valor'], 1)} interanual.",
            "enlace": "dashboard/#inflacion",
        },
        {
            "titulo": f"{rubros[0]['rubro']} subió más que todo",
            "texto": f"Desde dic-2016 los precios se multiplicaron por {formato.numero(veces_general, 1)} en promedio; "
            f"{rubros[0]['rubro'].lower()}, por {formato.numero(rubros[0]['veces'], 1)} y "
            f"{rubros[-1]['rubro'].lower()}, por {formato.numero(rubros[-1]['veces'], 1)}.",
            "enlace": "dashboard/#rubros",
        },
        {
            "titulo": (
                "El salario mínimo ya no cubre una canasta" if debajo_smvm else "Cuántas canastas compra cada ingreso"
            ),
            "texto": f"El salario promedio (RIPTE) compraba {formato.numero(canastas['inicio']['cbt_por_ripte'], 2)} "
            f"Canastas Básicas Totales en {canastas['inicio']['mes']} y "
            f"{formato.numero(canastas['ultimo']['cbt_por_ripte'], 2)} en {canastas['ultimo']['mes']}. "
            f"El salario mínimo compra {formato.numero(canastas['ultimo']['cbt_por_salario_minimo'], 2)} canastas"
            + (f": está por debajo de 1 desde {formato.mes(debajo_smvm + '-01')}." if debajo_smvm else "."),
            "enlace": "dashboard/#canastas",
        },
        {
            "titulo": "La inflación no fue igual en todo el país",
            "texto": f"En el último año {reg_max['nombre'].removeprefix('IPC nivel general – ')} tuvo la inflación "
            f"más alta ({formato.porcentaje(reg_max['interanual_pct'], 1)}) y "
            f"{reg_min['nombre'].removeprefix('IPC nivel general – ')} la más baja "
            f"({formato.porcentaje(reg_min['interanual_pct'], 1)}).",
            "enlace": "dashboard/#regiones",
        },
        {
            "titulo": f"En dólares oficiales, {'todavía abajo' if usd_abajo else 'arriba'} de {usd['inicio']['anio']}",
            "texto": f"El RIPTE promedió US$ {formato.numero(usd['ultimo']['ripte_usd'], 0)} "
            f"en {usd['ultimo']['anio']} ({usd['ultimo']['meses']} meses), "
            f"contra US$ {formato.numero(usd['inicio']['ripte_usd'], 0)} en "
            f"{usd['inicio']['anio']}. El mínimo fue US$ {formato.numero(usd_min['ripte_usd'], 0)} en "
            f"{usd_min['anio']}.",
            "enlace": "dashboard/#dolares",
        },
    ]
    return {
        "respuesta_corta": respuesta_corta,
        "peor_sector": dict(peor, sector=nombre(peor)),
        "respuesta": f"{respuesta_corta} {respuesta_resto}",
        "respuesta_resto": respuesta_resto,
        "detalle": detalle,
        "hallazgos": hallazgos,
        "vigencia": {f["analisis"]: f["vale_hasta"] for f in c["09_vigencia_de_conclusiones"]["filas"]},
    }


# ---------------------------------------------------------------------------
# Construcción
# ---------------------------------------------------------------------------


def _entorno(base: str) -> Environment:
    env = Environment(
        loader=FileSystemLoader(config.DIR_SITE_SRC / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(
        numero=formato.numero,
        pct=formato.porcentaje,
        pesos=formato.pesos,
        mes=formato.mes,
        mes_largo=_mes_largo,
        mes_largo_iso=lambda f: formato.mes(f, largo=True),
        celda=celda,
        clase_celda=clase_celda,
        sql=resaltar_sql,
        etiqueta=lambda c: ETIQUETAS.get(c, c.replace("_", " ").capitalize()),
    )
    env.globals.update(base=base, site_url=SITE_URL, repo=REPO_URL, echarts=ECHARTS, ocultas=OCULTAS)
    return env


def _json_embebido(datos) -> Markup:
    """JSON seguro para incrustar en <script type="application/json">."""
    texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    return Markup(texto.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def construir(datos: dict, salida: Path = config.DIR_BUILD, base: str | None = None) -> Path:
    base = base or os.environ.get("INFLATIONARG_BASE", "/InflationArg/")
    destino = salida / "site"
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(config.DIR_SITE_SRC / "static", destino / "static")

    env = _entorno(base)
    indices = json.loads((salida / "datos" / "indices.json").read_text(encoding="utf-8"))
    contexto = {
        "d": datos,
        "t": textos(datos),
        "paginas": PAGINAS,
        "graficos_json": _json_embebido(datos["graficos"]),
        "indices_json": _json_embebido(indices),
        "consultas_json": _json_embebido(
            {k: {"columnas": v["columnas"], "filas": v["filas"]} for k, v in datos["consultas"].items()}
        ),
        "meses_calculadora": sorted(indices["ipc"]),
    }
    for ruta, plantilla, nav, titulo, descripcion in PAGINAS:
        html_pagina = env.get_template(plantilla).render(
            **contexto, ruta=ruta, titulo=titulo, descripcion=descripcion, nav=nav
        )
        archivo = destino / ruta / "index.html"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(html_pagina, encoding="utf-8")

    (destino / "404.html").write_text(
        env.get_template("404.html").render(
            **contexto, ruta="404", titulo="Página no encontrada", descripcion="Página no encontrada.", nav=""
        ),
        encoding="utf-8",
    )
    (destino / "sitemap.xml").write_text(
        env.get_template("sitemap.xml").render(paginas=PAGINAS, fecha=datos["meta"]["fecha_descarga"]),
        encoding="utf-8",
    )
    (destino / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8")
    (destino / ".nojekyll").write_text("", encoding="utf-8")

    descargas = destino / "descargas"
    descargas.mkdir()
    shutil.copy(salida / "datos" / "dashboard.json", descargas / "dashboard.json")
    shutil.copy(salida / "inflationarg.xlsx", descargas / "inflationarg.xlsx")
    shutil.copy(salida / "inflationarg.db", descargas / "inflationarg.db")
    with zipfile.ZipFile(descargas / "powerbi.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for csv in sorted((salida / "powerbi").glob("*.csv")):
            zf.write(csv, csv.name)
    return destino
