import pandas as pd

from inflationarg import config, extract, qa, transform


def _stg(filas):
    return pd.DataFrame(filas, columns=["fecha", "serie_id", "valor"]).assign(archivo="x.csv")


def _por_id(reporte):
    return {r.chequeo: r for r in reporte.resultados}


def test_la_foto_pasa_sin_errores(corrida):
    assert not corrida.reporte.tiene_errores
    assert corrida.reporte.conteo() == {"ok": 7, "info": 1, "alerta": 3, "error": 0}


def test_detecta_las_series_vacias_de_la_api(corrida):
    api = _por_id(corrida.reporte)["api_vs_csv"]
    assert api.nivel == "alerta"
    vacias = {f["serie_id"] for f in api.filas if f["problema"] == "API vacía"}
    assert vacias == {"rubro_recreacion_cultura", "rubro_restaurantes_hoteles", "ipc_noa", "ripte"}


def test_detecta_api_incompleta_y_revisiones(corrida):
    filas = _por_id(corrida.reporte)["api_vs_csv"].filas
    nea = [f for f in filas if f["serie_id"] == "ipc_nea"]
    assert any(f["problema"].startswith("API incompleta") for f in nea)
    assert any("jul-2022" in f["problema"] for f in nea)


def test_ripte_agosto_repetido_queda_en_cuarentena(corrida):
    marcas = corrida.reporte.marcas
    assert marcas[["fecha", "serie_id"]].to_dict("records") == [{"fecha": "2026-08-01", "serie_id": "ripte"}]
    assert marcas["valor"].iloc[0] == 1915878.76
    assert "jun-2026" in marcas["motivo"].iloc[0]


def test_salario_minimo_a_futuro_se_excluye(corrida, con):
    futuro = _por_id(corrida.reporte)["futuro"]
    assert futuro.nivel == "alerta"
    assert futuro.filas == [{"serie_id": "smvm", "meses": 6, "desde": "nov-2026", "hasta": "abr-2027"}]
    assert con.execute("SELECT COUNT(*) FROM excluido WHERE serie_id = 'smvm'").fetchone()[0] == 6
    assert con.execute("SELECT MAX(fecha) FROM fact_valor WHERE serie_id = 'smvm'").fetchone()[0] == "2026-10-01"


def test_alineacion_dice_hasta_cuando_vale_cada_conclusion(corrida):
    filas = {f["conclusion"]: f["vale_hasta"] for f in _por_id(corrida.reporte)["alineacion"].filas}
    assert filas["Salario real por sector"] == "jul-2026"
    assert filas["Inflación, rubros y regiones"] == "sep-2026"
    assert filas["Poder de compra en canastas"] == "jul-2026"


def test_duplicados_son_error():
    r = qa.chequear_unicidad(_stg([("2020-01-01", "ripte", 1.0), ("2020-01-01", "ripte", 2.0)]))
    assert r.nivel == "error"


def test_mes_salteado_es_error():
    r = qa.chequear_fechas(_stg([("2020-01-01", "ripte", 1.0), ("2020-03-01", "ripte", 2.0)]))
    assert r.nivel == "error"
    assert r.filas == [{"serie_id": "ripte", "meses_faltantes": 1}]


def test_fecha_mal_formada_es_error():
    r = qa.chequear_fechas(_stg([("2020-01-15", "ripte", 1.0)]))
    assert r.nivel == "error"


def test_base_distinta_de_100_es_error():
    stg = transform.a_largo(extract.leer_crudos())
    stg.loc[(stg["serie_id"] == "ipc_nacional") & (stg["fecha"] == config.BASE_IPC), "valor"] = 100.5
    r = qa.chequear_base_100(stg)
    assert r.nivel == "error"
    assert r.filas[0]["serie_id"] == "ipc_nacional"


def test_valor_negativo_es_error_y_salto_es_alerta():
    neg = qa.chequear_rangos(_stg([("2020-01-01", "ripte", 10.0), ("2020-02-01", "ripte", -1.0)]))
    assert neg.nivel == "error"
    salto = qa.chequear_rangos(_stg([("2020-01-01", "ipc_nacional", 100.0), ("2020-02-01", "ipc_nacional", 150.0)]))
    assert salto.nivel == "alerta"
    assert salto.filas[0]["var_mensual_%"] == 50.0


def test_serie_faltante_es_error():
    stg = transform.a_largo(extract.leer_crudos())
    r = qa.chequear_completitud(stg[stg["serie_id"] != "cbt"])
    assert r.nivel == "error"
    assert r.filas == [{"serie_id": "cbt", "problema": "sin datos"}]


def test_sha_distinto_es_error_offline_e_info_online():
    archivo = extract.Archivo("a.csv", "INDEC", "u", "aaa", "bbb", 1, 1)
    assert qa.chequear_archivos([archivo], online=False).nivel == "error"
    assert qa.chequear_archivos([archivo], online=True).nivel == "info"


def test_repetidos_ignora_valores_que_se_mantienen():
    stg = _stg(
        [
            ("2020-01-01", "ripte", 10.0),
            ("2020-02-01", "ripte", 10.0),  # se mantiene: normal
            ("2020-03-01", "ripte", 11.0),
            ("2020-04-01", "ripte", 10.0),  # vuelve a un valor de hace 2 meses: sospechoso
            ("2020-05-01", "smvm", 5.0),
        ]
    )
    marcas = qa.detectar_repetidos(stg)
    assert marcas[["fecha", "serie_id"]].to_dict("records") == [{"fecha": "2020-04-01", "serie_id": "ripte"}]


def test_frescura_alerta_series_viejas():
    stg = transform.a_largo(extract.leer_crudos())
    r = qa.chequear_frescura(stg, "2027-06-01")
    assert r.nivel == "alerta"


def test_reporte_markdown_y_json(corrida):
    md = corrida.reporte.a_markdown()
    assert md.startswith("# Reporte de QA de datos")
    assert "⚠️" in md and "✅" in md
    assert "1.915.878,76" in md  # números en formato es-AR
    assert '"conteo"' in corrida.reporte.a_json()
