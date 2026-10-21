"""Transformación: de los CSV anchos de datos.gob.ar al formato largo de staging."""

from __future__ import annotations

import pandas as pd

from . import config


def a_largo(crudos: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Una fila por (fecha, serie_id) con valor no nulo, según el catálogo."""
    partes = []
    for serie in config.CATALOGO:
        df = crudos[serie.archivo]
        if serie.columna not in df.columns:
            raise KeyError(f"{serie.archivo} no tiene la columna {serie.columna!r}")
        parte = pd.DataFrame(
            {
                "fecha": df["indice_tiempo"].str.slice(0, 10),
                "serie_id": serie.serie_id,
                "valor": pd.to_numeric(df[serie.columna], errors="coerce"),
                "archivo": serie.archivo,
            }
        )
        partes.append(parte.dropna(subset=["valor"]))
    return pd.concat(partes, ignore_index=True)


def api_a_largo(api: pd.DataFrame) -> pd.DataFrame:
    """La descarga de la API en formato largo, con el serie_id del catálogo."""
    ids = {s.id_api: s.serie_id for s in config.CATALOGO if s.id_api}
    largo = api.melt(id_vars="indice_tiempo", var_name="id_api", value_name="valor")
    largo = largo[largo["id_api"].isin(ids)]
    largo = largo.assign(
        fecha=largo["indice_tiempo"].str.slice(0, 10),
        serie_id=largo["id_api"].map(ids),
    )
    return largo[["fecha", "serie_id", "id_api", "valor"]].reset_index(drop=True)


def catalogo_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "serie_id": s.serie_id,
                "nombre": s.nombre,
                "grupo": s.grupo,
                "region": s.region,
                "unidad": s.unidad,
                "base": s.base,
                "fuente": s.fuente,
                "archivo": s.archivo,
                "columna": s.columna,
            }
            for s in config.CATALOGO
        ]
    )
