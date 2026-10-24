
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    PlayerStatistic,
    PlayerProfile,
    TeamStatistic,
    Team,
    Sport,
)

router = APIRouter(prefix="/rankings", tags=["Rankings"])


# Player leaderboard:
# Higher wins rank first. If wins are equal, higher points rank first.
@router.get("/players")
def get_player_leaderboard(
    sport_id: int | None = Query(default=None, gt=0),
    city: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(PlayerStatistic, PlayerProfile, Sport)
        .join(
            PlayerProfile,
            PlayerProfile.id == PlayerStatistic.player_id,
        )
        .join(Sport, Sport.id == PlayerStatistic.sport_id)
    )

    if sport_id is not None:
        query = query.filter(PlayerStatistic.sport_id == sport_id)

    if city:
        query = query.filter(PlayerProfile.city.ilike(city.strip()))

    rows = (
        query.order_by(
            PlayerStatistic.wins.desc(),
            PlayerStatistic.points_scored.desc(),
            PlayerStatistic.matches_played.asc(),
            PlayerStatistic.player_id.asc(),
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "rank": index,
            "player_id": stats.player_id,
            "player_name": profile.display_name,
            "sport_id": stats.sport_id,
            "sport_name": sport.name,
            "city": profile.city,
            "matches_played": stats.matches_played,
            "wins": stats.wins,
            "losses": stats.losses,
            "points_scored": stats.points_scored,
        }
        for index, (stats, profile, sport) in enumerate(rows, start=1)
    ]


# Team leaderboard:
# Higher wins rank first. If wins are equal, higher points rank first.
@router.get("/teams")
def get_team_leaderboard(
    sport_id: int | None = Query(default=None, gt=0),
    city: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(TeamStatistic, Team, Sport)
        .join(Team, Team.id == TeamStatistic.team_id)
        .join(Sport, Sport.id == Team.sport_id)
    )

    if sport_id is not None:
        query = query.filter(Team.sport_id == sport_id)

    if city:
        query = query.filter(Team.city.ilike(city.strip()))

    rows = (
        query.order_by(
            TeamStatistic.wins.desc(),
            TeamStatistic.points_scored.desc(),
            TeamStatistic.matches_played.asc(),
            TeamStatistic.team_id.asc(),
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "rank": index,
            "team_id": stats.team_id,
            "team_name": team.name,
            "sport_id": team.sport_id,
            "sport_name": sport.name,
            "city": team.city,
            "matches_played": stats.matches_played,
            "wins": stats.wins,
            "losses": stats.losses,
            "points_scored": stats.points_scored,
        }
        for index, (stats, team, sport) in enumerate(rows, start=1)
    ]
