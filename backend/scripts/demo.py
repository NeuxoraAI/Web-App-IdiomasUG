"""Recorrido completo de la plataforma sobre una base de DEMOSTRACIÓN.

Crea la base `idiomas_ug_demo` desde cero, carga el Excel de prueba del
repositorio, y simula a un sustentante presentando el examen de inglés del
prototipo. En cada paso imprime cómo quedan los documentos, para que veas
qué guarda la base y cuándo.

Al terminar, abre MongoDB Compass y explora `idiomas_ug_demo`.

Uso (desde la raíz del repositorio):
    python scripts/demo.py
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

os.environ.setdefault("CLAVE_PEPPER", "solo-para-la-demo")

from db import operaciones as op  # noqa: E402
from db.conexion import obtener_db, verificar_conexion  # noqa: E402
from db.carga import procesar  # noqa: E402
from scripts.cargar_solicitantes_db import imprimir_resumen  # noqa: E402
from scripts.sembrar import sembrar  # noqa: E402

DB_DEMO = "idiomas_ug_demo"


def titulo(texto: str) -> None:
    print(f"\n\n{'━' * 70}\n  {texto}\n{'━' * 70}")


def mostrar(doc, etiqueta: str = "") -> None:
    if etiqueta:
        print(f"\n▸ {etiqueta}")
    print(json.dumps(doc, indent=2, ensure_ascii=False, default=str))


def main() -> int:
    db = obtener_db(nombre=DB_DEMO)
    verificar_conexion(db)
    db.client.drop_database(DB_DEMO)

    titulo("1. Crear colecciones e índices, cargar idiomas y examen")
    sembrar(db)
    # Solo en la demo: activamos inglés y publicamos el examen del prototipo.
    db.idiomas.update_one({"_id": "en"}, {"$set": {"activo": True}})
    op.publicar_examen(db, "EXAUBI-2026B-en-v1")
    print("  ✓ (demo) inglés activado y EXAUBI-2026B-en-v1 publicado")

    titulo("2. El Centro carga el Excel de solicitantes")
    df = pd.read_excel(RAIZ / "tests" / "fixtures" / "alumnos_solicitantes.xlsx")
    filas, _ = procesar(db, df, "2026B")
    imprimir_resumen(filas)

    ingles = next(f for f in filas if f.es_valida and f.idioma == "Inglés")
    print(f"\n  Clave entregada a {ingles.nombre} para Inglés: {ingles.clave}")
    mostrar(db.sustentantes.find_one({"curp": ingles.curp}, {"_id": 0}),
            "Documento en `sustentantes` (UNA persona, aunque presenta dos idiomas)")
    mostrar(list(db.asignaciones.find({"curp": ingles.curp}, {"_id": 0, "sustentante_id": 0})),
            "Documentos en `asignaciones` (uno por idioma; la clave solo como hash)")

    titulo("3. Login con CURP + código")
    asignacion = op.autenticar(db, ingles.curp, ingles.clave.lower().replace("-", " "))
    print(f"  ✓ Acceso correcto (aunque se escribió '{ingles.clave.lower().replace('-', ' ')}')")
    try:
        op.autenticar(db, ingles.curp, "AAAA-BBBB")
    except op.AccesoDenegado as exc:
        print(f"  ✗ Con un código equivocado: {exc}")

    titulo("4. Iniciar examen → se crea el intento y arranca el cronómetro")
    intento = op.iniciar_intento(db, asignacion["_id"])
    mostrar({k: v for k, v in intento.items() if k != "_id"}, "Documento nuevo en `intentos`")
    vista = op.examen_para_sustentante(db, intento["_id"])
    print(f"\n  El navegador recibe {len(vista['preguntas'])} preguntas y "
          f"{-(-vista['segundos_restantes'] // 60)} min. ¿Incluye respuestas correctas? "
          f"{'SÍ ✗' if any('respuesta' in p for p in vista['preguntas']) else 'No ✓'}")
    mostrar(vista["preguntas"][6], "Así llega una pregunta tipo 'match' (sin la respuesta)")

    titulo("5. El sustentante responde (cada cambio se guarda al momento)")
    respuestas = {
        "q01": 3,                                    # expensive ✓
        "q02": 1,                                    # False ✓
        "q03": 1,                                    # "in 3 o'clock" ✗
        "q04": ["am", "are"],                        # ✓
        "q05": [0, 1],                               # fichas went, saw ✓
        "q06": [2, 3, 0, 1, 4],                      # I have never been to London ✓
        "q07": ["can be trusted", "gives more than expected", "arrives on time"],  # ✓
        "q08": "Since",                              # ✓ (no distingue mayúsculas)
        "q09": 1,                                    # sin calificar en el prototipo
        "q10": "I would like to visit Kyoto because of its temples and gardens.",
    }
    for pid, valor in respuestas.items():
        op.guardar_respuesta(db, intento["_id"], pid, valor)
    op.registrar_incidencia(db, intento["_id"], "copia")
    print(f"  ✓ {len(respuestas)} respuestas guardadas y 1 incidencia ('copia') registrada")
    try:
        op.guardar_respuesta(db, intento["_id"], "q99", 1)
    except op.DatoInvalido as exc:
        print(f"  ✗ Respuesta a una pregunta que no existe: {exc}")

    titulo("6. Terminar → el servidor califica")
    final = op.finalizar_intento(db, intento["_id"])
    mostrar(final["resultado"], "Subdocumento `resultado` dentro del intento")
    try:
        op.iniciar_intento(db, asignacion["_id"])
    except op.IntentoNoPermitido as exc:
        print(f"\n  ✗ Si intenta entrar de nuevo: {exc}")

    titulo("7. Certificado ($lookup) y reporte del Centro ($group)")
    mostrar(op.datos_certificado(db, asignacion["_id"]), "Datos del certificado")
    mostrar(op.resumen_convocatoria(db, "2026B"), "Resumen de la convocatoria 2026B")

    print(f"\n\nListo. Explora la base '{DB_DEMO}' en MongoDB Compass.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
