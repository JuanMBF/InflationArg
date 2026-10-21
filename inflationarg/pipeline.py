"""Orquestación: extract -> QA -> SQLite -> exports -> sitio."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from . import config, db, export, extract, qa, transform


@dataclass
class Corrida:
    directorio_datos: Path
    salida: Path
    reporte: qa.Reporte
    ruta_db: Path


def preparar(online: bool = False, salida: Path = config.DIR_BUILD, log=print) -> tuple:
    """Extrae los datos y corre la QA. Devuelve (staging, reporte, directorio de datos)."""
    if online:
        directorio = salida / "raw_online"
        log(f"→ Bajando datos oficiales a {directorio} …")
        extract.bajar_todo(directorio)
    else:
        directorio = config.DIR_RAW
        log(f"→ Usando la foto offline de {directorio.relative_to(config.RAIZ)}")
    manifiesto = extract.leer_manifiesto(directorio)
    crudos = extract.leer_crudos(directorio)
    stg = transform.a_largo(crudos)
    api = transform.api_a_largo(crudos[config.ARCHIVO_API])
    inventario = extract.inventario(directorio, manifiesto)
    reporte = qa.correr(stg, api, inventario, manifiesto["descargado"], online=online)
    return stg, reporte, directorio


def correr_todo(online: bool = False, salida: Path = config.DIR_BUILD, sitio: bool = True, log=print) -> Corrida:
    inicio = time.perf_counter()
    salida.mkdir(parents=True, exist_ok=True)
    stg, reporte, directorio = preparar(online, salida, log)

    (salida / "qa").mkdir(exist_ok=True)
    (salida / "qa" / "reporte.md").write_text(reporte.a_markdown(), encoding="utf-8")
    (salida / "qa" / "reporte.json").write_text(reporte.a_json(), encoding="utf-8")
    conteo = reporte.conteo()
    log(
        f"→ QA: {conteo['ok']} ok, {conteo['info']} info, {conteo['alerta']} alertas, "
        f"{conteo['error']} errores (build/qa/reporte.md)"
    )
    if reporte.tiene_errores:
        raise SystemExit("✗ La QA encontró errores: no se generan exports. Ver build/qa/reporte.md")

    ruta_db = salida / "inflationarg.db"
    ruta_db.unlink(missing_ok=True)
    con = db.conectar(ruta_db)
    db.construir(con, stg, reporte.marcas, reporte.fecha_corte, reporte.fecha_descarga)
    log(f"→ Base SQLite: {ruta_db}")

    consultas = export.resultados_consultas(con)
    datos = export.datos_dashboard(con, consultas, reporte)
    export.escribir_json(datos, salida / "datos" / "dashboard.json")
    export.escribir_json(export.indices_calculadora(con), salida / "datos" / "indices.json")
    export.exportar_power_bi(con, salida / "powerbi")
    export.exportar_excel(con, consultas, reporte, salida / "inflationarg.xlsx")
    log(f"→ Exports: {len(consultas)} consultas, Excel, Power BI y JSON del sitio")

    if sitio:
        from . import site

        destino = site.construir(datos, salida)
        log(f"→ Sitio: {destino}")
    con.close()
    log(f"✓ Listo en {time.perf_counter() - inicio:.1f} s")
    return Corrida(directorio, salida, reporte, ruta_db)
