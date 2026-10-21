"""Validación de CURP y formato de claves (sin base de datos)."""

import re

import pytest

from db.carga import validar_curp
from db.operaciones import generar_clave


@pytest.mark.parametrize("entrada", ["RAME030101HGTXXX09", "  rame030101hgtxxx09 "])
def test_curp_valida_se_normaliza(entrada):
    assert validar_curp(entrada) == "RAME030101HGTXXX09"


@pytest.mark.parametrize("entrada", [
    None, "", "RAME030101HGTXXX0", "RAME030101HGTXXX092",  # longitud
    "0AME030101HGTXXX09", "RAME030101HZZXXX09", "RAME030101XGTXXX09",  # formato, entidad, sexo
    "RAME030101HGTXXX02",  # dígito verificador
])
def test_curp_invalida(entrada):
    with pytest.raises(ValueError):
        validar_curp(entrada)


def test_curp_nacido_en_el_extranjero():
    assert validar_curp("LOPE020202MNEXXX06")[11:13] == "NE"


def test_clave_formato_sin_caracteres_ambiguos():
    claves = {generar_clave() for _ in range(200)}
    assert len(claves) == 200
    assert all(re.fullmatch(r"[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}", c) for c in claves)
    assert re.fullmatch(r"(\w{4}-){2}\w{4}", generar_clave(segmentos=3))
