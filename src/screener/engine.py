import os
import re

import pandas as pd
import yaml

from src.database.database import Database


class ScreenerEngine:

    def __init__(self):

        self.db = Database()
        self.db.connect()

        self.config = self.load_config()

    # ==========================================================
    # CONFIG
    # ==========================================================

    def load_config(self):

        config_path = os.path.join("src", "screener", "screener_config.yaml")

        with open(config_path, "r", encoding="utf-8") as file:

            return yaml.safe_load(file)

    # ==========================================================
    # YEAR HELPERS
    # ==========================================================

    @staticmethod
    def _extract_year(value):

        if value is None:
            return None

        match = re.search(r"(19|20)\d{2}", str(value))

        if not match:
            return None

        return int(match.group(0))

    @staticmethod
    def _safe_cagr(start_value, end_value, years):

        if start_value is None or end_value is None:
            return None

        try:
            start_value = float(start_value)
            end_value = float(end_value)

        except (TypeError, ValueError):
            return None

        if years <= 0:
            return None

        # CAGR is not mathematically meaningful
        # when the starting value is zero/negative.
        if start_value <= 0 or end_value <= 0:
            return None

        try:

            return (((end_value / start_value) ** (1 / years)) - 1) * 100

        except (ZeroDivisionError, ValueError, OverflowError):

            return None

    # ==========================================================
    # LOAD SECTOR DATA
    # ==========================================================

    def _load_sector_data(self):

        try:

            schema = self.db.execute_query("PRAGMA table_info(sectors)")

            if not schema:
                return pd.DataFrame(columns=["company_id", "broad_sector"])

            columns = [row[1] for row in schema]

            rows = self.db.execute_query("SELECT * FROM sectors")

            if not rows:
                return pd.DataFrame(columns=["company_id", "broad_sector"])

            sector_df = pd.DataFrame(rows, columns=columns)

            # Find company ID column
            company_column = None

            preferred_company_columns = ["company_id", "company", "symbol", "ticker"]

            for preferred in preferred_company_columns:
                for column in columns:
                    if column.lower() == preferred.lower():
                        company_column = column
                        break

                if company_column:
                    break

            # Fallback: use first column only if no company ID column exists
            if company_column is None and columns:
                company_column = columns[0]

            # Find broad sector / sector column
            sector_column = None

            preferred_sector_columns = [
                "broad_sector",
                "sector",
                "sector_name",
                "industry",
            ]

            for preferred in preferred_sector_columns:

                for column in columns:

                    if column.lower() == preferred:
                        sector_column = column
                        break

                if sector_column:
                    break

            if company_column is None:

                return pd.DataFrame(columns=["company_id", "broad_sector"])

            if sector_column is None:

                sector_df["broad_sector"] = "Unknown"

                return sector_df[[company_column, "broad_sector"]].rename(
                    columns={company_column: "company_id"}
                )

            return sector_df[[company_column, sector_column]].rename(
                columns={company_column: "company_id", sector_column: "broad_sector"}
            )

        except Exception as error:

            print(f"Warning: Could not load sector data: {error}")

            return pd.DataFrame(columns=["company_id", "broad_sector"])

    # ==========================================================
    # LOAD LATEST MARKET DATA
    # ==========================================================

    def _load_market_data(self):

        query = """
        SELECT
            company_id,
            year,
            market_cap_crore,
            enterprise_value_crore,
            pe_ratio,
            pb_ratio,
            ev_ebitda,
            dividend_yield_pct
        FROM market_cap
        """

        rows = self.db.execute_query(query)

        columns = [
            "company_id",
            "year",
            "market_cap",
            "enterprise_value",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield",
        ]

        market_df = pd.DataFrame(rows, columns=columns)

        if market_df.empty:
            return market_df

        market_df["year_num"] = market_df["year"].apply(self._extract_year)

        market_df = market_df.sort_values(
            ["company_id", "year_num"], na_position="first"
        )

        market_df = market_df.drop_duplicates(subset=["company_id"], keep="last")

        return market_df.drop(columns=["year_num"], errors="ignore")

    # ==========================================================
    # LOAD P&L DATA
    # ==========================================================

    def _load_profit_loss_data(self):

        query = """
        SELECT
            company_id,
            year,
            sales,
            net_profit,
            eps,
            dividend_payout
        FROM profitandloss
        """

        rows = self.db.execute_query(query)

        columns = [
            "company_id",
            "year",
            "sales",
            "net_profit",
            "eps",
            "dividend_payout",
        ]

        pnl = pd.DataFrame(rows, columns=columns)

        if pnl.empty:
            return pnl

        pnl["year_num"] = pnl["year"].apply(self._extract_year)

        return pnl

    # ==========================================================
    # CALCULATE 5-YEAR CAGR
    # ==========================================================

    def _calculate_cagr_data(self, pnl):

        if pnl.empty:

            return pd.DataFrame(
                columns=[
                    "company_id",
                    "revenue_cagr_5yr",
                    "pat_cagr_5yr",
                    "eps_cagr_5yr",
                    "revenue_cagr_3yr",
                ]
            )

        records = []

        for company_id, group in pnl.groupby("company_id"):

            annual = group[group["year_num"].notna()].copy()

            if annual.empty:
                continue

            annual["year_num"] = annual["year_num"].astype(int)

            annual = annual.sort_values("year_num")

            latest_year = int(annual["year_num"].max())

            target_year = latest_year - 5

            # Prefer exact five-year historical point.
            old_rows = annual[annual["year_num"] == target_year]

            latest_rows = annual[annual["year_num"] == latest_year]

            if old_rows.empty:

                records.append(
                    {
                        "company_id": company_id,
                        "revenue_cagr_5yr": None,
                        "pat_cagr_5yr": None,
                        "eps_cagr_5yr": None,
                    }
                )

                continue

            old = old_rows.iloc[-1]
            latest = latest_rows.iloc[-1]

            revenue_cagr = self._safe_cagr(old["sales"], latest["sales"], 5)

            pat_cagr = self._safe_cagr(old["net_profit"], latest["net_profit"], 5)

            eps_cagr = self._safe_cagr(old["eps"], latest["eps"], 5)

            records.append(
                {
                    "company_id": company_id,
                    "revenue_cagr_5yr": revenue_cagr,
                    "pat_cagr_5yr": pat_cagr,
                    "eps_cagr_5yr": eps_cagr,
                }
            )

        return pd.DataFrame(records)

    # ==========================================================
    # CALCULATE 3-YEAR REVENUE CAGR
    # ==========================================================

    def _calculate_revenue_cagr_3yr(self, pnl):

        results = []

        if pnl.empty:
            return pd.DataFrame(columns=["company_id", "revenue_cagr_3yr"])

        for company_id, group in pnl.groupby("company_id"):

            annual = group[group["year_num"].notna()].copy()

            if annual.empty:
                continue

            annual["year_num"] = annual["year_num"].astype(int)

            annual = annual.sort_values("year_num")

            latest_year = int(annual["year_num"].max())

            target_year = latest_year - 3

            old_rows = annual[annual["year_num"] == target_year]

            latest_rows = annual[annual["year_num"] == latest_year]

            if old_rows.empty or latest_rows.empty:
                continue

            old = old_rows.iloc[-1]
            latest = latest_rows.iloc[-1]

            revenue_cagr = self._safe_cagr(old["sales"], latest["sales"], 3)

            results.append({"company_id": company_id, "revenue_cagr_3yr": revenue_cagr})

        return pd.DataFrame(results)

        # ==========================================================

    # CALCULATE D/E DECLINING YEAR-OVER-YEAR
    # ==========================================================

    def _calculate_de_declining(self):

        query = """
        SELECT
            company_id,
            year,
            debt_to_equity
        FROM historical_financial_ratios
        """

        rows = self.db.execute_query(query)

        columns = ["company_id", "year", "debt_to_equity"]

        historical = pd.DataFrame(rows, columns=columns)

        if historical.empty:
            return pd.DataFrame(columns=["company_id", "de_declining"])

        historical["company_id"] = historical["company_id"].astype(str).str.strip()

        historical["year_num"] = historical["year"].apply(self._extract_year)

        historical["debt_to_equity"] = pd.to_numeric(
            historical["debt_to_equity"], errors="coerce"
        )

        historical = historical.dropna(subset=["year_num", "debt_to_equity"])

        results = []

        for company_id, group in historical.groupby("company_id"):

            group = group.sort_values("year_num")

            if len(group) < 2:
                continue

            previous_de = group.iloc[-2]["debt_to_equity"]

            latest_de = group.iloc[-1]["debt_to_equity"]

            results.append(
                {"company_id": company_id, "de_declining": (latest_de < previous_de)}
            )

        return pd.DataFrame(results)

    # ==========================================================
    # LOAD CASH FLOW DATA
    # ==========================================================

    def _load_cashflow_data(self):

        query = """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity,
            net_cash_flow
        FROM cashflow
        """

        rows = self.db.execute_query(query)

        columns = [
            "company_id",
            "year",
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ]

        if not rows:
            return pd.DataFrame(columns=columns)

        cashflow = pd.DataFrame(rows, columns=columns)

        cashflow["company_id"] = cashflow["company_id"].astype(str).str.strip()

        cashflow["operating_activity"] = pd.to_numeric(
            cashflow["operating_activity"], errors="coerce"
        )

        cashflow["investing_activity"] = pd.to_numeric(
            cashflow["investing_activity"], errors="coerce"
        )

        cashflow["financing_activity"] = pd.to_numeric(
            cashflow["financing_activity"], errors="coerce"
        )

        cashflow["net_cash_flow"] = pd.to_numeric(
            cashflow["net_cash_flow"], errors="coerce"
        )

        return cashflow

    # ==========================================================
    # CALCULATE FCF CAGR
    # ==========================================================

    def _calculate_fcf_cagr_data(self, cashflow):

        if cashflow.empty:
            return pd.DataFrame(columns=["company_id", "fcf_cagr"])

        data = cashflow.copy()

        # ------------------------------------------------------
        # Convert numeric fields
        # ------------------------------------------------------

        data["operating_activity"] = pd.to_numeric(
            data["operating_activity"], errors="coerce"
        )

        data["investing_activity"] = pd.to_numeric(
            data["investing_activity"], errors="coerce"
        )

        # ------------------------------------------------------
        # Calculate Free Cash Flow
        # FCF = Operating Cash Flow + Investing Cash Flow
        # ------------------------------------------------------

        data["free_cash_flow"] = data["operating_activity"] + data["investing_activity"]

        # ------------------------------------------------------
        # Extract year
        # ------------------------------------------------------

        data["year_num"] = data["year"].apply(self._extract_year)

        data["company_id"] = data["company_id"].astype(str).str.strip()

        data = data.dropna(subset=["company_id", "year_num", "free_cash_flow"])

        results = []

        # ------------------------------------------------------
        # Calculate 5-year FCF CAGR
        # ------------------------------------------------------

        for company_id, group in data.groupby("company_id"):

            group = group.sort_values("year_num")

            if len(group) < 2:
                continue

            latest = group.iloc[-1]

            latest_year = int(latest["year_num"])

            # Target year = 5 years before latest
            target_year = latest_year - 5

            historical = group[group["year_num"] == target_year]

            if historical.empty:
                # Use the closest available year
                # that is at least 4 years old.
                older = group[group["year_num"] <= target_year]

                if older.empty:
                    continue

                historical = older.iloc[[-1]]

            old_value = float(historical.iloc[0]["free_cash_flow"])

            new_value = float(latest["free_cash_flow"])

            # CAGR requires positive starting and ending values.
            if old_value <= 0 or new_value <= 0:
                fcf_cagr = None

            else:
                years = latest_year - int(historical.iloc[0]["year_num"])

                if years <= 0:
                    fcf_cagr = None

                else:
                    fcf_cagr = ((new_value / old_value) ** (1 / years) - 1) * 100

            results.append({"company_id": company_id, "fcf_cagr": fcf_cagr})

        return pd.DataFrame(results)

    # ==========================================================
    # LOAD CURRENT P&L VALUES
    # ==========================================================

    def _latest_pnl_values(self, pnl): ...

    # ==========================================================
    # LOAD CURRENT P&L VALUES
    # ==========================================================

    def _latest_pnl_values(self, pnl):

        if pnl.empty:

            return pd.DataFrame(
                columns=["company_id", "sales", "net_profit", "eps", "dividend_payout"]
            )

        result = []

        for company_id, group in pnl.groupby("company_id"):

            group = group.copy()

            # ------------------------------------------------------
            # Current P&L values
            # Prefer TTM because it is the most current value.
            # ------------------------------------------------------

            ttm = group[group["year"].astype(str).str.upper().str.contains("TTM")]

            if not ttm.empty:
                latest = ttm.iloc[-1]
            else:
                annual = group[group["year_num"].notna()].copy()

                if annual.empty:
                    continue

                annual = annual.sort_values("year_num")
                latest = annual.iloc[-1]

            # ------------------------------------------------------
            # Dividend payout
            #
            # Do NOT use TTM when dividend_payout is NULL.
            # Use the latest available annual dividend payout.
            # ------------------------------------------------------

            dividend_payout = None

            annual_dividend = group[
                group["year_num"].notna() & group["dividend_payout"].notna()
            ].copy()

            if not annual_dividend.empty:

                annual_dividend = annual_dividend.sort_values("year_num")

                dividend_payout = annual_dividend.iloc[-1]["dividend_payout"]

            else:

                # Fallback: if no annual payout exists,
                # use a non-null TTM payout if available.
                ttm_dividend = group[group["dividend_payout"].notna()]

                if not ttm_dividend.empty:
                    dividend_payout = ttm_dividend.iloc[-1]["dividend_payout"]

            result.append(
                {
                    "company_id": company_id,
                    "sales": latest["sales"],
                    "net_profit": latest["net_profit"],
                    "eps": latest["eps"],
                    "dividend_payout": dividend_payout,
                }
            )

        return pd.DataFrame(result)

    # ==========================================================
    # LOAD ALL FINANCIAL DATA
    # ==========================================================

    def load_financial_data(self):

        query = """
        SELECT
            fr.id,
            fr.company_id,
            fr.revenue_growth,
            fr.profit_growth,
            fr.net_profit_margin,
            fr.operating_profit_margin,
            fr.roe,
            fr.roce,
            fr.debt_to_equity,
            fr.interest_coverage,
            fr.asset_turnover,
            fr.net_debt,
            fr.free_cash_flow,
            fr.cfo_quality,
            fr.capex_intensity,
            fr.icr_label,
            fr.icr_warning,
            fr.high_leverage
        FROM financial_ratios fr
        """

        rows = self.db.execute_query(query)

        columns = [
            "id",
            "company_id",
            "revenue_growth",
            "profit_growth",
            "net_profit_margin",
            "operating_profit_margin",
            "roe",
            "roce",
            "debt_to_equity",
            "interest_coverage",
            "asset_turnover",
            "net_debt",
            "free_cash_flow",
            "cfo_quality",
            "capex_intensity",
            "icr_label",
            "icr_warning",
            "high_leverage",
        ]

        df = pd.DataFrame(rows, columns=columns)

        # ------------------------------------------------------
        # Market data
        # ------------------------------------------------------

        market_df = self._load_market_data()

        if not market_df.empty:

            df = df.merge(market_df, on="company_id", how="left")

        # ------------------------------------------------------
        # P&L data
        # ------------------------------------------------------

        pnl = self._load_profit_loss_data()

        latest_pnl = self._latest_pnl_values(pnl)

        if not latest_pnl.empty:

            df = df.merge(latest_pnl, on="company_id", how="left")

        # ------------------------------------------------------
        # 5-year CAGR
        # ------------------------------------------------------

        cagr_df = self._calculate_cagr_data(pnl)

        if not cagr_df.empty:

            df = df.merge(cagr_df, on="company_id", how="left")

        else:

            df["revenue_cagr_5yr"] = None
            df["pat_cagr_5yr"] = None
            df["eps_cagr_5yr"] = None

            # ------------------------------------------------------
        # 3-year Revenue CAGR
        # ------------------------------------------------------

        cagr_3yr_df = self._calculate_revenue_cagr_3yr(pnl)

        if not cagr_3yr_df.empty:

            df = df.merge(cagr_3yr_df, on="company_id", how="left")

        else:

            df["revenue_cagr_3yr"] = None

        # ------------------------------------------------------
        # FCF CAGR
        # ------------------------------------------------------

        cashflow = self._load_cashflow_data()

        fcf_cagr_df = self._calculate_fcf_cagr_data(cashflow)

        if not fcf_cagr_df.empty:

            df = df.merge(fcf_cagr_df, on="company_id", how="left")

        else:

            df["fcf_cagr"] = None

        # ------------------------------------------------------
        # D/E Declining Year-over-Year
        # ------------------------------------------------------

        de_declining_df = self._calculate_de_declining()

        if not de_declining_df.empty:

            df = df.merge(de_declining_df, on="company_id", how="left")

        else:

            df["de_declining"] = False

        # ------------------------------------------------------
        # Sector
        # ------------------------------------------------------

        sector_df = self._load_sector_data()

        if not sector_df.empty:

            # Normalize company_id types before merging.
            # financial_ratios uses TEXT company IDs,
            # while sectors may contain INTEGER IDs.
            df["company_id"] = df["company_id"].astype(str).str.strip()

            sector_df["company_id"] = sector_df["company_id"].astype(str).str.strip()

            df = df.merge(sector_df, on="company_id", how="left")

        else:

            df["broad_sector"] = "Unknown"

        if "broad_sector" not in df.columns:

            df["broad_sector"] = "Unknown"

        df["broad_sector"] = df["broad_sector"].fillna("Unknown").astype(str)

        # ------------------------------------------------------
        # Debt-free ICR
        # ------------------------------------------------------

        debt_free_mask = (
            df["icr_label"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["debt free", "debt-free", "debtfree"])
        )

        df.loc[debt_free_mask, "interest_coverage"] = float("inf")

        # ------------------------------------------------------
        # Numeric conversion
        # ------------------------------------------------------

        numeric_columns = [
            "revenue_growth",
            "profit_growth",
            "net_profit_margin",
            "operating_profit_margin",
            "roe",
            "roce",
            "debt_to_equity",
            "interest_coverage",
            "asset_turnover",
            "net_debt",
            "free_cash_flow",
            "cfo_quality",
            "capex_intensity",
            "market_cap",
            "enterprise_value",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield",
            "sales",
            "net_profit",
            "eps",
            "dividend_payout",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
            "eps_cagr_5yr",
            "revenue_cagr_3yr",
        ]

        for column in numeric_columns:

            if column in df.columns:

                df[column] = pd.to_numeric(df[column], errors="coerce")

        # ------------------------------------------------------
        # Composite Quality Score
        # ------------------------------------------------------

        df = self.calculate_composite_score(df)

        # Backward-compatible column name expected by tests
        df["sector_quality_score"] = df["sector_relative_score"]

        return df

    # ==========================================================
    # WINSORISATION
    # ==========================================================

    def winsorize_score(self, series, inverse=False):

        values = pd.to_numeric(series, errors="coerce")

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
    # COMPOSITE QUALITY SCORE
    # ==========================================================

    def calculate_composite_score(self, df):

        df = df.copy()

        # ------------------------------------------------------
        # Profitability - 35%
        # ROE 15% + ROCE 10% + NPM 10%
        # ------------------------------------------------------

        df["roe_score"] = self.winsorize_score(df["roe"])

        df["roce_score"] = self.winsorize_score(df["roce"])

        df["npm_score"] = self.winsorize_score(df["net_profit_margin"])

        profitability = (
            df["roe_score"] * 0.15 + df["roce_score"] * 0.10 + df["npm_score"] * 0.10
        )

        # ------------------------------------------------------
        # Cash Quality - 30%
        # FCF CAGR 15%
        # CFO/PAT ratio 10%
        # FCF positive flag 5%
        # ------------------------------------------------------

        # FCF CAGR - 15%
        # Higher FCF CAGR receives a higher score.

        df["fcf_score"] = self.winsorize_score(df["fcf_cagr"])

        if "cfo_quality" in df.columns:

            df["cfo_pat_score"] = self.winsorize_score(df["cfo_quality"])

        else:

            df["cfo_pat_score"] = 50.0

        df["fcf_positive_score"] = (
            pd.to_numeric(df["free_cash_flow"], errors="coerce") > 0
        ).astype(float) * 100

        cash_quality = (
            df["fcf_score"] * 0.15
            + df["cfo_pat_score"] * 0.10
            + df["fcf_positive_score"] * 0.05
        )

        # ------------------------------------------------------
        # Growth - 20%
        # Revenue CAGR 10% + PAT CAGR 10%
        # ------------------------------------------------------

        df["revenue_cagr_score"] = self.winsorize_score(df["revenue_cagr_5yr"])

        df["pat_cagr_score"] = self.winsorize_score(df["pat_cagr_5yr"])

        growth = df["revenue_cagr_score"] * 0.10 + df["pat_cagr_score"] * 0.10

        # ------------------------------------------------------
        # Leverage - 15%
        # D/E 10% + ICR 5%
        # ------------------------------------------------------

        df["de_score"] = self.winsorize_score(df["debt_to_equity"], inverse=True)

        df["icr_score"] = self.winsorize_score(df["interest_coverage"])

        leverage = df["de_score"] * 0.10 + df["icr_score"] * 0.05

        # ------------------------------------------------------
        # Raw composite
        # ------------------------------------------------------

        df["composite_quality_score"] = profitability + cash_quality + growth + leverage

        # ------------------------------------------------------
        # Sector-relative composite score
        # ------------------------------------------------------

        if "broad_sector" in df.columns and df["broad_sector"].nunique() > 1:

            sector_scores = []

            for sector, group in df.groupby("broad_sector", dropna=False):

                group = group.copy()

                if len(group) == 1:

                    group["sector_relative_score"] = group["composite_quality_score"]

                else:

                    group["sector_relative_score"] = self.winsorize_score(
                        group["composite_quality_score"]
                    )

                sector_scores.append(group)

            df = pd.concat(sector_scores, ignore_index=True)

        else:

            df["sector_relative_score"] = df["composite_quality_score"]

        return df

    # ==========================================================
    # FILTER METHODS
    # ==========================================================

    def filter_by_roe(self, minimum_roe):

        df = self.load_financial_data()

        return df[df["roe"] >= minimum_roe].reset_index(drop=True)

    def filter_by_roce(self, minimum_roce):

        df = self.load_financial_data()

        return df[df["roce"] >= minimum_roce].reset_index(drop=True)

    def filter_by_debt_to_equity(self, maximum_debt):

        df = self.load_financial_data()

        # Financial sector D/E is not filtered because
        # leverage is intrinsic to banking/financial businesses.
        if "broad_sector" in df.columns:

            financial_mask = (
                df["broad_sector"]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains("financial")
            )

            non_financial = df[~financial_mask]

            financials = df[financial_mask]

            non_financial = non_financial[
                non_financial["debt_to_equity"] <= maximum_debt
            ]

            return pd.concat([financials, non_financial], ignore_index=True)

        return df[df["debt_to_equity"] <= maximum_debt].reset_index(drop=True)

    def filter_by_free_cash_flow(self, minimum_fcf):

        df = self.load_financial_data()

        return df[df["free_cash_flow"] >= minimum_fcf].reset_index(drop=True)

    def filter_by_revenue_growth(self, minimum_growth):

        df = self.load_financial_data()

        return df[df["revenue_cagr_5yr"] >= minimum_growth].reset_index(drop=True)

    def filter_by_profit_growth(self, minimum_growth):

        df = self.load_financial_data()

        return df[df["pat_cagr_5yr"] >= minimum_growth].reset_index(drop=True)

    def filter_by_market_cap(self, minimum_market_cap):

        df = self.load_financial_data()

        return df[df["market_cap"] >= minimum_market_cap].reset_index(drop=True)

    def filter_by_pe(self, maximum_pe):

        df = self.load_financial_data()

        return df[df["pe_ratio"] <= maximum_pe].reset_index(drop=True)

    def filter_by_pb(self, maximum_pb):

        df = self.load_financial_data()

        return df[df["pb_ratio"] <= maximum_pb].reset_index(drop=True)

    def filter_by_dividend_yield(self, minimum_dividend):

        df = self.load_financial_data()

        return df[df["dividend_yield"] >= minimum_dividend].reset_index(drop=True)

    def filter_by_sales(self, minimum_sales):

        df = self.load_financial_data()

        return df[df["sales"] >= minimum_sales].reset_index(drop=True)

    def filter_by_opm(self, minimum_opm):

        df = self.load_financial_data()

        return df[df["operating_profit_margin"] >= minimum_opm].reset_index(drop=True)

    def filter_by_interest_coverage(self, minimum_icr):

        df = self.load_financial_data()

        # Debt Free companies have infinity ICR
        debt_free = (
            df["icr_label"]
            .fillna("")
            .astype(str)
            .str.lower()
            .isin(["debt free", "debt-free", "debtfree"])
        )

        passed = df["interest_coverage"] >= minimum_icr

        return df[passed | debt_free].reset_index(drop=True)

    def filter_by_asset_turnover(self, minimum_turnover):

        df = self.load_financial_data()

        return df[df["asset_turnover"] >= minimum_turnover].reset_index(drop=True)

    def filter_by_net_profit(self, minimum_net_profit):

        df = self.load_financial_data()

        return df[df["net_profit"] >= minimum_net_profit].reset_index(drop=True)

    def filter_by_eps_cagr(self, minimum_eps_cagr):

        df = self.load_financial_data()

        return df[df["eps_cagr_5yr"] >= minimum_eps_cagr].reset_index(drop=True)

    # ==========================================================
    # FILTER APPLICATION
    # ==========================================================

    def _apply_filter(self, df, key, value):

        if value is None:
            return df

        if key == "roe_min":

            return df[df["roe"] >= value]

        if key in ("de_max", "debt_to_equity_max"):

            # ------------------------------------------------------
            # Strict debt-free condition
            # de_max = 0 means D/E must actually be <= 0.
            # Financial-sector exception is NOT applied here.
            # ------------------------------------------------------

            if float(value) == 0.0:

                return df[pd.to_numeric(df["debt_to_equity"], errors="coerce") <= 0]

            # ------------------------------------------------------
            # Normal D/E limit
            # Financial-sector exception is retained for
            # non-zero D/E limits.
            # ------------------------------------------------------

            financial_mask = (
                df["broad_sector"]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains("financial")
            )

            return pd.concat(
                [
                    df[financial_mask],
                    df[~financial_mask][
                        pd.to_numeric(
                            df[~financial_mask]["debt_to_equity"], errors="coerce"
                        )
                        <= value
                    ],
                ],
                ignore_index=True,
            )

        if key == "fcf_min":

            return df[df["free_cash_flow"] >= value]

        if key == "revenue_growth_min":

            return df[df["revenue_growth"] >= value]

        if key in ("revenue_cagr_min", "revenue_cagr_5yr_min"):
            return df[df["revenue_cagr_5yr"] >= value]

        if key == "revenue_cagr_3yr_min":
            return df[df["revenue_cagr_3yr"] >= value]

        if key in ("pat_cagr_min", "pat_cagr_5yr_min", "profit_growth_min"):

            return df[df["pat_cagr_5yr"] >= value]

        if key == "opm_min":

            return df[df["operating_profit_margin"] >= value]

        if key == "pe_max":

            return df[df["pe_ratio"] <= value]

        if key == "pb_max":

            return df[df["pb_ratio"] <= value]

        if key == "dividend_yield_min":

            return df[df["dividend_yield"] >= value]

        if key == "icr_min":

            debt_free = (
                df["icr_label"]
                .fillna("")
                .astype(str)
                .str.lower()
                .isin(["debt free", "debt-free", "debtfree"])
            )

            return df[(df["interest_coverage"] >= value) | debt_free]

        if key == "market_cap_min":

            return df[df["market_cap"] >= value]

        if key == "net_profit_min":

            return df[df["net_profit"] >= value]

        if key == "eps_cagr_min":

            return df[df["eps_cagr_5yr"] >= value]

        if key == "asset_turnover_min":

            return df[df["asset_turnover"] >= value]

        if key == "dividend_payout_max":

            return df[df["dividend_payout"] <= value]
        if key == "sales_min":

            return df[df["sales"] >= value]
        if key == "de_declining":

            return df[df["de_declining"].fillna(False).astype(bool)]

        raise ValueError(f"Unsupported screener filter: {key}")

    # ==========================================================
    # MAIN FILTER ENGINE
    # ==========================================================

    def filter_data(self, filters):

        df = self.load_financial_data()

        # Calculate composite before filtering.
        df = self.calculate_composite_score(df)

        # ------------------------------------------------------
        # Preset from YAML
        # ------------------------------------------------------

        if isinstance(filters, str):

            if filters not in self.config:

                raise ValueError(f"Preset '{filters}' not found.")

            preset = self.config[filters]

            for key, value in preset.items():

                df = self._apply_filter(df, key, value)

        # ------------------------------------------------------
        # Custom filters
        # ------------------------------------------------------

        elif isinstance(filters, dict):

            for key, condition in filters.items():

                # Support:
                # {"roe_min": 15}
                if isinstance(condition, (int, float)):

                    df = self._apply_filter(df, key, condition)

                    continue

                # Support old style:
                # {"roe": (15, None)}
                if isinstance(condition, (tuple, list)):

                    if len(condition) != 2:

                        raise ValueError(f"Invalid filter condition: {key}")

                    minimum = condition[0]
                    maximum = condition[1]

                    if minimum is not None:

                        df = self._apply_filter(df, f"{key}_min", minimum)

                    if maximum is not None:

                        df = self._apply_filter(df, f"{key}_max", maximum)

                    continue

                raise ValueError(f"Invalid filter value for '{key}'.")

        else:

            raise ValueError("Filters must be a preset name or dictionary.")

        # ------------------------------------------------------
        # Final sorting
        # ------------------------------------------------------

        df = df.sort_values(by="composite_quality_score", ascending=False)

        return df.reset_index(drop=True)

    # ==========================================================
    # QUALITY STOCKS - BACKWARD COMPATIBILITY
    # ==========================================================

    def filter_quality_stocks(
        self, min_roe, min_roce, max_debt, min_revenue_growth, min_free_cash_flow
    ):

        df = self.load_financial_data()

        df = self.calculate_composite_score(df)

        df = df[df["roe"] >= min_roe]

        df = df[df["roce"] >= min_roce]

        # Use Financials exception.
        financial_mask = (
            df["broad_sector"]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains("financial")
        )

        df = pd.concat(
            [
                df[financial_mask],
                df[~financial_mask][df[~financial_mask]["debt_to_equity"] <= max_debt],
            ],
            ignore_index=True,
        )

        df = df[df["revenue_cagr_5yr"] >= min_revenue_growth]

        df = df[df["free_cash_flow"] >= min_free_cash_flow]

        return df.sort_values(
            by="composite_quality_score", ascending=False
        ).reset_index(drop=True)

    # ==========================================================
    # CLOSE DATABASE
    # ==========================================================

    def close(self):

        self.db.close()
