"""Vistas SQL sobre bases chicas armadas a mano, con resultados calculables en la cabeza."""

import pytest
from conftest import construir_mini


def _meses(desde_anio, desde_mes, n):
    salida = []
    a, m = desde_anio, desde_mes
    for _ in range(n):
        salida.append(f"{a}-{m:02d}-01")
        m += 1
        if m == 13:
            a, m = a + 1, 1
    return salida


@pytest.fixture
def mini():
    filas = []
    # IPC: +1 % por mes desde dic-2016 (base 100).
    for i, f in enumerate(_meses(2016, 12, 19)):
        filas.append((f, "ipc_nacional", 100 * 1.01**i))
    # Salario privado: base oct-2016 = 100, +2 % por mes.
    for i, f in enumerate(_meses(2016, 10, 21)):
        filas.append((f, "sal_privado", 100 * 1.02**i))
    # RIPTE, canasta, tipo de cambio constantes.
    for f in _meses(2016, 12, 19):
        filas += [(f, "ripte", 1000.0), (f, "cbt", 250.0), (f, "tc_oficial", 20.0)]
    # Un mes posterior al corte y una marca de QA.
    filas.append(("2018-12-01", "ripte", 9999.0))
    marcas = [("2017-05-01", "ripte", "prueba")]
    con = construir_mini(filas, marcas, fecha_corte="2018-06-01")
    yield con
    con.close()


def test_dim_fecha_contigua_con_etiquetas(mini):
    filas = mini.execute("SELECT fecha, etiqueta, trimestre FROM dim_fecha ORDER BY fecha").fetchall()
    assert filas[0] == ("2016-10-01", "oct-2016", 4)
    assert filas[-1] == ("2018-06-01", "jun-2018", 2)
    assert len(filas) == 21


def test_valores_a_futuro_van_a_excluido(mini):
    assert mini.execute("SELECT serie_id, valor FROM excluido").fetchall() == [("ripte", 9999.0)]


def test_marca_de_qa_se_guarda_pero_no_se_analiza(mini):
    estado = mini.execute("SELECT estado FROM fact_valor WHERE fecha='2017-05-01' AND serie_id='ripte'").fetchone()
    assert estado == ("sospechoso",)
    en_vista = mini.execute("SELECT COUNT(*) FROM v_valor WHERE fecha='2017-05-01' AND serie_id='ripte'").fetchone()
    assert en_vista == (0,)


def test_variaciones_con_lag(mini):
    mensual, interanual, acumulada = mini.execute(
        "SELECT var_mensual, var_interanual, var_acumulada_anio FROM v_variacion "
        "WHERE serie_id='ipc_nacional' AND fecha='2018-03-01'"
    ).fetchone()
    assert mensual == pytest.approx(0.01)
    assert interanual == pytest.approx(1.01**12 - 1)
    assert acumulada == pytest.approx(1.01**3 - 1)


def test_lag_no_compara_contra_un_mes_equivocado(mini):
    # Junio 2017 de RIPTE: el mes anterior (mayo) está en cuarentena, así que no hay variación.
    fila = mini.execute("SELECT var_mensual FROM v_variacion WHERE serie_id='ripte' AND fecha='2017-06-01'").fetchone()
    assert fila == (None,)


def test_salario_real_rebasado_y_deflactado(mini):
    nominal, real, caida = mini.execute(
        "SELECT indice_nominal, indice_real, caida_desde_maximo FROM v_salario_real "
        "WHERE serie_id='sal_privado' AND fecha='2017-12-01'"
    ).fetchone()
    assert nominal == pytest.approx(100 * 1.02**12)
    assert real == pytest.approx(100 * (1.02 / 1.01) ** 12)
    assert caida == pytest.approx(0)  # sube todos los meses: siempre está en su máximo


def test_ranking_de_inflacion(mini):
    filas = mini.execute(
        "SELECT var_mensual, ranking_mensual FROM v_inflacion WHERE serie_id='ipc_nacional' ORDER BY ranking_mensual"
    ).fetchall()
    assert filas[0][1] == 1
    assert filas[0][0] == max(v for v, _ in filas)
    assert len(filas) == 18  # 19 meses menos el primero, que no tiene mes anterior


def test_poder_de_compra_y_dolares(mini):
    assert mini.execute("SELECT cbt_por_ripte FROM v_poder_compra WHERE fecha='2017-01-01'").fetchone() == (4.0,)
    assert mini.execute("SELECT ripte_usd FROM v_salario_usd WHERE fecha='2017-01-01'").fetchone() == (50.0,)


def test_cobertura_y_rezago(mini):
    fila = mini.execute(
        "SELECT desde, hasta, meses_de_rezago FROM v_cobertura WHERE serie_id='ipc_nacional'"
    ).fetchone()
    assert fila == ("2016-12-01", "2018-06-01", 0)


def test_la_base_real_respeta_las_restricciones(con):
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    assert con.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert con.execute("SELECT COUNT(*) FROM fact_valor WHERE estado='sospechoso'").fetchone() == (1,)
