class FinancialMetrics:

    @staticmethod
    def safe_divide(numerator, denominator):
        """
        Safely divide two numbers.
        Returns None if values are invalid or denominator is zero.
        """
        if numerator is None or denominator is None:
            return None

        if denominator == 0:
            return None

        return numerator / denominator

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
        result = FinancialMetrics.safe_divide(total_debt, equity)
        return None if result is None else round(result, 2)

    @staticmethod
    def roe(net_profit, equity):
        result = FinancialMetrics.safe_divide(net_profit, equity)
        return None if result is None else round(result * 100, 2)

    @staticmethod
    def roce(ebit, capital_employed):
        result = FinancialMetrics.safe_divide(ebit, capital_employed)
        return None if result is None else round(result * 100, 2)

    @staticmethod
    def return_on_assets(net_profit, total_assets):
        result = FinancialMetrics.safe_divide(net_profit, total_assets)
        return None if result is None else round(result * 100, 2)

    @staticmethod
    def asset_turnover(revenue, total_assets):
        result = FinancialMetrics.safe_divide(revenue, total_assets)
        return None if result is None else round(result, 2)

    @staticmethod
    def net_profit_margin(net_profit, revenue):
        result = FinancialMetrics.safe_divide(net_profit, revenue)
        return None if result is None else round(result * 100, 2)

    @staticmethod
    def operating_profit_margin(operating_profit, revenue):
        result = FinancialMetrics.safe_divide(operating_profit, revenue)
        return None if result is None else round(result * 100, 2)

    @staticmethod
    def interest_coverage(ebit, interest_expense):
        result = FinancialMetrics.safe_divide(ebit, interest_expense)
        return None if result is None else round(result, 2)

    @staticmethod
    def current_ratio(current_assets, current_liabilities):
        result = FinancialMetrics.safe_divide(current_assets, current_liabilities)
        return None if result is None else round(result, 2)

    @staticmethod
    def debt_ratio(total_debt, total_assets):
        result = FinancialMetrics.safe_divide(total_debt, total_assets)
        return None if result is None else round(result, 2)

    @staticmethod
    def net_debt(total_debt, cash):
        if total_debt is None:
            return None

        if cash is None:
            cash = 0

        return round(total_debt - cash, 2)

    @staticmethod
    def free_cash_flow(cfo, capex):
        if cfo is None or capex is None:
            return None

        return round(cfo + capex, 2)

    @staticmethod
    def cfo_quality_score(cfo, net_profit):
        result = FinancialMetrics.safe_divide(cfo, net_profit)
        return None if result is None else round(result, 2)

    @staticmethod
    def cfo_quality(cfo, net_profit):
        return FinancialMetrics.cfo_quality_score(cfo, net_profit)

    @staticmethod
    def capex_intensity(capex, revenue):
        if capex is None or revenue in (0, None):
            return None

        result = FinancialMetrics.safe_divide(abs(capex), revenue)
        return None if result is None else round(result * 100, 2)

    @staticmethod
    def fcf_conversion(fcf, operating_profit):
        result = FinancialMetrics.safe_divide(fcf, operating_profit)
        return None if result is None else round(result * 100, 2)

    @staticmethod
    def dividend_payout(dividend, net_profit):
        result = FinancialMetrics.safe_divide(dividend, net_profit)
        return None if result is None else round(result * 100, 2)

    @staticmethod
    def earnings_per_share(net_profit, shares_outstanding):
        result = FinancialMetrics.safe_divide(net_profit, shares_outstanding)
        return None if result is None else round(result, 2)

    @staticmethod
    def book_value_per_share(equity, shares):
        result = FinancialMetrics.safe_divide(equity, shares)
        return None if result is None else round(result, 2)

    @staticmethod
    def price_to_book(price, book_value):
        result = FinancialMetrics.safe_divide(price, book_value)
        return None if result is None else round(result, 2)

    @staticmethod
    def price_to_earnings(price, eps):
        result = FinancialMetrics.safe_divide(price, eps)
        return None if result is None else round(result, 2)
