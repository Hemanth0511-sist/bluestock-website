# ============================================================
# DAY 24 - PEER COMPARISON
# File:
# src/dashboard/pages/04_peers.py
# ============================================================

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# PATHS
# ============================================================

# Current file:
# src/dashboard/pages/04_peers.py

CURRENT_FILE = Path(__file__).resolve()

# src/dashboard/pages
PAGES_DIR = CURRENT_FILE.parent

# src/dashboard
DASHBOARD_DIR = PAGES_DIR.parent

# src
SRC_DIR = DASHBOARD_DIR.parent

# Project root
PROJECT_ROOT = SRC_DIR.parent

# Database
DATABASE_PATH = PROJECT_ROOT / "database" / "n100.db"


# Add src/dashboard to Python path
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))


# ============================================================
# DATABASE IMPORT
# ============================================================

from src.dashboard.utils.db import (
    get_peers,
    get_ratios,
)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Peer Comparison | Nifty 100 Analytics",
    page_icon="👥",
    layout="wide",
)


# ============================================================
# TITLE
# ============================================================

st.title("👥 Peer Comparison")

st.caption("Compare a company against companies in the same peer group.")

st.divider()


# ============================================================
# LOAD PEER GROUPS
# ============================================================


@st.cache_data(ttl=600)
def load_peer_groups():

    connection = sqlite3.connect(DATABASE_PATH)

    try:

        query = """
            SELECT DISTINCT
                peer_group_name
            FROM peer_groups
            WHERE peer_group_name IS NOT NULL
              AND TRIM(peer_group_name) <> ''
            ORDER BY peer_group_name
        """

        df = pd.read_sql_query(query, connection)

    finally:

        connection.close()

    return df


# ============================================================
# LOAD GROUPS
# ============================================================

peer_groups_df = load_peer_groups()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.subheader("👥 Peer Group")

    if peer_groups_df.empty:

        st.error("No peer groups were found in the database.")

    else:

        peer_group_options = (
            peer_groups_df["peer_group_name"].dropna().astype(str).tolist()
        )

        selected_group = st.selectbox("Select Peer Group", peer_group_options, index=0)


# ============================================================
# STOP IF NO GROUPS
# ============================================================

if peer_groups_df.empty:

    st.error("No peer groups were found in the peer_groups table.")

    st.info(
        "Please verify that peer_groups contains "
        "company_id and peer_group_name values."
    )

    st.stop()


# ============================================================
# LOAD PEERS
# ============================================================

peers_df = get_peers(selected_group)


# ============================================================
# EMPTY GROUP
# ============================================================

if peers_df is None or peers_df.empty:

    st.warning(f"No companies were found for peer group " f"'{selected_group}'.")

    st.stop()


# ============================================================
# NORMALIZE COLUMN NAMES
# ============================================================

peers_df.columns = [str(column).strip().lower() for column in peers_df.columns]


# ============================================================
# CHECK COMPANY ID
# ============================================================

if "company_id" not in peers_df.columns:

    st.error("Peer data is missing company_id.")

    st.write("Available columns:", peers_df.columns.tolist())

    st.stop()


# ============================================================
# COMPANY NAME FALLBACK
# ============================================================

if "name" not in peers_df.columns:

    peers_df["name"] = peers_df["company_id"]


# ============================================================
# BENCHMARK COLUMN
# ============================================================

if "is_benchmark" not in peers_df.columns:

    peers_df["is_benchmark"] = 0


# ============================================================
# FIND BENCHMARK
# ============================================================

benchmark_rows = peers_df[peers_df["is_benchmark"] == 1]


if not benchmark_rows.empty:

    benchmark_ticker = benchmark_rows.iloc[0]["company_id"]

else:

    benchmark_ticker = peers_df.iloc[0]["company_id"]


# ============================================================
# COMPANY SELECTOR
# ============================================================

company_options_df = peers_df[["company_id", "name"]].copy()


company_options_df["name"] = company_options_df["name"].fillna("").astype(str)


company_options_df["label"] = (
    company_options_df["company_id"].astype(str) + " — " + company_options_df["name"]
)


labels = company_options_df["label"].tolist()


default_index = 0

for i, ticker in enumerate(company_options_df["company_id"]):

    if ticker == benchmark_ticker:

        default_index = i
        break


selected_label = st.selectbox("Select Company", labels, index=default_index)


selected_company_row = company_options_df[company_options_df["label"] == selected_label]


selected_company = selected_company_row.iloc[0]["company_id"]


selected_company_name = selected_company_row.iloc[0]["name"]


# ============================================================
# COMPANY INFORMATION
# ============================================================

st.subheader(f"📊 {selected_company_name}")

st.caption(f"Ticker: {selected_company}  |  " f"Peer Group: {selected_group}")

st.divider()


# ============================================================
# FINANCIAL METRICS
# ============================================================

METRICS = {
    "ROE": ["roe", "return_on_equity"],
    "ROCE": ["roce", "return_on_capital_employed"],
    "Net Profit Margin": ["net_profit_margin", "npm"],
    "Operating Margin": ["operating_profit_margin", "opm"],
    "Debt / Equity": ["debt_to_equity", "de"],
    "Interest Coverage": ["interest_coverage", "icr"],
    "Asset Turnover": ["asset_turnover"],
    "Revenue Growth": ["revenue_growth"],
}


# ============================================================
# GET LATEST RATIOS
# ============================================================


