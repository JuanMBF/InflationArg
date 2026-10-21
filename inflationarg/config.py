"""Rutas del proyecto y catálogo de series.

El catálogo es la única fuente de verdad sobre qué columna de qué CSV oficial
se carga, con qué nombre y en qué grupo de análisis cae. Todo lo demás
(dimensiones, vistas, sitio) se deriva de acá.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_SQL = RAIZ / "sql"
DIR_CONSULTAS = DIR_SQL / "consultas"
DIR_BUILD = RAIZ / "build"
DIR_SITE_SRC = RAIZ / "site"

MANIFIESTO = "MANIFEST.json"
ARCHIVO_API = "api_series_mensuales.csv"

# Bases oficiales: el IPC es base dic-2016 = 100 y el índice de salarios, oct-2016 = 100.
BASE_IPC = "2016-12-01"
BASE_SALARIOS = "2016-10-01"
# Inicio del análisis: primer mes con IPC nacional (base dic-2016).
INICIO_ANALISIS = "2016-12-01"

# La API rechaza el User-Agent por defecto de urllib con un 403.
USER_AGENT = "InflationArg/1.0 (+https://github.com/JuanMBF/InflationArg)"

REGIONES = {
    "nacional": "Total país",
    "gba": "GBA",
    "pampeana": "Pampeana",
    "nea": "Noreste (NEA)",
    "noa": "Noroeste (NOA)",
    "cuyo": "Cuyo",
    "patagonia": "Patagonia",
}

RUBROS = {
    "alimentos_bebidas_no_alcoholicas": "Alimentos y bebidas no alcohólicas",
    "bebidas_alcoholicas_tabaco": "Bebidas alcohólicas y tabaco",
    "prendas_vestir_calzado": "Prendas de vestir y calzado",
    "vivienda_agua_electricidad_combustibles": "Vivienda, agua, electricidad y combustibles",
    "equipamiento_mantenimientos_hogar": "Equipamiento y mantenimiento del hogar",
    "salud": "Salud",
    "transporte": "Transporte",
    "comunicaciones": "Comunicación",
    "recreacion_cultura": "Recreación y cultura",
    "educacion": "Educación",
    "restaurantes_hoteles": "Restaurantes y hoteles",
    "bienes_servicios_varios": "Bienes y servicios varios",
}


@dataclass(frozen=True)
class Serie:
    serie_id: str
    nombre: str
    grupo: str
    unidad: str
    fuente: str
    archivo: str
    columna: str
    region: str = "nacional"
    base: str | None = None
    id_api: str | None = None
    # Meses de rezago con que se publica la serie: el dato del mes t refleja el mes t - desfase.
    # El modelo corre la fecha antes de analizar (sql/02_modelo.sql).
    desfase_meses: int = 0


def _catalogo() -> list[Serie]:
    series: list[Serie] = []
    ids_api_region = {
        "nacional": "148.3_INIVELNAL_DICI_M_26",
        "gba": "148.3_INIVELGBA_DICI_M_21",
        "pampeana": "148.3_INIVELANA_DICI_M_26",
        "nea": "148.3_INIVELNEA_DICI_M_21",
        "noa": "148.3_INIVELNOA_DICI_M_21",
        "cuyo": "148.3_INIVELUYO_DICI_M_22",
        "patagonia": "148.3_INIVELNIA_DICI_M_27",
    }
    for region, nombre in REGIONES.items():
        series.append(
            Serie(
                f"ipc_{region}",
                f"IPC nivel general – {nombre}",
                "ipc_region",
                "índice",
                "INDEC",
                "ipc_nivel_general_regiones.csv",
                f"ipc_ng_{region}",
                region=region,
                base=BASE_IPC,
                id_api=ids_api_region[region],
            )
        )

    categorias = {
        "nucleo": ("IPC núcleo", "148.3_INUCLEONAL_DICI_M_19"),
        "regulados": ("IPC regulados", "148.3_IREGULANAL_DICI_M_22"),
        "estacionales": ("IPC estacionales", "148.3_IESTACINAL_DICI_M_25"),
    }
    for clave, (nombre, id_api) in categorias.items():
        series.append(
            Serie(
                f"ipc_{clave}",
                nombre,
                "ipc_categoria",
                "índice",
                "INDEC",
                "ipc_categorias.csv",
                f"ipc_{clave}_nacional",
                base=BASE_IPC,
                id_api=id_api,
            )
        )

    ids_api_rubro = {
        "alimentos_bebidas_no_alcoholicas": "146.3_IALIMENNAL_DICI_M_45",
        "bebidas_alcoholicas_tabaco": "146.3_IBEBIDANAL_DICI_M_39",
        "prendas_vestir_calzado": "146.3_IPRENDANAL_DICI_M_35",
        "vivienda_agua_electricidad_combustibles": "146.3_IVIVIENNAL_DICI_M_52",
        "equipamiento_mantenimientos_hogar": "146.3_IEQUIPANAL_DICI_M_46",
        "salud": "146.3_ISALUDNAL_DICI_M_18",
        "transporte": "146.3_ITRANSPNAL_DICI_M_23",
        "comunicaciones": "146.3_ICOMUNINAL_DICI_M_27",
        "recreacion_cultura": "146.3_IRECREANAL_DICI_M_31",
        "educacion": "146.3_IEDUCACNAL_DICI_M_22",
        "restaurantes_hoteles": "146.3_IRESTAUNAL_DICI_M_33",
        "bienes_servicios_varios": "146.3_IBIENESNAL_DICI_M_36",
    }
    for clave, nombre in RUBROS.items():
        series.append(
            Serie(
                f"rubro_{clave}",
                nombre,
                "ipc_rubro",
                "índice",
                "INDEC",
                "ipc_capitulos.csv",
                f"ipc_{clave}_nacional",
                base=BASE_IPC,
                id_api=ids_api_rubro[clave],
            )
        )

    salarios = [
        ("sal_total", "Salarios – total", "indice_salarios", "149.1_TL_INDIIOS_OCTU_0_21"),
        (
            "sal_registrado",
            "Salarios – registrados",
            "indice_salarios_registrado",
            "149.1_TL_REGIADO_OCTU_0_16",
        ),
        (
            "sal_privado",
            "Salarios – privado registrado",
            "indice_salarios_registrado_sector_privado",
            "149.1_SOR_PRIADO_OCTU_0_25",
        ),
        (
            "sal_publico",
            "Salarios – sector público",
            "indice_salarios_registrado_sector_publico",
            "149.1_SOR_PUBICO_OCTU_0_14",
        ),
        (
            "sal_no_registrado",
            "Salarios – privado no registrado",
            "indice_salarios_no_registrado_sector_privado",
            "149.1_SOR_PRIADO_OCTU_0_28",
        ),
    ]
    for serie_id, nombre, columna, id_api in salarios:
        series.append(
            Serie(
                serie_id,
                nombre,
                "salario_indice",
                "índice",
                "INDEC",
                "indice_salarios.csv",
                columna,
                base=BASE_SALARIOS,
                id_api=id_api,
                # El INDEC publica el no registrado con 5 meses de rezago: el valor del mes t mide t - 5.
                desfase_meses=5 if serie_id == "sal_no_registrado" else 0,
            )
        )

    series += [
        Serie(
            "ripte",
            "RIPTE (remuneración promedio de trabajadores estables)",
            "ingreso_pesos",
            "pesos",
            "Secretaría de Seguridad Social",
            "ripte.csv",
            "ripte",
            id_api="158.1_REPTE_0_0_5",
        ),
        Serie(
            "smvm",
            "Salario mínimo, vital y móvil",
            "ingreso_pesos",
            "pesos",
            "Consejo del Salario / MTEySS",
            "salario_minimo.csv",
            "salario_minimo_vital_movil_mensual",
            id_api="57.1_SMVMM_0_M_34",
        ),
        Serie(
            "haber_minimo",
            "Haber mínimo jubilatorio",
            "ingreso_pesos",
            "pesos",
            "ANSES",
            "haber_minimo_jubilatorio.csv",
            "mensual_pesos_corrientes",
            id_api="58.1_MP_0_M_13",
        ),
        Serie(
            "cbt",
            "Canasta Básica Total (adulto equivalente, GBA)",
            "canasta",
            "pesos",
            "INDEC",
            "canastas_basicas.csv",
            "canasta_basica_total",
            region="gba",
            id_api="150.1_CSTA_BATAL_0_D_20",
        ),
        Serie(
            "cba",
            "Canasta Básica Alimentaria (adulto equivalente, GBA)",
            "canasta",
            "pesos",
            "INDEC",
            "canastas_basicas.csv",
            "canasta_basica_alimentaria",
            region="gba",
            id_api="150.1_CSTA_BARIA_0_D_26",
        ),
        Serie(
            "tc_oficial",
            "Tipo de cambio oficial de valuación (BCRA, promedio mensual)",
            "tipo_cambio",
            "pesos por dólar",
            "BCRA",
            "tipo_cambio_bcra.csv",
            "tipo_cambio_valuacion",
            id_api="92.1_TCV_0_0_21",
        ),
    ]
    return series


CATALOGO: list[Serie] = _catalogo()
POR_ID: dict[str, Serie] = {s.serie_id: s for s in CATALOGO}

SECTORES_SALARIO = {
    "sal_total": "Total",
    "sal_privado": "Privado registrado",
    "sal_publico": "Público",
    "sal_no_registrado": "Privado no registrado",
}
