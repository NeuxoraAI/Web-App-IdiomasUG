# Calidad: tanda de prioridad media (convenciones, duplicados, YAGNI)

Objective: apply the medium-priority review findings without changing behavior. Branch: develop (local commits, no push). Delivery: ask-on-risk. Runners: `cd backend && .venv/bin/python -m pytest tests -q`; `cd frontend && npm run lint && npm run build`.

## Specs

- S1. "que se use un mismo estilo para poder tener consistentes los estilos": one written naming/comment rule in AGENTS.md. Assumption (default picked, no product impact): backend identifiers, comments and docstrings in Spanish (db/ already is); frontend identifiers, file names and comments in English (pages already are), keeping API field names (perfil, folio, estado) and UI text in Spanish.
- S2. Apply S1: Panel files/identifiers to English; api/main.py and tests comments to Spanish.
- S3. Duplicates: one estado label map typed with `EstadoAsignacion`; one `CLAVE_PEPPER` reader; unused frontend type aliases removed or used.
- S4. "que no se hagan cosas de mas": remove `services/config.ts` (`AI_GUARD` constant, `API_URL` into client), the hardcoded "EXAUBI 2026B · Inglés" login eyebrow.
- S5. Panel is mounted outside `SessionProvider`, so `/panel` never calls applicant endpoints.
- S6. Indexes for the panel listings (`listar_solicitantes`, `examenes_presentados`); "not found" cases raise `NoEncontrado` (404) instead of generic 400.
- Not done, by decision: `datos_certificado`/`resumen_convocatoria` stay (used by `scripts/demo.py`, the DB walkthrough); `cerrar_intentos_vencidos` stays (needs a scheduler decision); pagination deferred (ponytail note already in Filtros).

## Tasks

- [x] T1 (S3-S5 frontend, S2 frontend) — inline — commit 6093076 — frontend structure + renames.
- [x] T2 (S2 backend, S3 backend, S6) — inline — commit d04c470 — backend comments, pepper, errors, indexes. Risk: item 1 (new indexes on existing collections, applied by sembrar).
- [x] T3 (S1) — inline — this commit — AGENTS.md rule.

## Log

- L1 (2026-10-20): "dale la media" (after the review listing the media items).
- L2: Frontend lint + build clean after T1. Backend RED observed for the index + NoEncontrado tests (fail with T2 stashed), GREEN 90 passed / 2 skipped. Error-handling pattern left as is: `(err as Error).message` is the single display pattern; `instanceof`/`err.status` only where the status matters.
- L3: Production needs `docker exec idiomas-ug-api-1 python scripts/sembrar.py` once to create the new indexes (deploy does not run it).
