#!/usr/bin/env python3
"""
Feedback Data Extractor

This script extracts feedback data from the code review database and exports it to a CSV file.
It joins the feedback table with related review data to provide context for each feedback entry.

Usage:
  python feedback_extractor.py [--output filename.csv] [--days 30] [--format csv|json]
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("feedback-extractor")

# Load environment variables from .env file
load_dotenv()

# Database connection settings
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DB = os.getenv("POSTGRES_DB", "llm_review_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Extract feedback data from code review database")
    parser.add_argument(
        "--output", type=str, default="feedback_data.csv", help="Output filename (default: feedback_data.csv)"
    )
    parser.add_argument("--days", type=int, default=30, help="Number of days of data to extract (default: 30)")
    parser.add_argument(
        "--format", type=str, choices=["csv", "json"], default="csv", help="Output format (default: csv)"
    )
    parser.add_argument(
        "--include-code",
        action="store_true",
        help="Include source code in the export (warning: may create large files)",
    )

    return parser.parse_args()


def get_feedback_data(session, days_ago, include_code=False):
    """
    Query the database for feedback data with related review information

    Args:
        session: SQLAlchemy database session
        days_ago: Number of days of data to extract
        include_code: Whether to include source code in the export

    Returns:
        List of dictionaries containing feedback data
    """
    # Calculate the date threshold
    cutoff_date = datetime.utcnow() - timedelta(days=days_ago)

    # Build SQL query with appropriate joins
    sql = """
    SELECT 
        rf.feedback_id,
        rf.review_id,
        rf.category_name,
        rf.user_feedback,
        rf.created_at as feedback_created_at,
        r.language,
        r.file_name,
        r.created_at as review_created_at,
        rc.message as category_message,
        j.job_id,
        j.status as job_status
    """

    # Conditionally include source code
    if include_code:
        sql += ", r.source_code, r.diff"

    sql += """
    FROM 
        review_feedback rf
    JOIN 
        reviews r ON rf.review_id = r.review_id
    JOIN 
        review_categories rc ON r.review_id = rc.review_id AND rf.category_name = rc.category_name
    LEFT JOIN 
        review_jobs j ON r.review_id = j.review_id
    WHERE 
        rf.created_at >= :cutoff_date
    ORDER BY 
        rf.created_at DESC
    """

    # Execute the query
    result = session.execute(text(sql), {"cutoff_date": cutoff_date})

    # Convert to list of dictionaries
    columns = result.keys()
    rows = []
    for row in result:
        rows.append(dict(zip(columns, row, strict=False)))

    logger.info(f"Retrieved {len(rows)} feedback records from the database")
    return rows


def export_to_csv(data, filename):
    """Export data to CSV file"""
    if not data:
        logger.warning("No data to export")
        return False

    # Get field names from the first row
    fieldnames = data[0].keys()

    try:
        with open(filename, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Data exported to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        return False


def export_to_json(data, filename):
    """Export data to JSON file"""
    if not data:
        logger.warning("No data to export")
        return False

    try:
        with open(filename, "w") as jsonfile:
            json.dump(data, jsonfile, default=str, indent=2)

        logger.info(f"Data exported to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        return False


def main():
    """Main function"""
    args = parse_arguments()

    # Create database engine and session
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        logger.info("Connected to database")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

    try:
        # Get feedback data
        data = get_feedback_data(session, args.days, args.include_code)

        # Export data based on format
        if args.format == "csv":
            success = export_to_csv(data, args.output)
        else:  # json
            success = export_to_json(data, args.output)

        if success:
            logger.info(f"Successfully exported {len(data)} records to {args.output}")
        else:
            logger.error("Failed to export data")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error processing data: {e}")
        sys.exit(1)
    finally:
        session.close()
        logger.info("Database session closed")


if __name__ == "__main__":
    main()
