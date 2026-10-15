"""Calificación de un intento, del lado del servidor.

Es la misma lógica que hoy vive en js/data/questions.js (isCorrect y
computeResults) de la rama `desing`, trasladada a Python. Debe vivir en el
servidor porque, si las respuestas correctas viajan al navegador, cualquier
sustentante puede verlas con las herramientas de desarrollador.

Forma de `valor` (lo que manda el navegador) según el tipo de pregunta:
    choice/tf/listen/notice → int (índice de la opción elegida)
    select/match            → list[str] (texto elegido en cada hueco/renglón)
    drag/order              → list[int] (índices de las fichas del banco)
    short/essay             → str
"""

import re
from typing import Any

_FIN_PUNTUACION = re.compile(r"[.!?]$")


def _norm(texto: Any) -> str:
    """Igual que `norm` del prototipo: minúsculas, sin espacios ni punto final."""
    return _FIN_PUNTUACION.sub("", str(texto or "").strip().lower())


def _es_entero(x: Any) -> bool:
    # En Python True/False también son int; aquí no los aceptamos como índice.
    return isinstance(x, int) and not isinstance(x, bool)


def _ficha(banco: list[str], indice: Any) -> str | None:
    """Texto de la ficha `indice` del banco, o None si el índice no es válido."""
    if _es_entero(indice) and 0 <= indice < len(banco):
        return banco[indice]
    return None


def es_calificable(pregunta: dict) -> bool:
    return pregunta.get("respuesta") is not None


def es_correcta(pregunta: dict, valor: Any) -> bool:
    """¿La respuesta `valor` es correcta para esta pregunta?"""
    correcta = pregunta.get("respuesta")
    if valor is None or correcta is None:
        return False

    tipo = pregunta["tipo"]

    if tipo in ("choice", "tf", "listen", "notice"):
        return _es_entero(valor) and valor == correcta

    if tipo == "short":
        aceptadas = correcta if isinstance(correcta, list) else [correcta]
        return isinstance(valor, str) and any(_norm(valor) == _norm(a) for a in aceptadas)

    if not isinstance(valor, list):
        return False

    if tipo in ("select", "match"):
        return len(valor) >= len(correcta) and all(valor[i] == v for i, v in enumerate(correcta))

    if tipo == "drag":
        banco = pregunta.get("banco", [])
        return len(valor) >= len(correcta) and all(
            _ficha(banco, valor[i]) == v for i, v in enumerate(correcta)
        )

    if tipo == "order":
        fichas = [_ficha(pregunta.get("banco", []), i) for i in valor]
        return None not in fichas and " ".join(fichas) == correcta

    return False  # essay y cualquier tipo desconocido


def nivel_para(aciertos: int, niveles: list[dict]) -> dict:
    """Nivel MCER más alto cuyo mínimo de aciertos se alcanzó."""
    alcanzados = [n for n in niveles if aciertos >= n["min_aciertos"]]
    return max(alcanzados, key=lambda n: n["min_aciertos"]) if alcanzados else niveles[0]


def calificar(examen: dict, respuestas: dict[str, Any]) -> dict:
    """Calcula el resultado completo de un intento.

    `respuestas` es un dict {id_pregunta: valor}. Devuelve el subdocumento
    `resultado` que se guarda dentro del intento.
    """
    preguntas = examen["preguntas"]
    calificables = [p for p in preguntas if es_calificable(p)]
    correctas = {p["id"] for p in calificables if es_correcta(p, respuestas.get(p["id"]))}

    por_parte = []
    for parte in examen["partes"]:
        de_la_parte = [p for p in calificables if p["parte"] == parte["numero"]]
        ok = sum(1 for p in de_la_parte if p["id"] in correctas)
        total = len(de_la_parte)
        por_parte.append({
            "parte": parte["numero"],
            "nombre": parte["nombre"],
            "aciertos": ok,
            "total": total,
            "porcentaje": round(ok / total * 100) if total else 0,
        })

    nivel = nivel_para(len(correctas), examen["niveles"])

    return {
        "aciertos": len(correctas),
        "calificables": len(calificables),
        "mcer": nivel["mcer"],
        "nivel": nivel["nombre"],
        "por_parte": por_parte,
        # Preguntas que una persona debe revisar (p. ej. el texto breve)
        "pendientes_revision": [
            p["id"] for p in preguntas
            if p["tipo"] == "essay" and isinstance(respuestas.get(p["id"]), str)
            and respuestas[p["id"]].strip()
        ],
    }
