"""Reglas de validación ($jsonSchema) de cada colección.

MongoDB no obliga a que todos los documentos tengan la misma forma, pero SÍ
permite declarar reglas mínimas por colección. Si un documento no las cumple,
el servidor rechaza la escritura (error 121 "Document failed validation").

Así combinamos lo mejor de los dos mundos:
  - Flexibilidad: cada tipo de pregunta guarda solo los campos que necesita.
  - Seguridad: un CURP mal formado o un estado inventado nunca entran a la base.

Nota: se usa bsonType "number" para los enteros porque así aceptan tanto lo que
inserta Python (int) como lo que inserta mongosh/Compass (double).
"""

# ---------------------------------------------------------------------------
# Valores permitidos (catálogos pequeños que no cambian con frecuencia)
# ---------------------------------------------------------------------------

TIPOS_PREGUNTA = [
    "choice",   # Opción múltiple
    "tf",       # Verdadero / Falso
    "listen",   # Comprensión auditiva (audio + opciones)
    "notice",   # Pregunta con imagen (imagen + opciones)
    "select",   # Palabras faltantes (un menú por hueco)
    "drag",     # Arrastrar fichas a los huecos
    "order",    # Traducir ordenando fichas
    "match",    # Relacionar columnas
    "short",    # Respuesta corta escrita
    "essay",    # Texto breve (revisión manual)
]

ESTADOS_EXAMEN = ["borrador", "publicado", "archivado"]
ESTADOS_ASIGNACION = ["pendiente", "en_curso", "finalizado", "cancelado"]
ESTADOS_INTENTO = ["en_curso", "enviado", "tiempo_agotado"]

# Misma estructura que valida scripts/cargar_solicitantes.py (versión compacta).
PATRON_CURP = r"^[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$"
PATRON_PREGUNTA_ID = r"^q\d{2,3}$"
PATRON_CONVOCATORIA = r"^\d{4}[A-Z]$"          # 2026B
PATRON_HASH = r"^[0-9a-f]{64}$"                # HMAC-SHA256 en hexadecimal

_fecha = {"bsonType": "date"}
_fecha_o_nula = {"bsonType": ["date", "null"]}
_texto = {"bsonType": "string", "minLength": 1}


# ---------------------------------------------------------------------------
# idiomas — catálogo de idiomas que ofrece el Centro
# ---------------------------------------------------------------------------
# { _id: "fr", nombre: "Francés", nombre_nativo: "Français", activo: true }

IDIOMAS = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["_id", "nombre", "activo"],
        "properties": {
            "_id": {"bsonType": "string", "pattern": "^[a-z]{2,3}$",
                    "description": "Código ISO 639-1 del idioma (fr, de, ja…)"},
            "nombre": _texto,
            "nombre_nativo": {"bsonType": "string"},
            "activo": {"bsonType": "bool",
                       "description": "Solo los idiomas activos aceptan solicitantes"},
        },
    }
}


# ---------------------------------------------------------------------------
# examenes — un documento por versión de examen, con sus preguntas EMBEBIDAS
# ---------------------------------------------------------------------------

