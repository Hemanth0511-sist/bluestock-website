from src.database.database import Database


class Queries:

    def __init__(self):
        self.db = Database()
        self.db.connect()

    def get_all_companies(self):
        query = """
        SELECT *
        FROM companies;
        """
        return self.db.execute_query(query)

    def get_company(self, company_id):
        query = """
        SELECT *
        FROM companies
        WHERE id = ?;
        """
        return self.db.execute_one(query, (company_id,))

    def get_balance_sheet(self, company_id):
        query = """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY year DESC;
        """
        return self.db.execute_query(query, (company_id,))

    def get_profit_loss(self, company_id):
        query = """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year DESC;
        """
        return self.db.execute_query(query, (company_id,))

    def get_cash_flow(self, company_id):
        query = """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year DESC;
        """
        return self.db.execute_query(query, (company_id,))

    def get_stock_prices(self, company_id):
        query = """
        SELECT *
        FROM stock_prices
        WHERE company_id = ?
        ORDER BY date DESC;
        """
        return self.db.execute_query(query, (company_id,))

    def close(self):
        self.db.close()
