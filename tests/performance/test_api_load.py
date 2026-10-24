import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "http://127.0.0.1:8000/api/v1"

SCREENER_URL = f"{BASE_URL}/screener"

CONCURRENT_REQUESTS = 10

TIMEOUT_SECONDS = 10

PARAMETERS = {
    "min_roe": 15,
}


# ============================================================
# SINGLE API REQUEST
# ============================================================


def _call_screener(request_number):
    """
    Execute one screener API request.

    Returns:
        {
            "request": int,
            "status_code": int,
            "elapsed": float,
            "success": bool,
            "error": str | None
        }
    """

    start_time = time.perf_counter()

    try:
        response = requests.get(
            SCREENER_URL,
            params=PARAMETERS,
            timeout=TIMEOUT_SECONDS,
        )

        elapsed = time.perf_counter() - start_time

        return {
            "request": request_number,
            "status_code": response.status_code,
            "elapsed": elapsed,
            "success": response.status_code == 200,
            "error": None,
        }

    except Exception as exc:

        elapsed = time.perf_counter() - start_time

        return {
            "request": request_number,
            "status_code": None,
            "elapsed": elapsed,
            "success": False,
            "error": str(exc),
        }


# ============================================================
# LOAD TEST
# ============================================================


def test_screener_10_concurrent_requests():
    """
    Run 10 concurrent screener API requests.

    Performance requirement:

        - 10 requests must complete successfully.
        - Total wall-clock time must be below 10 seconds.
    """

    start_time = time.perf_counter()

    results = []

    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:

        futures = [
            executor.submit(
                _call_screener,
                request_number,
            )
            for request_number in range(
                1,
                CONCURRENT_REQUESTS + 1,
            )
        ]

        for future in as_completed(futures):

            result = future.result()

            results.append(result)

    total_time = time.perf_counter() - start_time

    # --------------------------------------------------------
    # Sort results for readable output
    # --------------------------------------------------------

    results.sort(key=lambda item: item["request"])

    # --------------------------------------------------------
    # Print performance information
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SCREENER API LOAD TEST")
    print("=" * 70)

    print(f"Concurrent requests : {CONCURRENT_REQUESTS}")

    print(f"Total wall time     : {total_time:.4f} seconds")

    print()

    for result in results:

        if result["success"]:

            print(
                f"Request {result['request']:02d} | "
                f"HTTP {result['status_code']} | "
                f"{result['elapsed']:.4f} seconds"
            )

        else:

            print(
                f"Request {result['request']:02d} | "
                f"FAILED | "
                f"{result['elapsed']:.4f} seconds | "
                f"{result['error']}"
            )

    print()

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    successful_results = [result for result in results if result["success"]]

    failed_results = [result for result in results if not result["success"]]

    if successful_results:

        response_times = [result["elapsed"] for result in successful_results]

        average_time = sum(response_times) / len(response_times)

        fastest_time = min(response_times)

        slowest_time = max(response_times)

        print(f"Successful requests: " f"{len(successful_results)}")

        print(f"Failed requests    : " f"{len(failed_results)}")

        print(f"Average response   : " f"{average_time:.4f} seconds")

        print(f"Fastest response   : " f"{fastest_time:.4f} seconds")

        print(f"Slowest response   : " f"{slowest_time:.4f} seconds")

    print("=" * 70)

    # --------------------------------------------------------
    # Assertions
    # --------------------------------------------------------

    assert len(results) == CONCURRENT_REQUESTS, (
        f"Expected {CONCURRENT_REQUESTS} results, " f"got {len(results)}"
    )

    assert (
        not failed_results
    ), "One or more screener API requests failed:\n" + "\n".join(
        str(result) for result in failed_results
    )

    assert total_time < 10.0, (
        f"Load test exceeded 10 seconds. " f"Actual time: {total_time:.4f} seconds"
    )
