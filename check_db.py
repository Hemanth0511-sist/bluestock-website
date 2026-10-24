import sqlite3

DB_PATH = "database/n100.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("\n========== DATABASE CHECK ==========\n")

# 1. Cash flow duplicate records
print("1. CASH FLOW DUPLICATES")
rows = cur.execute("""
    SELECT company_id, year, COUNT(*) AS cnt
    FROM cashflow
    GROUP BY company_id, year
    HAVING COUNT(*) > 1
    ORDER BY company_id, year
""").fetchall()

print(rows)
print("Duplicate groups:", len(rows))


# 2. Profit & Loss duplicate records
print("\n2. PROFIT & LOSS DUPLICATES")
rows = cur.execute("""
    SELECT company_id, year, COUNT(*) AS cnt
    FROM profitandloss
    GROUP BY company_id, year
    HAVING COUNT(*) > 1
    ORDER BY company_id, year
""").fetchall()

print(rows)
print("Duplicate groups:", len(rows))


# 3. Balance Sheet duplicate records
print("\n3. BALANCE SHEET DUPLICATES")
rows = cur.execute("""
    SELECT company_id, year, COUNT(*) AS cnt
    FROM balancesheet
    GROUP BY company_id, year
    HAVING COUNT(*) > 1
    ORDER BY company_id, year
""").fetchall()

print(rows)
print("Duplicate groups:", len(rows))


# 4. ABB cash-flow records
print("\n4. ABB CASH FLOW")
rows = cur.execute("""
    SELECT *
    FROM cashflow
    WHERE company_id = 'ABB'
    ORDER BY year
""").fetchall()

for row in rows:
    print(row)

print("\nABB cash-flow records:", len(rows))


# 5. ABB P&L records
print("\n5. ABB PROFIT & LOSS")
rows = cur.execute("""
    SELECT *
    FROM profitandloss
    WHERE company_id = 'ABB'
    ORDER BY year
""").fetchall()

for row in rows:
    print(row)

print("\nABB P&L records:", len(rows))


# 6. ABB Balance Sheet records
print("\n6. ABB BALANCE SHEET")
rows = cur.execute("""
    SELECT *
    FROM balancesheet
    WHERE company_id = 'ABB'
    ORDER BY year
""").fetchall()

for row in rows:
    print(row)

print("\nABB balance-sheet records:", len(rows))


conn.close()

print("\n========== CHECK COMPLETE ==========\n")