import sqlite3

DB = "database/n100.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=" * 70)
print("DAY 30 - DATABASE CHECK")
print("=" * 70)

print("\n--- TABLES ---")

tables = cur.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""").fetchall()

for table in tables:
    print(table[0])

print("\n--- HISTORICAL FINANCIAL RATIOS ---")

columns = cur.execute(
    "PRAGMA table_info(historical_financial_ratios)"
).fetchall()

for column in columns:
    print(
        f"{column[0]}: "
        f"{column[1]} "
        f"{column[2]}"
    )

print("\n--- CURRENT FINANCIAL RATIOS ---")

columns = cur.execute(
    "PRAGMA table_info(financial_ratios)"
).fetchall()

for column in columns:
    print(
        f"{column[0]}: "
        f"{column[1]} "
        f"{column[2]}"
    )

print("\n--- SAMPLE HISTORICAL DATA ---")

rows = cur.execute("""
    SELECT
        company_id,
        year,
        roe,
        roce,
        debt_to_equity,
        free_cash_flow,
        cfo_quality,
        capex_intensity,
        interest_coverage
    FROM historical_financial_ratios
    ORDER BY company_id, year
    LIMIT 10
""").fetchall()

for row in rows:
    print(row)

print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)

conn.close()