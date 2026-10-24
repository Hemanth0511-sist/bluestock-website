from typing import Any

import pandas as pd
import requests


class DataValidator:
    """
    Data Quality validation engine for the N100 Financial Intelligence Platform.

    Implements DQ-01 through DQ-14 from the project specification.
    """

    RULE_SEVERITY = {
        "DQ-01": "CRITICAL",
        "DQ-02": "CRITICAL",
        "DQ-03": "CRITICAL",
        "DQ-04": "WARNING",
        "DQ-05": "WARNING",
        "DQ-06": "WARNING",
        "DQ-07": "CRITICAL",
        "DQ-08": "CRITICAL",
        "DQ-09": "WARNING",
        "DQ-10": "WARNING",
        "DQ-11": "WARNING",
        "DQ-12": "WARNING",
        "DQ-13": "WARNING",
        "DQ-14": "WARNING",
    }

    # ---------------------------------------------------------
    # GENERAL HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _find_column(df: pd.DataFrame, *names: str) -> str | None:
        """
        Find a column using case-insensitive matching.
        """

        if df is None:
            return None

        mapping = {str(column).strip().lower(): column for column in df.columns}

        for name in names:
            key = str(name).strip().lower()

            if key in mapping:
                return mapping[key]

        return None

    @staticmethod
    def _result(
        rule_id: str,
        valid: bool,
        message: str,
        row_indices=None,
    ) -> dict[str, Any]:
        """
        Standard result format for every DQ rule.
        """

        return {
            "rule_id": rule_id,
            "severity": DataValidator.RULE_SEVERITY[rule_id],
            "valid": bool(valid),
            "message": message,
            "row_indices": list(row_indices or []),
        }

    @staticmethod
    def _numeric_series(
        df: pd.DataFrame,
        column: str,
    ) -> pd.Series:
        """
        Convert a DataFrame column to numeric safely.
        """

        return pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # =========================================================
    # DQ-01
    # Company PK Uniqueness
    # =========================================================

    def check_dq_01(self, df: pd.DataFrame) -> dict[str, Any]:

        column = self._find_column(
            df,
            "id",
            "company_id",
            "ticker",
        )

        if column is None:
            return self._result(
                "DQ-01",
                False,
                "Company primary-key column not found.",
            )

        duplicates = df[column].duplicated(keep=False)

        indices = df.index[duplicates].tolist()

        return self._result(
            "DQ-01",
            len(indices) == 0,
            (
                "Company primary key is unique."
                if len(indices) == 0
                else "Duplicate company primary keys found."
            ),
            indices,
        )

    # =========================================================
    # DQ-02
    # Annual PK Uniqueness
    # =========================================================

    def check_dq_02(self, df: pd.DataFrame) -> dict[str, Any]:

        company_column = self._find_column(
            df,
            "company_id",
            "id",
            "ticker",
        )

        year_column = self._find_column(
            df,
            "year",
            "financial_year",
            "period",
        )

        if company_column is None or year_column is None:
            return self._result(
                "DQ-02",
                False,
                "company_id/year columns not found.",
            )

        duplicates = df.duplicated(
            subset=[company_column, year_column],
            keep=False,
        )

        indices = df.index[duplicates].tolist()

        return self._result(
            "DQ-02",
            len(indices) == 0,
            (
                "Annual company/year keys are unique."
                if len(indices) == 0
                else "Duplicate company/year records found."
            ),
            indices,
        )

    # =========================================================
    # DQ-03
    # Foreign Key Integrity
    # =========================================================

    def check_dq_03(
        self,
        df: pd.DataFrame,
        companies_df: pd.DataFrame | None = None,
    ) -> dict[str, Any]:

        if companies_df is None:
            return self._result(
                "DQ-03",
                False,
                "Reference companies DataFrame is required.",
            )

        child_column = self._find_column(
            df,
            "company_id",
            "id",
            "ticker",
        )

        parent_column = self._find_column(
            companies_df,
            "id",
            "company_id",
            "ticker",
        )

        if child_column is None or parent_column is None:
            return self._result(
                "DQ-03",
                False,
                "Foreign-key columns not found.",
            )

        parent_values = set(
            companies_df[parent_column].dropna().astype(str).str.strip().str.upper()
        )

        child_values = df[child_column].astype(str).str.strip().str.upper()

        invalid = ~child_values.isin(parent_values)

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-03",
            len(indices) == 0,
            (
                "All child company IDs exist in companies."
                if len(indices) == 0
                else "Orphan company IDs found."
            ),
            indices,
        )

    # =========================================================
    # DQ-04
    # Balance Sheet Balance
    # =========================================================

    def check_dq_04(self, df: pd.DataFrame) -> dict[str, Any]:

        assets_col = self._find_column(
            df,
            "total_assets",
        )

        liabilities_col = self._find_column(
            df,
            "total_liabilities",
            "liabilities",
        )

        if assets_col is None or liabilities_col is None:
            return self._result(
                "DQ-04",
                False,
                "total_assets/total_liabilities columns not found.",
            )

        assets = self._numeric_series(
            df,
            assets_col,
        )

        liabilities = self._numeric_series(
            df,
            liabilities_col,
        )

        valid_assets = assets.abs() > 0

        difference = (assets - liabilities).abs() / assets.abs()

        invalid = valid_assets & (difference >= 0.01)

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-04",
            len(indices) == 0,
            (
                "Balance sheet balance check passed."
                if len(indices) == 0
                else "Balance sheet imbalance exceeds 1%."
            ),
            indices,
        )

    # =========================================================
    # DQ-05
    # OPM Cross-Check
    # =========================================================

    def check_dq_05(self, df: pd.DataFrame) -> dict[str, Any]:

        source_opm_col = self._find_column(
            df,
            "opm_percentage",
            "opm",
        )

        operating_profit_col = self._find_column(
            df,
            "operating_profit",
            "op_profit",
        )

        sales_col = self._find_column(
            df,
            "sales",
            "revenue",
        )

        if source_opm_col is None or operating_profit_col is None or sales_col is None:
            return self._result(
                "DQ-05",
                False,
                "OPM cross-check columns not found.",
            )

        source_opm = self._numeric_series(
            df,
            source_opm_col,
        )

        operating_profit = self._numeric_series(
            df,
            operating_profit_col,
        )

        sales = self._numeric_series(
            df,
            sales_col,
        )

        calculated_opm = operating_profit / sales * 100

        divergence = (source_opm - calculated_opm).abs()

        invalid = (
            sales.notna()
            & sales.ne(0)
            & source_opm.notna()
            & calculated_opm.notna()
            & (divergence >= 1.0)
        )

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-05",
            len(indices) == 0,
            (
                "OPM cross-check passed."
                if len(indices) == 0
                else "OPM divergence is greater than or equal to 1 percentage point."
            ),
            indices,
        )

    # =========================================================
    # DQ-06
    # Positive Sales
    # =========================================================

    def check_dq_06(self, df: pd.DataFrame) -> dict[str, Any]:

        sales_col = self._find_column(
            df,
            "sales",
            "revenue",
        )

        if sales_col is None:
            return self._result(
                "DQ-06",
                False,
                "Sales column not found.",
            )

        sales = self._numeric_series(
            df,
            sales_col,
        )

        # Bank / financial-company identification
        sector_col = self._find_column(
            df,
            "broad_sector",
            "sector",
        )

        bank_col = self._find_column(
            df,
            "is_bank",
        )

        if bank_col is not None:
            is_bank = (
                df[bank_col].astype(str).str.lower().isin(["true", "1", "yes", "y"])
            )
        elif sector_col is not None:
            sector = df[sector_col].astype(str).str.lower()

            is_bank = sector.str.contains(
                "financial",
                na=False,
            ) | sector.str.contains(
                "bank",
                na=False,
            )
        else:
            is_bank = pd.Series(
                False,
                index=df.index,
            )

        invalid = sales.notna() & (sales <= 0) & (~is_bank)

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-06",
            len(indices) == 0,
            (
                "Positive sales check passed."
                if len(indices) == 0
                else "Non-bank company has sales less than or equal to zero."
            ),
            indices,
        )

    # =========================================================
    # DQ-07
    # Year Format
    # =========================================================

    def check_dq_07(self, df: pd.DataFrame) -> dict[str, Any]:

        year_col = self._find_column(
            df,
            "year",
            "financial_year",
            "period",
        )

        if year_col is None:
            return self._result(
                "DQ-07",
                False,
                "Year column not found.",
            )

        values = df[year_col].astype(str)

        valid = values.str.fullmatch(
            r"\d{4}-\d{2}",
            na=False,
        )

        invalid = ~valid

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-07",
            len(indices) == 0,
            (
                "All year values match YYYY-MM."
                if len(indices) == 0
                else "Invalid year format found."
            ),
            indices,
        )

    # =========================================================
    # DQ-08
    # Ticker Format
    # =========================================================

    def check_dq_08(self, df: pd.DataFrame) -> dict[str, Any]:

        column = self._find_column(
            df,
            "company_id",
            "ticker",
            "id",
        )

        if column is None:
            return self._result(
                "DQ-08",
                False,
                "Ticker/company_id column not found.",
            )

        values = df[column].fillna("").astype(str).str.strip().str.upper()

        valid = values.str.fullmatch(
            r"[A-Z0-9._&-]{2,12}",
            na=False,
        )

        invalid = ~valid

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-08",
            len(indices) == 0,
            (
                "Ticker format is valid."
                if len(indices) == 0
                else "Invalid ticker format found."
            ),
            indices,
        )

    # =========================================================
    # DQ-09
    # Net Cash Flow Check
    # =========================================================

    def check_dq_09(self, df: pd.DataFrame) -> dict[str, Any]:

        net_col = self._find_column(
            df,
            "net_cash_flow",
        )

        cfo_col = self._find_column(
            df,
            "cfo",
            "cash_from_operations",
            "operating_cash_flow",
        )

        cfi_col = self._find_column(
            df,
            "cfi",
            "cash_from_investing",
            "investing_cash_flow",
        )

        cff_col = self._find_column(
            df,
            "cff",
            "cash_from_financing",
            "financing_cash_flow",
        )

        if None in (
            net_col,
            cfo_col,
            cfi_col,
            cff_col,
        ):
            return self._result(
                "DQ-09",
                False,
                "Cash flow component columns not found.",
            )

        net_cash = self._numeric_series(
            df,
            net_col,
        )

        cfo = self._numeric_series(
            df,
            cfo_col,
        )

        cfi = self._numeric_series(
            df,
            cfi_col,
        )

        cff = self._numeric_series(
            df,
            cff_col,
        )

        calculated = cfo + cfi + cff

        difference = (net_cash - calculated).abs()

        invalid = net_cash.notna() & calculated.notna() & (difference > 10)

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-09",
            len(indices) == 0,
            (
                "Net cash flow check passed."
                if len(indices) == 0
                else "Net cash flow differs from CFO + CFI + CFF by more than 10."
            ),
            indices,
        )

    # =========================================================
    # DQ-10
    # Non-Negative Fixed Assets
    # =========================================================

    def check_dq_10(self, df: pd.DataFrame) -> dict[str, Any]:

        column = self._find_column(
            df,
            "fixed_assets",
        )

        if column is None:
            return self._result(
                "DQ-10",
                False,
                "fixed_assets column not found.",
            )

        values = self._numeric_series(
            df,
            column,
        )

        invalid = values.notna() & (values < 0)

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-10",
            len(indices) == 0,
            (
                "Fixed assets are non-negative."
                if len(indices) == 0
                else "Negative fixed assets found."
            ),
            indices,
        )

    # =========================================================
    # DQ-11
    # Tax Rate Range
    # =========================================================

    def check_dq_11(self, df: pd.DataFrame) -> dict[str, Any]:

        column = self._find_column(
            df,
            "tax_percentage",
            "tax_rate",
            "tax_pct",
        )

        if column is None:
            return self._result(
                "DQ-11",
                False,
                "Tax percentage column not found.",
            )

        values = self._numeric_series(
            df,
            column,
        )

        invalid = values.notna() & ((values < 0) | (values > 60))

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-11",
            len(indices) == 0,
            (
                "Tax rate is within 0-60%."
                if len(indices) == 0
                else "Tax rate is outside the allowed 0-60% range."
            ),
            indices,
        )

    # =========================================================
    # DQ-12
    # Dividend Payout Cap
    # =========================================================

    def check_dq_12(self, df: pd.DataFrame) -> dict[str, Any]:

        column = self._find_column(
            df,
            "dividend_payout",
            "dividend_payout_pct",
            "payout_ratio",
        )

        if column is None:
            return self._result(
                "DQ-12",
                False,
                "Dividend payout column not found.",
            )

        values = self._numeric_series(
            df,
            column,
        )

        invalid = values.notna() & (values > 200)

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-12",
            len(indices) == 0,
            (
                "Dividend payout is within 200%."
                if len(indices) == 0
                else "Dividend payout exceeds 200%."
            ),
            indices,
        )

    # =========================================================
    # DQ-13
    # URL Validity
    # =========================================================

    @staticmethod
    def check_url(url: str) -> bool:

        if not isinstance(url, str):
            return False

        url = url.strip()

        if not url:
            return False

        try:
            response = requests.head(
                url,
                timeout=10,
                allow_redirects=True,
            )

            return response.status_code == 200

        except requests.RequestException:
            return False

    def check_dq_13(self, df: pd.DataFrame) -> dict[str, Any]:

        url_col = self._find_column(
            df,
            "Annual_Report",
            "annual_report",
            "annual_report_url",
            "report_url",
            "url",
        )

        if url_col is None:
            return self._result(
                "DQ-13",
                False,
                "Annual report URL column not found.",
            )

        invalid_indices = []

        for index, value in df[url_col].items():

            if not self.check_url(value):
                invalid_indices.append(index)

        return self._result(
            "DQ-13",
            len(invalid_indices) == 0,
            (
                "All annual report URLs are valid."
                if len(invalid_indices) == 0
                else "Invalid or unavailable annual report URLs found."
            ),
            invalid_indices,
        )

    # =========================================================
    # DQ-14
    # EPS Sign Consistency
    # =========================================================

    def check_dq_14(self, df: pd.DataFrame) -> dict[str, Any]:

        eps_col = self._find_column(
            df,
            "eps",
            "earnings_per_share",
        )

        profit_col = self._find_column(
            df,
            "net_profit",
            "profit_after_tax",
            "pat",
        )

        if eps_col is None or profit_col is None:
            return self._result(
                "DQ-14",
                False,
                "EPS/net_profit columns not found.",
            )

        eps = self._numeric_series(
            df,
            eps_col,
        )

        profit = self._numeric_series(
            df,
            profit_col,
        )

        invalid = profit.notna() & eps.notna() & (profit > 0) & (eps <= 0)

        indices = df.index[invalid].tolist()

        return self._result(
            "DQ-14",
            len(indices) == 0,
            (
                "EPS sign is consistent with positive net profit."
                if len(indices) == 0
                else "Positive net profit has non-positive EPS."
            ),
            indices,
        )

    # =========================================================
    # RUN ONE RULE
    # =========================================================

    def validate_rule(
        self,
        rule_id: str,
        df: pd.DataFrame,
        companies_df: pd.DataFrame | None = None,
    ) -> dict[str, Any]:

        rule_id = rule_id.upper().strip()

        methods = {
            "DQ-01": self.check_dq_01,
            "DQ-02": self.check_dq_02,
            "DQ-03": lambda data: self.check_dq_03(
                data,
                companies_df,
            ),
            "DQ-04": self.check_dq_04,
            "DQ-05": self.check_dq_05,
            "DQ-06": self.check_dq_06,
            "DQ-07": self.check_dq_07,
            "DQ-08": self.check_dq_08,
            "DQ-09": self.check_dq_09,
            "DQ-10": self.check_dq_10,
            "DQ-11": self.check_dq_11,
            "DQ-12": self.check_dq_12,
            "DQ-13": self.check_dq_13,
            "DQ-14": self.check_dq_14,
        }

        if rule_id not in methods:
            raise ValueError(f"Unknown DQ rule: {rule_id}")

        return methods[rule_id](df)

    # =========================================================
    # RUN ALL 14 RULES
    # =========================================================

    def validate_all(
        self,
        df: pd.DataFrame,
        companies_df: pd.DataFrame | None = None,
    ) -> list[dict[str, Any]]:

        results = []

        for rule_id in self.RULE_SEVERITY:

            results.append(
                self.validate_rule(
                    rule_id,
                    df,
                    companies_df,
                )
            )

        return results

    # =========================================================
    # EXISTING BASIC VALIDATION
    # =========================================================

    def validate_dataframe(
        self,
        name,
        df,
    ):

        print("\n" + "=" * 70)
        print(name)
        print("=" * 70)

        print(f"Rows    : {len(df)}")
        print(f"Columns : {len(df.columns)}")

        missing = df.isnull().sum().sum()

        print(f"Missing Values : {missing}")

        duplicates = df.duplicated().sum()

        print(f"Duplicate Rows : {duplicates}")

        print("Validation Complete")

        return {
            "name": name,
            "rows": len(df),
            "columns": len(df.columns),
            "missing_values": int(missing),
            "duplicate_rows": int(duplicates),
        }
