from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime


# -------------------------
# USER SCHEMAS
# -------------------------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime | None = None


# -------------------------
# PLAYER PROFILE SCHEMAS
# -------------------------

class PlayerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    display_name: str
    city: str | None = None
    state: str | None = None
    skill_level: str


# -------------------------
# SPORT SCHEMAS
# -------------------------

class SportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class TeamCreate(BaseModel):
    sport_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sport_id: int
    name: str
    city: str | None = None
    state: str | None = None
    created_by_player_id: int

class TeamMemberAdd(BaseModel):
    player_id: int = Field(gt=0)
    role: str = Field(default="Member", min_length=1, max_length=20)


class TeamMemberResponse(BaseModel):
    team_id: int
    player_id: int
    role: str
    display_name: str

class MatchCreate(BaseModel):
    sport_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=150)
    scheduled_at: datetime
    location_name: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    team1_id: int | None = Field(default=None, gt=0)
    team2_id: int | None = Field(default=None, gt=0)


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sport_id: int
    created_by_player_id: int
    team1_id: int | None = None
    team2_id: int | None = None
    title: str
    location_name: str | None = None
    city: str | None = None
    state: str | None = None
    scheduled_at: datetime
    status: str

class InvitationStatusUpdate(BaseModel):
    status: str = Field(pattern="^(Accepted|Declined)$")


class MatchParticipantResponse(BaseModel):
    match_id: int
    player_id: int
    display_name: str
    team_id: int | None = None
    invitation_status: str

class MatchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: int
    team1_score: int
    team2_score: int
    winner_team_id: int | None = None
    finalized_at: datetime | None = None
    
class PlayerStatisticResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    player_id: int
    sport_id: int
    matches_played: int
    wins: int
    losses: int
    points_scored: int


class TeamStatisticResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    matches_played: int
    wins: int
    losses: int
    points_scored: int
