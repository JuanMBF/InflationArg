"""Fixtures compartidas: una corrida completa del pipeline (offline) por sesión."""

from __future__ import annotations

import json
import sqlite3

import pandas as pd
import pytest

from inflationarg import config, db, pipeline


@pytest.fixture(scope="session")
def corrida(tmp_path_factory):
    salida = tmp_path_factory.mktemp("build")
    return pipeline.correr_todo(salida=salida, log=lambda *_: None)


@pytest.fixture(scope="session")
def con(corrida):
    conexion = sqlite3.connect(corrida.ruta_db)
    yield conexion
    conexion.close()


@pytest.fixture(scope="session")
def dashboard(corrida):
    return json.loads((corrida.salida / "datos" / "dashboard.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def raw():
    """Los CSV oficiales leídos directo con pandas, para verificar números sin pasar por el pipeline."""

    def leer(nombre, columna):
        df = pd.read_csv(config.DIR_RAW / nombre, dtype={"indice_tiempo": str})
        return df.set_index(df["indice_tiempo"].str.slice(0, 7))[columna]

    return leer


def construir_mini(stg_filas, marcas=(), fecha_corte="2017-06-01", inicio="2016-10-01"):
    """Base chica en memoria a partir de filas (fecha, serie_id, valor) para testear las vistas."""
    stg = pd.DataFrame(stg_filas, columns=["fecha", "serie_id", "valor"]).assign(archivo="test.csv")
    marcas_df = pd.DataFrame(list(marcas), columns=["fecha", "serie_id", "motivo"])
    con = db.conectar()
    original = db.INICIO_FACT
    db.INICIO_FACT = inicio
    try:
        db.construir(con, stg, marcas_df, fecha_corte, "2017-06-15")
    finally:
        db.INICIO_FACT = original
    return con
