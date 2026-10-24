import pandas as pd

from src.screener.dynamic_screener import DynamicScreener


pd.set_option("display.max_columns", None)
pd.set_option("display.width", 300)
pd.set_option("display.max_rows", None)


def main():

    screener = DynamicScreener()

    try:

        df = screener.run(
            min_roe=15,
            max_debt=0.5,
            min_growth=10,
            ascending=False,
            top=5
        )

        print()
        print("=" * 80)
        print("DYNAMIC SCREENER - TOP 5")
        print("=" * 80)

        columns = [
            "company_id",
            "roe",
            "roce",
            "debt_to_equity",
            "market_cap",
            "pe_ratio",
            "pb_ratio",
            "dividend_yield",
            "sales",
            "revenue_growth",
            "profit_growth"
        ]

        available_columns = [
            column for column in columns
            if column in df.columns
        ]

        print(df[available_columns])

        print()
        print("=" * 80)
        print("SCREENING VERIFICATION")
        print("=" * 80)

        print(f"Companies returned : {len(df)}")

        if not df.empty:

            roe_valid = (df["roe"] > 15).all()
            debt_valid = (df["debt_to_equity"] < 0.5).all()
            growth_valid = (df["revenue_growth"] >= 10).all()

            print(f"ROE > 15%            : {roe_valid}")
            print(f"D/E < 0.5            : {debt_valid}")
            print(f"Revenue Growth >=10% : {growth_valid}")

            df.to_csv(
                "output/dynamic_screener_test.csv",
                index=False
            )

            df.to_excel(
                "output/dynamic_screener_test.xlsx",
                index=False
            )

            print()
            print("Test CSV   : output/dynamic_screener_test.csv")
            print("Test Excel : output/dynamic_screener_test.xlsx")

        else:
            print("WARNING: No companies returned.")

        print()
        print("=" * 80)
        print("DYNAMIC SCREENER TEST COMPLETE")
        print("=" * 80)

    finally:
        screener.close()


if __name__ == "__main__":
    main()