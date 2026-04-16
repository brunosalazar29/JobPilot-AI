from datetime import UTC, datetime

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Application, Job, ParsedResume, Resume, TaskRun
from app.services.cv_parser import parse_resume_file
from app.services.generation import generate_application_responses
from app.services.job_search import build_filters_from_profile, configured_adapters, search_jobs
from app.services.matching import run_matching_for_user
from app.services.profile_detection import apply_cv_profile
from app.services.search_run import mark_search_completed, mark_search_failed, mark_search_stage, should_continue_search
from app.services.task_dispatch import dispatch_task
from app.services.task_logger import (
    append_task_log,
    create_task_run,
    log_activity,
    mark_task_failed,
    mark_task_running,
    mark_task_success,
)
from app.tasks.automation_tasks import prepare_application_form_task


@celery_app.task(name="jobpilot.cv_pipeline")
def cv_pipeline_task(task_run_id: int, resume_id: int) -> dict:
    db = SessionLocal()
    try:
        task_run = db.get(TaskRun, task_run_id)
        resume = db.get(Resume, resume_id)
        if task_run is None or resume is None:
            raise ValueError("Task run or resume not found")
        if not should_continue_search(db, resume.user_id):
            append_task_log(db, task_run, "Search run is not active")
            mark_task_success(db, task_run, result={"resume_id": resume_id, "stopped": True})
            return {"resume_id": resume_id, "stopped": True}

        mark_task_running(db, task_run, progress=5)
        mark_search_stage(db, resume.user_id, "Analizando CV", "Analizando CV y actualizando tu perfil.")
        if resume.status == "parsed" and resume.parsed_resume is not None:
            parsed = resume.parsed_resume
            parsed_data = {
                "raw_text": parsed.raw_text or "",
                "work_experience": parsed.work_experience or [],
                "skills": parsed.skills or [],
                "education": parsed.education or [],
                "certifications": parsed.certifications or [],
                "languages": parsed.languages or [],
                "metadata": parsed.extra_data or {},
            }
            append_task_log(db, task_run, "parse_cv skipped: using stored parsed CV", data={"resume_id": resume.id})
        else:
            append_task_log(db, task_run, "parse_cv started", data={"resume_id": resume.id})
            resume.status = "parsing"
            db.add(resume)
            db.commit()

            parsed_data = parse_resume_file(resume.storage_path)
            parsed = resume.parsed_resume or ParsedResume(resume_id=resume.id)
            parsed.raw_text = parsed_data["raw_text"]
            parsed.work_experience = parsed_data["work_experience"]
            parsed.skills = parsed_data["skills"]
            parsed.education = parsed_data["education"]
            parsed.certifications = parsed_data["certifications"]
            parsed.languages = parsed_data["languages"]
            parsed.extra_data = parsed_data["metadata"]
            db.add(parsed)
            db.flush()

            resume.status = "parsed"
            resume.parsed_at = datetime.now(UTC)
            resume.error_message = None
            db.add(resume)
            db.commit()

        append_task_log(db, task_run, "infer_profile started")
        profile = apply_cv_profile(db, resume.user_id, parsed, parsed_data)
        if not should_continue_search(db, resume.user_id):
            append_task_log(db, task_run, "Search run stopped after profile detection")
            mark_task_success(db, task_run, result={"resume_id": resume.id, "stopped": True})
            return {"resume_id": resume.id, "stopped": True}

        adapters = configured_adapters()
        mark_search_stage(db, resume.user_id, "Buscando vacantes", "Buscando vacantes relacionadas con tu perfil.")
        append_task_log(
            db,
            task_run,
            "collect_jobs started" if adapters else "collect_jobs skipped: no real job sources configured",
            data={"sources": [adapter.source_name for adapter in adapters]},
        )
        filters = build_filters_from_profile(profile)
        jobs = search_jobs(db, filters, profile=profile) if adapters else []

        if not should_continue_search(db, resume.user_id):
            append_task_log(db, task_run, "Search run stopped after job collection")
            mark_task_success(db, task_run, result={"resume_id": resume.id, "stopped": True, "jobs_collected": len(jobs)})
            return {"resume_id": resume.id, "stopped": True, "jobs_collected": len(jobs)}

        mark_search_stage(db, resume.user_id, "Evaluando compatibilidad", "Comparando tu CV con las vacantes encontradas.")
        append_task_log(db, task_run, "match_jobs started", data={"job_count": len(jobs)})
        matches = run_matching_for_user(
            db,
            user_id=resume.user_id,
            resume_id=resume.id,
            job_ids=[job.id for job in jobs],
        ) if jobs else []

        if not should_continue_search(db, resume.user_id):
            append_task_log(db, task_run, "Search run stopped after matching")
            mark_task_success(db, task_run, result={"resume_id": resume.id, "stopped": True, "matches_created": len(matches)})
            return {"resume_id": resume.id, "stopped": True, "matches_created": len(matches)}

        mark_search_stage(db, resume.user_id, "Armando cola", "Creando la cola de postulaciones compatibles.")
        append_task_log(
            db,
            task_run,
            "create_queue_items started",
            data={"match_count": len(matches), "threshold": settings.application_match_threshold},
        )
        created_applications = []
        tracked_applications = 0
        for match in matches:
            if match.score < settings.application_match_threshold:
                continue
            job = db.get(Job, match.job_id)
            if job is None:
                continue
            existing = db.scalar(
                select(Application).where(Application.user_id == resume.user_id, Application.job_id == job.id)
            )
            if existing is not None:
                if existing.status not in {"applied", "cancelled"}:
                    tracked_applications += 1
                    existing.score = match.score
                    existing.resume_id = resume.id
                    existing.company = job.company
                    existing.position = job.title
                    existing.url = job.url
                if existing.status in {"found", "matched", "pending", "queued"}:
                    existing.status = "matched"
                    db.add(existing)
                    created_applications.append(existing)
                else:
                    db.add(existing)
                continue
            application = Application(
                user_id=resume.user_id,
                job_id=job.id,
                resume_id=resume.id,
                company=job.company,
                position=job.title,
                url=job.url,
                score=match.score,
                status="matched",
                generated_responses=generate_application_responses(profile, job, parsed),
                logs=[
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "level": "info",
                        "message": "Queue item created from CV pipeline",
                        "score": match.score,
                    }
                ],
            )
            db.add(application)
            created_applications.append(application)

        db.commit()
        for application in created_applications:
            db.refresh(application)

        auto_apply_tasks = 0
        if settings.auto_apply_enabled:
            mark_search_stage(db, resume.user_id, "Preparando postulaciones", "Encolando vacantes para intentar la postulación.")
            append_task_log(
                db,
                task_run,
                "auto_apply started",
                data={"queue_items": len(created_applications)},
            )
            for application in created_applications:
                if not should_continue_search(db, resume.user_id):
                    application.status = "cancelled"
                    application.logs = [
                        *(application.logs or []),
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "level": "warning",
                            "message": "Search run stopped by user",
                        },
                    ]
                    db.add(application)
                    continue
                if not application.url:
                    application.status = "needs_manual_action"
                    application.errors = "Missing job URL"
                    application.logs = [
                        *(application.logs or []),
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "level": "warning",
                            "message": "Queue item cannot be auto-applied because URL is missing",
                        },
                    ]
                    db.add(application)
                    continue
                application.status = "queued"
                application.logs = [
                    *(application.logs or []),
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "level": "info",
                        "message": "Queue item ready for auto-apply",
                        "url": application.url,
                    },
                ]
                db.add(application)
                apply_task_run = create_task_run(
                    db,
                    resume.user_id,
                    "prepare_application_form",
                    {"application_id": application.id, "auto_started": True},
                )
                dispatch_task(db, apply_task_run, prepare_application_form_task, apply_task_run.id, application.id)
                auto_apply_tasks += 1
            db.commit()

        result = {
            "resume_id": resume.id,
            "profile_completeness": profile.profile_completeness,
            "missing_fields": profile.missing_fields,
            "jobs_collected": len(jobs),
            "matches_created": len(matches),
            "queue_items_created": len(created_applications),
            "queue_items_tracked": tracked_applications,
            "auto_apply_tasks": auto_apply_tasks,
            "sources": [adapter.source_name for adapter in adapters],
        }
        if auto_apply_tasks:
            mark_search_stage(
                db,
                resume.user_id,
                "Procesando cola",
                f"Se iniciaron {auto_apply_tasks} intentos de postulacion en segundo plano.",
            )
        elif created_applications:
            mark_search_completed(db, resume.user_id, "La cola fue creada y quedo lista para revision.")
        elif tracked_applications:
            mark_search_completed(
                db,
                resume.user_id,
                f"Se encontraron {tracked_applications} vacantes ya registradas que siguen en seguimiento.",
            )
        else:
            mark_search_completed(
                db,
                resume.user_id,
                "No se encontraron vacantes en Peru/Lima ni vacantes remotas internacionales para esta corrida.",
            )
        log_activity(db, resume.user_id, "resume", "cv_pipeline_completed", resume.original_filename, resume.id, result)
        mark_task_success(db, task_run, result=result)
        return result
    except Exception as exc:
        db.rollback()
        task_run = db.get(TaskRun, task_run_id)
        resume = db.get(Resume, resume_id)
        if resume is not None:
            resume.status = "failed"
            resume.error_message = str(exc)
            db.add(resume)
            db.commit()
        if task_run is not None:
            mark_task_failed(db, task_run, str(exc))
        if resume is not None:
            mark_search_failed(db, resume.user_id, str(exc))
        raise
    finally:
        db.close()
