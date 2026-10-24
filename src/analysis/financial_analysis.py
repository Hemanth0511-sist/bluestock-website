class FinancialMetrics:

    @staticmethod
    def revenue_growth(current, previous):
        if previous in (0, None):
            return None
        return round(((current - previous) / previous) * 100, 2)

    @staticmethod
    def profit_growth(current, previous):
        if previous in (0, None):
            return None
        return round(((current - previous) / previous) * 100, 2)

    @staticmethod
    def debt_to_equity(total_debt, equity):
        if equity is None or abs(equity) < 1:
            return None
        return round(total_debt / equity, 2)

    @staticmethod
    def roe(net_profit, equity):
        if equity is None or abs(equity) < 1:
            return None

        value = (net_profit / equity) * 100

        # Limit unrealistic values
        value = max(min(value, 100), -100)

        return round(value, 2)

    @staticmethod
    def roce(ebit, capital_employed):
        if capital_employed is None or abs(capital_employed) < 1:
            return None

        value = (ebit / capital_employed) * 100

        # Limit unrealistic values
        value = max(min(value, 100), -100)

        return round(value, 2)

    @staticmethod
    def asset_turnover(revenue, total_assets):
        if total_assets in (0, None):
            return None
        return round(revenue / total_assets, 2)

    @staticmethod
    def net_profit_margin(net_profit, revenue):
        if revenue in (0, None):
            return None
        return round((net_profit / revenue) * 100, 2)

    @staticmethod
    def operating_profit_margin(operating_profit, revenue):
        if revenue in (0, None):
            return None
        return round((operating_profit / revenue) * 100, 2)

    @staticmethod
    def current_ratio(current_assets, current_liabilities):
        if current_liabilities in (0, None):
            return None
        return round(current_assets / current_liabilities, 2)

    @staticmethod
    def debt_ratio(total_debt, total_assets):
        if total_assets in (0, None):
            return None
        return round(total_debt / total_assets, 2)

    @staticmethod
    def interest_coverage(ebit, interest):
        if interest in (0, None):
            return None
        return round(ebit / interest, 2)

    @staticmethod
    def net_debt(borrowings, investments):
        if borrowings is None:
            return None

        if investments is None:
            investments = 0

        return round(borrowings - investments, 2)

    @staticmethod
    def free_cash_flow(cfo, investing_cashflow):
        if cfo is None or investing_cashflow is None:
            return None

        return round(cfo + investing_cashflow, 2)

    @staticmethod
    def cfo_quality_score(cfo, net_profit):
        if net_profit in (0, None):
            return None

        return round(cfo / net_profit, 2)

    @staticmethod
    def capex_intensity(investing_cashflow, revenue):
        if revenue in (0, None):
            return None

        return round((abs(investing_cashflow) / revenue) * 100, 2)

    @staticmethod
    def fcf_conversion(free_cash_flow, operating_profit):
        if operating_profit in (0, None):
            return None

        return round((free_cash_flow / operating_profit) * 100, 2)

    @staticmethod
    def earnings_per_share(net_profit, shares_outstanding):
        if shares_outstanding in (0, None):
            return None

        return round(net_profit / shares_outstanding, 2)

    @staticmethod
    def price_to_book(price, book_value):
        if book_value in (0, None):
            return None

        return round(price / book_value, 2)

    @staticmethod
    def price_to_earnings(price, eps):
        if eps in (0, None):
            return None

        return round(price / eps, 2)
