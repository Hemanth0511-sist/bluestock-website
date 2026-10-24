import sqlite3
from pathlib import Path


class DatabaseManager:

    def __init__(self, db_path="database/n100.db"):
        Path("database").mkdir(exist_ok=True)
        self.connection = sqlite3.connect(db_path)
        print(f"Connected to {db_path}")

    def save_dataframe(self, df, table_name):
        print(f"Saving table: {table_name}")

        df.to_sql(table_name, self.connection, if_exists="replace", index=False)

        self.connection.commit()

        print(f"✓ {table_name} saved successfully.")

    def close(self):
        self.connection.close()
        print("Database closed.")
