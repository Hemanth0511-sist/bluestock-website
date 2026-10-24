from src.database.database import Database


class Watchlist:

    def __init__(self):
        self.db = Database()
        self.db.connect()
        self.db.create_watchlist_table()

    def add_company(self, company_id):

        company = self.db.get_company(company_id)

        if company is None:
            print("Company not found.")
            return

        try:
            query = """
            INSERT INTO watchlist(company_id)
            VALUES(?)
            """

            self.db.execute_non_query(query, (company_id,))

            print(f"{company[1]} added to Watchlist.")

        except Exception:
            print("Company already exists in Watchlist.")

    def view_watchlist(self):

        query = """
        SELECT w.company_id, c.company_name
        FROM watchlist w
        JOIN companies c
        ON w.company_id = c.id
        ORDER BY c.company_name
        """

        companies = self.db.execute_query(query)

        print("\n" + "=" * 60)
        print("WATCHLIST")
        print("=" * 60)

        if not companies:
            print("Watchlist is empty.")
        else:
            for company in companies:
                print(f"{company[0]:<10} {company[1]}")

        print("=" * 60)

    def remove_company(self, company_id):

        query = """
        DELETE FROM watchlist
        WHERE company_id = ?
        """

        self.db.execute_non_query(query, (company_id,))

        print("Company removed from Watchlist.")

    def close(self):
        self.db.close()
