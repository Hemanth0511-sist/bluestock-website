# ============================================================
# FIX PEER GROUPS TABLE
# File: src/utils/fix_peergroups.py
# ============================================================

import sqlite3
from pathlib import Path

import pandas as pd

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = PROJECT_ROOT / "database" / "n100.db"

EXCEL_PATH = PROJECT_ROOT / "data" / "peer_groups.xlsx"


# ============================================================
# PRINT HEADER
# ============================================================

print("=" * 70)
print("FIXING PEER GROUPS TABLE")
print("=" * 70)

print()
print("Database:")
print(DATABASE_PATH)

print()
print("Excel:")
print(EXCEL_PATH)


# ============================================================
# CHECK FILES
# ============================================================

if not DATABASE_PATH.exists():

    print()
    print("ERROR: Database file not found.")
    print(DATABASE_PATH)
    raise SystemExit(1)


if not EXCEL_PATH.exists():

    print()
    print("ERROR: Excel file not found:")
    print(EXCEL_PATH)

    print()
    print("Checking common locations...")

    possible_paths = [
        PROJECT_ROOT / "peer_groups.xlsx",
        PROJECT_ROOT / "data" / "peer_groups.xlsx",
        PROJECT_ROOT / "datasets" / "peer_groups.xlsx",
    ]

    for path in possible_paths:

        print(f"  {path} -> " f"{'FOUND' if path.exists() else 'not found'}")

    raise SystemExit(1)


# ============================================================
# READ EXCEL
# ============================================================

print()
print("-" * 70)
print("READING EXCEL FILE")
print("-" * 70)

excel_raw = pd.read_excel(
    EXCEL_PATH,
    header=None,
)

print()
print("Raw Excel shape:")
print(excel_raw.shape)

print()
print("First rows:")
print(excel_raw.head(20).to_string(index=False))


# ============================================================
# FIND HEADER ROW
# ============================================================

print()
print("-" * 70)
print("SEARCHING FOR HEADER ROW")
print("-" * 70)


header_row = None

for index, row in excel_raw.iterrows():

    values = [str(value).strip().lower() for value in row.tolist() if pd.notna(value)]

    joined = " | ".join(values)

    has_company = (
        "company_id" in values
        or "company id" in values
        or "ticker" in values
        or "symbol" in values
    )

    has_peer = (
        "peer_group" in values
        or "peer group" in values
        or "group_name" in values
        or "group" in values
    )

    if has_company and has_peer:

        header_row = index
        break


if header_row is None:

    print()
    print("ERROR: Could not automatically find header row.")

    print()
    print("The Excel file must contain columns similar to:")

    print("company_id | peer_group")

    raise SystemExit(1)


print()
print("Header row found:")
print(header_row)


# ============================================================
# RE-READ EXCEL USING HEADER
# ============================================================

df = pd.read_excel(
    EXCEL_PATH,
    header=header_row,
)


# ============================================================
# CLEAN COLUMN NAMES
# ============================================================

df.columns = [
    str(column).strip().lower().replace(" ", "_").replace("-", "_")
    for column in df.columns
]


print()
print("Excel columns:")
for column in df.columns:
    print("  ", column)


# ============================================================
# FIND COMPANY COLUMN
# ============================================================

company_column = None

company_candidates = [
    "company_id",
    "companyid",
    "company",
    "ticker",
    "symbol",
]


for candidate in company_candidates:

    if candidate in df.columns:

        company_column = candidate
        break


# ============================================================
# FIND PEER GROUP COLUMN
# ============================================================

peer_column = None

peer_candidates = [
    "peer_group",
    "peer_group_name",
    "peergroup",
    "peer_group_name",
    "group_name",
    "group",
]


for candidate in peer_candidates:

    if candidate in df.columns:

        peer_column = candidate
        break


# ============================================================
# VALIDATE COLUMNS
# ============================================================

if company_column is None:

    print()
    print("ERROR: Company column not found.")

    print()
    print("Available columns:")
    print(df.columns.tolist())

    raise SystemExit(1)


if peer_column is None:

    print()
    print("ERROR: Peer group column not found.")

    print()
    print("Available columns:")
    print(df.columns.tolist())

    raise SystemExit(1)


print()
print("Detected company column:")
print(company_column)

print()
print("Detected peer group column:")
print(peer_column)


# ============================================================
# CREATE CLEAN DATAFRAME
# ============================================================

clean_df = df[
    [
        company_column,
        peer_column,
    ]
].copy()


clean_df.columns = [
    "company_id",
    "peer_group_name",
]


# ============================================================
# CLEAN VALUES
# ============================================================

clean_df["company_id"] = clean_df["company_id"].astype(str).str.strip()


clean_df["peer_group_name"] = clean_df["peer_group_name"].astype(str).str.strip()


# Remove invalid values

invalid_company_values = [
    "",
    "nan",
    "none",
    "null",
    "company_id",
]


invalid_group_values = [
    "",
    "nan",
    "none",
    "null",
    "peer_group",
    "peer_group_name",
]


clean_df = clean_df[~clean_df["company_id"].str.lower().isin(invalid_company_values)]


clean_df = clean_df[~clean_df["peer_group_name"].str.lower().isin(invalid_group_values)]


