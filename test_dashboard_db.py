from src.dashboard.utils.db import (
    get_companies,
    get_ratios,
    get_pl,
    get_bs,
    get_cf,
    get_sectors,
    get_peers,
    get_market_cap,
    get_rankings,
)

import sqlite3


print("\n" + "=" * 60)
print("N100 DASHBOARD DATABASE TEST")
print("=" * 60)


# ------------------------------------------------------------
# 1. COMPANIES
# ------------------------------------------------------------

print("\n1. COMPANIES")
print("-" * 40)

companies = get_companies()

print("Rows:", len(companies))
print("Columns:", len(companies.columns))

if not companies.empty:
    print(companies.head())


# ------------------------------------------------------------
# 2. FINANCIAL RATIOS
# ------------------------------------------------------------

print("\n2. FINANCIAL RATIOS")
print("-" * 40)

ratios = get_ratios("ABB")

print("Rows:", len(ratios))
print("Columns:", len(ratios.columns))

if not ratios.empty:
    print(ratios.head())


# ------------------------------------------------------------
# 3. PROFIT & LOSS
# ------------------------------------------------------------

print("\n3. PROFIT & LOSS")
print("-" * 40)

pl = get_pl("ABB")

print("Rows:", len(pl))
print("Columns:", len(pl.columns))

if not pl.empty:
    print(pl.head())


# ------------------------------------------------------------
# 4. BALANCE SHEET
# ------------------------------------------------------------

print("\n4. BALANCE SHEET")
print("-" * 40)

bs = get_bs("ABB")

print("Rows:", len(bs))
print("Columns:", len(bs.columns))

if not bs.empty:
    print(bs.head())


# ------------------------------------------------------------
# 5. CASH FLOW
# ------------------------------------------------------------

print("\n5. CASH FLOW")
print("-" * 40)

cf = get_cf("ABB")

print("Rows:", len(cf))
print("Columns:", len(cf.columns))

if not cf.empty:
    print(cf.head())


# ------------------------------------------------------------
# 6. SECTORS
# ------------------------------------------------------------

print("\n6. SECTORS")
print("-" * 40)

sectors = get_sectors()

print("Rows:", len(sectors))
print("Columns:", len(sectors.columns))

if not sectors.empty:
    print(sectors.head())


# ------------------------------------------------------------
# 7. MARKET CAP
# ------------------------------------------------------------

print("\n7. MARKET CAP")
print("-" * 40)

market_cap = get_market_cap()

print("Rows:", len(market_cap))
print("Columns:", len(market_cap.columns))

if not market_cap.empty:
    print(market_cap.head())


# ------------------------------------------------------------
# 8. COMPANY RANKINGS
# ------------------------------------------------------------

print("\n8. COMPANY RANKINGS")
print("-" * 40)

rankings = get_rankings()

print("Rows:", len(rankings))
print("Columns:", len(rankings.columns))

if not rankings.empty:
    print(rankings.head())


# ------------------------------------------------------------
# 9. PEER GROUPS
# ------------------------------------------------------------

print("\n9. PEER GROUPS")
print("-" * 40)

connection = sqlite3.connect("database/n100.db")

cursor = connection.cursor()

cursor.execute(
    "SELECT DISTINCT peer_group_name "
    "FROM peer_groups "
    "WHERE peer_group_name IS NOT NULL "
    "LIMIT 1"
)

peer_group = cursor.fetchone()

connection.close()


if peer_group:

    group_name = peer_group[0]

    print("Testing peer group:", group_name)

    peers = get_peers(group_name)

    print("Rows:", len(peers))
    print("Columns:", len(peers.columns))

    if not peers.empty:
        print(peers.head())

else:

    print("No peer group found in database.")


# ------------------------------------------------------------
# FINAL RESULT
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("DATABASE TEST COMPLETE")
print("=" * 60)

print("\nAll requested database functions were executed.")
print("If there are no red errors above, the database layer is working.")