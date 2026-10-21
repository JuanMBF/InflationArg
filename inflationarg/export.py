"""Exportaciones: JSON para el sitio, Excel con formato y CSV para Power BI.

Todo lo que se muestra sale de la base: vistas y consultas de sql/consultas.
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from . import config, db
from .calculadora import Indices
from .formato import mes
from .qa import Reporte

COLORES_SECTOR = {
    "sal_privado": "Privado registrado",
    "sal_publico": "Público",
    "sal_no_registrado": "Privado no registrado",
    "sal_total": "Total",
}


def _limpio(valor):
    if isinstance(valor, float) and (math.isnan(valor) or math.isinf(valor)):
        return None
    return valor


def _registros(df: pd.DataFrame) -> list[dict]:
    return [{k: _limpio(v) for k, v in fila.items()} for fila in df.to_dict(orient="records")]


def _serie_ancha(df: pd.DataFrame, columna: str, valores: str, redondeo: int = 4) -> dict:
    """De formato largo a {"fechas": [...], "series": {id: [...]}} para ECharts."""
    ancho = df.pivot(index="fecha", columns=columna, values=valores).sort_index()
    return {
        "fechas": [f[:7] for f in ancho.index],
        "series": {c: [None if pd.isna(v) else round(float(v), redondeo) for v in ancho[c]] for c in ancho.columns},
    }


def resultados_consultas(con: sqlite3.Connection) -> dict[str, dict]:
    salida = {}
    for nombre, sql in db.consultas_de_negocio().items():
        df = db.consultar(con, sql)
        salida[nombre] = {
            "descripcion": db.descripcion_consulta(sql),
            "sql": sql,
            "columnas": list(df.columns),
            "filas": _registros(df),
        }
    return salida


def datos_dashboard(con: sqlite3.Connection, consultas: dict, reporte: Reporte) -> dict:
    q = lambda sql: db.consultar(con, sql)  # noqa: E731

    parametros = dict(con.execute("SELECT clave, valor FROM parametro").fetchall())
    real = q("SELECT fecha, serie_id, indice_real FROM v_salario_real")
    inflacion = q(
        "SELECT fecha, var_mensual * 100 AS mensual, var_interanual * 100 AS interanual "
        "FROM v_variacion WHERE serie_id = 'ipc_nacional' AND var_mensual IS NOT NULL ORDER BY fecha"
    )
    categorias = q(
        "SELECT fecha, serie_id, var_interanual * 100 AS v FROM v_variacion "
        "WHERE grupo IN ('ipc_categoria') OR serie_id = 'ipc_nacional'"
    )
    regiones = q("SELECT fecha, region, var_interanual * 100 AS v FROM v_variacion WHERE grupo = 'ipc_region'")
    poder = q(
        "SELECT fecha, cbt_por_ripte AS ripte, cbt_por_smvm AS smvm, cbt_por_haber_minimo AS haber_minimo "
        "FROM v_poder_compra ORDER BY fecha"
    )
    usd = db.consultar(
        con,
        "SELECT fecha, ripte_usd AS ripte, smvm_usd AS smvm, haber_minimo_usd AS haber_minimo "
        "FROM v_salario_usd WHERE fecha >= :desde AND ripte IS NOT NULL ORDER BY fecha",
        desde=config.INICIO_ANALISIS,
    )
    cobertura = q("SELECT serie_id, nombre, fuente, desde, hasta, meses, meses_de_rezago FROM v_cobertura")

    def serie_simple(df: pd.DataFrame, columnas: list[str], redondeo: int = 3) -> dict:
        return {
            "fechas": [f[:7] for f in df["fecha"]],
            "series": {c: [None if pd.isna(v) else round(float(v), redondeo) for v in df[c]] for c in columnas},
        }

    # El pico interanual sale de toda la serie, no de los 10 picos mensuales.
    pico_interanual = _registros(
        q(
            "SELECT etiqueta AS mes, ROUND(100 * var_interanual, 2) AS inflacion_interanual_pct FROM v_inflacion "
            "WHERE serie_id = 'ipc_nacional' AND ranking_interanual = 1 ORDER BY fecha LIMIT 1"
        )
    )[0]
    principal = consultas["01_respuesta_principal"]["filas"]
    por_sector = {f["serie_id"]: f for f in principal}
    ultima_inflacion = inflacion.iloc[-1]
    picos = consultas["03_inflacion_picos"]["filas"]
    poder_ultimo = next(f for f in consultas["06_poder_compra_canastas"]["filas"] if f["es_ultimo"])
    poder_inicio = consultas["06_poder_compra_canastas"]["filas"][0]
    usd_anual = consultas["08_salario_en_dolares"]["filas"]

    kpis = {
        "salario_real_total": por_sector["sal_total"],
        "salario_real_privado": por_sector["sal_privado"],
        "salario_real_publico": por_sector["sal_publico"],
        "salario_real_no_registrado": por_sector["sal_no_registrado"],
        "inflacion_mensual": {
            "mes": mes(inflacion.iloc[-1]["fecha"]),
            "valor": round(float(ultima_inflacion["mensual"]), 2),
        },
        "inflacion_interanual": {
            "mes": mes(inflacion.iloc[-1]["fecha"]),
            "valor": round(float(ultima_inflacion["interanual"]), 2),
        },
        "pico_mensual": picos[0],
        "pico_interanual": pico_interanual,
        "canastas_ripte": {"inicio": poder_inicio, "ultimo": poder_ultimo},
        "ripte_usd": {"inicio": usd_anual[0], "ultimo": usd_anual[-1]},
    }

    return {
        "meta": {
            "fecha_descarga": parametros["fecha_descarga"],
            "fecha_corte": parametros["fecha_corte"],
            "base_analisis": parametros["base_analisis"],
            "series": len(config.CATALOGO),
            "observaciones": con.execute("SELECT COUNT(*) FROM fact_valor").fetchone()[0],
        },
        "kpis": kpis,
        "sectores": COLORES_SECTOR,
        "regiones": config.REGIONES,
        "graficos": {
            "salario_real": _serie_ancha(real, "serie_id", "indice_real", 2),
            "inflacion": serie_simple(inflacion, ["mensual", "interanual"], 2),
            "categorias": _serie_ancha(categorias, "serie_id", "v", 2),
            "regiones": _serie_ancha(regiones, "region", "v", 2),
            "poder_compra": serie_simple(poder, ["ripte", "smvm", "haber_minimo"], 3),
            "usd": serie_simple(usd, ["ripte", "smvm", "haber_minimo"], 0),
        },
        "cobertura": _registros(cobertura),
        "consultas": consultas,
        "qa": reporte.a_dict(),
    }


def escribir_json(datos: dict, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def indices_calculadora(con: sqlite3.Connection) -> dict:
    return Indices.desde_base(con).a_dict()


# ---------------------------------------------------------------------------
# Power BI
# ---------------------------------------------------------------------------


def exportar_power_bi(con: sqlite3.Connection, destino: Path) -> list[Path]:
    """El modelo estrella en CSV (UTF-8 con BOM, separador coma, punto decimal)."""
    destino.mkdir(parents=True, exist_ok=True)
    tablas = {
        "dim_fecha": "SELECT fecha, anio, mes, trimestre, etiqueta FROM dim_fecha ORDER BY fecha",
        "dim_serie": "SELECT serie_id, nombre, grupo, region, unidad, base, fuente FROM dim_serie",
        "fact_valor": "SELECT fecha, serie_id, valor, estado FROM fact_valor ORDER BY serie_id, fecha",
        "salario_real": "SELECT fecha, serie_id, indice_nominal, indice_real, var_real_interanual "
        "FROM v_salario_real ORDER BY serie_id, fecha",
    }
    rutas = []
    for nombre, sql in tablas.items():
        ruta = destino / f"{nombre}.csv"
        db.consultar(con, sql).to_csv(ruta, index=False, encoding="utf-8-sig")
        rutas.append(ruta)
    return rutas


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

AZUL = "1F4E79"
TITULOS_HOJA = {
    "01_respuesta_principal": "1 Respuesta",
    "02_ganadores_por_anio": "2 Sectores por año",
    "03_inflacion_picos": "3 Picos de inflación",
    "04_inflacion_anual_por_categoria": "4 Inflación por categoría",
    "05_rubros_ranking": "5 Rubros",
    "06_poder_compra_canastas": "6 Canastas",
    "07_regiones": "7 Regiones",
    "08_salario_en_dolares": "8 Salario en USD",
    "09_vigencia_de_conclusiones": "9 Vigencia",
}


def _hoja_tabla(wb: Workbook, titulo: str, descripcion: str, df: pd.DataFrame, nombre_tabla: str):
    ws = wb.create_sheet(titulo)
    ws["A1"] = titulo
    ws["A1"].font = Font(bold=True, size=14, color=AZUL)
    ws["A2"] = descripcion
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ancho = max(len(df.columns), 1)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(ancho, 6))
    ws.row_dimensions[2].height = 60
    fila0 = 4
    for j, columna in enumerate(df.columns, start=1):
        ws.cell(row=fila0, column=j, value=columna)
    for i, fila in enumerate(df.itertuples(index=False), start=fila0 + 1):
        for j, valor in enumerate(fila, start=1):
            ws.cell(row=i, column=j, value=_limpio(valor.item() if hasattr(valor, "item") else valor))
    ultima = fila0 + len(df)
    if len(df):
        ref = f"A{fila0}:{get_column_letter(len(df.columns))}{ultima}"
        tabla = Table(displayName=nombre_tabla, ref=ref)
        tabla.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(tabla)
    for j, columna in enumerate(df.columns, start=1):
        valores = [str(columna)] + [str(v) for v in df.iloc[:, j - 1].tolist()]
        ws.column_dimensions[get_column_letter(j)].width = min(max(len(v) for v in valores) + 2, 45)
        if pd.api.types.is_float_dtype(df.iloc[:, j - 1]):
            for i in range(fila0 + 1, ultima + 1):
                ws.cell(row=i, column=j).number_format = "#,##0.00"
    ws.freeze_panes = ws.cell(row=fila0 + 1, column=1)
    return ws


def exportar_excel(con: sqlite3.Connection, consultas: dict, reporte: Reporte, ruta: Path) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    portada = wb.active
    portada.title = "Leeme"
    parametros = dict(con.execute("SELECT clave, valor FROM parametro").fetchall())
    lineas = [
        ("¿Le ganaron los salarios a la inflación? Argentina 2016–2026", Font(bold=True, size=16, color=AZUL)),
        (f"Datos oficiales (INDEC, BCRA, ANSES, MTEySS) descargados el {parametros['fecha_descarga']}.", None),
        ("Cada hoja numerada responde una pregunta de negocio y sale de una consulta SQL de sql/consultas.", None),
        ("La hoja 'Salario real mensual' tiene la serie completa y el gráfico.", None),
        ("La hoja 'QA' resume los chequeos de calidad de datos.", None),
        ("Autor: Juan Barros · github.com/JuanMBF/InflationArg", None),
    ]
    for i, (texto, fuente) in enumerate(lineas, start=1):
        portada.cell(row=i, column=1, value=texto)
        if fuente:
            portada.cell(row=i, column=1).font = fuente
    portada.column_dimensions["A"].width = 100

    for nombre, datos in consultas.items():
        df = pd.DataFrame(datos["filas"], columns=datos["columnas"])
        _hoja_tabla(wb, TITULOS_HOJA.get(nombre, nombre[:31]), datos["descripcion"], df, f"t_{nombre[:3]}")

    real = db.consultar(con, "SELECT fecha, serie_id, indice_real FROM v_salario_real")
    ancho = real.pivot(index="fecha", columns="serie_id", values="indice_real").sort_index()
    ancho = ancho[[c for c in COLORES_SECTOR if c in ancho.columns]]
    ancho.columns = [COLORES_SECTOR[c] for c in ancho.columns]
    ancho.index = [mes(f) for f in ancho.index]
    tabla = ancho.round(2).reset_index(names="mes")
    ws = _hoja_tabla(
        wb,
        "Salario real mensual",
        "Índice de salario real (dic-2016 = 100) por sector: índice de salarios del INDEC deflactado por el IPC.",
        tabla,
        "t_salario_real",
    )
    grafico = LineChart()
    grafico.title = "Salario real por sector (dic-2016 = 100)"
    grafico.y_axis.title = "Índice"
    grafico.height, grafico.width = 9, 22
    datos = Reference(ws, min_col=2, max_col=1 + len(ancho.columns), min_row=4, max_row=4 + len(tabla))
    grafico.add_data(datos, titles_from_data=True)
    grafico.set_categories(Reference(ws, min_col=1, min_row=5, max_row=4 + len(tabla)))
    ws.add_chart(grafico, "H4")

    qa_df = pd.DataFrame([{"nivel": r.nivel, "chequeo": r.titulo, "resultado": r.detalle} for r in reporte.resultados])
    ws = _hoja_tabla(wb, "QA", "Chequeos automáticos de calidad de datos.", qa_df, "t_qa")
    colores = {"ok": "C6EFCE", "info": "DDEBF7", "alerta": "FFEB9C", "error": "FFC7CE"}
    for i, r in enumerate(reporte.resultados, start=5):
        ws.cell(row=i, column=1).fill = PatternFill("solid", fgColor=colores[r.nivel])
        ws.cell(row=i, column=3).alignment = Alignment(wrap_text=True)
    ws.column_dimensions["C"].width = 100

    wb.save(ruta)
    return ruta
