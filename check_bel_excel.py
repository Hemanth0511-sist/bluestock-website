import pandas as pd


files = [
    "data/raw/balancesheet.xlsx",
    "data/processed/balancesheet.xlsx"
]


for file in files:

    print()
    print("=" * 80)
    print("FILE:", file)
    print("=" * 80)

    df = pd.read_excel(file)

    print("\nColumns:")
    for i, column in enumerate(df.columns):
        print(f"{i}: {column}")

    print("\nFirst 5 rows:")
    print(df.head(5).to_string(index=False))

    print("\nDataFrame shape:", df.shape)