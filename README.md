# Web-App-IdiomasUG

Web app para la realización de exámenes de regularización del nivel de diferentes idiomas, del Departamento de Idiomas de la Universidad de Guanajuato, Campus León

## Project structure

```
frontend/             React + TypeScript app (Vite), served by Caddy
  index.html          Vite entry
  src/                api client, context, pages (one per screen), components, hooks, assets
backend/              Python: MongoDB data layer and applicant loading scripts
  db/                 MongoDB connection, schemas, indexes and operations
  datos/              Seed data (languages, exams)
  scripts/            sembrar, demo, cargar_solicitantes(_db)
  tests/              pytest suite and fixtures
```

## Run the frontend

Requires Node 22. The dev server proxies `/api` to the backend on `http://localhost:8000`:

```sh
cd frontend
npm install
npm run dev        # then open http://localhost:5173
npm run build      # production build into frontend/dist
```

## Base de datos

La plataforma usa MongoDB. La capa de datos está en [`backend/db/`](backend/db/) y su
guía de instalación, modelo de datos y uso está en [`backend/db/README.md`](backend/db/README.md).

```bash
cd backend
pip install -r requirements.txt -r requirements-db.txt
cp .env.example .env          # y llena MONGODB_URI y CLAVE_PEPPER
python scripts/demo.py        # recorrido completo sobre una base de prueba
python -m pytest tests -v
```
