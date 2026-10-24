import sys
from pathlib import Path

# ==========================================================
# PROJECT ROOT
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ==========================================================
# IMPORT SCREENER ENGINE
# ==========================================================

from src.screener.engine import ScreenerEngine

# ==========================================================
# DAY 16 PRESETS
# ==========================================================

PRESETS = [
    "quality_compounder",
    "value_pick",
    "growth_accelerator",
    "dividend_champion",
    "debt_free_bluechip",
    "turnaround_watch",
]


# ==========================================================
# EXPECTED VALIDATION RANGE
# ==========================================================

MIN_COMPANIES = 5
MAX_COMPANIES = 50


# ==========================================================
# MAIN TEST
# ==========================================================


def main():

    screener = ScreenerEngine()

    try:

        print("=" * 70)
        print("DAY 16 - PRESET SCREENER VALIDATION")
        print("=" * 70)

        # --------------------------------------------------
        # Load complete financial universe
        # --------------------------------------------------

        data = screener.load_financial_data()

        universe = len(data)

        print(f"FULL UNIVERSE: {universe} companies")
        print()

        # --------------------------------------------------
        # Validate universe
        # --------------------------------------------------

        if universe == 92:

            print("UNIVERSE CHECK: PASS - 92 companies")

        else:

            print(f"UNIVERSE CHECK: WARN - " f"expected 92, found {universe}")

        print()

        # --------------------------------------------------
        # Test all six presets
        # --------------------------------------------------

        results = []

        print("=" * 70)
        print("PRESET RESULTS")
        print("=" * 70)

        for preset in PRESETS:

            try:

                result = screener.filter_data(preset)

                count = len(result)

                # ------------------------------------------
                # Validate result count
                # ------------------------------------------

                if count == 0:
                    status = "ERROR"

                elif count > MAX_COMPANIES:
                    status = "WARN"

                elif count < MIN_COMPANIES:
                    status = "INFO"

                else:
                    status = "PASS"

                results.append(
                    {
                        "preset": preset,
                        "count": count,
                        "status": status,
                    }
                )

                print(f"{preset:<25} " f"{count:>3} companies   " f"{status}")

            except Exception as exc:

                results.append(
                    {
                        "preset": preset,
                        "count": 0,
                        "status": "ERROR",
                    }
                )

                print(f"{preset:<25} " f"ERROR")

                print(f"    {type(exc).__name__}: {exc}")

        # --------------------------------------------------
        # Detailed summary
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)

        for item in results:

            print(
                f"{item['status']:<6} " f"{item['preset']:<25} " f"{item['count']:>3}"
            )

        # --------------------------------------------------
        # Business sense checks
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("BUSINESS-SENSE VALIDATION")
        print("=" * 70)

        for item in results:

            preset = item["preset"]
            count = item["count"]

            # ----------------------------------------------
            # Quality Compounder
            # ----------------------------------------------

            if preset == "quality_compounder":

                print(
                    f"{preset:<25}: "
                    f"{count} results - "
                    f"quality/growth criteria applied"
                )

            # ----------------------------------------------
            # Value Pick
            # ----------------------------------------------

            elif preset == "value_pick":

                if count < MIN_COMPANIES:

                    print(
                        f"{preset:<25}: "
                        f"{count} results - "
                        f"STRICT VALUE CRITERIA PRODUCE FEW RESULTS"
                    )

                else:

                    print(
                        f"{preset:<25}: "
                        f"{count} results - "
                        f"value criteria look reasonable"
                    )

            # ----------------------------------------------
            # Growth Accelerator
            # ----------------------------------------------

            elif preset == "growth_accelerator":

                print(
                    f"{preset:<25}: " f"{count} results - " f"growth criteria applied"
                )

            # ----------------------------------------------
            # Dividend Champion
            # ----------------------------------------------

            elif preset == "dividend_champion":

                if count < MIN_COMPANIES:

                    print(
                        f"{preset:<25}: "
                        f"{count} results - "
                        f"CHECK DIVIDEND PAYOUT DATA COMPLETENESS"
                    )

                else:

                    print(
                        f"{preset:<25}: "
                        f"{count} results - "
                        f"dividend criteria look reasonable"
                    )

            # ----------------------------------------------
            # Debt-Free Blue Chip
            # ----------------------------------------------

            elif preset == "debt_free_bluechip":

                print(
                    f"{preset:<25}: "
                    f"{count} results - "
                    f"debt-free + quality + scale criteria applied"
                )

            # ----------------------------------------------
            # Turnaround Watch
            # ----------------------------------------------

            elif preset == "turnaround_watch":

                print(
                    f"{preset:<25}: "
                    f"{count} results - "
                    f"growth + positive FCF + declining D/E"
                )

        # --------------------------------------------------
        # Final Day 16 status
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("DAY 16 FINAL STATUS")
        print("=" * 70)

        pass_count = sum(1 for item in results if item["status"] == "PASS")

        warn_count = sum(1 for item in results if item["status"] == "WARN")

        error_count = sum(1 for item in results if item["status"] == "ERROR")

        print(f"PASS  : {pass_count}")
        print(f"WARN  : {warn_count}")
        print(f"ERROR : {error_count}")

        print()

        if error_count == 0:

            print("DAY 16 ENGINE TEST: COMPLETE")

        else:

            print("DAY 16 ENGINE TEST: FAILED")

        print()
        print("=" * 70)
        print("VALIDATION RULE")
        print("=" * 70)

        print("PASS = 5 to 50 companies")

        print("WARN = fewer than 5 or more than 50 companies")

        print("ERROR = preset execution failed")

        print("=" * 70)

    finally:

        screener.close()


# ==========================================================
# SCRIPT ENTRY POINT
# ==========================================================

if __name__ == "__main__":
    main()
