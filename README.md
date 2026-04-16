# JobPilot AI

JobPilot AI es una base web modular para gestionar postulaciones laborales con automatización semi-asistida. El CV es la fuente principal del perfil del candidato: al cargarlo se analiza automáticamente, se detectan datos clave y solo se piden campos faltantes opcionales cuando ayudan al matching o a completar formularios.

## Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: FastAPI, Python 3.11+, SQLAlchemy, Pydantic
- Jobs: Celery + Redis
- Base de datos: Microsoft SQL Server con `mssql+pyodbc`
- Automatización web: Playwright para Python
- Parsing: PyMuPDF, pdfplumber y python-docx
- Infra local: Docker Compose

No se usa PostgreSQL.

## Estructura

```text
frontend/                 Next.js app router
backend/app/core/          configuración, DB, seguridad, Celery
backend/app/models/        modelos SQLAlchemy
backend/app/schemas/       schemas Pydantic
backend/app/routers/       rutas FastAPI
backend/app/services/      parsing, matching, generación, búsqueda, automatización
backend/app/tasks/         tareas Celery
backend/alembic/           migraciones SQL Server
docker-compose.yml         frontend, backend, worker, redis, sqlserver
.env.example               variables de entorno
```

## Levantar con Docker

1. Copia variables si quieres ajustar valores:

```bash
cp .env.example .env
```

2. Construye y levanta todo:

```bash
docker compose up --build
```

3. Abre:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8011
- Docs Swagger: http://localhost:8011/docs
- Health: http://localhost:8011/health

El backend crea la base `jobpilot_ai` automáticamente si no existe y, por defecto, crea tablas en desarrollo con SQLAlchemy. También hay una migración Alembic inicial.

## Usuario demo

Puedes crear usuarios desde la pantalla de registro. Si quieres datos demo al iniciar, configura:

```env
SEED_DEMO_DATA=true
```

Credenciales demo:

```text
email: demo@jobpilot.ai
password: DemoPass123
```

## Backend local

Requisitos:

- Python 3.11+
- ODBC Driver 18 for SQL Server
- SQL Server accesible
- Redis accesible

Instalación:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

Ejecutar API:

```bash
uvicorn app.main:app --reload
```

Ejecutar worker:

```bash
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

Seeds:

```bash
python -m app.utils.seed
```

Migraciones:

```bash
alembic upgrade head
```

## Frontend local

```bash
cd frontend
npm install
npm run dev
```

Configura `NEXT_PUBLIC_API_URL=http://localhost:8011` si no usas Docker.

## Endpoints principales

- `POST /auth/register`
- `POST /auth/login`
- `GET|POST|PUT|DELETE /profile`
- `POST /documents/upload`
- `POST /documents/{resume_id}/parse`
- `POST /documents/generate`
- `GET /jobs`
- `POST /jobs/search`
- `POST /matches/run`
- `GET /matches`
- `POST /applications`
- `POST /applications/{application_id}/prepare`
- `PATCH /applications/{application_id}/status`
- `GET /tasks`

## Flujo sugerido

1. Registra o inicia sesión.
2. Sube un CV en Documentos; el parsing se encola automáticamente.
3. Revisa Perfil detectado para ver datos extraídos, inferidos y faltantes.
4. Completa solo los faltantes que quieras mejorar, como modalidad o salario.
5. Ejecuta búsqueda de vacantes.
6. Ejecuta matching.
7. Abre el detalle de una vacante, genera documentos y prepara aplicación.
8. Revisa respuestas, logs y estado antes de marcar la postulación como aplicada.

## Notas de diseño

- El servicio de búsqueda usa un adapter mock desacoplado para reemplazarlo por conectores reales.
- El perfil guarda origen por campo: `cv`, `inferred` o `user_input`.
- La generación usa plantillas desacopladas para permitir integrar LLM después.
- Playwright intenta completar campos comunes y adjuntar CV, pero nunca fuerza el envío final.
- `Application.status` soporta `pending`, `running`, `ready_for_review`, `applied`, `failed`, `rejected` y `needs_manual_action`.
- `TaskRun` y `ActivityLog` registran trazabilidad básica de tareas y actividad.
