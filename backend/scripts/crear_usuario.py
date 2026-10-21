"""Crea un usuario del personal (admin o profesor). La contraseña se pide por teclado.

Uso (desde backend/):
    python scripts/crear_usuario.py --correo ana@ugto.mx --nombre "Ana López" --rol admin
"""

import argparse
import getpass
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from db.conexion import obtener_db, verificar_conexion  # noqa: E402
from db.operaciones import ROLES, ErrorPlataforma, crear_usuario  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--correo", required=True)
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--rol", required=True, choices=ROLES)
    args = ap.parse_args()

    clave = getpass.getpass("Contraseña: ")
    if clave != getpass.getpass("Repite la contraseña: "):
        print("✗ Las contraseñas no coinciden")
        return 1

    db = obtener_db()
    verificar_conexion(db)
    try:
        u = crear_usuario(db, correo=args.correo, nombre=args.nombre, rol=args.rol, clave=clave)
    except ErrorPlataforma as exc:
        print(f"✗ {exc}")
        return 1
    print(f"✓ {u['correo']} creado como {u['rol']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