_PREGUNTA = {
    "bsonType": "object",
    "required": ["id", "parte", "tipo", "instruccion", "enunciado"],
    "properties": {
        "id": {"bsonType": "string", "pattern": PATRON_PREGUNTA_ID},
        "parte": {"bsonType": "number", "minimum": 1},
        "tipo": {"enum": TIPOS_PREGUNTA},
        "instruccion": _texto,
        "enunciado": _texto,
        "opciones": {"bsonType": "array", "items": {"bsonType": "string"}},
        "segmentos": {"bsonType": "array"},
        "opciones_hueco": {"bsonType": "array"},
        "banco": {"bsonType": "array", "items": {"bsonType": "string"}},
        "izquierdas": {"bsonType": "array", "items": {"bsonType": "string"}},
        "derechas": {"bsonType": "array", "items": {"bsonType": "string"}},
        "media": {
            "bsonType": "object",
            "required": ["tipo"],
            "properties": {
                "tipo": {"enum": ["audio", "imagen"]},
                "url": {"bsonType": ["string", "null"]},
            },
        },
        # La respuesta correcta cambia de forma según el tipo:
        #   choice/tf/listen/notice → número (índice de la opción)
        #   select/drag/match       → lista de textos (uno por hueco o renglón)
        #   order                   → texto con la oración completa
        #   short                   → lista de respuestas aceptadas
        #   null                    → no se califica automáticamente (essay)
        "respuesta": {"bsonType": ["number", "string", "array", "null"]},
    },
    # Validación polimórfica: cada tipo exige sus propios campos.
    "anyOf": [
        {"properties": {"tipo": {"enum": ["choice", "tf", "listen", "notice"]}},
         "required": ["opciones"]},
        {"properties": {"tipo": {"enum": ["select"]}},
         "required": ["segmentos", "opciones_hueco"]},
        {"properties": {"tipo": {"enum": ["drag"]}},
         "required": ["segmentos", "banco"]},
        {"properties": {"tipo": {"enum": ["order"]}},
         "required": ["banco"]},
        {"properties": {"tipo": {"enum": ["match"]}},
         "required": ["izquierdas", "derechas"]},
        {"properties": {"tipo": {"enum": ["short", "essay"]}}},
    ],
}

EXAMENES = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["_id", "clave", "convocatoria", "idioma", "version", "titulo",
                     "estado", "duracion_min", "partes", "niveles", "preguntas"],
        "properties": {
            "_id": {"bsonType": "string",
                    "description": "Ej. EXAUBI-2026B-en-v1"},
            "clave": _texto,
            "convocatoria": {"bsonType": "string", "pattern": PATRON_CONVOCATORIA},
            "idioma": {"bsonType": "string", "pattern": "^[a-z]{2,3}$"},
            "version": {"bsonType": "number", "minimum": 1},
            "titulo": _texto,
            "estado": {"enum": ESTADOS_EXAMEN},
            "duracion_min": {"bsonType": "number", "minimum": 5, "maximum": 180},
            "disponible_hasta": _fecha_o_nula,
            "partes": {
                "bsonType": "array", "minItems": 1,
                "items": {
                    "bsonType": "object",
                    "required": ["numero", "nombre"],
                    "properties": {"numero": {"bsonType": "number"}, "nombre": _texto},
                },
            },
            "niveles": {
                "bsonType": "array", "minItems": 1,
                "description": "Tabla de corte: aciertos mínimos para cada nivel MCER",
                "items": {
                    "bsonType": "object",
                    "required": ["min_aciertos", "mcer", "nombre"],
                    "properties": {
                        "min_aciertos": {"bsonType": "number", "minimum": 0},
                        "mcer": {"enum": ["A1", "A2", "B1", "B2", "C1", "C2"]},
                        "nombre": _texto,
                    },
                },
            },
            "preguntas": {"bsonType": "array", "minItems": 1, "items": _PREGUNTA},
            "creado_en": _fecha,
            "actualizado_en": _fecha,
        },
    }
}


# ---------------------------------------------------------------------------
# sustentantes — una persona (puede presentar varios idiomas y periodos)
# ---------------------------------------------------------------------------

SUSTENTANTES = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["curp", "nombre", "creado_en"],
        "properties": {
            "curp": {"bsonType": "string", "pattern": PATRON_CURP},
            "nombre": _texto,
            "correo": {"bsonType": "string", "pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$"},
            "creado_en": _fecha,
            "actualizado_en": _fecha,
        },
    }
}


# ---------------------------------------------------------------------------
# asignaciones — "esta persona presenta este idioma en esta convocatoria"
# Aquí vive la clave de acceso (solo su hash) y el folio del certificado.
# ---------------------------------------------------------------------------

