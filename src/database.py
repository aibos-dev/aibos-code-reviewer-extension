"""
Database Connection and Session Management
==========================================

Provides connections to PostgreSQL and manages sessions.
It defines global SQLAlchemy Engine and SessionMaker objects,
and uses a context manager to handle session creation and teardown.

Examples
--------
from .database import get_db_session

def some_function():
    with get_db_session() as session:
        # Perform DB operations with the session
"""

import logging
import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# Environment variables (or other configuration sources)
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "llm_review_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Define engine and sessionmaker
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db_session() -> Iterator[Session]:
    """
    Context manager for creating and closing a database session.

    Yields
    ------
    Session
        The SQLAlchemy DB session.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        logger.exception("Error occurred during DB session.")
        session.rollback()
        raise
    finally:
        session.close()
