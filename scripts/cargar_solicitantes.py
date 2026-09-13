"""Carga y valida solicitantes de exámenes de idiomas.

Lee un archivo Excel con datos de solicitantes (CURP, Nombre, Idioma),
valida cada registro, genera claves de acceso únicas por asignación
y produce un Excel de salida con las claves.

Uso:
    python scripts/cargar_solicitantes.py tests/fixtures/alumnos_solicitantes.xlsx
    python scripts/cargar_solicitantes.py input.xlsx --output codigos_acceso.xlsx
"""

import argparse
import re
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd
from enum import Enum

# ---------------------------------------------------------------------------
# CURP validation
# ---------------------------------------------------------------------------

# CURP (Clave Única de Registro de Población) — 18 chars, uppercase A-Z/0-9.
# Structure: 4 letters · 6-digit birthdate · sex (H/M) · 2-letter state code
# (incl. NE = nacido en el extranjero) · 3 consonants · homoclave · check digit.

_CURP_RE = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])"
    r"[HM](AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|"
    r"PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)"
    r"[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$"
)

_CURP_LEN = 18

# Dictionary for the check-digit (dígito verificador) algorithm.
_CURP_DICT = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"


def _curp_digito_verificador(curp: str) -> str:
    """Compute the official CURP check digit from its first 17 characters."""
    suma = sum(_CURP_DICT.index(ch) * (18 - i) for i, ch in enumerate(curp[:17]))
    return str((10 - (suma % 10)) % 10)


def validate_curp_formato(value: str) -> str:
    """Validate and normalize a CURP by FORMAT ONLY (length + structure)."""
    if value is None:
        raise ValueError("CURP es obligatoria")
    curp = value.strip().upper()
    if len(curp) != _CURP_LEN:
        raise ValueError(f"CURP debe tener exactamente {_CURP_LEN} caracteres")
    if not _CURP_RE.match(curp):
        raise ValueError("CURP tiene un formato inválido")
    return curp


def validate_curp(value: str) -> str:
    """Validate and normalize a Mexican CURP (format + check digit).

    Returns the uppercased, trimmed CURP. Raises ValueError on any failure.
    """
    curp = validate_curp_formato(value)
    if _curp_digito_verificador(curp) != curp[17]:
        raise ValueError("CURP inválida: el dígito verificador no coincide")
    return curp


def validar_curp_segura(value) -> bool:
    """Return True if the CURP is valid, False otherwise."""
    try:
        validate_curp(value)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Language validation
# ---------------------------------------------------------------------------

class IdiomasDisponibles(str, Enum):
    FRANCES = "Francés"
    ALEMAN = "Alemán"
    JAPONES = "Japonés"
    ESPANOL = "Español"
    ITALIANO = "Italiano"
    COREANO = "Coreano"
    CHINO = "Chino"


def idioma_es_valido(value: str) -> bool:
    """Return True if the language is one of the enabled options."""
    if value is None:
        return False
    try:
        IdiomasDisponibles(value.strip())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

# Characters allowed in access keys (no ambiguous chars: 0/O, 1/I/L)
_KEY_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_KEY_SEGMENT_LEN = 4
_KEY_SEPARATOR = "-"


def generar_clave(segmentos: int = 2) -> str:
    """Generate a cryptographically random access key.

    Default format: XXXX-XXXX (e.g. K7XM-P29Q).
    """
    parts = [
        "".join(secrets.choice(_KEY_CHARS) for _ in range(_KEY_SEGMENT_LEN))
        for _ in range(segmentos)
    ]
    return _KEY_SEPARATOR.join(parts)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FilaResultado:
    """Result for a single row — either a valid clave or an error message."""
    curp: str
    nombre: str
    idioma: str
    clave: Optional[str] = None
    error: Optional[str] = None

    @property
    def es_valida(self) -> bool:
        return self.error is None


@dataclass
class ResultadoCarga:
    """Outcome of processing the input file."""
    filas: list[FilaResultado] = field(default_factory=list)
    errores_globales: list[str] = field(default_factory=list)

    @property
    def registros_validos(self) -> list[FilaResultado]:
        return [f for f in self.filas if f.es_valida]

    @property
    def registros_con_error(self) -> list[FilaResultado]:
        return [f for f in self.filas if not f.es_valida]


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

_COLUMNAS_REQUERIDAS = {"CURP", "Nombre", "Idioma"}