ASIGNACIONES = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["sustentante_id", "curp", "nombre", "convocatoria", "idioma",
                     "folio", "clave_hash", "estado", "creada_en"],
        "properties": {
            "sustentante_id": {"bsonType": "objectId"},
            # Copias (desnormalización) para no consultar 'sustentantes' en cada login:
            "curp": {"bsonType": "string", "pattern": PATRON_CURP},
            "nombre": _texto,
            "correo": {"bsonType": "string"},
            "convocatoria": {"bsonType": "string", "pattern": PATRON_CONVOCATORIA},
            "idioma": {"bsonType": "string", "pattern": "^[a-z]{2,3}$"},
            "folio": _texto,
            "clave_hash": {"bsonType": "string", "pattern": PATRON_HASH,
                           "description": "Nunca se guarda la clave en texto plano"},
            "estado": {"enum": ESTADOS_ASIGNACION},
            "creada_en": _fecha,
            "iniciada_en": _fecha,
            "finalizada_en": _fecha,
        },
    }
}


# ---------------------------------------------------------------------------
# intentos — el examen en curso o terminado de una asignación
# ---------------------------------------------------------------------------

INTENTOS = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["asignacion_id", "examen_id", "preguntas_ids", "estado",
                     "iniciado_en", "expira_en", "respuestas"],
        "properties": {
            "asignacion_id": {"bsonType": "objectId"},
            "examen_id": _texto,
            "preguntas_ids": {"bsonType": "array",
                              "items": {"bsonType": "string", "pattern": PATRON_PREGUNTA_ID}},
            "estado": {"enum": ESTADOS_INTENTO},
            "iniciado_en": _fecha,
            "expira_en": _fecha,
            "finalizado_en": _fecha,
            # Índice de la pregunta en la que va la persona (para retomar)
            "pregunta_actual": {"bsonType": "int", "minimum": 0},
            # Mapa pregunta → respuesta: { "q01": { valor: 3, en: <fecha> }, … }
            "respuestas": {
                "bsonType": "object",
                "patternProperties": {
                    PATRON_PREGUNTA_ID: {
                        "bsonType": "object",
                        "required": ["valor", "en"],
                        "properties": {"en": _fecha},
                    }
                },
                "additionalProperties": False,
            },
            "incidencias": {
                "bsonType": "array",
                "maxItems": 100,
                "items": {
                    "bsonType": "object",
                    "required": ["tipo", "en"],
                    "properties": {"tipo": _texto, "en": _fecha},
                },
            },
            "resultado": {
                "bsonType": "object",
                "required": ["aciertos", "calificables", "mcer", "nivel", "por_parte"],
                "properties": {
                    "aciertos": {"bsonType": "number"},
                    "calificables": {"bsonType": "number"},
                    "mcer": {"bsonType": "string"},
                    "nivel": {"bsonType": "string"},
                    "por_parte": {"bsonType": "array"},
                    "pendientes_revision": {"bsonType": "array"},
                    "segundos_usados": {"bsonType": "number"},
                },
            },
        },
    }
}


# ---------------------------------------------------------------------------
# contadores — números consecutivos (folios de certificado)
# ---------------------------------------------------------------------------
# { _id: "folio-2026B", valor: 37 }

CONTADORES = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["_id", "valor"],
        "properties": {"_id": {"bsonType": "string"}, "valor": {"bsonType": "number"}},
    }
}


# ---------------------------------------------------------------------------
# usuarios — personal del Centro (admin / profesor); clave_hash = scrypt
# ---------------------------------------------------------------------------

USUARIOS = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["correo", "nombre", "rol", "clave_hash", "activo", "creado_en"],
        "properties": {
            "correo": {"bsonType": "string"},
            "nombre": _texto,
            "rol": {"enum": ["admin", "profesor"]},
            "clave_hash": {"bsonType": "string"},
            "activo": {"bsonType": "bool"},
            "creado_en": _fecha,
        },
    }
}


VALIDADORES = {
    "idiomas": IDIOMAS,
    "examenes": EXAMENES,
    "sustentantes": SUSTENTANTES,
    "asignaciones": ASIGNACIONES,
    "intentos": INTENTOS,
    "contadores": CONTADORES,
    "usuarios": USUARIOS,
}
