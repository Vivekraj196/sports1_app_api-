from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Numeric, CheckConstraint, UniqueConstraint, text
)
from sqlalchemy.orm import relationship
from app.database import Base


class Sport(Base):
    __tablename__ = "sports"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    player_profile = relationship(
        "PlayerProfile", back_populates="user", uselist=False
    )


class PlayerProfile(Base):
    __tablename__ = "player_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    display_name = Column(String(100), nullable=False)
    city = Column(String(100))
    state = Column(String(100))
    skill_level = Column(String(20), server_default="Beginner")

    __table_args__ = (
        CheckConstraint(
            "skill_level IN ('Beginner', 'Moderate', 'Advanced', 'Expert')"
        ),
    )

    user = relationship("User", back_populates="player_profile")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    sport_id = Column(Integer, ForeignKey("sports.id"), nullable=False)
    name = Column(String(100), nullable=False)
    city = Column(String(100))
    state = Column(String(100))
    created_by_player_id = Column(
        Integer, ForeignKey("player_profiles.id"), nullable=False
    )


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id = Column(Integer, ForeignKey("teams.id"), primary_key=True)
    player_id = Column(
        Integer, ForeignKey("player_profiles.id"), primary_key=True
    )
    role = Column(String(20), server_default="Member")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    sport_id = Column(Integer, ForeignKey("sports.id"), nullable=False)
    created_by_player_id = Column(
        Integer, ForeignKey("player_profiles.id"), nullable=False
    )
    team1_id = Column(Integer, ForeignKey("teams.id"))
    team2_id = Column(Integer, ForeignKey("teams.id"))
    title = Column(String(150), nullable=False)
    location_name = Column(String(200))
    city = Column(String(100))
    state = Column(String(100))
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String(20), server_default="Scheduled")

    __table_args__ = (
        CheckConstraint(
            "status IN ('Scheduled', 'Live', 'Completed', 'Cancelled')"
        ),
        CheckConstraint(
            "team1_id IS NULL OR team2_id IS NULL OR team1_id <> team2_id"
        ),
    )


class MatchParticipant(Base):
    __tablename__ = "match_participants"

    match_id = Column(Integer, ForeignKey("matches.id"), primary_key=True)
    player_id = Column(
        Integer, ForeignKey("player_profiles.id"), primary_key=True
    )
    team_id = Column(Integer, ForeignKey("teams.id"))
    invitation_status = Column(String(20), server_default="Invited")

    __table_args__ = (
        CheckConstraint(
            "invitation_status IN ('Invited', 'Accepted', 'Declined')"
        ),
    )


class ScoringEvent(Base):
    __tablename__ = "scoring_events"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    recorded_by_player_id = Column(
        Integer, ForeignKey("player_profiles.id"), nullable=False
    )
    player_id = Column(Integer, ForeignKey("player_profiles.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    points = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        CheckConstraint("points >= 0"),
    )


class MatchResult(Base):
    __tablename__ = "match_results"

    match_id = Column(
        Integer, ForeignKey("matches.id"), primary_key=True
    )
    team1_score = Column(Integer, nullable=False)
    team2_score = Column(Integer, nullable=False)
    winner_team_id = Column(Integer, ForeignKey("teams.id"))
    finalized_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        CheckConstraint("team1_score >= 0"),
        CheckConstraint("team2_score >= 0"),
    )


class PlayerStatistic(Base):
    __tablename__ = "player_statistics"

    id = Column(Integer, primary_key=True)
    player_id = Column(
        Integer, ForeignKey("player_profiles.id"), nullable=False
    )
    sport_id = Column(Integer, ForeignKey("sports.id"), nullable=False)
    matches_played = Column(Integer, server_default="0")
    wins = Column(Integer, server_default="0")
    losses = Column(Integer, server_default="0")
    points_scored = Column(Integer, server_default="0")

    __table_args__ = (
        UniqueConstraint("player_id", "sport_id"),
    )


class TeamStatistic(Base):
    __tablename__ = "team_statistics"

    id = Column(Integer, primary_key=True)
    team_id = Column(
        Integer, ForeignKey("teams.id"), unique=True, nullable=False
    )
    matches_played = Column(Integer, server_default="0")
    wins = Column(Integer, server_default="0")
    losses = Column(Integer, server_default="0")
    points_scored = Column(Integer, server_default="0")


class Ranking(Base):
    __tablename__ = "rankings"

    id = Column(Integer, primary_key=True)
    sport_id = Column(Integer, ForeignKey("sports.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("player_profiles.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    city = Column(String(100))
    rank_number = Column(Integer, nullable=False)
    rating = Column(Numeric(10, 2), server_default="0")

    __table_args__ = (
        CheckConstraint("rank_number > 0"),
        CheckConstraint(
            "(player_id IS NOT NULL AND team_id IS NULL) OR "
            "(player_id IS NULL AND team_id IS NOT NULL)"
        ),
    )