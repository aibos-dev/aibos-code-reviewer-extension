"""
Main Entry Point
================

This is the FastAPI application startup.
Run with Docker or locally via `python -m uvicorn src.main:app --reload`.

Includes an example using Tap + pydantic for argument parsing.
"""

import logging
import sys

from fastapi import FastAPI

from .api import router as review_router
from .database import engine
from .models_db import Base
from .schemas import CliArgs

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s : %(message)s")

# Create tables if they do not already exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LLM Review API", version="1.0")

# Register routers
app.include_router(review_router)


def main() -> None:
    """
    Main function to parse command-line arguments with Tap and start the Uvicorn server.

    Examples
    --------
    python src/main.py --host 0.0.0.0 --port 8000 --debug True
    """
    try:
        from tap import Tap  # typed-argument-parser
    except ImportError:
        logger.exception("Tap module not installed. Please `pip install typed-argument-parser`.")
        sys.exit(1)

    class ArgsParser(Tap):
        host: str = "127.0.0.1"
        port: int = 8000
        debug: bool = False

    parsed_args = ArgsParser().parse_args()
    cli_args = CliArgs(host=parsed_args.host, port=parsed_args.port, debug=parsed_args.debug)

    import uvicorn

    uvicorn.run("src.main:app", host=cli_args.host, port=cli_args.port, reload=cli_args.debug)


if __name__ == "__main__":
    main()
