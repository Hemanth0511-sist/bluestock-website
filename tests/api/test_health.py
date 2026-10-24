import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"


def test_health_status():
    response = requests.get(f"{BASE_URL}/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert "db_row_counts" in data


def test_health_contains_all_tables():
    response = requests.get(f"{BASE_URL}/health")

    assert response.status_code == 200

    data = response.json()
    counts = data["db_row_counts"]

    expected_tables = {
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "market_cap",
        "peer_groups",
        "sectors",
        "prosandcons",
        "documents",
    }

    assert expected_tables.issubset(set(counts.keys()))
