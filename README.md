# Web-App-IdiomasUG
Web app para la realización de exámenes de regularización del nivel de diferentes idiomas, del Departamento de Idiomas de la Universidad de Guanajuato, Campus León

## Base de datos

La plataforma usa MongoDB. La capa de datos está en [`db/`](db/) y su guía de
instalación, modelo de datos y uso está en [`db/README.md`](db/README.md).

```bash
pip install -r requirements.txt -r requirements-db.txt
cp .env.example .env          # y llena MONGODB_URI y CLAVE_PEPPER
python scripts/demo.py        # recorrido completo sobre una base de prueba
python -m pytest tests -v
```
