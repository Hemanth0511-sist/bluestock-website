import sqlite3
import pandas as pd

conn = sqlite3.connect("database/n100.db")

companies = pd.read_sql_query(
    "SELECT id FROM companies ORDER BY id",
    conn
)

cashflow = pd.read_sql_query(
    "SELECT DISTINCT company_id FROM cashflow",
    conn
)

companies["id"] = (
    companies["id"]
    .astype(str)
    .str.strip()
    .str.upper()
)

cashflow["company_id"] = (
    cashflow["company_id"]
    .astype(str)
    .str.strip()
    .str.upper()
)

missing = companies[
    ~companies["id"].isin(cashflow["company_id"])
]

print("=" * 70)
print("DAY 32 - MISSING COMPANY CHECK")
print("=" * 70)

print("\nCompanies in master table :", len(companies))
print("Companies with cashflow   :", cashflow["company_id"].nunique())
print("Missing companies         :", len(missing))

print("\nMISSING TICKERS:")
print(missing.to_string(index=False))

conn.close()

print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)