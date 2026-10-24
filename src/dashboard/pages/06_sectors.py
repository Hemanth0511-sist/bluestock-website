import sys
from pathlib import Path

# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS
# ============================================================

import re

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_market_cap,
    get_pl,
    get_ratios,
    get_sectors,
)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Sector Analysis | Nifty 100 Analytics",
    page_icon="🏭",
    layout="wide",
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def numeric_value(value):
    """
    Safely convert a value to numeric.
    """

    try:
        value = pd.to_numeric(value, errors="coerce")

        if pd.isna(value):
            return None

        return float(value)

    except Exception:
        return None


def normalize_roe_percentage(value):
    """
    Normalize ROE to percentage points.

    The database should normally store ROE as a percentage
    (for example 22.41 means 22.41%). If an older/current
    ratio record is still stored as a decimal fraction
    (for example 0.2241), convert it to 22.41.
    """
    value = numeric_value(value)

    if value is None:
        return None

    if abs(value) <= 1:
        return value * 100

    return value


def extract_year(value):
    """
    Extract four-digit year from values such as:
        Mar 2024
        Sep 2024
        2024
    """

    if pd.isna(value):
        return None

    text = str(value)

    match = re.search(r"(\d{4})", text)

    if match:
        return int(match.group(1))

    return None


def latest_annual_row(df):
    """
    Return the latest available annual row.

    March records are preferred when available.
    """

    if df is None or df.empty:
        return pd.Series(dtype="object")

    data = df.copy()

    if "year" not in data.columns:
        return data.iloc[-1]

    data["_year_number"] = data["year"].apply(extract_year)

    data["_year_number"] = pd.to_numeric(data["_year_number"], errors="coerce")

    data = data.dropna(subset=["_year_number"])

    if data.empty:
        return pd.Series(dtype="object")

    # Prefer March annual data.
    march_data = data[data["year"].astype(str).str.startswith("Mar")].copy()

    if not march_data.empty:
        data = march_data

    data = data.sort_values("_year_number")

    return data.iloc[-1]


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🏭 Sector Analysis")

st.write(
    "Compare revenue, ROE and market capitalization "
    "across Nifty 100 sectors and sub-sectors."
)

st.divider()


# ============================================================
# LOAD DATABASE DATA
# ============================================================

companies = get_companies()

sectors = get_sectors()

market_cap = get_market_cap()


# ============================================================
# BASIC VALIDATION
# ============================================================

if companies is None or companies.empty:

    st.error("No company data was found in the database.")

    st.stop()


if sectors is None or sectors.empty:

    st.error("No sector data was found in the database.")

    st.stop()


# ============================================================
# PREPARE COMPANY DATA
# ============================================================

company_df = companies.copy()

sector_df = sectors.copy()


# ============================================================
# ENSURE SECTOR COLUMNS EXIST
# ============================================================

if "broad_sector" not in company_df.columns or "sub_sector" not in company_df.columns:

    required_sector_columns = ["company_id", "broad_sector", "sub_sector"]

    available_columns = [
        column for column in required_sector_columns if column in sector_df.columns
    ]

    sector_mapping = sector_df[available_columns].drop_duplicates()

    company_df = company_df.merge(sector_mapping, on="company_id", how="left")


# ============================================================
# VALIDATE COMPANY ID
# ============================================================

if "company_id" not in company_df.columns:

    st.error("Company ID column is missing from company data.")

    st.stop()


# ============================================================
# GET AVAILABLE SECTORS
# ============================================================

if "broad_sector" not in company_df.columns:

    st.error("Broad sector information is not available.")

    st.stop()


available_sectors = sorted(
    company_df["broad_sector"].dropna().astype(str).unique().tolist()
)


if not available_sectors:

    st.error("No sectors are available in the database.")

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("🏭 Sector Controls")

selected_sector = st.sidebar.selectbox("Select Sector", available_sectors)

st.sidebar.caption("Bubble chart: Revenue vs ROE")

st.sidebar.caption("Bubble size: Market Capitalization")

st.sidebar.caption("Colour: Sub-sector")


# ============================================================
# FILTER SELECTED SECTOR
# ============================================================

sector_companies = company_df[
    company_df["broad_sector"].astype(str) == selected_sector
].copy()


