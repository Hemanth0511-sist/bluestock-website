import os
import sqlite3

import pandas as pd


class PeerPercentileAnalyzer:

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(self):

        # Project root:
        # N100-Financial-Intelligence-Platform
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        # SQLite database
        self.database_path = os.path.join(self.project_root, "database", "n100.db")

        # Peer group Excel file
        self.peer_groups_path = self._find_peer_groups_file()

        # ------------------------------------------------------
        # 10 required peer ranking metrics
        # ------------------------------------------------------

        self.metrics = {
            "roe": "ROE",
            "roce": "ROCE",
            "net_profit_margin": "Net Profit Margin",
            "debt_to_equity": "D/E",
            "free_cash_flow": "FCF",
            "pat_cagr_5yr": "PAT CAGR 5yr",
            "revenue_cagr_5yr": "Revenue CAGR 5yr",
            "eps_cagr_5yr": "EPS CAGR 5yr",
            "interest_coverage": "Interest Coverage",
            "asset_turnover": "Asset Turnover",
        }

    # ==========================================================
    # FIND PEER GROUP FILE
    # ==========================================================

    def _find_peer_groups_file(self):

        processed_path = os.path.join(
            self.project_root, "data", "processed", "peer_groups.xlsx"
        )

        raw_path = os.path.join(self.project_root, "data", "raw", "peer_groups.xlsx")

        # Prefer processed file
        if os.path.exists(processed_path):

            return processed_path

        # Fallback to raw file
        if os.path.exists(raw_path):

            return raw_path

        raise FileNotFoundError(
            "peer_groups.xlsx was not found in " "data/processed or data/raw."
        )

    # ==========================================================
    # LOAD PEER GROUP DATA
    # ==========================================================

    def load_peer_groups(self):

        df = pd.read_excel(self.peer_groups_path)

        required_columns = ["peer_group_name", "company_id"]

        missing_columns = [
            column for column in required_columns if column not in df.columns
        ]

        if missing_columns:

            raise ValueError(
                "Missing required peer group columns: " f"{missing_columns}"
            )

        df = df[required_columns].copy()

        # Clean company IDs
        df["company_id"] = df["company_id"].astype(str).str.strip()

        # Clean peer group names
        df["peer_group_name"] = df["peer_group_name"].astype(str).str.strip()

        # Remove invalid rows
        df = df[(df["company_id"] != "") & (df["peer_group_name"] != "")]

        # Remove duplicate company/peer assignments
        df = df.drop_duplicates(subset=["company_id", "peer_group_name"])

        return df.reset_index(drop=True)

    # ==========================================================
    # LOAD FINANCIAL DATA
    # ==========================================================

    def load_financial_data(self):

        from src.screener.engine import ScreenerEngine

        engine = ScreenerEngine()

        try:

            df = engine.load_financial_data()

        finally:

            engine.close()

        return df

    # ==========================================================
    # CREATE PEER PERCENTILES TABLE
    # ==========================================================

    def create_table(self):

        connection = sqlite3.connect(self.database_path)

        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peer_percentiles (

                company_id TEXT NOT NULL,

                peer_group_name TEXT NOT NULL,

                metric TEXT NOT NULL,

                value REAL,

                percentile_rank REAL,

                year TEXT

            )
            """)

        connection.commit()

        connection.close()

    # ==========================================================
    # CLEAR PREVIOUS RESULTS
    # ==========================================================

    def clear_table(self):

        connection = sqlite3.connect(self.database_path)

        cursor = connection.cursor()

        cursor.execute("""
            DELETE FROM peer_percentiles
            """)

        connection.commit()

        connection.close()

    # ==========================================================
    # PERCENT RANK
    # ==========================================================

    def calculate_percent_rank(self, series, inverse=False):

        numeric = pd.to_numeric(series, errors="coerce")

        result = pd.Series(float("nan"), index=series.index, dtype=float)

        valid = numeric.notna()

        if valid.sum() == 0:

            return result

        values = numeric[valid]

        # ------------------------------------------------------
        # PERCENT_RANK
        #
        # (RANK - 1) / (N - 1)
        #
        # Equivalent to SQL PERCENT_RANK behaviour.
        # ------------------------------------------------------

        if len(values) == 1:

            percentile = pd.Series(0.0, index=values.index, dtype=float)

        else:

            ranks = values.rank(method="min", ascending=True)

            percentile = (ranks - 1) / (len(values) - 1)

        # ------------------------------------------------------
        # D/E
        #
        # Lower D/E is better.
        #
        # Therefore:
        #
        # percentile = 1 - percentile
        # ------------------------------------------------------

        if inverse:

            percentile = 1.0 - percentile

        result.loc[percentile.index] = percentile

        return result

    # ==========================================================
    # CALCULATE PEER PERCENTILES
    # ==========================================================

    def calculate(self):

        # ------------------------------------------------------
        # Load peer groups
        # ------------------------------------------------------

        peer_groups = self.load_peer_groups()

        # ------------------------------------------------------
        # Load financial data
        # ------------------------------------------------------

        financial = self.load_financial_data()

        if financial.empty:

            return pd.DataFrame(
                columns=[
                    "company_id",
                    "peer_group_name",
                    "metric",
                    "value",
                    "percentile_rank",
                    "year",
                ]
            )

        # Clean company IDs
        financial["company_id"] = financial["company_id"].astype(str).str.strip()

        # ------------------------------------------------------
        # Identify companies without peer groups
        # ------------------------------------------------------

        assigned_companies = set(peer_groups["company_id"])

        all_companies = set(financial["company_id"])

        unassigned_companies = sorted(all_companies - assigned_companies)

        if unassigned_companies:

            print()
            print("No peer group assigned - " f"{len(unassigned_companies)} companies")

            print("Companies:", ", ".join(unassigned_companies))

        # ------------------------------------------------------
        # Merge financial data with peer groups
        #
        # Only companies having a peer group are included.
        # ------------------------------------------------------

        merged = peer_groups.merge(financial, on="company_id", how="left")

        # ------------------------------------------------------
        # Validate required columns
        # ------------------------------------------------------

        missing_metrics = [
            column for column in self.metrics if column not in merged.columns
        ]

        if missing_metrics:

            raise ValueError("Missing financial metric columns: " f"{missing_metrics}")

        # ------------------------------------------------------
        # Calculate percentile rankings
        # ------------------------------------------------------

        records = []

        for peer_group_name, group in merged.groupby("peer_group_name", dropna=False):

            group = group.copy()

            # --------------------------------------------------
            # Each metric
            # --------------------------------------------------

            for column, metric_name in self.metrics.items():

                # --------------------------------------------------
                # D/E is inverse
                # --------------------------------------------------

                inverse = column == "debt_to_equity"

                percentile = self.calculate_percent_rank(group[column], inverse=inverse)

                # --------------------------------------------------
                # Store company-level result
                # --------------------------------------------------

                for index in group.index:

                    company_id = group.loc[index, "company_id"]

                    value = pd.to_numeric(
                        pd.Series([group.loc[index, column]]), errors="coerce"
                    ).iloc[0]

                    rank = percentile.loc[index]

                    # Skip missing metric values
                    if pd.isna(value):

                        continue

                    # --------------------------------------------------
                    # Determine year
                    # --------------------------------------------------

                    if "year" in group.columns:

                        year_value = group.loc[index, "year"]

                    else:

                        year_value = None

                    if pd.isna(year_value):

                        year_value = None

                    else:

                        year_value = str(year_value)

                    # --------------------------------------------------
                    # Add record
                    # --------------------------------------------------

                    records.append(
                        {
                            "company_id": str(company_id),
                            "peer_group_name": str(peer_group_name),
                            "metric": metric_name,
                            "value": float(value),
                            "percentile_rank": (
                                float(rank) if pd.notna(rank) else None
                            ),
                            "year": year_value,
                        }
                    )

        # ------------------------------------------------------
        # Final DataFrame
        # ------------------------------------------------------

        results = pd.DataFrame(
            records,
            columns=[
                "company_id",
                "peer_group_name",
                "metric",
                "value",
                "percentile_rank",
                "year",
            ],
        )

        return results

    # ==========================================================
    # SAVE RESULTS TO SQLITE
    # ==========================================================

    def save_results(self, results):

        # Make sure table exists
        self.create_table()

        # Remove previous Day 18 results
        self.clear_table()

        if results.empty:

            print()
            print("No peer percentile results " "were generated.")

            return

        connection = sqlite3.connect(self.database_path)

        try:

            results.to_sql(
                "peer_percentiles", connection, if_exists="append", index=False
            )

            connection.commit()

        finally:

            connection.close()

    # ==========================================================
    # VERIFY RESULTS
    # ==========================================================

    def verify_results(self):

        connection = sqlite3.connect(self.database_path)

        try:

            count = pd.read_sql_query(
                """
                SELECT COUNT(*) AS total_rows
                FROM peer_percentiles
                """,
                connection,
            )

            groups = pd.read_sql_query(
                """
                SELECT
                    peer_group_name,
                    COUNT(*) AS rows
                FROM peer_percentiles
                GROUP BY peer_group_name
                ORDER BY peer_group_name
                """,
                connection,
            )

            metrics = pd.read_sql_query(
                """
                SELECT
                    metric,
                    COUNT(*) AS rows
                FROM peer_percentiles
                GROUP BY metric
                ORDER BY metric
                """,
                connection,
            )

            sample = pd.read_sql_query(
                """
                SELECT
                    company_id,
                    peer_group_name,
                    metric,
                    value,
                    percentile_rank,
                    year
                FROM peer_percentiles
                ORDER BY
                    peer_group_name,
                    metric,
                    percentile_rank DESC
                LIMIT 20
                """,
                connection,
            )

        finally:

            connection.close()

        return (count, groups, metrics, sample)

    # ==========================================================
    # RUN DAY 18
    # ==========================================================

    def run(self):

        print()
        print("=" * 70)
        print("DAY 18 - PEER PERCENTILE RANKINGS")
        print("=" * 70)

        # ------------------------------------------------------
        # File information
        # ------------------------------------------------------

        print(f"PEER GROUP FILE : " f"{self.peer_groups_path}")

        print(f"DATABASE        : " f"{self.database_path}")

        print("=" * 70)

        # ------------------------------------------------------
        # Load peer groups
        # ------------------------------------------------------

        peer_groups = self.load_peer_groups()

        print(f"PEER GROUP ROWS : " f"{len(peer_groups)}")

        print(f"UNIQUE COMPANIES: " f"{peer_groups['company_id'].nunique()}")

        print(f"PEER GROUPS     : " f"{peer_groups['peer_group_name'].nunique()}")

        # ------------------------------------------------------
        # Display peer group counts
        # ------------------------------------------------------

        print()
        print("PEER GROUP COUNTS")
        print("-" * 40)

        print(peer_groups["peer_group_name"].value_counts().sort_index().to_string())

        # ------------------------------------------------------
        # Calculate
        # ------------------------------------------------------

        print()
        print("Calculating peer percentile rankings...")

        results = self.calculate()

        # ------------------------------------------------------
        # Save
        # ------------------------------------------------------

        self.save_results(results)

        # ------------------------------------------------------
        # Results summary
        # ------------------------------------------------------

        print()
        print("=" * 70)
        print("DAY 18 PEER PERCENTILE RESULTS")
        print("=" * 70)

        print(f"RESULT ROWS    : " f"{len(results)}")

        if not results.empty:

            print(f"COMPANIES      : " f"{results['company_id'].nunique()}")

            print(f"PEER GROUPS    : " f"{results['peer_group_name'].nunique()}")

            print(f"METRICS        : " f"{results['metric'].nunique()}")

            print()
            print("METRIC COUNTS")
            print("-" * 40)

            print(results["metric"].value_counts().sort_index().to_string())

        # ------------------------------------------------------
        # Verify SQLite
        # ------------------------------------------------------

        count, groups, metrics, sample = self.verify_results()

        print()
        print(f"SQLITE ROW COUNT: " f"{int(count.iloc[0]['total_rows'])}")

        print()
        print("SAMPLE RESULTS")
        print("-" * 70)

        if not sample.empty:

            print(sample.to_string(index=False))

        print()
        print("=" * 70)
        print("DAY 18 COMPLETE")
        print("=" * 70)


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":

    analyzer = PeerPercentileAnalyzer()

    analyzer.run()
