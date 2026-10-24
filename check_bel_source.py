import sqlite3

DB_PATH = "database/n100.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n========== BEL SOURCE DATA ==========\n")

print("--- BEL BALANCE SHEET ---")

rows = cursor.execute("""
    SELECT
        id,
        company_id,
        year,
        equity_capital,
        reserves,
        borrowings,
        total_assets
    FROM balancesheet
    WHERE company_id = 'BEL'
    ORDER BY year
    LIMIT 3
""").fetchall()

for row in rows:
    print(row)

print("\n--- BEL PROFIT & LOSS ---")

rows = cursor.execute("""
    SELECT
        id,
        company_id,
        year,
        sales,
        expenses,
        operating_profit,
        net_profit
    FROM profitandloss
    WHERE company_id = 'BEL'
    ORDER BY year
    LIMIT 3
""").fetchall()

for row in rows:
    print(row)

conn.close()

print("\n========== CHECK COMPLETE ==========\n")