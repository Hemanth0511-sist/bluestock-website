import sqlite3

DB_PATH = "database/n100.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n========== N100 DATABASE SCHEMA ==========\n")

# Get all tables
cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""")

tables = cursor.fetchall()

print("TABLES:")
for (table,) in tables:
    print(f"  - {table}")

print("\n------------------------------------------\n")

# Get columns for every table
for (table,) in tables:
    print(f"TABLE: {table}")

    cursor.execute(f'PRAGMA table_info("{table}")')
    columns = cursor.fetchall()

    for column in columns:
        # column format:
        # cid, name, type, notnull, default, pk
        cid, name, col_type, notnull, default, pk = column

        print(
            f"  {name:<30} "
            f"type={col_type:<12} "
            f"PK={pk}"
        )

    print()

print("========== SCHEMA CHECK COMPLETE ==========\n")

conn.close()