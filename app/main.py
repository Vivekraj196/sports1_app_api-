from fastapi import FastAPI, HTTPException
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.database import (
    Base,
    engine,
    test_db_connection,
    get_existing_tables,
)
from app import models
from app.routers import (
    users,
    profiles,
    sports,
    teams,
    matches,
    invitations,
    scoring,
    results,
    statistics,
    rankings,
)

app = FastAPI(
    title="PlayRank API",
    description="Backend API for local sports matches and rankings",
    version="1.0.0",
)


@app.on_event("startup")
def create_tables():
    # Create missing tables without recreating existing tables.
    Base.metadata.create_all(bind=engine)


# Register all application routers.
app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(sports.router)
app.include_router(teams.router)
app.include_router(matches.router)
app.include_router(invitations.router)
app.include_router(scoring.router)
app.include_router(results.router)
app.include_router(statistics.router)
app.include_router(rankings.router)


@app.get("/")
def home():
    return {"message": "PlayRank API is running"}


@app.get("/db-check")
def db_check():
    try:
        test_db_connection()
        return {"message": "PostgreSQL connected successfully"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed. Check server logs.",
        )


@app.get("/tables")
def list_tables():
    try:
        tables = get_existing_tables()
        return {"count": len(tables), "tables": tables}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve database tables.",
        )


@app.get("/database-schema")
def database_schema():
    try:
        inspector = inspect(engine)
        result = {}

        for table in inspector.get_table_names(schema="public"):
            primary_keys = set(
                inspector.get_pk_constraint(
                    table, schema="public"
                ).get("constrained_columns") or []
            )

            result[table] = [
                {
                    "column": column["name"],
                    "type": str(column["type"]),
                    "nullable": column["nullable"],
                    "primary_key": column["name"] in primary_keys,
                }
                for column in inspector.get_columns(
                    table, schema="public"
                )
            ]

        return result

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve database schema.",
        )