# ============================================================
# REMOVE DUPLICATES
# ============================================================

clean_df = clean_df.drop_duplicates(
    subset=[
        "company_id",
        "peer_group_name",
    ]
)


# ============================================================
# SORT
# ============================================================

clean_df = clean_df.sort_values(
    by=[
        "peer_group_name",
        "company_id",
    ]
).reset_index(drop=True)


# ============================================================
# DISPLAY CLEAN DATA
# ============================================================

print()
print("-" * 70)
print("CLEAN PEER GROUP DATA")
print("-" * 70)

print()
print(clean_df.head(30).to_string(index=False))


print()
print("Total records:")
print(len(clean_df))


print()
print("Total peer groups:")
print(clean_df["peer_group_name"].nunique())


print()
print("Peer groups:")

for group in clean_df["peer_group_name"].drop_duplicates().tolist():

    count = len(clean_df[clean_df["peer_group_name"] == group])

    print(f"  {group}: {count} companies")


# ============================================================
# VALIDATION
# ============================================================

if clean_df.empty:

    print()
    print("ERROR: No valid peer-group records found.")

    raise SystemExit(1)


# ============================================================
# DATABASE CONNECTION
# ============================================================

connection = sqlite3.connect(DATABASE_PATH)

cursor = connection.cursor()


# ============================================================
# CHECK OLD TABLE
# ============================================================

print()
print("-" * 70)
print("CURRENT DATABASE TABLE")
print("-" * 70)

cursor.execute(
    "SELECT name FROM sqlite_master " "WHERE type='table' AND name='peer_groups'"
)

existing_table = cursor.fetchone()

if existing_table:

    print()
    print("Existing peer_groups table found.")

    cursor.execute("PRAGMA table_info(peer_groups)")

    columns = cursor.fetchall()

    for column in columns:

        print(f"  {column[1]} " f"{column[2]}")

else:

    print()
    print("peer_groups table does not currently exist.")


# ============================================================
# BACKUP OLD TABLE
# ============================================================

if existing_table:

    print()
    print("Creating backup table...")

    cursor.execute("""
        DROP TABLE IF EXISTS peer_groups_backup
        """)

    cursor.execute("""
        CREATE TABLE peer_groups_backup
        AS
        SELECT *
        FROM peer_groups
        """)

    print("Backup created:")

    print("peer_groups_backup")


# ============================================================
# DELETE OLD TABLE
# ============================================================

print()
print("Removing old peer_groups table...")

cursor.execute("DROP TABLE IF EXISTS peer_groups")


# ============================================================
# CREATE CORRECT TABLE
# ============================================================

print()
print("Creating corrected peer_groups table...")

cursor.execute("""
    CREATE TABLE peer_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        peer_group_name TEXT NOT NULL
    )
    """)


# ============================================================
# INSERT DATA
# ============================================================

records = clean_df[
    [
        "company_id",
        "peer_group_name",
    ]
].values.tolist()


cursor.executemany(
    """
    INSERT INTO peer_groups (
        company_id,
        peer_group_name
    )
    VALUES (?, ?)
    """,
    records,
)


# ============================================================
# INDEXES
# ============================================================

cursor.execute("""
    CREATE INDEX IF NOT EXISTS
    idx_peer_groups_company
    ON peer_groups(company_id)
    """)


cursor.execute("""
    CREATE INDEX IF NOT EXISTS
    idx_peer_groups_group
    ON peer_groups(peer_group_name)
    """)


# ============================================================
# COMMIT
# ============================================================

connection.commit()


# ============================================================
# VERIFY TABLE
# ============================================================

print()
print("=" * 70)
print("VERIFYING CORRECTED TABLE")
print("=" * 70)


cursor.execute("PRAGMA table_info(peer_groups)")

columns = cursor.fetchall()

print()

for column in columns:

    print(f"{column[0]:3} " f"{column[1]:25} " f"{column[2]}")


# ============================================================
# VERIFY RECORDS
# ============================================================

cursor.execute("""
    SELECT
        id,
        company_id,
        peer_group_name
    FROM peer_groups
    ORDER BY
        peer_group_name,
        company_id
    LIMIT 30
    """)

rows = cursor.fetchall()


print()
print("Corrected data:")

for row in rows:

    print(f"{row[0]:3} " f"{row[1]:15} " f"{row[2]}")


# ============================================================
# TOTAL COUNT
# ============================================================

cursor.execute("SELECT COUNT(*) FROM peer_groups")

total_records = cursor.fetchone()[0]


print()
print("Total records:")
print(total_records)


# ============================================================
# GROUP COUNT
# ============================================================

cursor.execute("""
    SELECT
        peer_group_name,
        COUNT(*) AS company_count
    FROM peer_groups
    GROUP BY peer_group_name
    ORDER BY peer_group_name
    """)

group_rows = cursor.fetchall()


print()
print("Peer groups:")

for group_name, count in group_rows:

    print(f"  {group_name}: " f"{count} companies")


# ============================================================
# CLOSE DATABASE
# ============================================================

connection.close()


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("PEER GROUP TABLE FIX COMPLETED")
print("=" * 70)

print()
print("Backup:")
print("peer_groups_backup")

print()
print("New table:")
print("peer_groups")

print()
print("Now restart Streamlit.")
print("=" * 70)
