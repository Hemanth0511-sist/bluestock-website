"""
Day 19 - Radar Charts

Generates peer-comparison radar charts for the N100
Financial Intelligence Platform.

Eight axes:
    1. ROE
    2. ROCE
    3. NPM
    4. D/E
    5. FCF Score
    6. PAT CAGR 5yr
    7. Revenue CAGR 5yr
    8. Composite Score

Peer companies:
    Company = filled polygon
    Peer average = dashed outline

Companies without a peer group:
    Company = filled polygon
    Nifty 100 average = dashed outline
"""

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ==========================================================
# CONFIGURATION
# ==========================================================

DB_PATH = Path("database/n100.db")

OUTPUT_DIR = Path("reports/radar_charts")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# RADAR METRICS
# ==========================================================

RADAR_METRICS = [
    "ROE",
    "ROCE",
    "NPM",
    "D/E",
    "FCF Score",
    "PAT CAGR 5yr",
    "Revenue CAGR 5yr",
    "Composite Score",
]


# ==========================================================
# DATABASE
# ==========================================================


def get_connection():

    return sqlite3.connect(DB_PATH)


# ==========================================================
# LOAD FINANCIAL RATIOS
# ==========================================================


def load_financial_ratios():

    query = """
    SELECT
        company_id,
        roe,
        roce,
        net_profit_margin,
        debt_to_equity,
        free_cash_flow,
        cfo_quality,
        interest_coverage
    FROM financial_ratios
    """

    with get_connection() as conn:

        df = pd.read_sql_query(query, conn)

    return df


# ==========================================================
# LOAD PEER GROUPS
# ==========================================================


def load_peer_groups():

    query = """
    SELECT
        company_id,
        peer_group_name
    FROM peer_percentiles
    GROUP BY
        company_id,
        peer_group_name
    """

    with get_connection() as conn:

        df = pd.read_sql_query(query, conn)

    return df


# ==========================================================
# LOAD PEER PERCENTILES
# ==========================================================


def load_peer_percentiles():

    query = """
    SELECT
        company_id,
        peer_group_name,
        metric,
        value,
        percentile_rank,
        year
    FROM peer_percentiles
    """

    with get_connection() as conn:

        df = pd.read_sql_query(query, conn)

    return df


# ==========================================================
# SAFE NUMERIC CONVERSION
# ==========================================================


def numeric(series):

    return pd.to_numeric(series, errors="coerce")


# ==========================================================
# P10 / P90 NORMALISATION
# ==========================================================


def winsorize_normalize(series, inverse=False):

    values = numeric(series)

    valid = values.dropna()

    if valid.empty:

        return pd.Series(50.0, index=series.index)

    p10 = valid.quantile(0.10)

    p90 = valid.quantile(0.90)

    if p90 == p10:

        score = pd.Series(50.0, index=series.index)

    else:

        clipped = values.clip(lower=p10, upper=p90)

        score = ((clipped - p10) / (p90 - p10)) * 100

    if inverse:

        score = 100 - score

    return score.fillna(50.0)


# ==========================================================
# GET PEER METRIC VALUES
# ==========================================================


def get_peer_metric_values(percentiles, peer_group, metric):

    result = percentiles[
        (percentiles["peer_group_name"] == peer_group)
        & (percentiles["metric"] == metric)
    ].copy()

    return result


# ==========================================================
# BUILD BASE DATA
# ==========================================================


def build_base_dataframe():

    ratios = load_financial_ratios()

    percentiles = load_peer_percentiles()

    if ratios.empty:

        raise RuntimeError("financial_ratios table is empty.")

    if percentiles.empty:

        raise RuntimeError("peer_percentiles table is empty.")

    ratios = ratios.copy()

    percentiles = percentiles.copy()

    ratios["company_id"] = ratios["company_id"].astype(str).str.strip().str.upper()

    percentiles["company_id"] = (
        percentiles["company_id"].astype(str).str.strip().str.upper()
    )

    return (ratios, percentiles)


# ==========================================================
# GET 5-YEAR CAGR VALUES
# ==========================================================


def get_cagr_values(percentiles, metric):

    data = percentiles[percentiles["metric"] == metric].copy()

    if data.empty:

        return pd.Series(dtype=float)

    data["value"] = numeric(data["value"])

    # One current value per company.
    #
    # Day 18 stores the current 2024 value
    # alongside its percentile ranking.
    data = (
        data.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )

    return data.set_index("company_id")["value"]


# ==========================================================
# CALCULATE FCF SCORE
# ==========================================================


def calculate_fcf_score(df):

    return winsorize_normalize(df["free_cash_flow"])


# ==========================================================
# CALCULATE COMPOSITE SCORE
# ==========================================================


