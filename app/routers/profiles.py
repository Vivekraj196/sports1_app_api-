from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, PlayerProfile
from app.schemas import PlayerProfileResponse


router = APIRouter(prefix="/profile", tags=["Player Profile"])


@router.get("/me", response_model=PlayerProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the profile belonging to the authenticated user.
    A valid JWT token is required.
    """

    profile = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.user_id == current_user.id)
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player profile not found",
        )

    return profile