if sector_companies.empty:

    st.warning(f"No companies found in {selected_sector}.")

    st.stop()


# ============================================================
# SECTOR HEADER
# ============================================================

st.subheader(f"📊 {selected_sector}")


# ============================================================
# PREPARE MARKET CAP DATA
# ============================================================

market_cap_latest = pd.DataFrame()


if market_cap is not None and not market_cap.empty:

    market_cap_latest = market_cap.copy()

    if "year" in market_cap_latest.columns:

        market_cap_latest["_year_number"] = market_cap_latest["year"].apply(
            extract_year
        )

        market_cap_latest["_year_number"] = pd.to_numeric(
            market_cap_latest["_year_number"], errors="coerce"
        )

        market_cap_latest = market_cap_latest.dropna(subset=["_year_number"]).copy()

        # Prefer March annual records.
        march_market_cap = market_cap_latest[
            market_cap_latest["year"].astype(str).str.startswith("Mar")
        ].copy()

        if not march_market_cap.empty:

            market_cap_latest = march_market_cap

        if not market_cap_latest.empty:

            latest_market_year = market_cap_latest["_year_number"].max()

            market_cap_latest = market_cap_latest[
                market_cap_latest["_year_number"] == latest_market_year
            ].copy()

            market_cap_latest = market_cap_latest.drop_duplicates(
                subset=["company_id"], keep="last"
            )


# ============================================================
# BUILD ANALYSIS DATA
# ============================================================

analysis_rows = []


for _, company in sector_companies.iterrows():

    ticker = company["company_id"]

    company_name = company.get("company_name", ticker)

    sub_sector = company.get("sub_sector", "Unknown")

    # --------------------------------------------------------
    # REVENUE
    # --------------------------------------------------------

    revenue = None

    try:

        pl = get_pl(ticker)

        if pl is not None and not pl.empty:

            latest_pl = latest_annual_row(pl)

            if not latest_pl.empty and "sales" in latest_pl.index:

                revenue = numeric_value(latest_pl["sales"])

    except Exception:

        revenue = None

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    roe = None

    try:

        ratios = get_ratios(ticker)

        if ratios is not None and not ratios.empty and "roe" in ratios.columns:

            ratio_data = ratios.copy()

            # Prefer the latest annual year.
            if "year" in ratio_data.columns:

                ratio_data["_year_number"] = ratio_data["year"].apply(extract_year)

                ratio_data["_year_number"] = pd.to_numeric(
                    ratio_data["_year_number"], errors="coerce"
                )

                ratio_data = ratio_data.dropna(subset=["_year_number"]).sort_values(
                    "_year_number"
                )

                if not ratio_data.empty:

                    roe_values = pd.to_numeric(
                        ratio_data["roe"], errors="coerce"
                    ).dropna()

                else:

                    roe_values = pd.Series(dtype="float64")

            else:

                roe_values = pd.to_numeric(ratio_data["roe"], errors="coerce").dropna()

            if not roe_values.empty:

                roe = normalize_roe_percentage(roe_values.iloc[-1])

    except Exception:

        roe = None

    # --------------------------------------------------------
    # MARKET CAP
    # --------------------------------------------------------

    company_market_cap = None

    if (
        market_cap_latest is not None
        and not market_cap_latest.empty
        and "company_id" in market_cap_latest.columns
    ):

        cap_rows = market_cap_latest[
            market_cap_latest["company_id"].astype(str) == str(ticker)
        ]

        if not cap_rows.empty:

            if "market_cap_crore" in cap_rows.columns:

                company_market_cap = numeric_value(cap_rows.iloc[0]["market_cap_crore"])

    # --------------------------------------------------------
    # ADD ROW
    # --------------------------------------------------------

    analysis_rows.append(
        {
            "company_id": ticker,
            "Company": company_name,
            "Sub-sector": (sub_sector if pd.notna(sub_sector) else "Unknown"),
            "Revenue": revenue,
            "ROE": roe,
            "Market Cap": company_market_cap,
        }
    )


analysis_df = pd.DataFrame(analysis_rows)


# ============================================================
# CLEAN DATA
# ============================================================

