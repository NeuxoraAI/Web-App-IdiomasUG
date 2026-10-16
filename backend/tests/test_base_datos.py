"""Pruebas de la capa de base de datos contra un MongoDB REAL.

Usa el servidor de MONGODB_URI (por defecto mongodb://localhost:27017) y una
base temporal que se borra al terminar. Si no hay servidor, se omiten.

    python -m pytest tests/test_base_datos.py -v
"""

import json
import os
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytest
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError, WriteError

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("CLAVE_PEPPER", "pepper-de-pruebas")

from db import operaciones as op  # noqa: E402
from db.calificacion import calificar, es_correcta  # noqa: E402
from db.conexion import obtener_cliente  # noqa: E402
from scripts.cargar_solicitantes_db import procesar  # noqa: E402
from scripts.sembrar import sembrar  # noqa: E402

EXAMEN_ID = "EXAUBI-2026B-en-v1"
EXAMEN = json.loads((RAIZ / "datos" / "examenes" / f"{EXAMEN_ID}.json").read_text(encoding="utf-8"))
FIXTURE = RAIZ / "tests" / "fixtures" / "alumnos_solicitantes.xlsx"

# Respuestas que obtienen 8/8 en el examen del prototipo
PERFECTAS = {
    "q01": 3, "q02": 1, "q03": 0, "q04": ["am", "are"], "q05": [0, 1],
    "q06": [2, 3, 0, 1, 4],
    "q07": ["can be trusted", "gives more than expected", "arrives on time"],
    "q08": "since",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def cliente():
    c = obtener_cliente()
    try:
        c.admin.command("ping")
    except ServerSelectionTimeoutError:
        pytest.skip("No hay un servidor MongoDB disponible en MONGODB_URI")
    return c


@pytest.fixture
def db(cliente):
    # Base fija para que el usuario de la app solo necesite permisos sobre ella.
    nombre = "idiomas_ug_test"
    cliente.drop_database(nombre)  # por si una corrida anterior se interrumpió
    base = cliente[nombre]
    sembrar(base, verbose=False)
    base.idiomas.update_one({"_id": "en"}, {"$set": {"activo": True}})
    op.publicar_examen(base, EXAMEN_ID)
    yield base
    cliente.drop_database(nombre)


def _asignacion(db, curp="LOPE020202MGTXXX09", nombre="Ana López", idioma="en"):
    return op.registrar_asignacion(db, curp=curp, nombre=nombre, idioma=idioma,
                                   convocatoria="2026B", correo="ana@ugto.mx")


# ---------------------------------------------------------------------------
# Esquema e índices: el servidor hace cumplir las reglas
# ---------------------------------------------------------------------------

class TestEsquema:
    def test_rechaza_curp_mal_formada(self, db):
        with pytest.raises(WriteError) as e:
            db.sustentantes.insert_one({"curp": "NO-ES-CURP", "nombre": "X",
                                        "creado_en": op.ahora_utc()})
        assert e.value.code == 121  # Document failed validation

    def test_rechaza_estado_inventado(self, db):
        asignacion, _ = _asignacion(db)
        with pytest.raises(WriteError):
            db.asignaciones.update_one({"_id": asignacion["_id"]}, {"$set": {"estado": "aprobado"}})

    def test_rechaza_pregunta_sin_campos_de_su_tipo(self, db):
        malo = json.loads(json.dumps(EXAMEN))
        malo.update(_id="EXAUBI-2026B-en-v9", version=9, estado="borrador")
        del malo["preguntas"][0]["opciones"]  # 'choice' sin opciones
        with pytest.raises(WriteError):
            op.cargar_examen(db, malo)

    def test_solo_un_examen_publicado_por_idioma(self, db):
        v2 = dict(EXAMEN, _id="EXAUBI-2026B-en-v2", version=2, estado="borrador")
        op.cargar_examen(db, v2)
        with pytest.raises(op.ErrorPlataforma, match="otro examen publicado"):
            op.publicar_examen(db, "EXAUBI-2026B-en-v2")

    def test_no_se_modifica_un_examen_con_intentos(self, db):
        asignacion, _ = _asignacion(db)
        op.iniciar_intento(db, asignacion["_id"])
        with pytest.raises(op.ErrorPlataforma, match="versión nueva"):
            op.cargar_examen(db, EXAMEN)

    def test_sembrar_es_repetible(self, db):
        sembrar(db, verbose=False)
        assert db.idiomas.count_documents({}) == 9
        assert db.examenes.count_documents({}) == 1


# ---------------------------------------------------------------------------
# Carga de solicitantes
# ---------------------------------------------------------------------------

class TestCarga:
    def test_fixture_del_repositorio(self, db):
        filas, errores = procesar(db, pd.read_excel(FIXTURE), "2026B")
        assert errores == []
        validas = [f for f in filas if f.es_valida]
        assert len(filas) == 10
        assert len(validas) == 3          # con inglés activado
        assert {f.error for f in filas if not f.es_valida} == {"CURP inválida"}
        assert [f.folio for f in validas] == [
            "EXAUBI-2026B-0001", "EXAUBI-2026B-0002", "EXAUBI-2026B-0003"]
        # Misma persona con dos idiomas → 1 sustentante, 2 asignaciones
        assert db.sustentantes.count_documents({"curp": "RAHE030910HQTMRMA3"}) == 1
        assert db.asignaciones.count_documents({"curp": "RAHE030910HQTMRMA3"}) == 2

    def test_idioma_inactivo_se_rechaza(self, db):
        db.idiomas.update_one({"_id": "en"}, {"$set": {"activo": False}})
        filas, _ = procesar(db, pd.read_excel(FIXTURE), "2026B")
        ingles = next(f for f in filas if f.curp == "RAHE030910HQTMRMA3" and f.idioma == "Inglés")
        assert ingles.error == "Idioma no válido: 'Inglés'"

    def test_recargar_el_mismo_archivo_no_duplica(self, db):
        procesar(db, pd.read_excel(FIXTURE), "2026B")
        filas, _ = procesar(db, pd.read_excel(FIXTURE), "2026B")
        assert not any(f.es_valida for f in filas)
        assert sum(f.error == "Ya registrado en la base" for f in filas) == 3
        assert db.asignaciones.count_documents({}) == 3

    def test_otra_convocatoria_si_se_permite(self, db):
        procesar(db, pd.read_excel(FIXTURE), "2026B")
        filas, _ = procesar(db, pd.read_excel(FIXTURE), "2027A")
        assert sum(f.es_valida for f in filas) == 3
        assert db.sustentantes.count_documents({}) == 2

    def test_columnas_faltantes(self, db):
        _, errores = procesar(db, pd.DataFrame([{"CURP": "X"}]), "2026B")
        assert "Columnas faltantes" in errores[0]

    def test_la_clave_nunca_se_guarda_en_texto_plano(self, db):
        asignacion, clave = _asignacion(db)
        doc = db.asignaciones.find_one({"_id": asignacion["_id"]})
        assert clave not in json.dumps(doc, default=str)
        assert op.normalizar_clave(clave) not in json.dumps(doc, default=str)

    def test_indice_unico_impide_duplicado_aunque_se_salte_el_codigo(self, db):
        asignacion, _ = _asignacion(db)
        copia = {k: v for k, v in asignacion.items() if k != "_id"}
        copia.update(folio="OTRO", clave_hash="0" * 64)
        with pytest.raises(DuplicateKeyError):
            db.asignaciones.insert_one(copia)


# ---------------------------------------------------------------------------
# Login y examen
# ---------------------------------------------------------------------------

class TestFlujoSustentante:
    def test_login_normaliza_la_clave(self, db):
        asignacion, clave = _asignacion(db)
        variante = " " + clave.lower().replace("-", " ") + " "
        assert op.autenticar(db, "lope020202mgtxxx09", variante)["_id"] == asignacion["_id"]

    def test_login_incorrecto(self, db):
        _, clave = _asignacion(db)
        with pytest.raises(op.AccesoDenegado):
            op.autenticar(db, "LOPE020202MGTXXX09", "AAAA-BBBB")
        with pytest.raises(op.AccesoDenegado):
            op.autenticar(db, "RAME030101HGTXXX09", clave)  # clave correcta, otra CURP

    def test_examen_sin_respuestas_correctas(self, db):
        asignacion, _ = _asignacion(db)
        intento = op.iniciar_intento(db, asignacion["_id"])
        vista = op.examen_para_sustentante(db, intento["_id"])
        assert len(vista["preguntas"]) == 10
        assert all("respuesta" not in p for p in vista["preguntas"])
        assert 34 * 60 < vista["segundos_restantes"] <= 35 * 60

    def test_flujo_completo_perfecto(self, db):
        asignacion, clave = _asignacion(db)
        a = op.autenticar(db, "LOPE020202MGTXXX09", clave)
        intento = op.iniciar_intento(db, a["_id"])
        for pid, valor in PERFECTAS.items():
            op.guardar_respuesta(db, intento["_id"], pid, valor)
        op.guardar_respuesta(db, intento["_id"], "q10", "A short essay.")
        final = op.finalizar_intento(db, intento["_id"])

        r = final["resultado"]
        assert (r["aciertos"], r["calificables"], r["mcer"]) == (8, 8, "C1")
        assert r["pendientes_revision"] == ["q10"]
        assert final["estado"] == "enviado"
        assert db.asignaciones.find_one({"_id": a["_id"]})["estado"] == "finalizado"

        cert = op.datos_certificado(db, a["_id"])
        assert cert["folio"] == asignacion["folio"]
        assert cert["idioma"] == "Inglés"
        assert cert["mcer"] == "C1"

    def test_sin_respuestas_es_a1(self, db):
        asignacion, _ = _asignacion(db)
        intento = op.iniciar_intento(db, asignacion["_id"])
        r = op.finalizar_intento(db, intento["_id"])["resultado"]
        assert (r["aciertos"], r["mcer"]) == (0, "A1")

    def test_un_solo_intento(self, db):
        asignacion, clave = _asignacion(db)
        intento = op.iniciar_intento(db, asignacion["_id"])
        op.finalizar_intento(db, intento["_id"])
        with pytest.raises(op.IntentoNoPermitido):
            op.iniciar_intento(db, asignacion["_id"])
        with pytest.raises(op.AccesoDenegado, match="ya se utilizó"):
            op.autenticar(db, "LOPE020202MGTXXX09", clave)

    def test_reanudar_conserva_tiempo_y_respuestas(self, db):
        asignacion, _ = _asignacion(db)
        t0 = op.ahora_utc()
        intento = op.iniciar_intento(db, asignacion["_id"], ahora=t0)
        op.guardar_respuesta(db, intento["_id"], "q01", 3, ahora=t0)
        t1 = t0 + timedelta(minutes=10)
        otra_vez = op.iniciar_intento(db, asignacion["_id"], ahora=t1)
        assert otra_vez["_id"] == intento["_id"]
        vista = op.examen_para_sustentante(db, intento["_id"], ahora=t1)
        assert vista["respuestas"] == {"q01": 3}
        assert vista["segundos_restantes"] == 25 * 60

    def test_dos_inicios_simultaneos_crean_un_solo_intento(self, db):
        asignacion, _ = _asignacion(db)
        a = op.iniciar_intento(db, asignacion["_id"])
        # Simula la carrera: una segunda inserción para la misma asignación choca con el índice único
        with pytest.raises(DuplicateKeyError):
            db.intentos.insert_one({k: v for k, v in a.items() if k != "_id"})
        assert db.intentos.count_documents({"asignacion_id": asignacion["_id"]}) == 1

    def test_no_se_responde_fuera_de_tiempo(self, db):
        asignacion, _ = _asignacion(db)
        t0 = op.ahora_utc()
        intento = op.iniciar_intento(db, asignacion["_id"], ahora=t0)
        tarde = t0 + timedelta(minutes=35, seconds=op.GRACIA_SEGUNDOS + 1)
        with pytest.raises(op.IntentoCerrado):
            op.guardar_respuesta(db, intento["_id"], "q01", 3, ahora=tarde)
        # Dentro del margen de gracia sí se acepta
        op.guardar_respuesta(db, intento["_id"], "q01", 3,
                             ahora=t0 + timedelta(minutes=35, seconds=5))

    @pytest.mark.parametrize("pid", ["q99", "q01.valor", "$set", "respuestas", 1])
    def test_pregunta_invalida(self, db, pid):
        asignacion, _ = _asignacion(db)
        intento = op.iniciar_intento(db, asignacion["_id"])
        with pytest.raises(op.DatoInvalido):
            op.guardar_respuesta(db, intento["_id"], pid, 1)

    @pytest.mark.parametrize("valor", [True, {"$gt": 1}, [[1]], "x" * 6000, list(range(40))])
    def test_valor_invalido(self, db, valor):
        asignacion, _ = _asignacion(db)
        intento = op.iniciar_intento(db, asignacion["_id"])
        with pytest.raises(op.DatoInvalido):
            op.guardar_respuesta(db, intento["_id"], "q01", valor)

    def test_cierre_automatico_por_tiempo(self, db):
        asignacion, _ = _asignacion(db)
        t0 = op.ahora_utc()
        intento = op.iniciar_intento(db, asignacion["_id"], ahora=t0)
        op.guardar_respuesta(db, intento["_id"], "q01", 3, ahora=t0)
        assert op.cerrar_intentos_vencidos(db, ahora=t0 + timedelta(minutes=20)) == 0
        assert op.cerrar_intentos_vencidos(db, ahora=t0 + timedelta(minutes=40)) == 1
        cerrado = db.intentos.find_one({"_id": intento["_id"]})
        assert cerrado["estado"] == "tiempo_agotado"
        assert cerrado["resultado"]["aciertos"] == 1
        assert cerrado["resultado"]["segundos_usados"] == 35 * 60

    def test_finalizar_dos_veces_es_seguro(self, db):
        asignacion, _ = _asignacion(db)
        intento = op.iniciar_intento(db, asignacion["_id"])
        primero = op.finalizar_intento(db, intento["_id"])
        segundo = op.finalizar_intento(db, intento["_id"])
        assert primero["resultado"] == segundo["resultado"]

    def test_incidencias_acotadas(self, db):
        asignacion, _ = _asignacion(db)
        intento = op.iniciar_intento(db, asignacion["_id"])
        for _ in range(op.MAX_INCIDENCIAS + 20):
            op.registrar_incidencia(db, intento["_id"], "copia")
        doc = db.intentos.find_one({"_id": intento["_id"]})
        assert len(doc["incidencias"]) == op.MAX_INCIDENCIAS

    def test_examen_no_publicado(self, db):
        asignacion, _ = _asignacion(db, idioma="fr")  # no hay examen de francés
        with pytest.raises(op.ExamenNoDisponible):
            op.iniciar_intento(db, asignacion["_id"])

    def test_regenerar_clave(self, db):
        asignacion, vieja = _asignacion(db)
        nueva = op.regenerar_clave(db, asignacion["_id"])
        assert nueva != vieja
        with pytest.raises(op.AccesoDenegado):
            op.autenticar(db, "LOPE020202MGTXXX09", vieja)
        assert op.autenticar(db, "LOPE020202MGTXXX09", nueva)


class TestReportes:
    def test_resumen_convocatoria(self, db):
        procesar(db, pd.read_excel(FIXTURE), "2026B")
        en = db.asignaciones.find_one({"idioma": "en"})
        intento = op.iniciar_intento(db, en["_id"])
        for pid, valor in PERFECTAS.items():
            op.guardar_respuesta(db, intento["_id"], pid, valor)
        op.finalizar_intento(db, intento["_id"])
        resumen = {r["idioma"]: r for r in op.resumen_convocatoria(db, "2026B")}
        assert resumen["de"] == {"idioma": "de", "registrados": 2, "niveles": {"sin_presentar": 2}}
        assert resumen["en"] == {"idioma": "en", "registrados": 1, "niveles": {"C1": 1}}


# ---------------------------------------------------------------------------
# Calificación (sin base de datos)
# ---------------------------------------------------------------------------

class TestCalificacion:
    P = {p["id"]: p for p in EXAMEN["preguntas"]}

    def test_perfectas(self):
        r = calificar(EXAMEN, PERFECTAS)
        assert (r["aciertos"], r["mcer"]) == (8, "C1")

    @pytest.mark.parametrize("pid,valor,esperado", [
        ("q01", 3, True), ("q01", 2, False), ("q01", True, False), ("q01", "3", False),
        ("q04", ["am", "are"], True), ("q04", ["am"], False),
        ("q05", [0, 1], True), ("q05", [1, 0], False), ("q05", [0, 99], False),
        ("q06", [2, 3, 0, 1, 4], True), ("q06", [2, 3, 0, 1], False), ("q06", [2, -9], False),
        ("q07", ["can be trusted", "gives more than expected", "arrives on time"], True),
        ("q08", "  Since. ", True), ("q08", "for", False),
        ("q09", 0, False),   # sin respuesta correcta definida en el prototipo
        ("q10", "texto", False),
    ])
    def test_por_tipo(self, pid, valor, esperado):
        assert es_correcta(self.P[pid], valor) is esperado

    def test_cortes_de_nivel_del_prototipo(self):
        # Mismos cortes que computeResults: ≤2 A1, ≤4 A2, ≤6 B1, 7 B2, 8 C1
        ids = list(PERFECTAS)
        esperados = ["A1", "A1", "A1", "A2", "A2", "B1", "B1", "B2", "C1"]
        for n, mcer in enumerate(esperados):
            r = calificar(EXAMEN, {pid: PERFECTAS[pid] for pid in ids[:n]})
            assert (r["aciertos"], r["mcer"]) == (n, mcer)
