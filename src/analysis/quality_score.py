class QualityScore:

    @staticmethod
    def calculate(ratios):
        """
        Calculate a Composite Quality Score (0-100)
        """

        score = 0

        # -----------------------
        # Profitability (40 Marks)
        # -----------------------

        roe = ratios.get("ROE")
        if roe is not None:
            if roe >= 20:
                score += 15
            elif roe >= 15:
                score += 10
            elif roe >= 10:
                score += 5

        roce = ratios.get("ROCE")
        if roce is not None:
            if roce >= 20:
                score += 15
            elif roce >= 15:
                score += 10
            elif roce >= 10:
                score += 5

        npm = ratios.get("Net Profit Margin")
        if npm is not None:
            if npm >= 20:
                score += 10
            elif npm >= 10:
                score += 5

        # -----------------------
        # Growth (20 Marks)
        # -----------------------

        rev_growth = ratios.get("Revenue Growth")
        if rev_growth is not None:
            if rev_growth >= 15:
                score += 10
            elif rev_growth >= 8:
                score += 5

        profit_growth = ratios.get("Profit Growth")
        if profit_growth is not None:
            if profit_growth >= 15:
                score += 10
            elif profit_growth >= 8:
                score += 5

        # -----------------------
        # Financial Health (25 Marks)
        # -----------------------

        debt = ratios.get("Debt/Equity")
        if debt is not None:
            if debt <= 0.5:
                score += 10
            elif debt <= 1:
                score += 5

        icr = ratios.get("Interest Coverage")
        if icr is not None:
            if icr >= 5:
                score += 10
            elif icr >= 2:
                score += 5

        cfo_quality = ratios.get("CFO Quality")
        if cfo_quality is not None:
            if cfo_quality >= 1:
                score += 5

        # -----------------------
        # Penalty
        # -----------------------

        if ratios.get("High Leverage"):
            score -= 10

        # Keep score in range 0–100
        score = max(0, min(score, 100))

        return score
