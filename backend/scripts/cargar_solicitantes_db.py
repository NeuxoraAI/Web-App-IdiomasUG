"""Carga solicitantes desde Excel A LA BASE DE DATOS y genera sus claves.

Es la versión con MongoDB de scripts/cargar_solicitantes.py: reutiliza su
validación de CURP y su formato de clave, pero ahora

  * los idiomas válidos se leen de la colección `idiomas` (ya no de un Enum),
  * cada solicitante válido queda guardado en `sustentantes` y `asignaciones`,
  * los duplicados se detectan también contra lo que YA está en la base,
  * cada asignación recibe un folio consecutivo (EXAUBI-2026B-0001…).

El Excel de salida es el ÚNICO lugar donde quedan las claves en texto plano
(la base solo guarda su hash). Guárdalo en un lugar seguro.

Uso (desde la raíz del repositorio):
    python scripts/cargar_solicitantes_db.py tests/fixtures/alumnos_solicitantes.xlsx --convocatoria 2026B
    python scripts/cargar_solicitantes_db.py entrada.xlsx -c 2026B -o codigos_acceso.xlsx

Columnas requeridas: CURP, Nombre, Idioma. Opcional: Correo.
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from db.conexion import obtener_db, verificar_conexion  # noqa: E402
from db.esquemas import PATRON_CORREO  # noqa: E402
from db.operaciones import YaRegistrado, idiomas_activos, registrar_asignacion  # noqa: E402
from scripts.cargar_solicitantes import validate_curp  # noqa: E402

COLUMNAS_REQUERIDAS = {"CURP", "Nombre", "Idioma"}


@dataclass
class FilaCarga:
    fila: int                      # número de renglón en Excel (encabezado = 1)
    curp: str
    nombre: str
    idioma: str
    correo: str = ""
    folio: str | None = None
    clave: str | None = None
    error: str | None = None

    @property
    def es_valida(self) -> bool:
        return self.error is None


def _texto(valor) -> str:
    return "" if pd.isna(valor) else str(valor).strip()


def procesar(db, df: pd.DataFrame, convocatoria: str, prefijo: str = "EXAUBI"
             ) -> tuple[list[FilaCarga], list[str]]:
    """Valida cada renglón y registra en la base los válidos."""
    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        return [], [f"Columnas faltantes en el archivo: {', '.join(sorted(faltantes))}"]

    catalogo = idiomas_activos(db)          # {'Francés': 'fr', …}
    if not catalogo:
        return [], ["No hay idiomas activos en la base. ¿Ya ejecutaste scripts/sembrar.py?"]

    filas: list[FilaCarga] = []
    vistos: set[tuple[str, str]] = set()

    for i, row in df.iterrows():
        f = FilaCarga(
            fila=int(i) + 2,
            curp=_texto(row.get("CURP")),
            nombre=_texto(row.get("Nombre")),
            idioma=_texto(row.get("Idioma")),
            correo=_texto(row.get("Correo")) if "Correo" in df.columns else "",
        )
        filas.append(f)

        # Mismas reglas y mensajes que scripts/cargar_solicitantes.py
        if not f.curp:
            f.error = "CURP vacía"
            continue
        if not f.nombre:
            f.error = "Nombre vacío"
            continue
        if not f.idioma:
            f.error = "Idioma vacío"
            continue
        try:
            f.curp = validate_curp(f.curp)
        except ValueError:
            f.error = "CURP inválida"
            continue
        if f.correo and not re.match(PATRON_CORREO, f.correo):
            f.error = "Correo inválido"  # the sustentantes validator would reject it mid-upload
            continue
        if f.idioma not in catalogo:
            f.error = f"Idioma no válido: '{f.idioma}'"
            continue
        if (f.curp, f.idioma) in vistos:
            f.error = "Registro duplicado"
            continue
        vistos.add((f.curp, f.idioma))

        # Nueva regla: también es duplicado si ya estaba en la base
        try:
            asignacion, clave = registrar_asignacion(
                db, curp=f.curp, nombre=f.nombre, idioma=catalogo[f.idioma],
                convocatoria=convocatoria, correo=f.correo or None, prefijo=prefijo,
            )
        except YaRegistrado:
            f.error = "Ya registrado en la base"
            continue
        f.folio, f.clave = asignacion["folio"], clave

    return filas, []


def generar_excel_salida(filas: list[FilaCarga], ruta: Path | BinaryIO) -> None:
    pd.DataFrame([{
        "CURP": f.curp,
        "Nombre": f.nombre,
        "Idioma": f.idioma,
        "Folio": f.folio or "",
        "Clave": f.clave if f.es_valida else f.error,
    } for f in filas]).to_excel(ruta, index=False)


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
