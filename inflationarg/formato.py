"""Formato de números y fechas en es-AR (punto de miles, coma decimal)."""

from __future__ import annotations

import math

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def redondear(valor: float, decimales: int = 2) -> float:
    """Redondeo "half up" idéntico a Math.round de JavaScript (no el bancario de round())."""
    factor = 10**decimales
    return math.floor(valor * factor + 0.5) / factor


def numero(valor: float | None, decimales: int = 0) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "–"
    texto = f"{redondear(valor, decimales):,.{decimales}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def pesos(valor: float | None, decimales: int = 0) -> str:
    return "–" if valor is None else f"$ {numero(valor, decimales)}"


def porcentaje(valor: float | None, decimales: int = 1, signo: bool = False) -> str:
    """`valor` ya expresado en puntos porcentuales (12.3 -> "12,3 %")."""
    if valor is None:
        return "–"
    texto = numero(valor, decimales)
    if signo and redondear(valor, decimales) > 0:
        texto = "+" + texto
    return f"{texto}\u00a0%".replace("-", "−")


def mes(fecha: str, largo: bool = False) -> str:
    """Convierte "2026-09-01" en "sep-2026" (o "septiembre de 2026")."""
    anio, m = int(fecha[:4]), int(fecha[5:7])
    return f"{MESES_LARGOS[m - 1]} de {anio}" if largo else f"{MESES[m - 1]}-{anio}"
