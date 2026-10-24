import sqlite3
from pathlib import Path

import pandas as pd

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = PROJECT_ROOT / "database" / "n100.db"


# ============================================================
# MAIN
# ============================================================


def fix_prosandcons():

    print("=" * 70)
    print("FIXING PROS & CONS TABLE")
    print("=" * 70)

    print()
    print(f"Database: {DATABASE_PATH}")

    if not DATABASE_PATH.exists():

        print()
        print("ERROR: Database file not found.")

        return

    connection = sqlite3.connect(DATABASE_PATH)

    try:

        # ====================================================
        # SHOW CURRENT TABLE STRUCTURE
        # ====================================================

        print()
        print("-" * 70)
        print("CURRENT TABLE STRUCTURE")
        print("-" * 70)

        schema = pd.read_sql_query(
            """
            PRAGMA table_info(prosandcons)
            """,
            connection,
        )

        if schema.empty:

            print("prosandcons table does not exist.")

        else:

            print(schema[["cid", "name", "type"]].to_string(index=False))

        # ====================================================
        # READ OLD TABLE
        # ====================================================

        old_data = pd.read_sql_query(
            """
            SELECT *
            FROM prosandcons
            """,
            connection,
        )

        print()
        print("-" * 70)
        print("OLD DATA")
        print("-" * 70)

        print(old_data.head(10).to_string(index=False))

        print()
        print(f"Old rows: {len(old_data)}")

        # ====================================================
        # DETERMINE OLD COLUMN NAMES
        # ====================================================

        old_columns = list(old_data.columns)

        print()
        print("Old columns:")

        for column in old_columns:

            print(f"  {column}")

        # ====================================================
        # EXPECTED DATA
        # ====================================================

        expected_columns = ["id", "company_id", "pros", "cons"]

        # ====================================================
        # CHECK WHETHER TABLE IS ALREADY CORRECT
        # ====================================================

        if all(column in old_columns for column in expected_columns):

            print()
            print("prosandcons table is already correct.")

            return

        # ====================================================
        # THE CURRENT DATABASE WAS CREATED WITH
        # THE TITLE ROW AS COLUMN NAMES.
        #
        # DATA STRUCTURE:
        #
        # Row 0:
        #   title
        #
        # Row 1:
        #   id
        #   company_id
        #   pros
        #   cons
        #
        # Row 2 onward:
        #   actual data
        #
        # Therefore we need to reconstruct the table.
        # ====================================================

        print()
        print("-" * 70)
        print("REBUILDING TABLE")
        print("-" * 70)

        # ====================================================
        # FIND THE FOUR ORIGINAL COLUMNS
        # ====================================================

        if len(old_columns) < 4:

            print("ERROR: Expected at least 4 columns.")

            return

        # The old table has exactly four columns.
        #
        # Example:
        #
        # column 0 -> id
        # column 1 -> company_id
        # column 2 -> pros
        # column 3 -> cons

        col_id = old_columns[0]
        col_company = old_columns[1]
        col_pros = old_columns[2]
        col_cons = old_columns[3]

        # ====================================================
        # CONVERT TO CORRECT COLUMN NAMES
        # ====================================================

        fixed_data = old_data[[col_id, col_company, col_pros, col_cons]].copy()

        fixed_data.columns = ["id", "company_id", "pros", "cons"]

        # ====================================================
        # REMOVE INVALID TITLE ROWS
        # ====================================================

        fixed_data["id_numeric"] = pd.to_numeric(fixed_data["id"], errors="coerce")

        fixed_data = fixed_data[fixed_data["id_numeric"].notna()].copy()

        fixed_data["id"] = fixed_data["id_numeric"].astype(int)

        fixed_data.drop(columns=["id_numeric"], inplace=True)

        # ====================================================
        # CLEAN COMPANY ID
        # ====================================================

        fixed_data["company_id"] = fixed_data["company_id"].astype(str).str.strip()

        # ====================================================
        # CLEAN PROS
        # ====================================================

        fixed_data["pros"] = fixed_data["pros"].where(fixed_data["pros"].notna(), None)

        # ====================================================
        # CLEAN CONS
        # ====================================================

        fixed_data["cons"] = fixed_data["cons"].where(fixed_data["cons"].notna(), None)

        # ====================================================
        # REMOVE EMPTY COMPANY IDS
        # ====================================================

        fixed_data = fixed_data[fixed_data["company_id"].notna()]

        fixed_data = fixed_data[fixed_data["company_id"].str.lower() != "nan"]

        fixed_data = fixed_data[fixed_data["company_id"].str.strip() != ""]

        # ====================================================
        # SHOW FIXED DATA
        # ====================================================

        print()
        print("Fixed columns:")

        print(list(fixed_data.columns))

        print()
        print(f"Fixed rows: {len(fixed_data)}")

        print()
        print(fixed_data.head(10).to_string(index=False))

        # ====================================================
        # BACKUP OLD TABLE
        # ====================================================

        print()
        print("Creating backup table...")

        connection.execute("""
            DROP TABLE IF EXISTS prosandcons_backup
            """)

        connection.execute("""
            ALTER TABLE prosandcons
            RENAME TO prosandcons_backup
            """)

        connection.commit()

        # ====================================================
        # CREATE CORRECT TABLE
        # ====================================================

        print("Creating corrected prosandcons table...")

        connection.execute("""
            CREATE TABLE prosandcons (

                id INTEGER PRIMARY KEY,

                company_id TEXT NOT NULL,

                pros TEXT,

                cons TEXT,

                FOREIGN KEY(company_id)
                    REFERENCES companies(id)

            )
            """)

        # ====================================================
        # INSERT CORRECT DATA
        # ====================================================

        for _, row in fixed_data.iterrows():

            connection.execute(
                """
                INSERT INTO prosandcons
                (
                    id,
                    company_id,
                    pros,
                    cons
                )
                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (int(row["id"]), row["company_id"], row["pros"], row["cons"]),
            )

        connection.commit()

        # ====================================================
        # VERIFY
        # ====================================================

        print()
        print("-" * 70)
        print("VERIFYING CORRECTED TABLE")
        print("-" * 70)

        new_schema = pd.read_sql_query(
            """
            PRAGMA table_info(prosandcons)
            """,
            connection,
        )

        print(new_schema[["cid", "name", "type"]].to_string(index=False))

        # ====================================================
        # VERIFY DATA
        # ====================================================

        verification = pd.read_sql_query(
            """
            SELECT
                id,
                company_id,
                pros,
                cons
            FROM prosandcons
            ORDER BY id
            """,
            connection,
        )

        print()
        print("Corrected data:")

        print(verification.to_string(index=False))

        print()
        print(f"Total records: {len(verification)}")

        # ====================================================
        # CHECK HDFCBANK
        # ====================================================

        hdfc = pd.read_sql_query(
            """
            SELECT
                id,
                company_id,
                pros,
                cons
            FROM prosandcons
            WHERE company_id = ?
            """,
            connection,
            params=("HDFCBANK",),
        )

        print()
        print("-" * 70)
        print("HDFCBANK CHECK")
        print("-" * 70)

        if hdfc.empty:

            print("No HDFCBANK Pros & Cons record found.")

        else:

            print(hdfc.to_string(index=False))

        # ====================================================
        # FINAL MESSAGE
        # ====================================================

        print()
        print("=" * 70)
        print("PROS & CONS TABLE FIX COMPLETED")
        print("=" * 70)

        print()
        print("Backup table:")

        print("prosandcons_backup")

        print()
        print("New table:")

        print("prosandcons")

    except Exception as e:

        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)

        print(str(e))

        connection.rollback()

    finally:

        connection.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    fix_prosandcons()
