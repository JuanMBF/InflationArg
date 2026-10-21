"""Las consultas de negocio: estructura, y sus números contra un cálculo independiente con pandas."""

import pytest

from inflationarg import db


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
        w = raw("indice_salarios.csv", columna)
        real = 100 * (w["2026-07"] / w["2016-12"]) / (ipc["2026-07"] / ipc["2016-12"])
        assert filas[serie_id]["indice_real"] == pytest.approx(real, abs=0.006)
        assert filas[serie_id]["hasta"] == "jul-2026"


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
        "Salario real por sector": "2026-07-01",
        "Inflación, rubros y regiones": "2026-09-01",
    }


def test_pico_interanual_de_toda_la_serie(dashboard, raw):
    ipc = raw("ipc_nivel_general_regiones.csv", "ipc_ng_nacional")
    interanual = (ipc / ipc.shift(12) - 1).dropna() * 100
    pico = dashboard["kpis"]["pico_interanual"]
    assert pico["inflacion_interanual_pct"] == pytest.approx(interanual.max(), abs=0.006)
    assert pico["mes"] == "abr-2024" and interanual.idxmax() == "2024-04"
