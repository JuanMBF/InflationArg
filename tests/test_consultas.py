"""Las consultas de negocio: estructura, y sus números contra un cálculo independiente con pandas."""

import pandas as pd
import pytest

from inflationarg import db, formato


@pytest.fixture(scope="module")
def resultados(dashboard):
    return dashboard["consultas"]


def test_hay_una_consulta_por_pregunta_con_comentario():
    consultas = db.consultas_de_negocio()
    assert len(consultas) == 9
    for nombre, sql in consultas.items():
        descripcion = db.descripcion_consulta(sql)
        assert descripcion.startswith("Pregunta: ¿"), nombre
        assert "Lectura:" in descripcion, nombre


def test_todas_devuelven_filas(resultados):
    for nombre, r in resultados.items():
        assert r["filas"], nombre


def test_salario_real_contra_pandas(resultados, raw):
    ipc = raw("ipc_nivel_general_regiones.csv", "ipc_ng_nacional")
    columnas = {
        "sal_total": "indice_salarios",
        "sal_privado": "indice_salarios_registrado_sector_privado",
        "sal_publico": "indice_salarios_registrado_sector_publico",
        "sal_no_registrado": "indice_salarios_no_registrado_sector_privado",
    }
    filas = {f["serie_id"]: f for f in resultados["01_respuesta_principal"]["filas"]}
    for serie_id, columna in columnas.items():
        w = raw("indice_salarios.csv", columna).dropna()
        if serie_id == "sal_no_registrado":
            # Se publica con 5 meses de rezago: el dato fechado t mide el mes t - 5.
            w.index = (pd.PeriodIndex(w.index, freq="M") - 5).strftime("%Y-%m")
        hasta = w.index.max()
        real = 100 * (w[hasta] / w["2016-12"]) / (ipc[hasta] / ipc["2016-12"])
        assert filas[serie_id]["indice_real"] == pytest.approx(real, abs=0.006), serie_id
        assert filas[serie_id]["hasta"] == formato.mes(hasta + "-01")
    assert filas["sal_no_registrado"]["hasta"] == "feb-2026"
    assert filas["sal_total"]["hasta"] == "jul-2026"


def test_no_registrado_corrido_cinco_meses(con, raw):
    publicado = raw("indice_salarios.csv", "indice_salarios_no_registrado_sector_privado")
    en_base = dict(con.execute("SELECT fecha, valor FROM fact_valor WHERE serie_id = 'sal_no_registrado'").fetchall())
    assert en_base["2026-02-01"] == publicado["2026-07"]
    assert en_base["2024-01-01"] == publicado["2024-06"]
    # staging conserva la fecha de publicación (la que valida la QA)
    assert con.execute("SELECT MAX(fecha) FROM stg_valor WHERE serie_id = 'sal_no_registrado'").fetchone() == (
        "2026-07-01",
    )


def test_respuesta_principal_ordenada_por_ranking(resultados):
    filas = resultados["01_respuesta_principal"]["filas"]
    assert [f["ranking"] for f in filas] == list(range(1, len(filas) + 1))
    assert filas[0]["serie_id"] == "sal_no_registrado"
    assert filas[-1]["serie_id"] == "sal_publico"


def test_picos_de_inflacion_contra_pandas(resultados, raw):
    ipc = raw("ipc_nivel_general_regiones.csv", "ipc_ng_nacional")
    mensual = (ipc.pct_change() * 100).dropna().sort_values(ascending=False)
    picos = resultados["03_inflacion_picos"]["filas"]
    assert len(picos) == 10
    assert picos[0]["mes"] == "dic-2023"
    assert picos[0]["inflacion_mensual_pct"] == pytest.approx(mensual.iloc[0], abs=0.006)
    valores = [p["inflacion_mensual_pct"] for p in picos]
    assert valores == sorted(valores, reverse=True)


def test_inflacion_anual_contra_pandas(resultados, raw):
    ipc = raw("ipc_nivel_general_regiones.csv", "ipc_ng_nacional")
    filas = {f["anio"]: f for f in resultados["04_inflacion_anual_por_categoria"]["filas"]}
    assert filas[2023]["nivel_general"] == pytest.approx(100 * (ipc["2023-12"] / ipc["2022-12"] - 1), abs=0.006)
    assert filas[2026]["hasta"] == "sep-2026"
    assert filas[2026]["nivel_general"] == pytest.approx(100 * (ipc["2026-09"] / ipc["2025-12"] - 1), abs=0.006)


