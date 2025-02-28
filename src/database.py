"""
Database Connection and Session Management
==========================================
"""

import logging
import os
from collections.abc import Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Load variables from .env
load_dotenv()

logger = logging.getLogger(__name__)

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DB = os.getenv("POSTGRES_DB", "llm_review_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# echo=DEBUG_MODE logs all SQL if True
engine = create_engine(DATABASE_URL, echo=DEBUG_MODE, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        logger.exception("Error occurred during DB session.")
        session.rollback()
        raise
    finally:
        session.close()
