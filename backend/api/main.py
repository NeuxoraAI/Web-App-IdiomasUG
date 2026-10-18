"""HTTP API for applicants (sustentantes). Thin layer over db.operaciones.

Run from backend/:
    uvicorn api.main:app --reload
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from pymongo.database import Database

from db import operaciones as op
from db.conexion import obtener_db

SESION_HORAS = 4

app = FastAPI(title="Idiomas UG - Exámenes de ubicación")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("CORS_ORIGENES", "").split(",") if o],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Business errors -> HTTP status. The message is already user-facing (Spanish).
_ESTADOS = {
    op.AccesoDenegado: 401,
    op.IntentoNoPermitido: 403,
    op.ExamenNoDisponible: 409,
    op.IntentoCerrado: 409,
    op.YaRegistrado: 409,
    op.DatoInvalido: 422,
}


@app.exception_handler(op.ErrorPlataforma)
def _error_plataforma(_: Request, exc: op.ErrorPlataforma) -> JSONResponse:
    estado = next((s for cls, s in _ESTADOS.items() if isinstance(exc, cls)), 400)
    return JSONResponse({"detail": str(exc)}, status_code=estado)


def get_db() -> Database:
    return obtener_db()


# ---------------------------------------------------------------------------
# Session token: base64(payload).hmac — stdlib only.
# ponytail: stateless token can't be revoked before it expires; add a sessions
# collection if the Centro needs to kick someone out mid-exam.
# ---------------------------------------------------------------------------

def _firma(datos: bytes) -> str:
    pepper = os.environ.get("CLAVE_PEPPER")
    if not pepper:
        raise RuntimeError("Falta la variable de entorno CLAVE_PEPPER")
    # "sesion|" prefix keeps these signatures distinct from access-code hashes.
    return hmac.new(pepper.encode(), b"sesion|" + datos, hashlib.sha256).hexdigest()


def crear_token(asignacion_id: str, ahora: float | None = None) -> str:
    exp = int((ahora or time.time()) + SESION_HORAS * 3600)
    datos = base64.urlsafe_b64encode(json.dumps({"a": asignacion_id, "exp": exp}).encode())
    return f"{datos.decode()}.{_firma(datos)}"


def leer_token(token: str, ahora: float | None = None) -> str | None:
    datos, _, firma = token.partition(".")
    if not hmac.compare_digest(firma, _firma(datos.encode())):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(datos))
        return payload["a"] if payload["exp"] > (ahora or time.time()) else None
    except (ValueError, KeyError, TypeError):
        return None


def asignacion_actual(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))],
) -> str:
    asignacion_id = leer_token(cred.credentials) if cred else None
    if asignacion_id is None:
        raise HTTPException(401, "Sesión inválida o expirada; vuelve a iniciar sesión")
    return asignacion_id


DB = Annotated[Database, Depends(get_db)]
Asignacion = Annotated[str, Depends(asignacion_actual)]


def _intento_id(db: Database, asignacion_id: str) -> Any:
    intento = db.intentos.find_one({"asignacion_id": op._id(asignacion_id)}, {"_id": 1})
    if intento is None:
        raise HTTPException(404, "Aún no has iniciado tu examen")
    return intento["_id"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class Login(BaseModel):
    curp: str = Field(max_length=18)
    clave: str = Field(max_length=20)


class Respuesta(BaseModel):
    valor: Any = None


class Incidencia(BaseModel):
    tipo: str = Field(max_length=40)


@app.get("/api/salud")
def salud(db: DB) -> dict:
    db.client.admin.command("ping")
    return {"ok": True}


@app.post("/api/sesion")
def iniciar_sesion(body: Login, db: DB) -> dict:
    asignacion = op.autenticar(db, body.curp, body.clave)
    asignacion_id = str(asignacion["_id"])
    return {"token": crear_token(asignacion_id), "perfil": perfil(db, asignacion_id)}


@app.get("/api/perfil")
def perfil(db: DB, asignacion_id: Asignacion) -> dict:
    a = db.asignaciones.find_one({"_id": op._id(asignacion_id)})
    if a is None:
        raise HTTPException(401, "Sesión inválida o expirada; vuelve a iniciar sesión")
    idioma = db.idiomas.find_one({"_id": a["idioma"]}, {"nombre": 1}) or {}
    examen = db.examenes.find_one(
        {"convocatoria": a["convocatoria"], "idioma": a["idioma"], "estado": "publicado"},
        {"titulo": 1, "duracion_min": 1, "disponible_hasta": 1, "preguntas.id": 1},
    )
    return {
        "nombre": a["nombre"],
        "correo": a.get("correo"),
        "folio": a["folio"],
        "convocatoria": a["convocatoria"],
        "idioma": idioma.get("nombre", a["idioma"]),
        "estado": a["estado"],
        "examen": examen and {
            "titulo": examen["titulo"],
            "duracion_min": examen["duracion_min"],
            "preguntas": len(examen["preguntas"]),
            "disponible_hasta": examen.get("disponible_hasta"),
        },
    }


@app.post("/api/intento")
def iniciar_intento(db: DB, asignacion_id: Asignacion) -> dict:
    intento = op.iniciar_intento(db, asignacion_id)
    return op.examen_para_sustentante(db, intento["_id"])


@app.get("/api/intento")
def ver_intento(db: DB, asignacion_id: Asignacion) -> dict:
    return op.examen_para_sustentante(db, _intento_id(db, asignacion_id))


@app.put("/api/intento/respuestas/{pregunta_id}", status_code=204)
def guardar_respuesta(pregunta_id: str, body: Respuesta, db: DB, asignacion_id: Asignacion) -> None:
    op.guardar_respuesta(db, _intento_id(db, asignacion_id), pregunta_id, body.valor)


@app.post("/api/intento/incidencias", status_code=204)
def registrar_incidencia(body: Incidencia, db: DB, asignacion_id: Asignacion) -> None:
    op.registrar_incidencia(db, _intento_id(db, asignacion_id), body.tipo)


@app.post("/api/intento/finalizar")
def finalizar(db: DB, asignacion_id: Asignacion) -> dict:
    return op.finalizar_intento(db, _intento_id(db, asignacion_id))["resultado"]
