from src.database.database import Database


class PortfolioAnalytics:

    def __init__(self):
        self.db = Database()
        self.db.connect()

    def get_portfolio(self):

        query = """
        SELECT
            p.company_id,
            c.company_name,
            p.quantity,
            p.buy_price,
            sp.close_price
        FROM portfolio p

        JOIN companies c
            ON p.company_id = c.id

        JOIN stock_prices sp
            ON p.company_id = sp.company_id

        WHERE sp.date = (
            SELECT MAX(date)
            FROM stock_prices
            WHERE company_id = p.company_id
        );
        """

        return self.db.execute_query(query)

    def portfolio_summary(self):

        portfolio = self.get_portfolio()

        print("\n========== PORTFOLIO SUMMARY ==========\n")

        total_investment = 0
        total_current_value = 0

        for stock in portfolio:

            company_id = stock[0]
            company_name = stock[1]
            quantity = stock[2]
            buy_price = stock[3]
            current_price = stock[4]

            investment = quantity * buy_price
            current_value = quantity * current_price
            profit = current_value - investment

            total_investment += investment
            total_current_value += current_value

            print(f"Company       : {company_name}")
            print(f"Symbol        : {company_id}")
            print(f"Quantity      : {quantity}")
            print(f"Buy Price     : ₹{buy_price:.2f}")
            print(f"Current Price : ₹{current_price:.2f}")
            print(f"Investment    : ₹{investment:.2f}")
            print(f"Current Value : ₹{current_value:.2f}")
            print(f"Profit/Loss   : ₹{profit:.2f}")
            print("-" * 45)

        total_profit = total_current_value - total_investment

        print("\n========== OVERALL PORTFOLIO ==========")
        print(f"Total Investment : ₹{total_investment:.2f}")
        print(f"Current Value    : ₹{total_current_value:.2f}")
        print(f"Total Profit     : ₹{total_profit:.2f}")

    def portfolio_allocation(self):

        portfolio = self.get_portfolio()

        print("\n========== PORTFOLIO ALLOCATION ==========\n")

        total_value = 0

        for stock in portfolio:
            total_value += stock[2] * stock[4]

        for stock in portfolio:

            company = stock[1]
            value = stock[2] * stock[4]

            allocation = (value / total_value) * 100

            print(f"{company:<30} {allocation:.2f}%")

    def top_gainer(self):

        portfolio = self.get_portfolio()

        if not portfolio:
            print("Portfolio Empty.")
            return

        best_stock = None
        best_profit = float("-inf")

        for stock in portfolio:

            quantity = stock[2]
            buy_price = stock[3]
            current_price = stock[4]

            profit = quantity * (current_price - buy_price)

            if profit > best_profit:
                best_profit = profit
                best_stock = stock

        print("\n========== TOP GAINER ==========")
        print(f"Company : {best_stock[1]}")
        print(f"Profit  : ₹{best_profit:.2f}")

    def top_loser(self):

        portfolio = self.get_portfolio()

        if not portfolio:
            print("Portfolio Empty.")
            return

        worst_stock = None
        worst_profit = float("inf")

        for stock in portfolio:

            quantity = stock[2]
            buy_price = stock[3]
            current_price = stock[4]

            profit = quantity * (current_price - buy_price)

            if profit < worst_profit:
                worst_profit = profit
                worst_stock = stock

        print("\n========== TOP LOSER ==========")
        print(f"Company : {worst_stock[1]}")
        print(f"Loss    : ₹{worst_profit:.2f}")

    def close(self):
        self.db.close()
