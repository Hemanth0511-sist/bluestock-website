# ============================================================
# N100 FINANCIAL INTELLIGENCE PLATFORM
# DAY 26 - VALUATION MODULE
# ============================================================

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "database" / "n100.db"

OUTPUT_DIR = PROJECT_ROOT / "output"

VALUATION_XLSX = OUTPUT_DIR / "valuation_summary.xlsx"

VALUATION_CSV = OUTPUT_DIR / "valuation_flags.csv"


# ============================================================
# CONFIGURATION
# ============================================================

LATEST_YEAR = 2024

FIVE_YEAR_START = 2020

CAUTION_MULTIPLIER = 1.5

DISCOUNT_MULTIPLIER = 0.7


# ============================================================
# DATABASE CONNECTION
# ============================================================


def get_connection():

    if not DB_PATH.exists():

        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    return sqlite3.connect(str(DB_PATH))


# ============================================================
# LOAD COMPANIES
# ============================================================


def load_companies(conn):

    query = """
        SELECT
            id AS company_id,
            company_name
        FROM companies
    """

    return pd.read_sql_query(query, conn)


# ============================================================
# LOAD SECTORS
# ============================================================


def load_sectors(conn):

    query = """
        SELECT
            company_id,
            broad_sector,
            sub_sector
        FROM sectors
    """

    return pd.read_sql_query(query, conn)


# ============================================================
# LOAD MARKET CAP DATA
# ============================================================


def load_market_cap(conn):

    query = """
        SELECT
            company_id,
            year,
            market_cap_crore,
            pe_ratio,
            pb_ratio,
            ev_ebitda,
            dividend_yield_pct
        FROM market_cap
        WHERE year BETWEEN ? AND ?
        ORDER BY company_id, year
    """

    return pd.read_sql_query(query, conn, params=(FIVE_YEAR_START, LATEST_YEAR))


# ============================================================
# LOAD HISTORICAL FCF
# ============================================================


def load_historical_ratios(conn):

    query = """
        SELECT
            company_id,
            year,
            free_cash_flow
        FROM historical_financial_ratios
    """

    return pd.read_sql_query(query, conn)


# ============================================================
# CLEAN YEAR VALUE
# ============================================================


def extract_year(value):

    if value is None:
        return np.nan

    text = str(value).strip()

    # Handles:
    # 2024
    # Mar 2024
    # Sep 2024

    digits = text[-4:]

    if digits.isdigit():

        return int(digits)

    return np.nan


# ============================================================
# MEDIAN HELPER
# ============================================================


def safe_median(series):

    numeric = pd.to_numeric(series, errors="coerce")

    numeric = numeric.replace([np.inf, -np.inf], np.nan)

    numeric = numeric.dropna()

    if numeric.empty:

        return np.nan

    return float(numeric.median())


# ============================================================
# MAIN VALUATION CALCULATION
# ============================================================


