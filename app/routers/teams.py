from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.auth import get_current_user
from app.database import get_db
from app.models import Sport, Team, PlayerProfile, User,TeamMember
from app.schemas import TeamCreate, TeamResponse,TeamMemberAdd, TeamMemberResponse

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    team_data: TeamCreate,
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

    sport = db.query(Sport).filter(Sport.id == team_data.sport_id).first()
    if sport is None:
        raise HTTPException(status_code=404, detail="Sport not found")

    team = Team(
        sport_id=team_data.sport_id,
        name=team_data.name,
        city=team_data.city,
        state=team_data.state,
        created_by_player_id=profile.id,
    )

    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("/", response_model=list[TeamResponse])
def get_teams(db: Session = Depends(get_db)):
    return db.query(Team).order_by(Team.id).all()


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()

    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    return team
@router.post("/{team_id}/members", status_code=status.HTTP_201_CREATED)
def add_team_member(
    team_id: int,
    member_data: TeamMemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Find the team.
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    # Only the player who created the team can add members.
    creator = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.user_id == current_user.id)
        .first()
    )
    if creator is None or team.created_by_player_id != creator.id:
        raise HTTPException(status_code=403, detail="Only the team creator can add members")

    # Check that the player exists.
    player = (
        db.query(PlayerProfile)
        .filter(PlayerProfile.id == member_data.player_id)
        .first()
    )
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    # Prevent duplicate membership.
    existing = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == team_id,
            TeamMember.player_id == member_data.player_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Player is already a team member")

    membership = TeamMember(
        team_id=team_id,
        player_id=member_data.player_id,
        role=member_data.role,
    )

    try:
        db.add(membership)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not add team member")

    return {
        "message": "Player added to team successfully",
        "team_id": team_id,
        "player_id": player.id,
        "role": membership.role,
    }


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
def get_team_members(
    team_id: int,
    db: Session = Depends(get_db),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    members = (
        db.query(TeamMember, PlayerProfile.display_name)
        .join(
            PlayerProfile,
            PlayerProfile.id == TeamMember.player_id,
        )
        .filter(TeamMember.team_id == team_id)
        .order_by(TeamMember.player_id)
        .all()
    )

    return [
        {
            "team_id": member.team_id,
            "player_id": member.player_id,
            "role": member.role,
            "display_name": display_name,
        }
        for member, display_name in members
    ]