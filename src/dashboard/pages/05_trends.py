import re
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

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_bs,
    get_cf,
    get_companies,
    get_historical_ratios,
    get_pl,
)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Trend Analysis | Nifty 100 Analytics",
    page_icon="📈",
    layout="wide",
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def year_number(value):
    """
    Extract four-digit year from values such as:

    Mar 2024
    Dec 2023
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


def prepare_year_column(df):
    """
    Add a numeric year column and sort chronologically.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()

    if "year" not in result.columns:
        return result

    result["_year_number"] = result["year"].apply(year_number)

    result["_year_number"] = pd.to_numeric(result["_year_number"], errors="coerce")

    result = result.dropna(subset=["_year_number"])

    result = result.sort_values("_year_number")

    return result


def prepare_annual_data(df):
    """
    Keep annual March financial-year observations.

    This prevents periods such as Sep 2024 from being mixed
    with Mar 2024 in annual trend charts.

    If March records are unavailable, the available records
    are retained.
    """

    result = prepare_year_column(df)

    if result.empty:
        return result

    if "year" not in result.columns:
        return result

    result["_period_month"] = (
        result["year"]
        .astype(str)
        .str.extract(r"^([A-Za-z]{3})", expand=False)
        .str.title()
    )

    march_data = result[result["_period_month"] == "Mar"].copy()

    # Prefer March annual records whenever they exist.
    if not march_data.empty:
        result = march_data

    # One observation per year.
    result = (
        result.sort_values("_year_number")
        .drop_duplicates(subset=["_year_number"], keep="last")
        .reset_index(drop=True)
    )

    result = result.drop(columns=["_period_month"], errors="ignore")

    return result


def numeric_series(df, column):
    """
    Safely convert a dataframe column to numeric.
    """

    if df is None or df.empty:
        return pd.Series(dtype="float64")

    if column not in df.columns:
        return pd.Series(dtype="float64")

    return pd.to_numeric(df[column], errors="coerce")


def calculate_growth(start, end, years):
    """
    Calculate CAGR.

    CAGR is not calculated when the starting value is
    zero or negative.
    """

    if pd.isna(start) or pd.isna(end):
        return None

    if years <= 0:
        return None

    if start <= 0:
        return None

    try:

        return ((float(end) / float(start)) ** (1 / years) - 1) * 100

    except Exception:

        return None


def calculate_cagr(df, column, years):
    """
    Calculate CAGR using annual financial data.

    The latest available annual value is compared with
    the closest available annual value at least N years
    earlier.
    """

    if df is None or df.empty:
        return None

    if column not in df.columns:
        return None

    if "_year_number" not in df.columns:
        return None

    data = df[["_year_number", column]].copy()

    data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=["_year_number", column])

    if data.empty:
        return None

    data = data.sort_values("_year_number").drop_duplicates(
        subset=["_year_number"], keep="last"
    )

    latest_year = int(data["_year_number"].iloc[-1])

    latest_value = data[column].iloc[-1]

    target_year = latest_year - years

    previous = data[data["_year_number"] <= target_year]

    if previous.empty:
        return None

    start_value = previous[column].iloc[-1]

    return calculate_growth(start_value, latest_value, years)


def calculate_yoy_growth(df, value_column):
    """
    Calculate year-over-year growth from the underlying
    annual financial data.

    This is used for the Historical Growth Metrics table,
    so the table and CAGR calculations use the same P&L
    source.
    """

    if df is None or df.empty or value_column not in df.columns:
        return pd.Series(dtype="float64")

    values = pd.to_numeric(df[value_column], errors="coerce")

    previous = values.shift(1)

    growth = ((values / previous) - 1) * 100

    # Do not calculate growth from zero or negative
    # previous-year values.
    growth = growth.where(previous > 0)

    return growth


