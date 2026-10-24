from src.analysis.metrics import FinancialMetrics


class HealthScore:

    def __init__(self):
        self.metrics = FinancialMetrics()

    def calculate_score(self, revenue_growth, profit_growth, debt_equity, roe, roce):

        score = 0

        # Revenue Growth (20 Marks)
        if revenue_growth is not None:
            if revenue_growth >= 15:
                score += 20
            elif revenue_growth >= 10:
                score += 15
            elif revenue_growth >= 5:
                score += 10
            else:
                score += 5

        # Profit Growth (20 Marks)
        if profit_growth is not None:
            if profit_growth >= 15:
                score += 20
            elif profit_growth >= 10:
                score += 15
            elif profit_growth >= 5:
                score += 10
            else:
                score += 5

        # Debt to Equity (20 Marks)
        if debt_equity is not None:
            if debt_equity <= 0.5:
                score += 20
            elif debt_equity <= 1:
                score += 15
            elif debt_equity <= 2:
                score += 10
            else:
                score += 5

        # ROE (20 Marks)
        if roe is not None:
            if roe >= 20:
                score += 20
            elif roe >= 15:
                score += 15
            elif roe >= 10:
                score += 10
            else:
                score += 5

        # ROCE (20 Marks)
        if roce is not None:
            if roce >= 20:
                score += 20
            elif roce >= 15:
                score += 15
            elif roce >= 10:
                score += 10
            else:
                score += 5

        return score

    def get_rating(self, score):

        if score >= 90:
            return "★★★★★ Excellent"

        elif score >= 75:
            return "★★★★☆ Very Good"

        elif score >= 60:
            return "★★★☆☆ Good"

        elif score >= 40:
            return "★★☆☆☆ Average"

        else:
            return "★☆☆☆☆ Poor"
