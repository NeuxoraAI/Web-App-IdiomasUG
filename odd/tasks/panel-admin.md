# Panel admin: exámenes con calificaciones y carga de solicitantes

Objective: make the staff panel tabs functional. Branch: develop (local commits, no push). Delivery: ask-on-risk. Runners: `cd backend && python -m pytest tests -v`; `cd frontend && npm run lint && npm run build`.

## Specs

- S1. "se elimina la parte de calificaciones" — the Calificaciones tab is removed for every rol.
- S2. "esa se integra en examenes y cotiene un buscador y filtros por idioma igual para profesores" — the Exámenes tab shows grades (results of applicants' exams) with a search box and a language filter; both admin and profesor see it.
- S3. "en la parte de solicitantes no exite la parte de cargar el excel, ni la tabla de los solicitantes" — admin Solicitantes tab: upload an applicants Excel (columns CURP, Nombre, Idioma, optional Correo; same rules as `scripts/cargar_solicitantes_db.py`) and a table listing the registered applicants.
- S4. "ni el excel con lo que pedi que se genera el token de acceso apra los solicitantes y te deja descargar ese excel" — the upload generates the access keys and lets the admin download the output Excel (CURP, Nombre, Idioma, Folio, Clave/error), the same file the CLI script produces.
- S5. "tambien ahi mismo estará la tabla de usuarios y sus claves de acceso para poder ver los activos" — in the Solicitantes tab the applicants table gets an estado filter to see the active ones; keys stay hash-only (user chose "Regenerar bajo demanda"): a per-row "Regenerar clave" for pending applicants shows the new key once and invalidates the old one.
- S6. "recuerda usar grid layout para tener todo mejor organizado" — the panel layout uses CSS grid.
- Assumption: convocatoria for the upload is typed by the admin (e.g. 2026B), as the CLI requires `--convocatoria`.
- Assumption: search/filter are client-side over the full list.

## Tasks

- [x] T1 (S1-S4 backend) — inline — commits 8a51d5d, fix (see L4) — endpoints `GET /api/personal/examenes`, `GET /api/personal/solicitantes`, `POST /api/personal/solicitantes/carga` + tests. Risk: item 2.
- [x] T2 (S1-S4 frontend) — inline — commit 29aa6bf — Panel tabs Exámenes / Solicitantes.
- [ ] T3 (S5-S6) — inline — `POST /api/personal/solicitantes/{folio}/clave` + estado filter + regenerate button + grid layout. Risk: item 2.

## Log

- L1 (2026-10-20): "Okay con ODD integraremos mejos la parte de administrador, se elimina la parte de calificaciones, esa se integra en examenes y cotiene un buscador y filtros por idioma igual para profesores, en la parte de solicitantes no exite la parte de cargar el excel, ni la tabla de los solicitantes, ni el excel con lo que pedi que se genera el token de acceso apra los solicitantes y te deja descargar ese excel"
- L2: Explored: Panel.tsx tabs only render "próximamente"; no staff data endpoints exist. Upload reuses `procesar`/`generar_excel_salida`. Raw body upload avoids adding python-multipart.
- L3: RED observed (5 new API tests, 404). GREEN: backend suite 112 passed; frontend lint + build clean.
- L4: Independent verifier (item 2): S1/S2 PASS; S3/S4 blocker — an invalid Correo made the sustentantes validator fail mid-upload (500, earlier rows registered with keys lost). Fixed: `procesar` rejects it as a row error "Correo inválido" using shared `PATRON_CORREO`; test added. Suite 113 passed (`test_incidencias_acotadas` intermittent ERROR, passes alone, unrelated). Advisory left open: 5 MB check runs after reading the body; a Caddy `request_body max_size` would cap it (deploy config, not changed).
- L5: RDD assess high (item 2 escalated); native review consent: declined for this candidate (7cd45e4..4cce065). Push/deploy left to the user.
- L6 (2026-10-20): "Excelente, tambien ahi mismo estará la tabla de usuarios y sus claves de acceso para poder ver los activos recuerda usar grid layout para tener todo mejor organizado"
- L7: Plaintext keys don't exist in the DB (hash-only rule). User chose "Regenerar bajo demanda (Recommended)" over storing encrypted keys or status-only.
