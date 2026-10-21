import pytest

from inflationarg import formato
from inflationarg.__main__ import main


@pytest.mark.parametrize(
    ("valor", "dec", "esperado"),
    [(1234567.891, 2, "1.234.567,89"), (0.5, 0, "1"), (2.5, 0, "3"), (-2.5, 0, "-2"), (None, 0, "–")],
)
def test_numero_es_ar_con_redondeo_half_up(valor, dec, esperado):
    assert formato.numero(valor, dec) == esperado


def test_porcentaje_pesos_y_meses():
    assert formato.porcentaje(-21.79, 1) == "−21,8\u00a0%"
    assert formato.porcentaje(3.04, 1, signo=True) == "+3,0\u00a0%"
    assert formato.pesos(1500000) == "$ 1.500.000"
    assert formato.mes("2026-09-01") == "sep-2026"
    assert formato.mes("2026-09-01", largo=True) == "septiembre de 2026"


def test_cli_qa_sale_con_cero(capsys):
    assert main(["qa"]) == 0
    assert "Reporte de QA" in capsys.readouterr().out


def test_cli_consulta(corrida, capsys):
    assert main(["consulta", "03", "--salida", str(corrida.salida)]) == 0
    salida = capsys.readouterr().out
    assert "03_inflacion_picos" in salida and "dic-2023" in salida


def test_cli_consulta_inexistente(corrida, capsys):
    assert main(["consulta", "99", "--salida", str(corrida.salida)]) == 1
    assert main(["consulta", "01", "--salida", "/no/existe"]) == 1
