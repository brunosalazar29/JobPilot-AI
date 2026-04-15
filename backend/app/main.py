from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, ensure_database_exists
from app.core.schema_upgrades import ensure_profile_detection_columns
from app.models import Base
from app.routers import applications, auth, documents, health, jobs, matches, profile, tasks
from app.utils.seed import seed_demo_data


app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(documents.router)
app.include_router(jobs.router)
app.include_router(matches.router)
app.include_router(applications.router)
app.include_router(tasks.router)


@app.on_event("startup")
def on_startup() -> None:
    ensure_database_exists()
    if settings.app_auto_create_tables:
        Base.metadata.create_all(bind=engine)
        ensure_profile_detection_columns()
    if settings.seed_demo_data:
        seed_demo_data()
