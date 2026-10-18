# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Placement-exam web app for the Departamento de Idiomas, Universidad de Guanajuato (Campus León). Domain code, identifiers, API fields and user-facing messages are in Spanish; keep that convention.

## Commands

All Python commands run from `backend/` (imports are `db.*`, `api.*`, `tests.*`; `.env` is found in `backend/` or the repo root).

```sh
cd backend
pip install -r requirements.txt -r requirements-db.txt
cp .env.example .env                      # MONGODB_URI, CLAVE_PEPPER (required), MONGODB_DB, CORS_ORIGENES

uvicorn api.main:app --reload             # API on :8000
python -m pytest tests -v                 # full suite
python -m pytest tests/test_api.py -v -k <name>   # single test
python scripts/sembrar.py                 # idempotent: collections, validators, indexes, languages, exams from datos/
python scripts/sembrar.py --publicar <examen_id>   # also publish an exam
python scripts/demo.py                    # end-to-end walkthrough, recreates idiomas_ug_demo
```

Tests need a reachable MongoDB and always use the fixed database `idiomas_ug_test` (DB tests are skipped if no server is available). `CLAVE_PEPPER` defaults to a test value inside the tests.

Frontend (static ES modules, must be served over HTTP):

```sh
cd frontend && python3 -m http.server 5500
```

`frontend/js/config.js` points to `http://localhost:8000/api` only when the page is on port **5500**; any other port uses same-origin `/api` (the README's port 8000 example collides with the API). Add `http://localhost:5500` to `CORS_ORIGENES` for local dev.

## Architecture

- **`backend/db/`** — the domain layer. `operaciones.py` holds all business operations (auth, attempts, saving answers, incidents, finalizing, certificates) and raises `ErrorPlataforma` subclasses with user-facing Spanish messages. `calificacion.py` grades on the server; `esquemas.py`/`crear_base_datos.py` define collection validators and indexes; `conexion.py` resolves the DB from env.
- **`backend/api/main.py`** — thin FastAPI wrapper over `db.operaciones`. Maps `ErrorPlataforma` subclasses to HTTP codes via `_ESTADOS`. Sessions are stateless HMAC tokens (`crear_token`/`leer_token`, signed with `CLAVE_PEPPER`, 4h) sent as `Bearer`. `get_db` is overridden in tests via `app.dependency_overrides`. Health check: `GET /api/salud`.
- **`backend/scripts/`** — offline admin tools (seed, load applicants from Excel into the DB).
- **`frontend/`** — vanilla HTML/CSS/JS, no build step, no framework. `index.html` contains markup for every screen; `js/app.js` toggles screens and wires modules; `js/state.js` is a single mutable state object (screens mutate it and re-render themselves, no reactivity); `js/api.js` is the fetch client (token in `sessionStorage`). `js/data/questions.js` adapts the API's Spanish question schema into the compact shape the exam screen renders. **Answer keys never reach the browser** — all scoring happens server-side.
- Exam content lives as JSON in `backend/datos/examenes/` and is loaded into MongoDB.

## Deploy

Push to `develop` (touching `backend/**`, `frontend/**`, `docker-compose.yml` or the workflow) triggers `.github/workflows/deploy-vps.yml` on the self-hosted runner on the home server `nextcl`: copies `.env` from `~/inst/ug_idiomas_entorno/.env`, builds images, runs pytest inside the `api` container, `docker compose up -d`, then health-checks `/api/salud`. Caddy (`frontend/Caddyfile`) serves static files and proxies `/api/*` to `api:8000`. MongoDB runs in a separate compose stack on the same server, not in this repo's `docker-compose.yml`.

## CodeGraph

The repo is indexed (`.codegraph/`). Use `codegraph_explore` (or `codegraph explore "<query>"`) before grep/Read to locate or understand code.
