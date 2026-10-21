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

Tests need a reachable MongoDB and always use the fixed database `idiomas_ug_test` (DB tests are skipped if no server is available). `CLAVE_PEPPER` defaults to a test value inside the tests. `tests/test_cache.py` needs Redis at `REDIS_URL_TEST` (default `redis://localhost:6379/15`, flushed by the tests) and is skipped otherwise.

Frontend (React + TypeScript, Vite; Node 22):

```sh
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to http://localhost:8000 (no CORS setup needed)
npm run lint       # eslint (typescript-eslint + react-hooks)
npm run build      # tsc -b typecheck, then vite build into dist/
```

## Architecture

- **`backend/db/`** — the domain layer. `operaciones.py` holds all business operations (auth, attempts, saving answers, incidents, finalizing, certificates) and raises `ErrorPlataforma` subclasses with user-facing Spanish messages. `calificacion.py` grades on the server; `carga.py` validates and registers applicants from Excel (CURP check digit, key Excel); `esquemas.py`/`crear_base_datos.py` define collection validators and indexes; `conexion.py` resolves the DB from env. `cache.py` is a write-through Redis cache (`REDIS_URL`; unset or unreachable = plain MongoDB): operations write MongoDB first, then Redis; attempt state, exam content, profile and the assignment→attempt id are read from Redis with MongoDB fallback.
- **`backend/api/main.py`** — thin FastAPI wrapper over `db.operaciones`. Maps `ErrorPlataforma` subclasses to HTTP codes via `_ESTADOS`. Sessions are stateless HMAC tokens (`crear_token`/`leer_token`, signed with `CLAVE_PEPPER`, 4h) sent as `Bearer`. `get_db` is overridden in tests via `app.dependency_overrides`. Staff (collection `usuarios`, roles `admin`/`profesor`, scrypt hashes in `operaciones.py` "Personal") use the same token scheme with a different signature prefix (`personal|`) so tokens are not interchangeable; `personal_actual` re-reads the user on every request and `requiere_rol(...)` guards routes (`/api/personal/*`). `POST /api/personal/solicitantes/carga?convocatoria=` takes the raw .xlsx body (no multipart), runs `db/carga.procesar` (shared with `scripts/cargar_solicitantes_db.py`) and returns the key Excel as base64; a MongoDB error on one row becomes a row error so issued keys are never lost. Health check: `GET /api/salud`.
- **`backend/scripts/`** — offline admin CLIs (seed, load applicants from Excel into the DB, `crear_usuario.py` creates staff users). Only argument parsing and printing: `db/` and `api/` never import from `scripts/`.
- **`frontend/`** — React + TypeScript SPA built with Vite, no router and no state library. `src/App.tsx` switches screens from `screen` in `src/context/SessionContext.tsx` (session, profile, result, loaded exam, navigation actions; replaces the old mutable `state.js`). `src/pages/<Screen>/` holds each screen with its co-located CSS (Login + Bee bot `HelpChat`, Profile, Instructions, Exam + per-type `Answer`, Results); the Exam page owns its question index, answers, debounced autosave and the anti-AI copy guard. `src/api/` is the fetch client (token in `sessionStorage`, always same-origin `/api`) plus types mirroring `backend/api/main.py`. `src/services/questions.ts` adapts the API's Spanish question schema into the compact shape the exam renders; `src/data/copy.ts` holds the login/Bee bot copy; `src/hooks/` has `useCountdown` and `useTypewriter`; `src/pages/Panel/` is the staff panel at `/panel` (rendered by `App.tsx` on that path, own login and `exaubi-personal` token, API calls through `apiPersonal` which sends a 401 back to the panel login, tabs by rol: Exámenes with grades, search and language filter for admin and profesor; Solicitantes for admin, which uploads the applicants Excel, downloads the generated access-key Excel, filters by estado and regenerates a pending applicant's key on demand — keys are hash-only, so a lost key is regenerated, never shown); `src/components/` the shared `AppShell` header and `Flip`/`TypedText`. Global CSS is `src/assets/styles/{tokens,base}.css`. `frontend/design-reference/` is an untracked design prototype, excluded from the build. **Answer keys never reach the browser** — all scoring happens server-side.
- Exam content lives as JSON in `backend/datos/examenes/` and is loaded into MongoDB.

## Deploy

Push to `develop` (touching `backend/**`, `frontend/**`, `docker-compose.yml` or the workflow) triggers `.github/workflows/deploy-vps.yml` on the self-hosted runner on the home server `nextcl`: copies `.env` from `~/inst/ug_idiomas_entorno/.env`, builds images, runs pytest inside the `api` container, `docker compose up -d`, then health-checks `/api/salud`. The `web` image builds the frontend with `node:22-alpine` (`npm ci && npm run build`) and Caddy (`frontend/Caddyfile`) serves `dist/` as static files and proxies `/api/*` to `api:8000`. MongoDB runs in a separate compose stack on the same server, not in this repo's `docker-compose.yml`; Redis (cache only, no persistence) is the `redis` service in it.

## CodeGraph

The repo is indexed (`.codegraph/`). Use `codegraph_explore` (or `codegraph explore "<query>"`) before grep/Read to locate or understand code.
