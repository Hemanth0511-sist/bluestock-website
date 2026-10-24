from pathlib import Path

import pandas as pd


class DataCleaner:

    def __init__(self):
        pass

    def clean_dataframe(self, df):
        """
        Generic cleaning for every dataframe.
        """

        # Remove completely empty rows
        df = df.dropna(how="all")

        # Remove duplicate rows
        df = df.drop_duplicates()

        # Remove completely empty columns
        df = df.dropna(axis=1, how="all")

        # Strip whitespace from column names
        df.columns = [str(col).strip() for col in df.columns]

        # Strip whitespace from string columns
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.strip().replace("nan", pd.NA)

        # Reset index
        df.reset_index(drop=True, inplace=True)

        return df

    def show_info(self, df):
        print("=" * 60)
        print("Cleaned Data Summary")
        print(f"Rows    : {len(df)}")
        print(f"Columns : {len(df.columns)}")
        print("Column Names:")
        print(df.columns.tolist())
        print("=" * 60)

    def save_dataframe(self, df, filename, output_folder="data/processed"):
        """
        Save cleaned dataframe as Excel.
        """

        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / f"{filename}.xlsx"

        df.to_excel(file_path, index=False, engine="openpyxl")

        print(f"Saved: {file_path}")

    def clean_all(self, dataframes):
        """
        Clean all loaded dataframes.
        """

        cleaned_data = {}

        for name, df in dataframes.items():
            print(f"\nCleaning {name}...")

            cleaned_df = self.clean_dataframe(df)

            self.show_info(cleaned_df)

            self.save_dataframe(cleaned_df, name)

            cleaned_data[name] = cleaned_df

        return cleaned_data