def calculate_valuation():

    print("\n")
    print("=" * 70)
    print("DAY 26 - VALUATION MODULE")
    print("=" * 70)

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # Connect database
    # --------------------------------------------------------

    conn = get_connection()

    try:

        print("\nLoading database data...")

        companies = load_companies(conn)

        sectors = load_sectors(conn)

        market_cap = load_market_cap(conn)

        ratios = load_historical_ratios(conn)

    finally:

        conn.close()

    # --------------------------------------------------------
    # Validate company count
    # --------------------------------------------------------

    print(f"Companies loaded: {len(companies)}")

    print(f"Sector records loaded: {len(sectors)}")

    print(f"Market-cap records loaded: {len(market_cap)}")

    print(f"Historical ratio records loaded: {len(ratios)}")

    # --------------------------------------------------------
    # Clean company IDs
    # --------------------------------------------------------

    for df in [companies, sectors, market_cap, ratios]:

        df["company_id"] = df["company_id"].astype(str).str.strip().str.upper()

    # --------------------------------------------------------
    # Clean numeric market-cap columns
    # --------------------------------------------------------

    market_numeric = [
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
    ]

    for column in market_numeric:

        market_cap[column] = pd.to_numeric(market_cap[column], errors="coerce")

    # --------------------------------------------------------
    # Clean FCF
    # --------------------------------------------------------

    ratios["free_cash_flow"] = pd.to_numeric(ratios["free_cash_flow"], errors="coerce")

    # --------------------------------------------------------
    # Extract year from historical ratios
    # --------------------------------------------------------

    ratios["year_num"] = ratios["year"].apply(extract_year)

    ratios = ratios[ratios["year_num"].notna()].copy()

    ratios["year_num"] = ratios["year_num"].astype(int)

    # ========================================================
    # 1. LATEST MARKET DATA - 2024
    # ========================================================

    latest_market = market_cap[market_cap["year"] == LATEST_YEAR].copy()

    # If duplicate 2024 records exist,
    # keep one record per company.
    latest_market = latest_market.sort_values(["company_id"]).drop_duplicates(
        subset=["company_id"], keep="last"
    )

    print(f"\nLatest market records: " f"{len(latest_market)}")

    # ========================================================
    # 2. FCF - LATEST AVAILABLE YEAR
    # ========================================================

    # Prefer Mar 2024 / 2024 FCF.
    # Since historical_financial_ratios can contain
    # multiple periods, select the latest year available.

    ratios_sorted = ratios.sort_values(["company_id", "year_num"])

    latest_fcf = ratios_sorted.groupby("company_id", as_index=False).tail(1).copy()

    latest_fcf = latest_fcf[["company_id", "year_num", "free_cash_flow"]]

    latest_fcf = latest_fcf.rename(columns={"year_num": "fcf_year"})

    # ========================================================
    # 3. FIVE-YEAR MEDIAN P/E
    # ========================================================

    five_year_market = market_cap[
        market_cap["year"].between(FIVE_YEAR_START, LATEST_YEAR)
    ].copy()

    # P/E must be positive for a meaningful
    # valuation multiple.
    five_year_market.loc[five_year_market["pe_ratio"] <= 0, "pe_ratio"] = np.nan

    five_year_median_pe = (
        five_year_market.groupby("company_id")["pe_ratio"].median().reset_index()
    )

    five_year_median_pe = five_year_median_pe.rename(
        columns={"pe_ratio": "5yr_median_PE"}
    )

    # ========================================================
    # 4. SECTOR MEDIAN P/E - LATEST YEAR
    # ========================================================

    sector_pe = latest_market.merge(
        sectors[["company_id", "broad_sector"]], on="company_id", how="left"
    )

    # Only positive P/E values
    # are meaningful.
    sector_pe.loc[sector_pe["pe_ratio"] <= 0, "pe_ratio"] = np.nan

    sector_median_pe = (
        sector_pe.groupby("broad_sector")["pe_ratio"].median().reset_index()
    )

    sector_median_pe = sector_median_pe.rename(columns={"pe_ratio": "sector_median_PE"})

    # ========================================================
    # 5. BUILD 92-COMPANY OUTPUT
    # ========================================================

    result = companies.copy()

    # --------------------------------------------------------
    # Add sector
    # --------------------------------------------------------

    sector_clean = sectors[["company_id", "broad_sector"]].drop_duplicates(
        subset=["company_id"], keep="first"
    )

    result = result.merge(sector_clean, on="company_id", how="left")

    # --------------------------------------------------------
    # Add latest market data
    # --------------------------------------------------------

    result = result.merge(
        latest_market[
            [
                "company_id",
                "year",
                "market_cap_crore",
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "dividend_yield_pct",
            ]
        ],
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Add latest FCF
    # --------------------------------------------------------

    result = result.merge(
        latest_fcf[["company_id", "fcf_year", "free_cash_flow"]],
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Add five-year median PE
    # --------------------------------------------------------

    result = result.merge(five_year_median_pe, on="company_id", how="left")

    # --------------------------------------------------------
    # Add sector median PE
    # --------------------------------------------------------

    result = result.merge(sector_median_pe, on="broad_sector", how="left")

    # ========================================================
    # 6. FCF YIELD
    # ========================================================

    result["FCF_yield_pct"] = np.nan

    valid_fcf_yield = (
        result["market_cap_crore"].notna()
        & result["market_cap_crore"].gt(0)
        & result["free_cash_flow"].notna()
    )

    result.loc[valid_fcf_yield, "FCF_yield_pct"] = (
        result.loc[valid_fcf_yield, "free_cash_flow"]
        / result.loc[valid_fcf_yield, "market_cap_crore"]
        * 100
    )

    # ========================================================
    # 7. P/E VS SECTOR MEDIAN
    # ========================================================

    result["PE_vs_sector_median_pct"] = np.nan

    valid_sector_pe = (
        result["pe_ratio"].notna()
        & result["pe_ratio"].gt(0)
        & result["sector_median_PE"].notna()
        & result["sector_median_PE"].gt(0)
    )

    result.loc[valid_sector_pe, "PE_vs_sector_median_pct"] = (
        (
            result.loc[valid_sector_pe, "pe_ratio"]
            / result.loc[valid_sector_pe, "sector_median_PE"]
        )
        - 1
    ) * 100

    # ========================================================
    # 8. VALUATION FLAG
    # ========================================================

    def valuation_flag(row):

        pe = row["pe_ratio"]

        sector_median = row["sector_median_PE"]

        if pd.isna(pe) or pe <= 0 or pd.isna(sector_median) or sector_median <= 0:

            return "Fair"

        if pe > (sector_median * CAUTION_MULTIPLIER):

            return "Caution"

        if pe < (sector_median * DISCOUNT_MULTIPLIER):

            return "Discount"

        return "Fair"

    result["flag"] = result.apply(valuation_flag, axis=1)

    # ========================================================
    # 9. RENAME OUTPUT COLUMNS
    # ========================================================

    result = result.rename(
        columns={
            "company_name": "company_name",
            "broad_sector": "sector",
            "pe_ratio": "P/E",
            "pb_ratio": "P/B",
            "ev_ebitda": "EV/EBITDA",
        }
    )

    # ========================================================
    # 10. REQUIRED OUTPUT COLUMNS
    # ========================================================

    output_columns = [
        "company_id",
        "company_name",
        "sector",
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
        "flag",
    ]

    result = result[output_columns].copy()

    # ========================================================
    # 11. ROUND NUMERIC VALUES
    # ========================================================

    rounding_columns = [
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
    ]

    for column in rounding_columns:

        result[column] = pd.to_numeric(result[column], errors="coerce").round(2)

    # ========================================================
    # 12. SORT BY COMPANY ID
    # ========================================================

    result = result.sort_values("company_id").reset_index(drop=True)

    # ========================================================
    # 13. VALIDATION
    # ========================================================

    print("\n")
    print("-" * 70)
    print("VALUATION VALIDATION")
    print("-" * 70)

    print(f"Total companies: {len(result)}")

    print(f"Companies with P/E: " f"{result['P/E'].notna().sum()}")

    print(f"Companies with FCF yield: " f"{result['FCF_yield_pct'].notna().sum()}")

    print(
        f"Companies with sector median PE: " f"{result['5yr_median_PE'].notna().sum()}"
    )

    print("\nFlag distribution:")

    print(result["flag"].value_counts().to_string())

    # ========================================================
    # 14. SAVE EXCEL
    # ========================================================

    result.to_excel(VALUATION_XLSX, index=False)

    print("\nExcel created:")

    print(VALUATION_XLSX)

    # ========================================================
    # 15. CREATE FLAG CSV
    # ========================================================

    flags = result[result["flag"].isin(["Caution", "Discount"])].copy()

    flags.to_csv(VALUATION_CSV, index=False)

    print("\nCSV created:")

    print(VALUATION_CSV)

    # ========================================================
    # 16. PREVIEW
    # ========================================================

    print("\n")
    print("-" * 70)
    print("VALUATION PREVIEW")
    print("-" * 70)

    print(result.head(10).to_string(index=False))

    print("\n")
    print("=" * 70)
    print("DAY 26 VALUATION COMPLETE")
    print("=" * 70)

    return result


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":

    calculate_valuation()
