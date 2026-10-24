import os
import sqlite3

import pandas as pd

# ==========================================================
# PATHS
# ==========================================================

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DB_FILE = os.path.join(BASE_DIR, "database", "n100.db")

OUTPUT_DIR = os.path.join(BASE_DIR, "output")

EXCEL_FILE = os.path.join(OUTPUT_DIR, "cashflow_intelligence.xlsx")

DISTRESS_FILE = os.path.join(OUTPUT_DIR, "distress_alerts.csv")


# ==========================================================
# HELPERS
# ==========================================================


def safe_float(value):
    if value is None or pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_divide(numerator, denominator):
    numerator = safe_float(numerator)
    denominator = safe_float(denominator)

    if numerator is None or denominator in (None, 0):
        return None

    return numerator / denominator


def calculate_cagr(first, last, years):
    first = safe_float(first)
    last = safe_float(last)

    if first is None or last is None:
        return None

    if first <= 0 or last <= 0:
        return None

    if years <= 0:
        return None

    try:
        return (((last / first) ** (1 / years)) - 1) * 100
    except (ValueError, ZeroDivisionError):
        return None


def sort_years(df):
    """
    Preserve the financial statement sequence.

    The source uses values such as:
    Mar-13, Mar-14, etc.
    """

    if df.empty:
        return df

    return df.reset_index(drop=True)


# ==========================================================
# CASH FLOW INTELLIGENCE
# ==========================================================


