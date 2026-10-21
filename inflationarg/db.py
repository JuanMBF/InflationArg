"""Carga en SQLite: staging -> modelo estrella -> vistas, y ejecución de consultas."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from . import config, transform

SCRIPTS = ("01_esquema.sql", "02_modelo.sql", "03_vistas.sql")
INICIO_FACT = config.BASE_SALARIOS  # primer mes que se guarda en fact_valor


def conectar(ruta: Path | str = ":memory:") -> sqlite3.Connection:
    con = sqlite3.connect(ruta)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _script(nombre: str) -> str:
    return (config.DIR_SQL / nombre).read_text(encoding="utf-8")


def construir(
    con: sqlite3.Connection,
    stg: pd.DataFrame,
    marcas: pd.DataFrame,
    fecha_corte: str,
    fecha_descarga: str,
) -> None:
    """Crea el esquema, carga staging y dimensiones y arma hechos y vistas."""
    con.executescript(_script(SCRIPTS[0]))
    parametros = {
        "inicio_fact": INICIO_FACT,
        "base_analisis": config.INICIO_ANALISIS,
        "fecha_corte": fecha_corte,
        "fecha_descarga": fecha_descarga,
    }
    con.executemany("INSERT INTO parametro VALUES (?, ?)", parametros.items())
    con.executemany(
        "INSERT INTO stg_valor (fecha, serie_id, valor, archivo) VALUES (?, ?, ?, ?)",
        stg[["fecha", "serie_id", "valor", "archivo"]].itertuples(index=False),
    )
    con.executemany(
        "INSERT INTO qa_marca (fecha, serie_id, motivo) VALUES (?, ?, ?)",
        marcas[["fecha", "serie_id", "motivo"]].itertuples(index=False),
    )
    cat = transform.catalogo_df()
    con.executemany(
        f"INSERT INTO dim_serie ({', '.join(cat.columns)}) VALUES ({', '.join('?' * len(cat.columns))})",
        cat.itertuples(index=False),
    )
    con.executescript(_script(SCRIPTS[1]))
    con.executescript(_script(SCRIPTS[2]))
    con.commit()


def consultar(con: sqlite3.Connection, sql: str, **parametros) -> pd.DataFrame:
    return pd.read_sql_query(sql, con, params=parametros or None)


def consultas_de_negocio() -> dict[str, str]:
    """Las consultas de sql/consultas, por nombre de archivo sin extensión."""
    return {ruta.stem: ruta.read_text(encoding="utf-8") for ruta in sorted(config.DIR_CONSULTAS.glob("*.sql"))}


def descripcion_consulta(sql: str) -> str:
    """El comentario de cabecera de una consulta (líneas `--` iniciales), sin los guiones."""
    lineas = []
    for linea in sql.splitlines():
        if not linea.startswith("--"):
            break
        texto = linea[2:].strip()
        if texto and not set(texto) <= {"=", "-"}:
            lineas.append(texto)
    return " ".join(lineas)
