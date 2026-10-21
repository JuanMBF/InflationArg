"""Los números del README se escribieron a mano: este test los compara con la base."""

from pathlib import Path

from inflationarg import formato

README = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")


def _n(valor, dec=1):
    return formato.numero(valor, dec)


def test_respuesta_y_sectores(dashboard):
    filas = {f["serie_id"]: f for f in dashboard["consultas"]["01_respuesta_principal"]["filas"]}
    total = filas["sal_total"]
    assert f"compraba **{_n(-total['var_real_pct'])} % menos**" in README
    for f in filas.values():
        if f["serie_id"] == "sal_registrado":
            continue
        assert f"{_n(f['indice_real'])} ({_n(f['var_real_pct'])} %)".replace("-", "−") in README, f["serie_id"]
        assert f"{_n(f['minimo'])} en {f['fecha_minimo']}" in README, f["serie_id"]


def test_hallazgos(dashboard):
    k = dashboard["kpis"]
    c = dashboard["consultas"]
    assert f"{_n(k['pico_mensual']['inflacion_mensual_pct'])} % de inflación mensual" in README
    assert f"{_n(k['pico_interanual']['inflacion_interanual_pct'])} % en abril de 2024" in README
    assert (
        f"{_n(k['inflacion_mensual']['valor'])} % mensual y {_n(k['inflacion_interanual']['valor'])} % interanual"
        in README
    )
    rubros = c["05_rubros_ranking"]["filas"]
    assert f"por {_n(rubros[0]['veces'])}" in README and f"por {_n(rubros[-1]['veces'])}" in README
    canastas = k["canastas_ripte"]
    assert f"compraba {_n(canastas['inicio']['cbt_por_ripte'], 2)} Canastas" in README
    assert f"y {_n(canastas['ultimo']['cbt_por_ripte'], 2)} en {canastas['ultimo']['mes']}" in README
    usd = c["08_salario_en_dolares"]["filas"]
    assert f"US$ {_n(usd[0]['ripte_usd'], 0)} en 2017" in README
    assert f"US$ {_n(usd[-1]['ripte_usd'], 0)} de promedio en 2026 ({usd[-1]['meses']} meses)" in README
    regiones = {f["region"]: f for f in c["07_regiones"]["filas"]}
    assert f"más alta ({_n(regiones['nea']['interanual_pct'])} %)" in README
    assert f"más baja ({_n(regiones['patagonia']['interanual_pct'])} %)" in README


def test_hallazgos_derivados(dashboard):
    total = dashboard["kpis"]["salario_real_total"]
    recuperacion = 100 * (total["indice_real"] / total["minimo"] - 1)
    assert f"recuperó {_n(recuperacion)} %" in README
    assert f"sigue {_n(-total['distancia_al_maximo_pct'])} % debajo de su máximo ({total['fecha_maximo']})" in README
    nacional = next(f for f in dashboard["consultas"]["07_regiones"]["filas"] if f["region"] == "nacional")
    assert f"multiplicaron por {_n(1 + nacional['acumulado_desde_dic2016_pct'] / 100)} en promedio" in README
    ultimo = dashboard["kpis"]["canastas_ripte"]["ultimo"]
    assert f"el salario mínimo compra {_n(ultimo['cbt_por_salario_minimo'], 2)}" in README
    usd = min(dashboard["consultas"]["08_salario_en_dolares"]["filas"], key=lambda f: f["ripte_usd"])
    assert f"el mínimo fue US$ {_n(usd['ripte_usd'], 0)} en {usd['anio']}" in README
