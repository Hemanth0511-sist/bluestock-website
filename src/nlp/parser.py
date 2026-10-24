import os
import re

import pandas as pd

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

INPUT_FILE = os.path.join(BASE_DIR, "data", "raw", "analysis.xlsx")

OUTPUT_DIR = os.path.join(BASE_DIR, "output")

PARSED_FILE = os.path.join(OUTPUT_DIR, "analysis_parsed.csv")

FAILURE_FILE = os.path.join(OUTPUT_DIR, "parse_failures.csv")

DB_FILE = os.path.join(BASE_DIR, "database", "n100.db")


# ==========================================================
# REGEX
# ==========================================================

PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([-+]?\d+(?:\.\d+)?)%", re.IGNORECASE)


# ==========================================================
# LOAD ANALYSIS DATA
# ==========================================================


def load_analysis():

    df = pd.read_excel(INPUT_FILE, header=1)

    df.columns = [str(col).strip() for col in df.columns]

    required_columns = [
        "id",
        "company_id",
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe",
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df[required_columns].copy()


# ==========================================================
# PARSE ONE VALUE
# ==========================================================


def parse_value(value):

    if pd.isna(value):
        return []

    text = str(value).strip()

    matches = PATTERN.findall(text)

    results = []

    for period, percentage in matches:

        results.append({"period_years": int(period), "value_pct": float(percentage)})

    return results


# ==========================================================
# MAIN PARSER
# ==========================================================


def parse_analysis():

    print("=" * 70)
    print("DAY 29 - NLP ANALYSIS TEXT PARSER")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\nLoading analysis.xlsx...")

    df = load_analysis()

    print(f"Analysis records loaded: {len(df)}")

    metric_columns = {
        "compounded_sales_growth": "compounded_sales_growth",
        "compounded_profit_growth": "compounded_profit_growth",
        "stock_price_cagr": "stock_price_cagr",
        "roe": "roe",
    }

    parsed_rows = []
    failure_rows = []

    for _, row in df.iterrows():

        company_id = str(row["company_id"]).strip().upper()

        for metric_type, column in metric_columns.items():

            raw_value = row[column]

            parsed = parse_value(raw_value)

            if parsed:

                for item in parsed:

                    parsed_rows.append(
                        {
                            "company_id": company_id,
                            "metric_type": metric_type,
                            "period_years": item["period_years"],
                            "value_pct": item["value_pct"],
                        }
                    )

            else:

                if not pd.isna(raw_value):

                    failure_rows.append(
                        {
                            "company_id": company_id,
                            "metric_type": metric_type,
                            "raw_value": str(raw_value),
                            "reason": "Regex pattern did not match",
                        }
                    )

    parsed_df = pd.DataFrame(
        parsed_rows, columns=["company_id", "metric_type", "period_years", "value_pct"]
    )

    failure_df = pd.DataFrame(
        failure_rows, columns=["company_id", "metric_type", "raw_value", "reason"]
    )

    # ======================================================
    # SAVE OUTPUTS
    # ======================================================

    parsed_df.to_csv(PARSED_FILE, index=False)

    failure_df.to_csv(FAILURE_FILE, index=False)

    print("\n" + "-" * 70)
    print("PARSER VALIDATION")
    print("-" * 70)

    print(f"Parsed rows   : {len(parsed_df)}")

    print(f"Failed entries: {len(failure_df)}")

    print(
        f"Companies     : " f"{parsed_df['company_id'].nunique()}"
        if not parsed_df.empty
        else "Companies     : 0"
    )

    if not parsed_df.empty:

        print("\nMetric distribution:")

        print(parsed_df["metric_type"].value_counts().to_string())

        print("\nPeriod distribution:")

        print(parsed_df["period_years"].value_counts().sort_index().to_string())

    print("\nOutput files:")

    print(PARSED_FILE)

    print(FAILURE_FILE)

    print("\n" + "=" * 70)
    print("DAY 29 PARSER COMPLETE")
    print("=" * 70)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    parse_analysis()