def calculate_composite_scores(df):

    df = df.copy()

    # ------------------------------------------------------
    # Profitability - 35%
    # ------------------------------------------------------

    df["roe_score"] = winsorize_normalize(df["roe"])

    df["roce_score"] = winsorize_normalize(df["roce"])

    df["npm_score"] = winsorize_normalize(df["net_profit_margin"])

    profitability = (
        df["roe_score"] * 0.15 + df["roce_score"] * 0.10 + df["npm_score"] * 0.10
    )

    # ------------------------------------------------------
    # Cash Quality - 30%
    # ------------------------------------------------------

    df["fcf_score"] = calculate_fcf_score(df)

    df["cfo_pat_score"] = winsorize_normalize(df["cfo_quality"])

    df["fcf_positive_score"] = (numeric(df["free_cash_flow"]) > 0).astype(float) * 100

    cash_quality = (
        df["fcf_score"] * 0.15
        + df["cfo_pat_score"] * 0.10
        + df["fcf_positive_score"] * 0.05
    )

    # ------------------------------------------------------
    # Growth - 20%
    # ------------------------------------------------------

    df["revenue_cagr_score"] = winsorize_normalize(df["revenue_cagr_5yr"])

    df["pat_cagr_score"] = winsorize_normalize(df["pat_cagr_5yr"])

    growth = df["revenue_cagr_score"] * 0.10 + df["pat_cagr_score"] * 0.10

    # ------------------------------------------------------
    # Leverage - 15%
    # ------------------------------------------------------

    df["de_score"] = winsorize_normalize(df["debt_to_equity"], inverse=True)

    df["icr_score"] = winsorize_normalize(df["interest_coverage"])

    leverage = df["de_score"] * 0.10 + df["icr_score"] * 0.05

    # ------------------------------------------------------
    # Composite
    # ------------------------------------------------------

    df["composite_score"] = profitability + cash_quality + growth + leverage

    return df


# ==========================================================
# PREPARE RADAR DATA
# ==========================================================


def prepare_data():

    ratios, percentiles = build_base_dataframe()

    # ------------------------------------------------------
    # CAGR values from Day 18 data
    # ------------------------------------------------------

    pat_cagr = get_cagr_values(percentiles, "PAT CAGR 5yr")

    revenue_cagr = get_cagr_values(percentiles, "Revenue CAGR 5yr")

    # ------------------------------------------------------
    # Merge
    # ------------------------------------------------------

    df = ratios.copy()

    df["pat_cagr_5yr"] = df["company_id"].map(pat_cagr)

    df["revenue_cagr_5yr"] = df["company_id"].map(revenue_cagr)

    # ------------------------------------------------------
    # Composite
    # ------------------------------------------------------

    df = calculate_composite_scores(df)

    # ------------------------------------------------------
    # Peer groups
    # ------------------------------------------------------

    peer_groups = load_peer_groups()

    peer_groups["company_id"] = (
        peer_groups["company_id"].astype(str).str.strip().str.upper()
    )

    df = df.merge(peer_groups, on="company_id", how="left")

    return df


# ==========================================================
# NORMALISE RADAR AXES
# ==========================================================


def prepare_radar_scores(df):

    result = df.copy()

    result["ROE"] = winsorize_normalize(result["roe"])

    result["ROCE"] = winsorize_normalize(result["roce"])

    result["NPM"] = winsorize_normalize(result["net_profit_margin"])

    # Lower D/E is better.
    result["D/E"] = winsorize_normalize(result["debt_to_equity"], inverse=True)

    result["FCF Score"] = result["fcf_score"]

    result["PAT CAGR 5yr"] = winsorize_normalize(result["pat_cagr_5yr"])

    result["Revenue CAGR 5yr"] = winsorize_normalize(result["revenue_cagr_5yr"])

    result["Composite Score"] = result["composite_score"].clip(0, 100)

    return result


# ==========================================================
# PEER AVERAGE
# ==========================================================


def get_peer_average(df, company_id, peer_group):

    peer_df = df[df["peer_group_name"] == peer_group].copy()

    if peer_df.empty:

        return None

    averages = []

    for metric in RADAR_METRICS:

        averages.append(peer_df[metric].mean())

    return np.array(averages, dtype=float)


# ==========================================================
# NIFTY 100 AVERAGE
# ==========================================================


def get_nifty_average(df):

    averages = []

    for metric in RADAR_METRICS:

        averages.append(df[metric].mean())

    return np.array(averages, dtype=float)


# ==========================================================
# FILENAME
# ==========================================================


def make_filename(company_id):

    safe_name = (
        str(company_id).strip().replace("/", "_").replace("\\", "_").replace(" ", "_")
    )

    return OUTPUT_DIR / f"{safe_name}_radar.png"


