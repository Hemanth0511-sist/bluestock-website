class ScoreCalculator:

    def quality_score(self, roe, roce, npm, opm):
        score = 0

        if roe >= 20:
            score += 25
        elif roe >= 15:
            score += 20
        elif roe >= 10:
            score += 15

        if roce >= 20:
            score += 25
        elif roce >= 15:
            score += 20
        elif roce >= 10:
            score += 15

        if npm >= 15:
            score += 25
        elif npm >= 10:
            score += 20
        elif npm >= 5:
            score += 15

        if opm >= 20:
            score += 25
        elif opm >= 15:
            score += 20
        elif opm >= 10:
            score += 15

        return min(score, 100)

    def growth_score(self, revenue_growth, profit_growth):
        score = 0

        if revenue_growth >= 20:
            score += 50
        elif revenue_growth >= 10:
            score += 40
        elif revenue_growth >= 5:
            score += 30

        if profit_growth >= 20:
            score += 50
        elif profit_growth >= 10:
            score += 40
        elif profit_growth >= 5:
            score += 30

        return min(score, 100)

    def value_score(self, debt_equity, market_cap):

        score = 0

        if debt_equity <= 0.5:
            score += 50
        elif debt_equity <= 1:
            score += 40
        elif debt_equity <= 2:
            score += 30

        if market_cap >= 100000:
            score += 50
        elif market_cap >= 50000:
            score += 40
        else:
            score += 30

        return min(score, 100)

    def risk_score(self, debt_equity, interest_coverage, cfo_quality):

        score = 100

        if debt_equity > 2:
            score -= 30
        elif debt_equity > 1:
            score -= 15

        if interest_coverage < 2:
            score -= 30
        elif interest_coverage < 5:
            score -= 15

        if cfo_quality < 1:
            score -= 20

        return max(score, 0)

    def final_score(self, quality, growth, value, risk):

        score = quality * 0.35 + growth * 0.30 + value * 0.20 + risk * 0.15

        return round(score, 2)

    def recommendation(self, score):

        if score >= 85:
            return "Strong Buy"

        if score >= 70:
            return "Buy"

        if score >= 55:
            return "Hold"

        if score >= 40:
            return "Reduce"

        return "Sell"