for column in ["Revenue", "ROE", "Market Cap"]:

    analysis_df[column] = pd.to_numeric(analysis_df[column], errors="coerce")


analysis_df["Sub-sector"] = analysis_df["Sub-sector"].fillna("Unknown").astype(str)


# ============================================================
# TOP KPI CARDS
# ============================================================

metric1, metric2, metric3, metric4 = st.columns(4)


company_count = len(analysis_df)


median_revenue = None

if analysis_df["Revenue"].notna().any():

    median_revenue = analysis_df["Revenue"].median()


median_roe = None

if analysis_df["ROE"].notna().any():

    median_roe = analysis_df["ROE"].median()


median_market_cap = None

if analysis_df["Market Cap"].notna().any():

    median_market_cap = analysis_df["Market Cap"].median()


with metric1:

    st.metric("Companies", f"{company_count:,}")


with metric2:

    if median_revenue is not None:

        st.metric("Median Revenue", f"{median_revenue:,.2f}")

    else:

        st.metric("Median Revenue", "N/A")


with metric3:

    if median_roe is not None:

        st.metric("Median ROE", f"{median_roe:.2f}%")

    else:

        st.metric("Median ROE", "N/A")


with metric4:

    if median_market_cap is not None:

        st.metric("Median Market Cap", f"{median_market_cap:,.0f}")

    else:

        st.metric("Median Market Cap", "N/A")


# ============================================================
# BUBBLE CHART
# ============================================================

st.divider()

st.subheader("🫧 Revenue vs ROE — Market Cap Bubble")


bubble_df = analysis_df[
    ["company_id", "Company", "Sub-sector", "Revenue", "ROE", "Market Cap"]
].copy()


bubble_df = bubble_df.dropna(subset=["Revenue", "ROE"])


if bubble_df.empty:

    st.warning(
        "Insufficient Revenue and ROE data " "to create the sector bubble chart."
    )

else:

    # Market cap must be non-negative
    # for bubble sizing.

    bubble_df["Market Cap"] = bubble_df["Market Cap"].fillna(0).clip(lower=0)

    # If all market caps are unavailable,
    # use a constant bubble size.

    if bubble_df["Market Cap"].max() <= 0:

        bubble_df["Market Cap"] = 1

    fig = px.scatter(
        bubble_df,
        x="Revenue",
        y="ROE",
        size="Market Cap",
        color="Sub-sector",
        hover_name="Company",
        hover_data={
            "company_id": True,
            "Revenue": ":,.2f",
            "ROE": ":.2f",
            "Market Cap": ":,.2f",
            "Sub-sector": True,
        },
        title=(f"{selected_sector} — " "Revenue vs ROE"),
        labels={
            "Revenue": "Revenue (₹ Crore)",
            "ROE": "ROE (%)",
            "Market Cap": "Market Cap (₹ Crore)",
        },
        size_max=55,
    )

    fig.update_layout(
        height=600,
        xaxis_title="Revenue (₹ Crore)",
        yaxis_title="ROE (%)",
        legend_title="Sub-sector",
        margin=dict(l=20, r=20, t=70, b=20),
    )

    st.plotly_chart(fig, width="stretch")


# ============================================================
# SECTOR MEDIAN KPI CARDS
# ============================================================

st.divider()

st.subheader("📊 Sector Median KPIs")


kpi1, kpi2, kpi3 = st.columns(3)


# ------------------------------------------------------------
# Median Revenue
# ------------------------------------------------------------

if "Revenue" in analysis_df.columns and analysis_df["Revenue"].notna().any():

    median_revenue = analysis_df["Revenue"].median()

    with kpi1:

        st.metric("Median Revenue", f"₹{median_revenue:,.2f} Cr")

else:

    with kpi1:

        st.metric("Median Revenue", "N/A")


# ------------------------------------------------------------
# Median ROE
# ------------------------------------------------------------

if "ROE" in analysis_df.columns and analysis_df["ROE"].notna().any():

    median_roe = analysis_df["ROE"].median()

    with kpi2:

        st.metric("Median ROE", f"{median_roe:.2f}%")

else:

    with kpi2:

        st.metric("Median ROE", "N/A")


# ------------------------------------------------------------
# Median Market Cap
# ------------------------------------------------------------

