"""
Day 36 - KMeans Clustering
N100 Financial Intelligence Platform

Features:
    - return_on_equity_pct
    - debt_to_equity
    - revenue_cagr_5yr
    - fcf_cagr_5yr
    - operating_profit_margin_pct

Missing values are imputed using the sector median for each feature.
Features are standardized with StandardScaler.
KMeans uses n_clusters=5 and random_state=42.

Outputs:
    reports/elbow_plot.png
    output/cluster_labels.csv
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "n100.db"
OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = ROOT / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CLUSTER_OUTPUT = OUTPUT_DIR / "cluster_labels.csv"
ELBOW_OUTPUT = REPORTS_DIR / "elbow_plot.png"

N_CLUSTERS = 5
RANDOM_STATE = 42


def clean_id(series: pd.Series) -> pd.Series:
    """Normalize company identifiers."""
    return (
        series.astype(str)
        .str.strip()
        .str.upper()
        .replace({"NAN": np.nan, "NONE": np.nan})
    )


def year_number(value) -> int:
    """Extract a four-digit year from a database year value."""
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group()) if match else -1


def safe_cagr(start, end, years: int = 5) -> float:
    """Return CAGR percentage when both endpoints are positive."""
    try:
        start = float(start)
        end = float(end)

        if not np.isfinite(start) or not np.isfinite(end):
            return np.nan

        # CAGR is not mathematically meaningful for a non-positive
        # starting value, so leave those cases missing for imputation.
        if start <= 0 or end <= 0 or years <= 0:
            return np.nan

        return ((end / start) ** (1.0 / years) - 1.0) * 100.0

    except (TypeError, ValueError, ZeroDivisionError):
        return np.nan


def load_data():
    """Load the tables required for clustering."""
    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        "SELECT id, company_name FROM companies",
        conn,
    )

    sectors = pd.read_sql_query(
        """
        SELECT company_id, broad_sector, sub_sector
        FROM sectors
        """,
        conn,
    )

    ratios = pd.read_sql_query(
        """
        SELECT company_id, year, roe, debt_to_equity,
               operating_profit_margin, free_cash_flow
        FROM historical_financial_ratios
        """,
        conn,
    )

    pl = pd.read_sql_query(
        """
        SELECT company_id, year, sales
        FROM profitandloss
        """,
        conn,
    )

    conn.close()

    companies["company_id"] = clean_id(companies["id"])
    sectors["company_id"] = clean_id(sectors["company_id"])
    ratios["company_id"] = clean_id(ratios["company_id"])
    pl["company_id"] = clean_id(pl["company_id"])

    return companies, sectors, ratios, pl


def prepare_latest_ratios(ratios: pd.DataFrame) -> pd.DataFrame:
    """Select the latest ratio observation for each company."""
    df = ratios.copy()
    df["_year_num"] = df["year"].apply(year_number)

    df = df.sort_values(["company_id", "_year_num"])
    df = df.drop_duplicates("company_id", keep="last")

    return df[
        [
            "company_id",
            "year",
            "roe",
            "debt_to_equity",
            "operating_profit_margin",
            "free_cash_flow",
        ]
    ].copy()


def prepare_cagrs(pl: pd.DataFrame, ratios: pd.DataFrame) -> pd.DataFrame:
    """Compute five-year revenue and FCF CAGR from the available history."""
    sales = pl.copy()
    sales["_year_num"] = sales["year"].apply(year_number)

    fcf = ratios[["company_id", "year", "free_cash_flow"]].copy()
    fcf["_year_num"] = fcf["year"].apply(year_number)

    records = []

    for company_id in sorted(
        set(sales["company_id"].dropna()) | set(fcf["company_id"].dropna())
    ):
        sales_company = sales[sales["company_id"] == company_id].sort_values(
            "_year_num"
        )

        fcf_company = fcf[fcf["company_id"] == company_id].sort_values("_year_num")

        revenue_cagr = np.nan
        fcf_cagr = np.nan

        if not sales_company.empty:
            valid_sales = sales_company[
                (sales_company["_year_num"] > 0) & sales_company["sales"].notna()
            ].copy()

            if len(valid_sales) >= 2:
                latest = valid_sales.iloc[-1]
                target_year = int(latest["_year_num"]) - 5

                prior = valid_sales[valid_sales["_year_num"] <= target_year]

                if not prior.empty:
                    prior_row = prior.iloc[-1]
                    actual_years = int(latest["_year_num"]) - int(
                        prior_row["_year_num"]
                    )

                    revenue_cagr = safe_cagr(
                        prior_row["sales"],
                        latest["sales"],
                        actual_years,
                    )

        if not fcf_company.empty:
            valid_fcf = fcf_company[
                (fcf_company["_year_num"] > 0) & fcf_company["free_cash_flow"].notna()
            ].copy()

            if len(valid_fcf) >= 2:
                latest = valid_fcf.iloc[-1]
                target_year = int(latest["_year_num"]) - 5

                prior = valid_fcf[valid_fcf["_year_num"] <= target_year]

                if not prior.empty:
                    prior_row = prior.iloc[-1]
                    actual_years = int(latest["_year_num"]) - int(
                        prior_row["_year_num"]
                    )

                    fcf_cagr = safe_cagr(
                        prior_row["free_cash_flow"],
                        latest["free_cash_flow"],
                        actual_years,
                    )

        records.append(
            {
                "company_id": company_id,
                "revenue_cagr_5yr": revenue_cagr,
                "fcf_cagr_5yr": fcf_cagr,
            }
        )

    return pd.DataFrame(records)


def build_feature_table(
    companies: pd.DataFrame,
    sectors: pd.DataFrame,
    ratios: pd.DataFrame,
    pl: pd.DataFrame,
) -> pd.DataFrame:
    """Build the five clustering features for all 92 companies."""
    latest = prepare_latest_ratios(ratios)
    cagrs = prepare_cagrs(pl, ratios)

    sector_map = (
        sectors[["company_id", "broad_sector"]]
        .dropna(subset=["company_id"])
        .drop_duplicates("company_id")
    )

    features = companies[["company_id", "company_name"]].drop_duplicates("company_id")

    features = features.merge(
        sector_map,
        on="company_id",
        how="left",
    )

    features = features.merge(
        latest,
        on="company_id",
        how="left",
    )

    features = features.merge(
        cagrs,
        on="company_id",
        how="left",
    )

    features["return_on_equity_pct"] = pd.to_numeric(features["roe"], errors="coerce")

    features["debt_to_equity"] = pd.to_numeric(
        features["debt_to_equity"], errors="coerce"
    )

    features["operating_profit_margin_pct"] = pd.to_numeric(
        features["operating_profit_margin"], errors="coerce"
    )

    # If the source ratios are stored as fractions (e.g. 0.20 for 20%),
    # convert them to percentages. If they are already percentage values,
    # leave them unchanged.
    for col in [
        "return_on_equity_pct",
        "operating_profit_margin_pct",
    ]:
        valid = features[col].dropna()

        if not valid.empty and valid.abs().median() <= 2:
            features[col] = features[col] * 100.0

    feature_cols = [
        "return_on_equity_pct",
        "debt_to_equity",
        "revenue_cagr_5yr",
        "fcf_cagr_5yr",
        "operating_profit_margin_pct",
    ]

    for col in feature_cols:
        features[col] = pd.to_numeric(
            features[col],
            errors="coerce",
        )

    return features


def impute_by_sector(
    df: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Impute missing feature values using the relevant sector median."""
    result = df.copy()

    global_medians = {}
    for col in feature_cols:
        median = result[col].median()

        if pd.isna(median):
            median = 0.0

        global_medians[col] = float(median)

    for col in feature_cols:
        sector_medians = result.groupby(
            "broad_sector",
            dropna=False,
        )[
            col
        ].transform("median")

        result[col] = result[col].fillna(sector_medians)
        result[col] = result[col].fillna(global_medians[col])

    return result, global_medians


