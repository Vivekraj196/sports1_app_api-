
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Match,
    MatchParticipant,
    PlayerProfile,
    ScoringEvent,
    Team,
    User,
)

router = APIRouter(prefix="/matches", tags=["Scoring"])


class ScoreCreate(BaseModel):
    player_id: int = Field(gt=0)
    team_id: int = Field(gt=0)
    points: int = Field(ge=0, le=100)
    event_type: str = Field(default="Points", min_length=1, max_length=50)


@router.post("/{match_id}/scores")
def record_score(
    match_id: int,
    data: ScoreCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()

    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.status != "Live":
        raise HTTPException(
            status_code=400,
            detail="Scores can only be recorded for live matches",
        )

    profile = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.user_id == current_user.id)
        .first()
    )

    if profile is None:
        raise HTTPException(status_code=404, detail="Player profile not found")

    # Only the match creator or an accepted participant can record scores.
    is_creator = match.created_by_player_id == profile.id

    participation = (
        db.query(MatchParticipant)
        .filter(
            MatchParticipant.match_id == match_id,
            MatchParticipant.player_id == profile.id,
            MatchParticipant.invitation_status == "Accepted",
        )
        .first()
    )

    if not is_creator and participation is None:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to record scores for this match",
        )

    if data.team_id not in (match.team1_id, match.team2_id):
        raise HTTPException(
            status_code=400,
            detail="Team must belong to this match",
        )

    target_player = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.id == data.player_id)
        .first()
    )

    if target_player is None:
        raise HTTPException(status_code=404, detail="Scoring player not found")

    # The scoring player must be an accepted participant assigned to this team.
    target_participation = (
        db.query(MatchParticipant)
        .filter(
            MatchParticipant.match_id == match_id,
            MatchParticipant.player_id == data.player_id,
            MatchParticipant.invitation_status == "Accepted",
            MatchParticipant.team_id == data.team_id,
        )
        .first()
    )

    if target_participation is None:
        raise HTTPException(
            status_code=400,
            detail="Scoring player must be an accepted participant on that team",
        )

    event = ScoringEvent(
        match_id=match_id,
        recorded_by_player_id=profile.id,
        player_id=data.player_id,
        team_id=data.team_id,
        points=data.points,
        event_type=data.event_type,
        created_at=datetime.now(timezone.utc),
    )

    try:
        db.add(event)
        db.commit()
        db.refresh(event)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save score")

    return {
        "message": "Score recorded",
        "event_id": event.id,
        "match_id": event.match_id,
        "player_id": event.player_id,
        "team_id": event.team_id,
        "points": event.points,
        "event_type": event.event_type,
    }


@router.get("/{match_id}/scores")
def get_live_score(
    match_id: int,
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()

    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    events = (
        db.query(ScoringEvent)
        .filter(ScoringEvent.match_id == match_id)
        .order_by(ScoringEvent.created_at.asc(), ScoringEvent.id.asc())
        .all()
    )

    team1_score = sum(
        event.points for event in events if event.team_id == match.team1_id
    )
    team2_score = sum(
        event.points for event in events if event.team_id == match.team2_id
    )

    return {
        "match_id": match_id,
        "match_status": match.status,
        "team1_id": match.team1_id,
        "team1_score": team1_score,
        "team2_id": match.team2_id,
        "team2_score": team2_score,
        "events": [
            {
                "event_id": event.id,
                "player_id": event.player_id,
                "team_id": event.team_id,
                "points": event.points,
                "event_type": event.event_type,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }

