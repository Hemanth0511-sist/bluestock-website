import sqlite3

conn = sqlite3.connect("database/n100.db")

print("=" * 70)
print("CAPITAL ALLOCATION DATABASE CHECK")
print("=" * 70)

tables = conn.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""").fetchall()

print("\nTABLES:")
for table in tables:
    print(table[0])

print("\nCAPITAL-RELATED TABLES:")
capital_tables = [
    table[0]
    for table in tables
    if "capital" in table[0].lower()
]

if capital_tables:
    for table in capital_tables:
        print(table)
else:
    print("No capital-related table found.")

conn.close()

print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)