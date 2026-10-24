"""
Database utilities for the N100 API.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = BASE_DIR / "database" / "n100.db"


def get_db_connection():
    """
    Create and return a SQLite connection.
    """

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection
