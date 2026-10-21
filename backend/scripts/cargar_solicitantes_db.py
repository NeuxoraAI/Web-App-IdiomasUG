"""Carga solicitantes desde Excel A LA BASE DE DATOS y genera sus claves.

La validación y el registro viven en db/carga.py (los comparte con la API);
este script solo lee argumentos e imprime el resumen.

El Excel de salida es el ÚNICO lugar donde quedan las claves en texto plano
(la base solo guarda su hash). Guárdalo en un lugar seguro.

Uso (desde backend/):
    python scripts/cargar_solicitantes_db.py tests/fixtures/alumnos_solicitantes.xlsx --convocatoria 2026B
    python scripts/cargar_solicitantes_db.py entrada.xlsx -c 2026B -o codigos_acceso.xlsx

Columnas requeridas: CURP, Nombre, Idioma. Opcional: Correo.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from db.carga import FilaCarga, generar_excel_salida, procesar  # noqa: E402
from db.conexion import obtener_db, verificar_conexion  # noqa: E402


def imprimir_resumen(filas: list[FilaCarga]) -> None:
    validas = [f for f in filas if f.es_valida]
    errores = [f for f in filas if not f.es_valida]
    print(f"\n{'=' * 60}")
    print(f"Registrados en la base: {len(validas)}")
    print(f"Renglones con error:    {len(errores)}")
    print(f"{'=' * 60}")
    for f in errores:
        print(f"  ✗ fila {f.fila}: {f.curp or '(vacía)'} | {f.nombre or '(vacío)'} | "
              f"{f.idioma or '(vacío)'} → {f.error}")
    for f in validas:
        print(f"  ✓ fila {f.fila}: {f.curp} | {f.idioma} → {f.folio}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Carga solicitantes a MongoDB y genera claves.")
    parser.add_argument("archivo", type=Path, help="Excel de solicitantes (.xlsx)")
    parser.add_argument("--convocatoria", "-c", required=True, help="Ej. 2026B")
    parser.add_argument("--prefijo", default="EXAUBI", help="Prefijo del folio (default: EXAUBI)")
    parser.add_argument("--output", "-o", type=Path, default=Path("codigos_acceso.xlsx"))
    args = parser.parse_args(argv)

    if not args.archivo.exists():
        print(f"Error: archivo no encontrado — {args.archivo}", file=sys.stderr)
        return 1
    if not os.environ.get("CLAVE_PEPPER"):
        print("✗ Falta CLAVE_PEPPER en tu archivo .env (ver .env.example).", file=sys.stderr)
        return 1

    db = obtener_db()
    verificar_conexion(db)
    filas, errores_globales = procesar(db, pd.read_excel(args.archivo),
                                       args.convocatoria.upper(), args.prefijo)
    if errores_globales:
        for e in errores_globales:
            print(f"✗ {e}", file=sys.stderr)
        return 1

    imprimir_resumen(filas)
    generar_excel_salida(filas, args.output)
    print(f"\n✓ Excel con claves generado: {args.output}")
    print("  Es la única copia de las claves en texto plano: guárdalo en un lugar seguro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
