"""End-to-end tests of the HTTP API against the real test database.

    python -m pytest tests/test_api.py -v
"""

import base64
import io

import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.main import app, crear_token, get_db, leer_token, requiere_rol
from db import operaciones as op
from tests.test_base_datos import FIXTURE, PERFECTAS, _asignacion, cliente, db  # noqa: F401 (fixtures)

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


# ---------------------------------------------------------------------------
# Personal (staff)
# ---------------------------------------------------------------------------

def _login_personal(api, correo="ana@ugto.mx", clave="clave-larga-123"):
    return api.post("/api/personal/sesion", json={"correo": correo, "clave": clave})


@pytest.fixture
def personal(api, db):  # noqa: F811
    op.crear_usuario(db, correo="Ana@UGTO.mx", nombre="Ana", rol="profesor", clave="clave-larga-123")
    return db.usuarios.find_one({"correo": "ana@ugto.mx"})


def test_personal_login_ok(api, personal):
    r = _login_personal(api)
    assert r.status_code == 200, r.text
    assert r.json()["usuario"] == {"id": str(personal["_id"]), "correo": "ana@ugto.mx", "nombre": "Ana", "rol": "profesor"}
    yo = api.get("/api/personal/yo", headers={"Authorization": f"Bearer {r.json()['token']}"})
    assert yo.status_code == 200 and "clave_hash" not in yo.json()


def test_personal_clave_incorrecta_o_inactivo(api, db, personal):  # noqa: F811
    assert _login_personal(api, clave="otra-clave-larga").status_code == 401
    assert _login_personal(api, correo="nadie@ugto.mx").status_code == 401
    token = _login_personal(api).json()["token"]
    db.usuarios.update_one({"_id": personal["_id"]}, {"$set": {"activo": False}})
    assert _login_personal(api).status_code == 401
    # an already-issued token stops working as soon as the user is deactivated
    assert api.get("/api/personal/yo", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_tokens_no_intercambiables(api, sesion, personal):
    solicitante = sesion["token"]
    assert api.get("/api/personal/yo", headers={"Authorization": f"Bearer {solicitante}"}).status_code == 401
    token = _login_personal(api).json()["token"]
    assert api.get("/api/perfil", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_requiere_rol():
    guarda = requiere_rol("admin")
    assert guarda({"rol": "admin"}) == {"rol": "admin"}
    with pytest.raises(HTTPException) as e:
        guarda({"rol": "profesor"})
    assert e.value.status_code == 403


# ---------------------------------------------------------------------------
# Panel: exams with grades, applicants and the access-key Excel
# ---------------------------------------------------------------------------

def _bearer(api, correo, clave="clave-larga-123"):
    return {"Authorization": f"Bearer {_login_personal(api, correo, clave).json()['token']}"}


@pytest.fixture
def admin(api, db, personal):  # noqa: F811
    op.crear_usuario(db, correo="jefa@ugto.mx", nombre="Jefa", rol="admin", clave="clave-larga-123")
    return _bearer(api, "jefa@ugto.mx")


@pytest.fixture
def profesor(api, personal):
    return _bearer(api, "ana@ugto.mx")


def _cargar(api, headers, convocatoria="2026b", archivo=FIXTURE):
    return api.post(f"/api/personal/solicitantes/carga?convocatoria={convocatoria}",
                    content=archivo.read_bytes(), headers=headers)


def test_carga_genera_excel_con_claves(api, admin):
    r = _cargar(api, admin)
    assert r.status_code == 200, r.text
    datos = r.json()
    salida = pd.read_excel(io.BytesIO(base64.b64decode(datos["excel"])), dtype=str)
    assert list(salida.columns) == ["CURP", "Nombre", "Idioma", "Folio", "Clave"]
    assert len(salida) == 10
    assert datos["registrados"] + len(datos["errores"]) == 10
    ingles = salida[salida["Idioma"] == "Inglés"]
    assert list(ingles["Clave"])[0] == "CURP inválida"  # rejected rows carry their error
    ingles = ingles[ingles["Folio"].notna()]
    assert len(ingles) == 1 and ingles["Folio"].str.startswith("EXAUBI-2026B-").all()
    # the generated key is the applicant's real access key
    fila = ingles.iloc[0]
    assert api.post("/api/sesion", json={"curp": fila["CURP"], "clave": fila["Clave"]}).status_code == 200
    # the same file again: everything already registered, no new keys
    otra = _cargar(api, admin).json()
    assert otra["registrados"] == 0 and len(otra["errores"]) == 10


def test_carga_archivo_o_convocatoria_invalidos(api, admin, tmp_path):
    basura = tmp_path / "x.xlsx"
    basura.write_bytes(b"no es un excel")
    assert _cargar(api, admin, archivo=basura).status_code == 422
    assert _cargar(api, admin, convocatoria="26B").status_code == 422
    sin_columnas = tmp_path / "y.xlsx"
    pd.DataFrame([{"Nombre": "X"}]).to_excel(sin_columnas, index=False)
    r = _cargar(api, admin, archivo=sin_columnas)
    assert r.status_code == 422 and "Columnas faltantes" in r.json()["detail"]


def test_solicitantes_lista_sin_claves(api, admin):
    _cargar(api, admin)
    r = api.get("/api/personal/solicitantes", headers=admin)
    assert r.status_code == 200
    filas = r.json()
    ingles = [f for f in filas if f["idioma"] == "Inglés"]
    assert len(ingles) == 1 and "clave_hash" not in ingles[0]
    assert set(ingles[0]) == {"folio", "curp", "nombre", "correo", "idioma", "convocatoria", "estado", "creada_en"}


def test_solicitantes_solo_admin(api, profesor):
    assert api.get("/api/personal/solicitantes", headers=profesor).status_code == 403
    assert _cargar(api, profesor).status_code == 403
    assert api.get("/api/personal/solicitantes").status_code == 401


def test_examenes_con_calificaciones(api, sesion, profesor, admin):
    api.post("/api/intento")
    for pid, valor in PERFECTAS.items():
        api.put(f"/api/intento/respuestas/{pid}", json={"valor": valor})
    resultado = api.post("/api/intento/finalizar").json()
    del api.headers["Authorization"]

    for headers in (profesor, admin):
        r = api.get("/api/personal/examenes", headers=headers)
        assert r.status_code == 200, r.text
        [fila] = r.json()
        assert fila["curp"] == CURP and fila["idioma"] == "Inglés" and fila["estado"] == "finalizado"
        assert fila["aciertos"] == resultado["aciertos"] and fila["mcer"] == resultado["mcer"]
    assert api.get("/api/personal/examenes").status_code == 401
