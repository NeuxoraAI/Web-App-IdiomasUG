# Calidad: tanda de prioridad alta (backend + frontend)

Objective: apply the 7 high-priority review findings without changing behavior. Branch: develop (local commits, no push). Delivery: ask-on-risk. Runners: `cd backend && .venv/bin/python -m pytest tests -q`; `cd frontend && npm run lint && npm run build`.

## Specs

- S1. Layering: `db/` and `api/` no longer import from `scripts/`. Upload logic (CURP validation, key generation, `procesar`, output Excel) lives in `db/`; scripts only parse args and print.
- S2. Delete the old DB-less `scripts/cargar_solicitantes.py` (and its tests for the hardcoded language enum); keep CURP and key tests against the new location.
- S3. Business logic out of routes: `perfil`, `_intento_id` and the folio lookup move to `db/operaciones.py`; `api/main.py` stops using `op._id`.
- S4. Upload never loses keys: a MongoDB error on one row becomes a row error, the key Excel is still returned.
- S5. Panel error message style no longer depends on `login.css`.
- S6. Panel returns to its login when the staff token expires (401) in any tab.
- S7. Remove zustand (only persisted `q` in sessionStorage); AGENTS.md "no state library" stays true.

## Tasks

- [x] T1 (S1, S2, S4) — inline — commit 979d3de — backend upload module `db/carga.py`, delete old script. Risk: item 1 (persisted keys on upload).
- [x] T2 (S3) — inline — commit c4e87f0 — routes delegate to operaciones.
- [x] T3 (S5, S6) — inline — commit de611c7 — panel CSS + 401 handling.
- [x] T4 (S7) — inline — commit 88c2847 (docs 4f7eb06) — drop zustand.

## Log

- L1 (2026-10-20): "si, aplica la tanda de prioridad alta" (after the review listing items 1-7 alta).
- L2: RED observed for S4 (row MongoDB error test fails without the except). Backend 88 passed / 2 skipped; frontend lint + build clean.
- L3: Independent verifier (item 1): S1-S7 PASS, no blockers. Differential: old validate_curp vs validar_curp identical on 24 inputs; API status/bodies identical to baseline for perfil, intento, sesion, personal/yo, regenerar clave. Advisories: old zustand sessionStorage format reads as 0 (server position still resumes); partial write in registrar_asignacion is pre-existing. 401 panel flow not exercised in a browser.
