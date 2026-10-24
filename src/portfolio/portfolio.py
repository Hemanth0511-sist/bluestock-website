from src.database.database import Database


class Portfolio:

    def __init__(self):
        self.db = Database()
        self.db.connect()
        self.db.create_portfolio_table()

    def add_stock(self, company_id, quantity, buy_price):
        query = """
        INSERT INTO portfolio(company_id, quantity, buy_price)
        VALUES (?, ?, ?);
        """
        self.db.execute_non_query(query, (company_id, quantity, buy_price))
        print("Stock added to Portfolio.")

    def view_portfolio(self):
        query = """
        SELECT * FROM portfolio;
        """
        portfolio = self.db.execute_query(query)

        print("\n==============================")
        print("PORTFOLIO")
        print("==============================")

        if not portfolio:
            print("Portfolio is empty.")
            return

        for stock in portfolio:
            print(stock)

    def remove_stock(self, portfolio_id):
        query = """
        DELETE FROM portfolio
        WHERE id = ?;
        """
        self.db.execute_non_query(query, (portfolio_id,))
        print("Stock removed.")

    def close(self):
        self.db.close()
