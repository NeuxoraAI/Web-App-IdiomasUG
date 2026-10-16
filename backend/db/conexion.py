"""Conexión a MongoDB.

La dirección del servidor y el nombre de la base se leen de variables de
entorno (o de un archivo .env en backend/ o en la raíz del repositorio):

    MONGODB_URI=mongodb://localhost:27017          # local
    MONGODB_URI=mongodb+srv://usuario:pass@cluster0.xxxxx.mongodb.net   # Atlas
    MONGODB_DB=idiomas_ug
"""

import os

from pymongo import MongoClient
from pymongo.database import Database

try:  # python-dotenv es opcional: si está instalado, carga el archivo .env
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

URI_POR_DEFECTO = "mongodb://localhost:27017"
DB_POR_DEFECTO = "idiomas_ug"

_clientes: dict[str, MongoClient] = {}


def obtener_cliente(uri: str | None = None) -> MongoClient:
    """Devuelve un MongoClient reutilizable (uno por URI).

    MongoClient mantiene su propio pool de conexiones: se crea UNA vez por
    proceso y se reutiliza, no se abre y cierra en cada consulta.
    tz_aware=True hace que las fechas regresen con zona horaria (UTC).
    """
    uri = uri or os.environ.get("MONGODB_URI", URI_POR_DEFECTO)
    if uri not in _clientes:
        _clientes[uri] = MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    return _clientes[uri]


def obtener_db(uri: str | None = None, nombre: str | None = None) -> Database:
    """Devuelve la base de datos de la plataforma."""
    nombre = nombre or os.environ.get("MONGODB_DB", DB_POR_DEFECTO)
    return obtener_cliente(uri)[nombre]


def verificar_conexion(db: Database) -> None:
    """Falla con un mensaje claro si el servidor no responde."""
    import re

    from pymongo.errors import PyMongoError

    try:
        db.client.admin.command("ping")
    except PyMongoError as exc:
        # Nunca imprimir la contraseña de la URI.
        uri = re.sub(r"(//[^:/@]+:)[^@]*@", r"\1***@", os.environ.get("MONGODB_URI", URI_POR_DEFECTO))
        raise SystemExit(
            "✗ No se pudo conectar a MongoDB.\n"
            f"  MONGODB_URI = {uri}\n"
            "  ¿Está encendido el servidor (o tu IP está permitida en Atlas)? "
            "Revisa tu archivo .env.\n"
            f"  Detalle: {str(exc).splitlines()[0][:200]}"
        ) from None
