from sqlalchemy import select

from app.core.database import SessionLocal, engine, ensure_database_exists
from app.core.security import get_password_hash
from app.models import Base, Job, Profile, User
from app.schemas.job import JobFilter
from app.services.job_search import MockJobSearchAdapter, upsert_jobs


def seed_demo_data() -> None:
    ensure_database_exists()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "demo@jobpilot.ai"))
        if user is None:
            user = User(email="demo@jobpilot.ai", hashed_password=get_password_hash("DemoPass123"))
            db.add(user)
            db.flush()
            profile = Profile(
                user_id=user.id,
                full_name="Demo User",
                email=user.email,
                phone="+51 999 999 999",
                location="Lima, Peru",
                linkedin_url="https://linkedin.com/in/demo",
                github_url="https://github.com/demo",
                portfolio_url="https://demo.example.com",
                experience_summary="Mid software engineer focused on Python, FastAPI, React and SQL Server.",
                skills=["python", "fastapi", "typescript", "react", "sql server", "docker", "celery"],
                languages=["english", "spanish"],
                preferred_modality="remote",
                salary_expectation=4500,
                salary_currency="USD",
            )
            db.add(profile)
            db.commit()

        existing_jobs = db.scalar(select(Job.id))
        if existing_jobs is None:
            adapter = MockJobSearchAdapter()
            upsert_jobs(
                db,
                adapter.search(
                    JobFilter(
                        role="Full Stack Engineer",
                        seniority="mid",
                        location="Remote LATAM",
                        remote=True,
                        salary_min=4000,
                        technologies=["python", "fastapi", "typescript", "react", "sql server"],
                        language="english",
                    )
                ),
            )
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
