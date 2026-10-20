"""Operaciones de la plataforma sobre MongoDB.

Cada función corresponde a un paso real del sustentante o del Centro. El
backend (FastAPI, Flask, etc.) solo tiene que llamarlas desde sus rutas:

    Centro      registrar_asignacion · regenerar_clave · cargar_examen ·
                publicar_examen · resumen_convocatoria · cerrar_intentos_vencidos
    Sustentante autenticar → iniciar_intento → examen_para_sustentante →
                guardar_respuesta (×N) → finalizar_intento

Ideas clave de diseño (ver README):
  * Cada escritura toca UN documento, y en MongoDB la escritura sobre un solo
    documento es atómica. Por eso no hacen falta transacciones.
  * Las reglas importantes ("un solo intento", "sin duplicados") las hace
    cumplir el servidor con índices únicos, no solo el código.
  * El tiempo del examen lo controla el servidor (campo expira_en).
  * Redis (db/cache.py) guarda copias para leer rápido: siempre se escribe
    primero en MongoDB y después en la caché (write-through).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from db import cache
from db.calificacion import calificar

# Margen para respuestas que salen del navegador justo antes de que acabe el tiempo.
GRACIA_SEGUNDOS = 15
MAX_INCIDENCIAS = 100
_PREGUNTA_ID = re.compile(r"^q\d{2,3}$")


# ---------------------------------------------------------------------------
# Errores que el backend puede traducir a mensajes para el usuario
# ---------------------------------------------------------------------------

class ErrorPlataforma(Exception):
    """Error de negocio con mensaje apto para mostrarse al usuario."""


class YaRegistrado(ErrorPlataforma):
    pass


class AccesoDenegado(ErrorPlataforma):
    pass


class ExamenNoDisponible(ErrorPlataforma):
    pass


class IntentoNoPermitido(ErrorPlataforma):
    pass


class IntentoCerrado(ErrorPlataforma):
    pass


class DatoInvalido(ErrorPlataforma):
    pass


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def ahora_utc() -> datetime:
    # MongoDB guarda milisegundos; truncamos para que lo leído sea igual a lo escrito.
    t = datetime.now(timezone.utc)
    return t.replace(microsecond=t.microsecond // 1000 * 1000)


def _id(valor: Any) -> ObjectId:
    try:
        return valor if isinstance(valor, ObjectId) else ObjectId(str(valor))
    except Exception as exc:  # noqa: BLE001
        raise DatoInvalido("Identificador inválido") from exc


def normalizar_clave(clave: str) -> str:
    """'k7xm p29q', 'K7XM-P29Q' y 'K7XMP29Q' se tratan como la misma clave."""
    return re.sub(r"[^A-Z0-9]", "", str(clave or "").upper())


def hash_clave(clave: str) -> str:
    """HMAC-SHA256 de la clave con un secreto del servidor (CLAVE_PEPPER).

    La base nunca guarda la clave en texto plano: si alguien obtiene una copia
    de la base, no puede usar las claves para entrar a exámenes ajenos.
    """
    pepper = os.environ.get("CLAVE_PEPPER")
    if not pepper:
        raise RuntimeError(
            "Falta la variable de entorno CLAVE_PEPPER (ver .env.example). "
            "Debe ser la misma en todos los servidores y no cambiar durante la convocatoria."
        )
    return hmac.new(pepper.encode(), normalizar_clave(clave).encode(), hashlib.sha256).hexdigest()


def siguiente_folio(db: Database, convocatoria: str, prefijo: str = "EXAUBI") -> str:
    """Folio consecutivo por convocatoria: EXAUBI-2026B-0001, -0002, …

    find_one_and_update con $inc es atómico: dos cargas simultáneas nunca
    reciben el mismo número.
    """
    doc = db.contadores.find_one_and_update(
        {"_id": f"folio-{convocatoria}"},
        {"$inc": {"valor": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"{prefijo}-{convocatoria}-{int(doc['valor']):04d}"


# ---------------------------------------------------------------------------
# Centro: catálogo y exámenes
# ---------------------------------------------------------------------------

def idiomas_activos(db: Database) -> dict[str, str]:
    """{nombre: código} de los idiomas que aceptan solicitantes, p. ej. {'Francés': 'fr'}."""
    return {d["nombre"]: d["_id"] for d in db.idiomas.find({"activo": True})}


def cargar_examen(db: Database, examen: dict, ahora: datetime | None = None) -> str:
    """Inserta o reemplaza un examen (por su _id).

    Si ya hay intentos que usan ese examen, NO se reemplaza: cambiar preguntas
    o respuestas a mitad de convocatoria alteraría calificaciones. En ese caso
    hay que crear una versión nueva (v2).
    """
    ahora = ahora or ahora_utc()
    examen = dict(examen)
    if isinstance(examen.get("disponible_hasta"), str):
        examen["disponible_hasta"] = datetime.fromisoformat(examen["disponible_hasta"])

    if db.intentos.count_documents({"examen_id": examen["_id"]}, limit=1):
        raise ErrorPlataforma(
            f"El examen {examen['_id']} ya tiene intentos; crea una versión nueva en lugar de modificarlo."
        )

    previo = db.examenes.find_one({"_id": examen["_id"]}, {"creado_en": 1})
    examen["creado_en"] = previo["creado_en"] if previo else ahora
    examen["actualizado_en"] = ahora
    db.examenes.replace_one({"_id": examen["_id"]}, examen, upsert=True)
    return "actualizado" if previo else "creado"


def publicar_examen(db: Database, examen_id: str) -> None:
    """Publica un examen. El índice parcial impide tener dos publicados a la vez."""
    try:
        r = db.examenes.update_one({"_id": examen_id}, {"$set": {"estado": "publicado"}})
    except DuplicateKeyError as exc:
        raise ErrorPlataforma(
            "Ya hay otro examen publicado para ese idioma y convocatoria; archívalo primero."
        ) from exc
    if r.matched_count == 0:
        raise ErrorPlataforma(f"No existe el examen {examen_id}")


# ---------------------------------------------------------------------------
# Centro: registro de sustentantes y claves de acceso
# ---------------------------------------------------------------------------

def registrar_asignacion(
    db: Database,
    *,
    curp: str,
    nombre: str,
    idioma: str,
    convocatoria: str,
    correo: str | None = None,
    prefijo: str = "EXAUBI",
    ahora: datetime | None = None,
) -> tuple[dict, str]:
    """Registra que `curp` presentará `idioma` en `convocatoria`.

    Devuelve (asignación, clave_en_texto_plano). La clave en texto plano solo
    existe en este momento: se entrega en el Excel de salida y no se guarda.
    Los datos deben llegar ya validados (CURP con formato correcto, idioma
    activo); de eso se encarga scripts/cargar_solicitantes_db.py.
    """
    from scripts.cargar_solicitantes import generar_clave  # reutiliza el formato XXXX-XXXX

    ahora = ahora or ahora_utc()

    if db.asignaciones.find_one({"curp": curp, "convocatoria": convocatoria, "idioma": idioma},
                                {"_id": 1}):
        raise YaRegistrado("Ya registrado en la base para este idioma y convocatoria")

    # 1) La persona: se crea si no existe; si existe se actualizan sus datos (upsert).
    cambios: dict[str, Any] = {"nombre": nombre, "actualizado_en": ahora}
    if correo:
        cambios["correo"] = correo
    sustentante = db.sustentantes.find_one_and_update(
        {"curp": curp},
        {"$set": cambios, "$setOnInsert": {"creado_en": ahora}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    # 2) La asignación, con folio consecutivo y clave única.
    folio = siguiente_folio(db, convocatoria, prefijo)
    for _ in range(5):
        clave = generar_clave()
        asignacion = {
            "sustentante_id": sustentante["_id"],
            "curp": curp,
            "nombre": nombre,
            "convocatoria": convocatoria,
            "idioma": idioma,
            "folio": folio,
            "clave_hash": hash_clave(clave),
            "estado": "pendiente",
            "creada_en": ahora,
        }
        if correo:
            asignacion["correo"] = correo
        try:
            db.asignaciones.insert_one(asignacion)
            return asignacion, clave
        except DuplicateKeyError as exc:
            if "clave_hash" in (exc.details or {}).get("keyPattern", {}):
                continue  # coincidencia de clave (rarísimo): se genera otra
            raise YaRegistrado("Ya registrado en la base para este idioma y convocatoria") from exc
    raise RuntimeError("No se pudo generar una clave única tras varios intentos")


def regenerar_clave(db: Database, asignacion_id: Any) -> str:
    """Nueva clave para quien perdió la suya (solo si aún no inicia el examen)."""
    from scripts.cargar_solicitantes import generar_clave

    for _ in range(5):
        clave = generar_clave()
        try:
            r = db.asignaciones.update_one(
                {"_id": _id(asignacion_id), "estado": "pendiente"},
                {"$set": {"clave_hash": hash_clave(clave)}},
            )
        except DuplicateKeyError:
            continue
        if r.matched_count == 0:
            raise ErrorPlataforma("Solo se puede regenerar la clave de un examen no iniciado")
        return clave
    raise RuntimeError("No se pudo generar una clave única tras varios intentos")


# ---------------------------------------------------------------------------
# Sustentante: acceso y examen
# ---------------------------------------------------------------------------

def autenticar(db: Database, curp: str, clave: str) -> dict:
    """Pantalla de login: CURP + código de acceso → asignación."""
    curp = str(curp or "").strip().upper()
    asignacion = db.asignaciones.find_one({"curp": curp, "clave_hash": hash_clave(clave)})
    if asignacion is None:
        raise AccesoDenegado("CURP o código de acceso incorrectos")
    if asignacion["estado"] == "finalizado":
        raise AccesoDenegado("Este código ya se utilizó: el examen permite un solo intento")
    if asignacion["estado"] == "cancelado":
        raise AccesoDenegado("Este código fue cancelado; comunícate con el Centro")
    return asignacion


def iniciar_intento(db: Database, asignacion_id: Any, ahora: datetime | None = None) -> dict:
    """Botón "Iniciar examen". Arranca el cronómetro en el servidor.

    Si la persona ya tenía un intento en curso (se fue el internet, recargó la
    página) se le devuelve el mismo, con el tiempo que le queda: el
    cronómetro no se pausa.
    """
    ahora = ahora or ahora_utc()
    asignacion_id = _id(asignacion_id)
    asignacion = db.asignaciones.find_one({"_id": asignacion_id})
    if asignacion is None:
        raise ErrorPlataforma("Asignación inexistente")

    previo = db.intentos.find_one({"asignacion_id": asignacion_id})
    if previo is not None:
        if previo["estado"] == "en_curso" and previo["expira_en"] > ahora:
            return previo
        if previo["estado"] == "en_curso":
            finalizar_intento(db, previo["_id"], ahora=ahora)
        raise IntentoNoPermitido("Ya utilizaste tu único intento")

    if asignacion["estado"] != "pendiente":
        raise IntentoNoPermitido("Este examen ya no está disponible")

    examen = db.examenes.find_one(
        {"convocatoria": asignacion["convocatoria"], "idioma": asignacion["idioma"],
         "estado": "publicado"},
        {"duracion_min": 1, "disponible_hasta": 1, "preguntas.id": 1},
    )
    if examen is None:
        raise ExamenNoDisponible("Tu examen todavía no está disponible")
    if examen.get("disponible_hasta") and ahora > examen["disponible_hasta"]:
        raise ExamenNoDisponible("La fecha límite para presentar este examen ya pasó")

    intento = {
        "asignacion_id": asignacion_id,
        "examen_id": examen["_id"],
        # Orden en que se presentan las preguntas (permite barajarlas en el futuro)
        "preguntas_ids": [p["id"] for p in examen["preguntas"]],
        "estado": "en_curso",
        "iniciado_en": ahora,
        "expira_en": ahora + timedelta(minutes=examen["duracion_min"]),
        "respuestas": {},
        "incidencias": [],
    }
    try:
        db.intentos.insert_one(intento)
    except DuplicateKeyError:
        # Dos pestañas pulsaron "Iniciar" a la vez: el índice único dejó pasar solo una.
        return db.intentos.find_one({"asignacion_id": asignacion_id})

    db.asignaciones.update_one(
        {"_id": asignacion_id, "estado": "pendiente"},
        {"$set": {"estado": "en_curso", "iniciada_en": ahora}},
    )
    cache.borrar(db, "perfil", asignacion_id)
    return intento


def examen_para_sustentante(db: Database, intento_id: Any, ahora: datetime | None = None) -> dict:
    """Lo que el navegador necesita para mostrar el examen, SIN respuestas correctas.

    Se lee de Redis; si no está ahí, de MongoDB, y se deja en la caché.
    """
    ahora = ahora or ahora_utc()
    intento = cache.obtener_intento(db, intento_id)
    if intento is not None:
        intento["expira_en"] = datetime.fromisoformat(intento["expira_en"])
    else:
        doc = db.intentos.find_one({"_id": _id(intento_id)})
        if doc is None or doc["estado"] != "en_curso":
            raise IntentoCerrado("Este examen ya terminó")
        intento = {
            "examen_id": doc["examen_id"],
            "preguntas_ids": doc["preguntas_ids"],
            "expira_en": doc["expira_en"],
            "pregunta_actual": doc.get("pregunta_actual", 0),
            "respuestas": {pid: r["valor"] for pid, r in doc["respuestas"].items()},
        }
        meta = {k: intento[k] for k in ("examen_id", "preguntas_ids")}
        meta["expira_en"] = doc["expira_en"].isoformat()
        cache.llenar_intento(db, intento_id, meta, intento["respuestas"], intento["pregunta_actual"])

    examen = cache.obtener(db, "examen", intento["examen_id"])
    if examen is None:
        # Proyección: excluye el campo `respuesta` de cada pregunta embebida.
        doc = db.examenes.find_one({"_id": intento["examen_id"]}, {"preguntas.respuesta": 0})
        examen = {k: doc[k] for k in ("titulo", "partes", "preguntas")}
        cache.guardar(db, examen, cache.TTL_EXAMEN, "examen", intento["examen_id"])

    orden = {pid: i for i, pid in enumerate(intento["preguntas_ids"])}
    preguntas = sorted(examen["preguntas"], key=lambda p: orden.get(p["id"], len(orden)))

    return {
        "intento_id": str(intento_id),
        "titulo": examen["titulo"],
        "partes": examen["partes"],
        "preguntas": preguntas,
        "segundos_restantes": max(0, int((intento["expira_en"] - ahora).total_seconds())),
        "respuestas": intento["respuestas"],
        "pregunta_actual": intento["pregunta_actual"],
    }


def _validar_valor(valor: Any) -> None:
    """Acota lo que el navegador puede guardar (evita documentos gigantes o raros)."""
    if valor is None or (isinstance(valor, int) and not isinstance(valor, bool)):
        return
    if isinstance(valor, str):
        if len(valor) > 5000:
            raise DatoInvalido("Respuesta demasiado larga")
        return
    if isinstance(valor, list) and len(valor) <= 30 and all(
        v is None or (isinstance(v, int) and not isinstance(v, bool))
        or (isinstance(v, str) and len(v) <= 200)
        for v in valor
    ):
        return
    raise DatoInvalido("Formato de respuesta no válido")


def guardar_respuesta(
    db: Database, intento_id: Any, pregunta_id: str, valor: Any, ahora: datetime | None = None
) -> None:
    """Guarda (o cambia) la respuesta de una pregunta. Se llama en cada cambio.

    Una sola operación atómica comprueba TODO a la vez: que el intento siga
    en curso, que no se haya acabado el tiempo y que la pregunta pertenezca a
    este examen. Si algo falla, no se escribe nada.
    """
    ahora = ahora or ahora_utc()
    if not isinstance(pregunta_id, str) or not _PREGUNTA_ID.match(pregunta_id):
        # Importante: pregunta_id se usa como nombre de campo; nunca aceptar
        # cosas como "q01.x" o "$set" que vienen del navegador.
        raise DatoInvalido("Pregunta inválida")
    _validar_valor(valor)

    r = db.intentos.update_one(
        {
            "_id": _id(intento_id),
            "estado": "en_curso",
            "expira_en": {"$gt": ahora - timedelta(seconds=GRACIA_SEGUNDOS)},
            "preguntas_ids": pregunta_id,
        },
        {"$set": {f"respuestas.{pregunta_id}": {"valor": valor, "en": ahora}}},
    )
    if r.matched_count == 0:
        intento = db.intentos.find_one({"_id": _id(intento_id)}, {"estado": 1, "preguntas_ids": 1})
        if intento is None:
            raise DatoInvalido("Intento inexistente")
        if pregunta_id not in intento["preguntas_ids"]:
            raise DatoInvalido("La pregunta no pertenece a este examen")
        raise IntentoCerrado("El tiempo del examen terminó; tu examen ya fue enviado")
    cache.escribir_intento(db, intento_id, f"r:{pregunta_id}", valor)


def guardar_posicion(db: Database, intento_id: Any, indice: int) -> None:
    """Recuerda en qué pregunta va la persona, para retomar ahí si se apaga el
    equipo o entra desde otro. Mejor esfuerzo: si el intento ya cerró o el
    índice no existe, no se escribe nada."""
    r = db.intentos.update_one(
        {"_id": _id(intento_id), "estado": "en_curso", f"preguntas_ids.{int(indice)}": {"$exists": True}},
        {"$set": {"pregunta_actual": int(indice)}},
    )
    if r.matched_count:
        cache.escribir_intento(db, intento_id, "pos", int(indice))


def registrar_incidencia(db: Database, intento_id: Any, tipo: str,
                         ahora: datetime | None = None) -> None:
    """Registra eventos como 'copia' (el guardia anti-IA) o 'salio_de_pestana'.

    $slice mantiene solo las últimas MAX_INCIDENCIAS: un arreglo dentro de un
    documento nunca debe crecer sin límite.
    """
    ahora = ahora or ahora_utc()
    db.intentos.update_one(
        {"_id": _id(intento_id), "estado": "en_curso"},
        {"$push": {"incidencias": {"$each": [{"tipo": str(tipo)[:40], "en": ahora}],
                                   "$slice": -MAX_INCIDENCIAS}}},
    )


def finalizar_intento(db: Database, intento_id: Any, ahora: datetime | None = None) -> dict:
    """Botón "Terminar" o fin del cronómetro. Califica y cierra el intento.

    Paso 1 cierra el intento de forma atómica (a partir de aquí ya no se
    aceptan respuestas). Paso 2 califica con las respuestas congeladas.
    Si se llama dos veces, la segunda solo devuelve el resultado ya guardado.
    """
    ahora = ahora or ahora_utc()
    intento_id = _id(intento_id)
    previo = db.intentos.find_one({"_id": intento_id}, {"expira_en": 1})
    if previo is None:
        raise DatoInvalido("Intento inexistente")
    estado_final = "tiempo_agotado" if ahora >= previo["expira_en"] else "enviado"

    intento = db.intentos.find_one_and_update(
        {"_id": intento_id, "estado": "en_curso"},
        {"$set": {"estado": estado_final, "finalizado_en": ahora}},
        return_document=ReturnDocument.AFTER,
    )
    # Ya no se aceptan respuestas: la copia en caché deja de servir.
    # ponytail: una lectura que leyó MongoDB justo antes del cierre puede volver
    # a llenar la caché unos milisegundos después; las escrituras igual fallan
    # en MongoDB (409) y la clave vence sola (TTL_INTENTO).
    cache.borrar(db, "intento", intento_id)
    if intento is None:  # ya estaba cerrado
        intento = db.intentos.find_one({"_id": intento_id})
        if "resultado" in intento:
            return intento

    examen = db.examenes.find_one({"_id": intento["examen_id"]})
    resultado = calificar(examen, {pid: r["valor"] for pid, r in intento["respuestas"].items()})
    fin = min(intento["finalizado_en"], intento["expira_en"])
    resultado["segundos_usados"] = int((fin - intento["iniciado_en"]).total_seconds())

    db.intentos.update_one({"_id": intento_id}, {"$set": {"resultado": resultado}})
    db.asignaciones.update_one(
        {"_id": intento["asignacion_id"]},
        {"$set": {"estado": "finalizado", "finalizada_en": intento["finalizado_en"]}},
    )
    cache.borrar(db, "perfil", intento["asignacion_id"])
    intento["resultado"] = resultado
    return intento


def cerrar_intentos_vencidos(db: Database, ahora: datetime | None = None) -> int:
    """Tarea programada (p. ej. cada minuto): cierra exámenes cuyo tiempo acabó
    aunque el navegador nunca avisó (se cerró la laptop, se fue la luz…)."""
    ahora = ahora or ahora_utc()
    limite = ahora - timedelta(seconds=GRACIA_SEGUNDOS)
    vencidos = db.intentos.find({"estado": "en_curso", "expira_en": {"$lt": limite}}, {"_id": 1})
    n = 0
    for doc in vencidos:
        finalizar_intento(db, doc["_id"], ahora=ahora)
        n += 1
    return n


def datos_certificado(db: Database, asignacion_id: Any) -> dict:
    """Datos para el certificado de nivel. Ejemplo de $lookup (el "JOIN" de MongoDB)."""
    pipeline = [
        {"$match": {"_id": _id(asignacion_id), "estado": "finalizado"}},
        {"$lookup": {"from": "intentos", "localField": "_id",
                     "foreignField": "asignacion_id", "as": "intento"}},
        {"$unwind": "$intento"},
        {"$lookup": {"from": "idiomas", "localField": "idioma",
                     "foreignField": "_id", "as": "idioma_doc"}},
        {"$unwind": "$idioma_doc"},
        {"$project": {
            "_id": 0,
            "nombre": 1,
            "folio": 1,
            "idioma": "$idioma_doc.nombre",
            "mcer": "$intento.resultado.mcer",
            "nivel": "$intento.resultado.nivel",
            "aciertos": "$intento.resultado.aciertos",
            "calificables": "$intento.resultado.calificables",
            "fecha": "$intento.finalizado_en",
        }},
    ]
    docs = list(db.asignaciones.aggregate(pipeline))
    if not docs:
        raise ErrorPlataforma("No hay un examen terminado para esta asignación")
    return docs[0]


def resumen_convocatoria(db: Database, convocatoria: str) -> list[dict]:
    """Reporte para el Centro: por idioma, cuántos se registraron y qué nivel obtuvieron.

    Ejemplo de agregación ($group): el equivalente a GROUP BY en SQL.
    """
    pipeline = [
        {"$match": {"convocatoria": convocatoria}},
        {"$lookup": {"from": "intentos", "localField": "_id",
                     "foreignField": "asignacion_id", "as": "intento"}},
        {"$unwind": {"path": "$intento", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": {"idioma": "$idioma",
                    "nivel": {"$ifNull": ["$intento.resultado.mcer", "sin_presentar"]}},
            "n": {"$sum": 1},
        }},
        {"$group": {
            "_id": "$_id.idioma",
            "registrados": {"$sum": "$n"},
            "niveles": {"$push": {"k": "$_id.nivel", "v": "$n"}},
        }},
        {"$project": {"_id": 0, "idioma": "$_id", "registrados": 1,
                      "niveles": {"$arrayToObject": "$niveles"}}},
        {"$sort": {"idioma": 1}},
    ]
    return list(db.asignaciones.aggregate(pipeline))
