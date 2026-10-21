"""Carga de solicitantes desde Excel: valida cada renglón, registra los válidos
y arma el Excel de salida con las claves.

Lo usan la API (POST /api/personal/solicitantes/carga) y
scripts/cargar_solicitantes_db.py. El Excel de salida es el ÚNICO lugar donde
quedan las claves en texto plano (la base solo guarda su hash).

Columnas requeridas: CURP, Nombre, Idioma. Opcional: Correo.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd
from pymongo.database import Database
from pymongo.errors import PyMongoError

from db.esquemas import PATRON_CORREO
from db.operaciones import YaRegistrado, idiomas_activos, registrar_asignacion

COLUMNAS_REQUERIDAS = {"CURP", "Nombre", "Idioma"}

# CURP: 4 letras · fecha AAMMDD · sexo (H/M) · entidad (NE = extranjero) ·
# 3 consonantes · homoclave · dígito verificador.
_CURP_RE = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])"
    r"[HM](AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|"
    r"PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)"
    r"[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$"
)
_CURP_DICT = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"


def validar_curp(valor: str) -> str:
    """CURP normalizada (mayúsculas, sin espacios); ValueError si el formato o
    el dígito verificador no coinciden."""
    curp = str(valor or "").strip().upper()
    if not _CURP_RE.match(curp):
        raise ValueError("CURP inválida")
    suma = sum(_CURP_DICT.index(ch) * (18 - i) for i, ch in enumerate(curp[:17]))
    if str((10 - suma % 10) % 10) != curp[17]:
        raise ValueError("CURP inválida: el dígito verificador no coincide")
    return curp


@dataclass
class FilaCarga:
    fila: int                      # número de renglón en Excel (encabezado = 1)
    curp: str
    nombre: str
    idioma: str
    correo: str = ""
    folio: str | None = None
    clave: str | None = None
    error: str | None = None

    @property
    def es_valida(self) -> bool:
        return self.error is None


def _texto(valor) -> str:
    return "" if pd.isna(valor) else str(valor).strip()


def procesar(db: Database, df: pd.DataFrame, convocatoria: str, prefijo: str = "EXAUBI"
             ) -> tuple[list[FilaCarga], list[str]]:
    """Valida cada renglón y registra en la base los válidos."""
    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        return [], [f"Columnas faltantes en el archivo: {', '.join(sorted(faltantes))}"]

    catalogo = idiomas_activos(db)          # {'Francés': 'fr', …}
    if not catalogo:
        return [], ["No hay idiomas activos en la base. ¿Ya ejecutaste scripts/sembrar.py?"]

    filas: list[FilaCarga] = []
    vistos: set[tuple[str, str]] = set()

    for i, row in df.iterrows():
        f = FilaCarga(
            fila=int(i) + 2,
            curp=_texto(row.get("CURP")),
            nombre=_texto(row.get("Nombre")),
            idioma=_texto(row.get("Idioma")),
            correo=_texto(row.get("Correo")) if "Correo" in df.columns else "",
        )
        filas.append(f)

        if not f.curp:
            f.error = "CURP vacía"
            continue
        if not f.nombre:
            f.error = "Nombre vacío"
            continue
        if not f.idioma:
            f.error = "Idioma vacío"
            continue
        try:
            f.curp = validar_curp(f.curp)
        except ValueError:
            f.error = "CURP inválida"
            continue
        if f.correo and not re.match(PATRON_CORREO, f.correo):
            f.error = "Correo inválido"  # el validador de sustentantes lo rechazaría a media carga
            continue
        if f.idioma not in catalogo:
            f.error = f"Idioma no válido: '{f.idioma}'"
            continue
        if (f.curp, f.idioma) in vistos:
            f.error = "Registro duplicado"
            continue
        vistos.add((f.curp, f.idioma))

        try:
            asignacion, clave = registrar_asignacion(
                db, curp=f.curp, nombre=f.nombre, idioma=catalogo[f.idioma],
                convocatoria=convocatoria, correo=f.correo or None, prefijo=prefijo,
            )
        except YaRegistrado:
            f.error = "Ya registrado en la base"
            continue
        except PyMongoError:
            # Un renglón que falla no debe tirar la carga: las claves de los ya
            # registrados solo existen en el Excel de salida.
            f.error = "No se pudo guardar; vuelve a cargar este renglón"
            continue
        f.folio, f.clave = asignacion["folio"], clave

    return filas, []


def generar_excel_salida(filas: list[FilaCarga], ruta: Path | BinaryIO) -> None:
    pd.DataFrame([{
        "CURP": f.curp,
        "Nombre": f.nombre,
        "Idioma": f.idioma,
        "Folio": f.folio or "",
        "Clave": f.clave if f.es_valida else f.error,
    } for f in filas]).to_excel(ruta, index=False)
