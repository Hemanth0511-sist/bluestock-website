from src.database.database import Database
from src.analysis.ratios import RatioEngine


def main():

    db = Database()
    db.connect()

    engine = RatioEngine()

    for company_id in ["PNB", "SBIN"]:

        print("\n" + "=" * 70)
        print(f"CHECKING COMPANY: {company_id}")
        print("=" * 70)

        pnl = db.get_all_profit_loss(company_id)
        bs = db.get_all_balance_sheet(company_id)
        cf = db.get_all_cashflow(company_id)

        print(f"P&L records       : {len(pnl)}")
        print(f"Balance Sheet     : {len(bs)}")
        print(f"Cash Flow         : {len(cf)}")

        if pnl:
            print("\nP&L years:")
            print([row[2] for row in pnl])

            print("\nLATEST P&L:")
            print(pnl[0])

            if len(pnl) > 1:
                print("\nPREVIOUS P&L:")
                print(pnl[1])

        if bs:
            print("\nBalance Sheet years:")
            print([row[2] for row in bs])

            print("\nLATEST BALANCE SHEET:")
            print(bs[0])

        if cf:
            print("\nCash Flow years:")
            print([row[2] for row in cf])

            print("\nLATEST CASH FLOW:")
            print(cf[0])

        if len(pnl) >= 2 and bs and cf:

            current = pnl[0]
            previous = pnl[1]

            current_year = current[2]

            bs_map = {row[2]: row for row in bs}
            cf_map = {row[2]: row for row in cf}

            print("\nLATEST YEAR:")
            print(current_year)

            print("\nBALANCE SHEET MATCH:")
            print(current_year in bs_map)

            print("\nCASH FLOW MATCH:")
            print(current_year in cf_map)

            if current_year in bs_map and current_year in cf_map:

                print("\nCALCULATING RATIOS...")

                try:

                    ratios = engine.calculate_from_records(
                        company_id,
                        current,
                        previous,
                        bs_map[current_year],
                        cf_map[current_year]
                    )

                    print("\nRATIO RESULT:")
                    print(ratios)

                    if ratios is None:
                        print("\n*** RESULT IS NONE ***")
                        print("*** THIS IS WHY THE COMPANY IS NOT SAVED ***")

                except Exception as e:

                    print("\n*** RATIO CALCULATION ERROR ***")
                    print(type(e).__name__)
                    print(str(e))

        print("\n" + "=" * 70)

    engine.close()
    db.close()


if __name__ == "__main__":
    main()