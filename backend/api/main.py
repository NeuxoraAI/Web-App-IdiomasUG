"""HTTP API for applicants (sustentantes). Thin layer over db.operaciones.

Run from backend/:
    uvicorn api.main:app --reload
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
import time
from datetime import datetime
from typing import Annotated, Any, Literal

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from pymongo.database import Database
from starlette.concurrency import run_in_threadpool

from db import cache
from db import operaciones as op
from db.conexion import obtener_db
from db.carga import generar_excel_salida, procesar

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

def _firma(datos: bytes, prefijo: bytes = b"sesion|") -> str:
    pepper = os.environ.get("CLAVE_PEPPER")
    if not pepper:
        raise RuntimeError("Falta la variable de entorno CLAVE_PEPPER")
    # The prefix keeps applicant ("sesion|") and staff ("personal|") tokens, and
    # access-code hashes, from ever being interchangeable.
    return hmac.new(pepper.encode(), prefijo + datos, hashlib.sha256).hexdigest()


def crear_token(sujeto: str, ahora: float | None = None, *, campo: str = "a", prefijo: bytes = b"sesion|") -> str:
    exp = int((ahora or time.time()) + SESION_HORAS * 3600)
    datos = base64.urlsafe_b64encode(json.dumps({campo: sujeto, "exp": exp}).encode())
    return f"{datos.decode()}.{_firma(datos, prefijo)}"


def leer_token(token: str, ahora: float | None = None, *, campo: str = "a", prefijo: bytes = b"sesion|") -> str | None:
    datos, _, firma = token.partition(".")
    if not hmac.compare_digest(firma, _firma(datos.encode(), prefijo)):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(datos))
        return payload[campo] if payload["exp"] > (ahora or time.time()) else None
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

_BEARER = Depends(HTTPBearer(auto_error=False))


def personal_actual(db: DB, cred: Annotated[HTTPAuthorizationCredentials | None, _BEARER]) -> dict:
    # Re-read on every request so deactivating a user or changing rol applies at once.
    uid = leer_token(cred.credentials, campo="u", prefijo=b"personal|") if cred else None
    usuario = db.usuarios.find_one({"_id": op._id(uid)}) if uid else None
    if usuario is None or not usuario["activo"]:
        raise HTTPException(401, "Sesión inválida o expirada; vuelve a iniciar sesión")
    return usuario


def requiere_rol(*roles: str):
    def dependencia(usuario: Annotated[dict, Depends(personal_actual)]) -> dict:
        if usuario["rol"] not in roles:
            raise HTTPException(403, "No tienes permiso para esta sección")
        return usuario
    return dependencia


def _intento_id(db: Database, asignacion_id: str) -> Any:
    # One attempt per assignment and it never changes, so it caches for good.
    intento_id = cache.obtener(db, "intento_de", asignacion_id)
    if intento_id is not None:
        return op._id(intento_id)
    intento = db.intentos.find_one({"asignacion_id": op._id(asignacion_id)}, {"_id": 1})
    if intento is None:
        raise HTTPException(404, "Aún no has iniciado tu examen")
    cache.guardar(db, str(intento["_id"]), cache.TTL_INTENTO, "intento_de", asignacion_id)
    return intento["_id"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# Response models: the browser's data contract. frontend/src/api/schema.ts is
# generated from them (npm run gen:api). They also act as a whitelist: any
# field not declared here (e.g. a question's `respuesta`) never leaves the API.

TipoPregunta = Literal["choice", "tf", "listen", "notice", "select", "drag", "order", "match", "short", "essay"]
# Stored answer: option index, text, or one entry per gap / row / word.
Valor = int | str | list[int | str | None]


class ExamenResumen(BaseModel):
    titulo: str
    duracion_min: int
    preguntas: int
    disponible_hasta: datetime | None


class Perfil(BaseModel):
    nombre: str
    correo: str | None
    folio: str
    convocatoria: str
    idioma: str
    estado: Literal["pendiente", "en_curso", "finalizado", "cancelado"]
    examen: ExamenResumen | None


class Sesion(BaseModel):
    token: str
    perfil: Perfil


class Media(BaseModel):
    tipo: Literal["audio", "imagen"]
    url: str | None = None


class Hueco(BaseModel):
    hueco: int


class Palabras(BaseModel):
    min: int
    max: int


class Pregunta(BaseModel):
    id: str
    parte: int
    tipo: TipoPregunta
    instruccion: str
    enunciado: str
    opciones: list[str] | None = None
    media: Media | None = None
    segmentos: list[str | Hueco] | None = None
    opciones_hueco: list[list[str]] | None = None
    banco: list[str] | None = None
    izquierdas: list[str] | None = None
    derechas: list[str] | None = None
    palabras: Palabras | None = None


class Parte(BaseModel):
    numero: int
    nombre: str


class Examen(BaseModel):
    intento_id: str
    titulo: str
    partes: list[Parte]
    preguntas: list[Pregunta]
    segundos_restantes: int
    respuestas: dict[str, Valor | None]
    pregunta_actual: int


class ResultadoParte(BaseModel):
    parte: int
    nombre: str
    aciertos: int
    total: int
    porcentaje: int


class Resultado(BaseModel):
    aciertos: int
    calificables: int
    mcer: str
    nivel: str
    por_parte: list[ResultadoParte]
    pendientes_revision: list[str]
    segundos_usados: int


class Login(BaseModel):
    curp: str = Field(max_length=18)
    clave: str = Field(max_length=20)


class LoginPersonal(BaseModel):
    correo: str = Field(max_length=200)
    clave: str = Field(max_length=200)


class Usuario(BaseModel):
    id: str
    correo: str
    nombre: str
    rol: Literal["admin", "profesor"]


class SesionPersonal(BaseModel):
    token: str
    usuario: Usuario


class Respuesta(BaseModel):
    valor: Valor | None = None


class Incidencia(BaseModel):
    tipo: str = Field(max_length=40)


class Posicion(BaseModel):
    pregunta: int = Field(ge=0, le=500)


EstadoAsignacion = Literal["pendiente", "en_curso", "finalizado", "cancelado"]


class ExamenPresentado(BaseModel):
    folio: str
    curp: str
    nombre: str
    idioma: str
    convocatoria: str
    estado: EstadoAsignacion
    aciertos: int | None = None
    calificables: int | None = None
    mcer: str | None = None
    nivel: str | None = None
    iniciado_en: datetime | None = None
    finalizado_en: datetime | None = None


class Solicitante(BaseModel):
    folio: str
    curp: str
    nombre: str
    correo: str | None = None
    idioma: str
    convocatoria: str
    estado: EstadoAsignacion
    creada_en: datetime


class ErrorCarga(BaseModel):
    fila: int
    curp: str
    nombre: str
    idioma: str
    error: str


class NuevaClave(BaseModel):
    clave: str = Field(description="Shown once; the previous key stops working")


class Carga(BaseModel):
    registrados: int
    errores: list[ErrorCarga]
    excel: str = Field(description="Output .xlsx (base64): the only plain-text copy of the access keys")



@app.get("/api/salud")
def salud(db: DB) -> dict:
    db.client.admin.command("ping")
    return {"ok": True}


@app.post("/api/sesion")
def iniciar_sesion(body: Login, db: DB) -> Sesion:
    asignacion = op.autenticar(db, body.curp, body.clave)
    asignacion_id = str(asignacion["_id"])
    return {"token": crear_token(asignacion_id), "perfil": perfil(db, asignacion_id)}


def _usuario(u: dict) -> dict:
    return {"id": str(u["_id"]), "correo": u["correo"], "nombre": u["nombre"], "rol": u["rol"]}


@app.post("/api/personal/sesion")
def iniciar_sesion_personal(body: LoginPersonal, db: DB) -> SesionPersonal:
    u = op.autenticar_personal(db, body.correo, body.clave)
    token = crear_token(str(u["_id"]), campo="u", prefijo=b"personal|")
    return {"token": token, "usuario": _usuario(u)}


@app.get("/api/personal/yo")
def personal_yo(usuario: Annotated[dict, Depends(personal_actual)]) -> Usuario:
    return _usuario(usuario)


@app.get("/api/perfil")
def perfil(db: DB, asignacion_id: Asignacion) -> Perfil:
    if (en_cache := cache.obtener(db, "perfil", asignacion_id)) is not None:
        return en_cache
    a = db.asignaciones.find_one({"_id": op._id(asignacion_id)})
    if a is None:
        raise HTTPException(401, "Sesión inválida o expirada; vuelve a iniciar sesión")
    idioma = db.idiomas.find_one({"_id": a["idioma"]}, {"nombre": 1}) or {}
    examen = db.examenes.find_one(
        {"convocatoria": a["convocatoria"], "idioma": a["idioma"], "estado": "publicado"},
        {"titulo": 1, "duracion_min": 1, "disponible_hasta": 1, "preguntas.id": 1},
    )
    datos = {
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
    cache.guardar(db, datos, cache.TTL_PERFIL, "perfil", asignacion_id)
    return datos


@app.post("/api/intento")
def iniciar_intento(db: DB, asignacion_id: Asignacion) -> Examen:
    intento = op.iniciar_intento(db, asignacion_id)
    return op.examen_para_sustentante(db, intento["_id"])


@app.get("/api/intento")
def ver_intento(db: DB, asignacion_id: Asignacion) -> Examen:
    return op.examen_para_sustentante(db, _intento_id(db, asignacion_id))


@app.put("/api/intento/respuestas/{pregunta_id}", status_code=204)
def guardar_respuesta(pregunta_id: str, body: Respuesta, db: DB, asignacion_id: Asignacion) -> None:
    op.guardar_respuesta(db, _intento_id(db, asignacion_id), pregunta_id, body.valor)


@app.put("/api/intento/posicion", status_code=204)
def guardar_posicion(body: Posicion, db: DB, asignacion_id: Asignacion) -> None:
    op.guardar_posicion(db, _intento_id(db, asignacion_id), body.pregunta)


@app.post("/api/intento/incidencias", status_code=204)
def registrar_incidencia(body: Incidencia, db: DB, asignacion_id: Asignacion) -> None:
    op.registrar_incidencia(db, _intento_id(db, asignacion_id), body.tipo)


@app.post("/api/intento/finalizar")
def finalizar(db: DB, asignacion_id: Asignacion) -> Resultado:
    return op.finalizar_intento(db, _intento_id(db, asignacion_id))["resultado"]


# ---------------------------------------------------------------------------
# Panel del Centro
# ---------------------------------------------------------------------------

Personal = Annotated[dict, Depends(requiere_rol("admin", "profesor"))]
Admin = Annotated[dict, Depends(requiere_rol("admin"))]

MAX_EXCEL = 5 * 1024 * 1024


@app.get("/api/personal/examenes")
def examenes_presentados(db: DB, _: Personal) -> list[ExamenPresentado]:
    return op.examenes_presentados(db)


@app.get("/api/personal/solicitantes")
def solicitantes(db: DB, _: Admin) -> list[Solicitante]:
    return op.listar_solicitantes(db)


@app.post("/api/personal/solicitantes/{folio}/clave")
def regenerar_clave(folio: str, db: DB, _: Admin) -> NuevaClave:
    a = db.asignaciones.find_one({"folio": folio}, {"_id": 1})
    if a is None:
        raise HTTPException(404, "No existe ese folio")
    return {"clave": op.regenerar_clave(db, a["_id"])}


def _cargar_excel(db: Database, datos: bytes, convocatoria: str) -> dict:
    try:
        df = pd.read_excel(io.BytesIO(datos))
    except Exception as exc:  # any parse failure is the uploader's file, not our bug
        raise op.DatoInvalido("El archivo no es un Excel válido (.xlsx)") from exc
    filas, errores = procesar(db, df, convocatoria)
    if errores:
        raise op.DatoInvalido(errores[0])
    salida = io.BytesIO()
    generar_excel_salida(filas, salida)
    return {
        "registrados": sum(f.es_valida for f in filas),
        "errores": [{"fila": f.fila, "curp": f.curp, "nombre": f.nombre, "idioma": f.idioma,
                     "error": f.error} for f in filas if not f.es_valida],
        "excel": base64.b64encode(salida.getvalue()).decode(),
    }


# Raw .xlsx body (Content-Type: application/octet-stream) instead of a multipart
# form, so the API needs no python-multipart.
@app.post("/api/personal/solicitantes/carga")
async def cargar_solicitantes(
    request: Request, db: DB, _: Admin,
    convocatoria: Annotated[str, Query(pattern=r"^\d{4}[A-Za-z]$")],
) -> Carga:
    datos = await request.body()
    if len(datos) > MAX_EXCEL:
        raise HTTPException(413, "El archivo excede 5 MB")
    return await run_in_threadpool(_cargar_excel, db, datos, convocatoria.upper())
