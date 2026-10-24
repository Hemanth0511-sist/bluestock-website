"""
Day 43 - SQLite Database Optimization

Creates indexes for frequently queried company_id/year columns.

The script is:
- Safe to run multiple times
- Idempotent
- Does not modify or delete any data
- Automatically checks which tables/columns exist
"""

import sqlite3
from pathlib import Path


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "n100.db"
)


# ============================================================
# TABLE INDEX CONFIGURATION
# ============================================================

# Tables that are normally queried by company_id.
COMPANY_ID_TABLES = [
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "market_cap",
    "financial_ratios",
    "historical_financial_ratios",
    "peer_groups",
]


# ============================================================
# HELPERS
# ============================================================

def get_existing_tables(connection):
    """Return all SQLite user tables."""

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return {
        row[0]
        for row in rows
    }


def get_columns(connection, table_name):
    """Return column names for a table."""

    rows = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return {
        row[1]
        for row in rows
    }


def create_index(
    connection,
    index_name,
    table_name,
    columns,
):
    """Create an index if it does not already exist."""

    quoted_columns = ", ".join(
        f'"{column}"'
        for column in columns
    )

    sql = f"""
        CREATE INDEX IF NOT EXISTS
        "{index_name}"
        ON "{table_name}" ({quoted_columns})
    """

    connection.execute(sql)

    print(
        f"  CREATED/VERIFIED: "
        f"{index_name}"
    )


# ============================================================
# MAIN OPTIMIZATION
# ============================================================

def optimize_database():
    """Create useful SQLite indexes."""

    print("=" * 70)
    print("N100 DATABASE OPTIMIZATION")
    print("=" * 70)

    print(
        f"Database: {DATABASE_PATH}"
    )

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(
        str(DATABASE_PATH)
    )

    try:

        # ----------------------------------------------------
        # Existing tables
        # ----------------------------------------------------

        existing_tables = get_existing_tables(
            connection
        )

        print("\nExisting tables:")

        for table in sorted(existing_tables):
            print(f"  - {table}")

        print("\nApplying indexes...\n")

        indexes_created = 0

        # ----------------------------------------------------
        # Company ID indexes
        # ----------------------------------------------------

        for table_name in COMPANY_ID_TABLES:

            if table_name not in existing_tables:
                continue

            columns = get_columns(
                connection,
                table_name
            )

            if "company_id" not in columns:
                continue

            # ------------------------------------------------
            # Composite company_id + year index
            # ------------------------------------------------

            if "year" in columns:

                index_name = (
                    f"idx_{table_name}"
                    f"_company_id_year"
                )

                create_index(
                    connection,
                    index_name,
                    table_name,
                    [
                        "company_id",
                        "year",
                    ],
                )

                indexes_created += 1

            # ------------------------------------------------
            # Company ID-only index
            #
            # This is useful for tables where year does
            # not exist.
            # ------------------------------------------------

            else:

                index_name = (
                    f"idx_{table_name}"
                    f"_company_id"
                )

                create_index(
                    connection,
                    index_name,
                    table_name,
                    [
                        "company_id",
                    ],
                )

                indexes_created += 1

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        connection.commit()

        # ----------------------------------------------------
        # SQLite statistics
        # ----------------------------------------------------

        print("\nRunning ANALYZE...")

        connection.execute(
            "ANALYZE"
        )

        connection.commit()

        print(
            "\nDatabase optimization completed."
        )

        print(
            f"Indexes created/verified: "
            f"{indexes_created}"
        )

    finally:

        connection.close()

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    optimize_database()