def test_rubros_contra_pandas(resultados, raw):
    filas = resultados["05_rubros_ranking"]["filas"]
    assert len(filas) == 12
    ropa = raw("ipc_capitulos.csv", "ipc_prendas_vestir_calzado_nacional")
    ultimo = next(f for f in filas if f["rubro"] == "Prendas de vestir y calzado")
    assert ultimo["veces"] == pytest.approx(ropa["2026-09"] / 100, abs=0.06)
    assert ultimo["ultimo_anio_pct"] == pytest.approx(100 * (ropa["2026-09"] / ropa["2025-09"] - 1), abs=0.006)


def test_canastas_contra_pandas(resultados, raw):
    ripte = raw("ripte.csv", "ripte")
    cbt = raw("canastas_basicas.csv", "canasta_basica_total")
    filas = resultados["06_poder_compra_canastas"]["filas"]
    ultimo = next(f for f in filas if f["es_ultimo"])
    assert ultimo["mes"] == "jul-2026"  # ago-2026 de RIPTE está en cuarentena
    assert ultimo["cbt_por_ripte"] == pytest.approx(ripte["2026-07"] / cbt["2026-07"], abs=0.006)


def test_regiones_contra_pandas(resultados, raw):
    nea = raw("ipc_nivel_general_regiones.csv", "ipc_ng_nea")
    fila = next(f for f in resultados["07_regiones"]["filas"] if f["region"] == "nea")
    assert fila["interanual_pct"] == pytest.approx(100 * (nea["2026-09"] / nea["2025-09"] - 1), abs=0.006)
    assert resultados["07_regiones"]["filas"][0]["region"] == "nacional"


def test_dolares_contra_pandas(resultados, raw):
    ripte = raw("ripte.csv", "ripte")
    tc = raw("tipo_cambio_bcra.csv", "tipo_cambio_valuacion")
    anio = [f"2017-{m:02d}" for m in range(1, 13)]
    esperado = sum(ripte[m] / tc[m] for m in anio) / 12
    fila = resultados["08_salario_en_dolares"]["filas"][0]
    assert fila["anio"] == 2017
    assert fila["ripte_usd"] == pytest.approx(esperado, abs=0.5)


def test_vigencia(resultados):
    filas = {f["analisis"]: f["vale_hasta"] for f in resultados["09_vigencia_de_conclusiones"]["filas"]}
    assert filas == {
        "Poder de compra en canastas": "2026-07-01",
        "Salario en dólares": "2026-07-01",
        "Salario real: total, registrados, privado y público": "2026-07-01",
        "Salario real: privado no registrado": "2026-02-01",
        "Inflación, rubros y regiones": "2026-09-01",
    }


def test_pico_interanual_de_toda_la_serie(dashboard, raw):
    ipc = raw("ipc_nivel_general_regiones.csv", "ipc_ng_nacional")
    interanual = (ipc / ipc.shift(12) - 1).dropna() * 100
    pico = dashboard["kpis"]["pico_interanual"]
    assert pico["inflacion_interanual_pct"] == pytest.approx(interanual.max(), abs=0.006)
    assert pico["mes"] == "abr-2024" and interanual.idxmax() == "2024-04"


def test_mejor_y_peor_sector_por_anio(resultados):
    filas = {f["anio"]: f for f in resultados["02_ganadores_por_anio"]["filas"]}
    # El último año compara a todos los sectores en el mismo período (hasta el último mes común).
    assert filas[2026]["hasta"] == "feb-2026"
    assert filas[2017]["ganador"] == "Salarios – privado registrado"
    for f in filas.values():
        valores = {
            "Salarios – privado registrado": f["privado_registrado"],
            "Salarios – sector público": f["publico"],
            "Salarios – privado no registrado": f["no_registrado"],
        }
        assert valores[f["ganador"]] == max(valores.values())
        assert valores[f["perdedor"]] == min(valores.values())
