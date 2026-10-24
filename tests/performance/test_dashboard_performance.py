import re
import time
from pathlib import Path

from streamlit.testing.v1 import AppTest

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

COMPANY_PROFILE_PAGE = PROJECT_ROOT / "src" / "dashboard" / "pages" / "02_profile.py"

TEST_TICKERS = [
    "TCS",
    "INFY",
    "HCLTECH",
    "BEL",
    "HAL",
]

MAX_LOAD_TIME = 3.0


# ============================================================
# FIND COMPANY SELECTOR
# ============================================================


def _find_company_selector(app):
    """
    Find the company selector on the Company Profile page.

    The current page uses:

        st.selectbox("Select company", labels)
    """

    for selector in app.selectbox:

        label = (
            str(
                getattr(
                    selector,
                    "label",
                    "",
                )
            )
            .strip()
            .lower()
        )

        if "select company" in label or "company" in label or "ticker" in label:
            return selector

    return None


# ============================================================
# FIND TICKER OPTION
# ============================================================


def _find_ticker_option(options, ticker):
    """
    Find the complete selectbox option containing the ticker.

    Example:

        ticker = "TCS"

        option =
            "Tata Consultancy Services Ltd (TCS)"

    The Streamlit selectbox value must be the complete option,
    not just "TCS".
    """

    ticker = str(ticker).strip().upper()

    # Exact ticker token inside parentheses.
    ticker_pattern = re.compile(
        rf"\(\s*{re.escape(ticker)}\s*\)",
        re.IGNORECASE,
    )

    for option in options:

        option_text = str(option).strip()

        if ticker_pattern.search(option_text):
            return option

    # --------------------------------------------------------
    # Fallback:
    # Some labels may not use parentheses.
    # --------------------------------------------------------

    for option in options:

        option_text = str(option).strip().upper()

        if (
            option_text == ticker
            or option_text.endswith(f"({ticker})")
            or f"({ticker})" in option_text
        ):
            return option

    return None


# ============================================================
# STREAMLIT ERROR CHECK
# ============================================================


def _assert_no_streamlit_errors(app, ticker):
    """
    Fail the test if Streamlit raised an exception.
    """

    if not app.exception:
        return

    errors = []

    for exception in app.exception:

        value = getattr(
            exception,
            "value",
            exception,
        )

        errors.append(str(value))

    assert (
        not errors
    ), f"Company Profile page raised an exception " f"for {ticker}:\n" + "\n".join(
        errors
    )


# ============================================================
# MEASURE ONE COMPANY PROFILE
# ============================================================


def _measure_company_profile(ticker):
    """
    Load Company Profile and measure the time required
    to display the requested ticker.
    """

    # --------------------------------------------------------
    # Verify page exists
    # --------------------------------------------------------

    assert COMPANY_PROFILE_PAGE.exists(), (
        "Company Profile page not found:\n" f"{COMPANY_PROFILE_PAGE}"
    )

    # --------------------------------------------------------
    # Create Streamlit AppTest
    # --------------------------------------------------------

    app = AppTest.from_file(
        str(COMPANY_PROFILE_PAGE),
        default_timeout=10,
    )

    # --------------------------------------------------------
    # Initial page load
    # --------------------------------------------------------

    start_time = time.perf_counter()

    app.run()

    initial_load_time = time.perf_counter() - start_time

    _assert_no_streamlit_errors(
        app,
        ticker,
    )

    # --------------------------------------------------------
    # Find company selector
    # --------------------------------------------------------

    selector = _find_company_selector(app)

    assert selector is not None, (
        "Company selector was not found on the "
        "Company Profile page.\n"
        f"Page: {COMPANY_PROFILE_PAGE}"
    )

    # --------------------------------------------------------
    # Read available options
    # --------------------------------------------------------

    options = list(
        getattr(
            selector,
            "options",
            [],
        )
    )

    assert options, (
        "Company selector contains no options.\n" f"Ticker being tested: {ticker}"
    )

    # --------------------------------------------------------
    # Find complete label for ticker
    # --------------------------------------------------------

    selected_option = _find_ticker_option(
        options,
        ticker,
    )

    assert selected_option is not None, (
        f"Ticker '{ticker}' was not found "
        "inside the Company Profile selector.\n\n"
        "Available options:\n" + "\n".join(str(option) for option in options)
    )

    # --------------------------------------------------------
    # Select complete option label
    # --------------------------------------------------------

    selector.set_value(selected_option)

    # --------------------------------------------------------
    # Measure selected company reload
    # --------------------------------------------------------

    start_time = time.perf_counter()

    app.run()

    profile_load_time = time.perf_counter() - start_time

    _assert_no_streamlit_errors(
        app,
        ticker,
    )

    return {
        "ticker": ticker,
        "initial_load": initial_load_time,
        "profile_load": profile_load_time,
        "selected_option": str(selected_option),
    }


# ============================================================
# PERFORMANCE TEST
# ============================================================


def test_company_profile_load_time():
    """
    Verify Company Profile performance for five tickers.

    Requirement:

        Every company profile must load in
        less than 3 seconds.
    """

    results = []

    print()
    print("=" * 70)
    print("COMPANY PROFILE DASHBOARD PERFORMANCE TEST")
    print("=" * 70)

    print(f"Page    : {COMPANY_PROFILE_PAGE}")

    print(f"Tickers : {len(TEST_TICKERS)}")

    print(f"Target  : < {MAX_LOAD_TIME:.1f} seconds each")

    print()

    # --------------------------------------------------------
    # Test all five tickers
    # --------------------------------------------------------

    for ticker in TEST_TICKERS:

        result = _measure_company_profile(ticker)

        results.append(result)

        print(
            f"{ticker:<12} | "
            f"Initial: "
            f"{result['initial_load']:.4f}s | "
            f"Profile: "
            f"{result['profile_load']:.4f}s"
        )

        print(f"{'':12} | " f"Selected: " f"{result['selected_option']}")

    # --------------------------------------------------------
    # Extract profile timings
    # --------------------------------------------------------

    profile_times = [result["profile_load"] for result in results]

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    average_time = sum(profile_times) / len(profile_times)

    fastest_time = min(profile_times)

    slowest_time = max(profile_times)

    print()

    print(f"Average profile load : " f"{average_time:.4f}s")

    print(f"Fastest profile load : " f"{fastest_time:.4f}s")

    print(f"Slowest profile load : " f"{slowest_time:.4f}s")

    print("=" * 70)

    # --------------------------------------------------------
    # Check 3-second requirement
    # --------------------------------------------------------

    slow_results = [
        result for result in results if result["profile_load"] >= MAX_LOAD_TIME
    ]

    assert not slow_results, (
        "Company Profile performance requirement failed.\n\n"
        f"Required: every profile < "
        f"{MAX_LOAD_TIME:.1f} seconds\n\n"
        + "\n".join(
            f"{result['ticker']}: " f"{result['profile_load']:.4f}s"
            for result in slow_results
        )
    )
