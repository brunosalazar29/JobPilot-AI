import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def validate_resume_file(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX resumes are supported",
        )
    return suffix


def save_upload_file(upload: UploadFile, user_id: int) -> Path:
    suffix = validate_resume_file(upload)
    upload_root = Path(settings.upload_dir)
    user_dir = upload_root / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    destination = user_dir / f"{uuid4().hex}{suffix}"
    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return destination
