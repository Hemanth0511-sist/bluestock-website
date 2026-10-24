import sqlite3

DB_PATH = "database/n100.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n========== BEL FULL BALANCE SHEET ==========\n")

rows = cursor.execute("""
    SELECT *
    FROM balancesheet
    WHERE company_id = 'BEL'
    ORDER BY year
""").fetchall()

columns = [
    description[0]
    for description in cursor.description
]

print("COLUMNS:")
for i, column in enumerate(columns):
    print(f"{i}: {column}")

print("\nRECORDS:")

for row in rows:
    print("\n------------------------------")

    for i, value in enumerate(row):
        print(f"{columns[i]} = {value}")

conn.close()

print("\n========== CHECK COMPLETE ==========\n")