from src.database.database import Database


class PortfolioBacktest:

    def __init__(self):

        self.db = Database()
        self.db.connect()

    def load_stock_prices(self):

        query = """
        SELECT

            company_id,
            date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume

        FROM stock_prices

        ORDER BY
            company_id,
            date;
        """

        rows = self.db.execute_query(query)

        return rows

    def get_company_history(self, company_id):

        query = """
        SELECT

            date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume

        FROM stock_prices

        WHERE company_id = ?

        ORDER BY date;
        """

        rows = self.db.execute_query(query, (company_id,))

        return rows

    def buy_and_hold(self, company_id, investment):

        history = self.get_company_history(company_id)

        if len(history) == 0:
            return None

        first = history[0]
        last = history[-1]

        buy_date = first[0]
        buy_price = first[4]

        sell_date = last[0]
        sell_price = last[4]

        shares = investment / buy_price

        final_value = shares * sell_price

        profit = final_value - investment

        return_pct = (profit / investment) * 100

        months = len(history) - 1

        years = months / 12

        cagr = self.calculate_cagr(investment, final_value, years)

        return {
            "company": company_id,
            "buy_date": buy_date,
            "sell_date": sell_date,
            "buy_price": round(buy_price, 2),
            "sell_price": round(sell_price, 2),
            "shares": round(shares, 4),
            "investment": round(investment, 2),
            "final_value": round(final_value, 2),
            "profit": round(profit, 2),
            "return_pct": round(return_pct, 2),
            "cagr": cagr,
        }

    def portfolio_backtest(self, companies, investment):

        per_stock = investment / len(companies)

        results = []

        total_final = 0

        for company in companies:

            result = self.buy_and_hold(company, per_stock)

            if result is None:
                continue

            results.append(result)

            total_final += result["final_value"]

        total_profit = total_final - investment

        total_return = (total_profit / investment) * 100

        avg_cagr = sum(r["cagr"] for r in results) / len(results)

        return {
            "results": results,
            "investment": investment,
            "final_value": round(total_final, 2),
            "profit": round(total_profit, 2),
            "return_pct": round(total_return, 2),
            "cagr": round(avg_cagr, 2),
        }

    def calculate_cagr(self, investment, final_value, years):

        if investment <= 0 or years <= 0:
            return 0

        cagr = ((final_value / investment) ** (1 / years) - 1) * 100

        return round(cagr, 2)

    def close(self):

        self.db.close()
