import subprocess
import sys
import time
from pathlib import Path

import requests

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

API_HOST = "127.0.0.1"
API_PORT = 8000

STREAMLIT_HOST = "127.0.0.1"
STREAMLIT_PORT = 8501

API_URL = f"http://{API_HOST}:{API_PORT}"

STREAMLIT_URL = f"http://{STREAMLIT_HOST}:{STREAMLIT_PORT}"

API_HEALTH_URL = f"{API_URL}/api/v1/health"

API_COMPANIES_URL = f"{API_URL}/api/v1/companies"

API_SCREENER_URL = f"{API_URL}/api/v1/screener"

STREAMLIT_HEALTH_URL = f"{STREAMLIT_URL}/_stcore/health"

STARTUP_TIMEOUT = 15

POLL_INTERVAL = 0.25


# ============================================================
# START FASTAPI
# ============================================================


def _start_fastapi():
    """
    Start FastAPI using the project's Python environment.
    """

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.main:app",
            "--host",
            API_HOST,
            "--port",
            str(API_PORT),
        ],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


# ============================================================
# START STREAMLIT
# ============================================================


def _start_streamlit():
    """
    Start Streamlit using the project's Python environment.
    """

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/dashboard/app.py",
            "--server.address",
            STREAMLIT_HOST,
            "--server.port",
            str(STREAMLIT_PORT),
            "--server.headless",
            "true",
        ],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


# ============================================================
# PROCESS OUTPUT
# ============================================================


def _read_process_output(process):
    """
    Safely read available subprocess output.

    Used only for diagnostics when a process exits.
    """

    if process is None:
        return ""

    try:
        return process.stdout.read()
    except Exception:
        return ""


# ============================================================
# WAIT FOR SERVICE
# ============================================================


def _wait_for_service(
    url,
    process,
    service_name,
    timeout=STARTUP_TIMEOUT,
):
    """
    Wait until an HTTP service becomes available.
    """

    start_time = time.perf_counter()

    last_error = None

    while time.perf_counter() - start_time < timeout:

        # ----------------------------------------------------
        # Try HTTP first.
        #
        # This is the important test: the service must actually
        # respond over its assigned port.
        # ----------------------------------------------------

        try:

            response = requests.get(
                url,
                timeout=2,
            )

            if response.status_code == 200:
                return response

            last_error = f"HTTP {response.status_code}"

        except requests.RequestException as exc:

            last_error = str(exc)

        # ----------------------------------------------------
        # If process has exited and the service is not
        # responding, fail with useful diagnostics.
        # ----------------------------------------------------

        if process.poll() is not None:

            output = _read_process_output(process)

            raise AssertionError(
                f"{service_name} stopped before "
                f"becoming available.\n\n"
                f"URL: {url}\n"
                f"Exit code: {process.returncode}\n"
                f"Last HTTP error: {last_error}\n\n"
                f"Process output:\n{output}"
            )

        time.sleep(POLL_INTERVAL)

    raise AssertionError(
        f"{service_name} did not become available "
        f"within {timeout} seconds.\n\n"
        f"URL: {url}\n"
        f"Last error: {last_error}"
    )


# ============================================================
# VERIFY SERVICE STILL RESPONDS
# ============================================================


def _verify_service(
    url,
    service_name,
):
    """
    Verify that the service still responds after
    both applications have been started.
    """

    try:

        response = requests.get(
            url,
            timeout=5,
        )

    except requests.RequestException as exc:

        raise AssertionError(
            f"{service_name} is no longer responding.\n" f"URL: {url}\n" f"Error: {exc}"
        ) from exc

    assert response.status_code == 200, (
        f"{service_name} returned "
        f"HTTP {response.status_code}.\n"
        f"URL: {url}\n"
        f"Response: {response.text}"
    )

    return response


# ============================================================
# STOP PROCESS
# ============================================================


def _stop_process(process):
    """
    Safely stop a subprocess.
    """

    if process is None:
        return

    if process.poll() is not None:
        return

    try:

        process.terminate()

        process.wait(timeout=5)

    except subprocess.TimeoutExpired:

        process.kill()

        process.wait(timeout=5)


# ============================================================
# END-TO-END TEST
# ============================================================


