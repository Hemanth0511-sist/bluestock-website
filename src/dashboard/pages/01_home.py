import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# PATH SETUP
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


from dashboard.utils.db import (
    get_companies,
    get_market_cap,
    get_pl_all,
    get_rankings,
    get_ratios,
    get_sectors,
)

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def num(series):
    return pd.to_numeric(series, errors="coerce")


def pct(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}%"


def number(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}"


def extract_year(value):
    if pd.isna(value):
        return None
    text = str(value)
    for y in range(2010, 2031):
        if str(y) in text:
            return y
    return None


# ============================================================
# LOAD DATA
# ============================================================
try:
    companies = get_companies().copy()
except Exception as e:
    st.error(f"Unable to load companies: {e}")
    st.stop()

if companies.empty:
    st.error("No company data available.")
    st.stop()

companies["company_id"] = companies["company_id"].astype(str)
companies["company_name"] = (
    companies["company_name"].fillna(companies["company_id"]).astype(str)
)


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("📊 Nifty 100 Analytics")
st.sidebar.markdown("---")

selected_year = st.sidebar.selectbox(
    "Select Financial Year",
    list(range(2019, 2025)),
    index=5,
)
st.sidebar.caption("Home dashboard metrics are based on the selected financial year.")


# ============================================================
# HEADER
# ============================================================
st.title("📊 Nifty 100 Analytics")
st.write("Financial intelligence dashboard for the Nifty 100 universe")
st.divider()
st.header(f"📌 Universe Overview — {selected_year}")


# ============================================================
# RATIOS FOR SELECTED YEAR
# ============================================================
try:
    ratios = get_ratios(ticker=None, year=selected_year).copy()
except Exception as e:
    st.error(f"Unable to load historical ratios: {e}")
    ratios = pd.DataFrame()

if not ratios.empty:
    ratios["company_id"] = ratios["company_id"].astype(str)
    ratios = ratios.drop_duplicates(subset=["company_id", "year"], keep="first")


# ============================================================
# KPI 1 — AVERAGE ROE
# ============================================================
average_roe = None
if "roe" in ratios.columns:
    values = num(ratios["roe"]).dropna()
    if not values.empty:
        average_roe = values.mean()


# ============================================================
# KPI 2 — MEDIAN P/E
# ============================================================
median_pe = None
try:
    market = get_market_cap(selected_year).copy()
    if not market.empty and "pe_ratio" in market.columns:
        pe = num(market["pe_ratio"])
        pe = pe[(pe > 0) & (pe < 1000)].dropna()
        if not pe.empty:
            median_pe = pe.median()
except Exception as e:
    st.warning(f"Unable to load P/E data: {e}")


# ============================================================
# KPI 3 — MEDIAN D/E
# ============================================================
median_de = None
if "debt_to_equity" in ratios.columns:
    de = num(ratios["debt_to_equity"]).dropna()
    if not de.empty:
        median_de = de.median()


# ============================================================
# KPI 4 — TOTAL COMPANIES
# ============================================================
total_companies = len(companies)


# ============================================================
# KPI 5 — MEDIAN 5-YEAR REVENUE CAGR
# ============================================================
median_revenue_cagr = None
try:
    pl = get_pl_all().copy()
    if not pl.empty:
        pl["company_id"] = pl["company_id"].astype(str)
        pl["year_num"] = pl["year"].apply(extract_year)
        pl["sales"] = num(pl["sales"])

        start_year = selected_year - 5
        start = pl[pl["year_num"] == start_year][["company_id", "sales"]].rename(
            columns={"sales": "sales_start"}
        )
        end = pl[pl["year_num"] == selected_year][["company_id", "sales"]].rename(
            columns={"sales": "sales_end"}
        )

        cagr = start.merge(end, on="company_id", how="inner")
        cagr = cagr[(cagr["sales_start"] > 0) & (cagr["sales_end"] > 0)]

        if not cagr.empty:
            cagr["revenue_cagr_5yr"] = (
                (cagr["sales_end"] / cagr["sales_start"]) ** (1 / 5) - 1
            ) * 100
            cagr["revenue_cagr_5yr"] = cagr["revenue_cagr_5yr"].replace(
                [float("inf"), float("-inf")], pd.NA
            )
            cagr_values = num(cagr["revenue_cagr_5yr"]).dropna()
            if not cagr_values.empty:
                median_revenue_cagr = cagr_values.median()
