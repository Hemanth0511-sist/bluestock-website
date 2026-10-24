import sqlite3
import pandas as pd

DB_PATH = "database/n100.db"

conn = sqlite3.connect(DB_PATH)

print("\n========== DAY 23 DATA CHECK ==========\n")

# ---------------------------------------------------------
# 1. CHECK RATIO TABLE COLUMNS
# ---------------------------------------------------------
print("1. RATIOS TABLE COLUMNS")
columns = pd.read_sql_query(
    "PRAGMA table_info(ratios)",
    conn
)

print(columns[["name", "type"]].to_string(index=False))


# ---------------------------------------------------------
# 2. LOAD 2024 ROE DATA
# ---------------------------------------------------------
print("\n2. 2024 ROE DATA")

query = """
SELECT
    company_id,
    year,
    roe
FROM ratios
WHERE year = '2024'
ORDER BY roe DESC
"""

try:
    df = pd.read_sql_query(query, conn)
    print(df.to_string(index=False))

    print("\nROE statistics:")
    print("Count :", df["roe"].count())
    print("Mean  :", df["roe"].mean())
    print("Median:", df["roe"].median())
    print("Min   :", df["roe"].min())
    print("Max   :", df["roe"].max())

except Exception as e:
    print("ROE query failed:", e)


# ---------------------------------------------------------
# 3. FIND ABNORMAL ROE VALUES
# ---------------------------------------------------------
print("\n3. ROE VALUES ABOVE 100")

try:
    abnormal = df[df["roe"] > 100]

    if abnormal.empty:
        print("No ROE values above 100.")
    else:
        print(abnormal.to_string(index=False))

except Exception as e:
    print("Abnormal-value check failed:", e)


# ---------------------------------------------------------
# 4. CHECK SECTORS
# ---------------------------------------------------------
print("\n4. SECTOR DISTRIBUTION")

queries = [
    "SELECT DISTINCT broad_sector FROM companies ORDER BY broad_sector",
    "SELECT broad_sector, COUNT(*) AS company_count "
    "FROM companies "
    "GROUP BY broad_sector "
    "ORDER BY broad_sector"
]

for q in queries:
    try:
        result = pd.read_sql_query(q, conn)
        print(result.to_string(index=False))
        print()
    except Exception as e:
        print("Sector query failed:", e)


# ---------------------------------------------------------
# 5. CHECK NULL / EMPTY SECTORS
# ---------------------------------------------------------
print("\n5. MISSING SECTOR VALUES")

try:
    missing = pd.read_sql_query(
        """
        SELECT company_id, company_name, broad_sector
        FROM companies
        WHERE broad_sector IS NULL
           OR TRIM(broad_sector) = ''
        """,
        conn
    )

    if missing.empty:
        print("No missing sector values.")
    else:
        print(missing.to_string(index=False))

except Exception as e:
    print("Missing-sector check failed:", e)


print("\n========== CHECK COMPLETE ==========\n")

conn.close()