"""QA de datos: chequeos automáticos con reporte legible.

Cada chequeo devuelve un `Resultado` con nivel:
- ``ok``: pasó.
- ``info``: no es un problema, pero hay que saberlo para leer los resultados.
- ``alerta``: anomalía real en los datos; se documenta y, si corresponde, se
  aparta la observación del análisis. No frena el pipeline.
- ``error``: los datos no son confiables; el pipeline se detiene.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import pandas as pd

from . import config
from .extract import Archivo
from .formato import mes, numero

NIVELES = ("ok", "info", "alerta", "error")
ICONOS = {"ok": "✅", "info": "ℹ️", "alerta": "⚠️", "error": "❌"}

# Rezago máximo esperado (meses entre el último dato y el mes de descarga).
REZAGO_MAXIMO = {
    "ipc_region": 2,
    "ipc_categoria": 2,
    "ipc_rubro": 2,
    "salario_indice": 4,
    "ingreso_pesos": 3,
    "canasta": 2,
    "tipo_cambio": 2,
}

# Rango plausible de variación mensual por grupo (fuera de esto, alerta).
RANGO_VAR_MENSUAL = {
    "ipc_region": (-0.03, 0.30),
    "ipc_categoria": (-0.05, 0.40),
    "ipc_rubro": (-0.10, 0.60),
    "salario_indice": (-0.05, 0.40),
    "ingreso_pesos": (-0.10, 0.60),
    "canasta": (-0.10, 0.40),
    "tipo_cambio": (-0.20, 1.50),
}

TOLERANCIA_API = 1e-4  # diferencia relativa admitida entre API y CSV (redondeo)


@dataclass
class Resultado:
    chequeo: str
    titulo: str
    nivel: str
    detalle: str
    filas: list[dict] = field(default_factory=list)


@dataclass
class Reporte:
    fecha_descarga: str
    fecha_corte: str
    resultados: list[Resultado]
    marcas: pd.DataFrame

    @property
    def tiene_errores(self) -> bool:
        return any(r.nivel == "error" for r in self.resultados)

    def conteo(self) -> dict[str, int]:
        return {n: sum(r.nivel == n for r in self.resultados) for n in NIVELES}

    def a_dict(self) -> dict:
        return {
            "fecha_descarga": self.fecha_descarga,
            "fecha_corte": self.fecha_corte,
            "conteo": self.conteo(),
            "resultados": [asdict(r) for r in self.resultados],
            "marcas": self.marcas.to_dict(orient="records"),
        }

    def a_json(self) -> str:
        return json.dumps(self.a_dict(), ensure_ascii=False, indent=2)

    def a_markdown(self) -> str:
        c = self.conteo()
        lineas = [
            "# Reporte de QA de datos",
            "",
            f"Datos descargados el {self.fecha_descarga}; ventana de análisis hasta {mes(self.fecha_corte)}.",
            "",
            f"**{c['ok']}** ok · **{c['info']}** informativos · **{c['alerta']}** alertas · **{c['error']}** errores",
            "",
            "| | Chequeo | Resultado |",
            "|---|---|---|",
        ]
        for r in self.resultados:
            lineas.append(f"| {ICONOS[r.nivel]} | {r.titulo} | {r.detalle} |")
        for r in self.resultados:
            if not r.filas:
                continue
            lineas += ["", f"## {ICONOS[r.nivel]} {r.titulo}", "", r.detalle, ""]
            columnas = list(r.filas[0])
            lineas.append("| " + " | ".join(columnas) + " |")
            lineas.append("|" + "---|" * len(columnas))
            for fila in r.filas:
                lineas.append("| " + " | ".join(_celda(fila[k]) for k in columnas) + " |")
        return "\n".join(lineas) + "\n"


def _celda(valor) -> str:
    if isinstance(valor, float):
        texto = numero(valor, 4)
        return texto.rstrip("0").rstrip(",") if "," in texto else texto
    return str(valor)


def nombre_corto(serie_id: str) -> str:
    """Nombre legible para los textos del reporte: "ripte" -> "RIPTE", "ipc_noa" -> "IPC Noroeste"."""
    serie = config.POR_ID[serie_id]
    nombre = serie.nombre.split(" (")[0].replace("IPC nivel general – ", "IPC ")
    return f"IPC {nombre.lower()}" if serie.grupo == "ipc_rubro" else nombre


def _mes(fecha: str) -> int:
    return int(fecha[:4]) * 12 + int(fecha[5:7])


# ---------------------------------------------------------------------------
# Chequeos
# ---------------------------------------------------------------------------


def chequear_archivos(inventario: list[Archivo], online: bool) -> Resultado:
    filas = [
        {
            "archivo": a.archivo,
            "filas": a.filas,
            "filas_manifiesto": a.filas_esperadas,
            "sha256": a.sha256[:12],
            "coincide": "sí" if a.sha_ok and a.filas == a.filas_esperadas else "no",
        }
        for a in inventario
    ]
    malos = [f for f in filas if f["coincide"] == "no"]
    if not malos:
        return Resultado(
            "integridad",
            "Integridad de archivos (sha256 y filas vs. manifiesto)",
            "ok",
            f"Los {len(filas)} archivos coinciden byte a byte con el manifiesto.",
            filas,
        )
    nivel = "info" if online else "error"
    detalle = f"{len(malos)} archivo(s) difieren del manifiesto" + (
        ": son datos nuevos de la descarga online." if online else ": la foto fue modificada."
    )
    return Resultado("integridad", "Integridad de archivos (sha256 y filas vs. manifiesto)", nivel, detalle, filas)


def chequear_unicidad(stg: pd.DataFrame) -> Resultado:
    dup = stg[stg.duplicated(["fecha", "serie_id"], keep=False)]
    if dup.empty:
        return Resultado(
            "unicidad",
            "Unicidad de fecha + serie",
            "ok",
            f"{numero(len(stg))} observaciones descargadas (la historia completa de cada serie, "
            "no solo la ventana de análisis), ninguna repetida.",
        )
    filas = dup.groupby("serie_id").size().reset_index(name="duplicados").to_dict("records")
    return Resultado("unicidad", "Unicidad de fecha + serie", "error", f"{len(dup)} filas duplicadas.", filas)


def fechas_validas(stg: pd.DataFrame) -> pd.Series:
    """Máscara de filas con fecha ISO de primer día de mes (las demás las reporta chequear_fechas)."""
    return stg["fecha"].astype("string").str.fullmatch(r"\d{4}-\d{2}-01").fillna(False).astype(bool)


def chequear_fechas(stg: pd.DataFrame) -> Resultado:
    filas = []
    validas = fechas_validas(stg)
    mal_formadas = stg[~validas]
    for serie_id, grupo in mal_formadas.groupby("serie_id"):
        ejemplo = grupo["fecha"].iloc[0]
        filas.append({"serie_id": serie_id, "problema": f"{len(grupo)} fechas mal formadas (p. ej. {ejemplo!r})"})
    for serie_id, grupo in stg[validas].groupby("serie_id"):
        meses = sorted(_mes(f) for f in grupo["fecha"])
        faltan = (meses[-1] - meses[0] + 1) - len(set(meses))
        if faltan:
            salteados = "1 mes salteado" if faltan == 1 else f"{faltan} meses salteados"
            filas.append({"serie_id": serie_id, "problema": salteados})
    if not filas:
        return Resultado(
            "fechas",
            "Fechas mensuales contiguas",
            "ok",
            "Todas las fechas son primero de mes y ninguna serie tiene meses salteados.",
        )
    detalle = f"{len(mal_formadas)} fechas mal formadas; {len(filas)} series con problemas de fecha."
    return Resultado("fechas", "Fechas mensuales contiguas", "error", detalle, filas)


def chequear_completitud(stg: pd.DataFrame) -> Resultado:
    filas = []
    for serie in config.CATALOGO:
        datos = stg[stg["serie_id"] == serie.serie_id]
        desde = datos["fecha"].min() if not datos.empty else None
        problema = None
        if datos.empty:
            problema = "sin datos"
        elif desde > config.INICIO_ANALISIS:
            problema = f"empieza en {mes(desde)}, después del inicio del análisis"
        if problema:
            filas.append({"serie_id": serie.serie_id, "problema": problema})
    if not filas:
        return Resultado(
            "completitud",
            "Completitud del catálogo",
            "ok",
            f"Las {len(config.CATALOGO)} series del catálogo tienen datos desde {mes(config.INICIO_ANALISIS)} o antes.",
        )
    return Resultado("completitud", "Completitud del catálogo", "error", f"{len(filas)} series incompletas.", filas)


def chequear_base_100(stg: pd.DataFrame) -> Resultado:
    filas = []
    for serie in config.CATALOGO:
        if not serie.base:
            continue
        fila = stg[(stg["serie_id"] == serie.serie_id) & (stg["fecha"] == serie.base)]
        valor = float(fila["valor"].iloc[0]) if not fila.empty else None
        if valor is None or abs(valor - 100) > 1e-6:
            filas.append({"serie_id": serie.serie_id, "base": mes(serie.base), "valor": valor})
    total = sum(1 for s in config.CATALOGO if s.base)
    if not filas:
        return Resultado(
            "base_100",
            "Base 100 de los índices",
            "ok",
            f"Los {total} índices valen 100 en su mes base (IPC dic-2016, salarios oct-2016).",
        )
    return Resultado("base_100", "Base 100 de los índices", "error", f"{len(filas)} índices fuera de base.", filas)


def chequear_rangos(stg: pd.DataFrame) -> Resultado:
    grupos = {s.serie_id: s.grupo for s in config.CATALOGO}
    negativos = stg[stg["valor"] <= 0]
    filas = []
    recorte = stg[stg["fecha"] >= config.BASE_SALARIOS].sort_values(["serie_id", "fecha"])
    for serie_id, datos in recorte.groupby("serie_id"):
        bajo, alto = RANGO_VAR_MENSUAL[grupos[serie_id]]
        var = datos["valor"].pct_change()
        fuera = datos[(var < bajo) | (var > alto)]
        for _, f in fuera.iterrows():
            filas.append(
                {
                    "serie_id": serie_id,
                    "fecha": mes(f["fecha"]),
                    "var_mensual_%": round(float(var.loc[f.name]) * 100, 1),
                    "rango_%": f"{bajo * 100:.0f} a {alto * 100:.0f}",
                }
            )
    if not negativos.empty:
        return Resultado("rangos", "Rangos plausibles", "error", f"{len(negativos)} valores ≤ 0.", filas)
    if filas:
        return Resultado(
            "rangos",
            "Rangos plausibles",
            "alerta",
            f"{len(filas)} saltos mensuales fuera del rango esperado: revisar contra la fuente.",
            filas,
        )
    return Resultado(
        "rangos",
        "Rangos plausibles",
        "ok",
        "Todos los valores son positivos y ninguna variación mensual sale del rango plausible de su grupo.",
    )


def chequear_futuro(stg: pd.DataFrame, fecha_corte: str) -> Resultado:
    futuro = stg[stg["fecha"] > fecha_corte]
    if futuro.empty:
        return Resultado("futuro", "Valores con fecha futura", "ok", "Ninguna serie trae meses posteriores al corte.")
    filas = (
        futuro.groupby("serie_id")
        .agg(meses=("fecha", "size"), desde=("fecha", "min"), hasta=("fecha", "max"))
        .reset_index()
    )
    filas["desde"] = filas["desde"].map(mes)
    filas["hasta"] = filas["hasta"].map(mes)
    nombres = ", ".join(map(nombre_corto, filas["serie_id"]))
    return Resultado(
        "futuro",
        "Valores con fecha futura",
        "alerta",
        f"{nombres}: {len(futuro)} valores posteriores a {mes(fecha_corte)} (ya fijados por resolución). "
        "Se excluyen del análisis.",
        filas.to_dict("records"),
    )


def detectar_repetidos(stg: pd.DataFrame, ventana: int = 3) -> pd.DataFrame:
    """Valores que repiten exactamente el de 2 a `ventana` meses atrás después de haber cambiado.

    En una serie de promedios mensuales en pesos (RIPTE, canastas, tipo de cambio)
    volver al centavo a un valor anterior es casi imposible: suele ser un error de carga.
    """
    grupos = {"ingreso_pesos", "canasta", "tipo_cambio"}
    ids = [s.serie_id for s in config.CATALOGO if s.grupo in grupos]
    marcas = []
    for serie_id in ids:
        datos = stg[stg["serie_id"] == serie_id].sort_values("fecha").reset_index(drop=True)
        valores = datos["valor"].tolist()
        for i in range(2, len(valores)):
            if valores[i] == valores[i - 1]:
                continue
            for atras in range(2, ventana + 1):
                if i - atras >= 0 and valores[i] == valores[i - atras]:
                    marcas.append(
                        {
                            "fecha": datos.loc[i, "fecha"],
                            "serie_id": serie_id,
                            "motivo": f"repite exacto el valor de {mes(datos.loc[i - atras, 'fecha'])}",
                            "valor": valores[i],
                        }
                    )
                    break
    return pd.DataFrame(marcas, columns=["fecha", "serie_id", "motivo", "valor"])


def chequear_repetidos(marcas: pd.DataFrame) -> Resultado:
    if marcas.empty:
        return Resultado(
            "repetidos",
            "Valores repetidos sospechosos",
            "ok",
            "Ninguna serie en pesos repite un valor anterior al centavo.",
        )
    filas = [
        {"serie_id": m.serie_id, "fecha": mes(m.fecha), "valor": m.valor, "motivo": m.motivo}
        for m in marcas.itertuples()
    ]
    detalle = "; ".join(f"{nombre_corto(f['serie_id'])} de {f['fecha']} {f['motivo']}" for f in filas)
    return Resultado(
        "repetidos",
        "Valores repetidos sospechosos",
        "alerta",
        f"{detalle}. "
        + (
            "Se carga con estado 'sospechoso' y las vistas no lo usan."
            if len(filas) == 1
            else "Se cargan con estado 'sospechoso' y las vistas no los usan."
        ),
        filas,
    )


def chequear_api(stg: pd.DataFrame, api: pd.DataFrame, fecha_corte: str) -> Resultado:
    """Consistencia entre la API de Series de Tiempo y los CSV de descarga."""
    filas = []
    for serie in config.CATALOGO:
        if not serie.id_api:
            continue
        csv = stg[(stg["serie_id"] == serie.serie_id) & (stg["fecha"] <= fecha_corte)].set_index("fecha")["valor"]
        datos_api = api[api["serie_id"] == serie.serie_id].set_index("fecha")["valor"].dropna()
        datos_api = datos_api[datos_api.index <= fecha_corte]
        comun = csv.index.intersection(api["fecha"].unique())  # meses que la API debería cubrir
        if datos_api.empty:
            filas.append(
                {"serie_id": serie.serie_id, "id_api": serie.id_api, "problema": "API vacía", "meses": len(comun)}
            )
            continue
        faltan = comun.difference(datos_api.index)
        faltan_dentro = faltan[faltan <= datos_api.index.max()]
        if len(faltan_dentro):
            filas.append(
                {
                    "serie_id": serie.serie_id,
                    "id_api": serie.id_api,
                    "problema": f"API incompleta: devuelve {len(datos_api)} de {len(comun)} meses",
                    "meses": len(faltan_dentro),
                }
            )
        ambos = csv.index.intersection(datos_api.index)
        diferencia = (datos_api[ambos] / csv[ambos] - 1).abs()
        distintos = diferencia[diferencia > TOLERANCIA_API]
        if len(distintos):
            peor = distintos.idxmax()
            filas.append(
                {
                    "serie_id": serie.serie_id,
                    "id_api": serie.id_api,
                    "problema": f"valores distintos al CSV (peor: {mes(peor)}, "
                    f"API {numero(datos_api[peor], 2)} vs. CSV {numero(csv[peor], 2)})",
                    "meses": len(distintos),
                }
            )
    if not filas:
        return Resultado(
            "api_vs_csv",
            "Consistencia API vs. CSV",
            "ok",
            "La API de Series de Tiempo devuelve los mismos valores que los CSV.",
        )
    vacias = [f["serie_id"] for f in filas if f["problema"] == "API vacía"]
    detalle = f"{len(filas)} diferencias entre la API y los CSV"
    if vacias:
        nombres = ", ".join(map(nombre_corto, vacias))
        detalle += f"; la API devolvió vacías {len(vacias)} series ({nombres}) que en el CSV están completas"
    detalle += ". El pipeline usa siempre los CSV de descarga."
    return Resultado("api_vs_csv", "Consistencia API vs. CSV", "alerta", detalle, filas)


def chequear_frescura(stg: pd.DataFrame, fecha_corte: str) -> Resultado:
    filas = []
    corte = _mes(fecha_corte)
    vigente = stg[stg["fecha"] <= fecha_corte]
    for serie in config.CATALOGO:
        hasta = vigente.loc[vigente["serie_id"] == serie.serie_id, "fecha"].max()
        if pd.isna(hasta):
            continue  # serie sin datos: ya la marca chequear_completitud como error
        rezago = corte - _mes(hasta)
        filas.append(
            {
                "serie_id": serie.serie_id,
                "ultimo_dato": mes(hasta),
                "rezago_meses": rezago,
                "maximo_esperado": REZAGO_MAXIMO[serie.grupo],
            }
        )
    viejas = [f for f in filas if f["rezago_meses"] > f["maximo_esperado"]]
    if viejas:
        nombres = ", ".join(nombre_corto(f["serie_id"]) for f in viejas)
        return Resultado("frescura", "Frescura", "alerta", f"Series con más rezago del esperado: {nombres}.", filas)
    return Resultado(
        "frescura",
        "Frescura",
        "ok",
        "Todas las series están dentro del rezago habitual de publicación.",
        filas,
    )


# Qué series usa cada conclusión (por grupo, con exclusiones o una serie puntual).
CONCLUSIONES = [
    ("Salario real: total, registrados, privado y público", ["salario_indice", "ipc_region"], {"sal_no_registrado"}),
    ("Salario real: privado no registrado", ["ipc_region"], set(), ["sal_no_registrado"]),
    ("Inflación, rubros y regiones", ["ipc_region", "ipc_categoria", "ipc_rubro"], set()),
    ("Poder de compra en canastas", ["ingreso_pesos", "canasta"], set()),
    ("Salario en dólares", ["ingreso_pesos", "tipo_cambio"], set()),
]


def chequear_alineacion(stg: pd.DataFrame, marcas: pd.DataFrame, fecha_corte: str) -> Resultado:
    """Hasta qué mes vale cada conclusión, con las series fechadas en el mes que miden."""
    vigente = stg[stg["fecha"] <= fecha_corte].merge(
        marcas[["fecha", "serie_id"]].assign(marca=True), on=["fecha", "serie_id"], how="left"
    )
    vigente = vigente[vigente["marca"].isna()]
    ultimo = {}
    for serie_id, fecha in vigente.groupby("serie_id")["fecha"].max().items():
        desfase = config.POR_ID[serie_id].desfase_meses if serie_id in config.POR_ID else 0
        ultimo[serie_id] = (pd.Period(fecha, freq="M") - desfase).strftime("%Y-%m-01")
    filas = []
    for nombre, grupos, sin, *extra in CONCLUSIONES:
        ids = [s.serie_id for s in config.CATALOGO if s.grupo in grupos and s.serie_id not in sin]
        ids += extra[0] if extra else []
        fechas = [ultimo[i] for i in ids if i in ultimo]
        filas.append({"conclusion": nombre, "vale_hasta": mes(min(fechas)) if len(fechas) == len(ids) else "sin datos"})
    distintas = [mes(f) for f in sorted(set(ultimo.values()))]
    rezagadas = [s for s in config.CATALOGO if s.desfase_meses]
    nota = "".join(
        f" El índice «{nombre_corto(s.serie_id)}» se publica con {s.desfase_meses} meses de rezago: "
        "se fecha en el mes que mide, por eso termina antes."
        for s in rezagadas
    )
    return Resultado(
        "alineacion",
        "Alineación de series",
        "info",
        f"Las series terminan en meses distintos ({distintas[0]} a {distintas[-1]}): cada conclusión "
        f"se calcula hasta el último mes en que están todas sus series.{nota}",
        filas,
    )


def correr(
    stg: pd.DataFrame,
    api: pd.DataFrame,
    inventario: list[Archivo],
    fecha_descarga: str,
    online: bool = False,
) -> Reporte:
    fecha_corte = fecha_descarga[:7] + "-01"
    # Las fechas mal formadas las reporta chequear_fechas; el resto de los chequeos usa las válidas.
    completo, stg = stg, stg[fechas_validas(stg)]
    marcas = detectar_repetidos(stg[stg["fecha"] <= fecha_corte])
    resultados = [
        chequear_archivos(inventario, online),
        chequear_unicidad(stg),
        chequear_fechas(completo),
        chequear_completitud(stg),
        chequear_base_100(stg),
        chequear_rangos(stg),
        chequear_futuro(stg, fecha_corte),
        chequear_repetidos(marcas),
        chequear_api(stg, api, fecha_corte),
        chequear_frescura(stg, fecha_corte),
        chequear_alineacion(stg, marcas, fecha_corte),
    ]
    return Reporte(fecha_descarga, fecha_corte, resultados, marcas)