def make_elbow_plot(X_scaled: np.ndarray) -> list[float]:
    """Create and save the KMeans elbow plot for k=2..10."""
    max_k = min(10, len(X_scaled) - 1)
    k_values = list(range(2, max_k + 1))

    inertias = []

    for k in k_values:
        model = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=20,
        )
        model.fit(X_scaled)
        inertias.append(float(model.inertia_))

    plt.figure(figsize=(8, 5))
    plt.plot(k_values, inertias, marker="o")
    plt.xticks(k_values)
    plt.xlabel("Number of clusters (k)")
    plt.ylabel("Inertia")
    plt.title("KMeans Elbow Plot")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(ELBOW_OUTPUT, dpi=160, bbox_inches="tight")
    plt.close()

    return inertias


def assign_cluster_names(
    feature_data: pd.DataFrame,
    labels: np.ndarray,
) -> dict[int, str]:
    """
    Assign deterministic descriptive names from cluster profiles.

    Names are provisional Day 36 archetypes. Day 37 requires team-lead
    review of actual company membership before final naming.
    """
    temp = feature_data.copy()
    temp["cluster_id"] = labels

    profile = temp.groupby("cluster_id")[
        [
            "return_on_equity_pct",
            "debt_to_equity",
            "revenue_cagr_5yr",
            "fcf_cagr_5yr",
            "operating_profit_margin_pct",
        ]
    ].mean()

    names = {}

    for cluster_id, row in profile.iterrows():
        roe = row["return_on_equity_pct"]
        de = row["debt_to_equity"]
        rev = row["revenue_cagr_5yr"]
        fcf = row["fcf_cagr_5yr"]
        opm = row["operating_profit_margin_pct"]

        # Priority rules create stable, interpretable archetypes.
        if de >= profile["debt_to_equity"].quantile(0.75):
            name = "Distressed or Turnaround"
        elif (
            roe >= profile["return_on_equity_pct"].quantile(0.75)
            and opm >= profile["operating_profit_margin_pct"].median()
        ):
            name = "High-Quality Compounders"
        elif rev >= profile["revenue_cagr_5yr"].quantile(0.75):
            name = "Emerging Growth"
        elif (
            fcf >= profile["fcf_cagr_5yr"].quantile(0.75)
            and de <= profile["debt_to_equity"].median()
        ):
            name = "Defensive Dividend Payers"
        else:
            name = "Value Cyclicals"

        names[int(cluster_id)] = name

    # Guarantee five unique labels even if two clusters satisfy the same rule.
    used = set()
    fallback = [
        "High-Quality Compounders",
        "Defensive Dividend Payers",
        "Value Cyclicals",
        "Distressed or Turnaround",
        "Emerging Growth",
    ]

    for cluster_id in sorted(names):
        proposed = names[cluster_id]

        if proposed not in used:
            used.add(proposed)
            continue

        for candidate in fallback:
            if candidate not in used:
                names[cluster_id] = candidate
                used.add(candidate)
                break

    return names


