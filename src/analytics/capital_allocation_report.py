import os
import sqlite3

import numpy as np
import pandas as pd

# ============================================================
# DAY 32 - CAPITAL ALLOCATION REPORT
# ============================================================

DB_PATH = "database/n100.db"
OUTPUT_DIR = "output"

CASHFLOW_OUTPUT = os.path.join(OUTPUT_DIR, "cashflow_intelligence.xlsx")

PATTERN_CHANGES_OUTPUT = os.path.join(OUTPUT_DIR, "pattern_changes.csv")

DISTRIBUTION_OUTPUT = os.path.join(OUTPUT_DIR, "capital_allocation_distribution.csv")


# ============================================================
# HELPERS
# ============================================================


def clean_number(value):
    try:
        if value is None:
            return np.nan

        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return np.nan

        return value

    except (TypeError, ValueError):
        return np.nan


def classify_pattern(row):
    """
    Capital allocation classification.

    Priority:
    1. Distress Signal
    2. Deleveraging
    3. Cash Generator
    4. High Growth Reinvestor
    5. Capital Intensive
    6. Operating Stress
    7. Value Builder
    8. Conservative / Debt-Free
    """

    cfo = clean_number(row.get("operating_activity"))
    cfi = clean_number(row.get("investing_activity"))
    cff = clean_number(row.get("financing_activity"))

    sales = clean_number(row.get("sales"))
    net_profit = clean_number(row.get("net_profit"))
    borrowings = clean_number(row.get("borrowings"))

    roe = clean_number(row.get("roe"))
    roce = clean_number(row.get("roce"))
    debt_to_equity = clean_number(row.get("debt_to_equity"))

    # --------------------------------------------------------
    # Distress
    # --------------------------------------------------------
    if not np.isnan(cfo) and not np.isnan(cff) and cfo < 0 and cff > 0:
        return "Distress Signal"

    # --------------------------------------------------------
    # Deleveraging
    # --------------------------------------------------------
    if not np.isnan(cff) and cff < 0 and not np.isnan(borrowings) and borrowings >= 0:
        return "Deleveraging"

    # --------------------------------------------------------
    # Cash Generator
    # --------------------------------------------------------
    if (
        not np.isnan(cfo)
        and not np.isnan(net_profit)
        and cfo > 0
        and net_profit > 0
        and (np.isnan(cfi) or cfi >= 0)
    ):
        return "Cash Generator"

    # --------------------------------------------------------
    # High Growth Reinvestor
    # --------------------------------------------------------
    if (
        not np.isnan(cfo)
        and cfo > 0
        and not np.isnan(cfi)
        and cfi < 0
        and not np.isnan(roe)
        and roe >= 15
    ):
        return "High Growth Reinvestor"

    # --------------------------------------------------------
    # Capital Intensive
    # --------------------------------------------------------
    if not np.isnan(cfi) and not np.isnan(sales) and sales > 0:
        capex_intensity = abs(cfi) / sales * 100

        if capex_intensity > 8:
            return "Capital Intensive"

    # --------------------------------------------------------
    # Operating Stress
    # --------------------------------------------------------
    if not np.isnan(cfo) and not np.isnan(net_profit) and cfo < 0 and net_profit < 0:
        return "Operating Stress"

    # --------------------------------------------------------
    # Value Builder
    # --------------------------------------------------------
    if (
        not np.isnan(roe)
        and not np.isnan(roce)
        and roe >= 12
        and roce >= 12
        and (np.isnan(debt_to_equity) or debt_to_equity <= 1.5)
    ):
        return "Value Builder"

    # --------------------------------------------------------
    # Conservative / Debt-Free
    # --------------------------------------------------------
    if (
        not np.isnan(debt_to_equity)
        and debt_to_equity <= 0
        and not np.isnan(cfo)
        and cfo >= 0
    ):
        return "Conservative / Debt-Free"

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------
    return "Unknown"


# ============================================================
# LOAD DATA
# ============================================================