def get_latest_ratios(ticker):

    try:

        df = get_ratios(ticker)

    except Exception:

        return pd.DataFrame()

    if df is None:

        return pd.DataFrame()

    if df.empty:

        return pd.DataFrame()

    df = df.copy()

    df.columns = [str(column).strip().lower() for column in df.columns]

    # If year exists, sort by year

    if "year" in df.columns:

        try:

            df = df.sort_values("year")

        except Exception:

            pass

    return df.iloc[-1:]


# ============================================================
# SELECTED COMPANY RATIOS
# ============================================================

selected_ratios = get_latest_ratios(selected_company)


# ============================================================
# BUILD SELECTED COMPANY METRICS
# ============================================================

selected_metrics = {}


if not selected_ratios.empty:

    latest = selected_ratios.iloc[0]

    for metric_name, candidates in METRICS.items():

        value = None

        for candidate in candidates:

            if candidate in selected_ratios.columns:

                value = latest[candidate]

                break

        try:

            value = float(value)

        except Exception:

            value = 0.0

        selected_metrics[metric_name] = value

else:

    for metric_name in METRICS:

        selected_metrics[metric_name] = 0.0


# ============================================================
# LOAD ALL PEER METRICS
# ============================================================

peer_metric_rows = []


for _, peer in peers_df.iterrows():

    ticker = str(peer["company_id"])

    ratios = get_latest_ratios(ticker)

    if ratios.empty:

        continue

    latest = ratios.iloc[0]

    row = {
        "company_id": ticker,
        "name": str(peer.get("name", ticker)),
        "is_benchmark": int(peer.get("is_benchmark", 0)),
    }

    for metric_name, candidates in METRICS.items():

        value = None

        for candidate in candidates:

            if candidate in ratios.columns:

                value = latest[candidate]

                break

        try:

            value = float(value)

        except Exception:

            value = None

        row[metric_name] = value

    peer_metric_rows.append(row)


peer_metrics_df = pd.DataFrame(peer_metric_rows)


# ============================================================
# RADAR CHART
# ============================================================

st.subheader("📡 Company vs Peer Group Average")


RADAR_METRICS = [
    "ROE",
    "ROCE",
    "Net Profit Margin",
    "Operating Margin",
    "Debt / Equity",
    "Interest Coverage",
    "Asset Turnover",
    "Revenue Growth",
]


if peer_metrics_df.empty:

    st.warning("Financial ratio data is not available " "for this peer group.")

else:

    available_metrics = []

    for metric in RADAR_METRICS:

        if metric not in peer_metrics_df.columns:

            continue

        values = pd.to_numeric(peer_metrics_df[metric], errors="coerce")

        if values.notna().any():

            available_metrics.append(metric)

    if not available_metrics:

        st.warning("No financial metrics are available " "for this peer group.")

    else:

        company_values = []

        peer_average_values = []

        for metric in available_metrics:

            company_value = selected_metrics.get(metric, 0.0)

            peer_values = pd.to_numeric(peer_metrics_df[metric], errors="coerce")

            peer_average = peer_values.dropna().mean()

            company_values.append(company_value)

            peer_average_values.append(peer_average)

        # Close polygons

        theta = available_metrics + [available_metrics[0]]

        company_r = company_values + [company_values[0]]

        average_r = peer_average_values + [peer_average_values[0]]

        fig = go.Figure()

        # Selected company

        fig.add_trace(
            go.Scatterpolar(
                r=company_r,
                theta=theta,
                fill="toself",
                name=str(selected_company),
            )
        )

        # Peer average

        fig.add_trace(
            go.Scatterpolar(
                r=average_r,
                theta=theta,
                fill="toself",
                name="Peer Average",
            )
        )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            showlegend=True,
            height=600,
            margin=dict(
                l=60,
                r=60,
                t=50,
                b=50,
            ),
        )

        st.plotly_chart(fig, use_container_width=True)


# ============================================================
# PEER TABLE
# ============================================================

st.divider()

st.subheader("📋 Peer Company Comparison")


if peer_metrics_df.empty:

    st.info("No financial data is available " "for the companies in this group.")

else:

    display_columns = [
        "company_id",
        "name",
        "ROE",
        "ROCE",
        "Net Profit Margin",
        "Operating Margin",
        "Debt / Equity",
        "Interest Coverage",
        "Asset Turnover",
        "Revenue Growth",
    ]

    available_columns = [
        column for column in display_columns if column in peer_metrics_df.columns
    ]

    display_df = peer_metrics_df[available_columns].copy()

    numeric_columns = [
        column for column in available_columns if column not in ["company_id", "name"]
    ]

    for column in numeric_columns:

        display_df[column] = pd.to_numeric(display_df[column], errors="coerce").round(2)

    # ========================================================
    # HIGHLIGHT BENCHMARK
    # ========================================================

    def highlight_benchmark(row):

        if row["company_id"] == benchmark_ticker:

            return ["font-weight: bold" for _ in row]

        return ["" for _ in row]

    styled_df = display_df.style.apply(highlight_benchmark, axis=1)

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# SUMMARY
# ============================================================

st.divider()

st.subheader("📌 Peer Group Summary")


col1, col2, col3 = st.columns(3)


with col1:

    st.metric("Peer Group", selected_group)


with col2:

    st.metric("Companies", len(peers_df))


with col3:

    st.metric("Benchmark", benchmark_ticker)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption("Nifty 100 Financial Intelligence Platform • " "Peer Comparison")