def format_percent(value):
    """
    Format a percentage safely.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return f"{float(value):.2f}%"


# ============================================================
# HEADER
# ============================================================

st.title("📈 Trend & Growth Analysis")

st.caption(
    "Analyze long-term financial trends, growth rates "
    "and year-over-year performance for Nifty 100 companies."
)

st.divider()


# ============================================================
# LOAD COMPANIES
# ============================================================

companies = get_companies()

if companies is None or companies.empty:

    st.error("No company data was found in the database.")

    st.stop()


# ============================================================
# COMPANY OPTIONS
# ============================================================

company_options = companies[["company_id", "company_name"]].drop_duplicates()


company_options["display"] = (
    company_options["company_id"].astype(str)
    + " — "
    + company_options["company_name"].astype(str)
)


company_options = company_options.sort_values("company_name").reset_index(drop=True)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("📊 Trend Controls")


selected_display = st.sidebar.selectbox(
    "Select Company", company_options["display"].tolist()
)


selected_company = company_options[company_options["display"] == selected_display]


if selected_company.empty:

    st.error("Company not found.")

    st.stop()


ticker = selected_company.iloc[0]["company_id"]


company_name = selected_company.iloc[0]["company_name"]


# ============================================================
# COMPANY HEADER
# ============================================================

st.subheader(f"📊 {company_name}")

st.caption(f"Ticker: {ticker}")


# ============================================================
# LOAD DATA
# ============================================================

pl = get_pl(ticker)

bs = get_bs(ticker)

cf = get_cf(ticker)

# financial_ratios contains latest ratios only.
# historical_financial_ratios contains year-wise ratios.

ratios = get_historical_ratios(ticker)


# ============================================================
# PREPARE ANNUAL DATA
# ============================================================

pl = prepare_annual_data(pl)

bs = prepare_annual_data(bs)

cf = prepare_annual_data(cf)

ratios = prepare_annual_data(ratios)


# ============================================================
# DATA AVAILABILITY
# ============================================================

if pl.empty:

    st.warning("No historical Profit & Loss data is available " "for this company.")


# ============================================================
# AVAILABLE YEARS
# ============================================================

all_years = set()


for dataframe in [pl, bs, cf, ratios]:

    if (
        dataframe is not None
        and not dataframe.empty
        and "_year_number" in dataframe.columns
    ):

        all_years.update(dataframe["_year_number"].dropna().astype(int).tolist())


all_years = sorted(all_years)


if not all_years:

    st.error("No historical year information is available " "for this company.")

    st.stop()


latest_year = all_years[-1]


# ============================================================
# GROWTH SNAPSHOT
# ============================================================

st.divider()

st.subheader("📌 Growth Snapshot")


# ------------------------------------------------------------
# REVENUE CAGR
# ------------------------------------------------------------

revenue_1y = calculate_cagr(pl, "sales", 1)

revenue_3y = calculate_cagr(pl, "sales", 3)

revenue_5y = calculate_cagr(pl, "sales", 5)

revenue_10y = calculate_cagr(pl, "sales", 10)


# ------------------------------------------------------------
# PAT CAGR
# ------------------------------------------------------------

pat_1y = calculate_cagr(pl, "net_profit", 1)

pat_3y = calculate_cagr(pl, "net_profit", 3)

pat_5y = calculate_cagr(pl, "net_profit", 5)

pat_10y = calculate_cagr(pl, "net_profit", 10)


# ------------------------------------------------------------
# KPI ROW 1
# ------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric("Revenue Growth 1Y", format_percent(revenue_1y))


with c2:

    st.metric("Revenue CAGR 3Y", format_percent(revenue_3y))


with c3:

    st.metric("Revenue CAGR 5Y", format_percent(revenue_5y))


with c4:

    st.metric("Revenue CAGR 10Y", format_percent(revenue_10y))


# ------------------------------------------------------------
# KPI ROW 2
# ------------------------------------------------------------

c5, c6, c7, c8 = st.columns(4)


with c5:

    st.metric("PAT Growth 1Y", format_percent(pat_1y))


with c6:

    st.metric("PAT CAGR 3Y", format_percent(pat_3y))


with c7:

    st.metric("PAT CAGR 5Y", format_percent(pat_5y))


with c8:

    st.metric("PAT CAGR 10Y", format_percent(pat_10y))


# ============================================================
# REVENUE & NET PROFIT TREND
# ============================================================

st.divider()

st.subheader("📈 Revenue & Net Profit — 10 Year Trend")


if not pl.empty:

    chart_df = pl.tail(10).copy()

    available_columns = []

    if "sales" in chart_df.columns:

        available_columns.append("sales")

    if "net_profit" in chart_df.columns:

        available_columns.append("net_profit")

    if available_columns:

        plot_df = chart_df[["year", "_year_number"] + available_columns].copy()

        plot_df = plot_df.rename(
            columns={"sales": "Revenue", "net_profit": "Net Profit"}
        )

        plot_df = plot_df.drop(columns=["_year_number"])

        plot_df = plot_df.melt(id_vars="year", var_name="Metric", value_name="Value")

        plot_df["Value"] = pd.to_numeric(plot_df["Value"], errors="coerce")

        plot_df = plot_df.dropna(subset=["Value"])

        if not plot_df.empty:

            fig = px.bar(
                plot_df,
                x="year",
                y="Value",
                color="Metric",
                barmode="group",
                title="Revenue vs Net Profit",
                labels={"year": "Financial Year", "Value": "₹ Crore"},
            )

            fig.update_layout(height=500, legend_title_text="")

            st.plotly_chart(fig, width="stretch")

        else:

            st.info("Revenue and Net Profit values " "are not available.")

    else:

        st.info("Required P&L columns are not available.")


else:

    st.info("No Profit & Loss history available.")


# ============================================================
# PROFITABILITY TREND
# ============================================================

st.divider()

st.subheader("📊 Profitability Trend")


if not ratios.empty:

    ratio_chart = ratios.tail(10).copy()

    metric_columns = []

    if "net_profit_margin" in ratio_chart.columns:

        metric_columns.append("net_profit_margin")

    if "operating_profit_margin" in ratio_chart.columns:

        metric_columns.append("operating_profit_margin")

    if metric_columns:

        plot_df = ratio_chart[["year", "_year_number"] + metric_columns].copy()

        plot_df = plot_df.rename(
            columns={
                "net_profit_margin": "Net Profit Margin",
                "operating_profit_margin": "Operating Profit Margin",
            }
        )

        plot_df = plot_df.drop(columns=["_year_number"])

        plot_df = plot_df.melt(id_vars="year", var_name="Metric", value_name="Value")

        plot_df["Value"] = pd.to_numeric(plot_df["Value"], errors="coerce")

        plot_df = plot_df.dropna(subset=["Value"])

        if not plot_df.empty:

            fig = px.line(
                plot_df,
                x="year",
                y="Value",
                color="Metric",
                markers=True,
                title="Profitability Margins",
            )

            fig.update_layout(
                height=450,
                yaxis_title="Percentage (%)",
                xaxis_title="Financial Year",
                legend_title_text="",
            )

            st.plotly_chart(fig, width="stretch")

        else:

            st.info("Profitability ratio values " "are not available.")

    else:

        st.info("Historical profitability ratios " "are not available.")


else:

    st.info("No historical ratio data available.")


# ============================================================
# ROE / ROCE TREND
# ============================================================

st.divider()

st.subheader("📈 ROE & ROCE Trend")


if not ratios.empty:

    return_df = ratios.tail(10).copy()

    return_columns = []

    if "roe" in return_df.columns:

        return_columns.append("roe")

    if "roce" in return_df.columns:

        return_columns.append("roce")

    if return_columns:

        plot_df = return_df[["year", "_year_number"] + return_columns].copy()

        plot_df = plot_df.rename(columns={"roe": "ROE", "roce": "ROCE"})

        plot_df = plot_df.drop(columns=["_year_number"])

        plot_df = plot_df.melt(id_vars="year", var_name="Metric", value_name="Value")

        plot_df["Value"] = pd.to_numeric(plot_df["Value"], errors="coerce")

        plot_df = plot_df.dropna(subset=["Value"])

        if not plot_df.empty:

            fig = px.line(
                plot_df,
                x="year",
                y="Value",
                color="Metric",
                markers=True,
                title="Return on Equity vs Return on Capital",
            )

            fig.update_layout(
                height=450,
                yaxis_title="Percentage (%)",
                xaxis_title="Financial Year",
                legend_title_text="",
            )

            st.plotly_chart(fig, width="stretch")

        else:

            st.info("ROE / ROCE data is not available.")

    else:

        st.info("ROE and ROCE columns are not available.")


else:

    st.info("No historical return data available.")


# ============================================================
# HISTORICAL GROWTH METRICS
# ============================================================

st.divider()

st.subheader("🚀 Historical Growth Metrics")


growth_rows = []


# IMPORTANT:
# Use Profit & Loss data here instead of the historical
# ratio growth columns.
#
# This keeps the table consistent with the same underlying
# sales and net_profit values used for the CAGR KPIs.

if not pl.empty and "sales" in pl.columns:

    growth_df = pl.copy()

    # Revenue YoY
    growth_df["Revenue Growth (%)"] = calculate_yoy_growth(growth_df, "sales")

    # Profit YoY
    if "net_profit" in growth_df.columns:

        growth_df["Profit Growth (%)"] = calculate_yoy_growth(growth_df, "net_profit")

    else:

        growth_df["Profit Growth (%)"] = pd.NA

    # Last 10 annual observations
    growth_df = growth_df.tail(10)

    for _, row in growth_df.iterrows():

        growth_rows.append(
            {
                "Year": row["year"],
                "Revenue Growth (%)": row.get("Revenue Growth (%)"),
                "Profit Growth (%)": row.get("Profit Growth (%)"),
            }
        )


if growth_rows:

    growth_table = pd.DataFrame(growth_rows)

    for column in ["Revenue Growth (%)", "Profit Growth (%)"]:

        growth_table[column] = pd.to_numeric(growth_table[column], errors="coerce")

    growth_table = growth_table.round(2)

    st.dataframe(growth_table, width="stretch", hide_index=True)


else:

    st.info(
        "Historical growth metrics are not available "
        "from the underlying Profit & Loss data."
    )


# ============================================================
# BALANCE SHEET TREND
# ============================================================

st.divider()

st.subheader("🏦 Balance Sheet — 10 Year Trend")


if not bs.empty:

    bs_chart = bs.tail(10).copy()

    bs_columns = []

    if "total_assets" in bs_chart.columns:

        bs_columns.append("total_assets")

    if "borrowings" in bs_chart.columns:

        bs_columns.append("borrowings")

    if bs_columns:

        plot_df = bs_chart[["year", "_year_number"] + bs_columns].copy()

        plot_df = plot_df.rename(
            columns={"total_assets": "Total Assets", "borrowings": "Borrowings"}
        )

        plot_df = plot_df.drop(columns=["_year_number"])

        plot_df = plot_df.melt(id_vars="year", var_name="Metric", value_name="Value")

        plot_df["Value"] = pd.to_numeric(plot_df["Value"], errors="coerce")

        plot_df = plot_df.dropna(subset=["Value"])

        if not plot_df.empty:

            fig = px.bar(
                plot_df,
                x="year",
                y="Value",
                color="Metric",
                barmode="group",
                title="Total Assets vs Borrowings",
                labels={"year": "Financial Year", "Value": "₹ Crore"},
            )

            fig.update_layout(height=450, legend_title_text="")

            st.plotly_chart(fig, width="stretch")

        else:

            st.info("Balance Sheet values are not available.")

    else:

        st.info("Required Balance Sheet columns " "are not available.")


else:

    st.info("No Balance Sheet history available.")


# ============================================================
# CASH FLOW TREND
# ============================================================

st.divider()

st.subheader("💰 Cash Flow Trend")


if not cf.empty:

    cf_chart = cf.tail(10).copy()

    cf_columns = []

    if "operating_activity" in cf_chart.columns:

        cf_columns.append("operating_activity")

    if "investing_activity" in cf_chart.columns:

        cf_columns.append("investing_activity")

    if "financing_activity" in cf_chart.columns:

        cf_columns.append("financing_activity")

    if cf_columns:

        plot_df = cf_chart[["year", "_year_number"] + cf_columns].copy()

        plot_df = plot_df.rename(
            columns={
                "operating_activity": "Operating Cash Flow",
                "investing_activity": "Investing Cash Flow",
                "financing_activity": "Financing Cash Flow",
            }
        )

        plot_df = plot_df.drop(columns=["_year_number"])

        plot_df = plot_df.melt(id_vars="year", var_name="Metric", value_name="Value")

        plot_df["Value"] = pd.to_numeric(plot_df["Value"], errors="coerce")

        plot_df = plot_df.dropna(subset=["Value"])

        if not plot_df.empty:

            fig = px.bar(
                plot_df,
                x="year",
                y="Value",
                color="Metric",
                barmode="group",
                title=("Operating, Investing & " "Financing Cash Flow"),
                labels={"year": "Financial Year", "Value": "₹ Crore"},
            )

            fig.update_layout(height=500, legend_title_text="")

            st.plotly_chart(fig, width="stretch")

        else:

            st.info("Cash flow values are not available.")

    else:

        st.info("Required cash flow columns " "are not available.")


else:

    st.info("No cash flow history available.")


# ============================================================
# HISTORICAL DATA COVERAGE
# ============================================================

st.divider()

st.subheader("📋 Historical Data Coverage")


coverage_rows = []


for name, dataframe in [
    ("Profit & Loss", pl),
    ("Balance Sheet", bs),
    ("Cash Flow", cf),
    ("Historical Ratios", ratios),
]:

    if (
        dataframe is not None
        and not dataframe.empty
        and "_year_number" in dataframe.columns
    ):

        years = sorted(dataframe["_year_number"].dropna().astype(int).unique().tolist())

        coverage_rows.append(
            {
                "Data Source": name,
                "Available Years": ", ".join(str(year) for year in years),
            }
        )

    else:

        coverage_rows.append({"Data Source": name, "Available Years": "No data"})


coverage_df = pd.DataFrame(coverage_rows, columns=["Data Source", "Available Years"])


st.dataframe(coverage_df, width="stretch", hide_index=True)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption("Nifty 100 Financial Intelligence Platform • " "Trend & Growth Analysis")
