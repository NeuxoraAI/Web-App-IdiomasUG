"""Crea (o actualiza) las colecciones, sus validadores y sus índices.

Es seguro ejecutarlo varias veces: si la colección ya existe solo actualiza
su validador, y create_index no duplica índices que ya existen.

Uso (desde la raíz del repositorio):
    python -m db.crear_base_datos
"""

from pymongo import ASCENDING, IndexModel
from pymongo.database import Database

from db.esquemas import VALIDADORES

# ---------------------------------------------------------------------------
# Índices
# ---------------------------------------------------------------------------
# Un índice es como el índice alfabético de un libro: permite encontrar un
# documento sin revisar la colección completa. Los índices ÚNICOS además son
# reglas de negocio que el propio servidor hace cumplir.

INDICES: dict[str, list[IndexModel]] = {
    "idiomas": [
        IndexModel([("nombre", ASCENDING)], unique=True, name="nombre_unico"),
    ],
    "examenes": [
        IndexModel([("convocatoria", ASCENDING), ("idioma", ASCENDING), ("version", ASCENDING)],
                   unique=True, name="convocatoria_idioma_version_unico"),
        # Índice parcial: solo puede haber UN examen publicado por idioma y convocatoria.
        IndexModel([("convocatoria", ASCENDING), ("idioma", ASCENDING)],
                   unique=True, partialFilterExpression={"estado": "publicado"},
                   name="un_publicado_por_idioma"),
    ],
    "sustentantes": [
        IndexModel([("curp", ASCENDING)], unique=True, name="curp_unica"),
    ],
    "asignaciones": [
        # La misma regla que el script de carga: misma CURP + mismo idioma = duplicado
        # (ahora también entre archivos distintos de la misma convocatoria).
        IndexModel([("curp", ASCENDING), ("convocatoria", ASCENDING), ("idioma", ASCENDING)],
                   unique=True, name="curp_convocatoria_idioma_unico"),
        IndexModel([("clave_hash", ASCENDING)], unique=True, name="clave_unica"),
        IndexModel([("folio", ASCENDING)], unique=True, name="folio_unico"),
        IndexModel([("convocatoria", ASCENDING), ("idioma", ASCENDING), ("estado", ASCENDING)],
                   name="listado_por_convocatoria"),
    ],
    "intentos": [
        # "Un solo intento": la base rechaza un segundo intento para la misma asignación.
        IndexModel([("asignacion_id", ASCENDING)], unique=True, name="un_intento_por_asignacion"),
        # Para encontrar rápido los exámenes cuyo tiempo ya terminó.
        IndexModel([("estado", ASCENDING), ("expira_en", ASCENDING)], name="vencimiento"),
    ],
    "contadores": [],
}


def crear(db: Database, verbose: bool = True) -> None:
    """Crea/actualiza todas las colecciones de la plataforma."""
    existentes = set(db.list_collection_names())

    for nombre, validador in VALIDADORES.items():
        if nombre in existentes:
            db.command("collMod", nombre, validator=validador,
                       validationLevel="strict", validationAction="error")
            accion = "actualizada"
        else:
            db.create_collection(nombre, validator=validador,
                                 validationLevel="strict", validationAction="error")
            accion = "creada"

        if INDICES[nombre]:
            db[nombre].create_indexes(INDICES[nombre])

        if verbose:
            n_idx = len(INDICES[nombre])
            print(f"  ✓ {nombre:<13} {accion:<11} ({n_idx} índice{'s' if n_idx != 1 else ''})")


if __name__ == "__main__":
    from db.conexion import obtener_db, verificar_conexion

    base = obtener_db()
    verificar_conexion(base)
    print(f"Base de datos: {base.name}")
    crear(base)