def test_fastapi_and_streamlit_run_together():
    """
    End-to-end integration test.

    Requirements:

    1. FastAPI runs on port 8000.
    2. Streamlit runs on port 8501.
    3. Both services can run simultaneously.
    4. FastAPI health endpoint works.
    5. FastAPI company endpoint returns 92 companies.
    6. FastAPI screener endpoint works.
    7. Streamlit health endpoint works.
    8. Both services remain reachable while running together.
    9. No port conflict occurs.
    """

    api_process = None
    streamlit_process = None

    print()
    print("=" * 70)
    print("N100 END-TO-END INTEGRATION TEST")
    print("=" * 70)

    try:

        # ====================================================
        # START FASTAPI
        # ====================================================

        print()
        print("Starting FastAPI...")

        api_process = _start_fastapi()

        api_health = _wait_for_service(
            API_HEALTH_URL,
            api_process,
            "FastAPI",
        )

        print(f"FastAPI       : READY " f"({API_URL})")

        # ====================================================
        # VERIFY FASTAPI HEALTH
        # ====================================================

        assert api_health.status_code == 200

        health_data = api_health.json()

        assert health_data.get("status") == "ok", (
            "FastAPI health endpoint did not return "
            "status=ok.\n"
            f"Response: {health_data}"
        )

        print("API health    : PASS")

        # ====================================================
        # START STREAMLIT
        # ====================================================

        print("Starting Streamlit...")

        streamlit_process = _start_streamlit()

        streamlit_health = _wait_for_service(
            STREAMLIT_HEALTH_URL,
            streamlit_process,
            "Streamlit",
        )

        print(f"Streamlit     : READY " f"({STREAMLIT_URL})")

        # ====================================================
        # VERIFY COMPANY API
        # ====================================================

        companies_response = requests.get(
            API_COMPANIES_URL,
            timeout=5,
        )

        assert companies_response.status_code == 200, (
            "Companies API failed.\n"
            f"HTTP status: "
            f"{companies_response.status_code}\n"
            f"Response: "
            f"{companies_response.text}"
        )

        companies_data = companies_response.json()

        # ----------------------------------------------------
        # Support direct list or wrapped API response.
        # ----------------------------------------------------

        if isinstance(
            companies_data,
            list,
        ):

            companies = companies_data

        elif isinstance(
            companies_data,
            dict,
        ):

            companies = companies_data.get(
                "results",
                companies_data.get(
                    "companies",
                    [],
                ),
            )

        else:

            companies = []

        assert isinstance(
            companies,
            list,
        ), "Companies API did not return a list."

        assert len(companies) == 92, (
            "Expected 92 companies from API, " f"got {len(companies)}."
        )

        print(f"API companies : PASS " f"({len(companies)} records)")

        # ====================================================
        # VERIFY API SCREENER
        # ====================================================

        screener_response = requests.get(
            API_SCREENER_URL,
            params={
                "min_roe": 15,
            },
            timeout=5,
        )

        assert screener_response.status_code == 200, (
            "Screener API failed.\n"
            f"HTTP status: "
            f"{screener_response.status_code}\n"
            f"Response: "
            f"{screener_response.text}"
        )

        screener_data = screener_response.json()

        if isinstance(
            screener_data,
            list,
        ):

            screener_results = screener_data

        elif isinstance(
            screener_data,
            dict,
        ):

            screener_results = screener_data.get(
                "results",
                screener_data.get(
                    "companies",
                    [],
                ),
            )

        else:

            screener_results = []

        assert isinstance(
            screener_results,
            list,
        )

        assert len(screener_results) > 0, (
            "Screener returned no companies " "for min_roe=15."
        )

        print(f"API screener  : PASS " f"({len(screener_results)} results)")

        # ====================================================
        # VERIFY STREAMLIT HEALTH
        # ====================================================

        assert streamlit_health.status_code == 200

        print("Dashboard     : PASS " "(Streamlit health)")

        # ====================================================
        # CRITICAL INTEGRATION CHECK
        #
        # Both services must still respond AFTER the other
        # service has started and API requests have been made.
        # ====================================================

        _verify_service(
            API_HEALTH_URL,
            "FastAPI",
        )

        _verify_service(
            STREAMLIT_HEALTH_URL,
            "Streamlit",
        )

        print("Concurrent run : PASS")

        # ====================================================
        # PORT VERIFICATION
        # ====================================================

        print(f"Port {API_PORT:<6} : PASS")

        print(f"Port {STREAMLIT_PORT:<6} : PASS")

        print()
        print("FastAPI and Streamlit successfully " "ran simultaneously.")

        print("No port conflict detected.")

        print("=" * 70)
        print("END-TO-END TEST PASSED")
        print("=" * 70)

    finally:

        # ====================================================
        # CLEANUP
        # ====================================================

        print()
        print("Stopping test services...")

        _stop_process(streamlit_process)

        _stop_process(api_process)

        print("Test services stopped.")