def load_data(conn):

    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        """,
        conn,
    )

    cashflow = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity,
            net_cash_flow
        FROM cashflow
        """,
        conn,
    )

    pnl = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            sales,
            net_profit
        FROM profitandloss
        """,
        conn,
    )

    balance = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            borrowings
        FROM balancesheet
        """,
        conn,
    )

    ratios = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            roe,
            roce,
            debt_to_equity
        FROM historical_financial_ratios
        """,
        conn,
    )

    return companies, cashflow, pnl, balance, ratios


# ============================================================
# BUILD HISTORICAL DATA
# ============================================================


def build_historical(companies, cashflow, pnl, balance, ratios):

    df = cashflow.merge(pnl, on=["company_id", "year"], how="left")

    df = df.merge(balance, on=["company_id", "year"], how="left")

    df = df.merge(ratios, on=["company_id", "year"], how="left")

    df = df.merge(companies, on="company_id", how="left")

    return df


# ============================================================
# YEAR NORMALIZATION
# ============================================================


def year_sort_key(value):

    if pd.isna(value):
        return 9999

    text = str(value)

    digits = "".join(char for char in text if char.isdigit())

    if len(digits) >= 2:

        try:
            return int(digits[-2:])

        except ValueError:
            pass

    return 9999


# ============================================================
# GENERATE PATTERNS
# ============================================================


def generate_patterns(df, valid_company_ids, companies):
    """
    Generate capital-allocation patterns for every company in the
    master companies table.

    Important:
    - The master companies table is the authoritative 92-company universe.
    - Companies without cash-flow history are NOT dropped.
    - Such companies receive one "Unknown" row so they remain part of
      the 92-company analysis.
    - Deleveraging requires CFF < 0 AND borrowings declining YoY.
    """

    records = []

    valid_company_ids = {
        str(x).strip().upper() for x in valid_company_ids if pd.notna(x)
    }

    # Only analyze companies that actually exist in the master table.
    df = df[
        df["company_id"].astype(str).str.strip().str.upper().isin(valid_company_ids)
    ].copy()

    company_ids = sorted(valid_company_ids)

    print(f"Companies available for pattern analysis: " f"{len(company_ids)}")

    for index, company_id in enumerate(company_ids, start=1):

        company_df = df[
            df["company_id"].astype(str).str.strip().str.upper() == company_id
        ].copy()

        # --------------------------------------------------------
        # NO CASH-FLOW DATA
        # --------------------------------------------------------
        # Example: ATGL is present in companies but has no cashflow
        # records. Keep it in the 92-company universe and classify
        # it as Unknown instead of silently dropping it.
        # --------------------------------------------------------

        if company_df.empty:

            company_name = ""

            matching_company = companies[
                companies["company_id"].astype(str).str.strip().str.upper()
                == company_id
            ]

            if not matching_company.empty:
                company_name = matching_company.iloc[0]["company_name"]

            records.append(
                {
                    "company_id": company_id,
                    "company_name": company_name,
                    "year": "N/A",
                    "capital_allocation_pattern": "Unknown",
                }
            )

            print(f"{company_id}: No cash-flow history -> Unknown")

            continue

        company_df["_sort"] = company_df["year"].apply(year_sort_key)

        company_df = company_df.sort_values("_sort").reset_index(drop=True)

        previous_borrowings = np.nan

        for _, row in company_df.iterrows():

            # ----------------------------------------------------
            # Deleveraging
            # Requires BOTH:
            #   CFF < 0
            #   Borrowings declining YoY
            # ----------------------------------------------------

            cff = clean_number(row.get("financing_activity"))

            borrowings = clean_number(row.get("borrowings"))

            if (
                not np.isnan(cff)
                and cff < 0
                and not np.isnan(borrowings)
                and not np.isnan(previous_borrowings)
                and borrowings < previous_borrowings
            ):
                pattern = "Deleveraging"
            else:
                pattern = classify_pattern(row)

            records.append(
                {
                    "company_id": company_id,
                    "company_name": row.get("company_name"),
                    "year": row.get("year"),
                    "capital_allocation_pattern": pattern,
                }
            )

            if not np.isnan(borrowings):
                previous_borrowings = borrowings

        if index % 10 == 0:
            print(f"Processed {index}/{len(company_ids)} companies")

    return pd.DataFrame(records)


# ============================================================
# PATTERN CHANGES
# ============================================================


def build_pattern_changes(pattern_df):

    changes = []

    for company_id, group in pattern_df.groupby("company_id"):

        group = group.copy()

        group["_sort"] = group["year"].apply(year_sort_key)

        group = group.sort_values("_sort")

        previous_pattern = None
        previous_year = None

        for _, row in group.iterrows():

            current_pattern = row["capital_allocation_pattern"]

            current_year = row["year"]

            if previous_pattern is not None and current_pattern != previous_pattern:

                changes.append(
                    {
                        "company_id": company_id,
                        "company_name": row.get("company_name"),
                        "from_year": previous_year,
                        "to_year": current_year,
                        "from_pattern": previous_pattern,
                        "to_pattern": current_pattern,
                    }
                )

            previous_pattern = current_pattern
            previous_year = current_year

    return pd.DataFrame(changes)


# ============================================================
# LATEST YEAR DISTRIBUTION
# ============================================================


def latest_distribution(pattern_df):

    latest_rows = []

    for company_id, group in pattern_df.groupby("company_id"):

        group = group.copy()

        group["_sort"] = group["year"].apply(year_sort_key)

        group = group.sort_values("_sort")

        latest_rows.append(group.iloc[-1])

    latest_df = pd.DataFrame(latest_rows)

    distribution = (
        latest_df["capital_allocation_pattern"]
        .value_counts()
        .rename_axis("capital_allocation_pattern")
        .reset_index(name="company_count")
    )

    return latest_df, distribution


# ============================================================
# UPDATE CASHFLOW EXCEL
# ============================================================


def update_cashflow_excel(pattern_df, latest_df):

    if not os.path.exists(CASHFLOW_OUTPUT):

        print("\nWARNING: cashflow_intelligence.xlsx " "not found.")

        return

    cashflow_df = pd.read_excel(CASHFLOW_OUTPUT)

    # Remove previous allocation column
    if "capital_allocation_label" in cashflow_df.columns:

        cashflow_df = cashflow_df.drop(columns=["capital_allocation_label"])

    allocation = latest_df[["company_id", "capital_allocation_pattern"]].rename(
        columns={"capital_allocation_pattern": "capital_allocation_label"}
    )

    cashflow_df["company_id"] = (
        cashflow_df["company_id"].astype(str).str.strip().str.upper()
    )

    allocation["company_id"] = (
        allocation["company_id"].astype(str).str.strip().str.upper()
    )

    cashflow_df = cashflow_df.merge(allocation, on="company_id", how="left")

    cashflow_df["capital_allocation_label"] = cashflow_df[
        "capital_allocation_label"
    ].fillna("Unknown")

    cashflow_df.to_excel(CASHFLOW_OUTPUT, index=False)

    print("\nUpdated:")
    print(CASHFLOW_OUTPUT)


# ============================================================
# MAIN
# ============================================================


def main():

    print("=" * 70)
    print("DAY 32 - CAPITAL ALLOCATION REPORT")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    try:

        print("\nLoading database data...")

        companies, cashflow, pnl, balance, ratios = load_data(conn)

        print(f"Companies loaded : {len(companies)}")

        print(f"Cashflow rows    : {len(cashflow)}")

        print(f"P&L rows         : {len(pnl)}")

        print(f"Balance rows     : {len(balance)}")

        print(f"Ratio rows       : {len(ratios)}")

        # ----------------------------------------------------
        # BUILD DATA
        # ----------------------------------------------------

        historical = build_historical(companies, cashflow, pnl, balance, ratios)

        print(f"Historical rows  : {len(historical)}")

        # ----------------------------------------------------
        # GENERATE PATTERNS
        # ----------------------------------------------------

        valid_company_ids = companies["company_id"].dropna().tolist()

        pattern_df = generate_patterns(historical, valid_company_ids, companies)

        # ----------------------------------------------------
        # COMPANY COVERAGE VALIDATION
        # ----------------------------------------------------

        analyzed_ids = set(pattern_df["company_id"].astype(str).str.strip().str.upper())

        expected_ids = set(valid_company_ids)

        missing_ids = sorted(expected_ids - analyzed_ids)

        if missing_ids:
            raise RuntimeError(
                "Company coverage failure. Missing companies: " + ", ".join(missing_ids)
            )

        # ----------------------------------------------------
        # LATEST YEAR
        # ----------------------------------------------------

        latest_df, distribution = latest_distribution(pattern_df)

        # ----------------------------------------------------
        # PATTERN CHANGES
        # ----------------------------------------------------

        changes = build_pattern_changes(pattern_df)

        changes.to_csv(PATTERN_CHANGES_OUTPUT, index=False)

        distribution.to_csv(DISTRIBUTION_OUTPUT, index=False)

        # ----------------------------------------------------
        # UPDATE CASHFLOW OUTPUT
        # ----------------------------------------------------

        update_cashflow_excel(pattern_df, latest_df)

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        print("\n" + "-" * 70)
        print("CAPITAL ALLOCATION VALIDATION")
        print("-" * 70)

        print(f"Companies expected : {len(companies)}")

        analyzed_count = pattern_df["company_id"].nunique()

        print(f"Companies analyzed : {analyzed_count}")

        if analyzed_count == len(companies):
            print("Company coverage   : PASS (all companies included)")
        else:
            print("Company coverage   : FAIL")

        if missing_ids:
            print("Missing companies  : " + ", ".join(missing_ids))
        else:
            print("Missing companies  : None")

        print(f"Historical pattern rows : " f"{len(pattern_df)}")

        print(f"Pattern changes : " f"{len(changes)}")

        print("\nLatest-year distribution:")

        print(distribution.to_string(index=False))

        print("\nOutput files:")

        print(os.path.abspath(PATTERN_CHANGES_OUTPUT))

        print(os.path.abspath(DISTRIBUTION_OUTPUT))

        print(os.path.abspath(CASHFLOW_OUTPUT))

        print("\n" + "=" * 70)
        print("DAY 32 CAPITAL ALLOCATION COMPLETE")
        print("=" * 70)

    finally:

        conn.close()


if __name__ == "__main__":
    main()
