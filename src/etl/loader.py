from pathlib import Path
import pandas as pd


class ExcelLoader:
    def __init__(self, data_folder="data/raw"):
        self.data_folder = Path(data_folder)

    def load_excel(self, filename, sheet_name=0):
        file_path = self.data_folder / filename

        if not file_path.exists():
            raise FileNotFoundError(file_path)

        preview = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=None,
            nrows=3,
            engine="openpyxl"
        )

        first_cell = str(preview.iloc[0, 0])

        if "Mkt Fintech" in first_cell:
            header_row = 1
        else:
            header_row = 0

        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=header_row,
            engine="openpyxl"
        )

        return df

    def show_info(self, df):
        print("=" * 60)
        print(f"Rows    : {len(df)}")
        print(f"Columns : {len(df.columns)}")
        print(df.columns.tolist())
        print("=" * 60)

    def load_all_excels(self):
        dataframes = {}

        for file in self.data_folder.glob("*.xlsx"):
            print(f"Loading {file.name}...")
            df = self.load_excel(file.name)
            dataframes[file.stem] = df

        return dataframes