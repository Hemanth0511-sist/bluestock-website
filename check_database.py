import sqlite3


connection = sqlite3.connect("database/n100.db")
cursor = connection.cursor()


print("\n" + "=" * 70)
print("FIND MISSING COMPANY RANKING")
print("=" * 70)


# Get all companies
cursor.execute("""
    SELECT id, company_name
    FROM companies
    ORDER BY company_name
""")

companies = cursor.fetchall()


# Get companies that received a ranking
cursor.execute("""
    SELECT company_id
    FROM company_rankings
""")

ranked_companies = {
    row[0]
    for row in cursor.fetchall()
}


print("\nTotal companies:", len(companies))
print("Total ranked:", len(ranked_companies))


# Find missing company
missing_companies = []

for company_id, company_name in companies:

    if company_id not in ranked_companies:
        missing_companies.append(
            (company_id, company_name)
        )


print("\nMissing ranking:")
print("-" * 70)

for company_id, company_name in missing_companies:

    print(
        f"Company ID   : {company_id}"
    )

    print(
        f"Company Name : {company_name}"
    )

    # Check P&L
    cursor.execute("""
        SELECT COUNT(*)
        FROM profitandloss
        WHERE company_id = ?
    """, (company_id,))

    pnl_count = cursor.fetchone()[0]

    print(
        f"P&L records  : {pnl_count}"
    )

    # Check Balance Sheet
    cursor.execute("""
        SELECT COUNT(*)
        FROM balancesheet
        WHERE company_id = ?
    """, (company_id,))

    bs_count = cursor.fetchone()[0]

    print(
        f"BS records   : {bs_count}"
    )

    print("-" * 70)


connection.close()