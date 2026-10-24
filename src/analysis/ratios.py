from src.analysis.metrics import FinancialMetrics
from src.database.database import Database


class RatioEngine:

    def __init__(self):
        self.db = Database()
        self.db.connect()
        self.metrics = FinancialMetrics()

    # ==========================================================
    # CALCULATE RATIOS FROM RECORDS
    # ==========================================================

    def calculate_from_records(self, company_id, latest, previous, bs, cf):
        """
        Calculate financial ratios using supplied records.

        Used for historical calculations and for companies
        where ratios must be calculated from financial statements.
        """

        if latest is None or previous is None:
            print(f"Insufficient Profit & Loss data for Company ID: " f"{company_id}")
            return None

        if bs is None:
            print(f"Missing Balance Sheet data for Company ID: " f"{company_id}")
            return None

        if cf is None:
            print(f"Missing Cash Flow data for Company ID: " f"{company_id}")
            return None

        # ======================================================
        # PROFIT & LOSS
        # ======================================================

        sales = latest[3]
        expenses = latest[4]
        operating_profit = latest[5]

        other_income = latest[7] if latest[7] is not None else 0

        interest = latest[8] if latest[8] is not None else 0

        net_profit = latest[12]
        previous_sales = previous[3]
        previous_profit = previous[12]

        if sales is None or previous_sales is None:
            print(f"Incomplete sales data for Company ID: " f"{company_id}")
            return None

        if net_profit is None or previous_profit is None:
            print(f"Incomplete profit data for Company ID: " f"{company_id}")
            return None

        # ------------------------------------------------------
        # PNB has missing operating_profit in the source data.
        #
        # Use Sales - Expenses as a fallback only when the
        # source operating_profit is missing.
        # ------------------------------------------------------

        if operating_profit is None:

            if expenses is not None:

                operating_profit = sales - expenses

            else:

                print(
                    f"Missing operating profit and expenses "
                    f"for Company ID: {company_id}"
                )
                return None

        # ======================================================
        # BALANCE SHEET
        # ======================================================

        equity = (bs[3] if bs[3] is not None else 0) + (
            bs[4] if bs[4] is not None else 0
        )

        borrowings = bs[5] if bs[5] is not None else 0

        investments = bs[10] if bs[10] is not None else 0

        total_assets = bs[12]

        if total_assets is None:
            print(f"Incomplete Balance Sheet data for Company ID: " f"{company_id}")
            return None

        capital_employed = equity + borrowings

        # ======================================================
        # CASH FLOW
        # ======================================================

        cfo = cf[3]
        investing = cf[4]

        if cfo is None:
            print(f"Missing CFO data for Company ID: " f"{company_id}")
            return None

        if investing is None:
            print(f"Missing investing cash flow for Company ID: " f"{company_id}")
            return None

        # ======================================================
        # DEBT / LEVERAGE
        # ======================================================

        if borrowings == 0:

            debt_equity = 0

        else:

            debt_equity = self.metrics.debt_to_equity(borrowings, equity)

        high_leverage_flag = debt_equity is not None and debt_equity > 5

        # ======================================================
        # INTEREST COVERAGE
        # ======================================================

        interest_coverage = self.metrics.interest_coverage(
            operating_profit + other_income, interest
        )

        if borrowings == 0:

            icr_label = "Debt Free"

        else:

            icr_label = ""

        icr_warning = interest_coverage is not None and interest_coverage < 1.5

        # ======================================================
        # FINAL RATIOS
        # ======================================================

        ratios = {
            "Revenue Growth": self.metrics.revenue_growth(sales, previous_sales),
            "Profit Growth": self.metrics.profit_growth(net_profit, previous_profit),
            "Net Profit Margin": self.metrics.net_profit_margin(net_profit, sales),
            "Operating Profit Margin": self.metrics.operating_profit_margin(
                operating_profit, sales
            ),
            "ROE": self.metrics.roe(net_profit, equity),
            "ROCE": self.metrics.roce(operating_profit, capital_employed),
            "Debt/Equity": debt_equity,
            "Interest Coverage": interest_coverage,
            "Asset Turnover": self.metrics.asset_turnover(sales, total_assets),
            "Net Debt": self.metrics.net_debt(borrowings, investments),
            "Free Cash Flow": self.metrics.free_cash_flow(cfo, investing),
            "CFO Quality": self.metrics.cfo_quality_score(cfo, net_profit),
            "CapEx Intensity": self.metrics.capex_intensity(investing, sales),
            "ICR Label": icr_label,
            "ICR Warning": icr_warning,
            "High Leverage": high_leverage_flag,
        }

        return ratios

    # ==========================================================
    # LATEST RATIOS
    # ==========================================================

    def calculate_ratios(self, company_id):

        pnl = self.db.get_profit_loss(company_id)

        bs = self.db.get_balance_sheet(company_id)

        cf = self.db.get_cashflow(company_id)

        if len(pnl) < 2:

            print(f"Insufficient P&L data for Company ID: " f"{company_id}")

            return None

        # get_profit_loss() should already return newest first.
        latest = pnl[0]
        previous = pnl[1]

        return self.calculate_from_records(company_id, latest, previous, bs, cf)

    # ==========================================================
    # CLOSE
    # ==========================================================

    def close(self):

        self.db.close()