# ==========================================================
# RADAR CHART
# ==========================================================


def generate_radar_chart(
    company_id, company_values, reference_values, reference_label, peer_group=None
):

    company_values = np.nan_to_num(company_values, nan=50.0)

    reference_values = np.nan_to_num(reference_values, nan=50.0)

    number_of_axes = len(RADAR_METRICS)

    angles = np.linspace(0, 2 * np.pi, number_of_axes, endpoint=False)

    angles = np.concatenate([angles, [angles[0]]])

    company_plot = np.concatenate([company_values, [company_values[0]]])

    reference_plot = np.concatenate([reference_values, [reference_values[0]]])

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw={"polar": True})

    # ------------------------------------------------------
    # Company polygon
    # ------------------------------------------------------

    ax.plot(angles, company_plot, linewidth=2.5, label=company_id)

    ax.fill(angles, company_plot, alpha=0.25)

    # ------------------------------------------------------
    # Reference outline
    # ------------------------------------------------------

    ax.plot(angles, reference_plot, linestyle="--", linewidth=2, label=reference_label)

    # ------------------------------------------------------
    # Axis labels
    # ------------------------------------------------------

    ax.set_xticks(angles[:-1])

    ax.set_xticklabels(RADAR_METRICS, fontsize=11)

    # ------------------------------------------------------
    # Scale
    # ------------------------------------------------------

    ax.set_ylim(0, 100)

    ax.set_yticks([0, 20, 40, 60, 80, 100])

    ax.set_yticklabels(["0", "20", "40", "60", "80", "100"], fontsize=9)

    # ------------------------------------------------------
    # Title
    # ------------------------------------------------------

    if peer_group:

        title = f"{company_id} - " f"{peer_group} Peer Radar"

    else:

        title = f"{company_id} - " f"Nifty 100 Radar"

    ax.set_title(title, fontsize=16, fontweight="bold", pad=25)

    # ------------------------------------------------------
    # Legend
    # ------------------------------------------------------

    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.10), fontsize=10)

    # ------------------------------------------------------
    # Grid
    # ------------------------------------------------------

    ax.grid(linewidth=0.8, alpha=0.6)

    # ------------------------------------------------------
    # Save
    # ------------------------------------------------------

    output_file = make_filename(company_id)

    fig.savefig(output_file, dpi=160, bbox_inches="tight")

    plt.close(fig)

    return output_file


# ==========================================================
# GENERATE ALL CHARTS
# ==========================================================


def generate_all_charts():

    print("\n==========================================")
    print("DAY 19 - RADAR CHART GENERATION")
    print("==========================================")

    df = prepare_data()

    df = prepare_radar_scores(df)

    print(f"\nCompanies available: {len(df)}")

    peer_count = df["peer_group_name"].notna().sum()

    standalone_count = df["peer_group_name"].isna().sum()

    print(f"Peer-group companies : {peer_count}")

    print(f"Standalone companies : {standalone_count}")

    # ------------------------------------------------------
    # Nifty 100 reference
    # ------------------------------------------------------

    nifty_average = get_nifty_average(df)

    generated = 0

    # ------------------------------------------------------
    # Generate company charts
    # ------------------------------------------------------

    for _, row in df.iterrows():

        company_id = row["company_id"]

        company_values = np.array(
            [
                row["ROE"],
                row["ROCE"],
                row["NPM"],
                row["D/E"],
                row["FCF Score"],
                row["PAT CAGR 5yr"],
                row["Revenue CAGR 5yr"],
                row["Composite Score"],
            ],
            dtype=float,
        )

        peer_group = row["peer_group_name"]

        # --------------------------------------------------
        # Peer company
        # --------------------------------------------------

        if pd.notna(peer_group) and str(peer_group).strip():

            reference_values = get_peer_average(df, company_id, peer_group)

            if reference_values is None:

                reference_values = nifty_average

                reference_label = "Nifty 100 Average"

            else:

                reference_label = f"{peer_group} Average"

        # --------------------------------------------------
        # No peer group
        # --------------------------------------------------

        else:

            reference_values = nifty_average

            reference_label = "Nifty 100 Average"

        output_file = generate_radar_chart(
            company_id,
            company_values,
            reference_values,
            reference_label,
            peer_group if pd.notna(peer_group) else None,
        )

        generated += 1

        print(f"{generated:>3}. " f"{company_id:<15} -> " f"{output_file}")

    # ------------------------------------------------------
    # Final summary
    # ------------------------------------------------------

    print("\n==========================================")

    print("DAY 19 COMPLETE")

    print("==========================================")

    print(f"Charts generated : {generated}")

    print(f"Output directory : {OUTPUT_DIR}")


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    generate_all_charts()
