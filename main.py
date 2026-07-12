from src.etl.loader import ExcelLoader


def main():
    loader = ExcelLoader()

    all_data = loader.load_all_excels()

    print("\n========== SUMMARY ==========\n")

    for name, df in all_data.items():
        print(f"{name}")
        print(f"Rows    : {len(df)}")
        print(f"Columns : {len(df.columns)}")
        print("-" * 40)


if __name__ == "__main__":
    main()