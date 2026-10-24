from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status,Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.auth import get_current_user
from app.database import get_db
from app.models import Match, PlayerProfile, Sport, Team, User,MatchParticipant,User
from app.schemas import MatchCreate, MatchResponse

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.post("/", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
def create_match(
    match_data: MatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Player profile not found")

    sport = db.query(Sport).filter(Sport.id == match_data.sport_id).first()
    if sport is None:
        raise HTTPException(status_code=404, detail="Sport not found")

    for team_id in (match_data.team1_id, match_data.team2_id):
        if team_id is not None:
            team = db.query(Team).filter(Team.id == team_id).first()
            if team is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Team {team_id} not found",
                )
            if team.sport_id != match_data.sport_id:
                raise HTTPException(
                    status_code=400,
                    detail="Both teams must belong to the selected sport",
                )

    if (
        match_data.team1_id is not None
        and match_data.team1_id == match_data.team2_id
    ):
        raise HTTPException(
            status_code=400,
            detail="A team cannot play against itself",
        )

    scheduled_at = match_data.scheduled_at
    if scheduled_at.tzinfo is None:
        if scheduled_at <= datetime.now():
            raise HTTPException(
                status_code=400,
                detail="Schedule the match for a future date and time",
            )
    elif scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Schedule the match for a future date and time",
        )

    match = Match(
        sport_id=match_data.sport_id,
        created_by_player_id=profile.id,
        team1_id=match_data.team1_id,
        team2_id=match_data.team2_id,
        title=match_data.title,
        location_name=match_data.location_name,
        city=match_data.city,
        state=match_data.state,
        scheduled_at=scheduled_at,
        status="Scheduled",
    )

    db.add(match)
    db.commit()
    db.refresh(match)
    return match



@router.get("/", response_model=list[MatchResponse])
def get_matches(
    sport_id: int | None = Query(default=None, gt=0),
    city: str | None = None,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Match)

    if sport_id is not None:
        query = query.filter(Match.sport_id == sport_id)

    if city:
        query = query.filter(Match.city.ilike(f"%{city.strip()}%"))

    if status:
        allowed_statuses = {
            "Scheduled", "Live", "Completed", "Cancelled"
        }
        if status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid status",
            )
        query = query.filter(Match.status == status)

    return (
        query.order_by(Match.scheduled_at.asc())
        .limit(limit)
        .all()
    )


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.patch("/{match_id}/status", response_model=MatchResponse)
def update_match_status(
    match_id: int,
    new_status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed_statuses = {"Scheduled", "Live", "Completed", "Cancelled"}

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {', '.join(sorted(allowed_statuses))}",
        )

    profile = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.user_id == current_user.id)
        .first()
    )
    match = db.query(Match).filter(Match.id == match_id).first()

    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    if profile is None or match.created_by_player_id != profile.id:
        raise HTTPException(
            status_code=403,
            detail="Only the match creator can update its status",
        )

    match.status = new_status
    db.commit()
    db.refresh(match)
    return match

@router.get("/history/me", response_model=list[MatchResponse])
def get_my_match_history(
    sport_id: int | None = Query(default=None, gt=0),
    city: str | None = None,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.user_id == current_user.id)
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Player profile not found",
        )

    participated_match_ids = (
        db.query(MatchParticipant.match_id)
        .filter(MatchParticipant.player_id == profile.id)
        .subquery()
    )

    query = db.query(Match).filter(
        or_(
            Match.created_by_player_id == profile.id,
            Match.id.in_(participated_match_ids),
        )
    )

    if sport_id is not None:
        query = query.filter(Match.sport_id == sport_id)

    if city:
        query = query.filter(Match.city.ilike(f"%{city.strip()}%"))

    if status:
        allowed_statuses = {
            "Scheduled", "Live", "Completed", "Cancelled"
        }
        if status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid status",
            )
        query = query.filter(Match.status == status)

    return (
        query.order_by(Match.scheduled_at.desc())
        .limit(limit)
        .all()
    )