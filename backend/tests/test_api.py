"""End-to-end tests of the HTTP API against the real test database.

    python -m pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app, crear_token, get_db, leer_token
from tests.test_base_datos import PERFECTAS, _asignacion, cliente, db  # noqa: F401 (fixtures)

CURP = "LOPE020202MGTXXX09"


@pytest.fixture
def api(db):  # noqa: F811
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sesion(api, db):  # noqa: F811
    _, clave = _asignacion(db, curp=CURP)
    r = api.post("/api/sesion", json={"curp": CURP.lower(), "clave": clave})
    assert r.status_code == 200, r.text
    api.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return r.json()


def test_token_roundtrip_and_tampering():
    t = crear_token("abc", ahora=1000)
    assert leer_token(t, ahora=1001) == "abc"
    assert leer_token(t, ahora=10**10) is None  # expired
    assert leer_token(t[:-1] + ("0" if t[-1] != "0" else "1"), ahora=1001) is None
    assert leer_token("basura", ahora=1001) is None


def test_login_incorrecto(api, db):  # noqa: F811
    _asignacion(db, curp=CURP)
    r = api.post("/api/sesion", json={"curp": CURP, "clave": "AAAA-AAAA"})
    assert r.status_code == 401
    assert "incorrectos" in r.json()["detail"]


def test_rutas_protegidas_sin_token(api):
    for metodo, ruta in [("get", "/api/perfil"), ("post", "/api/intento")]:
        assert getattr(api, metodo)(ruta).status_code == 401


def test_flujo_completo(api, sesion):
    perfil = sesion["perfil"]
    assert perfil["nombre"] == "Ana López"
    assert perfil["idioma"] == "Inglés"
    assert perfil["examen"]["preguntas"] == 10

    assert api.get("/api/intento").status_code == 404  # not started yet

    examen = api.post("/api/intento").json()
    assert examen["segundos_restantes"] > 0
    assert all("respuesta" not in p for p in examen["preguntas"])

    for pid, valor in PERFECTAS.items():
        assert api.put(f"/api/intento/respuestas/{pid}", json={"valor": valor}).status_code == 204
    assert api.put("/api/intento/respuestas/q99", json={"valor": 1}).status_code == 422
    assert api.post("/api/intento/incidencias", json={"tipo": "copia"}).status_code == 204

    # Reload resumes the same attempt with saved answers and position.
    assert examen["pregunta_actual"] == 0
    assert api.put("/api/intento/posicion", json={"pregunta": 4}).status_code == 204
    assert api.put("/api/intento/posicion", json={"pregunta": 99}).status_code == 204  # out of range: ignored
    assert api.put("/api/intento/posicion", json={"pregunta": -1}).status_code == 422
    retomado = api.get("/api/intento").json()
    assert retomado["respuestas"]["q01"] == 3
    assert retomado["pregunta_actual"] == 4

    resultado = api.post("/api/intento/finalizar").json()
    assert resultado["aciertos"] == 8
    assert api.post("/api/intento/finalizar").json() == resultado  # idempotent

    assert api.post("/api/intento").status_code == 403  # single attempt
    assert api.put("/api/intento/respuestas/q01", json={"valor": 0}).status_code == 409
