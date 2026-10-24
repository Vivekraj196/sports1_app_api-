import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

# Find the .env file in the sportsapp project root.
# This works even when the application starts from another directory.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# Load database credentials from .env into environment variables.
load_dotenv(ENV_FILE)

# Build the database URL safely.
# URL.create handles special characters in the password.
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME", "playrank_db"),
)

# Engine manages connections between Python and PostgreSQL.
engine = create_engine(DATABASE_URL)

# SessionLocal creates a database session when an API needs to
# read or change data.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base is used later if we define SQLAlchemy ORM models.
Base = declarative_base()


def get_db():
    """
    Provide a database session to an API endpoint.

    yield passes the session to the endpoint.
    finally closes the session, even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_db_connection():
    """Run a tiny SQL query to check the database connection."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def get_existing_tables():
    """
    Return the names of tables in PostgreSQL's default schema.

    This inspects the database; it does NOT create or delete tables.
    """
    return inspect(engine).get_table_names(schema="public")