def procesar_solicitantes(df: pd.DataFrame) -> ResultadoCarga:
    """Validate every row and generate access keys.

    Returns a ResultadoCarga with ALL rows — valid ones get a clave,
    invalid ones get an error message.
    """
    resultado = ResultadoCarga()

    # --- Check required columns ---
    columnas_faltantes = _COLUMNAS_REQUERIDAS - set(df.columns)
    if columnas_faltantes:
        resultado.errores_globales.append(
            f"Columnas faltantes en el archivo: {', '.join(sorted(columnas_faltantes))}"
        )
        return resultado

    vistos: set[tuple[str, str]] = set()  # (CURP, Idioma) for duplicate detection

    for idx, row in df.iterrows():
        curp_raw = row.get("CURP")
        nombre_raw = row.get("Nombre")
        idioma_raw = row.get("Idioma")

        curp_str = str(curp_raw).strip() if not pd.isna(curp_raw) else ""
        nombre_str = str(nombre_raw).strip() if not pd.isna(nombre_raw) else ""
        idioma_str = str(idioma_raw).strip() if not pd.isna(idioma_raw) else ""

        # --- Incomplete records ---
        if not curp_str:
            resultado.filas.append(FilaResultado(
                curp=curp_str, nombre=nombre_str, idioma=idioma_str, error="CURP vacía"
            ))
            continue
        if not nombre_str:
            resultado.filas.append(FilaResultado(
                curp=curp_str, nombre=nombre_str, idioma=idioma_str, error="Nombre vacío"
            ))
            continue
        if not idioma_str:
            resultado.filas.append(FilaResultado(
                curp=curp_str, nombre=nombre_str, idioma=idioma_str, error="Idioma vacío"
            ))
            continue

        # --- CURP validation ---
        try:
            curp = validate_curp(curp_str)
        except ValueError:
            resultado.filas.append(FilaResultado(
                curp=curp_str, nombre=nombre_str, idioma=idioma_str, error="CURP inválida"
            ))
            continue

        # --- Language validation ---
        if not idioma_es_valido(idioma_str):
            resultado.filas.append(FilaResultado(
                curp=curp, nombre=nombre_str, idioma=idioma_str,
                error=f"Idioma no válido: '{idioma_str}'"
            ))
            continue

        # --- Duplicate detection (same CURP + same Idioma) ---
        clave_duplicado = (curp, idioma_str)
        if clave_duplicado in vistos:
            resultado.filas.append(FilaResultado(
                curp=curp, nombre=nombre_str, idioma=idioma_str,
                error="Registro duplicado"
            ))
            continue
        vistos.add(clave_duplicado)

        # --- Valid row: generate access key ---
        clave = generar_clave()
        resultado.filas.append(FilaResultado(
            curp=curp, nombre=nombre_str, idioma=idioma_str, clave=clave
        ))

    return resultado


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def generar_excel_salida(resultado: ResultadoCarga, ruta: Path) -> None:
    """Write the output Excel with ALL rows.

    Valid rows get their generated key.
    Invalid rows get the error description in the Clave column.
    """
    rows = []
    for f in resultado.filas:
        rows.append({
            "CURP": f.curp,
            "Nombre": f.nombre,
            "Idioma": f.idioma,
            "Clave": f.clave if f.es_valida else f.error,
        })
    df = pd.DataFrame(rows)
    df.to_excel(ruta, index=False)


def imprimir_resumen(resultado: ResultadoCarga) -> None:
    """Print a human-readable summary to stdout."""
    validos = resultado.registros_validos
    errores = resultado.registros_con_error

    print(f"\n{'='*60}")
    print(f"Registros válidos:  {len(validos)}")
    print(f"Registros con error: {len(errores)}")
    print(f"{'='*60}")

    if resultado.errores_globales:
        print("\n--- Error general ---")
        for e in resultado.errores_globales:
            print(f"  ✗ {e}")

    if errores:
        print("\n--- Errores por fila ---")
        for f in errores:
            print(f"  ✗ {f.curp or '(vacía)'} | {f.nombre or '(vacío)'} | {f.idioma or '(vacío)'} → {f.error}")

    if validos:
        print("\n--- Claves generadas ---")
        for f in validos:
            print(f"  ✓ {f.curp} | {f.nombre} | {f.idioma} → {f.clave}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Carga solicitantes de exámenes de idiomas y genera claves de acceso."
    )
    parser.add_argument(
        "archivo",
        type=Path,
        help="Ruta al archivo Excel de solicitantes (.xlsx)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Ruta del Excel de salida con claves (default: codigos_acceso.xlsx)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.archivo.exists():
        print(f"Error: archivo no encontrado — {args.archivo}", file=sys.stderr)
        return 1

    df = pd.read_excel(args.archivo)
    resultado = procesar_solicitantes(df)
    imprimir_resumen(resultado)

    if resultado.errores_globales:
        print("\n⚠ Error general. No se puede generar el archivo.", file=sys.stderr)
        return 1

    # Always generate the Excel
    ruta_salida = args.output or Path("codigos_acceso.xlsx")
    generar_excel_salida(resultado, ruta_salida)
    print(f"\n✓ Excel con claves generado: {ruta_salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
