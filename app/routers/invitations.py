
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Match, MatchParticipant, PlayerProfile, Team, User
from app.schemas import (
    InvitationStatusUpdate,
    MatchParticipantResponse,
)

router = APIRouter(prefix="/matches", tags=["Match Invitations"])


@router.post("/{match_id}/invites", status_code=status.HTTP_201_CREATED)
def invite_player(
    match_id: int,
    player_id: int,
    team_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()

    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.status in ("Completed", "Cancelled"):
        raise HTTPException(
            status_code=400,
            detail="Cannot invite players to a completed or cancelled match",
        )

    creator = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.user_id == current_user.id)
        .first()
    )

    if creator is None or creator.id != match.created_by_player_id:
        raise HTTPException(
            status_code=403,
            detail="Only the match creator can invite players",
        )

    player = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.id == player_id)
        .first()
    )

    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    # Team-based matches require the invited player to be assigned
    # to one of the two teams.
    if match.team1_id is not None and match.team2_id is not None:
        if team_id not in (match.team1_id, match.team2_id):
            raise HTTPException(
                status_code=400,
                detail="team_id must be one of the match's two teams",
            )
    elif team_id is not None:
        raise HTTPException(
            status_code=400,
            detail="This match does not have two teams configured",
        )

    # Verify the selected team exists and belongs to the match's sport.
    if team_id is not None:
        team = db.query(Team).filter(Team.id == team_id).first()

        if team is None or team.sport_id != match.sport_id:
            raise HTTPException(
                status_code=400,
                detail="The selected team does not belong to this sport",
            )

    existing = (
        db.query(MatchParticipant)
        .filter(
            MatchParticipant.match_id == match_id,
            MatchParticipant.player_id == player_id,
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Player has already been invited to this match",
        )

    participant = MatchParticipant(
        match_id=match_id,
        player_id=player_id,
        team_id=team_id,
        invitation_status="Invited",
    )

    try:
        db.add(participant)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Player invited successfully",
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "invitation_status": "Invited",
    }


@router.patch("/{match_id}/invites/{player_id}")
def update_invitation(
    match_id: int,
    player_id: int,
    update_data: InvitationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()

    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.status in ("Completed", "Cancelled"):
        raise HTTPException(
            status_code=400,
            detail="Cannot respond to an invitation for an inactive match",
        )

    profile = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.user_id == current_user.id)
        .first()
    )

    if profile is None or profile.id != player_id:
        raise HTTPException(
            status_code=403,
            detail="You can only respond to your own invitation",
        )

    participant = (
        db.query(MatchParticipant)
        .filter(
            MatchParticipant.match_id == match_id,
            MatchParticipant.player_id == player_id,
        )
        .first()
    )

    if participant is None:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if participant.invitation_status != "Invited":
        raise HTTPException(
            status_code=409,
            detail="Invitation has already been answered",
        )

    participant.invitation_status = update_data.status

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Invitation response saved",
        "match_id": match_id,
        "player_id": player_id,
        "team_id": participant.team_id,
        "invitation_status": participant.invitation_status,
    }


@router.get(
    "/{match_id}/participants",
    response_model=list[MatchParticipantResponse],
)
def get_match_participants(
    match_id: int,
    db: Session = Depends(get_db),
):
    match = db.query(Match).filter(Match.id == match_id).first()

    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    rows = (
        db.query(MatchParticipant, PlayerProfile.display_name)
        .join(
            PlayerProfile,
            PlayerProfile.id == MatchParticipant.player_id,
        )
        .filter(MatchParticipant.match_id == match_id)
        .order_by(MatchParticipant.player_id)
        .all()
    )

    return [
        {
            "match_id": participant.match_id,
            "player_id": participant.player_id,
            "display_name": display_name,
            "team_id": participant.team_id,
            "invitation_status": participant.invitation_status,
        }
        for participant, display_name in rows
    ]
