"""Calculadora de ajuste salarial (la misma lógica que site/static/js/calculadora.js).

Pregunta de RR.HH.: "si alguien cobraba X en el mes M, ¿cuánto tiene que cobrar hoy
para no perder contra la inflación?, ¿y cuánto aumentó en ese período el sector?".
Los casos de prueba de tests/casos_calculadora.json los corren pytest y node.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass

from .config import SECTORES_SALARIO
from .formato import mes as etiqueta_mes
from .formato import redondear


class ErrorCalculadora(ValueError):
    def __init__(self, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


@dataclass
class Indices:
    """Índices mensuales por clave "AAAA-MM": IPC nacional e índice de salarios por sector."""

    ipc: dict[str, float]
    salarios: dict[str, dict[str, float]]

    @classmethod
    def desde_base(cls, con: sqlite3.Connection) -> Indices:
        filas = con.execute(
            "SELECT serie_id, substr(fecha, 1, 7), valor FROM v_valor "
            "WHERE serie_id = 'ipc_nacional' OR grupo = 'salario_indice' ORDER BY fecha"
        ).fetchall()
        ipc: dict[str, float] = {}
        salarios: dict[str, dict[str, float]] = {s: {} for s in SECTORES_SALARIO}
        for serie_id, mes, valor in filas:
            if serie_id == "ipc_nacional":
                ipc[mes] = valor
            elif serie_id in salarios:
                salarios[serie_id][mes] = valor
        return cls(ipc, salarios)

    @classmethod
    def desde_dict(cls, datos: dict) -> Indices:
        return cls(datos["ipc"], datos["salarios"])

    def a_dict(self) -> dict:
        return {"ipc": self.ipc, "salarios": self.salarios}


def _variacion(serie: dict[str, float], desde: str, hasta: str) -> float:
    return serie[hasta] / serie[desde] - 1


def _monto_valido(valor) -> bool:
    """Número finito y positivo (bool no cuenta como número, igual que en JS)."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor) and valor > 0


def _mes(aaaamm: str) -> str:
    return etiqueta_mes(aaaamm + "-01")


def calcular(
    indices: Indices,
    sueldo: float,
    desde: str,
    hasta: str | None = None,
    sector: str | None = None,
    sueldo_actual: float | None = None,
) -> dict:
    """Ajuste por inflación de `sueldo` entre `desde` y `hasta` (meses "AAAA-MM").

    - `hasta` por defecto es el último mes con IPC.
    - `sector`: compara contra lo que aumentaron los salarios de ese sector en el
      mismo período (si el sector no tiene datos hasta `hasta`, usa su último mes).
      Si el período no tiene meses del sector para comparar, el cálculo por IPC sigue
      y `aviso_sector` explica por qué no hay comparación.
    - `sueldo_actual`: lo que se cobra hoy, para medir ganancia o pérdida real.
    """
    meses_ipc = sorted(indices.ipc)
    hasta = hasta or meses_ipc[-1]
    if not _monto_valido(sueldo):
        raise ErrorCalculadora("sueldo_invalido", "El sueldo tiene que ser un número mayor a cero.")
    if sueldo_actual is not None and not _monto_valido(sueldo_actual):
        raise ErrorCalculadora("sueldo_invalido", "El sueldo actual tiene que ser un número mayor a cero.")
    for mes in (desde, hasta):
        if mes not in indices.ipc:
            raise ErrorCalculadora(
                "mes_fuera_de_rango",
                f"No hay IPC para {mes}: elegí un mes entre {meses_ipc[0]} y {meses_ipc[-1]}.",
            )
    if hasta < desde:
        raise ErrorCalculadora("periodo_invertido", "El mes final no puede ser anterior al inicial.")

    inflacion = _variacion(indices.ipc, desde, hasta)
    equivalente = sueldo * (1 + inflacion)
    resultado: dict = {
        "desde": desde,
        "hasta": hasta,
        "inflacion_pct": redondear(100 * inflacion, 2),
        "sueldo_equivalente": redondear(equivalente, 2),
        "sector": None,
        "aviso_sector": None,
        "actual": None,
    }

    if sector is not None:
        if sector not in indices.salarios:
            raise ErrorCalculadora("sector_desconocido", f"Sector desconocido: {sector}.")
        serie = indices.salarios[sector]
        nombre = SECTORES_SALARIO[sector]
        ultimo_sector = max(serie)
        hasta_sector = min(hasta, ultimo_sector)
        if desde >= ultimo_sector:
            resultado["aviso_sector"] = (
                f"El índice de salarios «{nombre}» llega hasta {_mes(ultimo_sector)}: "
                "para comparar con el sector, elegí un mes inicial anterior."
            )
        elif desde not in serie:
            resultado["aviso_sector"] = f"El índice de salarios «{nombre}» no tiene dato para {_mes(desde)}."
        elif desde == hasta_sector:
            resultado["aviso_sector"] = "Para comparar con el sector, elegí un mes final posterior al inicial."
        else:
            aumento = _variacion(serie, desde, hasta_sector)
            inflacion_sector = _variacion(indices.ipc, desde, hasta_sector)
            resultado["sector"] = {
                "sector": sector,
                "nombre": nombre,
                "hasta": hasta_sector,
                "aumento_pct": redondear(100 * aumento, 2),
                "inflacion_pct": redondear(100 * inflacion_sector, 2),
                "sueldo_segun_sector": redondear(sueldo * (1 + aumento), 2),
                "resultado_real_pct": redondear(100 * ((1 + aumento) / (1 + inflacion_sector) - 1), 2),
            }

    if sueldo_actual is not None:
        resultado["actual"] = {
            "sueldo_actual": sueldo_actual,
            "diferencia_pesos": redondear(sueldo_actual - equivalente, 2),
            "resultado_real_pct": redondear(100 * (sueldo_actual / equivalente - 1), 2),
            "ajuste_para_empatar_pct": redondear(100 * (equivalente / sueldo_actual - 1), 2),
        }
    return resultado
