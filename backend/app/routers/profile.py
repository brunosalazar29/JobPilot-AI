from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Profile, User
from app.schemas.profile import DetectedProfileResponse, ProfileCreate, ProfileRead, ProfileUpdate
from app.services.profile_detection import (
    apply_user_profile_update,
    build_detected_profile,
    get_or_create_profile,
    refresh_profile_insights,
)
from app.services.task_logger import log_activity


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Profile:
    profile = get_or_create_profile(db, current_user.id)
    refresh_profile_insights(profile)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/detected", response_model=DetectedProfileResponse)
def get_detected_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return build_detected_profile(db, current_user.id)


@router.post("", response_model=ProfileRead, status_code=201)
def create_profile(
    payload: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = get_or_create_profile(db, current_user.id)
    profile = apply_user_profile_update(db, profile, payload.model_dump())
    log_activity(db, current_user.id, "profile", "upserted", "Profile created or updated", entity_id=profile.id)
    return profile


@router.put("", response_model=ProfileRead)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = get_or_create_profile(db, current_user.id)
    updates = payload.model_dump(exclude_unset=True)
    profile = apply_user_profile_update(db, profile, updates)
    log_activity(db, current_user.id, "profile", "completed_missing_fields", "Profile missing fields updated", entity_id=profile.id)
    return profile


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    if profile is not None:
        db.delete(profile)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
