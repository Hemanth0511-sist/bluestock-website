import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"


def test_screener_min_roe_returns_only_companies_above_threshold():
    response = requests.get(
        f"{BASE_URL}/screener",
        params={"min_roe": 15},
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert "results" in data
    assert isinstance(data["results"], list)

    companies = data["results"]

    for company in companies:
        roe = company.get("roe_pct")

        assert roe is not None
        assert float(roe) >= 15


def test_screener_invalid_parameter_returns_400():
    response = requests.get(
        f"{BASE_URL}/screener",
        params={"min_roe": "invalid"},
        timeout=10,
    )

    assert response.status_code == 400
