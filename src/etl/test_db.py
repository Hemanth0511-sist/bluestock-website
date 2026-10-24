from src.database.database import Database

db = Database()
db.connect()

print(db.execute_query("PRAGMA table_info(stock_prices);"))

db.close()