def main():
    """Run Day 36 clustering and generate required outputs."""
    print("=" * 70)
    print("DAY 36 - KMEANS CLUSTERING")
    print("=" * 70)

    print("\nLoading database data...")

    companies, sectors, ratios, pl = load_data()

    print(f"Companies loaded : {len(companies)}")
    print(f"Sector rows      : {len(sectors)}")
    print(f"Ratio rows       : {len(ratios)}")
    print(f"P&L rows         : {len(pl)}")

    features = build_feature_table(
        companies,
        sectors,
        ratios,
        pl,
    )

    expected = len(companies)

    print("\nBuilding clustering features...")

    feature_cols = [
        "return_on_equity_pct",
        "debt_to_equity",
        "revenue_cagr_5yr",
        "fcf_cagr_5yr",
        "operating_profit_margin_pct",
    ]

    print("\nMissing values BEFORE sector imputation:")
    print(features[feature_cols].isna().sum().to_string())

    features, global_medians = impute_by_sector(
        features,
        feature_cols,
    )

    print("\nMissing values AFTER sector imputation:")
    print(features[feature_cols].isna().sum().to_string())

    # Final safety check.
    if features[feature_cols].isna().any().any():
        raise RuntimeError(
            "Missing values remain after sector/global median imputation."
        )

    if len(features) != expected:
        raise RuntimeError(
            f"Expected {expected} companies but built {len(features)} feature rows."
        )

    X = features[feature_cols].to_numpy(dtype=float)

    print("\nApplying StandardScaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print("Generating elbow plot...")
    inertias = make_elbow_plot(X_scaled)

    print(f"Saved: {ELBOW_OUTPUT}")

    print("\nRunning KMeans...")
    model = KMeans(
        n_clusters=N_CLUSTERS,
        random_state=RANDOM_STATE,
        n_init=20,
    )

    labels = model.fit_predict(X_scaled)

    # Euclidean distance from each point to its assigned centroid.
    distances = np.linalg.norm(
        X_scaled - model.cluster_centers_[labels],
        axis=1,
    )

    cluster_names = assign_cluster_names(
        features,
        labels,
    )

    output = features[["company_id"]].copy()

    output["cluster_id"] = labels.astype(int)
    output["cluster_name"] = [cluster_names[int(x)] for x in labels]
    output["distance_from_centroid"] = distances

    output = output.sort_values("company_id").reset_index(drop=True)

    output["distance_from_centroid"] = output["distance_from_centroid"].round(6)

    output.to_csv(
        CLUSTER_OUTPUT,
        index=False,
    )

    print("\n" + "-" * 70)
    print("DAY 36 VALIDATION")
    print("-" * 70)

    print(f"Companies expected       : {expected}")
    print(f"Companies clustered      : {len(output)}")
    print(f"Unique cluster IDs       : {output['cluster_id'].nunique()}")
    print(
        "Cluster IDs              : "
        f"{sorted(output['cluster_id'].unique().tolist())}"
    )
    print("Companies without label  : " f"{output['cluster_id'].isna().sum()}")

    print("\nCluster distribution:")
    print(
        output.groupby(["cluster_id", "cluster_name"])
        .size()
        .reset_index(name="company_count")
        .sort_values("cluster_id")
        .to_string(index=False)
    )

    print("\nCluster names:")
    for cluster_id in sorted(cluster_names):
        print(f"  Cluster {cluster_id}: " f"{cluster_names[cluster_id]}")

    print("\nRequired output columns:")
    print(output.columns.tolist())

    print(f"\nElbow plot : {ELBOW_OUTPUT}")
    print(f"CSV output : {CLUSTER_OUTPUT}")

    if (
        len(output) == 92
        and output["cluster_id"].notna().all()
        and output["cluster_id"].nunique() == 5
        and set(output["cluster_id"]) == {0, 1, 2, 3, 4}
        and output["distance_from_centroid"].notna().all()
        and CLUSTER_OUTPUT.exists()
        and ELBOW_OUTPUT.exists()
    ):
        print("\n✓ All 92 companies assigned to one of 5 clusters.")
        print("✓ Required cluster output created.")
        print("✓ Elbow plot created.")
    else:
        raise RuntimeError("Day 36 validation failed. Check the results above.")

    print("\n" + "=" * 70)
    print("DAY 36 KMEANS CLUSTERING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
