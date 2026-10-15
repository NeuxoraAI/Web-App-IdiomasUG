# Base de datos NoSQL (MongoDB) · Web-App-IdiomasUG

Capa de base de datos para la plataforma de exámenes de ubicación **EXAUBI** del
Centro de Servicios de Lenguas Extranjeras (UG Campus León).

Todos los comandos se ejecutan desde la **raíz del repositorio**. Reutiliza
`scripts/cargar_solicitantes.py` (validación de CURP y formato de clave) y el
Excel de prueba `tests/fixtures/alumnos_solicitantes.xlsx`.

```
db/
  conexion.py            ← conexión a MongoDB (lee .env)
  esquemas.py            ← reglas de validación de cada colección ($jsonSchema)
  crear_base_datos.py    ← crea colecciones, validadores e índices
  calificacion.py        ← califica en el servidor (misma lógica que questions.js)
  operaciones.py         ← cada paso de la plataforma: login, iniciar, responder, terminar…
scripts/
  sembrar.py             ← prepara la base: colecciones + idiomas + exámenes
  cargar_solicitantes_db.py  ← Excel → base de datos + Excel con claves y folios
  demo.py                ← recorrido completo sobre una base de prueba
datos/
  idiomas.json           ← catálogo de idiomas
  examenes/EXAUBI-2026B-en-v1.json  ← el examen del prototipo (rama desing)
tests/test_base_datos.py ← 57 pruebas contra un MongoDB real
requirements-db.txt
.env.example
```

---

## 1. Instalar MongoDB (elige una opción)

