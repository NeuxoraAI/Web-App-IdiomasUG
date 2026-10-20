"""Redis write-through cache, against a real Redis (skipped if none is reachable).

    REDIS_URL_TEST=redis://localhost:6379/15 python -m pytest tests/test_cache.py -v
"""

import os

import pytest
import redis

from db import cache
from tests.test_api import api, sesion  # noqa: F401 (fixtures)
from tests.test_base_datos import PERFECTAS, cliente, db  # noqa: F401 (fixtures)

URL = os.environ.get("REDIS_URL_TEST", "redis://localhost:6379/15")


@pytest.fixture
def r(monkeypatch):
    cliente_redis = redis.Redis.from_url(URL, decode_responses=True)
    try:
        cliente_redis.ping()
    except redis.RedisError:
        pytest.skip(f"Redis no disponible en {URL}")
    cliente_redis.flushdb()
    monkeypatch.setenv("REDIS_URL", URL)
    yield cliente_redis
    cliente_redis.flushdb()


def _clave_intento(db, examen):  # noqa: F811
    return f"{db.name}:intento:{examen['intento_id']}"


def test_write_through_y_lectura_desde_cache(r, api, sesion, db):  # noqa: F811
    examen = api.post("/api/intento").json()
    clave = _clave_intento(db, examen)
    assert r.hget(clave, "meta")  # first read filled the cache

    assert api.put("/api/intento/respuestas/q01", json={"valor": 3}).status_code == 204
    assert api.put("/api/intento/posicion", json={"pregunta": 2}).status_code == 204
    assert r.hget(clave, "r:q01") == "3" and r.hget(clave, "pos") == "2"

    # MongoDB is written too (write-through), and reads now come from Redis:
    # a change made only in MongoDB is not seen while the cache holds the attempt.
    intento = db.intentos.find_one({}, {"respuestas": 1, "pregunta_actual": 1})
    assert intento["respuestas"]["q01"]["valor"] == 3 and intento["pregunta_actual"] == 2
    db.intentos.update_one({}, {"$set": {"pregunta_actual": 7}})
    assert api.get("/api/intento").json()["pregunta_actual"] == 2


def test_finalizar_borra_la_cache(r, api, sesion, db):  # noqa: F811
    examen = api.post("/api/intento").json()
    for pid, valor in PERFECTAS.items():
        api.put(f"/api/intento/respuestas/{pid}", json={"valor": valor})
    assert api.post("/api/intento/finalizar").json()["aciertos"] == 8

    assert not r.exists(_clave_intento(db, examen))
    assert api.get("/api/intento").status_code == 409
    assert api.get("/api/perfil").json()["estado"] == "finalizado"


def test_sin_redis_sigue_funcionando(monkeypatch, api, sesion):  # noqa: F811
    monkeypatch.setenv("REDIS_URL", "redis://localhost:1/0")  # nothing listens here
    cache._clientes.clear()
    assert api.post("/api/intento").status_code == 200
    assert api.put("/api/intento/respuestas/q01", json={"valor": 3}).status_code == 204
    assert api.get("/api/intento").json()["respuestas"]["q01"] == 3
