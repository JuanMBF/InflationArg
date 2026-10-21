"""Línea de comandos.

python -m inflationarg all              # todo offline: QA, base, exports y sitio
python -m inflationarg all --online     # baja datos nuevos de datos.gob.ar
python -m inflationarg qa               # solo la QA de datos
python -m inflationarg consulta 01      # corre una consulta de sql/consultas
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from . import config, db, pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inflationarg", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)

    p_all = sub.add_parser("all", help="QA, base SQLite, exports y sitio")
    p_all.add_argument("--online", action="store_true", help="bajar datos nuevos de datos.gob.ar")
    p_all.add_argument("--salida", type=Path, default=config.DIR_BUILD)
    p_all.add_argument("--sin-sitio", action="store_true", help="no generar el sitio")

    p_qa = sub.add_parser("qa", help="solo la QA de datos (sale con 1 si hay errores)")
    p_qa.add_argument("--online", action="store_true")
    p_qa.add_argument("--salida", type=Path, default=config.DIR_BUILD)

    p_c = sub.add_parser("consulta", help="corre una consulta de negocio sobre build/inflationarg.db")
    p_c.add_argument("nombre", help="prefijo del archivo, p. ej. 01 o 05_rubros")
    p_c.add_argument("--salida", type=Path, default=config.DIR_BUILD)

    args = parser.parse_args(argv)

    if args.comando == "all":
        pipeline.correr_todo(online=args.online, salida=args.salida, sitio=not args.sin_sitio)
        return 0

    if args.comando == "qa":
        _, reporte, _ = pipeline.preparar(online=args.online, salida=args.salida)
        print(reporte.a_markdown())
        return 1 if reporte.tiene_errores else 0

    ruta_db = args.salida / "inflationarg.db"
    if not ruta_db.exists():
        print("Primero corré: python -m inflationarg all", file=sys.stderr)
        return 1
    consultas = {k: v for k, v in db.consultas_de_negocio().items() if k.startswith(args.nombre)}
    if len(consultas) != 1:
        print(f"Elegí una de: {', '.join(db.consultas_de_negocio())}", file=sys.stderr)
        return 1
    ((nombre, sql),) = consultas.items()
    con = db.conectar(ruta_db)
    print(f"-- {nombre}\n-- {db.descripcion_consulta(sql)}\n")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(db.consultar(con, sql).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
