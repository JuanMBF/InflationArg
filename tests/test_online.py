"""Modo online (GitHub Actions) con la red simulada: baja, re-hashea y corre la QA sobre lo nuevo."""

import io

import pandas as pd

from inflationarg import config, extract, pipeline


def _red_falsa(monkeypatch, modificar_ripte=False):
    manifiesto = extract.leer_manifiesto()
    por_url = {a["url"]: config.DIR_RAW / a["archivo"] for a in manifiesto["archivos"]}
    pedidos = []

    def bajar(url, timeout=60):
        pedidos.append(url)
        if url.startswith(extract.URL_API):
            ids = url.split("ids=")[1].split("&")[0].split(",")
            api = pd.read_csv(config.DIR_RAW / config.ARCHIVO_API, dtype={"indice_tiempo": str})
            return api[["indice_tiempo", *ids]].to_csv(index=False).encode()
        datos = por_url[url].read_bytes()
        if modificar_ripte and url.endswith("serie-mensual.csv") and "ripte" in url:
            datos += b"2026-09-01,1999999.99\n"
        return datos

    monkeypatch.setattr(extract, "_bajar", bajar)
    return pedidos


def test_bajar_todo_escribe_manifiesto_nuevo(monkeypatch, tmp_path):
    pedidos = _red_falsa(monkeypatch, modificar_ripte=True)
    nuevo = extract.bajar_todo(tmp_path)
    assert (tmp_path / config.MANIFIESTO).exists()
    ripte = next(a for a in nuevo["archivos"] if a["archivo"] == "ripte.csv")
    assert ripte["filas"] == 387
    assert ripte["sha256"] == extract.sha256(tmp_path / "ripte.csv")
    assert sum(u.startswith(extract.URL_API) for u in pedidos) == 2  # 33 series en lotes de 20
    assert "header=ids" in next(u for u in pedidos if u.startswith(extract.URL_API))


def test_pipeline_online_completo(monkeypatch, tmp_path):
    _red_falsa(monkeypatch)
    corrida = pipeline.correr_todo(online=True, salida=tmp_path, sitio=False, log=lambda *_: None)
    assert corrida.directorio_datos == tmp_path / "raw_online"
    assert not corrida.reporte.tiene_errores
    api = pd.read_csv(io.StringIO((tmp_path / "raw_online" / config.ARCHIVO_API).read_text()))
    assert len(api.columns) == 1 + len([s for s in config.CATALOGO if s.id_api])
