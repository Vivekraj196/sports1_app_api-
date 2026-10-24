from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    PlayerProfile,
    PlayerStatistic,
    Team,
    TeamStatistic,
)
from app.schemas import (
    PlayerStatisticResponse,
    TeamStatisticResponse,
)

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("/players/{player_id}", response_model=list[PlayerStatisticResponse])
def get_player_statistics(
    player_id: int,
    db: Session = Depends(get_db),
):
    # Confirm that this player exists.
    player = db.query(PlayerProfile).filter(
        PlayerProfile.id == player_id
    ).first()

    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    # A player can have separate statistics for different sports.
    return (
        db.query(PlayerStatistic)
        .filter(PlayerStatistic.player_id == player_id)
        .order_by(PlayerStatistic.sport_id)
        .all()
    )


@router.get("/teams/{team_id}", response_model=TeamStatisticResponse)
def get_team_statistics(
    team_id: int,
    db: Session = Depends(get_db),
):
    # Confirm that the team exists.
    team = db.query(Team).filter(Team.id == team_id).first()

    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    statistics = db.query(TeamStatistic).filter(
        TeamStatistic.team_id == team_id
    ).first()

    if statistics is None:
        raise HTTPException(
            status_code=404,
            detail="Statistics are not available for this team yet",
        )

    return statistics