"""
Day 37 - Cluster Profiling & Statistics

Generates:
1. output/cluster_profiles.csv
2. reports/correlation_heatmap.png
3. output/outlier_report.csv
4. output/portfolio_stats.csv

Database:
    database/n100.db
"""

import sqlite3
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "database" / "n100.db"
CLUSTER_FILE = BASE_DIR / "output" / "cluster_labels.csv"

OUTPUT_DIR = BASE_DIR / "output"
REPORT_DIR = BASE_DIR / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONFIGURATION
# ============================================================

FEATURE_COLUMNS = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]

KPI_COLUMNS = [
    "revenue_growth",
    "profit_growth",
    "net_profit_margin",
    "operating_profit_margin",
    "roe",
    "roce",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow",
]

CLUSTER_NAMES = {
    0: "Value Cyclicals",
    1: "Distressed or Turnaround",
    2: "High-Quality Compounders",
    3: "Defensive Dividend Payers",
    4: "Emerging Growth",
}


# ============================================================
# DATABASE
# ============================================================


def get_connection():
    """Return a SQLite database connection."""
    return sqlite3.connect(DB_PATH)


def load_data():
    """Load all required data from SQLite and cluster output."""

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    if not CLUSTER_FILE.exists():
        raise FileNotFoundError(
            f"Cluster labels not found: {CLUSTER_FILE}\n" "Run Day 36 clustering first."
        )

    conn = get_connection()

    try:
        companies = pd.read_sql_query(
            "SELECT * FROM companies",
            conn,
        )

        sectors = pd.read_sql_query(
            "SELECT * FROM sectors",
            conn,
        )

        ratios = pd.read_sql_query(
            "SELECT * FROM historical_financial_ratios",
            conn,
        )

        clusters = pd.read_csv(CLUSTER_FILE)

    finally:
        conn.close()

    print(f"Companies loaded : {len(companies)}")
    print(f"Sector rows      : {len(sectors)}")
    print(f"Ratio rows       : {len(ratios)}")
    print(f"Cluster rows     : {len(clusters)}")

    return companies, sectors, ratios, clusters


# ============================================================
# YEAR SORTING
# ============================================================


def year_sort_key(value):
    """Convert financial year text into a sortable numeric key."""

    if pd.isna(value):
        return -1

    text = str(value).strip()

    # Extract a four-digit year.
    import re

    match = re.search(r"(19|20)\d{2}", text)

    if match:
        return int(match.group())

    # Extract two-digit year if necessary.
    match = re.search(r"\d{2}", text)

    if match:
        year = int(match.group())

        if year < 50:
            return 2000 + year

        return 1900 + year

    return -1


# ============================================================
# LATEST YEAR RATIOS
# ============================================================


