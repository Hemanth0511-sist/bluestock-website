from pathlib import Path

import requests
from streamlit.testing.v1 import AppTest

# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "http://127.0.0.1:8000/api/v1"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DASHBOARD_PAGE = PROJECT_ROOT / "src" / "dashboard" / "pages" / "03_screener.py"


# ============================================================
# COMMON HELPERS
# ============================================================


def _normalise_ticker(value):
    """Return a clean, comparable ticker string."""
    if value is None:
        return None

    text = str(value).strip().upper()

    if not text or text == "NAN":
        return None

    return text


def _extract_tickers_from_dataframe(df):
    """
    Extract company identifiers from a Streamlit dataframe/table.

    The dashboard normally exposes Company ID. Ticker/Symbol
    are accepted as fallbacks.
    """

    if df is None or df.empty:
        return set()

    possible_columns = (
        "Company ID",
        "company_id",
        "Ticker",
        "ticker",
        "Symbol",
        "symbol",
    )

    column = next(
        (name for name in possible_columns if name in df.columns),
        None,
    )

    if column is None:
        return set()

    tickers = set()

    for value in df[column].tolist():
        ticker = _normalise_ticker(value)

        if ticker:
            tickers.add(ticker)

    return tickers


def _find_widget(widgets, label):
    """
    Find a Streamlit widget by case-insensitive partial label.
    """

    wanted = label.strip().lower()

    for widget in widgets:
        actual = str(getattr(widget, "label", "")).strip().lower()

        if wanted in actual:
            return widget

    return None


def _set_checkbox(app, label, value):
    """
    Set a checkbox only if it exists.
    """

    checkbox = _find_widget(
        app.checkbox,
        label,
    )

    assert checkbox is not None, f"Dashboard checkbox not found: {label}"

    checkbox.set_value(value)


def _set_slider(app, label, value):
    """
    Set a slider by partial label.
    """

    slider = _find_widget(
        app.slider,
        label,
    )

    assert slider is not None, f"Dashboard slider not found: {label}"

    slider.set_value(value)


# ============================================================
# API SCREENER
# ============================================================


def _api_screener_tickers():
    """
    Get the authoritative screener result from FastAPI.

    Integration configuration:

        min_roe = 15

    No other filters are supplied.
    """

    response = requests.get(
        f"{BASE_URL}/screener",
        params={
            "min_roe": 15,
        },
        timeout=10,
    )

    assert response.status_code == 200, (
        f"API returned {response.status_code}: " f"{response.text}"
    )

    data = response.json()

    assert isinstance(data, dict), "Expected the screener API to return a JSON object."

    results = data.get("results", [])

    assert isinstance(
        results, list
    ), "Expected API response field 'results' to be a list."

    tickers = set()

    for company in results:

        if not isinstance(company, dict):
            continue

        ticker = _normalise_ticker(
            company.get("ticker") or company.get("company_id") or company.get("symbol")
        )

        if ticker:
            tickers.add(ticker)

    assert tickers, "API returned no screener tickers."

    return tickers


# ============================================================
# DASHBOARD SCREENER
# ============================================================


def _dashboard_screener_tickers():
    """
    Run the real Streamlit screener and configure it to the
    exact same effective filter as the API:

        ROE enabled
        ROE minimum = 15
        every other filter disabled

    The dashboard must therefore call:

        /api/v1/screener?min_roe=15

    and expose the same 52 companies.
    """

    assert DASHBOARD_PAGE.exists(), f"Dashboard page not found: {DASHBOARD_PAGE}"

    app = AppTest.from_file(str(DASHBOARD_PAGE))

    # --------------------------------------------------------
    # Initial run
    # --------------------------------------------------------

    app.run()

    # --------------------------------------------------------
    # Check initial exceptions
    # --------------------------------------------------------

    if app.exception:
        errors = [
            str(
                getattr(
                    exception,
                    "value",
                    exception,
                )
            )
            for exception in app.exception
        ]

        assert not errors, (
            "Streamlit dashboard raised an exception during "
            "initial run:\n" + "\n".join(errors)
        )

    # --------------------------------------------------------
    # Configure ROE
    # --------------------------------------------------------

    _set_checkbox(
        app,
        "Enable ROE Filter",
        True,
    )

    _set_slider(
        app,
        "ROE Minimum",
        15,
    )

    # --------------------------------------------------------
    # Explicitly disable every other dashboard filter.
    #
    # This is important because the test must represent the
    # same effective query as the API request.
    # --------------------------------------------------------

    other_filters = [
        "Enable D/E Filter",
        "Enable FCF Filter",
        "Enable Revenue CAGR Filter",
        "Enable PAT CAGR Filter",
        "Enable OPM Filter",
        "Enable P/E Filter",
        "Enable P/B Filter",
        "Enable Dividend Filter",
        "Enable ICR Filter",
    ]

    for label in other_filters:
        _set_checkbox(
            app,
            label,
            False,
        )

    # --------------------------------------------------------
    # Rerun after changing all widgets
    # --------------------------------------------------------

    app.run()

    # --------------------------------------------------------
    # Check final exceptions
    # --------------------------------------------------------

    if app.exception:
        errors = [
            str(
                getattr(
                    exception,
                    "value",
                    exception,
                )
            )
            for exception in app.exception
        ]

        assert not errors, (
            "Streamlit dashboard raised an exception after "
            "applying the integration-test filters:\n" + "\n".join(errors)
        )

    # --------------------------------------------------------
    # Extract results from displayed dataframes
    # --------------------------------------------------------

    dashboard_tickers = set()

    for dataframe in app.dataframe:

        try:
            df = dataframe.value
        except Exception:
            continue

        dashboard_tickers.update(_extract_tickers_from_dataframe(df))

    # --------------------------------------------------------
    # Streamlit may expose a table instead of dataframe
    # --------------------------------------------------------

    for table in app.table:

        try:
            df = table.value
        except Exception:
            continue

        dashboard_tickers.update(_extract_tickers_from_dataframe(df))

    assert dashboard_tickers, "Dashboard returned no company identifiers."

    return dashboard_tickers


# ============================================================
# INTEGRATION TEST
# ============================================================


def test_dashboard_screener_matches_api():
    """
    Verify that the real Streamlit dashboard and FastAPI
    screener return exactly the same companies for:

        min_roe = 15
    """

    api_tickers = _api_screener_tickers()

    dashboard_tickers = _dashboard_screener_tickers()

    only_in_api = api_tickers - dashboard_tickers

    only_in_dashboard = dashboard_tickers - api_tickers

    assert dashboard_tickers == api_tickers, (
        "\nDashboard and API screener results do not match."
        f"\n\nAPI tickers ({len(api_tickers)}):"
        f"\n{sorted(api_tickers)}"
        f"\n\nDashboard tickers ({len(dashboard_tickers)}):"
        f"\n{sorted(dashboard_tickers)}"
        f"\n\nOnly in API ({len(only_in_api)}):"
        f"\n{sorted(only_in_api)}"
        f"\n\nOnly in Dashboard ({len(only_in_dashboard)}):"
        f"\n{sorted(only_in_dashboard)}"
    )


# ============================================================
# BASIC DASHBOARD DATA TEST
# ============================================================


def test_dashboard_database_contains_92_companies():
    """
    Verify the dashboard database universe contains the
    expected 92 companies.

    This test intentionally uses the dashboard's database
    helper rather than the screener API.
    """

    from src.dashboard.utils.db import get_companies

    companies = get_companies()

    assert companies is not None
    assert not companies.empty

    assert len(companies) == 92, f"Expected 92 companies, found {len(companies)}."
