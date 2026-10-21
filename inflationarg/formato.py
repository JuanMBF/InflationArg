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


# Encabezados legibles para las columnas de las consultas (sitio y Excel).
ETIQUETAS = {
    "serie_id": "Serie",
    "nombre": "Serie",
    "hasta": "Hasta",
    "indice_real": "Índice real",
    "var_real_pct": "Var. real %",
    "maximo": "Máximo",
    "fecha_maximo": "Mes del máximo",
    "minimo": "Mínimo",
    "fecha_minimo": "Mes del mínimo",
    "distancia_al_maximo_pct": "Distancia al máximo %",
    "ranking": "Puesto",
    "anio": "Año",
    "privado_registrado": "Privado registrado %",
    "publico": "Público %",
    "no_registrado": "No registrado %",
    "total": "Total %",
    "ganador": "Ganó",
    "perdedor": "Perdió",
    "puesto": "Puesto",
    "mes": "Mes",
    "inflacion_mensual_pct": "Mensual %",
    "inflacion_interanual_pct": "Interanual %",
    "puesto_interanual": "Puesto interanual",
    "nivel_general": "Nivel general %",
    "nucleo": "Núcleo %",
    "regulados": "Regulados %",
    "estacionales": "Estacionales %",
    "regulados_menos_nucleo": "Regulados − núcleo (pp)",
    "puesto_acumulado": "Puesto",
    "rubro": "Rubro",
    "veces": "Veces",
    "acumulado_desde_dic2016_pct": "Acumulado desde dic-2016 %",
    "acumulado_vs_general_pct": "Vs. nivel general %",
    "puesto_ultimo_anio": "Puesto último año",
    "ultimo_anio_pct": "Último año %",
    "ultimo_anio_vs_general_pp": "Vs. general (pp)",
    "cbt_pesos": "CBT ($)",
    "cbt_por_ripte": "CBT por RIPTE",
    "cbt_por_salario_minimo": "CBT por salario mínimo",
    "cbt_por_jubilacion_minima": "CBT por jubilación mínima",
    "es_ultimo": "Último",
    "region": "Región",
    "interanual_pct": "Interanual %",
    "diferencia_vs_pais_pp": "Vs. país (pp)",
    "meses": "Meses",
    "ripte_usd": "RIPTE (US$)",
    "salario_minimo_usd": "Salario mínimo (US$)",
    "jubilacion_minima_usd": "Jubilación mínima (US$)",
    "tipo_cambio_promedio": "Tipo de cambio ($/US$)",
    "analisis": "Análisis",
    "vale_hasta": "Vale hasta",
    "grupos": "Grupos de series",
    "rezago_maximo_meses": "Rezago máx. (meses)",
}

# Columnas técnicas que no se muestran en las tablas del sitio ni del Excel.
OCULTAS = {"serie_id", "es_ultimo", "grupos", "region"}


def etiqueta(columna: str) -> str:
    return ETIQUETAS.get(columna, columna.replace("_", " ").capitalize())