except Exception as e:
    st.warning(f"Unable to calculate 5-year revenue CAGR: {e}")


# ============================================================
# KPI 6 — DEBT-FREE COMPANIES
# ============================================================
debt_free_count = 0
if "debt_to_equity" in ratios.columns:
    de = num(ratios["debt_to_equity"])
    debt_free_count = int((de.fillna(999999) <= 0).sum())


# ============================================================
# KPI DISPLAY
# ============================================================
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Average ROE", pct(average_roe))
k2.metric("Median P/E", number(median_pe))
k3.metric("Median D/E", number(median_de))
k4.metric("Total Companies", total_companies)
k5.metric("Median Revenue CAGR 5yr", pct(median_revenue_cagr))
k6.metric("Debt-Free Companies", debt_free_count)


st.divider()
s1, s2, s3 = st.columns(3)
s1.success(f"Companies loaded: {total_companies}")
s2.success(f"Selected year: {selected_year}")
s3.success(f"Ratio records: {len(ratios)}")


# ============================================================
# SECTOR DONUT
# ============================================================
st.divider()
st.header("🏭 Companies by Sector")

try:
    sectors = get_sectors().copy()
except Exception as e:
    st.error(f"Unable to load sector data: {e}")
    sectors = pd.DataFrame()

if not sectors.empty:
    sectors["company_id"] = sectors["company_id"].astype(str)
    sector_counts = (
        sectors[sectors["company_id"].isin(companies["company_id"])]
        .drop_duplicates(subset=["company_id"])
        .groupby("broad_sector")
        .size()
        .reset_index(name="company_count")
        .sort_values("company_count", ascending=False)
    )

    if not sector_counts.empty:
        st.caption(
            f"{len(sector_counts)} sectors represented across {sector_counts['company_count'].sum()} companies."
        )
        fig = px.pie(
            sector_counts,
            names="broad_sector",
            values="company_count",
            hole=0.55,
            title="Sector Breakdown",
        )
        fig.update_layout(height=500, margin=dict(l=20, r=20, t=70, b=20))
        fig.update_traces(textposition="inside", textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No sector records found.")
else:
    st.warning("Sector information is not available.")


# ============================================================
# TOP 5 BY COMPOSITE SCORE
# ============================================================
st.divider()
st.header("🏆 Top 5 Companies by Composite Quality Score")

try:
    rankings = get_rankings().copy()
except Exception as e:
    st.warning(f"Unable to load company rankings: {e}")
    rankings = pd.DataFrame()

if rankings.empty:
    st.info("Quality ranking data is not available.")
else:
    rankings["company_id"] = rankings["company_id"].astype(str)
    top5 = (
        rankings.sort_values("final_score", ascending=False)
        .head(5)
        .merge(
            companies[["company_id", "company_name"]],
            on="company_id",
            how="left",
        )
    )

    display = top5[
        [
            "company_id",
            "company_name",
            "final_score",
            "quality_score",
            "recommendation",
            "overall_rank",
        ]
    ].copy()

    display.columns = [
        "Company ID",
        "Company Name",
        "Composite Score",
        "Quality Score",
        "Recommendation",
        "Overall Rank",
    ]

    st.dataframe(display, use_container_width=True, hide_index=True)


st.divider()
st.caption(
    "All dashboard metrics are calculated from the N100 SQLite database. Missing or unavailable values are displayed as N/A."
)
