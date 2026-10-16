"""Tests for cargar_solicitantes.py"""

import pandas as pd
import pytest
from pathlib import Path

# Adjust import path so `python -m pytest` works from project root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from cargar_solicitantes import (
    validate_curp,
    validate_curp_formato,
    validar_curp_segura,
    idioma_es_valido,
    generar_clave,
    procesar_solicitantes,
    IdiomasDisponibles,
    FilaResultado,
)


# ---------------------------------------------------------------------------
# CURP validation
# ---------------------------------------------------------------------------

class TestValidateCurpFormato:
    """Tests for format-only CURP validation."""

    def test_valid_curp(self):
        assert validate_curp_formato("RAME030101HGTXXX09") == "RAME030101HGTXXX09"

    def test_normalizes_to_uppercase(self):
        assert validate_curp_formato("rame030101hgtxxx09") == "RAME030101HGTXXX09"

    def test_strips_whitespace(self):
        assert validate_curp_formato("  RAME030101HGTXXX09  ") == "RAME030101HGTXXX09"

    def test_none_raises(self):
        with pytest.raises(ValueError, match="obligatoria"):
            validate_curp_formato(None)

    def test_too_short(self):
        with pytest.raises(ValueError, match="18 caracteres"):
            validate_curp_formato("RAME030101HGTXXX0")

    def test_too_long(self):
        with pytest.raises(ValueError, match="18 caracteres"):
            validate_curp_formato("RAME030101HGTXXX092")

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="formato inválido"):
            validate_curp_formato("0AME030101HGTXXX09")

    def test_invalid_state_code(self):
        with pytest.raises(ValueError, match="formato inválido"):
            validate_curp_formato("RAME030101HZZXXX09")

    def test_invalid_sex(self):
        with pytest.raises(ValueError, match="formato inválido"):
            validate_curp_formato("RAME030101XGTXXX09")

    def test_foreign_born_NE(self):
        curp = "RAME030101HNEXXX09"
        result = validate_curp_formato(curp)
        assert result == curp


class TestValidateCurp:
    """Tests for full CURP validation (format + check digit)."""

    def test_valid_curp_with_check_digit(self):
        assert validate_curp("RAME030101HGTXXX09") == "RAME030101HGTXXX09"

    def test_invalid_check_digit(self):
        with pytest.raises(ValueError, match="dígito verificador"):
            validate_curp("RAME030101HGTXXX02")

    def test_valid_curp_lope(self):
        assert validate_curp("LOPE020202MGTXXX09") == "LOPE020202MGTXXX09"


class TestValidarCurpSegura:
    """Tests for boolean CURP validation."""

    def test_valid_returns_true(self):
        assert validar_curp_segura("RAME030101HGTXXX09") is True

    def test_invalid_returns_false(self):
        assert validar_curp_segura("INVALID") is False

    def test_none_returns_false(self):
        assert validar_curp_segura(None) is False

    def test_wrong_check_digit_returns_false(self):
        assert validar_curp_segura("RAME030101HGTXXX02") is False


# ---------------------------------------------------------------------------
# Language validation
# ---------------------------------------------------------------------------

class TestIdiomaEsValido:
    """Tests for language validation."""

    def test_valid_languages(self):
        for idioma in IdiomasDisponibles:
            assert idioma_es_valido(idioma.value) is True

    def test_invalid_language(self):
        assert idioma_es_valido("Inglés") is False

    def test_none_returns_false(self):
        assert idioma_es_valido(None) is False

    def test_empty_string_returns_false(self):
        assert idioma_es_valido("") is False

    def test_whitespace_strips(self):
        assert idioma_es_valido("  Francés  ") is True

    def test_case_sensitive(self):
        assert idioma_es_valido("francés") is False


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

class TestGenerarClave:
    """Tests for access key generation."""

    def test_default_format(self):
        clave = generar_clave()
        parts = clave.split("-")
        assert len(parts) == 2
        assert all(len(p) == 4 for p in parts)

    def test_only_valid_chars(self):
        from cargar_solicitantes import _KEY_CHARS
        for _ in range(100):
            clave = generar_clave().replace("-", "")
            assert all(c in _KEY_CHARS for c in clave)

    def test_uniqueness(self):
        claves = {generar_clave() for _ in range(100)}
        assert len(claves) == 100

    def test_custom_segments(self):
        clave = generar_clave(segmentos=3)
        parts = clave.split("-")
        assert len(parts) == 3

    def test_no_ambiguous_chars(self):
        for _ in range(100):
            clave = generar_clave()
            assert "0" not in clave
            assert "O" not in clave
            assert "1" not in clave
            assert "I" not in clave
            assert "L" not in clave


# ---------------------------------------------------------------------------
# Full processing pipeline
# ---------------------------------------------------------------------------

