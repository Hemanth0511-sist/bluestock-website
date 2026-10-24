from pathlib import Path

import pandas as pd


class ExcelLoader:

    def __init__(self):
        self.data_folder = Path("data/raw")

    def load_excel(self, filename, sheet_name=0):

        file_path = self.data_folder / filename

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Preview first 5 rows
        preview = pd.read_excel(
            file_path, sheet_name=sheet_name, header=None, nrows=5, engine="openpyxl"
        )

        print("\n" + "=" * 70)
        print(f"Checking file: {filename}")
        print(preview)
        print("=" * 70)

        # Files whose headers are on the second row
        header_row = 0

        header_files = {
            "companies.xlsx",
            "profitandloss.xlsx",
            "balancesheet.xlsx",
            "cashflow.xlsx",
        }

        if filename.lower() in header_files:
            header_row = 1

        # Read Excel
        df = pd.read_excel(
            file_path, sheet_name=sheet_name, header=header_row, engine="openpyxl"
        )

        # Remove empty rows
        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")
        df.reset_index(drop=True, inplace=True)

        return df

    def load_all_excels(self):

        excel_files = [
            "analysis.xlsx",
            "balancesheet.xlsx",
            "cashflow.xlsx",
            "companies.xlsx",
            "documents.xlsx",
            "financial_ratios.xlsx",
            "market_cap.xlsx",
            "peer_groups.xlsx",
            "profitandloss.xlsx",
            "prosandcons.xlsx",
            "sectors.xlsx",
            "stock_prices.xlsx",
        ]

        all_data = {}

        for file in excel_files:
            print(f"Loading {file}...")
            all_data[file.replace(".xlsx", "")] = self.load_excel(file)

        return all_data
