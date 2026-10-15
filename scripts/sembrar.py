"""Prepara la base de datos: colecciones, validadores, índices y datos iniciales.

Carga el catálogo de idiomas (datos/idiomas.json) y todos los exámenes de
datos/examenes/*.json. Se puede ejecutar cuantas veces se quiera.

Uso (desde la raíz del repositorio):
    python scripts/sembrar.py
    python scripts/sembrar.py --publicar EXAUBI-2026B-fr-v1
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from db.conexion import obtener_db, verificar_conexion  # noqa: E402
from db.crear_base_datos import crear  # noqa: E402
from db.operaciones import ErrorPlataforma, cargar_examen, publicar_examen  # noqa: E402

DATOS = RAIZ / "datos"


def sembrar(db, publicar: list[str] | None = None, verbose: bool = True) -> None:
    log = print if verbose else (lambda *a, **k: None)

    log("\n1) Colecciones, validadores e índices")
    crear(db, verbose=verbose)

    log("\n2) Catálogo de idiomas")
    for idioma in json.loads((DATOS / "idiomas.json").read_text(encoding="utf-8")):
        db.idiomas.replace_one({"_id": idioma["_id"]}, idioma, upsert=True)
        log(f"  ✓ {idioma['_id']}  {idioma['nombre']:<10} {'activo' if idioma['activo'] else 'inactivo'}")

    log("\n3) Exámenes")
    for ruta in sorted((DATOS / "examenes").glob("*.json")):
        examen = json.loads(ruta.read_text(encoding="utf-8"))
        try:
            accion = cargar_examen(db, examen)
            log(f"  ✓ {examen['_id']:<22} {accion} ({len(examen['preguntas'])} preguntas, {examen['estado']})")
        except ErrorPlataforma as exc:
            log(f"  ⚠ {examen['_id']:<22} sin cambios: {exc}")

    for examen_id in publicar or []:
        publicar_examen(db, examen_id)
        log(f"  ✓ {examen_id} publicado")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--publicar", nargs="*", default=[], metavar="EXAMEN_ID",
                        help="Exámenes a publicar después de cargarlos")
    args = parser.parse_args(argv)

    db = obtener_db()
    verificar_conexion(db)
    print(f"Base de datos: {db.name}")
    try:
        sembrar(db, publicar=args.publicar)
    except ErrorPlataforma as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        return 1
    print("\nListo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