class TestProcesarSolicitantes:
    """Tests for the end-to-end processing function."""

    def _make_df(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_happy_path(self):
        df = self._make_df([
            {"CURP": "RAME030101HGTXXX09", "Nombre": "Emiliano Ramírez", "Idioma": "Francés"},
            {"CURP": "LOPE020202MGTXXX09", "Nombre": "Ana López", "Idioma": "Italiano"},
        ])
        resultado = procesar_solicitantes(df)
        assert len(resultado.filas) == 2
        assert len(resultado.registros_validos) == 2
        assert len(resultado.registros_con_error) == 0
        assert all(f.clave is not None for f in resultado.filas)

    def test_same_student_two_languages(self):
        """Same CURP + different language = two valid records, not duplicates."""
        df = self._make_df([
            {"CURP": "RAME030101HGTXXX09", "Nombre": "Emiliano Ramírez", "Idioma": "Francés"},
            {"CURP": "RAME030101HGTXXX09", "Nombre": "Emiliano Ramírez", "Idioma": "Japonés"},
        ])
        resultado = procesar_solicitantes(df)
        assert len(resultado.registros_validos) == 2
        assert resultado.filas[0].clave != resultado.filas[1].clave

    def test_duplicate_same_curp_same_idioma(self):
        """Same CURP + same language = duplicate."""
        df = self._make_df([
            {"CURP": "RAME030101HGTXXX09", "Nombre": "Emiliano Ramírez", "Idioma": "Francés"},
            {"CURP": "RAME030101HGTXXX09", "Nombre": "Emiliano Ramírez", "Idioma": "Francés"},
        ])
        resultado = procesar_solicitantes(df)
        assert len(resultado.registros_validos) == 1
        assert len(resultado.registros_con_error) == 1
        assert resultado.filas[1].error == "Registro duplicado"

    def test_missing_curp(self):
        df = self._make_df([
            {"CURP": None, "Nombre": "Emiliano Ramírez", "Idioma": "Francés"},
        ])
        resultado = procesar_solicitantes(df)
        assert len(resultado.filas) == 1
        assert resultado.filas[0].error == "CURP vacía"
        assert resultado.filas[0].es_valida is False

    def test_missing_nombre(self):
        df = self._make_df([
            {"CURP": "RAME030101HGTXXX09", "Nombre": "", "Idioma": "Francés"},
        ])
        resultado = procesar_solicitantes(df)
        assert resultado.filas[0].error == "Nombre vacío"

    def test_missing_idioma(self):
        df = self._make_df([
            {"CURP": "RAME030101HGTXXX09", "Nombre": "Emiliano Ramírez", "Idioma": None},
        ])
        resultado = procesar_solicitantes(df)
        assert resultado.filas[0].error == "Idioma vacío"

    def test_invalid_curp(self):
        df = self._make_df([
            {"CURP": "INVALIDCURP1234567", "Nombre": "Emiliano Ramírez", "Idioma": "Francés"},
        ])
        resultado = procesar_solicitantes(df)
        assert resultado.filas[0].error == "CURP inválida"

    def test_invalid_idioma(self):
        df = self._make_df([
            {"CURP": "RAME030101HGTXXX09", "Nombre": "Emiliano Ramírez", "Idioma": "Inglés"},
        ])
        resultado = procesar_solicitantes(df)
        assert "no válido" in resultado.filas[0].error

    def test_missing_columns(self):
        df = pd.DataFrame([{"CURP": "RAME030101HGTXXX09"}])
        resultado = procesar_solicitantes(df)
        assert len(resultado.errores_globales) == 1
        assert "Columnas faltantes" in resultado.errores_globales[0]

    def test_mixed_valid_and_invalid(self):
        df = self._make_df([
            {"CURP": "RAME030101HGTXXX09", "Nombre": "Emiliano Ramírez", "Idioma": "Francés"},
            {"CURP": "INVALID", "Nombre": "Bad Entry", "Idioma": "Francés"},
            {"CURP": "LOPE020202MGTXXX09", "Nombre": "Ana López", "Idioma": "Italiano"},
        ])
        resultado = procesar_solicitantes(df)
        assert len(resultado.filas) == 3
        assert len(resultado.registros_validos) == 2
        assert len(resultado.registros_con_error) == 1
        assert resultado.filas[1].error == "CURP inválida"

    def test_nan_values(self):
        df = self._make_df([
            {"CURP": float("nan"), "Nombre": "Emiliano Ramírez", "Idioma": "Francés"},
        ])
        resultado = procesar_solicitantes(df)
        assert resultado.filas[0].error == "CURP vacía"

    def test_all_rows_present_in_output(self):
        """Every input row appears in the result — valid or not."""
        df = self._make_df([
            {"CURP": "RAME030101HGTXXX09", "Nombre": "Emiliano Ramírez", "Idioma": "Francés"},
            {"CURP": "BAD", "Nombre": "Bad", "Idioma": "Francés"},
            {"CURP": "LOPE020202MGTXXX09", "Nombre": "Ana López", "Idioma": "Inglés"},
        ])
        resultado = procesar_solicitantes(df)
        assert len(resultado.filas) == 3
        # First: valid
        assert resultado.filas[0].es_valida
        assert resultado.filas[0].clave is not None
        # Second: invalid CURP
        assert not resultado.filas[1].es_valida
        assert resultado.filas[1].error == "CURP inválida"
        # Third: invalid language
        assert not resultado.filas[2].es_valida
        assert "no válido" in resultado.filas[2].error
