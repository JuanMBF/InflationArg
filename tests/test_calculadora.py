import json
from pathlib import Path

import pytest

from inflationarg.calculadora import ErrorCalculadora, Indices, calcular

CASOS = json.loads((Path(__file__).parent / "casos_calculadora.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def indices(con):
    return Indices.desde_base(con)


def _comparar(obtenido, esperado, tolerancia):
    if isinstance(esperado, dict):
        assert set(obtenido) == set(esperado)
        for k in esperado:
            _comparar(obtenido[k], esperado[k], tolerancia)
    elif isinstance(esperado, float) or isinstance(obtenido, float):
        assert obtenido == pytest.approx(esperado, abs=tolerancia)
    else:
        assert obtenido == esperado


@pytest.mark.parametrize("caso", CASOS["casos"], ids=lambda c: c["descripcion"])
def test_casos_compartidos(indices, caso):
    _comparar(calcular(indices, **caso["entrada"]), caso["esperado"], CASOS["tolerancia"])


@pytest.mark.parametrize("caso", CASOS["errores"], ids=lambda c: c["descripcion"])
def test_errores_compartidos(indices, caso):
    with pytest.raises(ErrorCalculadora) as error:
        calcular(indices, **caso["entrada"])
    assert error.value.codigo == caso["error"]


def test_ida_y_vuelta_por_dict(indices):
    copia = Indices.desde_dict(json.loads(json.dumps(indices.a_dict())))
    assert calcular(copia, 1000, "2020-01") == calcular(indices, 1000, "2020-01")


def test_indices_exportados_para_js_son_los_mismos(corrida, indices):
    exportado = json.loads((corrida.salida / "datos" / "indices.json").read_text(encoding="utf-8"))
    assert exportado == indices.a_dict()
    assert min(exportado["ipc"]) == "2016-12"
