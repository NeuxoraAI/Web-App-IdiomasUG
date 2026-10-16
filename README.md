# Web-App-IdiomasUG

Web app para la realización de exámenes de regularización del nivel de diferentes idiomas, del Departamento de Idiomas de la Universidad de Guanajuato, Campus León

## Project structure

```
frontend/             Static app (HTML/CSS/ES modules), served by nginx
  index.html          App shell: markup for all screens
  css/                Design tokens, base styles, one stylesheet per screen
  js/                 Entry point, config, state, data, helpers, screens
  assets/             Images used by the app
backend/              Python: MongoDB data layer and applicant loading scripts
  db/                 MongoDB connection, schemas, indexes and operations
  datos/              Seed data (languages, exams)
  scripts/            sembrar, demo, cargar_solicitantes(_db)
  tests/              pytest suite and fixtures
```

## Run the frontend

The app is a static site using ES modules, so it must be served over HTTP
(opening `index.html` directly with `file://` will not load the modules):

```sh
cd frontend
python3 -m http.server 8000
# then open http://localhost:8000
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
