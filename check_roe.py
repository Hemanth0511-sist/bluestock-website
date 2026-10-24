import sqlite3
import pandas as pd

DB_PATH = "database/n100.db"

conn = sqlite3.connect(DB_PATH)

query = """
SELECT
    company_id,
    year,
    roe,
    roce,
    debt_to_equity,
    free_cash_flow
FROM historical_financial_ratios
WHERE company_id IN (?, ?, ?)
ORDER BY company_id, year
"""

df = pd.read_sql_query(
    query,
    conn,
    params=("BEL", "HAL", "INDIGO")
)

print("\n========== BEL / HAL / INDIGO ROE CHECK ==========\n")
print(df.to_string(index=False))

conn.close()