class CashFlowIntelligence:

    def __init__(self):

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        self.conn = sqlite3.connect(DB_FILE)

        self.cashflow = pd.read_sql_query(
            """
            SELECT
                id,
                company_id,
                year,
                operating_activity,
                investing_activity,
                financing_activity,
                net_cash_flow
            FROM cashflow
            """,
            self.conn,
        )

        self.pnl = pd.read_sql_query(
            """
            SELECT
                id,
                company_id,
                year,
                sales,
                operating_profit,
                net_profit
            FROM profitandloss
            """,
            self.conn,
        )

        self.companies = pd.read_sql_query(
            """
            SELECT *
            FROM companies
            """,
            self.conn,
        )

        self.ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                free_cash_flow
            FROM historical_financial_ratios
            """,
            self.conn,
        )

        self.balancesheet = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                borrowings
            FROM balancesheet
            """,
            self.conn,
        )

        self.sectors = pd.read_sql_query(
            """
            SELECT *
            FROM sectors
            """,
            self.conn,
        )

    # ======================================================
    # COMPANY IDS
    # ======================================================

    def get_company_ids(self):

        rows = self.conn.execute("""
            SELECT id
            FROM companies
            WHERE id IS NOT NULL
            ORDER BY id
            """).fetchall()

        return [str(row[0]).strip().upper() for row in rows]

    # ======================================================
    # SECTOR
    # ======================================================

    def get_sector(self, company_id):

        if self.companies.empty:
            return "Unknown"

        company_rows = self.companies[
            self.companies["id"].astype(str).str.strip().str.upper() == company_id
        ]

        if company_rows.empty:
            return "Unknown"

        row = company_rows.iloc[0]

        for column in ["sector", "broad_sector", "sector_name"]:

            if column in company_rows.columns:

                value = row[column]

                if value is not None and not pd.isna(value) and str(value).strip():
                    return str(value).strip()

        # Try sectors table if company table doesn't contain sector.
        if not self.sectors.empty:

            if "company_id" in self.sectors.columns:

                sector_rows = self.sectors[
                    self.sectors["company_id"].astype(str).str.strip().str.upper()
                    == company_id
                ]

                if not sector_rows.empty:

                    for column in ["sector", "broad_sector", "sector_name"]:

                        if column in sector_rows.columns:

                            value = sector_rows.iloc[0][column]

                            if value is not None and not pd.isna(value):
                                return str(value).strip()

        return "Unknown"

    # ======================================================
    # COMPANY CASH FLOW
    # ======================================================

    def get_cashflow(self, company_id):

        df = self.cashflow[
            self.cashflow["company_id"].astype(str).str.strip().str.upper()
            == company_id
        ].copy()

        return sort_years(df)

    # ======================================================
    # COMPANY P&L
    # ======================================================

    def get_pnl(self, company_id):

        df = self.pnl[
            self.pnl["company_id"].astype(str).str.strip().str.upper() == company_id
        ].copy()

        return sort_years(df)

    # ======================================================
    # COMPANY RATIOS
    # ======================================================

    def get_ratios(self, company_id):

        df = self.ratios[
            self.ratios["company_id"].astype(str).str.strip().str.upper() == company_id
        ].copy()

        return sort_years(df)

    # ======================================================
    # BALANCE SHEET
    # ======================================================

    def get_balance_sheet(self, company_id):

        df = self.balancesheet[
            self.balancesheet["company_id"].astype(str).str.strip().str.upper()
            == company_id
        ].copy()

        return sort_years(df)

    # ======================================================
    # CFO QUALITY
    # ======================================================

    def calculate_cfo_quality(self, company_id):

        cf = self.get_cashflow(company_id)

        pnl = self.get_pnl(company_id)

        if cf.empty or pnl.empty:
            return None, "Accrual Risk"

        merged = pd.merge(
            cf[["year", "operating_activity"]],
            pnl[["year", "net_profit"]],
            on="year",
            how="inner",
        )

        if merged.empty:
            return None, "Accrual Risk"

        scores = []

        for _, row in merged.iterrows():

            cfo = safe_float(row["operating_activity"])

            pat = safe_float(row["net_profit"])

            score = safe_divide(cfo, pat)

            if score is not None:
                scores.append(score)

        if not scores:
            return None, "Accrual Risk"

        last_five = scores[-5:]

        average_score = sum(last_five) / len(last_five)

        if average_score > 1.0:

            label = "High Quality"

        elif average_score >= 0.5:

            label = "Moderate"

        else:

            label = "Accrual Risk"

        return round(average_score, 2), label

    # ======================================================
    # CAPEX INTENSITY
    # ======================================================

    def calculate_capex_intensity(self, company_id):

        cf = self.get_cashflow(company_id)

        pnl = self.get_pnl(company_id)

        if cf.empty or pnl.empty:
            return None, "Capital Intensive"

        merged = pd.merge(
            cf[["year", "investing_activity"]],
            pnl[["year", "sales"]],
            on="year",
            how="inner",
        )

        if merged.empty:
            return None, "Capital Intensive"

        latest = merged.iloc[-1]

        investing = safe_float(latest["investing_activity"])

        sales = safe_float(latest["sales"])

        if sales in (None, 0):
            return None, "Capital Intensive"

        intensity = (abs(investing) / sales) * 100

        if intensity < 3:

            label = "Asset Light"

        elif intensity <= 8:

            label = "Moderate"

        else:

            label = "Capital Intensive"

        return round(intensity, 2), label

    # ======================================================
    # FCF CAGR
    # ======================================================

    def calculate_fcf_cagr(self, company_id):

        cf = self.get_cashflow(company_id)

        if len(cf) < 6:
            return None

        fcf_values = []

        for _, row in cf.iterrows():

            cfo = safe_float(row["operating_activity"])

            cfi = safe_float(row["investing_activity"])

            if cfo is not None and cfi is not None:

                fcf_values.append(cfo + cfi)

        if len(fcf_values) < 6:
            return None

        first = fcf_values[-6]
        latest = fcf_values[-1]

        return (
            round(calculate_cagr(first, latest, 5), 2)
            if calculate_cagr(first, latest, 5) is not None
            else None
        )

    # ======================================================
    # FCF CONVERSION
    # ======================================================

    def calculate_fcf_conversion(self, company_id):

        cf = self.get_cashflow(company_id)

        pnl = self.get_pnl(company_id)

        if cf.empty or pnl.empty:
            return None

        merged = pd.merge(
            cf[["year", "operating_activity", "investing_activity"]],
            pnl[["year", "operating_profit"]],
            on="year",
            how="inner",
        )

        if merged.empty:
            return None

        latest = merged.iloc[-1]

        cfo = safe_float(latest["operating_activity"])

        cfi = safe_float(latest["investing_activity"])

        operating_profit = safe_float(latest["operating_profit"])

        if cfo is None or cfi is None or operating_profit in (None, 0):
            return None

        fcf = cfo + cfi

        return round((fcf / operating_profit) * 100, 2)

    # ======================================================
    # DISTRESS SIGNAL
    # ======================================================

    def calculate_distress(self, company_id):

        cf = self.get_cashflow(company_id)

        if cf.empty:
            return False, None, None

        latest = cf.iloc[-1]

        cfo = safe_float(latest["operating_activity"])

        cff = safe_float(latest["financing_activity"])

        distress = cfo is not None and cff is not None and cfo < 0 and cff > 0

        return (distress, cfo, cff)

    # ======================================================
    # LATEST NET PROFIT
    # ======================================================

    def latest_net_profit(self, company_id):

        pnl = self.get_pnl(company_id)

        if pnl.empty:
            return None

        return safe_float(pnl.iloc[-1]["net_profit"])

    # ======================================================
    # DELEVERAGING
    # ======================================================

    def calculate_deleveraging(self, company_id):

        cf = self.get_cashflow(company_id)

        bs = self.get_balance_sheet(company_id)

        if cf.empty or bs.empty:
            return False

        latest_cf = cf.iloc[-1]

        cff = safe_float(latest_cf["financing_activity"])

        if cff is None or cff >= 0:
            return False

        if len(bs) < 2:
            return False

        previous_borrowings = safe_float(bs.iloc[-2]["borrowings"])

        latest_borrowings = safe_float(bs.iloc[-1]["borrowings"])

        if previous_borrowings is None or latest_borrowings is None:
            return False

        return latest_borrowings < previous_borrowings

    # ======================================================
    # CAPITAL ALLOCATION
    # ======================================================

    def capital_allocation_label(self, company_id):

        cf = self.get_cashflow(company_id)

        if cf.empty:
            return "Unknown"

        latest = cf.iloc[-1]

        cfo = safe_float(latest["operating_activity"])

        cfi = safe_float(latest["investing_activity"])

        cff = safe_float(latest["financing_activity"])

        if cfo is None or cfi is None or cff is None:
            return "Unknown"

        # Distress
        if cfo < 0 and cff > 0:

            return "Distress Signal"

        # Deleveraging
        if self.calculate_deleveraging(company_id):

            return "Deleveraging"

        # Strong reinvestment
        if cfo > 0 and cfi < 0:

            return "Reinvestor"

        # Cash accumulation / low reinvestment
        if cfo > 0 and cfi >= 0 and cff <= 0:

            return "Cash Generator"

        # External funding
        if cfo > 0 and cff > 0:

            return "Capital Raiser"

        # Asset monetisation
        if cfo > 0 and cfi > 0:

            return "Asset Monetiser"

        # Operating weakness
        if cfo < 0:

            return "Operating Stress"

        return "Balanced"

    # ======================================================
    # PROCESS ONE COMPANY
    # ======================================================

    def process_company(self, company_id):

        cfo_quality_score, cfo_label = self.calculate_cfo_quality(company_id)

        capex_intensity_pct, capex_label = self.calculate_capex_intensity(company_id)

        fcf_cagr_5yr = self.calculate_fcf_cagr(company_id)

        fcf_conversion_pct = self.calculate_fcf_conversion(company_id)

        distress_flag, latest_cfo, latest_cff = self.calculate_distress(company_id)

        latest_net_profit = self.latest_net_profit(company_id)

        deleveraging_flag = self.calculate_deleveraging(company_id)

        capital_label = self.capital_allocation_label(company_id)

        sector = self.get_sector(company_id)

        return {
            "company_id": company_id,
            "sector": sector,
            "cfo_quality_score": cfo_quality_score,
            "cfo_quality_label": cfo_label,
            "capex_intensity_pct": capex_intensity_pct,
            "capex_label": capex_label,
            "fcf_cagr_5yr": fcf_cagr_5yr,
            "fcf_conversion_pct": fcf_conversion_pct,
            "distress_flag": int(distress_flag),
            "deleveraging_flag": int(deleveraging_flag),
            "capital_allocation_label": capital_label,
            "_latest_cfo": latest_cfo,
            "_latest_cff": latest_cff,
            "_latest_net_profit": latest_net_profit,
        }

    # ======================================================
    # GENERATE OUTPUTS
    # ======================================================

    def generate(self):

        print("=" * 70)
        print("DAY 31 - CASH FLOW INTELLIGENCE")
        print("=" * 70)

        companies = self.get_company_ids()

        print(f"\nCompanies loaded: {len(companies)}")

        rows = []
        distress_rows = []

        for index, company_id in enumerate(companies, start=1):

            result = self.process_company(company_id)

            rows.append(result)

            if result["distress_flag"] == 1:

                distress_rows.append(
                    {
                        "company_id": company_id,
                        "sector": result["sector"],
                        "CFO": result["_latest_cfo"],
                        "CFF": result["_latest_cff"],
                        "latest_net_profit": result["_latest_net_profit"],
                    }
                )

            if index % 10 == 0:

                print(f"Processed " f"{index}/{len(companies)} companies")

        # ==================================================
        # MAIN OUTPUT
        # ==================================================

        output_columns = [
            "company_id",
            "sector",
            "cfo_quality_score",
            "cfo_quality_label",
            "capex_intensity_pct",
            "capex_label",
            "fcf_cagr_5yr",
            "fcf_conversion_pct",
            "distress_flag",
            "deleveraging_flag",
            "capital_allocation_label",
        ]

        output_df = pd.DataFrame(rows)[output_columns]

        output_df.to_excel(EXCEL_FILE, index=False)

        # ==================================================
        # DISTRESS OUTPUT
        # ==================================================

        distress_df = pd.DataFrame(
            distress_rows,
            columns=["company_id", "sector", "CFO", "CFF", "latest_net_profit"],
        )

        distress_df.to_csv(DISTRESS_FILE, index=False)

        # ==================================================
        # VALIDATION
        # ==================================================

        print("\n" + "-" * 70)
        print("CASH FLOW INTELLIGENCE VALIDATION")
        print("-" * 70)

        print(f"Companies expected : {len(companies)}")

        print(f"Rows generated     : {len(output_df)}")

        print(f"Distress companies : " f"{len(distress_df)}")

        print("\nCFO Quality labels:")

        print(output_df["cfo_quality_label"].value_counts(dropna=False).to_string())

        print("\nCapEx labels:")

        print(output_df["capex_label"].value_counts(dropna=False).to_string())

        print("\nCapital allocation patterns:")

        print(
            output_df["capital_allocation_label"].value_counts(dropna=False).to_string()
        )

        print("\nOutput files:")

        print(EXCEL_FILE)

        print(DISTRESS_FILE)

        print("\n" + "=" * 70)

        if len(output_df) == len(companies):

            print("DAY 31 CASH FLOW INTELLIGENCE COMPLETE")

        else:

            print("DAY 31 VALIDATION FAILED")

        print("=" * 70)


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    engine = CashFlowIntelligence()

    try:
        engine.generate()

    finally:
        engine.conn.close()