**A. MongoDB Atlas (en la nube, recomendado para el equipo).** Crea una cuenta en
[mongodb.com/atlas](https://www.mongodb.com/atlas), un clúster gratuito (*Free*),
un usuario de base de datos y, en *Network Access*, permite tu IP. En
*Connect → Drivers → Python* copia la cadena `mongodb+srv://…`.

**B. En tu computadora.** Instala *MongoDB Community Server* (en Windows el
instalador incluye *MongoDB Compass*, la interfaz gráfica), o con Docker:

```bash
docker run -d --name mongo -p 27017:27017 -v mongo-datos:/data/db mongo:8
```

En ambos casos instala también **MongoDB Compass** para ver los documentos.

## 2. Preparar Python (3.10 o superior)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt -r requirements-db.txt
copy .env.example .env          # Linux/Mac: cp .env.example .env
```

Edita `.env`: pon tu `MONGODB_URI` y genera un `CLAVE_PEPPER` con
`python -c "import secrets; print(secrets.token_urlsafe(32))"`.

## 3. Ver todo funcionando (demo)

```bash
python scripts/demo.py
```

Crea la base `idiomas_ug_demo`, carga el Excel de prueba y simula a un
sustentante presentando el examen de inglés. En cada paso imprime cómo quedan
los documentos. Después ábrela en Compass y explórala.

## 4. Crear la base real

```bash
python scripts/sembrar.py                                   # colecciones, índices, idiomas, exámenes
python scripts/sembrar.py --publicar EXAUBI-2026B-fr-v1     # publicar un examen
```

Se puede ejecutar cuantas veces se quiera. Un examen que ya tiene intentos
**no se sobrescribe**: hay que crear una versión nueva (`…-v2`).

## 5. Cargar solicitantes

```bash
python scripts/cargar_solicitantes_db.py solicitantes.xlsx --convocatoria 2026B -o codigos_acceso.xlsx
```

Mismas validaciones y mensajes que `cargar_solicitantes.py`, más:
los idiomas válidos salen de la colección `idiomas`; cada renglón válido queda
en la base con un folio consecutivo (`EXAUBI-2026B-0001`); volver a cargar el
mismo archivo no duplica (*"Ya registrado en la base"*). Columna opcional `Correo`.

> El Excel de salida es la **única** copia de las claves en texto plano: la
> base solo guarda su *hash*. Si alguien pierde su clave, se usa
> `operaciones.regenerar_clave`.

## 6. Pruebas

```bash
python -m pytest tests -v
```

Necesitan un MongoDB encendido (`MONGODB_URI`); crean una base temporal por
prueba y la borran. Si no hay servidor, se omiten.

---

## Modelo de datos

| Colección | Un documento es… | `_id` | Reglas que impone el servidor |
|---|---|---|---|
| `idiomas` | un idioma del catálogo | `"fr"` | nombre único |
| `examenes` | una **versión** de examen, con sus preguntas **embebidas** | `"EXAUBI-2026B-en-v1"` | un solo examen *publicado* por idioma y convocatoria |
| `sustentantes` | una persona | ObjectId | CURP única y con formato válido |
| `asignaciones` | "esta persona presenta este idioma en esta convocatoria": folio + hash de la clave | ObjectId | CURP + convocatoria + idioma única; clave única; folio único |
| `intentos` | el examen en curso o terminado, con respuestas y resultado | ObjectId | **un solo intento por asignación** |
| `contadores` | el último folio usado por convocatoria | `"folio-2026B"` | — |

Ejemplo de `intentos` ya calificado:

```js
{
  _id: ObjectId("…"),
  asignacion_id: ObjectId("…"),
  examen_id: "EXAUBI-2026B-en-v1",
  preguntas_ids: ["q01", "q02", …, "q10"],
  estado: "enviado",                       // en_curso | enviado | tiempo_agotado
  iniciado_en: ISODate("2026-10-08T16:00:00Z"),
  expira_en:   ISODate("2026-10-08T16:35:00Z"),   // el cronómetro vive en el servidor
  finalizado_en: ISODate("2026-10-08T16:21:40Z"),
  respuestas: {
    q01: { valor: 3, en: ISODate("…") },
    q05: { valor: [0, 1], en: ISODate("…") },
    q08: { valor: "since", en: ISODate("…") }
  },
  incidencias: [ { tipo: "copia", en: ISODate("…") } ],
  resultado: {
    aciertos: 7, calificables: 8, mcer: "B2", nivel: "Nivel 3 · Intermedio alto",
    por_parte: [ { parte: 1, nombre: "Parte 1 · Básico", aciertos: 3, total: 4, porcentaje: 75 }, … ],
    pendientes_revision: ["q10"], segundos_usados: 1300
  }
}
```

## Cómo lo usa el backend

El backend (FastAPI, Flask…) aún no existe; cada ruta solo llama una función de
`db/operaciones.py`:

| Pantalla / acción | Ruta sugerida | Función |
|---|---|---|
| Login (CURP + código) | `POST /api/login` | `autenticar` |
| "Iniciar examen" | `POST /api/intento` | `iniciar_intento` |
| Cargar preguntas | `GET /api/intento` | `examen_para_sustentante` |
| Cada respuesta | `PUT /api/intento/respuestas/{q}` | `guardar_respuesta` |
| Guardia anti-IA | `POST /api/intento/incidencias` | `registrar_incidencia` |
| "Terminar" / fin del tiempo | `POST /api/intento/terminar` | `finalizar_intento` |
| Certificado | `GET /api/certificado` | `datos_certificado` |
| Tarea cada minuto | — | `cerrar_intentos_vencidos` |
| Centro | `/api/admin/…` | `resumen_convocatoria`, `regenerar_clave`, `publicar_examen` |

Después del login el servidor debe guardar el `asignacion_id` en una sesión
(cookie firmada o JWT) y **nunca** aceptar ese id desde el navegador. Conviene
limitar los intentos de login por IP.

## Cambios que necesitará el frontend (rama `desing`)

1. **Quitar las respuestas correctas de `js/data/questions.js`** (campo `c`) y
   dejar de calcular el resultado en el navegador: hoy cualquiera puede verlas
   con F12. Las preguntas y el resultado vienen del servidor.
2. Preguntas tipo *match*: `pairs` (que contiene la respuesta) pasa a ser
   `izquierdas` + `derechas`.
3. Las respuestas se identifican por id de pregunta (`"q01"`), no por posición.
4. El cronómetro arranca con `segundos_restantes` que manda el servidor.
5. **Folio:** `state.js` lo construye a partir del código de acceso, así que el
   certificado impreso mostraría el código. Usar el `folio` de la asignación.
6. El perfil tiene datos fijos (nombre, idioma, correo, fecha límite): salen de
   la asignación y del examen.

## Decisiones pendientes para el equipo

- **Idiomas:** el Enum de `develop` no incluye Inglés ni Portugués, pero el
  diseño muestra "EXAUBI · Inglés" y ambos en la lista. En `datos/idiomas.json`
  quedaron como `activo: false`. Para activarlos basta cambiar un documento
  (ya no hay que tocar código): `db.idiomas.updateOne({_id: "en"}, {$set: {activo: true}})`.
- "Español" (Enum) vs "Español para extranjeros" (diseño).
- La pregunta con imagen (`q09`) no tiene respuesta correcta en el prototipo, y
  el texto breve (`q10`) queda en `pendientes_revision`: ¿quién lo revisa y si
  cuenta para el nivel?
- Agregar la columna `Correo` al Excel si los códigos se enviarán por correo.
- Usuarios y permisos del personal del Centro (aún no modelados).

## Consultas útiles (mongosh o la barra de filtros de Compass)

```js
db.asignaciones.find({ convocatoria: "2026B", estado: "pendiente" })        // quién no ha presentado
db.intentos.find({ "resultado.mcer": "B2" })                                  // por nivel
db.intentos.find({ "incidencias.tipo": "copia" }, { asignacion_id: 1 })       // quién intentó copiar
db.asignaciones.find({ curp: "RAHE030910HQTMRMA3" })                          // todo lo de una persona
db.asignaciones.getIndexes()                                                  // ver los índices
```
