"""
Health API router.

Provides API health status, database row counts
and server uptime.
"""

import time

from fastapi import APIRouter

from src.api.database import get_db_connection

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


# ============================================================
# SERVER START TIME
# ============================================================

SERVER_START_TIME = time.time()


# ============================================================
# DATABASE TABLE COUNTS
# ============================================================


def get_db_row_counts():
    """
    Return row counts for all user tables in SQLite.

    sqlite_sequence is excluded because it is an internal
    SQLite sequence table.
    """

    connection = get_db_connection()

    try:
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """).fetchall()

        counts = {}

        for table in tables:
            table_name = table["name"]

            # Table names come directly from sqlite_master,
            # not from user input.
            count = connection.execute(
                f'SELECT COUNT(*) AS row_count FROM "{table_name}"'
            ).fetchone()["row_count"]

            counts[table_name] = count

        return counts

    finally:
        connection.close()


# ============================================================
# HEALTH ENDPOINT
# ============================================================


@router.get("")
def health_check():
    """
    API health check.
    """

    return {
        "status": "ok",
        "db_row_counts": get_db_row_counts(),
        "uptime_seconds": round(
            time.time() - SERVER_START_TIME,
            3,
        ),
        "version": "1.0.0",
    }
