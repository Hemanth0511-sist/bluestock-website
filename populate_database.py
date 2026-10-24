from src.etl.loader import ExcelLoader
from src.etl.database import DatabaseManager


def main():

    loader = ExcelLoader()
    database = DatabaseManager()

    print("=" * 70)
    print("Loading Excel Files")
    print("=" * 70)

    all_data = loader.load_all_excels()

    print("\nSaving into SQLite...\n")

    for table_name, dataframe in all_data.items():

        database.save_dataframe(
            dataframe,
            table_name
        )

    database.close()

    print("\n" + "=" * 70)
    print("DATABASE CREATED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()