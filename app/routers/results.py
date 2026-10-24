
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Match,
    MatchParticipant,
    MatchResult,
    PlayerProfile,
    PlayerStatistic,
    ScoringEvent,
    TeamStatistic,
    User,
)
from app.schemas import MatchResultResponse

router = APIRouter(prefix="/matches", tags=["Match Results"])


@router.post("/{match_id}/result", response_model=MatchResultResponse)
def finalize_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Lock this match row so simultaneous finalization requests
    # cannot both update its statistics.
    match = (
        db.query(Match)
        .filter(Match.id == match_id)
        .with_for_update()
        .first()
    )

    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    creator = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.user_id == current_user.id)
        .first()
    )

    if creator is None or creator.id != match.created_by_player_id:
        raise HTTPException(
            status_code=403,
            detail="Only the match creator can finalize the result",
        )

    if match.status != "Live":
        raise HTTPException(
            status_code=400,
            detail="Only live matches can be finalized",
        )

    if (
        match.team1_id is None
        or match.team2_id is None
        or match.team1_id == match.team2_id
    ):
        raise HTTPException(
            status_code=400,
            detail="The match must have two different teams",
        )

    existing = (
        db.query(MatchResult)
        .filter(MatchResult.match_id == match_id)
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="This match already has a finalized result",
        )

    participants = (
        db.query(MatchParticipant)
        .filter(
            MatchParticipant.match_id == match_id,
            MatchParticipant.invitation_status == "Accepted",
        )
        .all()
    )

    for participant in participants:
        if participant.team_id not in (match.team1_id, match.team2_id):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Player {participant.player_id} must be assigned "
                    "to one of the match teams"
                ),
            )

    try:
        # Calculate each team's final score.
        team1_score = int(
            db.query(func.coalesce(func.sum(ScoringEvent.points), 0))
            .filter(
                ScoringEvent.match_id == match_id,
                ScoringEvent.team_id == match.team1_id,
            )
            .scalar()
            or 0
        )

        team2_score = int(
            db.query(func.coalesce(func.sum(ScoringEvent.points), 0))
            .filter(
                ScoringEvent.match_id == match_id,
                ScoringEvent.team_id == match.team2_id,
            )
            .scalar()
            or 0
        )

        if team1_score > team2_score:
            winner_team_id = match.team1_id
        elif team2_score > team1_score:
            winner_team_id = match.team2_id
        else:
            winner_team_id = None

        # Save the result and complete the match.
        result = MatchResult(
            match_id=match_id,
            team1_score=team1_score,
            team2_score=team2_score,
            winner_team_id=winner_team_id,
            finalized_at=datetime.now(timezone.utc),
        )

        db.add(result)
        match.status = "Completed"

        # Update both teams' statistics.
        team_scores = {
            match.team1_id: team1_score,
            match.team2_id: team2_score,
        }

        for team_id in (match.team1_id, match.team2_id):
            stats = (
                db.query(TeamStatistic)
                .filter(TeamStatistic.team_id == team_id)
                .with_for_update()
                .first()
            )

            if stats is None:
                stats = TeamStatistic(
                    team_id=team_id,
                    matches_played=0,
                    wins=0,
                    losses=0,
                    points_scored=0,
                )
                db.add(stats)

            stats.matches_played += 1
            stats.points_scored += team_scores[team_id]

            if winner_team_id == team_id:
                stats.wins += 1
            elif winner_team_id is not None:
                stats.losses += 1

        # Update statistics for accepted players.
        for participant in participants:
            player_id = participant.player_id

            player_stats = (
                db.query(PlayerStatistic)
                .filter(
                    PlayerStatistic.player_id == player_id,
                    PlayerStatistic.sport_id == match.sport_id,
                )
                .with_for_update()
                .first()
            )

            if player_stats is None:
                player_stats = PlayerStatistic(
                    player_id=player_id,
                    sport_id=match.sport_id,
                    matches_played=0,
                    wins=0,
                    losses=0,
                    points_scored=0,
                )
                db.add(player_stats)

            player_points = int(
                db.query(func.coalesce(func.sum(ScoringEvent.points), 0))
                .filter(
                    ScoringEvent.match_id == match_id,
                    ScoringEvent.player_id == player_id,
                )
                .scalar()
                or 0
            )

            player_stats.matches_played += 1
            player_stats.points_scored += player_points

            if winner_team_id == participant.team_id:
                player_stats.wins += 1
            elif winner_team_id is not None:
                player_stats.losses += 1

        # Save result and all statistics together.
        db.commit()
        db.refresh(result)
        return result

    except Exception:
        db.rollback()
        raise


@router.get("/{match_id}/result", response_model=MatchResultResponse)
def get_match_result(
    match_id: int,
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()

    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    result = (
        db.query(MatchResult)
        .filter(MatchResult.match_id == match_id)
        .first()
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Final result not available",
        )

    return result
