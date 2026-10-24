import sqlite3

DB_PATH = "database/n100.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("\n========== DUPLICATE RECORD ANALYSIS ==========\n")

# --------------------------------------------------
# CASH FLOW
# --------------------------------------------------

print("=== ABB CASH FLOW DUPLICATES ===")

rows = cur.execute("""
    SELECT *
    FROM cashflow
    WHERE company_id = 'ABB'
      AND year IN (
          'Mar 2014',
          'Mar 2015',
          'Mar 2020',
          'Mar 2024'
      )
    ORDER BY year, id
""").fetchall()

for row in rows:
    print(row)


# --------------------------------------------------
# PROFIT & LOSS
# --------------------------------------------------

print("\n=== ADANIPORTS P&L DUPLICATES ===")

rows = cur.execute("""
    SELECT *
    FROM profitandloss
    WHERE company_id = 'ADANIPORTS'
    ORDER BY year, id
""").fetchall()

for row in rows:
    print(row)


# --------------------------------------------------
# BALANCE SHEET
# --------------------------------------------------

print("\n=== PNB BALANCE SHEET DUPLICATES ===")

rows = cur.execute("""
    SELECT *
    FROM balancesheet
    WHERE company_id = 'PNB'
    ORDER BY year, id
""").fetchall()

for row in rows:
    print(row)


conn.close()

print("\n========== ANALYSIS COMPLETE ==========\n")