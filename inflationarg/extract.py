"""Extracción: lee la foto offline de data/raw o baja los CSV oficiales.

Modo offline (por defecto): verifica el sha256 de cada archivo contra
MANIFEST.json. Modo online: baja todo de datos.gob.ar con un User-Agent propio
(la API responde 403 al de urllib) y lo guarda en otra carpeta, sin pisar la foto.
"""

from __future__ import annotations

import hashlib
import io
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import config

URL_API = "https://apis.datos.gob.ar/series/api/series/"


@dataclass
class Archivo:
    archivo: str
    fuente: str
    url: str
    sha256_esperado: str
    sha256: str
    filas_esperadas: int
    filas: int

    @property
    def sha_ok(self) -> bool:
        return self.sha256 == self.sha256_esperado


def leer_manifiesto(directorio: Path = config.DIR_RAW) -> dict:
    return json.loads((directorio / config.MANIFIESTO).read_text(encoding="utf-8"))


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def inventario(directorio: Path, manifiesto: dict) -> list[Archivo]:
    """Compara cada archivo del manifiesto con lo que hay en disco."""
    salida = []
    for item in manifiesto["archivos"]:
        ruta = directorio / item["archivo"]
        existe = ruta.exists()
        salida.append(
            Archivo(
                archivo=item["archivo"],
                fuente=item["fuente"],
                url=item["url"],
                sha256_esperado=item["sha256"],
                sha256=sha256(ruta) if existe else "",
                filas_esperadas=item["filas"],
                filas=len(pd.read_csv(ruta)) if existe else 0,
            )
        )
    return salida


def leer_crudos(directorio: Path = config.DIR_RAW) -> dict[str, pd.DataFrame]:
    """Lee todos los CSV del catálogo y el de la API, con la fecha como texto ISO."""
    archivos = {s.archivo for s in config.CATALOGO} | {config.ARCHIVO_API}
    return {nombre: pd.read_csv(directorio / nombre, dtype={"indice_tiempo": str}) for nombre in sorted(archivos)}


def _bajar(url: str, timeout: int = 60) -> bytes:
    pedido = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=timeout) as respuesta:
        return respuesta.read()


def bajar_api(ids: list[str], lote: int = 20) -> pd.DataFrame:
    """Baja las series de la API de Series de Tiempo en lotes y las une por fecha."""
    partes = []
    for i in range(0, len(ids), lote):
        url = f"{URL_API}?ids={','.join(ids[i : i + lote])}&format=csv&header=ids&limit=1000&start_date=2016-01-01"
        partes.append(pd.read_csv(io.BytesIO(_bajar(url)), dtype={"indice_tiempo": str}).set_index("indice_tiempo"))
    return pd.concat(partes, axis=1).reset_index()


def bajar_todo(destino: Path, directorio_foto: Path = config.DIR_RAW) -> dict:
    """Baja los CSV oficiales a `destino` y escribe un manifiesto nuevo con sus hashes."""
    destino.mkdir(parents=True, exist_ok=True)
    manifiesto = leer_manifiesto(directorio_foto)
    nuevos = []
    for item in manifiesto["archivos"]:
        ruta = destino / item["archivo"]
        nuevo = dict(item)
        if item["archivo"] == config.ARCHIVO_API:
            # La API solo se usa para el cruce de la QA: si falla, se sigue con un archivo vacío
            # (la QA lo reporta como alerta) en vez de abortar toda la actualización.
            ids = [s.id_api for s in config.CATALOGO if s.id_api]
            try:
                api = bajar_api(ids)
            except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
                api = pd.DataFrame(columns=["indice_tiempo"])
                nuevo["error"] = f"la API no respondió: {error}"
            api.to_csv(ruta, index=False)
        else:
            ruta.write_bytes(_bajar(item["url"]))
        datos = pd.read_csv(ruta, dtype={"indice_tiempo": str})
        fechas = datos["indice_tiempo"].dropna().str.slice(0, 10)
        nuevo["sha256"] = sha256(ruta)
        nuevo["bytes"] = ruta.stat().st_size
        nuevo["filas"] = len(datos)
        if not fechas.empty:
            nuevo["desde"], nuevo["hasta"] = fechas.min(), fechas.max()
        nuevos.append(nuevo)
    manifiesto_nuevo = dict(manifiesto, archivos=nuevos)
    manifiesto_nuevo["descargado"] = pd.Timestamp.today().strftime("%Y-%m-%d")
    (destino / config.MANIFIESTO).write_text(
        json.dumps(manifiesto_nuevo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifiesto_nuevo