def get_latest_ratios(ratios):
    """Return the latest ratio record for each company."""

    df = ratios.copy()

    df["_year_sort"] = df["year"].apply(year_sort_key)

    df = (
        df.sort_values(
            ["company_id", "_year_sort"],
            ascending=[True, True],
        )
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    df.drop(columns=["_year_sort"], inplace=True, errors="ignore")

    return df


# ============================================================
# CLUSTER PROFILING
# ============================================================


def build_cluster_profiles(clusters, ratios):
    """Calculate mean and median of the five clustering features."""

    print("\nBuilding cluster profiles...")

    latest = get_latest_ratios(ratios)

    # Build the five feature values from latest historical ratios.
    feature_df = latest[
        [
            "company_id",
            "roe",
            "debt_to_equity",
            "free_cash_flow",
            "operating_profit_margin",
        ]
    ].copy()

    feature_df.rename(
        columns={
            "roe": "return_on_equity_pct",
            "debt_to_equity": "debt_to_equity",
            "operating_profit_margin": "operating_profit_margin_pct",
        },
        inplace=True,
    )

    # FCF CAGR is not directly stored as a latest-year ratio.
    # Try to calculate it from available historical FCF.
    fcf_cagr = calculate_fcf_cagr(ratios)

    feature_df = feature_df.merge(
        fcf_cagr,
        on="company_id",
        how="left",
    )

    # Revenue CAGR is approximated from revenue_growth where available.
    revenue_cagr = calculate_revenue_cagr(ratios)

    feature_df = feature_df.merge(
        revenue_cagr,
        on="company_id",
        how="left",
    )

    feature_df = feature_df[
        [
            "company_id",
            "return_on_equity_pct",
            "debt_to_equity",
            "revenue_cagr_5yr",
            "fcf_cagr_5yr",
            "operating_profit_margin_pct",
        ]
    ]

    merged = clusters.merge(
        feature_df,
        on="company_id",
        how="left",
    )

    rows = []

    for cluster_id in sorted(merged["cluster_id"].dropna().unique()):

        cluster_data = merged[merged["cluster_id"] == cluster_id].copy()

        cluster_name = CLUSTER_NAMES.get(
            int(cluster_id),
            f"Cluster {int(cluster_id)}",
        )

        row = {
            "cluster_id": int(cluster_id),
            "cluster_name": cluster_name,
            "company_count": len(cluster_data),
        }

        for metric in FEATURE_COLUMNS:

            values = pd.to_numeric(
                cluster_data[metric],
                errors="coerce",
            ).dropna()

            if len(values) == 0:
                row[f"{metric}_mean"] = np.nan
                row[f"{metric}_median"] = np.nan
            else:
                row[f"{metric}_mean"] = values.mean()
                row[f"{metric}_median"] = values.median()

        rows.append(row)

    result = pd.DataFrame(rows)

    output_path = OUTPUT_DIR / "cluster_profiles.csv"
    result.to_csv(output_path, index=False)

    print(f"Cluster profiles saved: {output_path}")

    return result


# ============================================================
# CAGR HELPERS
# ============================================================


def calculate_fcf_cagr(ratios):
    """Calculate five-year FCF CAGR where valid."""

    rows = []

    for company_id, group in ratios.groupby("company_id"):

        group = group.copy()
        group["_year_sort"] = group["year"].apply(year_sort_key)

        group = group.sort_values("_year_sort")

        values = pd.to_numeric(
            group["free_cash_flow"],
            errors="coerce",
        )

        valid = group.loc[values.notna()].copy()

        if len(valid) < 6:
            rows.append(
                {
                    "company_id": company_id,
                    "fcf_cagr_5yr": np.nan,
                }
            )
            continue

        start = float(valid.iloc[-6]["free_cash_flow"])
        end = float(valid.iloc[-1]["free_cash_flow"])

        if start > 0 and end > 0:
            cagr = (((end / start) ** (1 / 5)) - 1) * 100
        else:
            cagr = np.nan

        rows.append(
            {
                "company_id": company_id,
                "fcf_cagr_5yr": cagr,
            }
        )

    return pd.DataFrame(rows)


def calculate_revenue_cagr(ratios):
    """Estimate five-year revenue CAGR from revenue growth history."""

    rows = []

    for company_id, group in ratios.groupby("company_id"):

        group = group.copy()
        group["_year_sort"] = group["year"].apply(year_sort_key)

        group = group.sort_values("_year_sort")

        values = pd.to_numeric(
            group["revenue_growth"],
            errors="coerce",
        ).dropna()

        if len(values) >= 5:

            # Compound the latest five annual growth rates.
            latest = values.iloc[-5:]

            growth_factor = np.prod(1 + latest / 100)

            cagr = (growth_factor ** (1 / 5) - 1) * 100

        else:
            cagr = np.nan

        rows.append(
            {
                "company_id": company_id,
                "revenue_cagr_5yr": cagr,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# CORRELATION MATRIX
# ============================================================


def build_correlation_heatmap(ratios):
    """Generate Pearson correlation heatmap for ten latest-year KPIs."""

    print("\nBuilding correlation matrix...")

    latest = get_latest_ratios(ratios)

    available = [column for column in KPI_COLUMNS if column in latest.columns]

    correlation_df = latest[available].apply(
        pd.to_numeric,
        errors="coerce",
    )

    correlation = correlation_df.corr(method="pearson")

    plt.figure(figsize=(14, 11))

    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        cbar=True,
    )

    plt.title(
        "Pearson Correlation Matrix - Latest Year KPIs",
        fontsize=15,
    )

    plt.xticks(
        rotation=45,
        ha="right",
    )

    plt.yticks(
        rotation=0,
    )

    plt.tight_layout()

    output_path = REPORT_DIR / "correlation_heatmap.png"

    plt.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(f"Correlation heatmap saved: {output_path}")

    return correlation


# ============================================================
# OUTLIER DETECTION
# ============================================================


def calculate_zscore(series):
    """Return population-standard-deviation Z-scores."""

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    mean = numeric.mean()
    std = numeric.std(ddof=0)

    if pd.isna(std) or std == 0:
        return pd.Series(
            np.nan,
            index=series.index,
        )

    return (numeric - mean) / std


def build_outlier_report(ratios, sectors):
    """Detect sector-level KPI outliers with absolute Z-score above 3."""

    print("\nRunning sector-based outlier detection...")

    latest = get_latest_ratios(ratios)

    sector_map = sectors[["company_id", "broad_sector"]].drop_duplicates(
        subset=["company_id"]
    )

    merged = latest.merge(
        sector_map,
        on="company_id",
        how="left",
    )

    outlier_rows = []

    for sector_name, sector_df in merged.groupby(
        "broad_sector",
        dropna=False,
    ):

        sector_df = sector_df.copy()

        z_scores = pd.DataFrame(index=sector_df.index)

        for metric in KPI_COLUMNS:

            if metric not in sector_df.columns:
                continue

            z_scores[metric] = calculate_zscore(sector_df[metric])

        for index, row in sector_df.iterrows():

            for metric in z_scores.columns:

                z_value = z_scores.loc[
                    index,
                    metric,
                ]

                if pd.isna(z_value):
                    continue

                if abs(z_value) > 3:

                    outlier_rows.append(
                        {
                            "company_id": row["company_id"],
                            "broad_sector": sector_name,
                            "metric": metric,
                            "value": row[metric],
                            "z_score": z_value,
                            "severity": "High",
                        }
                    )

    result = pd.DataFrame(
        outlier_rows,
        columns=[
            "company_id",
            "broad_sector",
            "metric",
            "value",
            "z_score",
            "severity",
        ],
    )

    output_path = OUTPUT_DIR / "outlier_report.csv"

    result.to_csv(
        output_path,
        index=False,
    )

    print(f"Outlier rows detected: {len(result)}")

    print(f"Outlier report saved: {output_path}")

    return result


# ============================================================
# PORTFOLIO STATISTICS
# ============================================================


def build_portfolio_stats(ratios):
    """Calculate percentile and dispersion statistics for ten KPIs."""

    print("\nBuilding portfolio statistics...")

    latest = get_latest_ratios(ratios)

    rows = []

    for metric in KPI_COLUMNS:

        if metric not in latest.columns:
            continue

        values = pd.to_numeric(
            latest[metric],
            errors="coerce",
        ).dropna()

        if len(values) == 0:
            continue

        rows.append(
            {
                "kpi": metric,
                "P10": values.quantile(0.10),
                "P25": values.quantile(0.25),
                "P50": values.quantile(0.50),
                "P75": values.quantile(0.75),
                "P90": values.quantile(0.90),
                "Mean": values.mean(),
                "Std": values.std(ddof=1),
                "company_count": len(values),
            }
        )

    result = pd.DataFrame(rows)

    output_path = OUTPUT_DIR / "portfolio_stats.csv"

    result.to_csv(
        output_path,
        index=False,
    )

    print(f"Portfolio statistics saved: {output_path}")

    return result


# ============================================================
# VALIDATION
# ============================================================


def validate(
    companies,
    clusters,
    cluster_profiles,
    correlation,
    outliers,
    portfolio_stats,
):
    """Validate all Day 37 outputs."""

    print("\n" + "-" * 70)
    print("DAY 37 VALIDATION")
    print("-" * 70)

    expected_companies = len(companies["id"].dropna().unique())

    clustered_companies = clusters["company_id"].dropna().nunique()

    unique_clusters = clusters["cluster_id"].dropna().nunique()

    print(f"Companies expected       : {expected_companies}")

    print(f"Companies profiled       : {clustered_companies}")

    print(f"Unique clusters          : {unique_clusters}")

    print(f"Cluster profile rows     : {len(cluster_profiles)}")

    print(f"Correlation KPI count    : {len(correlation.columns)}")

    print(f"Outlier rows             : {len(outliers)}")

    print(f"Portfolio KPI rows       : {len(portfolio_stats)}")

    coverage_pass = expected_companies == 92 and clustered_companies == 92

    cluster_pass = unique_clusters == 5

    profile_pass = len(cluster_profiles) == 5

    correlation_pass = len(correlation.columns) >= 10 and correlation.shape[0] >= 10

    portfolio_pass = len(portfolio_stats) >= 10

    print()

    print(f"Company coverage : " f"{'PASS' if coverage_pass else 'FAIL'}")

    print(f"5 clusters       : " f"{'PASS' if cluster_pass else 'FAIL'}")

    print(f"Cluster profiles : " f"{'PASS' if profile_pass else 'FAIL'}")

    print(f"Correlation      : " f"{'PASS' if correlation_pass else 'FAIL'}")

    print(f"Portfolio stats  : " f"{'PASS' if portfolio_pass else 'FAIL'}")

    all_pass = all(
        [
            coverage_pass,
            cluster_pass,
            profile_pass,
            correlation_pass,
            portfolio_pass,
        ]
    )

    if all_pass:
        print()
        print("✓ All Day 37 validation checks passed.")
    else:
        print()
        print("⚠ Some Day 37 validation checks require review.")

    return all_pass


# ============================================================
# MAIN
# ============================================================


def main():
    """Run the complete Day 37 cluster profiling pipeline."""

    print("=" * 70)
    print("DAY 37 - CLUSTER PROFILING & STATISTICS")
    print("=" * 70)

    print("\nLoading database data...")

    companies, sectors, ratios, clusters = load_data()

    cluster_profiles = build_cluster_profiles(
        clusters,
        ratios,
    )

    correlation = build_correlation_heatmap(ratios)

    outliers = build_outlier_report(
        ratios,
        sectors,
    )

    portfolio_stats = build_portfolio_stats(ratios)

    validate(
        companies,
        clusters,
        cluster_profiles,
        correlation,
        outliers,
        portfolio_stats,
    )

    print("\n" + "=" * 70)
    print("DAY 37 OUTPUT FILES")
    print("=" * 70)

    print(f"Cluster profiles : " f"{OUTPUT_DIR / 'cluster_profiles.csv'}")

    print(f"Correlation map  : " f"{REPORT_DIR / 'correlation_heatmap.png'}")

    print(f"Outlier report   : " f"{OUTPUT_DIR / 'outlier_report.csv'}")

    print(f"Portfolio stats  : " f"{OUTPUT_DIR / 'portfolio_stats.csv'}")

    print("\n" + "=" * 70)
    print("DAY 37 COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
