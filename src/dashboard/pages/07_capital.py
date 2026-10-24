# ============================================================
# N100 FINANCIAL INTELLIGENCE PLATFORM
# DAY 25 - CAPITAL ALLOCATION MAP
# File: src/dashboard/pages/07_capital.py
# ============================================================

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Capital Allocation | Nifty 100 Analytics", page_icon="📊", layout="wide"
)


# ============================================================
# DATABASE PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "database" / "n100.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================


@st.cache_data(ttl=600)
def load_capital_data():

    if not DB_PATH.exists():
        return pd.DataFrame()

    conn = sqlite3.connect(str(DB_PATH))

    try:

        # ----------------------------------------------------
        # Companies + sectors
        # ----------------------------------------------------

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            conn,
        )

        sectors = pd.read_sql_query(
            """
            SELECT
                company_id,
                broad_sector,
                sub_sector
            FROM sectors
            """,
            conn,
        )

        # ----------------------------------------------------
        # Historical ratios
        # ----------------------------------------------------

        historical = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                revenue_growth,
                profit_growth,
                net_profit_margin,
                operating_profit_margin,
                roe,
                roce,
                debt_to_equity,
                interest_coverage,
                net_debt,
                free_cash_flow,
                cfo_quality,
                capex_intensity
            FROM historical_financial_ratios
            """,
            conn,
        )

        # ----------------------------------------------------
        # Current ratios - fallback
        # ----------------------------------------------------

        current = pd.read_sql_query(
            """
            SELECT
                company_id,
                revenue_growth,
                profit_growth,
                net_profit_margin,
                operating_profit_margin,
                roe,
                roce,
                debt_to_equity,
                interest_coverage,
                net_debt,
                free_cash_flow,
                cfo_quality,
                capex_intensity
            FROM financial_ratios
            """,
            conn,
        )

        return companies, sectors, historical, current

    finally:
        conn.close()


# ============================================================
# LOAD DATA
# ============================================================

loaded = load_capital_data()


if isinstance(loaded, pd.DataFrame) or loaded is None:

    st.error("Unable to load capital allocation data from the database.")
    st.stop()


companies, sectors, historical, current = loaded


# ============================================================
# BASIC VALIDATION
# ============================================================

required_company_columns = {"company_id", "company_name"}

required_sector_columns = {"company_id", "broad_sector", "sub_sector"}

required_ratio_columns = {
    "company_id",
    "roe",
    "roce",
    "debt_to_equity",
    "free_cash_flow",
}


if not required_company_columns.issubset(companies.columns):

    st.error("Required company columns are missing.")
    st.stop()


if not required_sector_columns.issubset(sectors.columns):

    st.error("Required sector columns are missing.")
    st.stop()


if not required_ratio_columns.issubset(historical.columns):

    st.error("Required historical ratio columns are missing.")
    st.stop()


# ============================================================
# CLEAN DATA
# ============================================================

companies = companies.copy()
sectors = sectors.copy()
historical = historical.copy()
current = current.copy()


companies["company_id"] = companies["company_id"].astype(str).str.strip().str.upper()

sectors["company_id"] = sectors["company_id"].astype(str).str.strip().str.upper()

historical["company_id"] = historical["company_id"].astype(str).str.strip().str.upper()

current["company_id"] = current["company_id"].astype(str).str.strip().str.upper()


# ============================================================
# NUMERIC COLUMNS
# ============================================================

numeric_columns = [
    "revenue_growth",
    "profit_growth",
    "net_profit_margin",
    "operating_profit_margin",
    "roe",
    "roce",
    "debt_to_equity",
    "interest_coverage",
    "net_debt",
    "free_cash_flow",
    "cfo_quality",
    "capex_intensity",
]


for column in numeric_columns:

    if column in historical.columns:

        historical[column] = pd.to_numeric(historical[column], errors="coerce")

    if column in current.columns:

        current[column] = pd.to_numeric(current[column], errors="coerce")


# ============================================================
# FIND LATEST HISTORICAL RECORD FOR EACH COMPANY
# ============================================================

if not historical.empty:

    # Prefer Mar 2024 where available.
    mar_2024 = historical[
        historical["year"].astype(str).str.strip().eq("Mar 2024")
    ].copy()

    if not mar_2024.empty:

        latest = mar_2024.copy()

    else:

        # --------------------------------------------
        # Generic latest-year fallback
        # --------------------------------------------

        historical["_year_num"] = pd.to_numeric(
            historical["year"].astype(str).str.extract(r"(\d{4})")[0], errors="coerce"
        )

        historical = historical.sort_values(["company_id", "_year_num"])

        latest = historical.groupby("company_id", as_index=False).tail(1).copy()

else:

    latest = pd.DataFrame()


# ============================================================
# FALLBACK TO CURRENT RATIOS
# ============================================================

if not current.empty:

    current = current.drop_duplicates(subset=["company_id"], keep="last")

    if latest.empty:

        latest = current.copy()

    else:

        latest = latest.merge(
            current, on="company_id", how="outer", suffixes=("", "_current")
        )

        for column in numeric_columns:

            current_column = f"{column}_current"

            if current_column in latest.columns:

                if column not in latest.columns:

                    latest[column] = latest[current_column]

                else:

                    latest[column] = latest[column].fillna(latest[current_column])

                latest.drop(columns=[current_column], inplace=True)


# ============================================================
# MERGE ALL DATA
# ============================================================

data = companies.merge(sectors, on="company_id", how="left")

data = data.merge(latest, on="company_id", how="left")


# ============================================================
# REMOVE DUPLICATES
# ============================================================

data = data.drop_duplicates(subset=["company_id"], keep="first").copy()


# ============================================================
# DISPLAY NAME
# ============================================================

data["Ticker"] = data["company_id"]

data["Company"] = data["company_name"].fillna(data["company_id"]).astype(str)

data["Sector"] = data["broad_sector"].fillna("Unknown").astype(str)

data["Sub-sector"] = data["sub_sector"].fillna("Unknown").astype(str)


# ============================================================
# NORMALIZE ROE / ROCE
#
# Database normally stores percentage values such as:
# 15.79
#
# If a value is stored as decimal:
# 0.1579
#
# convert it to:
# 15.79
# ============================================================


def normalize_percentage(series):

    series = pd.to_numeric(series, errors="coerce")

    result = series.copy()

    mask = result.notna() & (result.abs() <= 1.5)

    result.loc[mask] = result.loc[mask] * 100

    return result


data["ROE (%)"] = normalize_percentage(data["roe"])

data["ROCE (%)"] = normalize_percentage(data["roce"])


# ============================================================
# OTHER METRICS
# ============================================================

data["D/E"] = pd.to_numeric(data["debt_to_equity"], errors="coerce")

data["FCF"] = pd.to_numeric(data["free_cash_flow"], errors="coerce")

data["Revenue Growth (%)"] = pd.to_numeric(data["revenue_growth"], errors="coerce")

data["Profit Growth (%)"] = pd.to_numeric(data["profit_growth"], errors="coerce")

data["OPM (%)"] = pd.to_numeric(data["operating_profit_margin"], errors="coerce")

data["Interest Coverage"] = pd.to_numeric(data["interest_coverage"], errors="coerce")

data["CFO Quality"] = pd.to_numeric(data["cfo_quality"], errors="coerce")

data["CapEx Intensity"] = pd.to_numeric(data["capex_intensity"], errors="coerce")


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def safe_value(row, column, default=np.nan):

    value = row.get(column, default)

    try:

        value = float(value)

        if np.isnan(value):
            return default

        return value

    except (TypeError, ValueError):

        return default


# ============================================================
# CAPITAL ALLOCATION CLASSIFICATION
# ============================================================


def classify_capital_allocation(row):

    roe = safe_value(row, "ROE (%)")
    roce = safe_value(row, "ROCE (%)")
    de = safe_value(row, "D/E")
    fcf = safe_value(row, "FCF")
    revenue_growth = safe_value(row, "Revenue Growth (%)")
    profit_growth = safe_value(row, "Profit Growth (%)")
    opm = safe_value(row, "OPM (%)")
    cfo_quality = safe_value(row, "CFO Quality")

    # --------------------------------------------------------
    # Missing data
    # --------------------------------------------------------

    if np.isnan(roe) and np.isnan(roce) and np.isnan(de) and np.isnan(fcf):
        return "Weak Capital Efficiency"

    # --------------------------------------------------------
    # Conservative / Debt-Free
    # --------------------------------------------------------

    if (
        not np.isnan(de)
        and de <= 0.15
        and (np.isnan(fcf) or fcf >= 0)
        and (np.isnan(roe) or roe >= 10)
    ):
        return "Conservative / Debt-Free"

    # --------------------------------------------------------
    # Capital Intensive
    # --------------------------------------------------------

    if not np.isnan(de) and de >= 1.5:
        return "Capital Intensive"

    if not np.isnan(de) and de >= 1.0 and (not np.isnan(opm) and opm < 15):
        return "Capital Intensive"

    # --------------------------------------------------------
    # High Growth Reinvestors
    # --------------------------------------------------------

    if (not np.isnan(revenue_growth) and revenue_growth >= 15) or (
        not np.isnan(profit_growth) and profit_growth >= 20
    ):

        if np.isnan(fcf) or fcf >= 0:
            return "High Growth Reinvestors"

    # --------------------------------------------------------
    # Cash Generators
    # --------------------------------------------------------

    if (
        not np.isnan(fcf)
        and fcf > 0
        and (np.isnan(cfo_quality) or cfo_quality >= 1)
        and (np.isnan(roe) or roe >= 15)
    ):
        return "Cash Generators"

    # --------------------------------------------------------
    # Weak Capital Efficiency
    # --------------------------------------------------------

    if (not np.isnan(roe) and roe < 8) or (not np.isnan(roce) and roce < 10):
        return "Weak Capital Efficiency"

    # --------------------------------------------------------
    # Turnaround / Recovery
    # --------------------------------------------------------

    if (
        not np.isnan(profit_growth)
        and profit_growth > 20
        and (np.isnan(roe) or roe < 15)
    ):
        return "Turnaround / Recovery"

    # --------------------------------------------------------
    # Value Builders
    # --------------------------------------------------------

    if (
        (not np.isnan(roe) and roe >= 15)
        and (not np.isnan(roce) and roce >= 15)
        and (np.isnan(de) or de <= 0.75)
    ):
        return "Value Builders"

    # --------------------------------------------------------
    # Balanced Compounders
    # --------------------------------------------------------

    return "Balanced Compounders"


data["Capital Allocation Pattern"] = data.apply(classify_capital_allocation, axis=1)


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🗺️ Capital Allocation Map")

st.caption(
    "Analyze Nifty 100 companies based on their capital "
    "allocation and financial characteristics."
)

st.divider()


# ============================================================
# SECTION 1 - TREEMAP
# ============================================================

st.header("📊 Capital Allocation Patterns")

st.subheader("Nifty 100 Capital Allocation Patterns")


pattern_counts = (
    data["Capital Allocation Pattern"]
    .value_counts()
    .rename_axis("Pattern")
    .reset_index(name="Companies")
)


# ============================================================
# FORCE ALL 8 PATTERNS TO EXIST IN SUMMARY
# ============================================================

all_patterns = [
    "Conservative / Debt-Free",
    "Weak Capital Efficiency",
    "Capital Intensive",
    "High Growth Reinvestors",
    "Cash Generators",
    "Value Builders",
    "Balanced Compounders",
    "Turnaround / Recovery",
]


pattern_template = pd.DataFrame({"Pattern": all_patterns})

pattern_counts = pattern_template.merge(pattern_counts, on="Pattern", how="left")

pattern_counts["Companies"] = pattern_counts["Companies"].fillna(0).astype(int)


# ============================================================
# TREEMAP
# ============================================================

treemap_data = pattern_counts[pattern_counts["Companies"] > 0].copy()


if not treemap_data.empty:

    fig_tree = px.treemap(
        treemap_data, path=["Pattern"], values="Companies", color="Pattern", title=None
    )

    fig_tree.update_traces(
        textinfo="label+value",
        hovertemplate=("<b>%{label}</b><br>" "Companies: %{value}" "<extra></extra>"),
    )

    fig_tree.update_layout(height=560, margin=dict(l=5, r=5, t=10, b=10))

    st.plotly_chart(
        fig_tree, width="stretch", config={"displayModeBar": True, "responsive": True}
    )

else:

    st.info("No capital allocation data is available.")


# ============================================================
# SECTION 2 - COMPANY LIST
# ============================================================

st.divider()

st.header("🔎 Companies by Capital Allocation Pattern")


available_patterns = [
    pattern
    for pattern in all_patterns
    if pattern in set(data["Capital Allocation Pattern"])
]


if not available_patterns:

    st.warning("No capital allocation patterns are available.")

    st.stop()


selected_pattern = st.selectbox(
    "Select a capital allocation pattern", available_patterns
)


selected_companies = data[data["Capital Allocation Pattern"] == selected_pattern].copy()


st.write(
    f"**{len(selected_companies)} companies** " f"belong to **{selected_pattern}**."
)


# ============================================================
# COMPANY TABLE
# ============================================================

company_table = selected_companies[
    ["Ticker", "Company", "Sector", "Sub-sector", "ROE (%)", "ROCE (%)"]
].copy()


company_table["ROE (%)"] = pd.to_numeric(company_table["ROE (%)"], errors="coerce")

company_table["ROCE (%)"] = pd.to_numeric(company_table["ROCE (%)"], errors="coerce")


company_table["ROE (%)"] = company_table["ROE (%)"].round(2)

company_table["ROCE (%)"] = company_table["ROCE (%)"].round(2)


st.dataframe(
    company_table,
    width="stretch",
    hide_index=True,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
        "Company": st.column_config.TextColumn("Company", width="medium"),
        "Sector": st.column_config.TextColumn("Sector", width="medium"),
        "Sub-sector": st.column_config.TextColumn("Sub-sector", width="medium"),
        "ROE (%)": st.column_config.NumberColumn(
            "ROE (%)", format="%.2f%%", width="small"
        ),
        "ROCE (%)": st.column_config.NumberColumn(
            "ROCE (%)", format="%.2f%%", width="small"
        ),
    },
)


# ============================================================
# SECTION 3 - PATTERN SUMMARY
# ============================================================

st.divider()

st.header("📋 Pattern Summary")


summary = pattern_counts.copy()


total_companies = int(summary["Companies"].sum())


if total_companies > 0:

    summary["Share (%)"] = (summary["Companies"] / total_companies * 100).round(2)

else:

    summary["Share (%)"] = 0.0


summary_display = summary[["Pattern", "Companies", "Share (%)"]].copy()


summary_display = summary_display.rename(
    columns={"Pattern": "Capital Allocation Pattern"}
)


st.dataframe(
    summary_display,
    width="stretch",
    hide_index=True,
    column_config={
        "Capital Allocation Pattern": st.column_config.TextColumn(
            "Capital Allocation Pattern", width="large"
        ),
        "Companies": st.column_config.NumberColumn(
            "Companies", format="%d", width="small"
        ),
        "Share (%)": st.column_config.NumberColumn(
            "Share (%)", format="%.2f%%", width="small"
        ),
    },
)


# ============================================================
# KPI SUMMARY
# ============================================================

st.divider()


companies_analyzed = len(data)

companies_with_data = int(
    data[data[["ROE (%)", "ROCE (%)", "D/E", "FCF"]].notna().any(axis=1)].shape[0]
)


patterns_identified = int((summary["Companies"] > 0).sum())


col1, col2, col3 = st.columns(3)


with col1:

    st.success(f"Companies analyzed: {companies_analyzed}")


with col2:

    st.success(f"Patterns identified: {patterns_identified}")


with col3:

    st.success(f"Companies with data: {companies_with_data}")


# ============================================================
# FOOTER
# ============================================================

st.caption("Nifty 100 Financial Intelligence Platform • " "Capital Allocation Analysis")
