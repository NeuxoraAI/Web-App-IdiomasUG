"""Caché Redis entre las operaciones y MongoDB (write-through).

MongoDB es siempre la fuente de verdad: primero se escribe ahí y después en
Redis. Si Redis no está configurado (REDIS_URL vacío) o no responde, todas
las funciones se comportan como si la caché estuviera vacía y la plataforma
sigue funcionando contra MongoDB, solo más lenta.

Claves (con el nombre de la base como prefijo, para que pruebas, demo y
producción nunca se mezclen):
    {db}:examen:{id}          JSON del examen sin respuestas correctas
    {db}:intento:{id}         hash con el estado vivo del intento
    {db}:intento_de:{asig}    id del intento de una asignación
    {db}:perfil:{asig}        JSON del perfil
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis
from pymongo.database import Database

log = logging.getLogger(__name__)

TTL_EXAMEN = 3600       # el contenido de un examen con intentos ya no cambia
TTL_INTENTO = 6 * 3600  # más que cualquier duración de examen
TTL_PERFIL = 60         # publicar un examen se refleja en a lo más un minuto

_clientes: dict[str, redis.Redis] = {}


def _cliente() -> redis.Redis | None:
    url = os.environ.get("REDIS_URL")
    if not url:
        return None
    if url not in _clientes:
        _clientes[url] = redis.Redis.from_url(
            url, decode_responses=True, socket_timeout=0.5, socket_connect_timeout=0.5
        )
    return _clientes[url]


def _llamar(fn, por_defecto: Any = None) -> Any:
    """Ejecuta fn(cliente); ante cualquier falla de Redis, devuelve por_defecto."""
    r = _cliente()
    if r is None:
        return por_defecto
    try:
        return fn(r)
    except redis.RedisError as exc:
        log.warning("Redis no disponible: %s", exc)
        return por_defecto


def _clave(db: Database, *partes: Any) -> str:
    return ":".join([db.name, *map(str, partes)])


# ---- JSON simple: examen, perfil, intento_de ------------------------------

def obtener(db: Database, *partes: Any) -> Any:
    texto = _llamar(lambda r: r.get(_clave(db, *partes)))
    return json.loads(texto) if texto else None


def guardar(db: Database, valor: Any, ttl: int, *partes: Any) -> None:
    _llamar(lambda r: r.set(_clave(db, *partes), json.dumps(valor, default=str), ex=ttl))


def borrar(db: Database, *partes: Any) -> None:
    _llamar(lambda r: r.delete(_clave(db, *partes)))


# ---- Intento: hash con campos meta, pos y r:{pregunta_id} -----------------
# Las escrituras usan HSET (siempre ganan) y el llenado desde MongoDB usa
# HSETNX (nunca pisa un valor más nuevo). "meta" se escribe al final del
# llenado: si existe, el hash está completo.

def obtener_intento(db: Database, intento_id: Any) -> dict | None:
    datos = _llamar(lambda r: r.hgetall(_clave(db, "intento", intento_id)))
    if not datos or "meta" not in datos:
        return None
    return {
        **json.loads(datos["meta"]),
        "pregunta_actual": int(datos.get("pos", 0)),
        "respuestas": {k[2:]: json.loads(v) for k, v in datos.items() if k.startswith("r:")},
    }


def llenar_intento(db: Database, intento_id: Any, meta: dict, respuestas: dict, pos: int) -> None:
    clave = _clave(db, "intento", intento_id)

    def fn(r: redis.Redis) -> None:
        p = r.pipeline()
        for pid, valor in respuestas.items():
            p.hsetnx(clave, f"r:{pid}", json.dumps(valor))
        p.hsetnx(clave, "pos", pos)
        p.hset(clave, "meta", json.dumps(meta, default=str))
        p.expire(clave, TTL_INTENTO)
        p.execute()

    _llamar(fn)


def escribir_intento(db: Database, intento_id: Any, campo: str, valor: Any) -> None:
    clave = _clave(db, "intento", intento_id)

    def fn(r: redis.Redis) -> None:
        p = r.pipeline()
        p.hset(clave, campo, json.dumps(valor))
        p.expire(clave, TTL_INTENTO)
        p.execute()

    _llamar(fn)