if "Market Cap" in analysis_df.columns and analysis_df["Market Cap"].notna().any():

    median_market_cap = analysis_df["Market Cap"].median()

    with kpi3:

        st.metric("Median Market Cap", f"₹{median_market_cap:,.0f} Cr")

else:

    with kpi3:

        st.metric("Median Market Cap", "N/A")


st.caption(
    "Median values are calculated using the "
    "companies available in the selected sector."
)


# ============================================================
# SUB-SECTOR SUMMARY
# ============================================================

st.divider()

st.subheader("🏷️ Sub-sector Summary")


subsector_summary = (
    analysis_df.groupby("Sub-sector", dropna=False)
    .agg(
        Companies=("company_id", "nunique"),
        Median_Revenue=("Revenue", "median"),
        Median_ROE=("ROE", "median"),
        Median_Market_Cap=("Market Cap", "median"),
    )
    .reset_index()
)


subsector_summary = subsector_summary.sort_values("Companies", ascending=False)


if not subsector_summary.empty:

    display_summary = subsector_summary.rename(
        columns={
            "Median_Revenue": "Median Revenue",
            "Median_ROE": "Median ROE",
            "Median_Market_Cap": "Median Market Cap",
        }
    )

    display_summary["Median Revenue"] = display_summary["Median Revenue"].round(2)

    display_summary["Median ROE"] = display_summary["Median ROE"].round(2)

    display_summary["Median Market Cap"] = display_summary["Median Market Cap"].round(2)

    st.dataframe(display_summary, width="stretch", hide_index=True)


else:

    st.info("Sub-sector information is not available.")


# ============================================================
# COMPANY TABLE
# ============================================================

st.divider()

st.subheader("🏢 Companies in Selected Sector")


company_table = analysis_df[
    ["company_id", "Company", "Sub-sector", "Revenue", "ROE", "Market Cap"]
].copy()


company_table = company_table.rename(
    columns={
        "company_id": "Ticker",
        "Company": "Company Name",
        "Revenue": "Revenue (₹ Cr)",
        "ROE": "ROE (%)",
        "Market Cap": "Market Cap (₹ Cr)",
    }
)


company_table = company_table.sort_values("Company Name")

if "ROE (%)" in company_table.columns:
    company_table["ROE (%)"] = pd.to_numeric(
        company_table["ROE (%)"], errors="coerce"
    ).round(2)

if "Revenue (₹ Cr)" in company_table.columns:
    company_table["Revenue (₹ Cr)"] = pd.to_numeric(
        company_table["Revenue (₹ Cr)"], errors="coerce"
    ).round(2)

if "Market Cap (₹ Cr)" in company_table.columns:
    company_table["Market Cap (₹ Cr)"] = pd.to_numeric(
        company_table["Market Cap (₹ Cr)"], errors="coerce"
    ).round(2)


st.dataframe(
    company_table,
    width="stretch",
    hide_index=True,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
        "Company Name": st.column_config.TextColumn("Company Name", width="medium"),
        "Sub-sector": st.column_config.TextColumn("Sub-sector", width="medium"),
        "Revenue (₹ Cr)": st.column_config.NumberColumn(
            "Revenue (₹ Cr)", format="%.2f", width="medium"
        ),
        "ROE (%)": st.column_config.NumberColumn(
            "ROE (%)", format="%.2f%%", width="small"
        ),
        "Market Cap (₹ Cr)": st.column_config.NumberColumn(
            "Market Cap (₹ Cr)", format="%.2f", width="medium"
        ),
    },
)


# ============================================================
# DATA STATUS
# ============================================================

st.divider()

valid_revenue = int(analysis_df["Revenue"].notna().sum())


valid_roe = int(analysis_df["ROE"].notna().sum())


valid_market_cap = int(analysis_df["Market Cap"].notna().sum())


status1, status2, status3 = st.columns(3)


with status1:

    st.success(f"Companies: {company_count}")


with status2:

    st.success(f"Revenue data: " f"{valid_revenue}/{company_count}")


with status3:

    st.success(f"Market Cap data: " f"{valid_market_cap}/{company_count}")


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption("Nifty 100 Financial Intelligence Platform • " "Sector Analysis")
