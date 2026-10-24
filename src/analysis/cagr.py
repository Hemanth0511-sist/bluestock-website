class CAGR:

    @staticmethod
    def calculate(start_value, end_value, years):
        """
        Generic CAGR Formula

        Returns:
            (cagr_value, status)

        Status values:
            OK
            ZERO_BASE
            TURNAROUND
            DECLINE_TO_LOSS
            BOTH_NEGATIVE
            INSUFFICIENT_DATA
        """

        if start_value is None or end_value is None or years is None or years <= 0:
            return None, "INSUFFICIENT_DATA"

        # Zero Base
        if start_value == 0:
            return None, "ZERO_BASE"

        # Loss to Loss
        if start_value < 0 and end_value < 0:
            return None, "BOTH_NEGATIVE"

        # Loss to Profit
        if start_value < 0 and end_value > 0:
            return None, "TURNAROUND"

        # Profit to Loss
        if start_value > 0 and end_value < 0:
            return None, "DECLINE_TO_LOSS"

        cagr = ((end_value / start_value) ** (1 / years) - 1) * 100

        return round(cagr, 2), "OK"

    @staticmethod
    def revenue_cagr(start_sales, end_sales, years):
        return CAGR.calculate(start_sales, end_sales, years)

    @staticmethod
    def profit_cagr(start_profit, end_profit, years):
        return CAGR.calculate(start_profit, end_profit, years)

    @staticmethod
    def eps_cagr(start_eps, end_eps, years):
        return CAGR.calculate(start_eps, end_eps, years)
