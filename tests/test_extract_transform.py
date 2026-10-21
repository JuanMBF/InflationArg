import shutil

import pandas as pd
import pytest

from inflationarg import config, extract, transform


def test_manifiesto_y_hashes_de_la_foto():
    manifiesto = extract.leer_manifiesto()
    inventario = extract.inventario(config.DIR_RAW, manifiesto)
    assert len(inventario) == len(manifiesto["archivos"]) == 10
    assert all(a.sha_ok for a in inventario)
    assert all(a.filas == a.filas_esperadas for a in inventario)


def test_un_byte_cambiado_rompe_el_sha(tmp_path):
    copia = tmp_path / "raw"
    shutil.copytree(config.DIR_RAW, copia)
    ruta = copia / "ripte.csv"
    ruta.write_bytes(ruta.read_bytes().replace(b"1915878.76", b"1915878.77", 1))
    inventario = extract.inventario(copia, extract.leer_manifiesto(copia))
    malos = [a.archivo for a in inventario if not a.sha_ok]
    assert malos == ["ripte.csv"]


def test_formato_largo_cubre_todo_el_catalogo():
    stg = transform.a_largo(extract.leer_crudos())
    assert set(stg.columns) == {"fecha", "serie_id", "valor", "archivo"}
    assert set(stg["serie_id"]) == {s.serie_id for s in config.CATALOGO}
    assert stg["valor"].notna().all()
    assert not stg.duplicated(["fecha", "serie_id"]).any()
    assert stg["fecha"].str.fullmatch(r"\d{4}-\d{2}-01").all()


def test_formato_largo_conserva_los_valores(raw):
    stg = transform.a_largo(extract.leer_crudos())
    ripte = stg[stg["serie_id"] == "ripte"].set_index("fecha")["valor"]
    assert ripte["2026-07-01"] == raw("ripte.csv", "ripte")["2026-07"]


def test_columna_inexistente_falla_con_mensaje_claro():
    crudos = extract.leer_crudos()
    crudos["ripte.csv"] = crudos["ripte.csv"].rename(columns={"ripte": "otra"})
    with pytest.raises(KeyError, match=r"ripte\.csv"):
        transform.a_largo(crudos)


def test_api_a_largo_mapea_ids_del_catalogo():
    api = pd.DataFrame({"indice_tiempo": ["2020-01-01"], "158.1_REPTE_0_0_5": [1.0], "id_que_no_esta": [2.0]})
    largo = transform.api_a_largo(api)
    assert largo.to_dict("records") == [
        {"fecha": "2020-01-01", "serie_id": "ripte", "id_api": "158.1_REPTE_0_0_5", "valor": 1.0}
    ]


def test_catalogo_ids_unicos_y_grupos_conocidos():
    ids = [s.serie_id for s in config.CATALOGO]
    assert len(ids) == len(set(ids)) == 33
    assert {s.grupo for s in config.CATALOGO} == {
        "ipc_region",
        "ipc_categoria",
        "ipc_rubro",
        "salario_indice",
        "ingreso_pesos",
        "canasta",
        "tipo_cambio",
    }


def test_descarga_online_manda_user_agent_propio(monkeypatch):
    capturado = {}

    class Respuesta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"ok"

    def falso_urlopen(pedido, timeout):
        capturado["ua"] = pedido.get_header("User-agent")
        return Respuesta()

    monkeypatch.setattr(extract.urllib.request, "urlopen", falso_urlopen)
    assert extract._bajar("https://example.org") == b"ok"
    assert capturado["ua"] == config.USER_AGENT
    assert "urllib" not in capturado["ua"].lower()
